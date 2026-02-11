#!/usr/bin/env python3
"""
SYSTEM 4 — SECURITY NEXUS: Authentik Initialization Script
Omni Quantum Elite AI Coding System — Security & Identity Layer

Sets up Authentik as the central SSO/identity provider:
- OAuth2/OIDC providers for all platform services
- Vault-backed credential storage
- RBAC groups and policies
- MFA enforcement
- Traefik forward-auth outpost
"""

import os
import secrets
import string
import sys
import time
from typing import Any

import httpx
import hvac

# ───────────────────────────────────────────────────────────────────────
# Configuration
# ───────────────────────────────────────────────────────────────────────

AUTHENTIK_URL = os.getenv("AUTHENTIK_URL", "http://omni-authentik:9000")
AUTHENTIK_API = f"{AUTHENTIK_URL}/api/v3"
AUTHENTIK_TOKEN = os.getenv("AUTHENTIK_BOOTSTRAP_TOKEN", "")
VAULT_ADDR = os.getenv("VAULT_ADDR", "http://omni-vault:8200")
VAULT_TOKEN = os.getenv("VAULT_TOKEN", "")
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "90"))
RETRY_INTERVAL = int(os.getenv("RETRY_INTERVAL", "5"))

# ───────────────────────────────────────────────────────────────────────
# Service OAuth Definitions
# ───────────────────────────────────────────────────────────────────────

OAUTH_SERVICES: list[dict[str, Any]] = [
    {
        "name": "gitea",
        "display": "Gitea",
        "redirect_uris": "http://omni-gitea:3000/user/oauth2/authentik/callback",
        "launch_url": "http://omni-gitea:3000/",
        "scopes": "openid profile email",
        "groups": ["omni-admins", "omni-developers"],
    },
    {
        "name": "grafana",
        "display": "Grafana",
        "redirect_uris": "http://omni-grafana:3000/login/generic_oauth",
        "launch_url": "http://omni-grafana:3000/",
        "scopes": "openid profile email",
        "groups": ["omni-admins", "omni-operators", "omni-viewers"],
    },
    {
        "name": "mattermost",
        "display": "Mattermost",
        "redirect_uris": "http://omni-mattermost:8065/signup/gitlab/complete",
        "launch_url": "http://omni-mattermost:8065/",
        "scopes": "openid profile email",
        "groups": ["omni-admins", "omni-developers", "omni-operators"],
    },
    {
        "name": "portainer",
        "display": "Portainer",
        "redirect_uris": "http://omni-portainer:9000",
        "launch_url": "http://omni-portainer:9000/",
        "scopes": "openid profile email",
        "groups": ["omni-admins", "omni-operators"],
    },
    {
        "name": "plane",
        "display": "Plane",
        "redirect_uris": "https://notion.so/auth/callback",
        "launch_url": "https://notion.so/",
        "scopes": "openid profile email",
        "groups": ["omni-admins", "omni-developers", "omni-clients"],
    },
    {
        "name": "superset",
        "display": "Superset",
        "redirect_uris": "http://omni-superset:8088/oauth-authorized/authentik",
        "launch_url": "http://omni-superset:8088/",
        "scopes": "openid profile email",
        "groups": ["omni-admins", "omni-operators", "omni-viewers"],
    },
    {
        "name": "wikijs",
        "display": "Wiki.js",
        "redirect_uris": "https://notion.so",
        "launch_url": "https://notion.so/",
        "scopes": "openid profile email",
        "groups": ["omni-admins", "omni-developers"],
    },
    {
        "name": "langfuse",
        "display": "Langfuse",
        "redirect_uris": "http://omni-langfuse:3000/api/auth/callback/custom",
        "launch_url": "http://omni-langfuse:3000/",
        "scopes": "openid profile email",
        "groups": ["omni-admins", "omni-developers"],
    },
    {
        "name": "n8n",
        "display": "n8n",
        "redirect_uris": "http://omni-n8n:5678/rest/oauth2-credential/callback",
        "launch_url": "http://omni-n8n:5678/",
        "scopes": "openid profile email",
        "groups": ["omni-admins", "omni-developers", "omni-operators"],
    },
    {
        "name": "coolify",
        "display": "Coolify",
        "redirect_uris": "http://omni-coolify:8000/auth/callback",
        "launch_url": "http://omni-coolify:8000/",
        "scopes": "openid profile email",
        "groups": ["omni-admins", "omni-operators"],
    },
    {
        "name": "woodpecker",
        "display": "Woodpecker CI",
        "redirect_uris": "http://omni-woodpecker-server:8000/authorize",
        "launch_url": "http://omni-woodpecker-server:8000/",
        "scopes": "openid profile email",
        "groups": ["omni-admins", "omni-developers"],
    },
    {
        "name": "orchestrator",
        "display": "Master Orchestrator",
        "redirect_uris": "http://omni-orchestrator:9501/auth/callback",
        "launch_url": "http://omni-orchestrator:9501/",
        "scopes": "openid profile email",
        "groups": ["omni-admins", "omni-developers"],
    },
]

