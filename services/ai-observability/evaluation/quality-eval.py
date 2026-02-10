#!/usr/bin/env python3
"""
SYSTEM 13 — AI OBSERVABILITY: Weekly Code Generation Quality Evaluation
Omni Quantum Elite AI Coding System — Observability Layer

Pulls traces from Langfuse, computes aggregate quality metrics,
compares to previous week, and posts a summary report to Mattermost.
Results are stored in Qdrant for RAG retrieval.

Requirements: httpx, qdrant-client, structlog
"""

import os
import statistics
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

import httpx
import structlog
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

# ---------------------------------------------------------------------------
# Structured Logging
# ---------------------------------------------------------------------------

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(0),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)

log = structlog.get_logger(
    service="quality-eval", system="13", component="ai-observability"
)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

LANGFUSE_URL = os.getenv("LANGFUSE_URL", "http://omni-langfuse:3000")
LANGFUSE_PUBLIC_KEY = os.getenv("LANGFUSE_PUBLIC_KEY", "")
LANGFUSE_SECRET_KEY = os.getenv("LANGFUSE_SECRET_KEY", "")
MATTERMOST_WEBHOOK_URL = os.getenv("MATTERMOST_WEBHOOK_URL", "")
MATTERMOST_CHANNEL = os.getenv("MATTERMOST_CHANNEL", "quality")
QDRANT_URL = os.getenv("QDRANT_URL", "http://omni-qdrant:6333")
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "human_feedback")
EMBEDDING_API_URL = os.getenv(
    "EMBEDDING_API_URL", "http://omni-embedding:8080/embed"
)
EMBEDDING_DIMENSION = int(os.getenv("EMBEDDING_DIMENSION", "384"))
LOOKBACK_DAYS = int(os.getenv("LOOKBACK_DAYS", "7"))

SCORE_DIMENSIONS = [
    "correctness",
    "security",
    "performance",
    "readability",
    "maintainability",
    "error_handling",
    "testing",
    "architecture",
    "standards_compliance",
    "completeness",
]


# ---------------------------------------------------------------------------
# Langfuse Data Fetching
# ---------------------------------------------------------------------------


def fetch_traces(
    from_dt: datetime, to_dt: datetime, tag: str = "code-generation"
) -> list[dict[str, Any]]:
    """Fetch traces from Langfuse for the given time range and tag."""
    traces: list[dict[str, Any]] = []
    page = 1
    page_size = 100

    with httpx.Client(timeout=60) as client:
        while True:
            resp = client.get(
                f"{LANGFUSE_URL}/api/public/traces",
                auth=(LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY),
                params={
                    "tag": tag,
                    "fromTimestamp": from_dt.isoformat(),
                    "toTimestamp": to_dt.isoformat(),
                    "limit": page_size,
                    "page": page,
                    "orderBy": "timestamp",
                },
            )
            if resp.status_code != 200:
                log.warning(
                    "langfuse_traces_fetch_failed",
                    status_code=resp.status_code,
                    body=resp.text,
                )
                break

            data = resp.json()
            batch = data.get("data", [])
            traces.extend(batch)

            if len(batch) < page_size:
                break
            page += 1

    log.info(
        "traces_fetched",
        count=len(traces),
        tag=tag,
        from_date=str(from_dt.date()),
        to_date=str(to_dt.date()),
    )
    return traces


def fetch_scores_for_trace(trace_id: str) -> list[dict[str, Any]]:
    """Fetch all scores for a specific trace."""
    with httpx.Client(timeout=30) as client:
        resp = client.get(
            f"{LANGFUSE_URL}/api/public/scores",
            auth=(LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY),
            params={"traceId": trace_id, "limit": 100},
        )
        if resp.status_code != 200:
            return []
        return resp.json().get("data", [])


