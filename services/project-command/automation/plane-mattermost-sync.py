import os
import structlog
import httpx
from fastapi import FastAPI, Request
from fastapi.responses import Response
from prometheus_client import Counter, generate_latest
from contextlib import asynccontextmanager
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

logger = structlog.get_logger()
EVENTS = Counter("webhook_events_total", "Webhook events", ["event_type"])
MM_WEBHOOK = "http://omni-mattermost-webhook:8066"

PLANE_API = os.getenv("PLANE_API_BASE", "https://notion.so")
PLANE_TOKEN = os.getenv("PLANE_API_TOKEN", "")
WORKSPACE = os.getenv("PLANE_WORKSPACE", "omni-quantum")
TWENTY_API = os.getenv("TWENTY_API_BASE", "https://notion.so")
TWENTY_TOKEN = os.getenv("TWENTY_API_TOKEN", "")

scheduler = AsyncIOScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler.add_job(daily_digest, CronTrigger(hour=17, minute=0))
    scheduler.start()
    yield
    scheduler.shutdown()


app = FastAPI(title="Plane-Mattermost Sync", lifespan=lifespan)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/ready")
async def ready():
    return {"status": "ready"}


@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type="text/plain")


async def notify_mm(channel: str, text: str):
    async with httpx.AsyncClient() as c:
        await c.post(MM_WEBHOOK, json={"channel": channel, "text": text})


async def plane_get(path: str) -> dict:
    async with httpx.AsyncClient() as c:
        r = await c.get(
            f"{PLANE_API}/workspaces/{WORKSPACE}/{path}",
            headers={"Authorization": f"Bearer {PLANE_TOKEN}"},
        )
        r.raise_for_status()
        return r.json()


@app.post("/webhook/plane/state-change")
async def handle_state_change(request: Request):
    payload = await request.json()
    EVENTS.labels(event_type="state_change").inc()

    issue = payload.get("data", {})
    title = issue.get("name", "Unknown")
    state = issue.get("state", {}).get("name", "")
    project_id = issue.get("project", "")
    issue_id = issue.get("id", "")
    assignee = issue.get("assignee", {}).get("display_name", "Unassigned")

    logger.info("plane.state_change", title=title, state=state, project_id=project_id)

    if state == "In Development":
        await notify_mm("#builds", f"\U0001f528 {title} moved to development — assigned to {assignee}")

    elif state == "AI Review":
        async with httpx.AsyncClient() as c:
            task_payload = {
                "title": f"Review: {title}",
                "issue_id": issue_id,
                "project_id": project_id,
                "type": "code_review",
            }
            try:
                await c.post("http://omni-openhands:3000/api/tasks", json=task_payload, timeout=15)
            except httpx.RequestError:
                logger.warning("openhands.unavailable, trying swe-agent")
                await c.post("http://omni-swe-agent:8000/api/tasks", json=task_payload, timeout=15)

    elif state == "Production":
        await notify_mm(
            "#deployments",
            f"\U0001f680 {title} deployed to production (project: {project_id})",
        )

    elif state == "Complete":
        async with httpx.AsyncClient() as c:
            r = await c.get(
                f"{TWENTY_API}/deals",
                headers={"Authorization": f"Bearer {TWENTY_TOKEN}"},
                params={"filter[plane_project_id]": project_id},
            )
            if r.status_code == 200:
                deals = r.json().get("data", [])
                for deal in deals:
                    await c.patch(
                        f"{TWENTY_API}/deals/{deal['id']}",
                        headers={"Authorization": f"Bearer {TWENTY_TOKEN}"},
                        json={"stage": "Completed"},
                    )
                    await notify_mm(
                        "#general",
                        f"\u2705 Project {title} completed — CRM deal {deal['id']} updated to Completed",
                    )

    return {"status": "processed", "state": state}


@app.post("/webhook/plane/issue-created")
async def handle_issue_created(request: Request):
    payload = await request.json()
    EVENTS.labels(event_type="issue_created").inc()

    issue = payload.get("data", {})
    title = issue.get("name", "Unknown")
    priority = issue.get("priority", "none")
    assignee = issue.get("assignee", {}).get("display_name", "Unassigned")

    logger.info("plane.issue_created", title=title, priority=priority)
    await notify_mm("#general", f"\U0001f4cb New: {title} [{priority}] \u2192 {assignee}")
    return {"status": "processed"}


async def daily_digest():
    EVENTS.labels(event_type="daily_digest").inc()
    logger.info("plane.daily_digest.start")

    try:
        projects = await plane_get("projects/")
        project_list = projects.get("results", projects) if isinstance(projects, dict) else projects

        lines = ["\U0001f4ca **Daily Project Digest**\n"]
        for proj in (project_list if isinstance(project_list, list) else []):
            pid = proj.get("id", "")
            pname = proj.get("name", "Unknown")
            issues = await plane_get(f"projects/{pid}/issues/?expand=state")
            issue_list = issues.get("results", issues) if isinstance(issues, dict) else issues

            state_counts = {}
            overdue = 0
            if isinstance(issue_list, list):
                for iss in issue_list:
                    sname = iss.get("state", {}).get("name", "Unknown")
                    state_counts[sname] = state_counts.get(sname, 0) + 1
                    if iss.get("target_date") and iss.get("state", {}).get("name") not in ("Complete", "Resolved"):
                        overdue += 1

            states_str = ", ".join(f"{k}: {v}" for k, v in state_counts.items())
            lines.append(f"**{pname}**: {states_str}")
            if overdue:
                lines.append(f"  \u26a0\ufe0f {overdue} potentially overdue")

        modules = await plane_get(f"projects/{pid}/modules/") if project_list else {}
        mod_list = modules.get("results", modules) if isinstance(modules, dict) else modules
        if isinstance(mod_list, list):
            for mod in mod_list:
                total = mod.get("total_issues", 0)
                completed = mod.get("completed_issues", 0)
                if total > 0:
                    pct = round((completed / total) * 100)
                    lines.append(f"  Sprint '{mod.get('name', '')}': {pct}% complete")

        await notify_mm("#general", "\n".join(lines))
    except Exception as e:
        logger.error("plane.daily_digest.error", error=str(e))
