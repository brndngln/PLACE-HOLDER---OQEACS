from __future__ import annotations

import argparse
import time
from common import add_toxic, remove_toxic, timed_probe, write_report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", required=True)
    parser.add_argument("--report-dir", required=True)
    args = parser.parse_args()

    baseline = timed_probe("http://omni-orchestrator:9500/health")
    add_toxic("postgres-proxy", "latency500", "latency", {"latency": 500, "jitter": 200})
    mild = timed_probe("http://omni-orchestrator:9500/health")

    remove_toxic("postgres-proxy", "latency500")
    add_toxic("postgres-proxy", "latency5000", "latency", {"latency": 5000, "jitter": 500})
    severe = timed_probe("http://omni-orchestrator:9500/health")

    remove_toxic("postgres-proxy", "latency5000")
    t0 = time.time()
    recovered = timed_probe("http://omni-orchestrator:9500/health")
    recovery_seconds = int(time.time() - t0)

    report = {
        "scenario": "database-latency",
        "target": args.target,
        "baseline": baseline,
        "mild_latency": mild,
        "severe_latency": severe,
        "recovered": recovered,
        "recovery_seconds": recovery_seconds,
        "circuit_breaker_triggered": not severe.get("ok", False),
    }
    write_report(args.report_dir, "database-latency-report.json", report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
