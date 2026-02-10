"""
VaultClient - Python SDK for HashiCorp Vault (AppRole Auth)

System 2: Cryptographic Fortress

Provides a robust client for interacting with Vault using AppRole authentication.
Features: auto-renew tokens, connection pooling via httpx, retry with exponential
backoff on 5xx errors, and methods for KV, dynamic DB creds, PKI, and Transit.
"""

import httpx
import time
import base64
import logging
import threading
from typing import Any, Optional

logger = logging.getLogger("vault_client")


class VaultError(Exception):
    """Base exception for Vault client errors."""

    def __init__(self, message: str, status_code: int = 0, errors: list | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.errors = errors or []


class VaultAuthError(VaultError):
    """Authentication or authorization failure."""
    pass


class VaultNotFoundError(VaultError):
    """Requested path or resource not found."""
    pass


class VaultClient:
    """
    Vault client using AppRole authentication with httpx connection pooling.

    Args:
        vault_url: Vault server URL.
        role_id: AppRole role ID.
        secret_id: AppRole secret ID.
        timeout: HTTP request timeout in seconds.
        max_retries: Maximum retry attempts on 5xx errors.
        retry_backoff_base: Base seconds for exponential backoff.
        token_renew_buffer: Seconds before expiry to trigger renewal.
    """

    def __init__(
        self,
        vault_url: str = "http://omni-vault:8200",
        role_id: str = "",
        secret_id: str = "",
        timeout: float = 15.0,
        max_retries: int = 3,
        retry_backoff_base: float = 0.5,
        token_renew_buffer: int = 60,
    ):
        self.vault_url = vault_url.rstrip("/")
        self.role_id = role_id
        self.secret_id = secret_id
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_backoff_base = retry_backoff_base
        self.token_renew_buffer = token_renew_buffer

        self._token: str = ""
        self._token_expires: float = 0.0
        self._token_accessor: str = ""
        self._token_renewable: bool = False
        self._lock = threading.Lock()
        self._client: Optional[httpx.Client] = None

    # ------------------------------------------------------------------
    # Context manager for connection pooling
    # ------------------------------------------------------------------
    def __enter__(self) -> "VaultClient":
        self._client = httpx.Client(
            base_url=self.vault_url,
            timeout=self.timeout,
            limits=httpx.Limits(
                max_connections=20,
                max_keepalive_connections=10,
                keepalive_expiry=30.0,
            ),
        )
        self._authenticate()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if self._client:
            self._client.close()
            self._client = None

    # ------------------------------------------------------------------
    # HTTP helpers with retry
    # ------------------------------------------------------------------
    def _get_client(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(
                base_url=self.vault_url,
                timeout=self.timeout,
                limits=httpx.Limits(
                    max_connections=20,
                    max_keepalive_connections=10,
                    keepalive_expiry=30.0,
                ),
            )
        return self._client

    def _headers(self) -> dict[str, str]:
        self._ensure_token()
        return {
            "X-Vault-Token": self._token,
            "Content-Type": "application/json",
        }

    def _get(self, path: str, params: dict | None = None) -> dict:
        return self._request("GET", path, params=params)

    def _post(self, path: str, data: dict | None = None) -> dict:
        return self._request("POST", path, json_data=data)

    def _put(self, path: str, data: dict | None = None) -> dict:
        return self._request("PUT", path, json_data=data)

    def _delete(self, path: str) -> dict:
        return self._request("DELETE", path)

    def _list(self, path: str) -> dict:
        return self._request("LIST", path)

    def _request(
        self,
        method: str,
        path: str,
        params: dict | None = None,
        json_data: dict | None = None,
    ) -> dict:
        client = self._get_client()
        url = f"/v1/{path.lstrip('/')}"
        headers = self._headers()
        last_exception: Optional[Exception] = None

        for attempt in range(self.max_retries + 1):
            try:
                if method == "LIST":
                    response = client.request(
                        "LIST", url, headers=headers, params=params
                    )
                elif method == "GET":
                    response = client.get(url, headers=headers, params=params)
                elif method == "POST":
                    response = client.post(
                        url, headers=headers, json=json_data or {}
                    )
                elif method == "PUT":
                    response = client.put(
                        url, headers=headers, json=json_data or {}
                    )
                elif method == "DELETE":
                    response = client.delete(url, headers=headers)
                else:
                    raise VaultError(f"Unsupported HTTP method: {method}")

                return self._handle_response(response)

            except (httpx.ConnectError, httpx.ReadTimeout, httpx.WriteTimeout) as exc:
                last_exception = exc
                if attempt < self.max_retries:
                    wait = self.retry_backoff_base * (2 ** attempt)
                    logger.warning(
                        "Vault request failed (attempt %d/%d), retrying in %.1fs: %s",
                        attempt + 1,
                        self.max_retries + 1,
                        wait,
                        str(exc),
                    )
                    time.sleep(wait)
                    continue
                raise VaultError(
                    f"Connection failed after {self.max_retries + 1} attempts: {exc}"
                ) from exc

            except VaultError as exc:
                # Retry on 5xx server errors
                if exc.status_code >= 500 and attempt < self.max_retries:
                    wait = self.retry_backoff_base * (2 ** attempt)
                    logger.warning(
                        "Vault 5xx error (attempt %d/%d), retrying in %.1fs: %s",
                        attempt + 1,
                        self.max_retries + 1,
                        wait,
                        str(exc),
                    )
                    time.sleep(wait)
                    last_exception = exc
                    continue
                raise

        raise VaultError(
            f"Request failed after {self.max_retries + 1} attempts"
        ) from last_exception

    def _handle_response(self, response: httpx.Response) -> dict:
        if response.status_code == 204:
            return {}

        if response.status_code == 403:
            raise VaultAuthError(
                f"Permission denied: {response.text}",
                status_code=403,
            )

        if response.status_code == 404:
            raise VaultNotFoundError(
                f"Not found: {response.text}",
                status_code=404,
            )

        if response.status_code >= 400:
            try:
                body = response.json()
                errors = body.get("errors", [])
            except Exception:
                errors = [response.text]
            raise VaultError(
                f"Vault error {response.status_code}: {errors}",
                status_code=response.status_code,
                errors=errors,
            )

        try:
            return response.json()
        except Exception:
            return {}

    # ------------------------------------------------------------------
    # Authentication
    # ------------------------------------------------------------------
    def _authenticate(self) -> None:
        """Authenticate via AppRole and obtain a client token."""
        with self._lock:
            client = self._get_client()
            response = client.post(
                "/v1/auth/approle/login",
                json={
                    "role_id": self.role_id,
                    "secret_id": self.secret_id,
                },
                headers={"Content-Type": "application/json"},
            )

            if response.status_code != 200:
                raise VaultAuthError(
                    f"AppRole authentication failed: {response.text}",
                    status_code=response.status_code,
                )

            body = response.json()
            auth = body.get("auth", {})

            self._token = auth.get("client_token", "")
            self._token_accessor = auth.get("accessor", "")
            self._token_renewable = auth.get("renewable", False)

            lease_duration = auth.get("lease_duration", 3600)
            self._token_expires = time.time() + lease_duration

            logger.info(
                "Authenticated via AppRole (accessor=%s, ttl=%ds)",
                self._token_accessor[:8] + "..." if self._token_accessor else "N/A",
                lease_duration,
            )

    def _ensure_token(self) -> None:
        """Ensure the token is valid; renew or re-authenticate if needed."""
        if not self._token:
            self._authenticate()
            return

        time_remaining = self._token_expires - time.time()

        if time_remaining <= 0:
            logger.info("Token expired, re-authenticating")
            self._authenticate()
            return

        if time_remaining <= self.token_renew_buffer and self._token_renewable:
            self._renew_token()

    def _renew_token(self) -> None:
        """Renew the current token."""
        with self._lock:
            try:
                client = self._get_client()
                response = client.post(
                    "/v1/auth/token/renew-self",
                    headers={
                        "X-Vault-Token": self._token,
                        "Content-Type": "application/json",
                    },
                    json={},
                )

                if response.status_code == 200:
                    body = response.json()
                    auth = body.get("auth", {})
                    lease_duration = auth.get("lease_duration", 3600)
                    self._token_expires = time.time() + lease_duration
                    logger.info("Token renewed (new ttl=%ds)", lease_duration)
                else:
                    logger.warning(
                        "Token renewal failed (HTTP %d), re-authenticating",
                        response.status_code,
                    )
                    self._authenticate()
            except Exception as exc:
                logger.warning("Token renewal error: %s -- re-authenticating", exc)
                self._authenticate()

    # ------------------------------------------------------------------
    # KV v2 Operations
    # ------------------------------------------------------------------
    def get_secret(self, path: str, version: int | None = None) -> dict:
        """
        Read a secret from KV v2 at secret/data/{path}.

        Args:
            path: Secret path (e.g., "gitea/config").
            version: Specific version to read (latest if None).

        Returns:
            The secret data dictionary.
        """
        url = f"secret/data/{path.lstrip('/')}"
        params = {}
        if version is not None:
            params["version"] = str(version)

        response = self._get(url, params=params if params else None)
        data = response.get("data", {})
        return data.get("data", {})

    def list_secrets(self, path: str) -> list[str]:
        """
        List secret keys at the given KV v2 path.

        Args:
            path: Path to list (e.g., "gitea").

        Returns:
            List of key names.
        """
        url = f"secret/metadata/{path.lstrip('/')}"
        try:
            response = self._list(url)
            return response.get("data", {}).get("keys", [])
        except VaultNotFoundError:
            return []

    def rotate_secret(self, path: str, new_value: dict) -> dict:
        """
        Write a new version of a secret to KV v2 (rotation).

        Args:
            path: Secret path (e.g., "gitea/config").
            new_value: New secret data dictionary.

        Returns:
            Write metadata (version, created_time, etc.).
        """
        url = f"secret/data/{path.lstrip('/')}"
        response = self._post(url, data={"data": new_value})
        return response.get("data", {})

    # ------------------------------------------------------------------
    # Dynamic Database Credentials
    # ------------------------------------------------------------------
    def get_dynamic_db_creds(
        self, service: str, role_type: str = "readonly"
    ) -> dict:
        """
        Get dynamic database credentials for a service.

        Args:
            service: Service name (e.g., "gitea", "mattermost").
            role_type: "readonly" or "readwrite".

        Returns:
            Dictionary with 'username', 'password', and lease info.
        """
        valid_types = ("readonly", "readwrite")
        if role_type not in valid_types:
            raise VaultError(
                f"Invalid role_type '{role_type}'. Must be one of: {valid_types}"
            )

        url = f"database/creds/{service}-{role_type}"
        response = self._get(url)

        data = response.get("data", {})
        return {
            "username": data.get("username", ""),
            "password": data.get("password", ""),
            "lease_id": response.get("lease_id", ""),
            "lease_duration": response.get("lease_duration", 0),
            "renewable": response.get("renewable", False),
        }

    # ------------------------------------------------------------------
    # PKI Certificate Issuance
    # ------------------------------------------------------------------
    def issue_cert(
        self,
        service_name: str,
        ttl: str = "24h",
        role: str = "omni-internal",
        domain: str = "omni-quantum.internal",
        alt_names: list[str] | None = None,
    ) -> dict:
        """
        Issue a TLS certificate for a service from the PKI engine.

        Args:
            service_name: Service name (becomes CN prefix).
            ttl: Certificate TTL (e.g., "24h", "72h").
            role: PKI role name.
            domain: Base domain for the CN.
            alt_names: Additional SANs.

        Returns:
            Dictionary with 'certificate', 'private_key', 'ca_chain',
            'serial_number', and 'expiration'.
        """
        common_name = f"{service_name}.{domain}"
        san_list = [common_name]
        if alt_names:
            san_list.extend(alt_names)

        url = f"pki/issue/{role}"
        payload: dict[str, Any] = {
            "common_name": common_name,
            "ttl": ttl,
        }
        if len(san_list) > 1:
            payload["alt_names"] = ",".join(san_list[1:])

        response = self._post(url, data=payload)
        data = response.get("data", {})

        return {
            "certificate": data.get("certificate", ""),
            "private_key": data.get("private_key", ""),
            "private_key_type": data.get("private_key_type", ""),
            "ca_chain": data.get("ca_chain", []),
            "issuing_ca": data.get("issuing_ca", ""),
            "serial_number": data.get("serial_number", ""),
            "expiration": data.get("expiration", 0),
        }

    # ------------------------------------------------------------------
    # Transit Encryption / Decryption
    # ------------------------------------------------------------------
    def encrypt(self, plaintext: str, key_name: str = "omni-transit") -> str:
        """
        Encrypt plaintext using the Transit secrets engine.

        Args:
            plaintext: The plaintext string to encrypt.
            key_name: Transit key name.

        Returns:
            Ciphertext string (vault:v1:...).
        """
        encoded = base64.b64encode(plaintext.encode("utf-8")).decode("utf-8")
        url = f"transit/encrypt/{key_name}"
        response = self._post(url, data={"plaintext": encoded})
        return response.get("data", {}).get("ciphertext", "")

    def decrypt(self, ciphertext: str, key_name: str = "omni-transit") -> str:
        """
        Decrypt ciphertext using the Transit secrets engine.

        Args:
            ciphertext: The Vault ciphertext string (vault:v1:...).
            key_name: Transit key name.

        Returns:
            Decrypted plaintext string.
        """
        url = f"transit/decrypt/{key_name}"
        response = self._post(url, data={"ciphertext": ciphertext})
        encoded = response.get("data", {}).get("plaintext", "")
        if not encoded:
            return ""
        return base64.b64decode(encoded).decode("utf-8")

    # ------------------------------------------------------------------
    # Lease Management
    # ------------------------------------------------------------------
    def renew_lease(self, lease_id: str, increment: int = 3600) -> dict:
        """
        Renew a Vault lease.

        Args:
            lease_id: The lease ID to renew.
            increment: Requested renewal duration in seconds.

        Returns:
            Lease renewal response data.
        """
        response = self._put(
            "sys/leases/renew",
            data={"lease_id": lease_id, "increment": increment},
        )
        return response

    def revoke_lease(self, lease_id: str) -> None:
        """
        Revoke a Vault lease.

        Args:
            lease_id: The lease ID to revoke.
        """
        self._put("sys/leases/revoke", data={"lease_id": lease_id})

    # ------------------------------------------------------------------
    # Health Check
    # ------------------------------------------------------------------
    def health(self) -> dict:
        """
        Check Vault health status (does not require authentication).

        Returns:
            Health status dictionary.
        """
        client = self._get_client()
        response = client.get(
            "/v1/sys/health",
            params={
                "standbyok": "true",
                "sealedcode": "200",
                "uninitcode": "200",
            },
        )
        try:
            return response.json()
        except Exception:
            return {"status_code": response.status_code}

    # ------------------------------------------------------------------
    # Token Info
    # ------------------------------------------------------------------
    def token_info(self) -> dict:
        """
        Look up the current token's metadata.

        Returns:
            Token metadata dictionary.
        """
        response = self._get("auth/token/lookup-self")
        return response.get("data", {})

    # ------------------------------------------------------------------
    # Close
    # ------------------------------------------------------------------
    def close(self) -> None:
        """Close the underlying HTTP client."""
        if self._client:
            self._client.close()
            self._client = None
