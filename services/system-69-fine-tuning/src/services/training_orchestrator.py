from __future__ import annotations

import uuid
from datetime import datetime

from src.models import FineTuneJob, LoRAConfig


class TrainingOrchestrator:
    def __init__(self) -> None:
        self._jobs: dict[str, FineTuneJob] = {}

    def start_job(self, base_model: str, dataset_id: str, lora_config: LoRAConfig) -> FineTuneJob:
        job = FineTuneJob(id=f"job-{uuid.uuid4().hex[:8]}", base_model=base_model, dataset_id=dataset_id, status="running")
        self._jobs[job.id] = job
        return job

    def complete_job(self, job_id: str, eval_results: list[dict]) -> FineTuneJob | None:
        job = self._jobs.get(job_id)
        if not job:
            return None
        job.status = "completed"
        job.completed_at = datetime.utcnow()
        job.eval_results = eval_results
        return job

    def list_jobs(self) -> list[FineTuneJob]:
        return sorted(self._jobs.values(), key=lambda x: x.created_at, reverse=True)

    def get_job(self, job_id: str) -> FineTuneJob | None:
        return self._jobs.get(job_id)
