#!/usr/bin/env python3
"""
Omni Quantum Elite — CLI Tool
===============================
Unified command-line interface for the entire platform.

Usage:
  omni status                      Platform overview
  omni services [--tier T] [--tag] List all services
  omni health <service>            Check specific service
  omni restart <service>           Restart a container
  omni backup [service]            Trigger backup
  omni deploy <app>                Trigger deployment
  omni rotate [service]            Rotate secrets
  omni search <query>              Search services
  omni logs <service> [--tail N]   View service logs
  omni docker                      Docker host stats
  omni topology                    Dependency graph
  omni events [--limit N]          Recent events
  omni refresh                     Force health refresh
  omni configure                   Set orchestrator URL
"""

import argparse
import json
import os
import subprocess
import sys

try:
    import httpx
except ImportError:
    print("Installing httpx...")
    os.system(f"{sys.executable} -m pip install httpx -q")
    import httpx

# Config
CONFIG_PATH = os.path.expanduser("~/.omni/config.json")
DEFAULT_URL = "http://localhost:9500"

# ---- Colors ----
class C:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    PURPLE = "\033[95m"
    CYAN = "\033[96m"
    DIM = "\033[2m"

STATUS_COLORS = {
    "healthy": C.GREEN, "degraded": C.YELLOW,
    "down": C.RED, "unknown": C.DIM,
}
STATUS_DOTS = {
    "healthy": "●", "degraded": "◐", "down": "○", "unknown": "·",
}
TIER_COLORS = {
    "critical": C.RED, "high": C.YELLOW, "standard": C.BLUE,
}


def get_url() -> str:
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH) as f:
            return json.load(f).get("url", DEFAULT_URL)
    return os.getenv("OMNI_URL", DEFAULT_URL)


def api_get(path: str) -> dict:
    try:
        resp = httpx.get(f"{get_url()}{path}", timeout=15)
        resp.raise_for_status()
        return resp.json()
    except httpx.ConnectError:
        print(f"{C.RED}✗ Cannot connect to Omni Command at {get_url()}{C.RESET}")
        print(f"  Run: {C.CYAN}omni configure{C.RESET} to set the correct URL")
        sys.exit(1)
    except Exception as e:
        print(f"{C.RED}✗ Error: {e}{C.RESET}")
        sys.exit(1)


