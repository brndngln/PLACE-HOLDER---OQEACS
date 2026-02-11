from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from src.models import CodeBiography


class BiographyBuilder:
    def build(self, repo_path: str, file: str, function: str) -> CodeBiography:
        path = Path(repo_path) / file
        text = path.read_text(errors="ignore") if path.exists() else ""
        workarounds = re.findall(r"(hack|workaround|temporary|temp)", text, flags=re.I)
        issues = re.findall(r"#(\d+)", text)
        return CodeBiography(
            function_name=function,
            file_path=file,
            created_date=datetime.utcnow(),
            created_by="unknown",
            total_changes=max(1, text.count(function)),
            linked_issues=[f"#{i}" for i in issues],
            purpose=f"Implements behavior for `{function}`",
            workarounds=sorted(set(workarounds)),
        )
