"""Mattermost notification helper for System 45 - Knowledge Freshness Service."""

from typing import Optional

import httpx
import structlog

from src.config import settings
from src.models import FeedCategory

logger = structlog.get_logger(__name__)

# Emoji map for notification categories
EMOJI_MAP: dict[str, str] = {
    "breaking_change": ":rotating_light:",
    "deprecation": ":warning:",
    "security": ":shield:",
    "new_release": ":rocket:",
    "best_practice": ":bulb:",
    "weekly_report": ":bar_chart:",
    "scan_complete": ":white_check_mark:",
    "error": ":x:",
}

CATEGORY_EMOJI: dict[FeedCategory, str] = {
    FeedCategory.GITHUB_RELEASES: ":package:",
    FeedCategory.SECURITY_ADVISORIES: ":shield:",
    FeedCategory.FRAMEWORK_CHANGELOGS: ":scroll:",
    FeedCategory.BEST_PRACTICES: ":bulb:",
}


async def send_mattermost_notification(
    title: str,
    message: str,
    category: str = "new_release",
    channel: Optional[str] = None,
    color: str = "#3498db",
) -> bool:
    """Send a formatted notification to Mattermost via incoming webhook.

    Args:
        title: Notification title.
        message: Notification body text (supports Markdown).
        category: Category key for emoji lookup.
        channel: Optional override for the target channel.
        color: Attachment sidebar colour hex.

    Returns:
        True if the notification was sent successfully.
    """
    webhook_url = settings.MATTERMOST_WEBHOOK_URL
    if not webhook_url:
        logger.warning("mattermost_webhook_not_configured")
        return False

    emoji = EMOJI_MAP.get(category, ":bell:")
    formatted_title = f"{emoji} **{title}**"

    payload: dict = {
        "username": "Knowledge Freshness Bot",
        "icon_emoji": ":brain:",
        "attachments": [
            {
                "fallback": f"{title}: {message}",
                "color": color,
                "title": formatted_title,
                "text": message,
                "footer": "System 45 - Knowledge Freshness Service",
            }
        ],
    }

    if channel:
        payload["channel"] = channel

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(webhook_url, json=payload)
            response.raise_for_status()
            logger.info(
                "mattermost_notification_sent",
                title=title,
                category=category,
                status_code=response.status_code,
            )
            return True
    except httpx.HTTPStatusError as exc:
        logger.error(
            "mattermost_notification_http_error",
            title=title,
            status_code=exc.response.status_code,
            detail=exc.response.text[:200],
        )
        return False
    except httpx.RequestError as exc:
        logger.error(
            "mattermost_notification_request_error",
            title=title,
            error=str(exc),
        )
        return False


async def notify_breaking_change(
    package: str,
    version: str,
    summary: str,
    url: str,
) -> bool:
    """Send a high-priority breaking change alert.

    Args:
        package: The affected package name.
        version: The version containing the breaking change.
        summary: Brief description of the breaking change.
        url: Link to full details.

    Returns:
        True if sent successfully.
    """
    message = (
        f"**Package:** `{package}` **Version:** `{version}`\n"
        f"{summary}\n"
        f"[View Details]({url})"
    )
    return await send_mattermost_notification(
        title=f"Breaking Change: {package} {version}",
        message=message,
        category="breaking_change",
        color="#e74c3c",
    )


async def notify_deprecation(
    package: str,
    old_version: str,
    new_version: str,
    migration_guide: str,
) -> bool:
    """Send a deprecation warning notification.

    Args:
        package: The affected package name.
        old_version: Deprecated version string.
        new_version: Recommended version string.
        migration_guide: Link or inline migration guidance.

    Returns:
        True if sent successfully.
    """
    message = (
        f"**Package:** `{package}`\n"
        f"**Deprecated:** `{old_version}` -> **Upgrade to:** `{new_version}`\n"
        f"**Migration:** {migration_guide}"
    )
    return await send_mattermost_notification(
        title=f"Deprecation Warning: {package}",
        message=message,
        category="deprecation",
        color="#f39c12",
    )


async def notify_security_advisory(
    cve_id: str,
    severity: str,
    package: str,
    summary: str,
    url: str,
) -> bool:
    """Send an urgent security advisory notification.

    Args:
        cve_id: The CVE identifier.
        severity: Severity level (critical, high, medium, low).
        package: Affected package name.
        summary: Brief description.
        url: Link to the advisory.

    Returns:
        True if sent successfully.
    """
    severity_colors = {
        "critical": "#e74c3c",
        "high": "#e67e22",
        "medium": "#f1c40f",
        "low": "#3498db",
    }
    color = severity_colors.get(severity.lower(), "#3498db")

    message = (
        f"**CVE:** `{cve_id}` | **Severity:** `{severity.upper()}`\n"
        f"**Package:** `{package}`\n"
        f"{summary}\n"
        f"[Full Advisory]({url})"
    )
    return await send_mattermost_notification(
        title=f"Security Advisory: {cve_id}",
        message=message,
        category="security",
        color=color,
    )


async def notify_weekly_report(
    total_updates: int,
    breaking_count: int,
    deprecation_count: int,
    freshness_score: float,
) -> bool:
    """Send the weekly knowledge freshness summary.

    Args:
        total_updates: Number of updates discovered.
        breaking_count: Number of breaking changes.
        deprecation_count: Number of deprecations.
        freshness_score: Overall freshness score (0-100).

    Returns:
        True if sent successfully.
    """
    score_indicator = (
        ":green_heart:" if freshness_score >= 80
        else ":yellow_heart:" if freshness_score >= 50
        else ":broken_heart:"
    )
    message = (
        f"| Metric | Value |\n"
        f"|---|---|\n"
        f"| Total Updates | {total_updates} |\n"
        f"| Breaking Changes | {breaking_count} |\n"
        f"| Deprecations | {deprecation_count} |\n"
        f"| Freshness Score | {score_indicator} {freshness_score:.1f}/100 |"
    )
    return await send_mattermost_notification(
        title="Weekly Knowledge Freshness Report",
        message=message,
        category="weekly_report",
        color="#2ecc71",
    )
