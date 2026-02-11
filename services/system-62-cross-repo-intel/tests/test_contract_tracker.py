from __future__ import annotations

from src.models import APIContract
from src.services.contract_tracker import ContractTracker


def test_extract_contracts_fastapi(tmp_path) -> None:
    (tmp_path / "main.py").write_text("@app.get('/x')\ndef x():\n    return {}", encoding="utf-8")
    contracts = ContractTracker().extract_contracts(str(tmp_path))
    assert len(contracts) == 1


def test_detect_changes_added_removed() -> None:
    tracker = ContractTracker()
    old = [APIContract(service="s", endpoint="/a", method="GET")]
    new = [APIContract(service="s", endpoint="/b", method="GET")]
    diff = tracker.detect_changes(old, new)
    assert diff["added"] and diff["removed"]


def test_extract_none_when_no_routes(tmp_path) -> None:
    (tmp_path / "a.py").write_text("print('x')", encoding="utf-8")
    contracts = ContractTracker().extract_contracts(str(tmp_path))
    assert contracts == []


def test_extract_multiple_methods(tmp_path) -> None:
    (tmp_path / "a.py").write_text("@app.post('/p')\ndef p():\n return {}\n@app.delete('/d')\ndef d():\n return {}", encoding="utf-8")
    contracts = ContractTracker().extract_contracts(str(tmp_path))
    assert len(contracts) == 2
