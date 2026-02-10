#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from typing import Any

import httpx

ORCH = os.getenv("ORCHESTRATOR_URL", "http://omni-orchestrator:9500")


def c(txt: str, color: str) -> str:
    m = {"red": "31", "green": "32", "yellow": "33", "blue": "34"}
    return f"\033[{m.get(color,'0')}m{txt}\033[0m"


def req(url: str, method: str = "GET", payload: dict[str, Any] | None = None) -> Any:
    try:
        with httpx.Client(timeout=30.0) as client:
            r = client.request(method, url, json=payload)
            if r.status_code == 404:
                print(c("Not found", "yellow"))
                sys.exit(1)
            r.raise_for_status()
            return r.json() if r.text else {}
    except httpx.ConnectError:
        print(c("Service unreachable", "red"))
        sys.exit(1)
    except Exception as e:
        print(c(f"Error: {e}", "red"))
        sys.exit(1)


def pretty(data: Any) -> None:
    print(json.dumps(data, indent=2, ensure_ascii=False))


def cmd_status(_: argparse.Namespace) -> int:
    pretty(req(f"{ORCH}/api/v1/overview"))
    return 0


def cmd_services(a: argparse.Namespace) -> int:
    data = req(f"{ORCH}/api/v1/status")
    if a.tier and a.tier != "all":
        data = [s for s in data if s.get("tier") == a.tier]
    pretty(data)
    return 0


def cmd_health(a: argparse.Namespace) -> int:
    pretty(req(f"{ORCH}/api/v1/status/name/{a.service}"))
    return 0


def cmd_build(a: argparse.Namespace) -> int:
    payload = {"description": a.description, "task_type": a.type, "complexity": a.complexity, "language": a.lang, "framework": a.framework}
    pretty(req("http://omni-openhands-orchestrator:3001/tasks", "POST", payload))
    return 0


def cmd_tasks(a: argparse.Namespace) -> int:
    data = req("http://omni-openhands-orchestrator:3001/tasks")
    if a.status:
        data = [t for t in data if t.get("status") == a.status]
    pretty(data)
    return 0


def cmd_approve(a: argparse.Namespace) -> int:
    pretty(req(f"http://omni-openhands-orchestrator:3001/tasks/{a.task_id}/approve", "POST"))
    return 0


def cmd_reject(a: argparse.Namespace) -> int:
    pretty(req(f"http://omni-openhands-orchestrator:3001/tasks/{a.task_id}/reject", "POST", {"feedback": a.feedback}))
    return 0


def cmd_deploy(a: argparse.Namespace) -> int:
    pretty(req(f"{ORCH}/api/v1/action/deploy", "POST", {"app": a.app, "environment": a.env}))
    return 0


def cmd_logs(a: argparse.Namespace) -> int:
    args = ["docker", "logs", f"--tail={a.tail}", f"omni-{a.service}"]
    if a.follow:
        args.insert(2, "-f")
    return subprocess.call(args)


def cmd_restart(a: argparse.Namespace) -> int:
    pretty(req(f"{ORCH}/api/v1/action/restart", "POST", {"container": f"omni-{a.service}"}))
    return 0


def cmd_backup(a: argparse.Namespace) -> int:
    endpoint = "all" if a.target == "all" else a.target
    pretty(req(f"http://omni-backup-orchestrator:8000/backup/{endpoint}", "POST"))
    return 0


def cmd_models(_: argparse.Namespace) -> int:
    pretty(req("http://omni-model-manager:11435/models"))
    return 0


def cmd_gpu(_: argparse.Namespace) -> int:
    pretty(req("http://omni-model-manager:11435/gpu/status"))
    return 0


def cmd_costs(a: argparse.Namespace) -> int:
    endpoint = {"today": "today", "week": "this_week", "month": "this_month"}[a.period]
    pretty(req(f"http://omni-litellm-cost-tracker:4001/costs/{endpoint}"))
    return 0


def cmd_invoices(a: argparse.Namespace) -> int:
    url = "http://omni-invoice-generator:81/invoices/overdue" if a.overdue else "http://omni-invoice-generator:81/invoices/summary"
    pretty(req(url))
    return 0


def cmd_revenue(_: argparse.Namespace) -> int:
    pretty({"pipeline": req("http://omni-crm-sync:3001/crm/pipeline-summary"), "forecast": req("http://omni-crm-sync:3001/crm/revenue-forecast")})
    return 0


def cmd_search(a: argparse.Namespace) -> int:
    pretty(req("http://omni-meilisearch-indexer:7701/search", "POST", {"query": a.query, "indexes": ["all"], "limit": 20}))
    return 0


