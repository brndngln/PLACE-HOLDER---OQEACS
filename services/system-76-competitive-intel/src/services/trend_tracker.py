from __future__ import annotations

from src.models import TrendReport
from src.services.project_monitor import ProjectMonitor


class TrendTracker:
    def detect_trends(self, domain: str) -> TrendReport:
        projects = [p for p in ProjectMonitor().list_projects() if domain.lower() in p.lower()]
        if not projects:
            projects = ProjectMonitor().list_projects()[:3]
        return TrendReport(topic=domain, current_state="adoption increasing", direction="up", key_projects=projects)
