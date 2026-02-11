"""System 46 — Pydantic v2 data models for the Multi-Agent Debate Engine."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# ── Enumerations ────────────────────────────────────────────────────


class AgentRole(str, Enum):
    ARCHITECT = "architect"
    IMPLEMENTER = "implementer"
    REVIEWER = "reviewer"
    SECURITY = "security"
    PERFORMANCE = "performance"
    DEVIL_ADVOCATE = "devil_advocate"


class DebatePhase(str, Enum):
    PROPOSAL = "proposal"
    CRITIQUE = "critique"
    REBUTTAL = "rebuttal"
    SYNTHESIS = "synthesis"
    VOTING = "voting"
    CONSENSUS = "consensus"


class VoteDecision(str, Enum):
    APPROVE = "approve"
    REJECT = "reject"
    ABSTAIN = "abstain"
    REQUEST_CHANGES = "request_changes"


class DebateStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    CONSENSUS_REACHED = "consensus_reached"
    DEADLOCKED = "deadlocked"
    TIMED_OUT = "timed_out"


# ── Core Models ─────────────────────────────────────────────────────


class AgentProfile(BaseModel):
    """Defines an agent's personality, expertise, and system prompt."""

    role: AgentRole
    name: str
    expertise: list[str]
    system_prompt: str
    priority_weight: float = Field(default=1.0, ge=0.1, le=5.0)


class Proposal(BaseModel):
    """An agent's proposed approach to a coding task."""

    agent_role: AgentRole
    approach: str
    reasoning: str
    code_outline: str
    estimated_complexity: str
    risks: list[str]
    alternatives_considered: list[str]
    confidence: float = Field(ge=0.0, le=1.0)


class Critique(BaseModel):
    """An agent's critique of a proposal."""

    critic_role: AgentRole
    target_role: AgentRole
    issues: list[CritiqueIssue]
    overall_assessment: str
    severity: str = Field(default="medium")


class CritiqueIssue(BaseModel):
    """A single issue raised during critique."""

    category: str
    description: str
    severity: str
    suggestion: str
    affected_section: str


class Rebuttal(BaseModel):
    """An agent's response to critiques of their proposal."""

    agent_role: AgentRole
    addressed_issues: list[AddressedIssue]
    revised_approach: str
    remaining_concerns: list[str]


class AddressedIssue(BaseModel):
    """How an issue from a critique was addressed."""

    original_issue: str
    resolution: str
    accepted: bool


class Vote(BaseModel):
    """An agent's vote on the final synthesis."""

    agent_role: AgentRole
    decision: VoteDecision
    reasoning: str
    conditions: list[str]
    confidence: float = Field(ge=0.0, le=1.0)


class DebateRound(BaseModel):
    """A single round of debate containing proposals, critiques, rebuttals."""

    round_number: int
    phase: DebatePhase
    proposals: list[Proposal] = Field(default_factory=list)
    critiques: list[Critique] = Field(default_factory=list)
    rebuttals: list[Rebuttal] = Field(default_factory=list)
    synthesis: str = ""
    votes: list[Vote] = Field(default_factory=list)
    consensus_score: float = 0.0
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class DebateResult(BaseModel):
    """The final outcome of a multi-agent debate."""

    debate_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    task_description: str
    status: DebateStatus
    rounds: list[DebateRound]
    final_approach: str
    final_code: str
    consensus_score: float
    participating_agents: list[AgentRole]
    total_duration_ms: float
    key_decisions: list[str]
    unresolved_concerns: list[str]
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ── Request / Response ──────────────────────────────────────────────


class DebateRequest(BaseModel):
    """Incoming request to start a multi-agent debate."""

    task_description: str = Field(min_length=10)
    context: str = ""
    language: str = "python"
    agents: list[AgentRole] = Field(
        default_factory=lambda: [
            AgentRole.ARCHITECT,
            AgentRole.IMPLEMENTER,
            AgentRole.REVIEWER,
            AgentRole.SECURITY,
            AgentRole.PERFORMANCE,
        ]
    )
    max_rounds: int = Field(default=5, ge=1, le=10)
    adversarial_mode: bool = False
    code_context: str = ""
    constraints: list[str] = Field(default_factory=list)


class QuickReviewRequest(BaseModel):
    """Request for a quick multi-perspective code review."""

    code: str = Field(min_length=1)
    language: str = "python"
    focus_areas: list[str] = Field(default_factory=list)


class QuickReviewResult(BaseModel):
    """Result of a quick multi-perspective review."""

    reviews: dict[str, AgentReview]
    overall_score: float
    critical_issues: list[str]
    recommendations: list[str]


class AgentReview(BaseModel):
    """A single agent's review of code."""

    agent_role: AgentRole
    score: float = Field(ge=0.0, le=10.0)
    issues: list[str]
    strengths: list[str]
    suggestions: list[str]


class DebateHistoryEntry(BaseModel):
    """Summary entry for debate history listing."""

    debate_id: str
    task_description: str
    status: DebateStatus
    consensus_score: float
    agents_count: int
    rounds_count: int
    created_at: datetime


# Forward reference resolution
Critique.model_rebuild()
