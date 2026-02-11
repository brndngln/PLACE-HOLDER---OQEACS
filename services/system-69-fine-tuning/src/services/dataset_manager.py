from __future__ import annotations

import json
import uuid
from collections import Counter
from pathlib import Path

from src.models import DatasetStats, TrainingDataEntry


class DatasetManager:
    def __init__(self, base_dir: str = "services/system-69-fine-tuning/data") -> None:
        self.base = Path(base_dir)
        self.base.mkdir(parents=True, exist_ok=True)

    def create_dataset(self, entries: list[TrainingDataEntry]) -> str:
        dataset_id = f"ds-{uuid.uuid4().hex[:8]}"
        path = self.base / f"{dataset_id}.jsonl"
        with path.open("w", encoding="utf-8") as f:
            for entry in entries:
                f.write(json.dumps(entry.model_dump(), ensure_ascii=False) + "\n")
        return dataset_id

    def stats(self, entries: list[TrainingDataEntry]) -> DatasetStats:
        by_lang = Counter(e.language for e in entries)
        by_task = Counter(e.task_type for e in entries)
        avg = sum(e.quality_score for e in entries) / max(len(entries), 1)
        return DatasetStats(total_entries=len(entries), by_language=dict(by_lang), by_task_type=dict(by_task), avg_quality=round(avg, 3))

    def split(self, entries: list[TrainingDataEntry]) -> dict[str, list[TrainingDataEntry]]:
        n = len(entries)
        a = int(n * 0.8)
        b = int(n * 0.9)
        return {"train": entries[:a], "val": entries[a:b], "test": entries[b:]}
