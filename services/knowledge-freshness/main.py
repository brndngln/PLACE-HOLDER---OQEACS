"""Knowledge Freshness Monitor — Watches sources for updates and triggers re-ingestion.

Monitors Git repositories, ArXiv feeds, NVD security advisories, and technical
blog RSS feeds. Computes freshness scores per source and queues re-ingestion
when sources become stale or are updated upstream.
"""

from __future__ import annotations

import asyncio
import os
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

import feedparser
import httpx
import structlog
import yaml
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI, HTTPException
from prometheus_client import Counter, Gauge, generate_latest
from pydantic import BaseModel, Field
from qdrant_client import QdrantClient
from starlette.responses import Response
from tenacity import retry, stop_after_attempt, wait_exponential

logger = structlog.get_logger()

# ─────────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────────

INGESTOR_URL = os.getenv("INGESTOR_URL", "http://omni-knowledge-ingestor:9420")
QDRANT_URL = os.getenv("QDRANT_URL", "http://omni-qdrant:6333")
MATTERMOST_WEBHOOK_URL = os.getenv("MATTERMOST_WEBHOOK_URL", "http://omni-mattermost-webhook:8066")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
NVD_API_KEY = os.getenv("NVD_API_KEY", "")
CONFIG_PATH = os.getenv("CONFIG_PATH", "/app/config/sources-config.yaml")

# ─────────────────────────────────────────────────────────────────────────────
# Prometheus Metrics
# ─────────────────────────────────────────────────────────────────────────────

FRESHNESS_SCORE = Gauge(
    "knowledge_freshness_score", "Freshness score per source", ["source"]
)
STALE_SOURCES = Gauge(
    "knowledge_stale_sources_total", "Total sources with score <50"
)
REINGESTION_QUEUE = Gauge(
    "knowledge_reingestion_queue_depth", "Re-ingestion queue depth"
)
REINGESTION_TOTAL = Counter(
    "knowledge_reingestion_total", "Total re-ingestion attempts", ["source", "status"]
)
NEW_PAPERS = Counter(
    "knowledge_new_papers_found_total", "New papers discovered"
)
NEW_BLOG_POSTS = Counter(
    "knowledge_new_blog_posts_found_total", "New blog posts discovered", ["source"]
)
SECURITY_ADVISORIES = Counter(
    "knowledge_security_advisories_total", "Security advisories found"
)

# ─────────────────────────────────────────────────────────────────────────────
# Pydantic Models
# ─────────────────────────────────────────────────────────────────────────────


class SourceTier(str, Enum):
    TIER_1 = "tier-1"
    TIER_2 = "tier-2"
    TIER_3 = "tier-3"


class SourceFreshness(BaseModel):
    """Freshness data for a single source."""
    source_name: str
    tier: str = "tier-2"
    freshness_score: int
    last_ingested: Optional[str] = None
    last_source_updated: Optional[str] = None
    latest_release: Optional[str] = None
    latest_commit: Optional[str] = None
    needs_reingestion: bool = False
    collection: str = "elite_codebases"
    source_url: str = ""


class ReingestionJob(BaseModel):
    """A queued re-ingestion job."""
    source_name: str
    priority: int  # 1=highest (tier-1)
    reason: str
    queued_at: str
    status: str = "pending"  # pending, running, completed, failed


class FeedStatus(BaseModel):
    """Status of an RSS feed watcher."""
    feed_name: str
    rss_url: str
    last_checked: Optional[str] = None
    new_posts_found: int = 0
    last_error: Optional[str] = None


class SecurityAdvisory(BaseModel):
    """A security advisory affecting our stack."""
    cve_id: str
    description: str
    severity: str
    affected_source: str
    published: str
    url: str


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str


# ─────────────────────────────────────────────────────────────────────────────
# Freshness Engine
# ─────────────────────────────────────────────────────────────────────────────