def fetch_observations_for_trace(trace_id: str) -> list[dict[str, Any]]:
    """Fetch observations (generations) for a trace to extract model and code."""
    with httpx.Client(timeout=30) as client:
        resp = client.get(
            f"{LANGFUSE_URL}/api/public/observations",
            auth=(LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY),
            params={"traceId": trace_id, "limit": 50},
        )
        if resp.status_code != 200:
            return []
        return resp.json().get("data", [])


# ---------------------------------------------------------------------------
# Metrics Computation
# ---------------------------------------------------------------------------


def compute_percentile(values: list[float], percentile: int) -> float:
    """Compute the given percentile of a sorted list."""
    if not values:
        return 0.0
    sorted_vals = sorted(values)
    k = (len(sorted_vals) - 1) * percentile / 100.0
    f = int(k)
    c = f + 1
    if c >= len(sorted_vals):
        return sorted_vals[f]
    return sorted_vals[f] + (k - f) * (sorted_vals[c] - sorted_vals[f])


def extract_trace_metrics(traces: list[dict[str, Any]]) -> dict[str, Any]:
    """Extract and aggregate quality metrics from traces and their scores.

    Returns breakdowns by: overall, model, task_type, language.
    """
    all_scores: dict[str, list[float]] = {dim: [] for dim in SCORE_DIMENSIONS}
    overall_scores: list[float] = []
    by_model: dict[str, list[float]] = {}
    by_task_type: dict[str, list[float]] = {}
    by_language: dict[str, list[float]] = {}
    trace_details: list[dict[str, Any]] = []
    total_cost = 0.0
    total_tokens = 0

    for trace in traces:
        trace_id = trace.get("id", "")
        tags = trace.get("tags", [])
        metadata = trace.get("metadata", {}) or {}

        scores = fetch_scores_for_trace(trace_id)

        trace_scores: dict[str, float] = {}
        for score in scores:
            name = (
                score.get("name", "")
                .lower()
                .replace(" ", "_")
                .replace("-", "_")
            )
            value = score.get("value")
            if value is not None and name in all_scores:
                all_scores[name].append(float(value))
                trace_scores[name] = float(value)
            elif (
                name in ("overall", "overall_score") and value is not None
            ):
                overall_scores.append(float(value))

        if trace_scores and not any(
            s.get("name", "").lower() in ("overall", "overall_score")
            for s in scores
        ):
            avg = statistics.mean(list(trace_scores.values()))
            overall_scores.append(avg)

        observations = fetch_observations_for_trace(trace_id)
        model = "unknown"
        for obs in observations:
            if obs.get("type", "").lower() == "generation":
                model = obs.get("model", "unknown") or "unknown"
                usage = obs.get("usage", {}) or {}
                cost = obs.get("calculatedTotalCost")
                if cost:
                    total_cost += float(cost)
                total_tokens += (
                    usage.get("total", 0)
                    or usage.get("totalTokens", 0)
                    or 0
                )
                break

        avg_score = (
            statistics.mean(trace_scores.values()) if trace_scores else None
        )

        if avg_score is not None:
            by_model.setdefault(model, []).append(avg_score)

            task_type = metadata.get("task_type", "general")
            for tag in tags:
                if tag.startswith("task:"):
                    task_type = tag.split(":", 1)[1]
            by_task_type.setdefault(task_type, []).append(avg_score)

            language = metadata.get("language", "unknown")
            for tag in tags:
                if tag.startswith("lang:"):
                    language = tag.split(":", 1)[1]
            by_language.setdefault(language, []).append(avg_score)

        trace_details.append(
            {
                "trace_id": trace_id,
                "model": model,
                "scores": trace_scores,
                "overall": avg_score,
                "tags": tags,
            }
        )

    def compute_stats(values: list[float]) -> dict[str, float | int]:
        if not values:
            return {
                "mean": 0.0,
                "median": 0.0,
                "p10": 0.0,
                "p90": 0.0,
                "count": 0,
            }
        return {
            "mean": round(statistics.mean(values), 3),
            "median": round(statistics.median(values), 3),
            "p10": round(compute_percentile(values, 10), 3),
            "p90": round(compute_percentile(values, 90), 3),
            "count": len(values),
        }

    return {
        "total_traces": len(traces),
        "total_cost_usd": round(total_cost, 4),
        "total_tokens": total_tokens,
        "overall": compute_stats(overall_scores),
        "by_dimension": {
            dim: compute_stats(vals) for dim, vals in all_scores.items()
        },
        "by_model": {
            model: compute_stats(vals) for model, vals in by_model.items()
        },
        "by_task_type": {
            tt: compute_stats(vals) for tt, vals in by_task_type.items()
        },
        "by_language": {
            lang: compute_stats(vals) for lang, vals in by_language.items()
        },
        "trace_details": trace_details,
    }


