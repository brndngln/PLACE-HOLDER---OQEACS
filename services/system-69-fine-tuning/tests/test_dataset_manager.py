from __future__ import annotations

from src.models import TrainingDataEntry
from src.services.dataset_manager import DatasetManager


def _sample() -> list[TrainingDataEntry]:
    return [
        TrainingDataEntry(instruction="i", input_text="x", output_text="y", quality_score=0.9, source="s", language="python", task_type="refactor"),
        TrainingDataEntry(instruction="i2", input_text="x2", output_text="y2", quality_score=0.8, source="s", language="python", task_type="bug_fix"),
    ]


def test_create_dataset(tmp_path) -> None:
    mgr = DatasetManager(base_dir=str(tmp_path))
    ds_id = mgr.create_dataset(_sample())
    assert ds_id.startswith("ds-")


def test_stats() -> None:
    mgr = DatasetManager()
    stats = mgr.stats(_sample())
    assert stats.total_entries == 2


def test_split() -> None:
    mgr = DatasetManager()
    split = mgr.split(_sample())
    assert set(split.keys()) == {"train", "val", "test"}
