"""Feed parser for RSS, Atom, and GitHub releases.

System 45 - Knowledge Freshness Service.
"""

import hashlib
from datetime import datetime, timezone
from time import mktime
from typing import Optional

import feedparser
import httpx
import structlog

from src.config import settings
from src.models import FeedCategory, KnowledgeUpdate

logger = structlog.get_logger(__name__)


class FeedParser:
    """Parses RSS, Atom, and GitHub release feeds into KnowledgeUpdate objects."""

    def __init__(self, http_client: Optional[httpx.AsyncClient] = None) -> None:
        self._client = http_client

    async def _get_client(self) -> httpx.AsyncClient:
        """Return the shared client or create a throwaway one."""
        if self._client is not None:
            return self._client
        return httpx.AsyncClient(timeout=30.0)

    @staticmethod
    def _make_id(source: str, title: str, url: str) -> str:
        """Generate a deterministic ID for an update."""
        raw = f"{source}:{title}:{url}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    @staticmethod
    def _parse_published(entry: dict) -> datetime:
        """Extract the published date from a feedparser entry."""
        published_parsed = entry.get("published_parsed") or entry.get("updated_parsed")
        if published_parsed:
            try:
                return datetime.fromtimestamp(mktime(published_parsed), tz=timezone.utc)
            except (ValueError, OverflowError, OSError):
                pass
        return datetime.now(tz=timezone.utc)

    async def parse_rss(
        self,
        url: str,
        source_name: str = "",
        category: FeedCategory = FeedCategory.FRAMEWORK_CHANGELOGS,
    ) -> list[KnowledgeUpdate]:
        """Parse an RSS feed and return a list of KnowledgeUpdate objects.

        Args:
            url: The RSS feed URL.
            source_name: Human-readable source name.
            category: Feed category.

        Returns:
            List of parsed KnowledgeUpdate objects.
        """
        updates: list[KnowledgeUpdate] = []
        try:
            client = await self._get_client()
            response = await client.get(url, follow_redirects=True)
            response.raise_for_status()
            feed = feedparser.parse(response.text)

            feed_title = source_name or feed.feed.get("title", url)

            for entry in feed.entries:
                title = entry.get("title", "Untitled")
                link = entry.get("link", "")
                summary = entry.get("summary", entry.get("description", ""))
                # Strip HTML tags from summary (basic)
                if "<" in summary:
                    import re
                    summary = re.sub(r"<[^>]+>", "", summary)
                summary = summary[:1000]

                update = KnowledgeUpdate(
                    id=self._make_id(feed_title, title, link),
                    title=title,
                    summary=summary,
                    url=link,
                    source=feed_title,
                    category=category,
                    published_at=self._parse_published(entry),
                )
                updates.append(update)

            logger.info(
                "rss_feed_parsed",
                url=url,
                source=feed_title,
                entries=len(updates),
            )

        except httpx.HTTPStatusError as exc:
            logger.error(
                "rss_feed_http_error",
                url=url,
                status_code=exc.response.status_code,
            )
        except httpx.RequestError as exc:
            logger.error("rss_feed_request_error", url=url, error=str(exc))
        except Exception as exc:
            logger.error("rss_feed_parse_error", url=url, error=str(exc))

        return updates

    async def parse_atom(
        self,
        url: str,
        source_name: str = "",
        category: FeedCategory = FeedCategory.FRAMEWORK_CHANGELOGS,
    ) -> list[KnowledgeUpdate]:
        """Parse an Atom feed.  Uses the same logic as RSS since feedparser handles both.

        Args:
            url: The Atom feed URL.
            source_name: Human-readable source name.
            category: Feed category.

        Returns:
            List of parsed KnowledgeUpdate objects.
        """
        return await self.parse_rss(url, source_name=source_name, category=category)

    async def parse_github_releases(
        self,
        owner: str,
        repo: str,
    ) -> list[KnowledgeUpdate]:
        """Parse GitHub releases for a repository.

        Args:
            owner: GitHub repository owner.
            repo: GitHub repository name.

        Returns:
            List of parsed KnowledgeUpdate objects.
        """
        updates: list[KnowledgeUpdate] = []
        api_url = f"https://api.github.com/repos/{owner}/{repo}/releases"
        headers: dict[str, str] = {"Accept": "application/vnd.github+json"}
        if settings.GITHUB_TOKEN:
            headers["Authorization"] = f"Bearer {settings.GITHUB_TOKEN}"

        try:
            client = await self._get_client()
            response = await client.get(
                api_url,
                headers=headers,
                params={"per_page": 10},
                follow_redirects=True,
            )
            response.raise_for_status()
            releases = response.json()

            for release in releases:
                name = release.get("name") or release.get("tag_name", "Unknown")
                tag = release.get("tag_name", "")
                body = release.get("body", "") or ""
                html_url = release.get("html_url", "")
                published_str = release.get("published_at", "")

                if published_str:
                    try:
                        published = datetime.fromisoformat(
                            published_str.replace("Z", "+00:00")
                        )
                    except ValueError:
                        published = datetime.now(tz=timezone.utc)
                else:
                    published = datetime.now(tz=timezone.utc)

                # Detect breaking changes from body keywords
                body_lower = body.lower()
                is_breaking = any(
                    kw in body_lower
                    for kw in ["breaking change", "breaking:", "breaking!", "removed"]
                )
                is_deprecation = any(
                    kw in body_lower
                    for kw in ["deprecated", "deprecation", "deprecating"]
                )

                summary = body[:1000] if body else f"Release {tag} of {owner}/{repo}"

                update = KnowledgeUpdate(
                    id=self._make_id(f"{owner}/{repo}", name, html_url),
                    title=f"{owner}/{repo} {name}",
                    summary=summary,
                    url=html_url,
                    source=f"github:{owner}/{repo}",
                    category=FeedCategory.GITHUB_RELEASES,
                    published_at=published,
                    is_breaking_change=is_breaking,
                    is_deprecation=is_deprecation,
                )
                updates.append(update)

            logger.info(
                "github_releases_parsed",
                repo=f"{owner}/{repo}",
                releases=len(updates),
            )

        except httpx.HTTPStatusError as exc:
            logger.error(
                "github_releases_http_error",
                repo=f"{owner}/{repo}",
                status_code=exc.response.status_code,
            )
        except httpx.RequestError as exc:
            logger.error(
                "github_releases_request_error",
                repo=f"{owner}/{repo}",
                error=str(exc),
            )
        except Exception as exc:
            logger.error(
                "github_releases_parse_error",
                repo=f"{owner}/{repo}",
                error=str(exc),
            )

        return updates