def compare_weeks(
    current: dict[str, Any], previous: dict[str, Any]
) -> dict[str, Any]:
    """Compare current week metrics to previous week, detect improvement or degradation."""
    comparison: dict[str, Any] = {}

    curr_overall = current.get("overall", {})
    prev_overall = previous.get("overall", {})
    curr_mean = curr_overall.get("mean", 0)
    prev_mean = prev_overall.get("mean", 0)

    if prev_mean > 0:
        change_pct = ((curr_mean - prev_mean) / prev_mean) * 100
    else:
        change_pct = 0.0

    if change_pct > 5:
        trend = "IMPROVING"
    elif change_pct < -5:
        trend = "DEGRADING"
    else:
        trend = "STABLE"

    comparison["overall_trend"] = trend
    comparison["overall_change_pct"] = round(change_pct, 2)
    comparison["current_mean"] = curr_mean
    comparison["previous_mean"] = prev_mean
    comparison["current_traces"] = current.get("total_traces", 0)
    comparison["previous_traces"] = previous.get("total_traces", 0)

    dimension_trends: dict[str, dict[str, Any]] = {}
    for dim in SCORE_DIMENSIONS:
        curr_dim = current.get("by_dimension", {}).get(dim, {})
        prev_dim = previous.get("by_dimension", {}).get(dim, {})
        c_mean = curr_dim.get("mean", 0)
        p_mean = prev_dim.get("mean", 0)
        if p_mean > 0:
            d_pct = ((c_mean - p_mean) / p_mean) * 100
        else:
            d_pct = 0.0

        dimension_trends[dim] = {
            "current": c_mean,
            "previous": p_mean,
            "change_pct": round(d_pct, 2),
            "trend": (
                "UP"
                if d_pct > 5
                else ("DOWN" if d_pct < -5 else "STABLE")
            ),
        }

    comparison["dimension_trends"] = dimension_trends
    return comparison


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------


