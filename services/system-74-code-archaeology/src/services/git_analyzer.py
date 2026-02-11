from __future__ import annotations

from datetime import datetime
from pathlib import Path

from src.models import CodeHistory, HistoryEntry


class GitAnalyzer:
    def get_function_history(self, repo_path: str, file: str, function: str) -> CodeHistory:
        path = Path(repo_path) / file
        if not path.exists():
            return CodeHistory(file_path=file, function_name=function, history=[])
        text = path.read_text(errors="ignore")
        entries = [
            HistoryEntry(
                commit_hash="local-working-tree",
                author="unknown",
                date=datetime.utcnow(),
                change_type="inspect",
                message=f"Observed function {function}",
                diff_summary=text[:200],
            )
        ]
        return CodeHistory(file_path=file, function_name=function, history=entries)
