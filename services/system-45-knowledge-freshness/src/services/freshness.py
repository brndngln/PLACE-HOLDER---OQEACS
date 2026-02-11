"""Core freshness service orchestrating scans, storage, and alerts.

System 45 - Knowledge Freshness Service.
"""

import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import httpx
import structlog
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)

from src.config import settings
from src.models import (
    DeprecationSeverity,
    DeprecationWarning,
    FeedCategory,
    KnowledgeUpdate,
    ScanReport,
    WeeklyReport,
)
from src.services.feed_parser import FeedParser
from src.services.scorer import RelevanceScorer
from src.utils.notifications import (
    notify_breaking_change,
    notify_deprecation,
    notify_security_advisory,
    notify_weekly_report,
    send_mattermost_notification,
)

logger = structlog.get_logger(__name__)

# Embedding dimension for text-embedding-ada-002 via LiteLLM
EMBEDDING_DIM = 1536

# ---------------------------------------------------------------------------
# Feed category definitions
# ---------------------------------------------------------------------------

FEED_CATEGORIES: dict[str, dict[str, Any]] = {
    "github_releases": {
        "category": FeedCategory.GITHUB_RELEASES,
        "repos": [
            ("tiangolo", "fastapi"),
            ("pydantic", "pydantic"),
            ("facebook", "react"),
            ("vercel", "next.js"),
            ("djangoproject", "django"),
            ("pallets", "flask"),
            ("golang", "go"),
            ("rust-lang", "rust"),
            ("microsoft", "TypeScript"),
            ("nodejs", "node"),
            ("python", "cpython"),
            ("docker", "compose"),
            ("kubernetes", "kubernetes"),
            ("hashicorp", "terraform"),
            ("grafana", "grafana"),
            ("prometheus", "prometheus"),
            ("langchain-ai", "langchain"),
            ("huggingface", "transformers"),
            ("astral-sh", "ruff"),
            ("astral-sh", "uv"),
        ],
    },
    "security_advisories": {
        "category": FeedCategory.SECURITY_ADVISORIES,
        "feeds": [
            {
                "name": "GitHub Security Advisories",
                "url": "https://github.com/advisories.atom",
            },
            {
                "name": "NVD CVE Feed",
                "url": "https://nvd.nist.gov/feeds/xml/cve/misc/nvd-rss.xml",
            },
            {
                "name": "CISA Advisories",
                "url": "https://www.cisa.gov/cybersecurity-advisories/all.xml",
            },
        ],
    },
    "framework_changelogs": {
        "category": FeedCategory.FRAMEWORK_CHANGELOGS,
        "feeds": [
            {
                "name": "Python Insider",
                "url": "https://blog.python.org/feeds/posts/default",
            },
            {
                "name": "Node.js Blog",
                "url": "https://nodejs.org/en/feed/blog.xml",
            },
            {
                "name": "Rust Blog",
                "url": "https://blog.rust-lang.org/feed.xml",
            },
            {
                "name": "Go Blog",
                "url": "https://go.dev/blog/feed.atom",
            },
            {
                "name": "TypeScript Blog",
                "url": "https://devblogs.microsoft.com/typescript/feed/",
            },
        ],
    },
    "best_practices": {
        "category": FeedCategory.BEST_PRACTICES,
        "feeds": [
            {
                "name": "Netflix Tech Blog",
                "url": "https://netflixtechblog.com/feed",
            },
            {
                "name": "Cloudflare Blog",
                "url": "https://blog.cloudflare.com/rss/",
            },
            {
                "name": "Stripe Engineering",
                "url": "https://stripe.com/blog/feed.rss",
            },
            {
                "name": "GitHub Engineering",
                "url": "https://github.blog/engineering.atom",
            },
            {
                "name": "Uber Engineering",
                "url": "https://eng.uber.com/feed/",
            },
        ],
    },
}


