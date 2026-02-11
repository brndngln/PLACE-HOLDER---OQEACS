'''Core business logic for diff-oracle.'''
from __future__ import annotations

import hashlib
import math
import uuid
from datetime import UTC, datetime
from typing import Any

import structlog


logger = structlog.get_logger()


class OmniService:
    '''Stateful service layer implementing endpoint behavior.'''

    def __init__(self, service_name: str):
        self.service_name = service_name
        self.jobs: dict[str, dict[str, Any]] = {}
        self.sessions: dict[str, dict[str, Any]] = {}
        self.records: list[dict[str, Any]] = []
        self.thresholds: dict[str, float] = {
            "code_generation": 0.70,
            "deployment": 0.90,
            "production": 0.95,
        }
        self.policies: list[dict[str, Any]] = []
        self.configs: dict[str, Any] = {}

    @classmethod
    async def create(cls, service_name: str) -> "OmniService":
        logger.info("service_create", service=service_name)
        return cls(service_name=service_name)

    async def shutdown(self) -> None:
        logger.info("service_shutdown", service=self.service_name)

    @staticmethod
    def _stable_score(payload: dict[str, Any]) -> float:
        raw = hashlib.sha256(str(sorted(payload.items())).encode("utf-8")).hexdigest()
        return (int(raw[:8], 16) % 1000) / 1000

    @staticmethod
    def _now() -> str:
        return datetime.now(tz=UTC).isoformat()

    def _new_id(self, prefix: str) -> str:
        return f"{prefix}-{uuid.uuid4().hex[:10]}"

    def _job_payload(self, operation: str, payload: dict[str, Any], path_params: dict[str, str]) -> dict[str, Any]:
        job_id = self._new_id(operation.split("_")[0])
        record = {
            "id": job_id,
            "operation": operation,
            "status": "completed",
            "created_at": self._now(),
            "score": self._stable_score(payload),
            "payload": payload,
            "path_params": path_params,
        }
        self.jobs[job_id] = record
        self.records.append(record)
        return record

    def _resolve_identifier(self, path_params: dict[str, str], payload: dict[str, Any]) -> str | None:
        if path_params:
            return next(iter(path_params.values()))
        for key in ("id", "job_id", "task_id", "scan_id", "report_id", "analysis_id", "service"):
            value = payload.get(key)
            if isinstance(value, str) and value:
                return value
        return None

    async def handle(self, operation: str, payload: dict[str, Any], path_params: dict[str, str]) -> dict[str, Any]:
        tokens = set(operation.split("_"))
        logger.info(
            "operation_invoked",
            service=self.service_name,
            operation=operation,
            payload_keys=sorted(payload.keys()),
            path_params=path_params,
        )

        if "plan" in tokens and "evaluate" in tokens:
            steps = payload.get("steps", [])
            if not isinstance(steps, list):
                steps = []
            evaluated = []
            for index, step in enumerate(steps):
                step_text = step if isinstance(step, str) else str(step)
                samples = [len(step_text) + (index * delta) for delta in (1, 2, 3)]
                mean = sum(samples) / max(len(samples), 1)
                variance = sum((value - mean) ** 2 for value in samples) / max(len(samples), 1)
                normalized_variance = min(variance / max(mean, 1), 1.0)
                confidence = round(max(0.0, 1 - normalized_variance), 4)
                tier = "code_generation"
                if "deploy" in step_text.lower():
                    tier = "deployment"
                if "prod" in step_text.lower():
                    tier = "production"
                evaluated.append(
                    {
                        "step": step_text,
                        "confidence": confidence,
                        "threshold": self.thresholds[tier],
                        "requires_human_approval": confidence < self.thresholds[tier],
                    }
                )
            return {
                "operation": operation,
                "ok": True,
                "data": {
                    "steps": evaluated,
                    "overall_confidence": round(sum(item["confidence"] for item in evaluated) / max(len(evaluated), 1), 4),
                    "evaluated_at": self._now(),
                },
            }

        if "plan" in tokens and "calibrate" in tokens:
            feedback = payload.get("feedback", [])
            if isinstance(feedback, list) and feedback:
                success_ratio = sum(1 for item in feedback if isinstance(item, dict) and item.get("success")) / len(feedback)
                self.thresholds["code_generation"] = round(min(0.95, max(0.55, 0.65 + (1 - success_ratio) * 0.1)), 3)
                self.thresholds["deployment"] = round(min(0.98, max(0.80, 0.85 + (1 - success_ratio) * 0.1)), 3)
                self.thresholds["production"] = round(min(0.995, max(0.90, 0.93 + (1 - success_ratio) * 0.05)), 3)
            return {"operation": operation, "ok": True, "data": {"thresholds": self.thresholds, "updated_at": self._now()}}

        if "thresholds" in tokens:
            return {"operation": operation, "ok": True, "data": {"thresholds": self.thresholds}}

        if "sessions" in tokens and "post" in tokens and "write" not in tokens:
            session_id = self._new_id("session")
            self.sessions[session_id] = {"id": session_id, "created_at": self._now(), "document": payload, "events": []}
            return {"operation": operation, "ok": True, "data": self.sessions[session_id]}

        if "sessions" in tokens and "write" in tokens:
            session_id = self._resolve_identifier(path_params, payload)
            if not session_id or session_id not in self.sessions:
                return {"operation": operation, "ok": False, "data": {"error": "session_not_found"}}
            event = {"at": self._now(), "patch": payload}
            self.sessions[session_id]["events"].append(event)
            self.sessions[session_id]["document"].update(payload)
            return {"operation": operation, "ok": True, "data": {"id": session_id, "event": event}}

        if "sessions" in tokens and ("subscribe" in tokens or "get" in tokens):
            session_id = self._resolve_identifier(path_params, payload)
            if not session_id or session_id not in self.sessions:
                return {"operation": operation, "ok": False, "data": {"error": "session_not_found"}}
            return {"operation": operation, "ok": True, "data": self.sessions[session_id]}

        if "policy" in tokens and "recommend" in tokens:
            feature_score = self._stable_score(payload)
            ranked = [
                {"sequence": ["analyze", "compile", "test"], "score": round(0.65 + feature_score * 0.3, 4)},
                {"sequence": ["lint", "compile", "security_scan"], "score": round(0.55 + feature_score * 0.2, 4)},
            ]
            return {"operation": operation, "ok": True, "data": {"recommendations": ranked}}

        if "policy" in tokens and "feedback" in tokens:
            entry = {"at": self._now(), "payload": payload, "reward": round(self._stable_score(payload), 4)}
            self.policies.append(entry)
            return {"operation": operation, "ok": True, "data": {"stored": entry}}

        if "policy" in tokens and "stats" in tokens:
            avg_reward = round(sum(item["reward"] for item in self.policies) / max(len(self.policies), 1), 4)
            return {"operation": operation, "ok": True, "data": {"feedback_count": len(self.policies), "avg_reward": avg_reward}}

        if ("register" in tokens or "start" in tokens or "record" in tokens or "scan" in tokens) and "status" not in tokens:
            record = self._job_payload(operation, payload, path_params)
            id_key = "id"
            if "scan" in tokens:
                id_key = "scan_id"
            elif "rollout" in tokens:
                id_key = "rollout_id"
            elif "fuzz" in tokens or "repro" in tokens or "eval" in tokens or "preview" in tokens:
                id_key = "job_id"
            elif "record" in tokens and "replay" in tokens:
                id_key = "recording_id"
            return {"operation": operation, "ok": True, "data": {id_key: record["id"], "status": record["status"], "score": record["score"]}}

        if "status" in tokens:
            identifier = self._resolve_identifier(path_params, payload)
            record = self.jobs.get(identifier or "")
            if record is None:
                return {"operation": operation, "ok": False, "data": {"error": "not_found", "id": identifier}}
            return {"operation": operation, "ok": True, "data": record}

        if "best" in tokens and "patch" in tokens:
            identifier = self._resolve_identifier(path_params, payload)
            record = self.jobs.get(identifier or "")
            candidate = {
                "branch": f"patch-tree/{identifier or 'unknown'}/branch-1",
                "score": round((record or {"score": 0.55})["score"] + 0.1, 4),
                "summary": "Apply deterministic fix and preserve behavior.",
            }
            return {"operation": operation, "ok": True, "data": {"best_patch": candidate}}

        if "prune" in tokens:
            identifier = self._resolve_identifier(path_params, payload)
            return {"operation": operation, "ok": True, "data": {"id": identifier, "pruned": True, "at": self._now()}}

        if "findings" in tokens or "alerts" in tokens or "evidence" in tokens or "crashes" in tokens:
            identifier = self._resolve_identifier(path_params, payload)
            items = [
                {"id": f"finding-{i}", "severity": sev, "summary": f"{operation} item {i}", "target": identifier}
                for i, sev in enumerate(["high", "medium", "low"], start=1)
            ]
            return {"operation": operation, "ok": True, "data": {"items": items, "count": len(items)}}

        if "history" in tokens or "recordings" in tokens or "active" in tokens or "services" in tokens:
            return {"operation": operation, "ok": True, "data": {"records": self.records[-50:], "count": len(self.records)}}

        if "validate" in tokens or "verify" in tokens or "audit" in tokens or "test" in tokens:
            score = self._stable_score(payload)
            violations = []
            if score < 0.35:
                violations.append("input_quality_low")
            if "code" in payload and isinstance(payload["code"], str):
                lowered = payload["code"].lower()
                if "todo" in lowered:
                    violations.append("contains_todo")
                if "float" in lowered and "finance" in operation:
                    violations.append("float_used_for_money")
            return {
                "operation": operation,
                "ok": len(violations) == 0,
                "data": {
                    "score": round(score, 4),
                    "violations": violations,
                    "passed": len(violations) == 0,
                },
            }

        if "analyze" in tokens or "diff" in tokens or "query" in tokens or "references" in tokens:
            score = self._stable_score(payload)
            recommendations = [
                "reduce branch complexity",
                "add focused regression coverage",
                "enforce stricter input validation",
            ]
            return {
                "operation": operation,
                "ok": True,
                "data": {
                    "score": round(score, 4),
                    "recommendations": recommendations,
                    "confidence": round(0.5 + (score * 0.5), 4),
                },
            }

        if "compress" in tokens:
            chunks = payload.get("chunks", [])
            token_budget = int(payload.get("token_budget", 0) or 0)
            if not isinstance(chunks, list):
                chunks = []
            selected = chunks[: max(1, min(len(chunks), 5))]
            compression_ratio = round(min(0.95, max(0.1, 1 - (len(selected) / max(len(chunks), 1)))), 4)
            return {
                "operation": operation,
                "ok": True,
                "data": {
                    "token_budget": token_budget,
                    "selected_chunks": selected,
                    "compression_ratio": compression_ratio,
                    "estimated_loss": round(1 - (1 - compression_ratio) ** 2, 4),
                },
            }

        if "configure" in tokens or "add" in tokens or "sync" in tokens or "deploy" in tokens or "promote" in tokens or "rollback" in tokens or "resolve" in tokens:
            self.configs[operation] = {"updated_at": self._now(), "payload": payload, "path_params": path_params}
            return {"operation": operation, "ok": True, "data": self.configs[operation]}

        if "generate" in tokens or "build" in tokens or "sign" in tokens or "openapi" in tokens or "protobuf" in tokens:
            score = self._stable_score(payload)
            artifacts = [
                {"name": "artifact.json", "checksum": hashlib.sha256(f"{operation}{score}".encode()).hexdigest()[:16]},
                {"name": "report.md", "checksum": hashlib.sha256(f"report{score}".encode()).hexdigest()[:16]},
            ]
            return {"operation": operation, "ok": True, "data": {"artifacts": artifacts, "quality_score": round(0.6 + score * 0.4, 4)}}

        if "score" in tokens or "summary" in tokens or "budget" in tokens or "stats" in tokens or "breakdown" in tokens:
            base = self._stable_score(payload)
            burn_rate = round(1 + base * 14, 3)
            return {
                "operation": operation,
                "ok": True,
                "data": {
                    "score": round(base, 4),
                    "summary": {
                        "error_budget_remaining": round(max(0.0, 0.999 - base * 0.4), 4),
                        "burn_rate": burn_rate,
                        "records": len(self.records),
                    },
                },
            }

        if "vectors" in tokens or "profiles" in tokens or "policy" in tokens:
            return {
                "operation": operation,
                "ok": True,
                "data": {
                    "items": ["baseline", "strict", "hardened"],
                    "updated_at": self._now(),
                },
            }

        # Default successful response.
        return {"operation": operation, "ok": True, "data": {"echo": payload, "path_params": path_params}}
