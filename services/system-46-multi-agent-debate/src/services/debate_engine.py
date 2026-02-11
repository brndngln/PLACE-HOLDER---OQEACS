"""System 46 — Core Debate Engine.

Orchestrates multi-agent debates: proposal → critique → rebuttal → synthesis
→ voting.  Repeats until consensus is reached or rounds are exhausted.
"""

from __future__ import annotations

import asyncio
import time
import uuid
from typing import Any

import structlog
from prometheus_client import Counter, Histogram

from src.config import Settings
from src.models import (
    AddressedIssue,
    AgentRole,
    Critique,
    CritiqueIssue,
    DebatePhase,
    DebateRequest,
    DebateResult,
    DebateRound,
    DebateStatus,
    Proposal,
    Rebuttal,
    Vote,
    VoteDecision,
)
from src.services.agents import AGENT_PROFILES, call_agent

logger = structlog.get_logger()

DEBATE_COUNT = Counter(
    "debate_total", "Total debates run", ["status"]
)
DEBATE_DURATION = Histogram(
    "debate_duration_seconds", "Debate duration", ["agent_count"]
)
ROUND_COUNT = Counter(
    "debate_rounds_total", "Total debate rounds", ["phase"]
)


class DebateEngine:
    """Orchestrates multi-agent debates for coding tasks."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._history: dict[str, DebateResult] = {}

    async def run_debate(self, request: DebateRequest) -> DebateResult:
        """Execute a full multi-agent debate and return the result."""
        debate_id = str(uuid.uuid4())
        start_time = time.perf_counter()
        agents = request.agents
        rounds: list[DebateRound] = []

        if request.adversarial_mode and AgentRole.DEVIL_ADVOCATE not in agents:
            agents = [*agents, AgentRole.DEVIL_ADVOCATE]

        logger.info(
            "debate_started",
            debate_id=debate_id,
            agents=[a.value for a in agents],
            task=request.task_description[:100],
        )

        status = DebateStatus.IN_PROGRESS
        final_approach = ""
        final_code = ""
        consensus_score = 0.0
        key_decisions: list[str] = []
        unresolved: list[str] = []

        for round_num in range(1, request.max_rounds + 1):
            # Phase 1: Proposals
            proposals = await self._collect_proposals(agents, request, rounds)
            ROUND_COUNT.labels(phase="proposal").inc()

            # Phase 2: Critiques
            critiques = await self._collect_critiques(agents, proposals, request)
            ROUND_COUNT.labels(phase="critique").inc()

            # Phase 3: Rebuttals
            rebuttals = await self._collect_rebuttals(proposals, critiques, request)
            ROUND_COUNT.labels(phase="rebuttal").inc()

            # Phase 4: Synthesis
            synthesis = await self._synthesize(proposals, critiques, rebuttals, request)
            ROUND_COUNT.labels(phase="synthesis").inc()

            # Phase 5: Voting
            votes = await self._collect_votes(agents, synthesis, request)
            consensus_score = self._calculate_consensus(votes, agents)
            ROUND_COUNT.labels(phase="voting").inc()

            debate_round = DebateRound(
                round_number=round_num,
                phase=DebatePhase.VOTING,
                proposals=proposals,
                critiques=critiques,
                rebuttals=rebuttals,
                synthesis=synthesis,
                votes=votes,
                consensus_score=consensus_score,
            )
            rounds.append(debate_round)

            key_decisions.extend(self._extract_key_decisions(votes))
            unresolved = self._extract_unresolved(votes)

            logger.info(
                "debate_round_complete",
                debate_id=debate_id,
                round=round_num,
                consensus=round(consensus_score, 3),
            )

            if consensus_score >= self.settings.MIN_CONSENSUS_SCORE:
                status = DebateStatus.CONSENSUS_REACHED
                final_approach = synthesis
                final_code = await self._generate_final_code(synthesis, request)
                break
        else:
            if consensus_score >= 0.5:
                status = DebateStatus.CONSENSUS_REACHED
                final_approach = rounds[-1].synthesis
                final_code = await self._generate_final_code(final_approach, request)
            else:
                status = DebateStatus.DEADLOCKED
                final_approach = rounds[-1].synthesis
                final_code = ""

        elapsed_ms = (time.perf_counter() - start_time) * 1000
        DEBATE_COUNT.labels(status=status.value).inc()
        DEBATE_DURATION.labels(agent_count=str(len(agents))).observe(elapsed_ms / 1000)

        result = DebateResult(
            debate_id=debate_id,
            task_description=request.task_description,
            status=status,
            rounds=rounds,
            final_approach=final_approach,
            final_code=final_code,
            consensus_score=consensus_score,
            participating_agents=agents,
            total_duration_ms=elapsed_ms,
            key_decisions=key_decisions,
            unresolved_concerns=unresolved,
        )
        self._history[debate_id] = result
        return result

    # ── Phase Implementations ───────────────────────────────────────

    async def _collect_proposals(
        self,
        agents: list[AgentRole],
        request: DebateRequest,
        prior_rounds: list[DebateRound],
    ) -> list[Proposal]:
        """Each agent proposes an approach in parallel."""
        prior_context = ""
        if prior_rounds:
            last = prior_rounds[-1]
            prior_context = (
                f"\n\nPrevious round synthesis: {last.synthesis}\n"
                f"Consensus score was {last.consensus_score:.2f}. "
                "Address unresolved issues from the previous round."
            )

        constraints_text = ""
        if request.constraints:
            constraints_text = "\n\nConstraints:\n" + "\n".join(
                f"- {c}" for c in request.constraints
            )

        prompt = (
            f"TASK: {request.task_description}\n\n"
            f"Language: {request.language}\n"
            f"Context: {request.context}\n"
            f"Existing code context: {request.code_context[:2000]}"
            f"{constraints_text}{prior_context}\n\n"
            "Propose your approach as JSON with keys: "
            '"approach" (string), "reasoning" (string), "code_outline" (string), '
            '"estimated_complexity" (string: "low"|"medium"|"high"), '
            '"risks" (list of strings), "alternatives_considered" (list of strings), '
            '"confidence" (float 0-1).'
        )

        tasks = [
            call_agent(role, prompt, settings=self.settings)
            for role in agents
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        proposals: list[Proposal] = []
        for role, result in zip(agents, results):
            if isinstance(result, Exception):
                logger.warning("proposal_failed", role=role.value, error=str(result))
                continue
            if result.get("error") or result.get("parse_error"):
                logger.warning("proposal_parse_error", role=role.value)
                continue
            try:
                proposals.append(Proposal(agent_role=role, **result))
            except Exception as exc:
                logger.warning("proposal_validation_failed", role=role.value, error=str(exc))
                proposals.append(
                    Proposal(
                        agent_role=role,
                        approach=result.get("approach", result.get("raw_response", "No proposal")),
                        reasoning=result.get("reasoning", ""),
                        code_outline=result.get("code_outline", ""),
                        estimated_complexity=result.get("estimated_complexity", "medium"),
                        risks=result.get("risks", []),
                        alternatives_considered=result.get("alternatives_considered", []),
                        confidence=float(result.get("confidence", 0.5)),
                    )
                )
        return proposals

    async def _collect_critiques(
        self,
        agents: list[AgentRole],
        proposals: list[Proposal],
        request: DebateRequest,
    ) -> list[Critique]:
        """Each agent critiques other agents' proposals."""
        proposals_text = "\n\n".join(
            f"[{p.agent_role.value.upper()}] Approach: {p.approach}\n"
            f"Reasoning: {p.reasoning}\nCode outline: {p.code_outline}\n"
            f"Risks: {', '.join(p.risks)}"
            for p in proposals
        )

        prompt = (
            f"TASK: {request.task_description}\n\n"
            f"The following proposals were made:\n\n{proposals_text}\n\n"
            "Critique ALL proposals (including your own if present). For each "
            "proposal you critique, identify specific issues. Respond as JSON "
            'with key "critiques" containing a list of objects, each with: '
            '"target_role" (string), "issues" (list of objects with '
            '"category", "description", "severity", "suggestion", '
            '"affected_section"), "overall_assessment" (string), '
            '"severity" (string: "low"|"medium"|"high"|"critical").'
        )

        tasks = [
            call_agent(role, prompt, settings=self.settings)
            for role in agents
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        critiques: list[Critique] = []
        for role, result in zip(agents, results):
            if isinstance(result, Exception) or result.get("error"):
                continue
            raw_critiques = result.get("critiques", [result])
            for rc in raw_critiques:
                try:
                    target_role_str = rc.get("target_role", "implementer")
                    try:
                        target_role = AgentRole(target_role_str.lower())
                    except ValueError:
                        target_role = AgentRole.IMPLEMENTER

                    issues = [
                        CritiqueIssue(**iss) if isinstance(iss, dict) else CritiqueIssue(
                            category="general", description=str(iss),
                            severity="medium", suggestion="", affected_section="",
                        )
                        for iss in rc.get("issues", [])
                    ]
                    critiques.append(
                        Critique(
                            critic_role=role,
                            target_role=target_role,
                            issues=issues,
                            overall_assessment=rc.get("overall_assessment", ""),
                            severity=rc.get("severity", "medium"),
                        )
                    )
                except Exception as exc:
                    logger.warning("critique_parse_error", role=role.value, error=str(exc))
        return critiques

    async def _collect_rebuttals(
        self,
        proposals: list[Proposal],
        critiques: list[Critique],
        request: DebateRequest,
    ) -> list[Rebuttal]:
        """Each proposer responds to critiques of their approach."""
        rebuttals: list[Rebuttal] = []

        for proposal in proposals:
            relevant_critiques = [
                c for c in critiques if c.target_role == proposal.agent_role
            ]
            if not relevant_critiques:
                continue

            critiques_text = "\n".join(
                f"[{c.critic_role.value}] {c.overall_assessment} "
                f"(Issues: {', '.join(i.description for i in c.issues)})"
                for c in relevant_critiques
            )

            prompt = (
                f"Your proposal: {proposal.approach}\n\n"
                f"Critiques received:\n{critiques_text}\n\n"
                "Address each critique. Respond as JSON with: "
                '"addressed_issues" (list of objects with "original_issue", '
                '"resolution", "accepted" boolean), '
                '"revised_approach" (string), '
                '"remaining_concerns" (list of strings).'
            )

            result = await call_agent(
                proposal.agent_role, prompt, settings=self.settings
            )
            if not result.get("error") and not result.get("parse_error"):
                try:
                    addressed = [
                        AddressedIssue(**ai) if isinstance(ai, dict) else AddressedIssue(
                            original_issue=str(ai), resolution="", accepted=False,
                        )
                        for ai in result.get("addressed_issues", [])
                    ]
                    rebuttals.append(
                        Rebuttal(
                            agent_role=proposal.agent_role,
                            addressed_issues=addressed,
                            revised_approach=result.get("revised_approach", ""),
                            remaining_concerns=result.get("remaining_concerns", []),
                        )
                    )
                except Exception as exc:
                    logger.warning("rebuttal_parse_error", role=proposal.agent_role.value, error=str(exc))
        return rebuttals

    async def _synthesize(
        self,
        proposals: list[Proposal],
        critiques: list[Critique],
        rebuttals: list[Rebuttal],
        request: DebateRequest,
    ) -> str:
        """Synthesize all perspectives into a unified approach."""
        proposals_text = "\n".join(
            f"[{p.agent_role.value}] {p.approach} (confidence: {p.confidence})"
            for p in proposals
        )
        critique_summary = "\n".join(
            f"[{c.critic_role.value} → {c.target_role.value}] {c.overall_assessment}"
            for c in critiques
        )
        rebuttal_summary = "\n".join(
            f"[{r.agent_role.value}] Revised: {r.revised_approach[:200]}"
            for r in rebuttals
        )

        prompt = (
            f"TASK: {request.task_description}\n\n"
            f"PROPOSALS:\n{proposals_text}\n\n"
            f"CRITIQUES:\n{critique_summary}\n\n"
            f"REBUTTALS:\n{rebuttal_summary}\n\n"
            "Synthesize all perspectives into a SINGLE unified approach that "
            "addresses the strongest points from each agent and resolves all "
            "critiques. Respond as JSON with key 'synthesis' (string: the "
            "complete unified approach)."
        )

        result = await call_agent(
            AgentRole.ARCHITECT, prompt, settings=self.settings, temperature=0.3
        )
        return result.get("synthesis", result.get("raw_response", "Synthesis failed"))

    async def _collect_votes(
        self,
        agents: list[AgentRole],
        synthesis: str,
        request: DebateRequest,
    ) -> list[Vote]:
        """Each agent votes on the synthesized approach."""
        prompt = (
            f"TASK: {request.task_description}\n\n"
            f"SYNTHESIZED APPROACH:\n{synthesis}\n\n"
            "Vote on this approach. Respond as JSON with: "
            '"decision" ("approve"|"reject"|"abstain"|"request_changes"), '
            '"reasoning" (string), '
            '"conditions" (list of strings — conditions for approval), '
            '"confidence" (float 0-1).'
        )

        tasks = [
            call_agent(role, prompt, settings=self.settings)
            for role in agents
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        votes: list[Vote] = []
        for role, result in zip(agents, results):
            if isinstance(result, Exception) or result.get("error"):
                votes.append(Vote(
                    agent_role=role,
                    decision=VoteDecision.ABSTAIN,
                    reasoning="Agent failed to respond",
                    conditions=[],
                    confidence=0.0,
                ))
                continue
            try:
                decision_str = result.get("decision", "abstain").lower()
                try:
                    decision = VoteDecision(decision_str)
                except ValueError:
                    decision = VoteDecision.ABSTAIN
                votes.append(Vote(
                    agent_role=role,
                    decision=decision,
                    reasoning=result.get("reasoning", ""),
                    conditions=result.get("conditions", []),
                    confidence=float(result.get("confidence", 0.5)),
                ))
            except Exception:
                votes.append(Vote(
                    agent_role=role,
                    decision=VoteDecision.ABSTAIN,
                    reasoning="Parse error",
                    conditions=[],
                    confidence=0.0,
                ))
        return votes

    def _calculate_consensus(
        self, votes: list[Vote], agents: list[AgentRole]
    ) -> float:
        """Calculate weighted consensus score from agent votes."""
        if not votes:
            return 0.0

        total_weight = 0.0
        approval_weight = 0.0

        for vote in votes:
            profile = AGENT_PROFILES.get(vote.agent_role)
            weight = profile.priority_weight if profile else 1.0
            total_weight += weight

            if vote.decision == VoteDecision.APPROVE:
                approval_weight += weight * vote.confidence
            elif vote.decision == VoteDecision.REQUEST_CHANGES:
                approval_weight += weight * vote.confidence * 0.5

        return approval_weight / total_weight if total_weight > 0 else 0.0

    async def _generate_final_code(
        self, synthesis: str, request: DebateRequest
    ) -> str:
        """Generate the final implementation based on the consensus approach."""
        prompt = (
            f"Based on this agreed approach, write COMPLETE, production-ready "
            f"{request.language} code.\n\n"
            f"APPROACH:\n{synthesis}\n\n"
            f"TASK: {request.task_description}\n"
            f"CONTEXT: {request.context}\n\n"
            "Respond as JSON with key 'code' containing the complete "
            "implementation. Include ALL imports, error handling, type hints, "
            "and docstrings. No placeholders."
        )

        result = await call_agent(
            AgentRole.IMPLEMENTER,
            prompt,
            settings=self.settings,
            temperature=0.2,
        )
        return result.get("code", result.get("raw_response", ""))

    def _extract_key_decisions(self, votes: list[Vote]) -> list[str]:
        """Extract key decisions from votes' reasoning."""
        return [
            f"[{v.agent_role.value}] {v.reasoning[:150]}"
            for v in votes
            if v.decision in (VoteDecision.APPROVE, VoteDecision.REQUEST_CHANGES)
            and v.reasoning
        ]

    def _extract_unresolved(self, votes: list[Vote]) -> list[str]:
        """Extract unresolved concerns from reject/request_changes votes."""
        concerns: list[str] = []
        for v in votes:
            if v.decision in (VoteDecision.REJECT, VoteDecision.REQUEST_CHANGES):
                concerns.extend(v.conditions)
        return concerns

    def get_debate(self, debate_id: str) -> DebateResult | None:
        """Retrieve a debate result by ID."""
        return self._history.get(debate_id)

    def list_debates(self) -> list[dict[str, Any]]:
        """List all debate summaries."""
        return [
            {
                "debate_id": d.debate_id,
                "task": d.task_description[:100],
                "status": d.status.value,
                "consensus": d.consensus_score,
                "rounds": len(d.rounds),
                "agents": len(d.participating_agents),
                "created_at": d.created_at.isoformat(),
            }
            for d in self._history.values()
        ]