class FreshnessEngine:
    """Core engine for monitoring knowledge freshness."""

    def __init__(self) -> None:
        self.qdrant: Optional[QdrantClient] = None
        self.http_client: Optional[httpx.AsyncClient] = None
        self.scheduler: Optional[AsyncIOScheduler] = None
        self._sources: Dict[str, Dict[str, Any]] = {}
        self._freshness: Dict[str, SourceFreshness] = {}
        self._reingestion_queue: List[ReingestionJob] = []
        self._feed_status: Dict[str, FeedStatus] = {}
        self._advisories: List[SecurityAdvisory] = []
        self._config: Dict[str, Any] = {}

    async def initialize(self) -> None:
        """Initialize connections and load configuration."""
        self.qdrant = QdrantClient(url=QDRANT_URL, timeout=30)
        headers = {}
        if GITHUB_TOKEN:
            headers["Authorization"] = f"token {GITHUB_TOKEN}"
        self.http_client = httpx.AsyncClient(timeout=30.0, headers=headers)
        self._load_config()
        self._init_freshness()
        self._start_scheduler()
        logger.info("freshness_engine_initialized", sources=len(self._sources))

    def _load_config(self) -> None:
        """Load sources configuration."""
        ingestor_config = os.path.join(
            os.path.dirname(__file__), "..", "knowledge-ingestor", "config", "sources-config.yaml"
        )
        config_path = CONFIG_PATH if os.path.exists(CONFIG_PATH) else ingestor_config

        if os.path.exists(config_path):
            with open(config_path) as f:
                self._config = yaml.safe_load(f) or {}
        else:
            logger.warning("config_not_found", path=config_path)
            self._config = {}

        for repo in self._config.get("repositories", []):
            name = repo["source_name"]
            tier = "tier-1" if any("tier-1" in t for t in repo.get("tags", [])) else \
                   "tier-2" if any("tier-2" in t for t in repo.get("tags", [])) else "tier-3"
            self._sources[name] = {
                "type": "repository",
                "tier": tier,
                "source_url": repo.get("source_url", ""),
                "branch": repo.get("branch", "main"),
                "collection": repo.get("collection", "elite_codebases"),
                "languages": repo.get("languages", []),
                "tags": repo.get("tags", []),
            }

        for blog in self._config.get("blogs", []):
            name = blog["source_name"]
            self._feed_status[name] = FeedStatus(
                feed_name=name,
                rss_url=blog["rss_url"],
            )

    def _init_freshness(self) -> None:
        """Initialize freshness scores from Qdrant metadata."""
        for name, info in self._sources.items():
            last_ingested = self._get_last_ingested(name, info.get("collection", "elite_codebases"))
            score = self._compute_score(last_ingested, None)
            self._freshness[name] = SourceFreshness(
                source_name=name,
                tier=info.get("tier", "tier-2"),
                freshness_score=score,
                last_ingested=last_ingested,
                collection=info.get("collection", "elite_codebases"),
                source_url=info.get("source_url", ""),
            )
            FRESHNESS_SCORE.labels(source=name).set(score)

    def _get_last_ingested(self, source_name: str, collection: str) -> Optional[str]:
        """Query Qdrant for the most recent ingestion timestamp for a source."""
        try:
            results = self.qdrant.scroll(
                collection_name=collection,
                scroll_filter={
                    "must": [{"key": "source_name", "match": {"value": source_name}}]
                },
                limit=1,
                with_payload=True,
                order_by="ingested_at",
            )
            points = results[0]
            if points:
                return points[0].payload.get("ingested_at")
        except Exception:
            pass
        return None

    @staticmethod
    def _compute_score(
        last_ingested: Optional[str],
        last_source_updated: Optional[str],
    ) -> int:
        """Compute freshness score (0-100).

        Score logic:
        - If source updated after our last ingestion: 0 (needs re-ingestion)
        - If ingested <7 days ago: 100
        - If ingested <30 days ago: 80
        - If ingested <90 days ago: 50
        - Otherwise: 20
        """
        if not last_ingested:
            return 0

        try:
            ingested_dt = datetime.fromisoformat(last_ingested.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            return 0

        now = datetime.now(timezone.utc)

        if last_source_updated:
            try:
                updated_dt = datetime.fromisoformat(last_source_updated.replace("Z", "+00:00"))
                if updated_dt > ingested_dt:
                    return 0
            except (ValueError, AttributeError):
                pass

        days_since = (now - ingested_dt).days

        if days_since < 7:
            return 100
        elif days_since < 30:
            return 80
        elif days_since < 90:
            return 50
        else:
            return 20

    def _start_scheduler(self) -> None:
        """Start APScheduler with all watchers."""
        self.scheduler = AsyncIOScheduler()

        self.scheduler.add_job(
            self._check_github_releases,
            "interval", hours=6,
            id="github_releases",
            name="GitHub Release Watcher",
        )

        self.scheduler.add_job(
            self._check_arxiv_feeds,
            "interval", hours=24,
            id="arxiv_feeds",
            name="ArXiv Feed Watcher",
        )

        self.scheduler.add_job(
            self._check_nvd_security,
            "interval", hours=12,
            id="nvd_security",
            name="NVD Security Watcher",
        )

        self.scheduler.add_job(
            self._check_blog_rss,
            "interval", hours=12,
            id="blog_rss",
            name="Blog RSS Watcher",
        )

        self.scheduler.add_job(
            self._staleness_alert,
            "cron", hour=8, minute=0,
            id="staleness_alert",
            name="Daily Staleness Alert",
        )

        self.scheduler.add_job(
            self._process_reingestion_queue,
            "interval", minutes=5,
            id="reingestion_processor",
            name="Re-ingestion Queue Processor",
        )

        self.scheduler.start()
        logger.info("scheduler_started", jobs=len(self.scheduler.get_jobs()))

    async def shutdown(self) -> None:
        """Clean up resources."""
        if self.scheduler:
            self.scheduler.shutdown(wait=False)
        if self.http_client:
            await self.http_client.aclose()

    # ── GitHub Release Watcher ────────────────────────────────────────────

    async def _check_github_releases(self) -> None:
        """Check for new GitHub releases and commits for each repository source."""
        logger.info("github_release_check_started")

        for name, info in self._sources.items():
            if info["type"] != "repository":
                continue

            source_url = info.get("source_url", "")
            if "github.com" not in source_url:
                continue

            # Extract owner/repo from URL
            parts = source_url.rstrip(".git").rstrip("/").split("/")
            if len(parts) < 2:
                continue
            owner, repo = parts[-2], parts[-1]

            try:
                # Check latest release
                resp = await self.http_client.get(
                    f"https://api.github.com/repos/{owner}/{repo}/releases/latest"
                )
                latest_release = None
                if resp.status_code == 200:
                    release_data = resp.json()
                    latest_release = release_data.get("tag_name")
                    published_at = release_data.get("published_at")

                    if name in self._freshness:
                        old_release = self._freshness[name].latest_release
                        if old_release and latest_release != old_release:
                            logger.info("new_release_detected", source=name, release=latest_release)
                            self._freshness[name].freshness_score = 0
                            self._freshness[name].last_source_updated = published_at
                            self._freshness[name].needs_reingestion = True
                            FRESHNESS_SCORE.labels(source=name).set(0)
                            self._queue_reingestion(name, f"New release: {latest_release}")
                        self._freshness[name].latest_release = latest_release

                # Check latest commit
                branch = info.get("branch", "main")
                resp = await self.http_client.get(
                    f"https://api.github.com/repos/{owner}/{repo}/commits/{branch}",
                    headers={"Accept": "application/vnd.github.v3+json"},
                )
                if resp.status_code == 200:
                    commit_data = resp.json()
                    commit_sha = commit_data.get("sha", "")[:12]
                    commit_date = commit_data.get("commit", {}).get("committer", {}).get("date")

                    if name in self._freshness:
                        self._freshness[name].latest_commit = commit_sha
                        if commit_date:
                            self._freshness[name].last_source_updated = commit_date
                            score = self._compute_score(
                                self._freshness[name].last_ingested,
                                commit_date,
                            )
                            self._freshness[name].freshness_score = score
                            FRESHNESS_SCORE.labels(source=name).set(score)

            except Exception as e:
                logger.error("github_check_failed", source=name, error=str(e))

            await asyncio.sleep(1)  # rate limiting

    # ── ArXiv Feed Watcher ────────────────────────────────────────────────

    async def _check_arxiv_feeds(self) -> None:
        """Query ArXiv for new papers in relevant categories."""
        logger.info("arxiv_feed_check_started")

        categories = self._config.get("arxiv_categories", [
            "cs.SE", "cs.AI", "cs.DC", "cs.DB", "cs.CR", "cs.PL"
        ])
        domain_keywords = self._config.get("domain_keywords", {})
        all_keywords = set()
        for kws in domain_keywords.values():
            all_keywords.update(kw.lower() for kw in kws)

        papers_found = 0

        for category in categories:
            try:
                search_query = f"cat:{category}"
                url = f"http://export.arxiv.org/api/query?search_query={search_query}&sortBy=submittedDate&sortOrder=descending&max_results=20"
                resp = await self.http_client.get(url)
                if resp.status_code != 200:
                    continue

                feed = feedparser.parse(resp.text)

                for entry in feed.entries[:10]:
                    title = entry.get("title", "").lower()
                    summary = entry.get("summary", "").lower()
                    combined = f"{title} {summary}"

                    # Filter by domain keywords
                    if all_keywords and not any(kw in combined for kw in all_keywords):
                        continue

                    papers_found += 1
                    NEW_PAPERS.inc()

                    # Queue paper ingestion
                    pdf_link = ""
                    for link in entry.get("links", []):
                        if link.get("type") == "application/pdf":
                            pdf_link = link.get("href", "")
                            break

                    if pdf_link:
                        authors = [a.get("name", "") for a in entry.get("authors", [])]
                        try:
                            await self.http_client.post(
                                f"{INGESTOR_URL}/ingest/paper",
                                json={
                                    "pdf_url": pdf_link,
                                    "title": entry.get("title", ""),
                                    "authors": authors[:10],
                                    "year": datetime.now().year,
                                    "venue": f"arXiv:{category}",
                                    "domain": category,
                                    "tags": [category, "arxiv", "auto-discovered"],
                                },
                                timeout=120.0,
                            )
                        except Exception as e:
                            logger.warning("paper_ingestion_trigger_failed", error=str(e))

            except Exception as e:
                logger.error("arxiv_check_failed", category=category, error=str(e))

            await asyncio.sleep(3)  # rate limiting

        logger.info("arxiv_feed_check_complete", papers_found=papers_found)

    # ── NVD Security Watcher ──────────────────────────────────────────────

    async def _check_nvd_security(self) -> None:
        """Check NVD for CVEs affecting our stack dependencies."""
        logger.info("nvd_security_check_started")

        keywords = [
            "linux kernel", "postgresql", "redis", "kubernetes",
            "python", "golang", "rust", "node.js", "docker",
            "nginx", "openssl", "git",
        ]

        now = datetime.now(timezone.utc)
        pub_start = (now - timedelta(days=7)).strftime("%Y-%m-%dT00:00:00.000")
        pub_end = now.strftime("%Y-%m-%dT23:59:59.999")

        headers = {}
        if NVD_API_KEY:
            headers["apiKey"] = NVD_API_KEY

        for keyword in keywords:
            try:
                resp = await self.http_client.get(
                    "https://services.nvd.nist.gov/rest/json/cves/2.0",
                    params={
                        "keywordSearch": keyword,
                        "pubStartDate": pub_start,
                        "pubEndDate": pub_end,
                        "resultsPerPage": 5,
                    },
                    headers=headers,
                    timeout=30.0,
                )
                if resp.status_code != 200:
                    continue

                data = resp.json()
                vulnerabilities = data.get("vulnerabilities", [])

                for vuln in vulnerabilities:
                    cve = vuln.get("cve", {})
                    cve_id = cve.get("id", "")
                    descriptions = cve.get("descriptions", [])
                    description = next(
                        (d["value"] for d in descriptions if d.get("lang") == "en"),
                        "No description",
                    )

                    metrics = cve.get("metrics", {})
                    severity = "UNKNOWN"
                    cvss_data = metrics.get("cvssMetricV31", [])
                    if cvss_data:
                        severity = cvss_data[0].get("cvssData", {}).get("baseSeverity", "UNKNOWN")

                    published = cve.get("published", "")

                    advisory = SecurityAdvisory(
                        cve_id=cve_id,
                        description=description[:500],
                        severity=severity,
                        affected_source=keyword,
                        published=published,
                        url=f"https://nvd.nist.gov/vuln/detail/{cve_id}",
                    )

                    if not any(a.cve_id == cve_id for a in self._advisories):
                        self._advisories.append(advisory)
                        SECURITY_ADVISORIES.inc()

                        # Alert on HIGH/CRITICAL
                        if severity in ("HIGH", "CRITICAL"):
                            await self._send_alert(
                                channel="security",
                                message=f"**Security Advisory** {cve_id} ({severity})\n"
                                        f"Affects: {keyword}\n{description[:200]}",
                            )

                            # Queue re-ingestion for affected codebases
                            for name, info in self._sources.items():
                                if keyword.lower() in name.lower() or keyword.lower() in " ".join(info.get("tags", [])):
                                    self._queue_reingestion(name, f"Security advisory: {cve_id}")

            except Exception as e:
                logger.error("nvd_check_failed", keyword=keyword, error=str(e))

            await asyncio.sleep(6)  # NVD rate limit

        # Keep only last 100 advisories
        self._advisories = self._advisories[-100:]
        logger.info("nvd_security_check_complete", advisories=len(self._advisories))

    # ── Blog RSS Watcher ──────────────────────────────────────────────────

    async def _check_blog_rss(self) -> None:
        """Parse RSS feeds for new technical blog posts."""
        logger.info("blog_rss_check_started")

        for name, status in self._feed_status.items():
            try:
                resp = await self.http_client.get(status.rss_url, timeout=15.0)
                if resp.status_code != 200:
                    status.last_error = f"HTTP {resp.status_code}"
                    continue

                feed = feedparser.parse(resp.text)
                status.last_checked = datetime.now(timezone.utc).isoformat()
                new_count = 0

                blog_config = next(
                    (b for b in self._config.get("blogs", []) if b["source_name"] == name),
                    {},
                )
                domain = blog_config.get("domain", "engineering")
                tags = blog_config.get("tags", [])

                for entry in feed.entries[:5]:
                    published = entry.get("published_parsed")
                    if published:
                        pub_dt = datetime(*published[:6], tzinfo=timezone.utc)
                        if (datetime.now(timezone.utc) - pub_dt).days > 7:
                            continue

                    link = entry.get("link", "")
                    if not link:
                        continue

                    new_count += 1
                    NEW_BLOG_POSTS.labels(source=name).inc()

                    try:
                        await self.http_client.post(
                            f"{INGESTOR_URL}/ingest/blog",
                            json={
                                "url": link,
                                "source": name,
                                "domain": domain,
                                "tags": tags + ["auto-discovered", "rss"],
                            },
                            timeout=60.0,
                        )
                    except Exception as e:
                        logger.warning("blog_ingestion_trigger_failed", source=name, error=str(e))

                status.new_posts_found += new_count
                status.last_error = None

            except Exception as e:
                status.last_error = str(e)
                logger.error("rss_check_failed", feed=name, error=str(e))

    # ── Staleness Alert ───────────────────────────────────────────────────

    async def _staleness_alert(self) -> None:
        """Daily 8 AM check: alert on stale sources."""
        logger.info("staleness_check_started")

        stale_sources: List[str] = []
        urgent_sources: List[str] = []

        for name, freshness in self._freshness.items():
            if freshness.freshness_score < 30:
                stale_sources.append(f"- {name}: score={freshness.freshness_score}")
            if freshness.freshness_score < 50 and freshness.tier == "tier-1":
                urgent_sources.append(f"- **{name}**: score={freshness.freshness_score}")

        STALE_SOURCES.set(len(stale_sources))

        if stale_sources:
            message = f"**Knowledge Freshness Report**\n\n{len(stale_sources)} stale sources (score <30):\n"
            message += "\n".join(stale_sources[:20])
            await self._send_alert(channel="knowledge", message=message)

        if urgent_sources:
            message = f"**URGENT: Tier-1 Sources Stale**\n\n"
            message += "\n".join(urgent_sources)
            await self._send_alert(channel="knowledge", message=message)

    # ── Re-ingestion Queue ────────────────────────────────────────────────

    def _queue_reingestion(self, source_name: str, reason: str) -> None:
        """Add a source to the re-ingestion queue."""
        if any(j.source_name == source_name and j.status == "pending" for j in self._reingestion_queue):
            return

        info = self._sources.get(source_name, {})
        tier = info.get("tier", "tier-3")
        priority = {"tier-1": 1, "tier-2": 2, "tier-3": 3}.get(tier, 3)

        job = ReingestionJob(
            source_name=source_name,
            priority=priority,
            reason=reason,
            queued_at=datetime.now(timezone.utc).isoformat(),
        )
        self._reingestion_queue.append(job)
        self._reingestion_queue.sort(key=lambda j: j.priority)
        REINGESTION_QUEUE.set(sum(1 for j in self._reingestion_queue if j.status == "pending"))
        logger.info("reingestion_queued", source=source_name, reason=reason, priority=priority)

    async def _process_reingestion_queue(self) -> None:
        """Process pending re-ingestion jobs."""
        pending = [j for j in self._reingestion_queue if j.status == "pending"]
        if not pending:
            return

        job = pending[0]
        job.status = "running"
        source_info = self._sources.get(job.source_name, {})

        logger.info("reingestion_started", source=job.source_name, reason=job.reason)

        max_retries = 3
        for attempt in range(max_retries):
            try:
                resp = await self.http_client.post(
                    f"{INGESTOR_URL}/ingest/repository",
                    json={
                        "source_url": source_info.get("source_url", ""),
                        "source_name": job.source_name,
                        "branch": source_info.get("branch", "main"),
                        "languages": source_info.get("languages", []),
                        "collection": source_info.get("collection", "elite_codebases"),
                        "chunk_strategy": "ast",
                        "tags": source_info.get("tags", []),
                    },
                    timeout=600.0,
                )
                if resp.status_code == 200:
                    job.status = "completed"
                    REINGESTION_TOTAL.labels(source=job.source_name, status="success").inc()

                    if job.source_name in self._freshness:
                        now_str = datetime.now(timezone.utc).isoformat()
                        self._freshness[job.source_name].last_ingested = now_str
                        self._freshness[job.source_name].freshness_score = 100
                        self._freshness[job.source_name].needs_reingestion = False
                        FRESHNESS_SCORE.labels(source=job.source_name).set(100)

                    logger.info("reingestion_completed", source=job.source_name)
                    break
                else:
                    raise Exception(f"Ingestor returned {resp.status_code}")

            except Exception as e:
                wait_time = (2 ** attempt) * 5
                logger.warning(
                    "reingestion_attempt_failed",
                    source=job.source_name,
                    attempt=attempt + 1,
                    error=str(e),
                    retry_in=wait_time,
                )
                if attempt < max_retries - 1:
                    await asyncio.sleep(wait_time)
                else:
                    job.status = "failed"
                    REINGESTION_TOTAL.labels(source=job.source_name, status="failed").inc()
                    await self._send_alert(
                        channel="knowledge",
                        message=f"**Re-ingestion Failed** {job.source_name}\n"
                                f"Reason: {job.reason}\nError: {e}",
                    )

        REINGESTION_QUEUE.set(sum(1 for j in self._reingestion_queue if j.status == "pending"))

        # Keep only last 200 jobs
        if len(self._reingestion_queue) > 200:
            self._reingestion_queue = self._reingestion_queue[-200:]

    # ── Alerts ────────────────────────────────────────────────────────────

    async def _send_alert(self, channel: str, message: str) -> None:
        """Send an alert to Mattermost via webhook router."""
        try:
            await self.http_client.post(
                f"{MATTERMOST_WEBHOOK_URL}/webhook/{channel}",
                json={"text": message},
                timeout=10.0,
            )
        except Exception as e:
            logger.warning("alert_send_failed", channel=channel, error=str(e))

    # ── Public API Methods ────────────────────────────────────────────────

    def get_all_freshness(self) -> List[SourceFreshness]:
        """Get all sources sorted by staleness (lowest score first)."""
        return sorted(self._freshness.values(), key=lambda f: f.freshness_score)

    def get_source_freshness(self, source_name: str) -> SourceFreshness:
        """Get freshness details for a specific source."""
        if source_name not in self._freshness:
            raise HTTPException(status_code=404, detail=f"Source not found: {source_name}")
        return self._freshness[source_name]

    def get_stale_sources(self) -> List[SourceFreshness]:
        """Get sources with freshness score <50."""
        return [f for f in self._freshness.values() if f.freshness_score < 50]

    async def check_now(self) -> Dict[str, str]:
        """Trigger an immediate full check of all watchers."""
        asyncio.create_task(self._check_github_releases())
        asyncio.create_task(self._check_blog_rss())
        asyncio.create_task(self._check_nvd_security())
        return {"status": "check_triggered", "watchers": "github,blog_rss,nvd_security"}

    async def trigger_reingest(self, source_name: str) -> Dict[str, str]:
        """Manually trigger re-ingestion for a source."""
        if source_name not in self._sources:
            raise HTTPException(status_code=404, detail=f"Source not found: {source_name}")
        self._queue_reingestion(source_name, "manual_trigger")
        return {"status": "queued", "source": source_name}

    def get_feed_status(self) -> List[FeedStatus]:
        """Get RSS feed monitoring status."""
        return list(self._feed_status.values())

    def get_advisories(self) -> List[SecurityAdvisory]:
        """Get security advisories."""
        return self._advisories


# ─────────────────────────────────────────────────────────────────────────────
# FastAPI Application
# ─────────────────────────────────────────────────────────────────────────────

engine = FreshnessEngine()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await engine.initialize()
    logger.info("knowledge_freshness_monitor_started", port=9430)
    yield
    await engine.shutdown()


app = FastAPI(
    title="Knowledge Freshness Monitor",
    description="Monitors knowledge source freshness and triggers re-ingestion",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/health", response_model=HealthResponse)
async def health():
    """Health check."""
    return HealthResponse(status="healthy", service="knowledge-freshness", version="1.0.0")


@app.get("/ready")
async def ready():
    """Readiness check."""
    try:
        engine.qdrant.get_collections()
        return {"status": "ready"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


@app.get("/metrics")
async def metrics():
    """Prometheus metrics."""
    return Response(content=generate_latest(), media_type="text/plain; charset=utf-8")


@app.get("/freshness", response_model=List[SourceFreshness])
async def get_freshness():
    """All sources sorted by staleness."""
    return engine.get_all_freshness()


@app.get("/freshness/stale", response_model=List[SourceFreshness])
async def get_stale():
    """Sources with score <50."""
    return engine.get_stale_sources()


@app.get("/freshness/{source_name}", response_model=SourceFreshness)
async def get_source_freshness(source_name: str):
    """Detailed freshness info for a specific source."""
    return engine.get_source_freshness(source_name)


@app.post("/freshness/check-now")
async def check_now():
    """Trigger immediate full check."""
    return await engine.check_now()


@app.post("/freshness/reingest/{source_name}")
async def reingest(source_name: str):
    """Manually trigger re-ingestion for a source."""
    return await engine.trigger_reingest(source_name)


@app.get("/feeds/status", response_model=List[FeedStatus])
async def feed_status():
    """RSS monitoring status."""
    return engine.get_feed_status()


@app.get("/advisories", response_model=List[SecurityAdvisory])
async def advisories():
    """Security advisories affecting our stack."""
    return engine.get_advisories()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9430)
