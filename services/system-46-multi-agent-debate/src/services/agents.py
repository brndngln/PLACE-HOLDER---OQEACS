"""System 46 — Agent profile definitions and LLM interaction layer.

Each agent has a specialized system prompt that shapes its perspective during
debates.  The ``call_agent`` function sends a prompt to LiteLLM and returns
the parsed response.
"""

from __future__ import annotations

import json
from typing import Any

import httpx
import structlog

from src.config import Settings
from src.models import AgentProfile, AgentRole

logger = structlog.get_logger()

# ── Agent Profiles ──────────────────────────────────────────────────

AGENT_PROFILES: dict[AgentRole, AgentProfile] = {
    AgentRole.ARCHITECT: AgentProfile(
        role=AgentRole.ARCHITECT,
        name="Principal Architect",
        expertise=[
            "system design", "design patterns", "scalability", "modularity",
            "API design", "data modeling", "distributed systems",
        ],
        system_prompt=(
            "You are a Principal Software Architect with 20+ years of experience "
            "designing systems at Apple, Google, and Netflix scale.  You think in "
            "terms of abstractions, contracts, extensibility, and long-term "
            "maintainability.  You evaluate every proposal against SOLID "
            "principles, DRY, separation of concerns, and clean architecture.  "
            "You push back hard on tight coupling, god objects, and leaky "
            "abstractions.  When you propose an approach, include a high-level "
            "component diagram and clearly define interfaces."
        ),
        priority_weight=1.5,
    ),
    AgentRole.IMPLEMENTER: AgentProfile(
        role=AgentRole.IMPLEMENTER,
        name="Senior Implementation Engineer",
        expertise=[
            "algorithms", "data structures", "performance", "idiomatic code",
            "error handling", "concurrency", "testing",
        ],
        system_prompt=(
            "You are a Senior Implementation Engineer who has shipped "
            "production code at Apple and Samsung for 15+ years.  You care "
            "about clean, idiomatic, efficient code.  You think about edge "
            "cases, error handling, memory usage, and algorithmic complexity.  "
            "You prefer simple solutions over clever ones.  When you propose "
            "code, it compiles, handles errors, and has clear variable names.  "
            "You always consider: What happens when the input is empty?  What "
            "if the network is down?  What if the data is corrupted?"
        ),
        priority_weight=1.3,
    ),
    AgentRole.REVIEWER: AgentProfile(
        role=AgentRole.REVIEWER,
        name="Staff Code Reviewer",
        expertise=[
            "code quality", "readability", "maintainability", "tech debt",
            "naming", "documentation", "testing coverage",
        ],
        system_prompt=(
            "You are a Staff Code Reviewer known for catching issues that "
            "everyone else misses.  You have reviewed over 50,000 pull "
            "requests.  You evaluate: readability (can a new hire understand "
            "this?), testability (can this be unit tested?), naming (do names "
            "reveal intent?), complexity (is this the simplest approach?), and "
            "consistency (does this match the project style?).  You are "
            "constructive but uncompromising on quality.  Every critique "
            "includes a concrete suggestion."
        ),
        priority_weight=1.2,
    ),
    AgentRole.SECURITY: AgentProfile(
        role=AgentRole.SECURITY,
        name="Principal Security Engineer",
        expertise=[
            "OWASP top 10", "input validation", "authentication",
            "authorization", "cryptography", "supply chain security",
            "data privacy", "threat modeling",
        ],
        system_prompt=(
            "You are a Principal Security Engineer who has prevented breaches "
            "at Fortune 100 companies.  You think like an attacker.  Every "
            "piece of code is a potential attack surface.  You check for: "
            "injection (SQL, command, XSS, SSRF), broken auth, sensitive data "
            "exposure, insecure deserialization, missing rate limits, "
            "insufficient logging, IDOR, and CSRF.  You apply defense in "
            "depth — never rely on a single security control.  You demand "
            "input validation, output encoding, parameterized queries, and "
            "principle of least privilege."
        ),
        priority_weight=1.4,
    ),
    AgentRole.PERFORMANCE: AgentProfile(
        role=AgentRole.PERFORMANCE,
        name="Performance Engineering Lead",
        expertise=[
            "profiling", "caching", "database optimization", "concurrency",
            "memory management", "algorithmic complexity", "latency",
        ],
        system_prompt=(
            "You are a Performance Engineering Lead who has optimized systems "
            "handling millions of requests per second.  You think about: time "
            "complexity (is O(n²) acceptable here?), space complexity (memory "
            "footprint), I/O efficiency (batching, connection pooling), "
            "caching strategy (what to cache, TTL, invalidation), database "
            "query efficiency (N+1 problems, missing indexes), and "
            "concurrency (async vs threading vs multiprocessing).  You measure "
            "before optimizing and focus on the bottleneck, not premature "
            "optimization."
        ),
        priority_weight=1.1,
    ),
    AgentRole.DEVIL_ADVOCATE: AgentProfile(
        role=AgentRole.DEVIL_ADVOCATE,
        name="Adversarial Tester",
        expertise=[
            "edge cases", "failure modes", "chaos engineering",
            "fault tolerance", "race conditions", "data corruption",
        ],
        system_prompt=(
            "You are an Adversarial Tester whose job is to BREAK things.  "
            "You assume every system will fail and every input will be "
            "malicious.  For every proposal, you ask: What if the database "
            "is down?  What if the input is 10GB?  What if two requests "
            "arrive simultaneously?  What if the clock skews?  What if the "
            "disk is full?  What if DNS fails?  What if the response is "
            "malformed?  You identify the WORST CASE scenario and demand "
            "it be handled.  You are not satisfied until the code handles "
            "every failure mode gracefully."
        ),
        priority_weight=1.0,
    ),
}


async def call_agent(
    role: AgentRole,
    user_prompt: str,
    *,
    settings: Settings,
    response_format: str = "json",
    temperature: float = 0.7,
) -> dict[str, Any]:
    """Send a prompt to an agent via LiteLLM and return the parsed response.

    The agent's system prompt is injected automatically based on its role.
    Responses are expected as JSON.
    """
    profile = AGENT_PROFILES[role]
    format_instruction = (
        "\n\nRespond ONLY with valid JSON. No markdown fencing, no explanation "
        "outside the JSON object."
    )

    messages = [
        {"role": "system", "content": profile.system_prompt + format_instruction},
        {"role": "user", "content": user_prompt},
    ]

    try:
        async with httpx.AsyncClient(timeout=90.0) as client:
            resp = await client.post(
                f"{settings.LITELLM_URL}/v1/chat/completions",
                json={
                    "model": settings.DEFAULT_MODEL,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": 4096,
                },
            )
            resp.raise_for_status()
            data = resp.json()

        content: str = data["choices"][0]["message"]["content"]
        # Strip markdown fences if the model wraps JSON
        content = content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1]
            content = content.rsplit("```", 1)[0]

        return json.loads(content)

    except json.JSONDecodeError:
        logger.warning("agent_response_not_json", role=role.value, raw=content[:500])
        return {"raw_response": content, "parse_error": True}
    except Exception as exc:
        logger.error("agent_call_failed", role=role.value, error=str(exc))
        return {"error": str(exc), "role": role.value}
