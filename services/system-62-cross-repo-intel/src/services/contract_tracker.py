from __future__ import annotations

import re
from pathlib import Path

from src.models import APIContract


class ContractTracker:
    def extract_contracts(self, service_path: str) -> list[APIContract]:
        contracts: list[APIContract] = []
        path = Path(service_path)
        for pyf in path.rglob("*.py"):
            text = pyf.read_text(errors="ignore")
            for method in ["get", "post", "put", "delete"]:
                for m in re.finditer(rf"@.*\.{method}\(\s*[\"']([^\"']+)", text):
                    contracts.append(
                        APIContract(
                            service=path.name,
                            endpoint=m.group(1),
                            method=method.upper(),
                            request_schema={},
                            response_schema={},
                            version="v1",
                        )
                    )
        return contracts

    def detect_changes(self, old: list[APIContract], new: list[APIContract]):
        old_set = {(c.method, c.endpoint) for c in old}
        new_set = {(c.method, c.endpoint) for c in new}
        removed = old_set - new_set
        added = new_set - old_set
        return {"removed": sorted(removed), "added": sorted(added)}