# Traefik dashboard uses forward-auth, not redirect — handled separately
FORWARD_AUTH_SERVICES: list[dict[str, str]] = [
    {
        "name": "traefik-dashboard",
        "display": "Traefik Dashboard",
        "launch_url": "http://omni-traefik:8080/dashboard/",
    },
]

# ───────────────────────────────────────────────────────────────────────
# Group and RBAC Definitions
# ───────────────────────────────────────────────────────────────────────

GROUP_DEFINITIONS: list[dict[str, Any]] = [
    {
        "name": "omni-admins",
        "is_superuser": True,
        "description": "Full access to all platform services and admin panels",
    },
    {
        "name": "omni-developers",
        "is_superuser": False,
        "description": "Access to code, pipeline, AI, and knowledge systems",
    },
    {
        "name": "omni-operators",
        "is_superuser": False,
        "description": "Access to monitoring, logs, backups, and infrastructure tools",
    },
    {
        "name": "omni-viewers",
        "is_superuser": False,
        "description": "Read-only dashboards and status pages only",
    },
    {
        "name": "omni-clients",
        "is_superuser": False,
        "description": "External client access — project views, status page, scheduling",
    },
]

# ───────────────────────────────────────────────────────────────────────
# HTTP Client Helpers
# ───────────────────────────────────────────────────────────────────────


def api_headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {AUTHENTIK_TOKEN}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def api_get(client: httpx.Client, path: str, params: dict | None = None) -> Any:
    resp = client.get(f"{AUTHENTIK_API}{path}", headers=api_headers(), params=params)
    resp.raise_for_status()
    return resp.json()


def api_post(client: httpx.Client, path: str, data: dict) -> Any:
    resp = client.post(f"{AUTHENTIK_API}{path}", headers=api_headers(), json=data)
    if resp.status_code == 400:
        error_data = resp.json()
        # Check if it's a duplicate name error
        if any("already exists" in str(v) for v in error_data.values()):
            return None
        print(f"  API error on POST {path}: {resp.status_code} {resp.text}", file=sys.stderr)
        return None
    resp.raise_for_status()
    return resp.json()


def api_patch(client: httpx.Client, path: str, data: dict) -> Any:
    resp = client.patch(f"{AUTHENTIK_API}{path}", headers=api_headers(), json=data)
    resp.raise_for_status()
    return resp.json()


def generate_client_secret(length: int = 64) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def generate_client_id(service_name: str) -> str:
    random_suffix = secrets.token_hex(12)
    return f"omni-{service_name}-{random_suffix}"


# ───────────────────────────────────────────────────────────────────────
# Step 1: Wait for Authentik
# ───────────────────────────────────────────────────────────────────────


def wait_for_authentik() -> None:
    print(f"Waiting for Authentik at {AUTHENTIK_URL} ...")
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = httpx.get(f"{AUTHENTIK_URL}/-/health/live/", timeout=5)
            if resp.status_code == 204 or resp.status_code == 200:
                print(f"  Authentik is healthy (attempt {attempt})")
                return
        except (httpx.ConnectError, httpx.TimeoutException):
            pass
        print(f"  attempt {attempt}/{MAX_RETRIES} — retrying in {RETRY_INTERVAL}s")
        time.sleep(RETRY_INTERVAL)
    print("ERROR: Authentik did not become healthy in time", file=sys.stderr)
    sys.exit(1)


