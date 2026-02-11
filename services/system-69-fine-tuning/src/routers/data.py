from __future__ import annotations

from fastapi import APIRouter

from src.models import CollectRequest
from src.services.data_collector import DataCollector
from src.services.dataset_manager import DatasetManager

router = APIRouter(prefix="/api/v1", tags=["data"])
_datasets: dict[str, dict] = {}
_mgr = DatasetManager()


@router.post("/collect")
def collect(req: CollectRequest):
    entries = DataCollector().collect(req)
    ds_id = _mgr.create_dataset(entries)
    _datasets[ds_id] = {"entries": entries, "stats": _mgr.stats(entries)}
    return {"dataset_id": ds_id, "count": len(entries)}


@router.get("/datasets")
def datasets():
    return [{"id": k, "stats": v["stats"]} for k, v in _datasets.items()]


@router.get("/datasets/{dataset_id}/stats")
def dataset_stats(dataset_id: str):
    item = _datasets.get(dataset_id)
    return item["stats"] if item else {"detail": "not found"}
