#!/usr/bin/env python3
import os
import json
import subprocess
import time

import httpx

SUPERSET_URL = os.getenv("SUPERSET_URL", "http://omni-superset:8088")
SUPERSET_ADMIN_PW = os.getenv("SUPERSET_ADMIN_PW", "admin")
PG_PW = os.getenv("PG_PW", "")
OIDC_CLIENT_ID = subprocess.check_output(
    ["vault", "kv", "get", "-field=client_id", "secret/authentik/superset"]
).decode().strip()
OIDC_CLIENT_SECRET = subprocess.check_output(
    ["vault", "kv", "get", "-field=client_secret", "secret/authentik/superset"]
).decode().strip()
MM_WEBHOOK = "http://omni-mattermost-webhook:8066"

DASHBOARD_DIR = os.path.join(os.path.dirname(__file__), "..", "dashboards")


def wait_for_health():
    while True:
        try:
            r = httpx.get(f"{SUPERSET_URL}/health", timeout=5)
            if r.status_code == 200:
                return
        except httpx.RequestError:
            pass
        time.sleep(3)


def notify_mm(channel: str, text: str):
    httpx.post(MM_WEBHOOK, json={"channel": channel, "text": text})


def run_cli(cmd: str):
    subprocess.run(cmd, shell=True, check=True)


def get_access_token() -> str:
    r = httpx.post(
        f"{SUPERSET_URL}/api/v1/security/login",
        json={"username": "admin", "password": SUPERSET_ADMIN_PW, "provider": "db"},
    )
    r.raise_for_status()
    return r.json()["access_token"]


def main():
    wait_for_health()

    # 1. Create admin user
    run_cli(
        f"superset fab create-admin "
        f"--username admin --firstname Admin --lastname User "
        f"--email admin@omni-quantum.local --password {SUPERSET_ADMIN_PW}"
    )

    # 2. Init DB
    run_cli("superset db upgrade")
    run_cli("superset init")

    # 3. Write Authentik OAuth config
    config_path = "/app/superset_config_oauth.py"
    oauth_config = f"""
from flask_appbuilder.security.manager import AUTH_OAUTH
AUTH_TYPE = AUTH_OAUTH
OAUTH_PROVIDERS = [
    {{
        "name": "authentik",
        "icon": "fa-key",
        "token_key": "access_token",
        "remote_app": {{
            "client_id": "{OIDC_CLIENT_ID}",
            "client_secret": "{OIDC_CLIENT_SECRET}",
            "api_base_url": "http://omni-authentik:9000/application/o/",
            "access_token_url": "http://omni-authentik:9000/application/o/token/",
            "authorize_url": "http://omni-authentik:9000/application/o/authorize/",
            "server_metadata_url": "http://omni-authentik:9000/application/o/superset/.well-known/openid-configuration",
            "client_kwargs": {{"scope": "openid profile email"}},
        }},
    }}
]
AUTH_ROLE_ADMIN = "Admin"
AUTH_USER_REGISTRATION = True
AUTH_USER_REGISTRATION_ROLE = "Gamma"
"""
    with open(config_path, "w") as f:
        f.write(oauth_config)

    # 4. Add databases
    token = get_access_token()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    databases = [
        {
            "database_name": "financial_data",
            "sqlalchemy_uri": f"postgresql://user:{PG_PW}@omni-postgres:5432/financial_data",
        },
        {
            "database_name": "platform_metrics",
            "sqlalchemy_uri": f"postgresql://user:{PG_PW}@omni-postgres:5432/platform_metrics",
        },
    ]

    for db in databases:
        r = httpx.post(f"{SUPERSET_URL}/api/v1/database/", headers=headers, json=db)
        if r.status_code in (200, 201):
            print(f"Database '{db['database_name']}' added")
        else:
            print(f"Database '{db['database_name']}' response: {r.status_code}")

    # 5. Import dashboards
    os.makedirs(DASHBOARD_DIR, exist_ok=True)

    # Generate dashboards first
    subprocess.run(
        ["python3", os.path.join(os.path.dirname(__file__), "generate_dashboards.py")],
        check=True,
    )

    for filename in sorted(os.listdir(DASHBOARD_DIR)):
        if not filename.endswith(".json"):
            continue
        filepath = os.path.join(DASHBOARD_DIR, filename)
        with open(filepath, "rb") as f:
            r = httpx.post(
                f"{SUPERSET_URL}/api/v1/dashboard/import/",
                headers={"Authorization": f"Bearer {token}"},
                files={"formData": (filename, f, "application/json")},
            )
            if r.status_code in (200, 201):
                print(f"Dashboard '{filename}' imported")
            else:
                print(f"Dashboard '{filename}' import status: {r.status_code}")

    notify_mm("#general", "Superset initialized: databases connected, OAuth configured, dashboards imported.")
    print("Superset init complete.")


if __name__ == "__main__":
    main()