# ───────────────────────────────────────────────────────────────────────
# Step 2: Create Groups
# ───────────────────────────────────────────────────────────────────────


def create_groups(client: httpx.Client) -> dict[str, str]:
    """Create RBAC groups, return mapping of name -> pk."""
    print("\n--- Creating Groups ---")
    group_map: dict[str, str] = {}

    for gdef in GROUP_DEFINITIONS:
        name = gdef["name"]
        print(f"  Creating group: {name}")

        result = api_post(client, "/core/groups/", {
            "name": name,
            "is_superuser": gdef["is_superuser"],
            "attributes": {
                "description": gdef["description"],
                "omni_quantum": True,
            },
        })

        if result is None:
            # Already exists — find it
            existing = api_get(client, "/core/groups/", params={"name": name})
            results = existing.get("results", [])
            if results:
                group_map[name] = results[0]["pk"]
                print(f"    Already exists (pk: {group_map[name]})")
            else:
                print(f"    WARNING: Could not create or find group {name}")
        else:
            group_map[name] = result["pk"]
            print(f"    Created (pk: {group_map[name]})")

    return group_map


# ───────────────────────────────────────────────────────────────────────
# Step 3: Create OAuth2 Providers + Applications
# ───────────────────────────────────────────────────────────────────────


def get_or_create_certificate_keypair(client: httpx.Client) -> str:
    """Get or create a signing certificate for OIDC tokens."""
    existing = api_get(client, "/crypto/certificatekeypairs/", params={"name": "omni-quantum-signing"})
    results = existing.get("results", [])
    if results:
        return results[0]["pk"]

    result = api_post(client, "/crypto/certificatekeypairs/generate/", {
        "name": "omni-quantum-signing",
        "common_name": "omni-quantum-signing",
        "validity_days": 3650,
        "key_size": 4096,
    })
    if result:
        print("  Created OIDC signing keypair")
        return result["pk"]

    # Fallback: use any existing keypair
    all_kp = api_get(client, "/crypto/certificatekeypairs/")
    if all_kp.get("results"):
        return all_kp["results"][0]["pk"]
    return ""


def get_or_create_scope_mappings(client: httpx.Client) -> list[str]:
    """Get the default OIDC scope mapping PKs."""
    mappings = api_get(client, "/propertymappings/all/", params={"managed__icontains": "goauthentik.io/providers/oauth2/scope-"})
    pks = [m["pk"] for m in mappings.get("results", [])]
    return pks


def create_oauth_provider(
    client: httpx.Client,
    service: dict[str, Any],
    signing_key_pk: str,
    scope_mapping_pks: list[str],
) -> dict[str, Any] | None:
    """Create an OAuth2 provider for a service."""
    name = service["name"]
    provider_name = f"omni-{name}-provider"
    client_id = generate_client_id(name)
    client_secret = generate_client_secret()

    print(f"  Creating OAuth2 provider: {provider_name}")

    result = api_post(client, "/providers/oauth2/", {
        "name": provider_name,
        "authorization_flow": None,  # Will be set after we find the default flow
        "client_type": "confidential",
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uris": service["redirect_uris"],
        "signing_key": signing_key_pk if signing_key_pk else None,
        "property_mappings": scope_mapping_pks,
        "access_code_validity": "minutes=1",
        "access_token_validity": "hours=1",
        "refresh_token_validity": "days=30",
        "include_claims_in_id_token": True,
        "sub_mode": "hashed_user_id",
        "issuer_mode": "per_provider",
    })

    if result is None:
        # Provider may already exist — look it up
        existing = api_get(client, "/providers/oauth2/", params={"name": provider_name})
        providers = existing.get("results", [])
        if providers:
            p = providers[0]
            print(f"    Already exists (pk: {p['pk']})")
            return {
                "pk": p["pk"],
                "client_id": p.get("client_id", client_id),
                "client_secret": client_secret,
                "name": provider_name,
            }
        return None

    return {
        "pk": result["pk"],
        "client_id": client_id,
        "client_secret": client_secret,
        "name": provider_name,
    }


