from __future__ import annotations

import re
from pathlib import Path

from src.models import DocSyncCheck


class SyncChecker:
    def check_sync(self, code_path: str, doc_path: str) -> DocSyncCheck:
        code_text = Path(code_path).read_text(errors="ignore") if Path(code_path).exists() else ""
        doc_text = Path(doc_path).read_text(errors="ignore") if Path(doc_path).exists() else ""

        code_functions = set(re.findall(r"def\s+([a-zA-Z0-9_]+)\(", code_text))
        stale: list[str] = []
        for fn in sorted(code_functions):
            if fn not in doc_text:
                stale.append(f"Missing docs for function: {fn}")

        in_sync = len(stale) == 0
        return DocSyncCheck(file_path=code_path, doc_path=doc_path, in_sync=in_sync, stale_sections=stale)
