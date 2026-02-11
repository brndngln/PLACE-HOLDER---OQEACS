"""Tests for the FeedParser service.

System 45 - Knowledge Freshness Service.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from src.models import FeedCategory, KnowledgeUpdate
from src.services.feed_parser import FeedParser

# ---------------------------------------------------------------------------
# Sample RSS feed XML
# ---------------------------------------------------------------------------

SAMPLE_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Test Framework Blog</title>
    <link>https://example.com/blog</link>
    <description>Latest updates from Test Framework</description>
    <item>
      <title>Version 3.0 Released</title>
      <link>https://example.com/blog/v3-release</link>
      <description>Major release with breaking changes and new features.</description>
      <pubDate>Mon, 01 Jan 2026 12:00:00 GMT</pubDate>
    </item>
    <item>
      <title>Security Patch 2.9.1</title>
      <link>https://example.com/blog/v2-9-1</link>
      <description>Fixes a critical vulnerability in the auth module.</description>
      <pubDate>Sun, 31 Dec 2025 10:00:00 GMT</pubDate>
    </item>
  </channel>
</rss>
"""

SAMPLE_ATOM = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Atom Feed Example</title>
  <entry>
    <title>Atom Entry One</title>
    <link href="https://example.com/atom/1" />
    <summary>First atom entry summary.</summary>
    <updated>2026-01-02T08:00:00Z</updated>
  </entry>
