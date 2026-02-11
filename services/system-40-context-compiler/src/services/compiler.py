"""Core context compilation engine — assembles optimal token context per LLM invocation."""
from __future__ import annotations

import hashlib
import json
from typing import Any

import httpx
import redis.asyncio as aioredis
import structlog

from src.config import Settings
from src.models import ContextBlock, ContextRequest, ContextResponse
from src.services.embeddings import EmbeddingService
from src.services.qdrant_client import QdrantSearchService
from src.utils.tokens import count_tokens, truncate_to_tokens

logger = structlog.get_logger()

CONTEXT_PRIORITY: list[tuple[str, int, str]] = [
    ("system_prompt", 1, "ALWAYS"),
    ("task_description", 2, "ALWAYS"),
    ("spec_md", 3, "IF_EXISTS"),
    ("referenced_files", 10, "BY_RELEVANCE"),
    ("open_files", 11, "BY_RECENCY"),
    ("error_context", 12, "IF_EXISTS"),
    ("qdrant_semantic", 20, "TOP_K"),
    ("qdrant_antipatterns", 21, "TOP_K"),
    ("adr_relevant", 22, "TOP_K"),
    ("architecture_rules", 30, "COMPRESSED"),
    ("compliance_rules", 31, "IF_TAGGED"),
    ("domain_module", 32, "IF_TAGGED"),
    ("past_feedback", 40, "RECENT_K"),
    ("conversation_history", 41, "SLIDING"),
]

SOURCE_PRIORITY_MAP: dict[str, int] = {name: prio for name, prio, _ in CONTEXT_PRIORITY}

SYSTEM_PROMPTS: dict[str, str] = {
    "architect": (
        "You are a senior software architect. Design systems with scalability, "
        "maintainability, and security as primary concerns. Use established patterns. "
        "Justify every architectural decision."
    ),
    "developer": (
        "You are a senior software developer. Write production-grade code with "
        "comprehensive error handling, type hints, and tests. Follow the project's "
        "coding conventions. No shortcuts."
    ),
    "tester": (
        "You are a senior QA engineer. Write thorough test suites covering edge cases, "
        "error conditions, and integration points. Use pytest with fixtures. Aim for "
        "high coverage without redundant tests."
    ),
    "reviewer": (
        "You are a senior code reviewer. Analyze code for correctness, security, "
        "performance, and maintainability. Provide specific, actionable feedback. "
        "Cite industry best practices."
    ),
    "optimizer": (
        "You are a performance optimization specialist. Profile before optimizing. "
        "Focus on algorithmic improvements over micro-optimizations. Measure everything."
    ),
    "security": (
        "You are a security engineer. Identify vulnerabilities using OWASP Top 10, "
        "CWE, and SANS 25. Provide remediation code, not just warnings. "
        "Assume adversarial input at every boundary."
    ),
}

DOMAIN_MODULES: dict[str, str] = {
    "fintech": (
        "Financial domain: Use decimal arithmetic (never floats for money). "
        "Implement idempotency for all transactions. Follow PCI-DSS for card data. "
        "Audit log every state change. Use event sourcing for ledger entries."
    ),
    "healthcare": (
        "Healthcare domain: HIPAA compliance required. Encrypt PHI at rest and in transit. "
        "Implement BAA-compliant audit trails. Use FHIR R4 for interoperability. "
        "Minimum necessary access principle."
    ),
    "ecommerce": (
        "E-commerce domain: Implement cart with optimistic locking. "
        "Idempotent payment processing. Inventory reservation with TTL. "
        "GDPR-compliant customer data handling."
    ),
    "saas": (
        "SaaS domain: Multi-tenant data isolation. Usage-based metering. "
        "Feature flags for progressive rollout. Webhook delivery with retry. "
        "Rate limiting per tenant."
    ),
    "realtime": (
        "Real-time domain: WebSocket connection management with heartbeat. "
        "Eventual consistency with CRDT or OT. Message ordering guarantees. "
        "Graceful degradation under load."
    ),
    "iot": (
        "IoT domain: MQTT for device communication. Time-series data storage. "
        "Edge computing for latency-sensitive operations. OTA firmware updates. "
        "Device provisioning and certificate rotation."
    ),
    "mobile": (
        "Mobile domain: Offline-first architecture. Sync conflict resolution. "
        "Optimistic UI updates. Push notification management. "
        "API versioning for backward compatibility."
    ),
}