def format_mattermost_report(
    current: dict[str, Any],
    comparison: dict[str, Any],
    period_start: datetime,
    period_end: datetime,
) -> str:
    """Format the quality evaluation report for Mattermost."""
    trend_emoji = {
        "IMPROVING": ":chart_with_upwards_trend:",
        "DEGRADING": ":chart_with_downwards_trend:",
        "STABLE": ":heavy_minus_sign:",
        "UP": ":arrow_up:",
        "DOWN": ":arrow_down:",
    }

    overall_trend = comparison.get("overall_trend", "STABLE")
    change_pct = comparison.get("overall_change_pct", 0)

    lines = [
        "### :bar_chart: Weekly Code Generation Quality Report",
        f"**Period:** {period_start.strftime('%Y-%m-%d')} to {period_end.strftime('%Y-%m-%d')}",
        "",
        f"**Overall Trend:** {trend_emoji.get(overall_trend, '')} {overall_trend} ({change_pct:+.1f}%)",
        f"**Traces Evaluated:** {current.get('total_traces', 0)} "
        f"(prev: {comparison.get('previous_traces', 0)})",
        f"**Total Cost:** ${current.get('total_cost_usd', 0):.2f}",
        f"**Total Tokens:** {current.get('total_tokens', 0):,}",
        "",
        "#### Overall Quality Scores",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Mean | {current['overall'].get('mean', 0):.2f} |",
        f"| Median | {current['overall'].get('median', 0):.2f} |",
        f"| P10 | {current['overall'].get('p10', 0):.2f} |",
        f"| P90 | {current['overall'].get('p90', 0):.2f} |",
        "",
        "#### Quality by Dimension",
        "| Dimension | Score | Change | Trend |",
        "|-----------|-------|--------|-------|",
    ]

    dim_trends = comparison.get("dimension_trends", {})
    for dim in SCORE_DIMENSIONS:
        dt = dim_trends.get(dim, {})
        trend_icon = trend_emoji.get(dt.get("trend", "STABLE"), "")
        lines.append(
            f"| {dim.replace('_', ' ').title()} "
            f"| {dt.get('current', 0):.2f} "
            f"| {dt.get('change_pct', 0):+.1f}% "
            f"| {trend_icon} |"
        )

    by_model = current.get("by_model", {})
    if by_model:
        lines.extend(
            [
                "",
                "#### By Model",
                "| Model | Mean | Count |",
                "|-------|------|-------|",
            ]
        )
        for model, stats in sorted(
            by_model.items(),
            key=lambda x: x[1].get("mean", 0),
            reverse=True,
        ):
            lines.append(
                f"| {model} | {stats['mean']:.2f} | {stats['count']} |"
            )

    by_lang = current.get("by_language", {})
    if by_lang:
        lines.extend(
            [
                "",
                "#### By Language",
                "| Language | Mean | Count |",
                "|----------|------|-------|",
            ]
        )
        for lang, stats in sorted(
            by_lang.items(),
            key=lambda x: x[1].get("mean", 0),
            reverse=True,
        ):
            lines.append(
                f"| {lang} | {stats['mean']:.2f} | {stats['count']} |"
            )

    lines.extend(
        [
            "",
            "---",
            f"*Generated by Omni Quantum Quality Evaluator at {datetime.now(timezone.utc).isoformat()}*",
        ]
    )

    return "\n".join(lines)


def post_to_mattermost(report: str) -> None:
    """Post formatted report to Mattermost webhook."""
    if not MATTERMOST_WEBHOOK_URL:
        log.warning(
            "mattermost_webhook_not_set", action="printing_to_stdout"
        )
        print(report)
        return

    payload = {
        "channel": MATTERMOST_CHANNEL,
        "username": "Omni Quality Bot",
        "icon_emoji": ":bar_chart:",
        "text": report,
    }

    with httpx.Client(timeout=30) as client:
        resp = client.post(MATTERMOST_WEBHOOK_URL, json=payload)
        if resp.status_code == 200:
            log.info(
                "report_posted",
                channel=f"#{MATTERMOST_CHANNEL}",
            )
        else:
            log.warning(
                "mattermost_post_failed",
                status_code=resp.status_code,
                body=resp.text,
            )


# ---------------------------------------------------------------------------
# Qdrant Storage
# ---------------------------------------------------------------------------


def get_embedding(text: str) -> list[float]:
    """Get text embedding from the embedding service."""
    with httpx.Client(timeout=30) as client:
        resp = client.post(
            EMBEDDING_API_URL,
            json={"text": text, "model": "all-MiniLM-L6-v2"},
        )
        if resp.status_code == 200:
            data = resp.json()
            return data.get(
                "embedding",
                data.get("embeddings", [[0.0] * EMBEDDING_DIMENSION])[0],
            )
        log.warning(
            "embedding_api_failed", status_code=resp.status_code
        )
        return [0.0] * EMBEDDING_DIMENSION