def get_default_authorization_flow(client: httpx.Client) -> str:
    """Find the default implicit-consent authorization flow."""
    flows = api_get(client, "/flows/instances/", params={
        "designation": "authorization",
        "ordering": "slug",
    })
    for flow in flows.get("results", []):
        slug = flow.get("slug", "")
        if "implicit" in slug or "default" in slug:
            return flow["pk"]
    # Return the first authorization flow
    results = flows.get("results", [])
    return results[0]["pk"] if results else ""


def set_provider_flow(client: httpx.Client, provider_pk: int, flow_pk: str) -> None:
    """Patch the provider to set the authorization flow."""
    if flow_pk:
        api_patch(client, f"/providers/oauth2/{provider_pk}/", {
            "authorization_flow": flow_pk,
        })


def create_application(
    client: httpx.Client,
    service: dict[str, Any],
    provider_pk: int,
    group_map: dict[str, str],
) -> dict[str, Any] | None:
    """Create an Authentik application tied to a provider."""
    name = service["name"]
    app_slug = f"omni-{name}"

    print(f"  Creating application: {app_slug}")

    result = api_post(client, "/core/applications/", {
        "name": service["display"],
        "slug": app_slug,
        "provider": provider_pk,
        "meta_launch_url": service.get("launch_url", ""),
        "meta_description": f"Omni Quantum — {service['display']} SSO",
        "policy_engine_mode": "any",
        "open_in_new_tab": True,
    })

    if result is None:
        existing = api_get(client, "/core/applications/", params={"slug": app_slug})
        results = existing.get("results", [])
        if results:
            print(f"    Already exists (slug: {app_slug})")
            return results[0]
        return None

    print(f"    Created (slug: {app_slug})")
    return result


def bind_groups_to_application(
    client: httpx.Client,
    app_slug: str,
    allowed_groups: list[str],
    group_map: dict[str, str],
) -> None:
    """Create policy bindings to restrict application access to specific groups."""
    for group_name in allowed_groups:
        group_pk = group_map.get(group_name)
        if not group_pk:
            continue

        # Create a group-membership policy
        policy_name = f"access-{app_slug}-{group_name}"
        policy = api_post(client, "/policies/expression/", {
            "name": policy_name,
            "expression": f'return ak_is_group_member(request.user, name="{group_name}")',
            "execution_logging": False,
        })

        if policy is None:
            # Find existing policy
            existing = api_get(client, "/policies/all/", params={"name": policy_name})
            results = existing.get("results", [])
            if results:
                policy = results[0]
            else:
                continue

        # Bind policy to application
        api_post(client, "/policies/bindings/", {
            "policy": policy["pk"],
            "target": app_slug,
            "negate": False,
            "enabled": True,
            "order": 0,
            "timeout": 30,
        })

    print(f"    Bound {len(allowed_groups)} group policies to {app_slug}")


# ───────────────────────────────────────────────────────────────────────
# Step 4: Vault Credential Storage
# ───────────────────────────────────────────────────────────────────────


def store_credentials_in_vault(
    vault_client: hvac.Client,
    service_name: str,
    client_id: str,
    client_secret: str,
) -> None:
    """Store OAuth client credentials in Vault KV v2."""
    path = f"authentik/clients/{service_name}"
    vault_client.secrets.kv.v2.create_or_update_secret(
        path=path,
        secret={
            "client_id": client_id,
            "client_secret": client_secret,
            "issuer_url": f"{AUTHENTIK_URL}/application/o/omni-{service_name}/",
            "authorize_url": f"{AUTHENTIK_URL}/application/o/authorize/",
            "token_url": f"{AUTHENTIK_URL}/application/o/token/",
            "userinfo_url": f"{AUTHENTIK_URL}/application/o/userinfo/",
            "jwks_url": f"{AUTHENTIK_URL}/application/o/omni-{service_name}/jwks/",
            "end_session_url": f"{AUTHENTIK_URL}/application/o/omni-{service_name}/end-session/",
            "service": service_name,
        },
        mount_point="secret",
    )
    print(f"    Stored credentials in Vault: secret/data/{path}")


