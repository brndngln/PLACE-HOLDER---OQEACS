"""System 46 — Debate engine unit tests."""

from __future__ import annotations

import pytest

from src.models import (
    AgentRole,
    DebateStatus,
    Vote,
    VoteDecision,
)
from src.services.agents import AGENT_PROFILES
from src.services.debate_engine import DebateEngine


class TestAgentProfiles:
    """Verify all agent profiles are correctly configured."""

    def test_all_roles_have_profiles(self) -> None:
        for role in AgentRole:
            assert role in AGENT_PROFILES, f"Missing profile for {role.value}"

    def test_profiles_have_system_prompts(self) -> None:
        for role, profile in AGENT_PROFILES.items():
            assert len(profile.system_prompt) > 50, f"{role.value} has short prompt"
            assert profile.name, f"{role.value} has no name"

    def test_profiles_have_expertise(self) -> None:
        for role, profile in AGENT_PROFILES.items():
            assert len(profile.expertise) >= 3, f"{role.value} has too few expertise areas"

    def test_priority_weights_are_valid(self) -> None:
        for role, profile in AGENT_PROFILES.items():
            assert 0.1 <= profile.priority_weight <= 5.0, (
                f"{role.value} has invalid weight {profile.priority_weight}"
            )

    def test_architect_has_highest_weight(self) -> None:
        arch_weight = AGENT_PROFILES[AgentRole.ARCHITECT].priority_weight
        for role, profile in AGENT_PROFILES.items():
            if role == AgentRole.ARCHITECT:
                continue
            assert arch_weight >= profile.priority_weight, (
                f"Architect weight ({arch_weight}) should be >= {role.value} ({profile.priority_weight})"
            )


class TestConsensusCalculation:
    """Test the weighted consensus scoring logic."""

    def test_full_approval(self, engine: DebateEngine) -> None:
        votes = [
            Vote(agent_role=AgentRole.ARCHITECT, decision=VoteDecision.APPROVE, reasoning="ok", conditions=[], confidence=1.0),
            Vote(agent_role=AgentRole.IMPLEMENTER, decision=VoteDecision.APPROVE, reasoning="ok", conditions=[], confidence=1.0),
            Vote(agent_role=AgentRole.REVIEWER, decision=VoteDecision.APPROVE, reasoning="ok", conditions=[], confidence=1.0),
        ]
        agents = [AgentRole.ARCHITECT, AgentRole.IMPLEMENTER, AgentRole.REVIEWER]
        score = engine._calculate_consensus(votes, agents)
        assert score == 1.0

    def test_full_rejection(self, engine: DebateEngine) -> None:
        votes = [
            Vote(agent_role=AgentRole.ARCHITECT, decision=VoteDecision.REJECT, reasoning="no", conditions=[], confidence=1.0),
            Vote(agent_role=AgentRole.IMPLEMENTER, decision=VoteDecision.REJECT, reasoning="no", conditions=[], confidence=1.0),
        ]
        agents = [AgentRole.ARCHITECT, AgentRole.IMPLEMENTER]
        score = engine._calculate_consensus(votes, agents)
        assert score == 0.0

    def test_mixed_votes_weighted(self, engine: DebateEngine) -> None:
        votes = [
            Vote(agent_role=AgentRole.ARCHITECT, decision=VoteDecision.APPROVE, reasoning="yes", conditions=[], confidence=1.0),
            Vote(agent_role=AgentRole.SECURITY, decision=VoteDecision.REJECT, reasoning="no", conditions=["fix auth"], confidence=1.0),
        ]
        agents = [AgentRole.ARCHITECT, AgentRole.SECURITY]
        score = engine._calculate_consensus(votes, agents)
        assert 0.0 < score < 1.0

    def test_request_changes_partial_score(self, engine: DebateEngine) -> None:
        votes = [
            Vote(agent_role=AgentRole.REVIEWER, decision=VoteDecision.REQUEST_CHANGES, reasoning="minor fixes", conditions=["add types"], confidence=0.8),
        ]
        agents = [AgentRole.REVIEWER]
        score = engine._calculate_consensus(votes, agents)
        assert 0.0 < score < 1.0

    def test_empty_votes(self, engine: DebateEngine) -> None:
        score = engine._calculate_consensus([], [])
        assert score == 0.0

    def test_abstain_does_not_count(self, engine: DebateEngine) -> None:
        votes = [
            Vote(agent_role=AgentRole.ARCHITECT, decision=VoteDecision.APPROVE, reasoning="yes", conditions=[], confidence=1.0),
            Vote(agent_role=AgentRole.DEVIL_ADVOCATE, decision=VoteDecision.ABSTAIN, reasoning="n/a", conditions=[], confidence=0.0),
        ]
        agents = [AgentRole.ARCHITECT, AgentRole.DEVIL_ADVOCATE]
        score = engine._calculate_consensus(votes, agents)
        assert score > 0.5


class TestDebateHistory:
    """Test debate history management."""

    def test_list_empty(self, engine: DebateEngine) -> None:
        assert engine.list_debates() == []

    def test_get_missing_debate(self, engine: DebateEngine) -> None:
        assert engine.get_debate("nonexistent") is None