def api_post(path: str, data: dict | None = None) -> dict:
    try:
        resp = httpx.post(f"{get_url()}{path}", json=data or {}, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except httpx.ConnectError:
        print(f"{C.RED}✗ Cannot connect to Omni Command at {get_url()}{C.RESET}")
        sys.exit(1)
    except Exception as e:
        print(f"{C.RED}✗ Error: {e}{C.RESET}")
        sys.exit(1)


# ---- Commands ----

def cmd_status(_args):
    """Platform overview."""
    data = api_get("/api/v1/overview")
    emoji = data.get("emoji", "⚪")
    status = data.get("platform_status", "unknown").upper()
    healthy = data.get("healthy", 0)
    total = data.get("total_services", 36)
    degraded = data.get("degraded", 0)
    down = data.get("down", 0)
    uptime = data.get("uptime_pct", 0)

    status_color = {
        "OPERATIONAL": C.GREEN, "DEGRADED": C.YELLOW,
        "PARTIAL_OUTAGE": C.YELLOW, "MAJOR_OUTAGE": C.RED,
    }.get(status, C.DIM)

    print()
    print(f"  {C.BOLD}{C.PURPLE}⚛ Omni Quantum Elite{C.RESET}")
    print(f"  {C.DIM}{'─' * 40}{C.RESET}")
    print(f"  Platform Status:  {status_color}{C.BOLD}{emoji} {status}{C.RESET}")
    print(f"  Services:         {C.GREEN}{healthy}{C.RESET}/{total} healthy")
    if degraded:
        print(f"  Degraded:         {C.YELLOW}{degraded}{C.RESET}")
    if down:
        print(f"  Down:             {C.RED}{down}{C.RESET}")
    print(f"  Uptime:           {C.CYAN}{uptime}%{C.RESET}")

    tier_summary = data.get("tier_summary", {})
    print(f"\n  {C.DIM}Tier Breakdown:{C.RESET}")
    for tier_name, info in tier_summary.items():
        tc = TIER_COLORS.get(tier_name, C.DIM)
        print(f"    {tc}{tier_name.title():12}{C.RESET}  {info.get('healthy', 0)}/{info.get('total', 0)}")
    print()


def cmd_services(args):
    """List all services."""
    data = api_get("/api/v1/status")
    services = data.get("services", [])

    if args.tier:
        services = [s for s in services if s.get("tier") == args.tier]
    if args.tag:
        services = [s for s in services if args.tag in s.get("tags", [])]

    print()
    print(f"  {C.BOLD}{'#':>3}  {'Service':<30} {'Status':^10} {'Tier':^10} {'Latency':>8}{C.RESET}")
    print(f"  {C.DIM}{'─' * 68}{C.RESET}")

    for s in services:
        sc = STATUS_COLORS.get(s["status"], C.DIM)
        tc = TIER_COLORS.get(s["tier"], C.DIM)
        dot = STATUS_DOTS.get(s["status"], "·")
        print(
            f"  {s['id']:>3}  {s['name']:<30} "
            f"{sc}{dot} {s['status']:<8}{C.RESET} "
            f"{tc}{s['tier']:<10}{C.RESET} "
            f"{C.DIM}{s['latency_ms']:>6}ms{C.RESET}"
        )
    print(f"\n  {C.DIM}{len(services)} services{C.RESET}\n")


def cmd_health(args):
    """Check specific service."""
    data = api_get(f"/api/v1/status/name/{args.service}")
    if "error" in data:
        print(f"{C.RED}✗ Service '{args.service}' not found{C.RESET}")
        return

    sc = STATUS_COLORS.get(data["status"], C.DIM)
    print()
    print(f"  {C.BOLD}{data['name']}{C.RESET} (#{data['id']})")
    print(f"  Status:   {sc}{data['status']}{C.RESET}")
    print(f"  Tier:     {data['tier']}")
    print(f"  Latency:  {data['latency_ms']}ms")
    print(f"  Message:  {data.get('message', '')}")
    print(f"  Tags:     {', '.join(data.get('tags', []))}")
    print(f"  Checked:  {data.get('checked_at', '')[:19]}")
    print()


def cmd_restart(args):
    """Restart service."""
    print(f"  Restarting {C.BOLD}{args.service}{C.RESET}...")
    data = api_post("/api/v1/action/restart", {"target": args.service})
    if "error" in data:
        print(f"  {C.RED}✗ {data['error']}{C.RESET}")
    else:
        print(f"  {C.GREEN}✓ Container {data.get('container', '')} restarting{C.RESET}")


def cmd_backup(args):
    """Trigger backup."""
    target = args.service or "all"
    print(f"  Triggering backup for {C.BOLD}{target}{C.RESET}...")
    data = api_post("/api/v1/action/backup", {"target": target})
    if "error" in data:
        print(f"  {C.RED}✗ {data['error']}{C.RESET}")
    else:
        print(f"  {C.GREEN}✓ Backup triggered{C.RESET}")


def cmd_deploy(args):
    """Trigger deployment."""
    print(f"  Deploying {C.BOLD}{args.app}{C.RESET}...")
    data = api_post("/api/v1/action/deploy", {"target": args.app})
    if "error" in data:
        print(f"  {C.RED}✗ {data['error']}{C.RESET}")
    else:
        print(f"  {C.GREEN}✓ Deploy triggered{C.RESET}")


def cmd_rotate(args):
    """Rotate secrets."""
    target = args.service or "all"
    print(f"  Rotating secrets for {C.BOLD}{target}{C.RESET}...")
    data = api_post("/api/v1/action/rotate-secrets", {"target": target})
    if "error" in data:
        print(f"  {C.RED}✗ {data['error']}{C.RESET}")
    else:
        print(f"  {C.GREEN}✓ Rotation triggered{C.RESET}")


def cmd_search(args):
    """Search services."""
    data = api_get(f"/api/v1/search?q={args.query}")
    results = data.get("results", [])
    if not results:
        print(f"  No services found matching '{args.query}'")
        return

    print(f"\n  {C.BOLD}Search: {args.query}{C.RESET} ({len(results)} results)\n")
    for r in results:
        sc = STATUS_COLORS.get(r.get("status", ""), C.DIM)
        dot = STATUS_DOTS.get(r.get("status", ""), "·")
        print(f"  {sc}{dot}{C.RESET} #{r['id']:>2} {C.BOLD}{r['name']}{C.RESET} — {C.DIM}{r['description'][:60]}{C.RESET}")
    print()


def cmd_logs(args):
    """Stream container logs for a service."""
    service = args.service
    tail = str(args.tail)
    cmd = ["docker", "logs", service, "--tail", tail]
    if args.follow:
        cmd.append("--follow")
    if args.since:
        cmd.extend(["--since", args.since])

    print(f"  {C.BOLD}Logs: {service}{C.RESET} (tail={tail}{', follow' if args.follow else ''}{', since=' + args.since if args.since else ''})")
    try:
        subprocess.run(cmd, check=True)
    except FileNotFoundError:
        print(f"{C.RED}✗ docker command not found{C.RESET}")
        sys.exit(1)
    except subprocess.CalledProcessError as exc:
        print(f"{C.RED}✗ Failed to fetch logs for '{service}' (exit {exc.returncode}){C.RESET}")
        sys.exit(exc.returncode)


def cmd_docker(_args):
    """Docker host stats."""
    data = api_get("/api/v1/docker/stats")
    print()
    print(f"  {C.BOLD}🐳 Docker Host{C.RESET}")
    print(f"  Running:  {C.GREEN}{data.get('containers_running', 0)}{C.RESET} containers")
    print(f"  Stopped:  {data.get('containers_stopped', 0)} containers")
    print(f"  Images:   {data.get('images', 0)}")
    print(f"  CPUs:     {data.get('cpu_count', 0)}")
    print(f"  Memory:   {data.get('memory_gb', 0)} GB")
    print(f"  Docker:   v{data.get('docker_version', '?')}")
    print(f"  OS:       {data.get('os', '?')}")
    print()


def cmd_topology(_args):
    """Dependency graph."""
    data = api_get("/api/v1/topology")
    nodes = {n["id"]: n for n in data.get("nodes", [])}
    edges = data.get("edges", [])

    print(f"\n  {C.BOLD}Service Dependency Graph{C.RESET}\n")
    for node in sorted(nodes.values(), key=lambda x: x["id"]):
        sc = STATUS_COLORS.get(node.get("status", ""), C.DIM)
        dot = STATUS_DOTS.get(node.get("status", ""), "·")
        deps = [nodes[e["from"]]["codename"] for e in edges if e["to"] == node["id"] and e["from"] in nodes]
        dep_str = f" ← {', '.join(deps)}" if deps else ""
        print(f"  {sc}{dot}{C.RESET} #{node['id']:>2} {node['name']}{C.DIM}{dep_str}{C.RESET}")
    print()


def cmd_events(args):
    """Recent events."""
    limit = args.limit or 20
    data = api_get(f"/api/v1/events/history?limit={limit}")
    events = data.get("events", [])

    if not events:
        print("  No recent events.")
        return

    print(f"\n  {C.BOLD}Recent Events{C.RESET}\n")
    for ev in reversed(events):
        ts = ev.get("timestamp", "")[:19]
        svc = ev.get("service", "?")
        from_s = ev.get("from", "?")
        to_s = ev.get("to", "?")
        tc = STATUS_COLORS.get(to_s, C.DIM)
        print(f"  {C.DIM}{ts}{C.RESET}  {C.BOLD}{svc:<20}{C.RESET} {from_s} → {tc}{to_s}{C.RESET}")
    print()


def cmd_refresh(_args):
    """Force health refresh."""
    print("  Refreshing all service health...")
    data = api_post("/api/v1/action/refresh")
    healthy = data.get("result", {}).get("healthy", 0)
    total = data.get("result", {}).get("total_services", 36)
    print(f"  {C.GREEN}✓ Done — {healthy}/{total} services healthy{C.RESET}")


def cmd_configure(_args):
    """Set orchestrator URL."""
    current = get_url()
    print(f"  Current URL: {C.CYAN}{current}{C.RESET}")
    url = input(f"  New URL [{current}]: ").strip() or current
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        json.dump({"url": url}, f)
    print(f"  {C.GREEN}✓ Saved to {CONFIG_PATH}{C.RESET}")


# ---- Main ----

def main():
    parser = argparse.ArgumentParser(
        prog="omni",
        description="⚛ Omni Quantum Elite — Unified Platform CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("status", help="Platform overview")

    p_svcs = sub.add_parser("services", help="List all services")
    p_svcs.add_argument("--tier", choices=["critical", "high", "standard"])
    p_svcs.add_argument("--tag")

    p_health = sub.add_parser("health", help="Check specific service")
    p_health.add_argument("service")

    p_restart = sub.add_parser("restart", help="Restart a service")
    p_restart.add_argument("service")

    p_backup = sub.add_parser("backup", help="Trigger backup")
    p_backup.add_argument("service", nargs="?")

    p_deploy = sub.add_parser("deploy", help="Trigger deployment")
    p_deploy.add_argument("app")

    p_rotate = sub.add_parser("rotate", help="Rotate secrets")
    p_rotate.add_argument("service", nargs="?")

    p_search = sub.add_parser("search", help="Search services")
    p_search.add_argument("query")

    p_logs = sub.add_parser("logs", help="View service logs")
    p_logs.add_argument("service")
    p_logs.add_argument("--follow", action="store_true")
    p_logs.add_argument("--tail", type=int, default=200)
    p_logs.add_argument("--since")

    sub.add_parser("docker", help="Docker host stats")
    sub.add_parser("topology", help="Dependency graph")

    p_events = sub.add_parser("events", help="Recent events")
    p_events.add_argument("--limit", type=int, default=20)

    sub.add_parser("refresh", help="Force health refresh")
    sub.add_parser("configure", help="Set orchestrator URL")

    args = parser.parse_args()

    commands = {
        "status": cmd_status, "services": cmd_services, "health": cmd_health,
        "restart": cmd_restart, "backup": cmd_backup, "deploy": cmd_deploy,
        "rotate": cmd_rotate, "search": cmd_search, "logs": cmd_logs, "docker": cmd_docker,
        "topology": cmd_topology, "events": cmd_events, "refresh": cmd_refresh,
        "configure": cmd_configure,
    }

    if args.command in commands:
        commands[args.command](args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