</feed>
"""

SAMPLE_GITHUB_RELEASES = [
    {
        "name": "v2.0.0",
        "tag_name": "v2.0.0",
        "body": "## Breaking Change\nRemoved legacy API endpoint.",
        "html_url": "https://github.com/org/repo/releases/tag/v2.0.0",
        "published_at": "2026-01-05T14:30:00Z",
    },
    {
        "name": "v1.9.5",
        "tag_name": "v1.9.5",
        "body": "Bug fix for edge case in parser. Deprecated old config format.",
        "html_url": "https://github.com/org/repo/releases/tag/v1.9.5",
        "published_at": "2025-12-20T09:00:00Z",
    },
]


def _mock_response(content: str, status_code: int = 200) -> httpx.Response:
    """Build a mock httpx.Response."""
    return httpx.Response(
        status_code=status_code,
        text=content,
        request=httpx.Request("GET", "https://example.com"),
    )


def _mock_json_response(data: object, status_code: int = 200) -> httpx.Response:
    """Build a mock httpx.Response returning JSON."""
    import json

    return httpx.Response(
        status_code=status_code,
        json=data,
        request=httpx.Request("GET", "https://api.github.com"),
    )


class TestParseRSS:
    """Tests for FeedParser.parse_rss."""

    @pytest.mark.asyncio
    async def test_parse_rss_returns_updates(self) -> None:
        """parse_rss should return KnowledgeUpdate objects from valid RSS."""
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get.return_value = _mock_response(SAMPLE_RSS)

        parser = FeedParser(http_client=mock_client)
        updates = await parser.parse_rss(
            url="https://example.com/feed.xml",
            source_name="Test Framework Blog",
            category=FeedCategory.FRAMEWORK_CHANGELOGS,
        )

        assert len(updates) == 2
        assert all(isinstance(u, KnowledgeUpdate) for u in updates)

    @pytest.mark.asyncio
    async def test_parse_rss_titles(self) -> None:
        """parse_rss should extract correct titles from RSS entries."""
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get.return_value = _mock_response(SAMPLE_RSS)

        parser = FeedParser(http_client=mock_client)
        updates = await parser.parse_rss(
            url="https://example.com/feed.xml",
            source_name="Test Framework Blog",
        )

        titles = [u.title for u in updates]
        assert "Version 3.0 Released" in titles
        assert "Security Patch 2.9.1" in titles

    @pytest.mark.asyncio
    async def test_parse_rss_category(self) -> None:
        """parse_rss should assign the specified category."""
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get.return_value = _mock_response(SAMPLE_RSS)

        parser = FeedParser(http_client=mock_client)
        updates = await parser.parse_rss(
            url="https://example.com/feed.xml",
            category=FeedCategory.SECURITY_ADVISORIES,
        )

        for u in updates:
            assert u.category == FeedCategory.SECURITY_ADVISORIES

    @pytest.mark.asyncio
    async def test_parse_rss_http_error(self) -> None:
        """parse_rss should return empty list on HTTP error."""
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get.return_value = _mock_response("Not Found", status_code=404)
        mock_client.get.return_value.raise_for_status = MagicMock(
            side_effect=httpx.HTTPStatusError(
                "Not Found",
                request=httpx.Request("GET", "https://example.com"),
                response=_mock_response("Not Found", 404),
            )
        )

        parser = FeedParser(http_client=mock_client)
        updates = await parser.parse_rss(url="https://example.com/bad-feed")

        assert updates == []

    @pytest.mark.asyncio
    async def test_parse_rss_ids_are_unique(self) -> None:
        """Each update from the same feed should have a unique id."""
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get.return_value = _mock_response(SAMPLE_RSS)

        parser = FeedParser(http_client=mock_client)
        updates = await parser.parse_rss(url="https://example.com/feed.xml")

        ids = [u.id for u in updates]
        assert len(ids) == len(set(ids))


class TestParseAtom:
    """Tests for FeedParser.parse_atom."""

    @pytest.mark.asyncio
    async def test_parse_atom_returns_updates(self) -> None:
        """parse_atom should handle Atom feeds via feedparser."""
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get.return_value = _mock_response(SAMPLE_ATOM)

        parser = FeedParser(http_client=mock_client)
        updates = await parser.parse_atom(
            url="https://example.com/feed.atom",
            source_name="Atom Feed",
        )

        assert len(updates) == 1
        assert updates[0].title == "Atom Entry One"


class TestParseGitHubReleases:
    """Tests for FeedParser.parse_github_releases."""

    @pytest.mark.asyncio
    async def test_parse_github_releases(self) -> None:
        """parse_github_releases should return releases from GitHub API."""
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get.return_value = _mock_json_response(SAMPLE_GITHUB_RELEASES)

        parser = FeedParser(http_client=mock_client)
        updates = await parser.parse_github_releases(owner="org", repo="repo")

        assert len(updates) == 2
        assert all(u.category == FeedCategory.GITHUB_RELEASES for u in updates)

    @pytest.mark.asyncio
    async def test_github_breaking_change_detection(self) -> None:
        """Releases mentioning 'breaking change' should be flagged."""
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get.return_value = _mock_json_response(SAMPLE_GITHUB_RELEASES)

        parser = FeedParser(http_client=mock_client)
        updates = await parser.parse_github_releases(owner="org", repo="repo")

        breaking = [u for u in updates if u.is_breaking_change]
        assert len(breaking) >= 1
        assert any("v2.0.0" in u.title for u in breaking)

    @pytest.mark.asyncio
    async def test_github_deprecation_detection(self) -> None:
        """Releases mentioning 'deprecated' should be flagged."""
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get.return_value = _mock_json_response(SAMPLE_GITHUB_RELEASES)

        parser = FeedParser(http_client=mock_client)
        updates = await parser.parse_github_releases(owner="org", repo="repo")

        deprecated = [u for u in updates if u.is_deprecation]
        assert len(deprecated) >= 1

    @pytest.mark.asyncio
    async def test_github_source_format(self) -> None:
        """Source should follow the 'github:owner/repo' convention."""
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get.return_value = _mock_json_response(SAMPLE_GITHUB_RELEASES)

        parser = FeedParser(http_client=mock_client)
        updates = await parser.parse_github_releases(owner="org", repo="repo")

        for u in updates:
            assert u.source == "github:org/repo"