COMPLIANCE_PROFILES: dict[str, str] = {
    "hipaa": (
        "HIPAA Compliance: Encrypt all PHI (AES-256 at rest, TLS 1.3 in transit). "
        "Implement access controls with minimum necessary principle. "
        "Maintain 6-year audit trail. Business Associate Agreements required. "
        "Breach notification within 60 days."
    ),
    "pci_dss": (
        "PCI-DSS Compliance: Never store CVV/CVC. Tokenize card numbers. "
        "Network segmentation for cardholder data environment. "
        "Quarterly vulnerability scans. Annual penetration testing. "
        "Encrypt transmission of cardholder data across open networks."
    ),
    "soc2": (
        "SOC 2 Type II: Implement security, availability, processing integrity, "
        "confidentiality, and privacy controls. Continuous monitoring. "
        "Change management process. Incident response plan. "
        "Vendor risk management."
    ),
    "gdpr": (
        "GDPR Compliance: Lawful basis for processing. Data minimization. "
        "Right to erasure (hard delete, not soft). Data portability (JSON/CSV export). "
        "72-hour breach notification. Privacy by design. "
        "Data Protection Impact Assessments for high-risk processing."
    ),
}


class ContextCompiler:
    """Assembles optimal context for each LLM invocation."""

    def __init__(
        self,
        qdrant: QdrantSearchService,
        embeddings: EmbeddingService,
        redis_client: aioredis.Redis,
        settings: Settings,
    ) -> None:
        self.qdrant = qdrant
        self.embeddings = embeddings
        self.redis = redis_client
        self.settings = settings

    async def compile(self, request: ContextRequest) -> ContextResponse:
        """Main compilation pipeline."""
        budget = request.token_budget

        candidates = await self._gather_candidates(request)
        scored = self._score_candidates(candidates, request)

        blocks: list[ContextBlock] = []
        excluded: list[ContextBlock] = []
        remaining_budget = budget

        for candidate in sorted(
            scored, key=lambda c: (SOURCE_PRIORITY_MAP.get(c.source, 99), -c.relevance_score)
        ):
            if candidate.token_count <= remaining_budget:
                blocks.append(candidate)
                remaining_budget -= candidate.token_count
            else:
                compressed = await self._compress_block(candidate, remaining_budget)
                if compressed and compressed.token_count <= remaining_budget:
                    blocks.append(compressed)
                    remaining_budget -= compressed.token_count
                else:
                    excluded.append(candidate)

        assembled = self._assemble_with_cache_hints(blocks)
        total_used = budget - remaining_budget

        context_hash = hashlib.sha256(assembled["text"].encode()).hexdigest()[:16]
        await self._cache_compilation(request.task_id, context_hash)

        logger.info(
            "context_compiled",
            task_id=request.task_id,
            tokens_used=total_used,
            budget_pct=round((total_used / budget) * 100, 1),
            blocks_included=len(blocks),
            blocks_excluded=len(excluded),
        )

        return ContextResponse(
            task_id=request.task_id,
            compiled_context=assembled["text"],
            blocks_included=blocks,
            blocks_excluded=excluded,
            total_tokens=total_used,
            budget_used_pct=round((total_used / budget) * 100, 2),
            kv_cache_hint=assembled["cache_hints"],
        )

    async def _gather_candidates(self, request: ContextRequest) -> list[ContextBlock]:
        """Gather all possible context blocks from all sources."""
        candidates: list[ContextBlock] = []

        system_prompt = SYSTEM_PROMPTS.get(request.agent_role, SYSTEM_PROMPTS["developer"])
        candidates.append(
            ContextBlock(
                source="system_prompt",
                content=system_prompt,
                token_count=count_tokens(system_prompt),
                relevance_score=1.0,
            )
        )

        candidates.append(
            ContextBlock(
                source="task_description",
                content=request.task_description,
                token_count=count_tokens(request.task_description),
                relevance_score=1.0,
            )
        )

        if request.error_context:
            candidates.append(
                ContextBlock(
                    source="error_context",
                    content=request.error_context,
                    token_count=count_tokens(request.error_context),
                    relevance_score=0.95,
                )
            )

        try:
            query_vec = await self.embeddings.embed(request.task_description)

            semantic_results = await self.qdrant.search(
                collection_name="knowledge_base",
                query_vector=query_vec,
                limit=20,
                score_threshold=0.7,
            )
            for result in semantic_results:
                content = result.payload.get("content", "")
                candidates.append(
                    ContextBlock(
                        source="qdrant_semantic",
                        content=content,
                        token_count=count_tokens(content),
                        relevance_score=result.score,
                        metadata={"collection": "knowledge_base", "id": str(result.id)},
                    )
                )

            ap_query = f"{request.task_type} {request.task_description}"
            ap_vec = await self.embeddings.embed(ap_query)
            antipattern_results = await self.qdrant.search(
                collection_name="engineering_antipatterns",
                query_vector=ap_vec,
                limit=5,
                score_threshold=0.75,
            )
            for result in antipattern_results:
                content = result.payload.get("content", "")
                candidates.append(
                    ContextBlock(
                        source="qdrant_antipatterns",
                        content=content,
                        token_count=count_tokens(content),
                        relevance_score=result.score,
                        metadata={"pattern_name": result.payload.get("pattern_name")},
                    )
                )
        except Exception as exc:
            logger.warning("qdrant_gather_failed", error=str(exc))

        rules = await self._fetch_rules(request.task_type, request.tags)
        if rules:
            candidates.append(
                ContextBlock(
                    source="architecture_rules",
                    content=rules,
                    token_count=count_tokens(rules),
                    relevance_score=0.9,
                )
            )

        for tag in request.tags:
            if tag in COMPLIANCE_PROFILES:
                profile = COMPLIANCE_PROFILES[tag]
                candidates.append(
                    ContextBlock(
                        source="compliance_rules",
                        content=profile,
                        token_count=count_tokens(profile),
                        relevance_score=0.95,
                        metadata={"compliance_framework": tag},
                    )
                )
            if tag in DOMAIN_MODULES:
                module = DOMAIN_MODULES[tag]
                candidates.append(
                    ContextBlock(
                        source="domain_module",
                        content=module,
                        token_count=count_tokens(module),
                        relevance_score=0.85,
                        metadata={"domain": tag},
                    )
                )

        for filepath in request.referenced_files:
            content = await self._read_file_from_gitea(filepath)
            if content:
                candidates.append(
                    ContextBlock(
                        source="referenced_files",
                        content=content,
                        token_count=count_tokens(content),
                        relevance_score=0.95,
                        metadata={"filepath": filepath},
                    )
                )

        feedback = await self._get_past_feedback(request.task_description, limit=3)
        for fb in feedback:
            candidates.append(
                ContextBlock(
                    source="past_feedback",
                    content=fb["content"],
                    token_count=count_tokens(fb["content"]),
                    relevance_score=fb.get("relevance", 0.6),
                )
            )

        return candidates

    def _score_candidates(
        self, candidates: list[ContextBlock], request: ContextRequest
    ) -> list[ContextBlock]:
        """Adjust relevance scores based on task context."""
        for block in candidates:
            if request.task_type == "fix" and block.source == "error_context":
                block.relevance_score = min(1.0, block.relevance_score * 1.2)
            if request.task_type == "review" and block.source == "qdrant_antipatterns":
                block.relevance_score = min(1.0, block.relevance_score * 1.15)
            if request.task_type == "generate" and block.source == "qdrant_semantic":
                block.relevance_score = min(1.0, block.relevance_score * 1.1)
        return candidates

    async def _compress_block(self, block: ContextBlock, max_tokens: int) -> ContextBlock | None:
        """Compress a block to fit within budget using LLM summarization."""
        if block.token_count <= max_tokens:
            return block
        if max_tokens < 100:
            return None

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    f"{self.settings.LITELLM_URL}/v1/chat/completions",
                    json={
                        "model": self.settings.COMPRESSION_MODEL,
                        "messages": [
                            {
                                "role": "user",
                                "content": (
                                    f"Compress the following to under {max_tokens} tokens "
                                    f"while preserving all technical details:\n\n{block.content}"
                                ),
                            }
                        ],
                        "max_tokens": max_tokens,
                    },
                )
                resp.raise_for_status()
                compressed_text = resp.json()["choices"][0]["message"]["content"]
                return ContextBlock(
                    source=block.source,
                    content=compressed_text,
                    token_count=count_tokens(compressed_text),
                    relevance_score=block.relevance_score * 0.9,
                    metadata={**block.metadata, "compressed": True},
                )
        except Exception as exc:
            logger.warning("compression_failed", error=str(exc))
            truncated = truncate_to_tokens(block.content, max_tokens)
            return ContextBlock(
                source=block.source,
                content=truncated,
                token_count=count_tokens(truncated),
                relevance_score=block.relevance_score * 0.8,
                metadata={**block.metadata, "truncated": True},
            )

    def _assemble_with_cache_hints(self, blocks: list[ContextBlock]) -> dict[str, Any]:
        """Assemble blocks with stable content first for KV-cache optimization."""
        stable_sources = {"system_prompt", "architecture_rules", "compliance_rules"}
        stable_blocks = [b for b in blocks if b.source in stable_sources]
        variable_blocks = [b for b in blocks if b.source not in stable_sources]

        parts: list[str] = []
        cache_boundary = 0
        for block in stable_blocks:
            parts.append(block.content)
            cache_boundary += block.token_count

        parts.append("\n--- TASK-SPECIFIC CONTEXT ---\n")
        for block in variable_blocks:
            parts.append(f"\n[{block.source.upper()}]\n{block.content}")

        return {
            "text": "\n".join(parts),
            "cache_hints": {"stable_prefix_tokens": cache_boundary, "cacheable": True},
        }

    async def _fetch_rules(self, task_type: str, tags: list[str]) -> str:
        """Fetch architecture rules from Rules Engine (GI-5)."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    "http://omni-rules:9624/api/v1/rules",
                    params={"task_type": task_type, "tags": ",".join(tags)},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    return "\n".join(r.get("content", "") for r in data.get("rules", []))
        except Exception as exc:
            logger.debug("rules_engine_unavailable", error=str(exc))
        return ""

    async def _read_file_from_gitea(self, filepath: str) -> str:
        """Read a file from Gitea."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"http://omni-gitea:3000/api/v1/repos/omni/main/raw/{filepath}",
                )
                if resp.status_code == 200:
                    return resp.text
        except Exception as exc:
            logger.debug("gitea_file_read_failed", filepath=filepath, error=str(exc))
        return ""

    async def _get_past_feedback(self, task_description: str, limit: int = 3) -> list[dict]:
        """Get past feedback from Redis cache."""
        try:
            cached = await self.redis.get(f"context:feedback:{hashlib.md5(task_description.encode()).hexdigest()[:8]}")
            if cached:
                return json.loads(cached)[:limit]
        except Exception:
            pass
        return []

    async def _cache_compilation(self, task_id: str, context_hash: str) -> None:
        """Cache compilation metadata for effectiveness tracking."""
        try:
            await self.redis.setex(
                f"context:compiled:{task_id}",
                3600,
                json.dumps({"context_hash": context_hash}),
            )
        except Exception:
            pass
