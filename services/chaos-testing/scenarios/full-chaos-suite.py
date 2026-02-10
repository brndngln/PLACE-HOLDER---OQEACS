from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
from pathlib import Path

import httpx

SCENARIOS = [
    "database-latency.py",
    "database-disconnect.py",
    "llm-timeout.py",
    "network-partition.py",
    "bandwidth-limit.py",
]


def score_from_reports(report_dir: Path) -> dict:
    score = 0
    services = {}
    for r in report_dir.glob("*-report.json"):
        data = json.loads(r.read_text())
        ok = any(v.get("ok") for v in data.values() if isinstance(v, dict))
        score += 20 if ok else 5
    overall = min(score, 100)
    services["overall"] = overall
    return {"overall_score": overall, "services": services}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", required=True)
    parser.add_argument("--report-dir", required=True)
    args = parser.parse_args()
    report_dir = Path(args.report_dir)
    report_dir.mkdir(parents=True, exist_ok=True)

    for scenario in SCENARIOS:
        subprocess.run(["python", str(Path(__file__).with_name(scenario)), "--target", args.target, "--report-dir", args.report_dir], check=True)

    resilience = score_from_reports(report_dir)
    resilience["generated_at"] = dt.datetime.utcnow().isoformat()
    (report_dir / "resilience-report.json").write_text(json.dumps(resilience, indent=2))
    (report_dir / "resilience-report.md").write_text(f"# Chaos Resilience\n\nOverall score: {resilience['overall_score']}/100\n")

    httpx.post("http://omni-mattermost-webhook:8066/hooks/builds", json={"text": f"[chaos-suite] overall resilience: {resilience['overall_score']}/100"}, timeout=10.0)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
