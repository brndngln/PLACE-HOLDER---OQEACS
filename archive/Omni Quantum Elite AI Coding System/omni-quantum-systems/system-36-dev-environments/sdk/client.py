"""
Omni Quantum Elite — Dev Environments SDK
Client for Coder workspace management.
"""

import httpx
from datetime import datetime, timezone


class DevEnvironmentClient:
    """Client for System 36 Dev Environments (Coder + Code Server)."""

    def __init__(
        self,
        coder_url: str = "http://omni-coder:7080",
        code_server_url: str = "http://omni-code-server:8443",
        coder_token: str = "",
        timeout: float = 30.0,
    ):
        self.coder_url = coder_url
        self.code_server_url = code_server_url
        self.coder_token = coder_token
        self.timeout = timeout

    def _headers(self) -> dict:
        h = {"Content-Type": "application/json"}
        if self.coder_token:
            h["Coder-Session-Token"] = self.coder_token
        return h

    def health(self) -> bool:
        try:
            with httpx.Client(timeout=5) as c:
                resp = c.get(f"{self.coder_url}/api/v2/buildinfo")
                return resp.status_code == 200
        except Exception:
            return False

    def list_workspaces(self) -> list[dict]:
        """List all workspaces."""
        with httpx.Client(timeout=self.timeout) as c:
            resp = c.get(f"{self.coder_url}/api/v2/workspaces", headers=self._headers())
            resp.raise_for_status()
            return resp.json().get("workspaces", [])

    def create_workspace(self, name: str, template: str = "omni-workspace", params: dict | None = None) -> dict:
        """Create a new workspace."""
        payload = {"name": name, "template_name": template}
        if params:
            payload["rich_parameter_values"] = [{"name": k, "value": v} for k, v in params.items()]
        with httpx.Client(timeout=self.timeout) as c:
            resp = c.post(f"{self.coder_url}/api/v2/organizations/default/workspaces", json=payload, headers=self._headers())
            resp.raise_for_status()
            return resp.json()

    def start_workspace(self, workspace_id: str) -> dict:
        """Start a stopped workspace."""
        with httpx.Client(timeout=self.timeout) as c:
            resp = c.put(
                f"{self.coder_url}/api/v2/workspaces/{workspace_id}/builds",
                json={"transition": "start"},
                headers=self._headers(),
            )
            resp.raise_for_status()
            return resp.json()

    def stop_workspace(self, workspace_id: str) -> dict:
        """Stop a running workspace."""
        with httpx.Client(timeout=self.timeout) as c:
            resp = c.put(
                f"{self.coder_url}/api/v2/workspaces/{workspace_id}/builds",
                json={"transition": "stop"},
                headers=self._headers(),
            )
            resp.raise_for_status()
            return resp.json()

    def delete_workspace(self, workspace_id: str) -> dict:
        """Delete a workspace."""
        with httpx.Client(timeout=self.timeout) as c:
            resp = c.put(
                f"{self.coder_url}/api/v2/workspaces/{workspace_id}/builds",
                json={"transition": "delete"},
                headers=self._headers(),
            )
            resp.raise_for_status()
            return resp.json()

    def list_templates(self) -> list[dict]:
        """List available workspace templates."""
        with httpx.Client(timeout=self.timeout) as c:
            resp = c.get(f"{self.coder_url}/api/v2/organizations/default/templates", headers=self._headers())
            resp.raise_for_status()
            return resp.json()

    def get_build_info(self) -> dict:
        """Get Coder build info."""
        with httpx.Client(timeout=self.timeout) as c:
            resp = c.get(f"{self.coder_url}/api/v2/buildinfo")
            resp.raise_for_status()
            return resp.json()
