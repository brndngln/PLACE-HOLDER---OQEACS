from __future__ import annotations

import httpx

from src.models import GenerateRequest, ReviewRequest


class CodeClient:
    async def generate(self, request: GenerateRequest) -> str:
        if len(request.description) > 120:
            async with httpx.AsyncClient(timeout=10.0) as client:
                try:
                    r = await client.post("http://localhost:9650/api/v1/debate", json={"task_description": request.description, "language": request.language})
                    if r.status_code == 200:
                        return str(r.json().get("final_code", ""))
                except Exception:
                    pass
        return f"# Generated {request.language} code for: {request.description}\n"

    async def review(self, request: ReviewRequest) -> dict:
        async with httpx.AsyncClient(timeout=5.0) as client:
            try:
                with open(request.file_path, "r", encoding="utf-8") as f:
                    code = f.read()
                r = await client.post("http://localhost:9650/api/v1/review", json={"code": code, "language": "python", "focus_areas": request.focus_areas})
                if r.status_code == 200:
                    return r.json()
            except Exception:
                pass
        return {"reviews": {}, "overall_score": 0.0}

    async def test(self, file_path: str) -> dict:
        return {"file": file_path, "status": "queued", "target": "system-60"}

    async def debug(self, error: str) -> dict:
        return {"error": error, "suggestion": "Check system-57 error pattern intelligence"}