# ───────────────────────────────────────────────────────────────────────
# Step 5: MFA Enforcement
# ───────────────────────────────────────────────────────────────────────


def configure_mfa(client: httpx.Client, group_map: dict[str, str]) -> None:
    """Configure TOTP MFA enforcement for admin and operator groups."""
    print("\n--- Configuring MFA ---")

    # Create a TOTP setup stage
    totp_stage = api_post(client, "/stages/authenticator/totp/", {
        "name": "omni-totp-setup",
        "friendly_name": "Omni Quantum TOTP Setup",
        "digits": 6,
    })
    if totp_stage is None:
        existing = api_get(client, "/stages/authenticator/totp/", params={"name": "omni-totp-setup"})
        results = existing.get("results", [])
        totp_stage = results[0] if results else None

    if not totp_stage:
        print("  WARNING: Could not create TOTP stage")
        return

    # Create an authenticator validation stage
    validation_stage = api_post(client, "/stages/authenticator/validate/", {
        "name": "omni-mfa-validation",
        "device_classes": ["totp", "webauthn", "static"],
        "not_configured_action": "configure",
    })
    if validation_stage is None:
        existing = api_get(client, "/stages/authenticator/validate/", params={"name": "omni-mfa-validation"})
        results = existing.get("results", [])
        validation_stage = results[0] if results else None

    if not validation_stage:
        print("  WARNING: Could not create validation stage")
        return

    # Create a policy that requires MFA for admin/operator groups
    mfa_policy = api_post(client, "/policies/expression/", {
        "name": "omni-require-mfa",
        "expression": (
            'groups = ["omni-admins", "omni-operators"]\n'
            "return any(ak_is_group_member(request.user, name=g) for g in groups)"
        ),
        "execution_logging": True,
    })
    if mfa_policy is None:
        existing = api_get(client, "/policies/all/", params={"name": "omni-require-mfa"})
        results = existing.get("results", [])
        mfa_policy = results[0] if results else None

    print("  TOTP MFA configured for admin and operator groups")


# ───────────────────────────────────────────────────────────────────────
# Step 6: Traefik Forward-Auth Outpost
# ───────────────────────────────────────────────────────────────────────


def create_forward_auth_outpost(client: httpx.Client) -> None:
    """Create a proxy outpost for Traefik forward-auth integration."""
    print("\n--- Creating Forward-Auth Outpost ---")

    # Create a proxy provider for forward-auth
    provider = api_post(client, "/providers/proxy/", {
        "name": "omni-traefik-forward-auth-provider",
        "mode": "forward_single",
        "authorization_flow": get_default_authorization_flow(client),
        "external_host": "https://auth.omni-quantum.internal",
        "internal_host": "http://omni-authentik:9000",
        "internal_host_ssl_validation": False,
        "access_token_validity": "hours=1",
    })

    if provider is None:
        existing = api_get(client, "/providers/proxy/", params={"name": "omni-traefik-forward-auth-provider"})
        results = existing.get("results", [])
        provider = results[0] if results else None

    if not provider:
        print("  WARNING: Could not create forward-auth provider")
        return

    # Create the application for the forward-auth
    app = api_post(client, "/core/applications/", {
        "name": "Traefik Dashboard",
        "slug": "omni-traefik-dashboard",
        "provider": provider["pk"],
        "meta_launch_url": "http://omni-traefik:8080/dashboard/",
        "meta_description": "Omni Quantum — Traefik dashboard protected by forward-auth",
    })

    if app is None:
        print("  Forward-auth application already exists")

    # Create embedded outpost
    outpost = api_post(client, "/outposts/instances/", {
        "name": "omni-traefik-outpost",
        "type": "proxy",
        "protocol_providers": [provider["pk"]],
        "service_connection": None,  # embedded
        "config": {
            "authentik_host": f"{AUTHENTIK_URL}/",
            "authentik_host_insecure": True,
            "authentik_host_browser": "https://auth.omni-quantum.internal",
            "log_level": "info",
            "docker_labels": {
                "traefik.enable": "true",
                "traefik.http.middlewares.authentik.forwardauth.address": "http://omni-authentik:9000/outpost.goauthentik.io/auth/traefik",
                "traefik.http.middlewares.authentik.forwardauth.trustForwardHeader": "true",
                "traefik.http.middlewares.authentik.forwardauth.authResponseHeaders": "X-authentik-username,X-authentik-groups,X-authentik-email,X-authentik-name,X-authentik-uid,X-authentik-jwt,X-authentik-meta-jwks,X-authentik-meta-outpost,X-authentik-meta-provider,X-authentik-meta-app,X-authentik-meta-version",
            },
        },
    })

    if outpost:
        print(f"  Forward-auth outpost created (pk: {outpost['pk']})")
    else:
        print("  Forward-auth outpost already exists or could not be created")


