"""Generate a Grafana dashboard JSON for omni-audit-logger."""
import json
from pathlib import Path

dashboard = {
    "title": "Omni Audit Logger",
    "schemaVersion": 39,
    "version": 1,
    "refresh": "30s",
    "panels": [
        {"type": "timeseries", "title": "Events Over Time", "targets": [{"expr": "sum by (event_type) (rate(audit_events_total[5m]))"}]},
        {"type": "barchart", "title": "Top Actors", "targets": [{"expr": "topk(10, sum by (actor_id) (increase(audit_events_total[24h])))"}]},
        {"type": "piechart", "title": "Action Breakdown", "targets": [{"expr": "sum by (action) (increase(audit_events_total[24h]))"}]},
        {"type": "table", "title": "Error Events", "targets": [{"expr": "sum by (event_type, action) (rate(audit_events_total{success='false'}[1h]))"}]},
        {"type": "timeseries", "title": "Resource Timeline", "targets": [{"expr": "sum by (resource_type) (rate(audit_events_total[5m]))"}]},
    ],
}

Path("dashboard.audit-logger.json").write_text(json.dumps({"dashboard": dashboard, "overwrite": True}, indent=2))
print("Generated dashboard.audit-logger.json")
