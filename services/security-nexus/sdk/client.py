#!/usr/bin/env python3
"""
SYSTEM 4 — SECURITY NEXUS: Authentik SDK Client
Omni Quantum Elite AI Coding System — Security & Identity Layer

Python client for the Authentik API v3.  Provides user, group,
application, session, and audit management.
"""

from datetime import datetime, timedelta, timezone
from typing import Any

import httpx


class AuthentikError(Exception):
    """Raised when an Authentik API call fails."""

    def __init__(self, message: str, status_code: int | None = None, detail: str = ""):
        super().__init__(message)
        self.status_code = status_code
        self.detail = detail


class AuthentikClient:
    """Client for the Authentik REST API v3.

    Args:
        base_url: Authentik base URL (e.g. http://omni-authentik:9000).
        api_token: API token (bootstrap token or user token).
        timeout: HTTP request timeout in seconds.
    """

    def __init__(self, base_url: str, api_token: str, timeout: int = 30):
        self.base_url = base_url.rstrip("/")
        self.api_url = f"{self.base_url}/api/v3"
        self._client = httpx.Client(
            base_url=self.api_url,
            headers={
                "Authorization": f"Bearer {api_token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            timeout=timeout,
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    # ───────────────────────────────────────────────────────────────
    # Internal helpers
    # ───────────────────────────────────────────────────────────────

    def _request(self, method: str, path: str, **kwargs) -> Any:
        resp = self._client.request(method, path, **kwargs)
        if resp.status_code >= 400:
            detail = resp.text[:500]
            raise AuthentikError(
                f"Authentik API error: {method} {path} => {resp.status_code}",
                status_code=resp.status_code,
                detail=detail,
            )
        if resp.status_code == 204 or not resp.content:
            return None
        return resp.json()

    def _paginate(self, path: str, params: dict | None = None) -> list[dict]:
        """Fetch all pages from a paginated endpoint."""
        all_results: list[dict] = []
        page = 1
        while True:
            p = dict(params or {})
            p["page"] = page
            p["page_size"] = 100
            data = self._request("GET", path, params=p)
            results = data.get("results", [])
            all_results.extend(results)
            if not data.get("pagination", {}).get("next"):
                break
            page += 1
        return all_results

    # ───────────────────────────────────────────────────────────────
    # Users
    # ───────────────────────────────────────────────────────────────

    def list_users(
        self,
        search: str | None = None,
        group: str | None = None,
        is_active: bool | None = None,
    ) -> list[dict[str, Any]]:
        """List users with optional filters.

        Args:
            search: Free-text search across name, email, username.
            group: Filter by group name.
            is_active: Filter by active/inactive status.
        """
        params: dict[str, Any] = {}
        if search:
            params["search"] = search
        if group:
            params["groups_by_name"] = group
        if is_active is not None:
            params["is_active"] = str(is_active).lower()
        return self._paginate("/core/users/", params)

    def get_user(self, user_id: int) -> dict[str, Any]:
        """Get a single user by ID."""
        return self._request("GET", f"/core/users/{user_id}/")

    def create_user(
        self,
        email: str,
        name: str,
        group: str | None = None,
        username: str | None = None,
        password: str | None = None,
        is_active: bool = True,
    ) -> dict[str, Any]:
        """Create a new user and optionally add them to a group.

        Args:
            email: User email address.
            name: Full display name.
            group: Group name to add the user to.
            username: Username (defaults to email prefix).
            password: Initial password (optional — user can use SSO).
            is_active: Whether the account is active.
        """
        if not username:
            username = email.split("@")[0]

        payload: dict[str, Any] = {
            "username": username,
            "name": name,
            "email": email,
            "is_active": is_active,
            "attributes": {},
        }
        if password:
            payload["password"] = password

        # Find group PK if specified
        if group:
            groups = self._request("GET", "/core/groups/", params={"name": group})
            group_results = groups.get("results", [])
            if group_results:
                payload["groups"] = [group_results[0]["pk"]]

        return self._request("POST", "/core/users/", json=payload)

    def deactivate_user(self, user_id: int) -> dict[str, Any]:
        """Deactivate a user account."""
        return self._request("PATCH", f"/core/users/{user_id}/", json={"is_active": False})

    # ───────────────────────────────────────────────────────────────
    # Groups
    # ───────────────────────────────────────────────────────────────

    def list_groups(self, search: str | None = None) -> list[dict[str, Any]]:
        """List all groups."""
        params = {}
        if search:
            params["search"] = search
        return self._paginate("/core/groups/", params)

    def get_group(self, group_id: str) -> dict[str, Any]:
        """Get a group by its PK (UUID)."""
        return self._request("GET", f"/core/groups/{group_id}/")

    def create_group(
        self,
        name: str,
        parent: str | None = None,
        is_superuser: bool = False,
    ) -> dict[str, Any]:
        """Create a new group.

        Args:
            name: Group name.
            parent: Parent group PK (for nested groups).
            is_superuser: Whether this is a superuser group.
        """
        payload: dict[str, Any] = {
            "name": name,
            "is_superuser": is_superuser,
        }
        if parent:
            payload["parent"] = parent
        return self._request("POST", "/core/groups/", json=payload)

    def add_user_to_group(self, user_id: int, group_id: str) -> None:
        """Add a user to a group."""
        self._request("POST", f"/core/groups/{group_id}/add_user/", json={"pk": user_id})

    def remove_user_from_group(self, user_id: int, group_id: str) -> None:
        """Remove a user from a group."""
        self._request("POST", f"/core/groups/{group_id}/remove_user/", json={"pk": user_id})

    # ───────────────────────────────────────────────────────────────
    # Applications
    # ───────────────────────────────────────────────────────────────

    def list_applications(self, search: str | None = None) -> list[dict[str, Any]]:
        """List all applications."""
        params = {}
        if search:
            params["search"] = search
        return self._paginate("/core/applications/", params)

    def get_application(self, slug: str) -> dict[str, Any]:
        """Get application by slug."""
        return self._request("GET", f"/core/applications/{slug}/")

    def get_provider_credentials(self, service_name: str) -> dict[str, Any]:
        """Get OAuth2 provider credentials for a service.

        Returns dict with client_id, client_secret (if available),
        redirect_uris, issuer_url, and authorization endpoints.
        """
        provider_name = f"omni-{service_name}-provider"
        providers = self._request("GET", "/providers/oauth2/", params={"name": provider_name})
        results = providers.get("results", [])
        if not results:
            raise AuthentikError(f"Provider not found: {provider_name}")

        provider = results[0]
        return {
            "client_id": provider.get("client_id", ""),
            "redirect_uris": provider.get("redirect_uris", ""),
            "issuer_url": f"{self.base_url}/application/o/omni-{service_name}/",
            "authorize_url": f"{self.base_url}/application/o/authorize/",
            "token_url": f"{self.base_url}/application/o/token/",
            "userinfo_url": f"{self.base_url}/application/o/userinfo/",
            "jwks_url": f"{self.base_url}/application/o/omni-{service_name}/jwks/",
            "end_session_url": f"{self.base_url}/application/o/omni-{service_name}/end-session/",
            "provider_pk": provider["pk"],
        }

    # ───────────────────────────────────────────────────────────────
    # Sessions
    # ───────────────────────────────────────────────────────────────

    def invalidate_sessions(self, user: int | str) -> int:
        """Invalidate all active sessions for a user.

        Args:
            user: User ID (int) or username (str).

        Returns:
            Number of sessions invalidated.
        """
        # Resolve username to ID if needed
        if isinstance(user, str):
            users = self._request("GET", "/core/users/", params={"username": user})
            results = users.get("results", [])
            if not results:
                raise AuthentikError(f"User not found: {user}")
            user_id = results[0]["pk"]
        else:
            user_id = user

        # List sessions for user
        sessions = self._paginate(
            "/core/authenticated_sessions/",
            params={"user": user_id},
        )

        count = 0
        for session in sessions:
            self._request("DELETE", f"/core/authenticated_sessions/{session['uuid']}/")
            count += 1

        return count

    # ───────────────────────────────────────────────────────────────
    # Audit Log
    # ───────────────────────────────────────────────────────────────

    def audit_log(
        self,
        days: int = 30,
        action: str | None = None,
        user: str | None = None,
    ) -> list[dict[str, Any]]:
        """Retrieve audit/event log entries.

        Args:
            days: Number of days to look back (default 30).
            action: Filter by action type (e.g. "login", "authorize_application").
            user: Filter by username.

        Returns:
            List of event log entries sorted newest-first.
        """
        since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        params: dict[str, Any] = {"ordering": "-created", "created__gte": since}
        if action:
            params["action"] = action
        if user:
            params["user__username"] = user

        return self._paginate("/events/events/", params)

    def get_login_events(self, days: int = 7) -> list[dict[str, Any]]:
        """Get all login events for the last N days."""
        return self.audit_log(days=days, action="login")

    def get_failed_logins(self, days: int = 7) -> list[dict[str, Any]]:
        """Get all failed login events for the last N days."""
        return self.audit_log(days=days, action="login_failed")

    # ───────────────────────────────────────────────────────────────
    # Health
    # ───────────────────────────────────────────────────────────────

    def health_check(self) -> dict[str, bool]:
        """Check Authentik health status."""
        try:
            resp = self._client.get(f"{self.base_url}/-/health/live/")
            live = resp.status_code in (200, 204)
        except Exception:
            live = False

        try:
            resp = self._client.get(f"{self.base_url}/-/health/ready/")
            ready = resp.status_code in (200, 204)
        except Exception:
            ready = False

        return {"live": live, "ready": ready}
