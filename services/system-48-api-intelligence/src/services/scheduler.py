"""APScheduler-based background task scheduler for periodic scans and alerts."""

from __future__ import annotations

from datetime import datetime

import httpx
import structlog
try:
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.triggers.interval import IntervalTrigger
except ImportError:  # pragma: no cover - exercised in offline test envs
    class IntervalTrigger:  # type: ignore[no-redef]
        def __init__(self, **kwargs: int) -> None:
            self.kwargs = kwargs

    class AsyncIOScheduler:  # type: ignore[no-redef]
        def __init__(self) -> None:
            self._jobs: dict[str, dict[str, object]] = {}

        def add_job(
            self,
            func,
            trigger: IntervalTrigger,
            *,
            id: str,
            name: str,
            replace_existing: bool = True,
            max_instances: int = 1,
        ) -> None:
            if not replace_existing and id in self._jobs:
                return
            self._jobs[id] = {
                "func": func,
                "trigger": trigger,
                "name": name,
                "max_instances": max_instances,
            }

        def start(self) -> None:
            return

        def shutdown(self, wait: bool = False) -> None:
            return

from src.config import settings
from src.services.registry_scanner import RegistryScanner
from src.utils.notifications import MattermostNotifier

logger = structlog.get_logger(__name__)

# In-memory tracked packages (in production, this would be backed by a database)
_tracked_packages: list[dict[str, str]] = []


def register_tracked_packages(packages: list[dict[str, str]]) -> None:
    """Register packages to be tracked by the scheduler.

    Adds packages to the in-memory tracking list that the periodic
    scan jobs will iterate over. Each dict should have keys:
    name, registry, current_version.
    """
    global _tracked_packages
    for pkg in packages:
        existing = next(
            (p for p in _tracked_packages if p["name"] == pkg["name"]),
            None,
        )
        if existing:
            existing.update(pkg)
        else:
            _tracked_packages.append(pkg)
    logger.info("packages_registered", count=len(packages), total=len(_tracked_packages))


def get_tracked_packages() -> list[dict[str, str]]:
    """Return the current list of tracked packages."""
    return list(_tracked_packages)


async def run_full_dependency_scan() -> None:
    """Execute a full dependency scan across all tracked packages.

    Scans every registered package for version updates, breaking changes,
    and deprecations. Sends Mattermost alerts for critical findings.
    """
    logger.info("scheduled_full_scan_start", package_count=len(_tracked_packages))

    if not _tracked_packages:
        logger.info("no_tracked_packages_skipping_scan")
        return

    async with httpx.AsyncClient(timeout=30.0) as client:
        scanner = RegistryScanner(http_client=client)
        notifier = MattermostNotifier(http_client=client)

        try:
            results = await scanner.scan_all(_tracked_packages)

            outdated_count = sum(1 for r in results if r.is_outdated)
            breaking_count = sum(1 for r in results if r.breaking_changes)
            security_count = sum(1 for r in results if r.security_advisories)

            logger.info(
                "scheduled_full_scan_complete",
                total=len(results),
                outdated=outdated_count,
                breaking=breaking_count,
                security=security_count,
            )

            # Alert on critical findings
            if security_count > 0:
                security_packages = [r for r in results if r.security_advisories]
                message_parts = [
                    f"**Security Alert** - {security_count} package(s) with advisories:",
                ]
                for pkg in security_packages:
                    message_parts.append(f"- **{pkg.name}** ({pkg.current_version}): {', '.join(pkg.security_advisories[:3])}")

                await notifier.send_alert(
                    title="Security Advisories Detected",
                    message="\n".join(message_parts),
                    level="critical",
                )

            if breaking_count > 0:
                breaking_packages = [r for r in results if r.breaking_changes]
                message_parts = [
                    f"**Breaking Changes** - {breaking_count} package(s):",
                ]
                for pkg in breaking_packages:
                    message_parts.append(
                        f"- **{pkg.name}** {pkg.current_version} -> {pkg.latest_version}: "
                        f"{len(pkg.breaking_changes)} breaking change(s)"
                    )

                await notifier.send_alert(
                    title="Breaking Changes Detected",
                    message="\n".join(message_parts),
                    level="warning",
                )

        except Exception as exc:
            logger.error("scheduled_full_scan_failed", error=str(exc))
            await notifier.send_alert(
                title="Dependency Scan Failed",
                message=f"Full dependency scan encountered an error: {exc}",
                level="error",
            )


async def run_security_check() -> None:
    """Execute a security-focused scan of all tracked packages.

    Checks OSV.dev for new security advisories on every tracked package
    and sends immediate Mattermost alerts for any findings.
    """
    logger.info("scheduled_security_check_start", package_count=len(_tracked_packages))

    if not _tracked_packages:
        logger.info("no_tracked_packages_skipping_security_check")
        return

    async with httpx.AsyncClient(timeout=30.0) as client:
        scanner = RegistryScanner(http_client=client)
        notifier = MattermostNotifier(http_client=client)

        critical_findings: list[str] = []

        for pkg in _tracked_packages:
            try:
                advisories = await scanner._check_security(
                    pkg["name"], pkg.get("registry", "pypi")
                )
                if advisories:
                    for advisory in advisories:
                        critical_findings.append(f"**{pkg['name']}**: {advisory}")
            except Exception as exc:
                logger.warning(
                    "security_check_failed_for_package",
                    package=pkg["name"],
                    error=str(exc),
                )

        if critical_findings:
            await notifier.send_alert(
                title="Security Check: New Advisories Found",
                message="\n".join(critical_findings[:20]),
                level="critical",
            )
            logger.warning(
                "security_advisories_found", count=len(critical_findings)
            )
        else:
            logger.info("security_check_clean", timestamp=datetime.utcnow().isoformat())


def create_scheduler() -> AsyncIOScheduler:
    """Create and configure the APScheduler instance.

    Sets up two recurring jobs:
    1. Full dependency scan every SCAN_INTERVAL_HOURS (default: 6h)
    2. Security check every SECURITY_CHECK_INTERVAL_HOURS (default: 1h)
    """
    scheduler = AsyncIOScheduler()

    scheduler.add_job(
        run_full_dependency_scan,
        trigger=IntervalTrigger(hours=settings.SCAN_INTERVAL_HOURS),
        id="full_dependency_scan",
        name="Full Dependency Scan",
        replace_existing=True,
        max_instances=1,
    )

    scheduler.add_job(
        run_security_check,
        trigger=IntervalTrigger(hours=settings.SECURITY_CHECK_INTERVAL_HOURS),
        id="security_check",
        name="Security Advisory Check",
        replace_existing=True,
        max_instances=1,
    )

    logger.info(
        "scheduler_configured",
        scan_interval_hours=settings.SCAN_INTERVAL_HOURS,
        security_interval_hours=settings.SECURITY_CHECK_INTERVAL_HOURS,
    )

    return scheduler