# ───────────────────────────────────────────────────────────────────────
# Main
# ───────────────────────────────────────────────────────────────────────


def main() -> None:
    print("=" * 72)
    print("SYSTEM 4 — SECURITY NEXUS: Authentik Initialization")
    print("=" * 72)

    if not AUTHENTIK_TOKEN:
        print("ERROR: AUTHENTIK_BOOTSTRAP_TOKEN must be set", file=sys.stderr)
        sys.exit(1)

    # Step 1: Wait for health
    wait_for_authentik()

    # Step 2: Connect to Vault
    print("\nConnecting to Vault ...")
    vault_client = hvac.Client(url=VAULT_ADDR, token=VAULT_TOKEN)
    if not vault_client.is_authenticated():
        print("ERROR: Vault authentication failed", file=sys.stderr)
        sys.exit(1)
    print("  Vault connection established")

    client = httpx.Client(timeout=30)

    # Step 3: Create groups
    group_map = create_groups(client)

    # Step 4: Get signing key and scope mappings
    print("\n--- Preparing OAuth2 Infrastructure ---")
    signing_key_pk = get_or_create_certificate_keypair(client)
    scope_mapping_pks = get_or_create_scope_mappings(client)
    auth_flow_pk = get_default_authorization_flow(client)
    print(f"  Signing key: {signing_key_pk[:8]}...")
    print(f"  Scope mappings: {len(scope_mapping_pks)} found")
    print(f"  Authorization flow: {auth_flow_pk[:8]}..." if auth_flow_pk else "  WARNING: No auth flow")

    # Step 5: Create providers, applications, and store credentials
    print("\n--- Creating OAuth2 Providers & Applications ---")
    credentials_created = 0

    for service in OAUTH_SERVICES:
        provider = create_oauth_provider(client, service, signing_key_pk, scope_mapping_pks)
        if not provider:
            print(f"  WARNING: Skipping {service['name']} — provider creation failed")
            continue

        # Set the authorization flow
        set_provider_flow(client, provider["pk"], auth_flow_pk)

        # Create application
        app = create_application(client, service, provider["pk"], group_map)
        if not app:
            continue

        # Bind groups
        bind_groups_to_application(
            client,
            f"omni-{service['name']}",
            service.get("groups", []),
            group_map,
        )

        # Store credentials in Vault
        store_credentials_in_vault(
            vault_client,
            service["name"],
            provider["client_id"],
            provider["client_secret"],
        )
        credentials_created += 1

    # Step 6: MFA
    configure_mfa(client, group_map)

    # Step 7: Forward-auth outpost
    create_forward_auth_outpost(client)

    # Summary
    print("\n" + "=" * 72)
    print("Authentik initialization complete!")
    print(f"  Groups created: {len(group_map)}")
    print(f"  OAuth providers: {credentials_created}")
    print(f"  Vault paths: secret/data/authentik/clients/{{service-name}}")
    print(f"  MFA: TOTP required for omni-admins, omni-operators")
    print(f"  Forward-auth: Traefik outpost configured")
    print("=" * 72)

    client.close()


if __name__ == "__main__":
    main()
