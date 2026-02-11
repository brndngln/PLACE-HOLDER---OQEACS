from __future__ import annotations

import uuid

from fastapi import APIRouter

from src.models import HealingAttempt, HealingConfig, HealingResult, PipelineStatus
from src.services.error_monitor import ErrorMonitor
from src.services.fix_generator import FixGenerator
from src.services.pr_creator import PRCreator
from src.services.verification import FixVerifier

router = APIRouter(prefix="/api/v1", tags=["healing"])
_monitor = ErrorMonitor()
_config = HealingConfig()
_attempts: dict[str, HealingAttempt] = {}
_stats = {"healed": 0, "failed": 0}


@router.post("/heal")
def heal(payload: dict):
    events = _monitor.poll_errors([payload])
    if not events:
        return {"status": "no_new_errors"}

    event = events[0]
    source = payload.get("source_code", "")
    fix = FixGenerator().generate_fix(event, source)
    passed = FixVerifier().verify_fix(source, fix)
    pr_url = PRCreator().create_pr(fix, event.message) if passed and _config.auto_pr else None

    attempt = HealingAttempt(
        id=str(uuid.uuid4()),
        error_event=event,
        generated_fix=fix,
        verification_status="passed" if passed else "failed",
        pr_url=pr_url,
        attempts=1,
    )
    _attempts[attempt.id] = attempt
    _stats["healed" if passed else "failed"] += 1

    return HealingResult(success=passed, fix_code=fix, diff="+auto-fix", tests_passed=passed, pr_created=bool(pr_url))


@router.get("/status", response_model=PipelineStatus)
def status() -> PipelineStatus:
    total = _stats["healed"] + _stats["failed"]
    rate = 0.0 if total == 0 else (_stats["healed"] / total) * 100
    return PipelineStatus(active_healings=0, total_healed=_stats["healed"], total_failed=_stats["failed"], success_rate=round(rate, 2))


@router.get("/attempts")
def attempts():
    return list(_attempts.values())


@router.get("/attempts/{attempt_id}")
def attempt(attempt_id: str):
    return _attempts.get(attempt_id, {"detail": "not found"})