def store_in_qdrant(
    metrics: dict[str, Any],
    period_start: datetime,
    period_end: datetime,
) -> None:
    """Store quality evaluation results in Qdrant for RAG retrieval."""
    log.info("storing_in_qdrant", collection=QDRANT_COLLECTION)

    qdrant = QdrantClient(url=QDRANT_URL)

    collections = [c.name for c in qdrant.get_collections().collections]
    if QDRANT_COLLECTION not in collections:
        qdrant.create_collection(
            collection_name=QDRANT_COLLECTION,
            vectors_config=VectorParams(
                size=EMBEDDING_DIMENSION, distance=Distance.COSINE
            ),
        )
        log.info("qdrant_collection_created", collection=QDRANT_COLLECTION)

    summary_text = (
        f"Code generation quality report for {period_start.date()} to {period_end.date()}. "
        f"Overall mean quality score: {metrics['overall'].get('mean', 0):.2f}. "
        f"Total traces: {metrics['total_traces']}. "
        f"Total cost: ${metrics['total_cost_usd']:.2f}. "
    )
    for dim in SCORE_DIMENSIONS:
        dim_stats = metrics.get("by_dimension", {}).get(dim, {})
        if dim_stats.get("count", 0) > 0:
            summary_text += f"{dim}: {dim_stats['mean']:.2f}. "

    embedding = get_embedding(summary_text)

    point = PointStruct(
        id=str(uuid4()),
        vector=embedding,
        payload={
            "type": "quality_evaluation",
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "summary": summary_text,
            "metrics": {
                "total_traces": metrics["total_traces"],
                "total_cost_usd": metrics["total_cost_usd"],
                "total_tokens": metrics["total_tokens"],
                "overall": metrics["overall"],
                "by_dimension": metrics["by_dimension"],
                "by_model": metrics["by_model"],
                "by_task_type": metrics["by_task_type"],
                "by_language": metrics["by_language"],
            },
        },
    )

    qdrant.upsert(collection_name=QDRANT_COLLECTION, points=[point])
    log.info("qdrant_stored", collection=QDRANT_COLLECTION)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    """Run weekly quality evaluation pipeline."""
    log.info(
        "evaluation_starting",
        system="13",
        component="quality-eval",
        lookback_days=LOOKBACK_DAYS,
    )

    now = datetime.now(timezone.utc)

    current_end = now
    current_start = now - timedelta(days=LOOKBACK_DAYS)
    previous_end = current_start
    previous_start = previous_end - timedelta(days=LOOKBACK_DAYS)

    # Step 1: Fetch current week traces
    log.info(
        "fetching_current_period",
        start=str(current_start.date()),
        end=str(current_end.date()),
    )
    current_traces = fetch_traces(current_start, current_end)

    # Step 2: Fetch previous week traces
    log.info(
        "fetching_previous_period",
        start=str(previous_start.date()),
        end=str(previous_end.date()),
    )
    previous_traces = fetch_traces(previous_start, previous_end)

    # Step 3: Compute metrics
    log.info("computing_metrics", period="current")
    current_metrics = extract_trace_metrics(current_traces)

    log.info("computing_metrics", period="previous")
    previous_metrics = extract_trace_metrics(previous_traces)

    # Step 4: Compare weeks
    comparison = compare_weeks(current_metrics, previous_metrics)
    log.info(
        "comparison_complete",
        trend=comparison["overall_trend"],
        change_pct=comparison["overall_change_pct"],
    )

    # Step 5: Format and post report
    log.info("generating_report")
    report = format_mattermost_report(
        current_metrics, comparison, current_start, current_end
    )
    post_to_mattermost(report)

    # Step 6: Store in Qdrant
    try:
        store_in_qdrant(current_metrics, current_start, current_end)
    except Exception as e:
        log.error("qdrant_storage_failed", error=str(e))

    # Step 7: Summary
    log.info(
        "evaluation_complete",
        current_traces=current_metrics["total_traces"],
        current_mean=current_metrics["overall"].get("mean", 0),
        previous_traces=previous_metrics["total_traces"],
        previous_mean=previous_metrics["overall"].get("mean", 0),
        trend=comparison["overall_trend"],
    )


if __name__ == "__main__":
    main()
