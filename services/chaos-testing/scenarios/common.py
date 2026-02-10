from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

import httpx

TOXI_URL = os.getenv("TOXI_URL", "http://omni-toxiproxy:8474")
MM_WEBHOOK = os.getenv("MM_WEBHOOK", "http://omni-mattermost-webhook:8066/hooks/builds")


def toxiproxy_request(method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    resp = httpx.request(method, f"{TOXI_URL}{path}", json=payload, timeout=30.0)
    resp.raise_for_status()
    if resp.text:
        return resp.json()
    return {}


def add_toxic(proxy: str, name: str, toxic_type: str, attributes: dict[str, Any]) -> dict[str, Any]:
    return toxiproxy_request("POST", f"/proxies/{proxy}/toxics", {"name": name, "type": toxic_type, "stream": "downstream", "attributes": attributes})


def remove_toxic(proxy: str, name: str) -> None:
    try:
      toxiproxy_request("DELETE", f"/proxies/{proxy}/toxics/{name}")
    except Exception:
      pass


def post_mm(text: str) -> None:
    try:
        httpx.post(MM_WEBHOOK, json={"text": text}, timeout=10.0)
    except Exception:
        pass


def write_report(report_dir: str, filename: str, payload: dict[str, Any]) -> Path:
    p = Path(report_dir)
    p.mkdir(parents=True, exist_ok=True)
    out = p / filename
    out.write_text(json.dumps(payload, indent=2))
    return out


def timed_probe(url: str) -> dict[str, Any]:
    start = time.perf_counter()
    try:
        r = httpx.get(url, timeout=20.0)
        return {"ok": r.status_code < 500, "status_code": r.status_code, "elapsed_ms": int((time.perf_counter() - start) * 1000)}
    except Exception as exc:
        return {"ok": False, "error": str(exc), "elapsed_ms": int((time.perf_counter() - start) * 1000)}
