"""System 46 — Quick multi-perspective code review.

A lightweight alternative to full debates: sends code to multiple agents
in parallel and collates their reviews into a single scored report.
"""

from __future__ import annotations

import asyncio
from typing import Any

import structlog

from src.config import Settings
from src.models import AgentReview, AgentRole, QuickReviewRequest, QuickReviewResult
from src.services.agents import call_agent

logger = structlog.get_logger()

_REVIEW_AGENTS: list[AgentRole] = [
    AgentRole.REVIEWER,
    AgentRole.SECURITY,
    AgentRole.PERFORMANCE,
]


async def quick_review(
    request: QuickReviewRequest,
    settings: Settings,
) -> QuickReviewResult:
    """Run a quick parallel review of code from multiple perspectives."""
    focus_text = ""
    if request.focus_areas:
        focus_text = "\n\nFocus areas: " + ", ".join(request.focus_areas)

    prompt = (
        f"Review this {request.language} code:{focus_text}\n\n"
        f"```{request.language}\n{request.code}\n```\n\n"
        "Respond as JSON with: "
        '"score" (float 0-10), '
        '"issues" (list of strings), '
        '"strengths" (list of strings), '
        '"suggestions" (list of strings).'
    )

    tasks = [
        call_agent(role, prompt, settings=settings, temperature=0.3)
        for role in _REVIEW_AGENTS
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    reviews: dict[str, AgentReview] = {}
    all_issues: list[str] = []
    all_suggestions: list[str] = []
    scores: list[float] = []

    for role, result in zip(_REVIEW_AGENTS, results):
        if isinstance(result, Exception) or result.get("error"):
            reviews[role.value] = AgentReview(
                agent_role=role, score=0.0,
                issues=["Agent failed to respond"],
                strengths=[], suggestions=[],
            )
            continue

        score = float(result.get("score", 5.0))
        issues = result.get("issues", [])
        strengths = result.get("strengths", [])
        suggestions = result.get("suggestions", [])

        scores.append(score)
        all_issues.extend(f"[{role.value}] {i}" for i in issues)
        all_suggestions.extend(f"[{role.value}] {s}" for s in suggestions)

        reviews[role.value] = AgentReview(
            agent_role=role,
            score=min(max(score, 0.0), 10.0),
            issues=issues,
            strengths=strengths,
            suggestions=suggestions,
        )

    overall_score = sum(scores) / len(scores) if scores else 0.0
    critical = [i for i in all_issues if any(
        kw in i.lower() for kw in ("critical", "security", "injection", "vulnerability", "crash", "data loss")
    )]

    return QuickReviewResult(
        reviews=reviews,
        overall_score=round(overall_score, 1),
        critical_issues=critical,
        recommendations=all_suggestions[:10],
    )
