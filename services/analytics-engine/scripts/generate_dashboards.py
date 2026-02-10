#!/usr/bin/env python3
"""Programmatically generates Superset dashboard JSON export files."""
import json
import os

DASHBOARD_DIR = os.path.join(os.path.dirname(__file__), "..", "dashboards")
os.makedirs(DASHBOARD_DIR, exist_ok=True)

_chart_id = 0


def next_id():
    global _chart_id
    _chart_id += 1
    return _chart_id


def chart(name, viz_type, datasource, sql_expression, groupby=None, metrics=None, filters=None, **extra):
    return {
        "id": next_id(),
        "slice_name": name,
        "viz_type": viz_type,
        "datasource_type": "table",
        "datasource_name": datasource,
        "params": {
            "metrics": metrics or [{"label": "value", "expressionType": "SQL", "sqlExpression": sql_expression}],
            "groupby": groupby or [],
            "adhoc_filters": filters or [],
            **extra,
        },
    }


def dashboard(title, slug, charts, filters=None):
    positions = {}
    for i, c in enumerate(charts):
        row, col = divmod(i, 3)
        positions[f"CHART-{c['id']}"] = {
            "type": "CHART",
            "id": f"CHART-{c['id']}",
            "meta": {"chartId": c["id"], "sliceName": c["slice_name"], "width": 4, "height": 50},
            "children": [],
            "parents": ["ROOT_ID", "GRID_ID", f"ROW-{row}"],
        }
    return {
        "dashboard_title": title,
        "slug": slug,
        "position_json": positions,
        "metadata": {"native_filter_configuration": filters or []},
        "slices": charts,
    }


def date_filter(name="date_range", column="date"):
    return {"id": name, "filterType": "filter_time", "targets": [{"column": {"name": column}}]}


def select_filter(name, column, dataset):
    return {"id": name, "filterType": "filter_select", "targets": [{"column": {"name": column}, "datasetName": dataset}]}


# --- Financial Overview ---
fin_charts = [
    chart("Revenue Over Time", "line", "financial_data.invoices",
          "SUM(amount)", groupby=["date"], time_grain_sqla="P1D",
          time_compare=["P1W", "P1M"]),
    chart("Revenue by Client", "pie", "financial_data.invoices",
          "SUM(amount)", groupby=["client"], row_limit=10),
    chart("Expenses Breakdown", "dist_bar", "financial_data.transactions",
          "SUM(amount)", groupby=["category"],
          adhoc_filters=[{"clause": "WHERE", "expressionType": "SQL", "sqlExpression": "type = 'expense'"}],
          stacked=True),
    chart("Profit Margin", "line", "financial_data.monthly_summary",
          "(SUM(revenue) - SUM(expenses)) / NULLIF(SUM(revenue), 0)", groupby=["date"]),
    chart("Invoice Status", "pie", "financial_data.invoices",
          "COUNT(*)", groupby=["status"], donut=True),
    chart("AR Aging", "dist_bar", "financial_data.invoices",
          "SUM(amount)",
          groupby=["CASE WHEN days_outstanding <= 0 THEN 'current' "
                   "WHEN days_outstanding <= 30 THEN '1-30' "
                   "WHEN days_outstanding <= 60 THEN '31-60' "
                   "WHEN days_outstanding <= 90 THEN '61-90' "
                   "ELSE '90+' END"],
          adhoc_filters=[{"clause": "WHERE", "expressionType": "SQL", "sqlExpression": "status = 'outstanding'"}]),
    chart("Monthly P&L", "table", "financial_data.monthly_summary",
          "SUM(revenue)",
          groupby=["month"],
          metrics=[
              {"label": "Revenue", "expressionType": "SQL", "sqlExpression": "SUM(revenue)"},
              {"label": "COGS", "expressionType": "SQL", "sqlExpression": "SUM(cogs)"},
              {"label": "Gross Margin", "expressionType": "SQL", "sqlExpression": "SUM(revenue) - SUM(cogs)"},
              {"label": "OpEx", "expressionType": "SQL", "sqlExpression": "SUM(opex)"},
              {"label": "Net Income", "expressionType": "SQL", "sqlExpression": "SUM(revenue) - SUM(cogs) - SUM(opex)"},
          ]),
    chart("Client LTV", "scatter", "financial_data.client_metrics",
          "SUM(total_revenue)", groupby=["months_active"],
          entity="client_name"),
]

fin_dashboard = dashboard(
    "Financial Overview", "financial-overview", fin_charts,
    filters=[date_filter(), select_filter("client", "client", "invoices"), select_filter("project", "project", "invoices")],
)