def cmd_patterns(a: argparse.Namespace) -> int:
    pretty(req("http://omni-neo4j-pattern-api:7475/patterns/recommend", "POST", {"task_description": a.description, "language": a.lang}))
    return 0


def cmd_automate(a: argparse.Namespace) -> int:
    pretty(req("http://omni-mcp-automation:8337/tools/create_automation", "POST", {"description": a.description, "name": a.name, "activate": True}))
    return 0


def cmd_fresh(_: argparse.Namespace) -> int:
    pretty(req("http://omni-knowledge-freshness:9430/freshness"))
    return 0


def cmd_ingest(a: argparse.Namespace) -> int:
    pretty(req("http://omni-knowledge-ingestor:9420/ingest/repository", "POST", {"source_url": a.url, "source_name": a.name, "source_category": a.category}))
    return 0


def cmd_rotate(_: argparse.Namespace) -> int:
    pretty(req("http://omni-secret-rotation:9331/rotation/trigger-all-overdue", "POST"))
    return 0


def cmd_containers(_: argparse.Namespace) -> int:
    return subprocess.call(["docker", "ps", "--filter", "name=omni-", "--format", "table {{.Names}}\t{{.Status}}\t{{.Ports}}"])


def main() -> int:
    p = argparse.ArgumentParser(prog="omni")
    s = p.add_subparsers(dest="cmd", required=True)
    s.add_parser("status").set_defaults(func=cmd_status)
    sp = s.add_parser("services"); sp.add_argument("--tier", default="all", choices=["all", "critical", "high", "standard"]); sp.set_defaults(func=cmd_services)
    sp = s.add_parser("health"); sp.add_argument("service"); sp.set_defaults(func=cmd_health)
    sp = s.add_parser("build"); sp.add_argument("description"); sp.add_argument("--type", default="feature-build"); sp.add_argument("--complexity", default="medium"); sp.add_argument("--lang", default="python"); sp.add_argument("--framework", default="fastapi"); sp.set_defaults(func=cmd_build)
    sp = s.add_parser("tasks"); sp.add_argument("--status"); sp.set_defaults(func=cmd_tasks)
    sp = s.add_parser("approve"); sp.add_argument("task_id"); sp.set_defaults(func=cmd_approve)
    sp = s.add_parser("reject"); sp.add_argument("task_id"); sp.add_argument("feedback"); sp.set_defaults(func=cmd_reject)
    sp = s.add_parser("deploy"); sp.add_argument("app"); sp.add_argument("--env", default="staging", choices=["staging", "production"]); sp.set_defaults(func=cmd_deploy)
    sp = s.add_parser("logs"); sp.add_argument("service"); sp.add_argument("--tail", type=int, default=100); sp.add_argument("--follow", action="store_true"); sp.set_defaults(func=cmd_logs)
    sp = s.add_parser("restart"); sp.add_argument("service"); sp.set_defaults(func=cmd_restart)
    sp = s.add_parser("backup"); sp.add_argument("--target", default="all"); sp.set_defaults(func=cmd_backup)
    s.add_parser("models").set_defaults(func=cmd_models)
    s.add_parser("gpu").set_defaults(func=cmd_gpu)
    sp = s.add_parser("costs"); sp.add_argument("--period", default="today", choices=["today", "week", "month"]); sp.set_defaults(func=cmd_costs)
    sp = s.add_parser("invoices"); sp.add_argument("--overdue", action="store_true"); sp.set_defaults(func=cmd_invoices)
    s.add_parser("revenue").set_defaults(func=cmd_revenue)
    sp = s.add_parser("search"); sp.add_argument("query"); sp.set_defaults(func=cmd_search)
    sp = s.add_parser("patterns"); sp.add_argument("description"); sp.add_argument("--lang", default="python"); sp.set_defaults(func=cmd_patterns)
    sp = s.add_parser("automate"); sp.add_argument("description"); sp.add_argument("--name", default=""); sp.set_defaults(func=cmd_automate)
    s.add_parser("fresh").set_defaults(func=cmd_fresh)
    sp = s.add_parser("ingest"); sp.add_argument("url"); sp.add_argument("name"); sp.add_argument("--category", default="general"); sp.set_defaults(func=cmd_ingest)
    s.add_parser("rotate").set_defaults(func=cmd_rotate)
    s.add_parser("containers").set_defaults(func=cmd_containers)
    s.add_parser("help").set_defaults(func=lambda _: p.print_help() or 0)

    args = p.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
