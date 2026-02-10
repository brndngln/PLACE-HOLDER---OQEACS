from __future__ import annotations

import argparse
from common import add_toxic, remove_toxic, timed_probe, write_report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", required=True)
    parser.add_argument("--report-dir", required=True)
    args = parser.parse_args()

    add_toxic("qdrant-proxy", "qdrant-partition", "timeout", {"timeout": 1})
    ingestor = timed_probe("http://omni-knowledge-ingestor:9300/health")
    cache = timed_probe("http://omni-semantic-cache:9302/health")
    remove_toxic("qdrant-proxy", "qdrant-partition")

    report = {
        "scenario": "network-partition",
        "target": args.target,
        "knowledge_ingestor": ingestor,
        "semantic_cache": cache,
        "graceful_services": [s for s, v in [("knowledge-ingestor", ingestor), ("semantic-cache", cache)] if v.get("ok")],
    }
    write_report(args.report_dir, "network-partition-report.json", report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
