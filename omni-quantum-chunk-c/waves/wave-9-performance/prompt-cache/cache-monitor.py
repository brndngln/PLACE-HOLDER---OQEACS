#!/usr/bin/env python3
# ╔══════════════════════════════════════════════════════════════════════════════════════╗
# ║  PROMPT CACHE MONITOR — Track Cache Hit Rates via Langfuse                         ║
# ║  OMNI QUANTUM ELITE v3.0                                                           ║
# ╚══════════════════════════════════════════════════════════════════════════════════════╝

import argparse
import json
import os
from datetime import datetime, timezone
from typing import Dict, List

import requests
import structlog

logger = structlog.get_logger()

LANGFUSE_URL = os.getenv("LANGFUSE_URL", "http://omni-langfuse:3000")
LANGFUSE_PUBLIC_KEY = os.getenv("LANGFUSE_PUBLIC_KEY", "")
LANGFUSE_SECRET_KEY = os.getenv("LANGFUSE_SECRET_KEY", "")

def get_cache_metrics() -> Dict:
    """Fetch cache-related metrics from Langfuse."""
    try:
        response = requests.get(
            f"{LANGFUSE_URL}/api/public/metrics",
            auth=(LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY) if LANGFUSE_PUBLIC_KEY else None,
            timeout=10,
        )
        if response.status_code == 200:
            return response.json()
        else:
            logger.warning("langfuse_request_failed", status=response.status_code)
            return {}
    except Exception as e:
        logger.error("langfuse_error", error=str(e))
        return {}

def analyze_cache_performance(metrics: Dict) -> Dict:
    """Analyze cache performance from metrics."""
    # This would be customized based on actual Langfuse API response structure
    traces = metrics.get("traces", [])
    
    total_requests = len(traces)
    cache_hits = sum(1 for t in traces if t.get("metadata", {}).get("cache_hit", False))
    cache_misses = total_requests - cache_hits
    
    hit_rate = (cache_hits / total_requests * 100) if total_requests > 0 else 0
    
    # Token savings estimation
    tokens_saved = sum(
        t.get("metadata", {}).get("tokens_saved", 0)
        for t in traces if t.get("metadata", {}).get("cache_hit", False)
    )
    
    # Cost savings (rough estimate)
    cost_saved = (tokens_saved / 1000) * 0.002  # Average token price
    
    return {
        "total_requests": total_requests,
        "cache_hits": cache_hits,
        "cache_misses": cache_misses,
        "hit_rate_percent": round(hit_rate, 2),
        "tokens_saved": tokens_saved,
        "estimated_cost_saved_usd": round(cost_saved, 4),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

def get_model_breakdown(metrics: Dict) -> List[Dict]:
    """Break down cache performance by model."""
    traces = metrics.get("traces", [])
    
    model_stats = {}
    for trace in traces:
        model = trace.get("model", "unknown")
        if model not in model_stats:
            model_stats[model] = {"total": 0, "hits": 0, "tokens_saved": 0}
        
        model_stats[model]["total"] += 1
        if trace.get("metadata", {}).get("cache_hit", False):
            model_stats[model]["hits"] += 1
            model_stats[model]["tokens_saved"] += trace.get("metadata", {}).get("tokens_saved", 0)
    
    results = []
    for model, stats in model_stats.items():
        hit_rate = (stats["hits"] / stats["total"] * 100) if stats["total"] > 0 else 0
        results.append({
            "model": model,
            "total_requests": stats["total"],
            "cache_hits": stats["hits"],
            "hit_rate_percent": round(hit_rate, 2),
            "tokens_saved": stats["tokens_saved"],
        })
    
    return sorted(results, key=lambda x: x["tokens_saved"], reverse=True)

def main():
    parser = argparse.ArgumentParser(description="Prompt Cache Monitor")
    parser.add_argument("--output", help="Output JSON file")
    parser.add_argument("--format", choices=["json", "text"], default="text", help="Output format")
    args = parser.parse_args()
    
    logger.info("fetching_cache_metrics", langfuse_url=LANGFUSE_URL)
    
    metrics = get_cache_metrics()
    performance = analyze_cache_performance(metrics)
    model_breakdown = get_model_breakdown(metrics)
    
    report = {
        "summary": performance,
        "by_model": model_breakdown,
    }
    
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(report, f, indent=2)
        logger.info("report_written", path=args.output)
    
    if args.format == "json":
        print(json.dumps(report, indent=2))
    else:
        print("\n" + "="*60)
        print("PROMPT CACHE PERFORMANCE REPORT")
        print("="*60)
        print(f"Total Requests:      {performance['total_requests']}")
        print(f"Cache Hits:          {performance['cache_hits']}")
        print(f"Cache Misses:        {performance['cache_misses']}")
        print(f"Hit Rate:            {performance['hit_rate_percent']}%")
        print(f"Tokens Saved:        {performance['tokens_saved']:,}")
        print(f"Est. Cost Saved:     ${performance['estimated_cost_saved_usd']:.4f}")
        print("\nBy Model:")
        for m in model_breakdown[:5]:
            print(f"  {m['model']}: {m['hit_rate_percent']}% hit rate, {m['tokens_saved']:,} tokens saved")

if __name__ == "__main__":
    main()