class FreshnessService:
    """Orchestrates feed scanning, AI scoring, vector storage, and alerts."""

    def __init__(
        self,
        qdrant_client: Optional[AsyncQdrantClient] = None,
        http_client: Optional[httpx.AsyncClient] = None,
        db_pool: Any = None,
        redis_client: Any = None,
    ) -> None:
        self._qdrant = qdrant_client
        self._http = http_client
        self._db_pool = db_pool
        self._redis = redis_client
        self._parser = FeedParser(http_client=http_client)
        self._scorer = RelevanceScorer(http_client=http_client)
        self._collection = settings.QDRANT_COLLECTION

    # ------------------------------------------------------------------
    # Qdrant helpers
    # ------------------------------------------------------------------

    async def _ensure_collection(self) -> None:
        """Create the Qdrant collection if it does not exist."""
        if self._qdrant is None:
            return
        collections = await self._qdrant.get_collections()
        existing = {c.name for c in collections.collections}
        if self._collection not in existing:
            await self._qdrant.create_collection(
                collection_name=self._collection,
                vectors_config=VectorParams(
                    size=EMBEDDING_DIM,
                    distance=Distance.COSINE,
                ),
            )
            logger.info("qdrant_collection_created", collection=self._collection)

    async def _embed_text(self, text: str) -> Optional[list[float]]:
        """Generate an embedding vector via LiteLLM.

        Args:
            text: Text to embed.

        Returns:
            Embedding vector or None on failure.
        """
        url = f"{settings.LITELLM_URL.rstrip('/')}/v1/embeddings"
        payload = {
            "model": "text-embedding-ada-002",
            "input": text[:8000],
        }
        try:
            client = self._http or httpx.AsyncClient(timeout=30.0)
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            return data["data"][0]["embedding"]
        except Exception as exc:
            logger.error("embedding_error", error=str(exc))
            return None

    async def _apply_to_qdrant(self, update: KnowledgeUpdate) -> bool:
        """Store or update a knowledge entry in Qdrant.

        If a very similar entry exists (score >= 0.95), update its payload.
        Otherwise insert a new point.

        Args:
            update: The scored KnowledgeUpdate to persist.

        Returns:
            True if the operation succeeded.
        """
        if self._qdrant is None:
            logger.warning("qdrant_not_configured")
            return False

        await self._ensure_collection()

        embed_text = f"{update.title} {update.summary[:500]}"
        vector = await self._embed_text(embed_text)
        if vector is None:
            return False

        payload = {
            "id": update.id,
            "title": update.title,
            "summary": update.summary[:500],
            "url": update.url,
            "source": update.source,
            "category": update.category.value,
            "published_at": update.published_at.isoformat(),
            "relevance_score": update.relevance_score,
            "is_breaking_change": update.is_breaking_change,
            "is_deprecation": update.is_deprecation,
            "affected_languages": update.affected_languages,
        }

        # Check for existing similar entry
        try:
            search_results = await self._qdrant.search(
                collection_name=self._collection,
                query_vector=vector,
                limit=1,
                score_threshold=settings.SIMILARITY_THRESHOLD,
            )

            if search_results:
                existing_id = search_results[0].id
                await self._qdrant.set_payload(
                    collection_name=self._collection,
                    payload=payload,
                    points=[existing_id],
                )
                logger.info(
                    "qdrant_entry_updated",
                    update_id=update.id,
                    existing_point=existing_id,
                )
            else:
                point_id = str(uuid.uuid4())
                await self._qdrant.upsert(
                    collection_name=self._collection,
                    points=[
                        PointStruct(
                            id=point_id,
                            vector=vector,
                            payload=payload,
                        )
                    ],
                )
                logger.info(
                    "qdrant_entry_inserted",
                    update_id=update.id,
                    point_id=point_id,
                )
            return True

        except Exception as exc:
            logger.error("qdrant_apply_error", update_id=update.id, error=str(exc))
            return False

    # ------------------------------------------------------------------
    # Alerting helpers
    # ------------------------------------------------------------------

    async def _alert_breaking_change(self, update: KnowledgeUpdate) -> None:
        """Send a Mattermost alert for a breaking change.

        Args:
            update: The breaking-change KnowledgeUpdate.
        """
        await notify_breaking_change(
            package=update.source,
            version=update.title,
            summary=update.summary[:300],
            url=update.url,
        )
        logger.info("breaking_change_alerted", update_id=update.id, title=update.title)

    async def _track_deprecation(self, update: KnowledgeUpdate) -> None:
        """Store a deprecation record in PostgreSQL and notify Mattermost.

        Args:
            update: The deprecation KnowledgeUpdate.
        """
        deprecation = DeprecationWarning(
            package=update.source,
            old_version="",
            new_version=update.title,
            deprecation_type="api_change",
            migration_guide=update.url,
            severity=DeprecationSeverity.MEDIUM,
            detected_at=datetime.now(tz=timezone.utc),
        )

        if self._db_pool is not None:
            try:
                async with self._db_pool.acquire() as conn:
                    await conn.execute(
                        """
                        INSERT INTO deprecation_warnings
                            (package, old_version, new_version, deprecation_type,
                             migration_guide, severity, detected_at)
                        VALUES ($1, $2, $3, $4, $5, $6, $7)
                        ON CONFLICT (package, new_version) DO UPDATE
                            SET severity = EXCLUDED.severity,
                                detected_at = EXCLUDED.detected_at
                        """,
                        deprecation.package,
                        deprecation.old_version,
                        deprecation.new_version,
                        deprecation.deprecation_type,
                        deprecation.migration_guide,
                        deprecation.severity.value,
                        deprecation.detected_at,
                    )
                logger.info("deprecation_stored", package=deprecation.package)
            except Exception as exc:
                logger.error("deprecation_store_error", error=str(exc))

        await notify_deprecation(
            package=deprecation.package,
            old_version=deprecation.old_version,
            new_version=deprecation.new_version,
            migration_guide=deprecation.migration_guide,
        )

    # ------------------------------------------------------------------
    # Scanning
    # ------------------------------------------------------------------

    async def scan_all_feeds(self) -> ScanReport:
        """Run a full scan across all feed categories.

        Returns:
            ScanReport with aggregated results.
        """
        start = time.monotonic()
        all_updates: list[KnowledgeUpdate] = []

        # 1. GitHub releases
        gh_config = FEED_CATEGORIES["github_releases"]
        for owner, repo in gh_config["repos"]:
            updates = await self._parser.parse_github_releases(owner, repo)
            all_updates.extend(updates)

        # 2. Security advisories
        sec_config = FEED_CATEGORIES["security_advisories"]
        for feed in sec_config["feeds"]:
            updates = await self._parser.parse_rss(
                url=feed["url"],
                source_name=feed["name"],
                category=FeedCategory.SECURITY_ADVISORIES,
            )
            all_updates.extend(updates)

        # 3. Framework changelogs
        fw_config = FEED_CATEGORIES["framework_changelogs"]
        for feed in fw_config["feeds"]:
            updates = await self._parser.parse_rss(
                url=feed["url"],
                source_name=feed["name"],
                category=FeedCategory.FRAMEWORK_CHANGELOGS,
            )
            all_updates.extend(updates)

        # 4. Best practices
        bp_config = FEED_CATEGORIES["best_practices"]
        for feed in bp_config["feeds"]:
            updates = await self._parser.parse_rss(
                url=feed["url"],
                source_name=feed["name"],
                category=FeedCategory.BEST_PRACTICES,
            )
            all_updates.extend(updates)

        logger.info("all_feeds_parsed", total_updates=len(all_updates))

        # Score all updates
        scored_updates = await self._scorer.score_updates(all_updates)

        # Filter by relevance threshold
        relevant = [
            u for u in scored_updates
            if u.relevance_score >= settings.RELEVANCE_THRESHOLD
        ]

        breaking_changes: list[KnowledgeUpdate] = []
        deprecations: list[KnowledgeUpdate] = []

        # Process relevant updates
        for update in relevant:
            await self._apply_to_qdrant(update)

            if update.is_breaking_change:
                breaking_changes.append(update)
                await self._alert_breaking_change(update)

            if update.is_deprecation:
                deprecations.append(update)
                await self._track_deprecation(update)

        elapsed = time.monotonic() - start

        report = ScanReport(
            total_updates=len(all_updates),
            relevant_updates=len(relevant),
            breaking_changes=breaking_changes,
            deprecations=deprecations,
            scan_duration_seconds=round(elapsed, 2),
            scanned_at=datetime.now(tz=timezone.utc),
        )

        # Cache latest report in Redis
        if self._redis is not None:
            try:
                await self._redis.set(
                    "freshness:last_scan_report",
                    report.model_dump_json(),
                    ex=86400,
                )
            except Exception as exc:
                logger.error("redis_cache_error", error=str(exc))

        await send_mattermost_notification(
            title="Feed Scan Complete",
            message=(
                f"Scanned **{report.total_updates}** updates, "
                f"**{report.relevant_updates}** relevant, "
                f"**{len(breaking_changes)}** breaking, "
                f"**{len(deprecations)}** deprecations. "
                f"Duration: {report.scan_duration_seconds:.1f}s"
            ),
            category="scan_complete",
        )

        logger.info(
            "scan_complete",
            total=report.total_updates,
            relevant=report.relevant_updates,
            breaking=len(breaking_changes),
            deprecations=len(deprecations),
            duration=report.scan_duration_seconds,
        )

        return report

    async def scan_security_advisories(self) -> ScanReport:
        """Run an hourly security-focused scan for CVEs.

        Returns:
            ScanReport containing only security updates.
        """
        start = time.monotonic()
        all_updates: list[KnowledgeUpdate] = []

        sec_config = FEED_CATEGORIES["security_advisories"]
        for feed in sec_config["feeds"]:
            updates = await self._parser.parse_rss(
                url=feed["url"],
                source_name=feed["name"],
                category=FeedCategory.SECURITY_ADVISORIES,
            )
            all_updates.extend(updates)

        scored = await self._scorer.score_updates(all_updates)

        # Lower threshold for security -- we want to catch more
        relevant = [u for u in scored if u.relevance_score >= 0.5]

        breaking: list[KnowledgeUpdate] = []
        for update in relevant:
            await self._apply_to_qdrant(update)
            if update.is_breaking_change or update.relevance_score >= 0.85:
                breaking.append(update)
                await notify_security_advisory(
                    cve_id=update.id[:12],
                    severity="high" if update.relevance_score >= 0.85 else "medium",
                    package=update.source,
                    summary=update.summary[:300],
                    url=update.url,
                )

        elapsed = time.monotonic() - start

        report = ScanReport(
            total_updates=len(all_updates),
            relevant_updates=len(relevant),
            breaking_changes=breaking,
            deprecations=[],
            scan_duration_seconds=round(elapsed, 2),
            scanned_at=datetime.now(tz=timezone.utc),
        )

        logger.info(
            "security_scan_complete",
            total=report.total_updates,
            relevant=report.relevant_updates,
            critical=len(breaking),
            duration=report.scan_duration_seconds,
        )

        return report

    async def generate_weekly_report(self) -> WeeklyReport:
        """Generate a weekly summary of knowledge freshness.

        Returns:
            WeeklyReport with aggregated statistics.
        """
        now = datetime.now(tz=timezone.utc)
        week_start = now - timedelta(days=7)

        total_updates = 0
        breaking_count = 0
        deprecation_count = 0
        top_updates: list[KnowledgeUpdate] = []

        # Pull stats from Qdrant
        if self._qdrant is not None:
            try:
                collection_info = await self._qdrant.get_collection(self._collection)
                total_updates = collection_info.points_count or 0

                # Scroll for breaking changes this week
                breaking_results, _ = await self._qdrant.scroll(
                    collection_name=self._collection,
                    scroll_filter=Filter(
                        must=[
                            FieldCondition(
                                key="is_breaking_change",
                                match=MatchValue(value=True),
                            ),
                        ]
                    ),
                    limit=100,
                )
                breaking_count = len(breaking_results)

                # Scroll for deprecations this week
                deprecation_results, _ = await self._qdrant.scroll(
                    collection_name=self._collection,
                    scroll_filter=Filter(
                        must=[
                            FieldCondition(
                                key="is_deprecation",
                                match=MatchValue(value=True),
                            ),
                        ]
                    ),
                    limit=100,
                )
                deprecation_count = len(deprecation_results)

            except Exception as exc:
                logger.error("weekly_report_qdrant_error", error=str(exc))

        # Pull deprecation count from PostgreSQL
        if self._db_pool is not None:
            try:
                async with self._db_pool.acquire() as conn:
                    row = await conn.fetchrow(
                        "SELECT COUNT(*) AS cnt FROM deprecation_warnings WHERE detected_at >= $1",
                        week_start,
                    )
                    if row:
                        deprecation_count = max(deprecation_count, row["cnt"])
            except Exception as exc:
                logger.error("weekly_report_db_error", error=str(exc))

        # Compute freshness score: higher is better
        # 100 if we scanned recently and have few breaking/deprecation issues
        base_score = 85.0
        if breaking_count > 10:
            base_score -= 20.0
        elif breaking_count > 5:
            base_score -= 10.0
        if deprecation_count > 20:
            base_score -= 15.0
        elif deprecation_count > 10:
            base_score -= 5.0
        freshness_score = max(0.0, min(100.0, base_score))

        report = WeeklyReport(
            week_start=week_start,
            week_end=now,
            total_updates=total_updates,
            breaking_changes_count=breaking_count,
            deprecations_count=deprecation_count,
            top_updates=top_updates,
            freshness_score=freshness_score,
        )

        await notify_weekly_report(
            total_updates=total_updates,
            breaking_count=breaking_count,
            deprecation_count=deprecation_count,
            freshness_score=freshness_score,
        )

        # Cache in Redis
        if self._redis is not None:
            try:
                await self._redis.set(
                    "freshness:weekly_report",
                    report.model_dump_json(),
                    ex=604800,
                )
            except Exception as exc:
                logger.error("redis_weekly_cache_error", error=str(exc))

        logger.info(
            "weekly_report_generated",
            total_updates=total_updates,
            breaking=breaking_count,
            deprecations=deprecation_count,
            freshness_score=freshness_score,
        )

        return report

    async def get_deprecations(self) -> list[DeprecationWarning]:
        """Retrieve all tracked deprecation warnings from PostgreSQL.

        Returns:
            List of DeprecationWarning objects.
        """
        deprecations: list[DeprecationWarning] = []
        if self._db_pool is None:
            return deprecations

        try:
            async with self._db_pool.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT package, old_version, new_version, deprecation_type,
                           migration_guide, severity, detected_at
                    FROM deprecation_warnings
                    ORDER BY detected_at DESC
                    LIMIT 200
                    """
                )
                for row in rows:
                    deprecations.append(
                        DeprecationWarning(
                            package=row["package"],
                            old_version=row["old_version"],
                            new_version=row["new_version"],
                            deprecation_type=row["deprecation_type"],
                            migration_guide=row["migration_guide"],
                            severity=DeprecationSeverity(row["severity"]),
                            detected_at=row["detected_at"],
                        )
                    )
        except Exception as exc:
            logger.error("get_deprecations_error", error=str(exc))

        return deprecations

    async def get_recent_updates(
        self,
        limit: int = 50,
        category: Optional[FeedCategory] = None,
    ) -> list[dict]:
        """Retrieve recent updates from Qdrant.

        Args:
            limit: Maximum number of results.
            category: Optional category filter.

        Returns:
            List of update payloads from Qdrant.
        """
        if self._qdrant is None:
            return []

        try:
            scroll_filter = None
            if category is not None:
                scroll_filter = Filter(
                    must=[
                        FieldCondition(
                            key="category",
                            match=MatchValue(value=category.value),
                        )
                    ]
                )

            results, _ = await self._qdrant.scroll(
                collection_name=self._collection,
                scroll_filter=scroll_filter,
                limit=limit,
            )
            return [point.payload for point in results if point.payload]

        except Exception as exc:
            logger.error("get_recent_updates_error", error=str(exc))
            return []

    async def get_breaking_updates(self, limit: int = 50) -> list[dict]:
        """Retrieve breaking change updates from Qdrant.

        Args:
            limit: Maximum number of results.

        Returns:
            List of breaking change payloads.
        """
        if self._qdrant is None:
            return []

        try:
            results, _ = await self._qdrant.scroll(
                collection_name=self._collection,
                scroll_filter=Filter(
                    must=[
                        FieldCondition(
                            key="is_breaking_change",
                            match=MatchValue(value=True),
                        )
                    ]
                ),
                limit=limit,
            )
            return [point.payload for point in results if point.payload]

        except Exception as exc:
            logger.error("get_breaking_updates_error", error=str(exc))
            return []