# --- Pipeline Performance ---
pipe_charts = [
    chart("Tasks Over Time", "dist_bar", "platform_metrics.tasks",
          "COUNT(*)", groupby=["task_type", "date"]),
    chart("Avg Quality Score", "line", "platform_metrics.tasks",
          "AVG(score)", groupby=["date"],
          y_axis_bounds=[0, 10],
          annotation_layers=[{"name": "threshold", "value": 7.0, "style": "dashed"}]),
    chart("Gate Pass Rate", "big_number_total", "platform_metrics.quality_gates",
          "SUM(CASE WHEN passed_first THEN 1 ELSE 0 END)::float / NULLIF(COUNT(*), 0) * 100"),
    chart("Agent Comparison", "dist_bar", "platform_metrics.tasks",
          "COUNT(*)",
          groupby=["agent_name"],
          metrics=[
              {"label": "Count", "expressionType": "SQL", "sqlExpression": "COUNT(*)"},
              {"label": "Avg Score", "expressionType": "SQL", "sqlExpression": "AVG(score)"},
              {"label": "Avg Duration (min)", "expressionType": "SQL", "sqlExpression": "AVG(duration_minutes)"},
          ],
          adhoc_filters=[{"clause": "WHERE", "expressionType": "SQL",
                          "sqlExpression": "agent_name IN ('OpenHands', 'SWE-Agent')"}]),
    chart("LLM Cost by Task Type", "box_plot", "platform_metrics.llm_usage",
          "cost", groupby=["task_type"]),
    chart("Stage Duration", "dist_bar", "platform_metrics.task_stages",
          "SUM(duration_minutes)", groupby=["stage_name"], stacked=True),
    chart("Score Distribution", "histogram", "platform_metrics.tasks",
          "score", groupby=[], bins=20),
    chart("Revision Count", "dist_bar", "platform_metrics.tasks",
          "AVG(revision_count)", groupby=["task_type"]),
]

pipe_dashboard = dashboard("Pipeline Performance", "pipeline-performance", pipe_charts)

# --- System Health ---
health_charts = [
    chart("Uptime Heatmap", "heatmap", "platform_metrics.uptime",
          "AVG(uptime_pct)", groupby=["service_name", "date"],
          linear_color_scheme="greenred_reversed"),
    chart("SLA Compliance", "gauge_chart", "platform_metrics.sla_metrics",
          "AVG(uptime_pct)", groupby=["tier"],
          ranges={"CRITICAL": [99.9, 100], "HIGH": [99.5, 99.9], "STANDARD": [99.0, 99.5]}),
    chart("Incidents Timeline", "gantt", "platform_metrics.incidents",
          "duration_minutes", groupby=["service_name"],
          x_start="started_at", x_end="resolved_at"),
    chart("Backup Status", "table", "platform_metrics.backup_status",
          "COUNT(*)",
          groupby=["service_name"],
          metrics=[
              {"label": "Service", "expressionType": "SQL", "sqlExpression": "service_name"},
              {"label": "Last Backup", "expressionType": "SQL", "sqlExpression": "MAX(last_backup_at)"},
              {"label": "Last Verify", "expressionType": "SQL", "sqlExpression": "MAX(last_verify_at)"},
              {"label": "Status", "expressionType": "SQL", "sqlExpression": "MAX(status)"},
          ]),
    chart("Resource Usage", "line_multi", "platform_metrics.resource_usage",
          "AVG(value)", groupby=["timestamp"],
          metrics=[
              {"label": "CPU %", "expressionType": "SQL", "sqlExpression": "AVG(cpu_pct)"},
              {"label": "RAM %", "expressionType": "SQL", "sqlExpression": "AVG(ram_pct)"},
              {"label": "Disk %", "expressionType": "SQL", "sqlExpression": "AVG(disk_pct)"},
          ]),
    chart("Top Resource Consumers", "dist_bar", "platform_metrics.resource_usage",
          "AVG(cpu_pct + ram_pct)", groupby=["service_name"],
          row_limit=10, orientation="horizontal"),
]

health_dashboard = dashboard("System Health", "system-health", health_charts)

# --- Write files ---
for name, data in [
    ("financial-overview.json", fin_dashboard),
    ("pipeline-performance.json", pipe_dashboard),
    ("system-health.json", health_dashboard),
]:
    path = os.path.join(DASHBOARD_DIR, name)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    print(f"Generated {path}")

print("Dashboard generation complete.")
