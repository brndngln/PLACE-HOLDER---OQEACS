"""Tests for the FreshnessService and related configuration.

System 45 - Knowledge Freshness Service.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.models import (
    DeprecationSeverity,
    DeprecationWarning,
    FeedCategory,
    KnowledgeUpdate,
    ScanReport,
    WeeklyReport,
)
from src.services.freshness import FEED_CATEGORIES, FreshnessService


class TestFeedCategories:
    """Tests for the FEED_CATEGORIES configuration dict."""

    def test_all_categories_present(self) -> None:
        """FEED_CATEGORIES should contain all four expected keys."""
        expected = {
            "github_releases",
            "security_advisories",
            "framework_changelogs",
            "best_practices",
        }
        assert expected == set(FEED_CATEGORIES.keys())

    def test_github_releases_has_repos(self) -> None:
        """github_releases should have at least 20 repos defined."""
        repos = FEED_CATEGORIES["github_releases"]["repos"]
        assert len(repos) >= 20

    def test_github_repos_are_tuples(self) -> None:
        """Each GitHub repo entry should be an (owner, repo) tuple."""
        repos = FEED_CATEGORIES["github_releases"]["repos"]
        for entry in repos:
            assert len(entry) == 2
            owner, repo = entry
            assert isinstance(owner, str)
            assert isinstance(repo, str)

    def test_security_advisories_has_feeds(self) -> None:
        """security_advisories should have feed definitions."""
        feeds = FEED_CATEGORIES["security_advisories"]["feeds"]
        assert len(feeds) >= 1
        for feed in feeds:
            assert "name" in feed
            assert "url" in feed

    def test_framework_changelogs_has_feeds(self) -> None:
        """framework_changelogs should have feed definitions."""
        feeds = FEED_CATEGORIES["framework_changelogs"]["feeds"]
        assert len(feeds) >= 1

    def test_best_practices_has_feeds(self) -> None:
        """best_practices should include well-known tech blog feeds."""
        feeds = FEED_CATEGORIES["best_practices"]["feeds"]
        names = [f["name"] for f in feeds]
        assert any("Netflix" in n for n in names)
        assert any("Cloudflare" in n for n in names)
        assert any("Stripe" in n for n in names)

    def test_categories_have_enum(self) -> None:
        """Each category should reference a valid FeedCategory enum."""
        for key, config in FEED_CATEGORIES.items():
            assert isinstance(config["category"], FeedCategory)

    def test_github_popular_repos_included(self) -> None:
        """Key popular repos should be present in the github_releases list."""
        repos = FEED_CATEGORIES["github_releases"]["repos"]
        repo_names = {r[1].lower() for r in repos}
        expected_repos = {"fastapi", "pydantic", "react", "next.js", "django"}
        for repo in expected_repos:
            assert repo in repo_names, f"{repo} not found in GitHub releases"


class TestFreshnessServiceInit:
    """Tests for FreshnessService instantiation."""

    def test_init_without_deps(self) -> None:
        """FreshnessService should initialise even when all deps are None."""
        service = FreshnessService()
        assert service is not None

    def test_init_with_deps(self) -> None:
        """FreshnessService should accept injected dependencies."""
        mock_qdrant = MagicMock()
        mock_http = MagicMock()
        mock_db = MagicMock()
        mock_redis = MagicMock()

        service = FreshnessService(
            qdrant_client=mock_qdrant,
            http_client=mock_http,
            db_pool=mock_db,
            redis_client=mock_redis,
        )
        assert service._qdrant is mock_qdrant
        assert service._http is mock_http
        assert service._db_pool is mock_db
        assert service._redis is mock_redis


class TestScoringLogic:
    """Tests for RelevanceScorer behaviour."""

    def test_knowledge_update_defaults(self) -> None:
        """A new KnowledgeUpdate should default to unscored."""
        update = KnowledgeUpdate(
            id="test-1",
            title="Test Update",
            source="test-source",
            category=FeedCategory.GITHUB_RELEASES,
        )
        assert update.relevance_score == 0.0
        assert update.is_breaking_change is False
        assert update.is_deprecation is False
        assert update.affected_languages == []

    def test_knowledge_update_scored_fields(self) -> None:
        """Explicitly scored KnowledgeUpdate should retain values."""
        update = KnowledgeUpdate(
            id="test-2",
            title="Major Breaking Change",
            source="fastapi",
            category=FeedCategory.GITHUB_RELEASES,
            relevance_score=0.95,
            is_breaking_change=True,
            is_deprecation=False,
            affected_languages=["python"],
        )
        assert update.relevance_score == 0.95
        assert update.is_breaking_change is True
        assert update.affected_languages == ["python"]

    def test_relevance_score_bounds(self) -> None:
        """relevance_score should be constrained to 0.0 - 1.0."""
        update = KnowledgeUpdate(
            id="test-3",
            title="Bounded",
            source="test",
            category=FeedCategory.BEST_PRACTICES,
            relevance_score=0.0,
        )
        assert update.relevance_score >= 0.0
        assert update.relevance_score <= 1.0


class TestScanReport:
    """Tests for the ScanReport model."""

    def test_scan_report_defaults(self) -> None:
        """ScanReport should have sane defaults."""
        report = ScanReport()
        assert report.total_updates == 0
        assert report.relevant_updates == 0
        assert report.breaking_changes == []
        assert report.deprecations == []
        assert report.scan_duration_seconds == 0.0
        assert isinstance(report.scanned_at, datetime)


class TestWeeklyReport:
    """Tests for the WeeklyReport model."""

    def test_weekly_report_score_bounds(self) -> None:
        """freshness_score should be 0-100."""
        now = datetime.now(tz=timezone.utc)
        report = WeeklyReport(
            week_start=now,
            week_end=now,
            freshness_score=85.0,
        )
        assert 0.0 <= report.freshness_score <= 100.0


class TestDeprecationWarningModel:
    """Tests for the DeprecationWarning model."""

    def test_deprecation_warning_fields(self) -> None:
        """DeprecationWarning should capture all required fields."""
        warning = DeprecationWarning(
            package="some-lib",
            old_version="1.0.0",
            new_version="2.0.0",
            deprecation_type="removal",
            migration_guide="https://example.com/migrate",
            severity=DeprecationSeverity.HIGH,
        )
        assert warning.package == "some-lib"
        assert warning.severity == DeprecationSeverity.HIGH
        assert isinstance(warning.detected_at, datetime)
