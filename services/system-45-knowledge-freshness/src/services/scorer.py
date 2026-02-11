"""AI-powered relevance scoring for knowledge updates.

System 45 - Knowledge Freshness Service.
Uses LiteLLM gateway for classification and scoring.
"""

import json
from typing import Optional

import httpx
import structlog

from src.config import settings
from src.models import KnowledgeUpdate

logger = structlog.get_logger(__name__)

SCORING_SYSTEM_PROMPT = """You are an expert software engineering knowledge classifier.
Analyze the given update and return a JSON object with exactly these fields:

{
  "relevance_score": <float 0.0-1.0>,
  "is_breaking_change": <bool>,
  "is_deprecation": <bool>,
  "affected_languages": [<list of programming language strings>]
}

Scoring guidelines:
- relevance_score 0.9-1.0: Critical security patch, major breaking change, widely-used framework major release
- relevance_score 0.7-0.89: Important feature release, notable deprecation, significant library update
- relevance_score 0.4-0.69: Minor release, documentation update, small improvement
- relevance_score 0.0-0.39: Trivial patch, cosmetic change, very niche tool

is_breaking_change: true if the update describes backward-incompatible API changes, removed features, or requires code modifications to upgrade.

is_deprecation: true if the update announces that a feature, API, or version is deprecated.

affected_languages: list programming languages/ecosystems directly impacted (e.g. ["python", "javascript"]). Use lowercase.

Return ONLY the JSON object. No markdown, no explanation."""


class RelevanceScorer:
    """Scores knowledge updates for relevance using LiteLLM."""

    def __init__(self, http_client: Optional[httpx.AsyncClient] = None) -> None:
        self._client = http_client
        self._litellm_url = settings.LITELLM_URL.rstrip("/")

    async def _get_client(self) -> httpx.AsyncClient:
        """Return the shared client or create a throwaway one."""
        if self._client is not None:
            return self._client
        return httpx.AsyncClient(timeout=60.0)

    async def _call_llm(self, user_prompt: str) -> Optional[dict]:
        """Call LiteLLM chat completion and parse JSON response.

        Args:
            user_prompt: The user message to send to the model.

        Returns:
            Parsed JSON dict or None on failure.
        """
        payload = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": SCORING_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.1,
            "max_tokens": 256,
        }

        try:
            client = await self._get_client()
            response = await client.post(
                f"{self._litellm_url}/v1/chat/completions",
                json=payload,
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"]

            # Strip markdown fences if present
            content = content.strip()
            if content.startswith("```"):
                lines = content.split("\n")
                content = "\n".join(
                    line for line in lines if not line.strip().startswith("```")
                )
            return json.loads(content)

        except httpx.HTTPStatusError as exc:
            logger.error(
                "llm_http_error",
                status_code=exc.response.status_code,
                detail=exc.response.text[:200],
            )
        except httpx.RequestError as exc:
            logger.error("llm_request_error", error=str(exc))
        except (json.JSONDecodeError, KeyError, IndexError) as exc:
            logger.error("llm_response_parse_error", error=str(exc))

        return None

    async def score_update(self, update: KnowledgeUpdate) -> KnowledgeUpdate:
        """Score a single update using LiteLLM.

        Args:
            update: The KnowledgeUpdate to classify and score.

        Returns:
            The same update with relevance_score, is_breaking_change,
            is_deprecation, and affected_languages populated.
        """
        user_prompt = (
            f"Title: {update.title}\n"
            f"Source: {update.source}\n"
            f"Category: {update.category.value}\n"
            f"Summary: {update.summary[:500]}\n"
            f"URL: {update.url}"
        )

        result = await self._call_llm(user_prompt)
        if result is None:
            logger.warning(
                "scoring_fallback_used",
                update_id=update.id,
                title=update.title,
            )
            # Fallback: retain any pre-existing flags from feed parsing
            return update

        try:
            update.relevance_score = float(result.get("relevance_score", 0.0))
            update.relevance_score = max(0.0, min(1.0, update.relevance_score))
        except (TypeError, ValueError):
            update.relevance_score = 0.0

        update.is_breaking_change = bool(
            result.get("is_breaking_change", update.is_breaking_change)
        )
        update.is_deprecation = bool(
            result.get("is_deprecation", update.is_deprecation)
        )

        languages = result.get("affected_languages", [])
        if isinstance(languages, list):
            update.affected_languages = [
                lang.lower().strip() for lang in languages if isinstance(lang, str)
            ]
        else:
            update.affected_languages = []

        logger.info(
            "update_scored",
            update_id=update.id,
            title=update.title,
            relevance_score=update.relevance_score,
            is_breaking=update.is_breaking_change,
            is_deprecation=update.is_deprecation,
            languages=update.affected_languages,
        )

        return update

    async def score_updates(
        self, updates: list[KnowledgeUpdate]
    ) -> list[KnowledgeUpdate]:
        """Score a batch of updates.

        Each update is scored individually to provide granular classification.
        Failures on individual updates are logged but do not abort the batch.

        Args:
            updates: List of KnowledgeUpdate objects to score.

        Returns:
            The same list with scoring fields populated.
        """
        scored: list[KnowledgeUpdate] = []
        for update in updates:
            try:
                scored_update = await self.score_update(update)
                scored.append(scored_update)
            except Exception as exc:
                logger.error(
                    "score_update_unexpected_error",
                    update_id=update.id,
                    error=str(exc),
                )
                scored.append(update)

        logger.info(
            "batch_scoring_complete",
            total=len(updates),
            scored=len(scored),
        )
        return scored
