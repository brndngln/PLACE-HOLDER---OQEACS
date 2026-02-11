"""Feed management API router.

System 45 - Knowledge Freshness Service.
"""

import uuid
from typing import Optional

import structlog
from fastapi import APIRouter, HTTPException, Query, Request

from src.models import FeedCategory, FeedConfig, FeedConfigCreate
from src.services.freshness import FEED_CATEGORIES

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/feeds", tags=["feeds"])

# In-memory store for custom feeds (augments the built-in FEED_CATEGORIES)
_custom_feeds: dict[str, FeedConfig] = {}


def _builtin_feeds() -> list[FeedConfig]:
    """Convert built-in FEED_CATEGORIES into FeedConfig objects."""
    feeds: list[FeedConfig] = []

    # GitHub releases
    gh = FEED_CATEGORIES["github_releases"]
    for owner, repo in gh["repos"]:
        feeds.append(
            FeedConfig(
                id=f"gh-{owner}-{repo}",
                name=f"{owner}/{repo}",
                url=f"https://github.com/{owner}/{repo}/releases",
                category=FeedCategory.GITHUB_RELEASES,
                enabled=True,
                last_checked=None,
            )
        )

    # Other feed categories
    for cat_key in ("security_advisories", "framework_changelogs", "best_practices"):
        cat_config = FEED_CATEGORIES[cat_key]
        category = cat_config["category"]
        for feed_def in cat_config.get("feeds", []):
            feeds.append(
                FeedConfig(
                    id=f"{cat_key}-{feed_def['name'].lower().replace(' ', '-')}",
                    name=feed_def["name"],
                    url=feed_def["url"],
                    category=category,
                    enabled=True,
                    last_checked=None,
                )
            )

    return feeds


@router.get("", response_model=list[FeedConfig])
async def list_feeds(
    category: Optional[FeedCategory] = Query(default=None, description="Filter by category"),
) -> list[FeedConfig]:
    """List all configured feeds (built-in and custom).

    Args:
        category: Optional category filter.

    Returns:
        List of FeedConfig objects.
    """
    builtin = _builtin_feeds()
    custom = list(_custom_feeds.values())
    all_feeds = builtin + custom

    if category is not None:
        all_feeds = [f for f in all_feeds if f.category == category]

    logger.info("feeds_listed", total=len(all_feeds), category=category)
    return all_feeds


@router.post("", response_model=FeedConfig, status_code=201)
async def create_feed(payload: FeedConfigCreate) -> FeedConfig:
    """Add a custom feed source.

    Args:
        payload: FeedConfigCreate with name, url, category.

    Returns:
        The newly created FeedConfig.
    """
    feed_id = f"custom-{uuid.uuid4().hex[:8]}"
    feed = FeedConfig(
        id=feed_id,
        name=payload.name,
        url=payload.url,
        category=payload.category,
        enabled=payload.enabled,
        last_checked=None,
    )
    _custom_feeds[feed_id] = feed

    logger.info(
        "custom_feed_created",
        feed_id=feed_id,
        name=feed.name,
        category=feed.category.value,
    )
    return feed
