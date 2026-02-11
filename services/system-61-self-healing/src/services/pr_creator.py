from __future__ import annotations

import hashlib


class PRCreator:
    def create_pr(self, fix: str, error_message: str) -> str:
        token = hashlib.sha1((fix + error_message).encode()).hexdigest()[:10]
        return f"https://gitea.local/omni/auto-healing/pulls/{token}"
