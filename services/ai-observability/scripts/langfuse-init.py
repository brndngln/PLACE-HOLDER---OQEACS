#!/usr/bin/env python3
"""
SYSTEM 13 — AI OBSERVABILITY: Langfuse Initialization Script
Omni Quantum Elite AI Coding System — Observability Layer

Sets up Langfuse with projects, API keys, prompt templates, and Vault integration.
Run once during platform bootstrap.

Requirements: httpx, hvac, structlog
"""

import os
import sys
import time
from dataclasses import dataclass
from typing import Any

import httpx
import hvac
import structlog

# ---------------------------------------------------------------------------
# Structured Logging
# ---------------------------------------------------------------------------

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(0),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)

log = structlog.get_logger(
    service="langfuse-init", system="13", component="ai-observability"
)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

LANGFUSE_URL = os.getenv("LANGFUSE_URL", "http://omni-langfuse:3000")
LANGFUSE_ADMIN_EMAIL = os.getenv(
    "LANGFUSE_ADMIN_EMAIL", "admin@omni-quantum.internal"
)
LANGFUSE_ADMIN_PASSWORD = os.getenv("LANGFUSE_ADMIN_PASSWORD", "")
VAULT_ADDR = os.getenv("VAULT_ADDR", "http://omni-vault:8200")
VAULT_TOKEN = os.getenv("VAULT_TOKEN", "")
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "60"))
RETRY_INTERVAL = int(os.getenv("RETRY_INTERVAL", "5"))


PROJECTS: list[dict[str, str]] = [
    {
        "name": "omni-pipeline",
        "description": (
            "Main AI coding pipeline traces — code generation, review, and refactoring"
        ),
    },
    {
        "name": "omni-openhands",
        "description": (
            "OpenHands autonomous agent traces — task execution and tool use"
        ),
    },
    {
        "name": "omni-swe-agent",
        "description": (
            "SWE-Agent traces — issue resolution and code modification"
        ),
    },
    {
        "name": "omni-knowledge",
        "description": (
            "Knowledge ingestion and RAG query traces — embedding, retrieval, generation"
        ),
    },
    {
        "name": "omni-flowise",
        "description": "Flowise chatbot traces — conversational AI workflows",
    },
]


PROMPT_TEMPLATES: list[dict[str, Any]] = [
    {
        "name": "code-generation-v1",
        "prompt": (
            "You are an expert software engineer working on the Omni Quantum Elite platform.\n\n"
            "## Task\n"
            "Generate production-quality code for the following requirement:\n\n"
            "{{requirement}}\n\n"
            "## Context\n"
            "- Language: {{language}}\n"
            "- Framework: {{framework}}\n"
            "- Existing codebase patterns: {{patterns}}\n\n"
            "## Quality Requirements\n"
            "1. Follow existing code conventions and patterns\n"
            "2. Include comprehensive error handling\n"
            "3. Write self-documenting code with clear variable names\n"
            "4. Ensure type safety where applicable\n"
            "5. Consider edge cases and boundary conditions\n"
            "6. Follow SOLID principles\n"
            "7. Minimize external dependencies\n"
            "8. Include input validation at system boundaries\n"
            "9. Ensure thread safety where applicable\n"
            "10. Write testable code with dependency injection\n\n"
            "## Output Format\n"
            "Provide the complete implementation with:\n"
            "- All necessary imports\n"
            "- Complete function/class implementations\n"
            "- Inline comments for complex logic only\n"
        ),
        "config": {
            "model": "claude-sonnet-4-5-20250929",
            "temperature": 0.3,
            "max_tokens": 4096,
        },
        "labels": ["code-generation", "production"],
    },
    {
        "name": "code-review-v1",
        "prompt": (
            "You are a senior code reviewer for the Omni Quantum Elite platform.\n\n"
            "## Code to Review\n"
            "```{{language}}\n{{code}}\n```\n\n"
            "## Review Criteria (score 1-10 for each)\n"
            "1. **Correctness** — Does the code do what it claims?\n"
            "2. **Security** — Are there vulnerabilities (OWASP Top 10)?\n"
            "3. **Performance** — Time/space complexity, resource usage\n"
            "4. **Readability** — Clear naming, structure, documentation\n"
            "5. **Maintainability** — Modularity, coupling, cohesion\n"
            "6. **Error Handling** — Edge cases, failure modes, recovery\n"
            "7. **Testing** — Testability, coverage considerations\n"
            "8. **Architecture** — Design patterns, SOLID adherence\n"
            "9. **Standards Compliance** — Language idioms, project conventions\n"
            "10. **Completeness** — Missing features, TODO items, gaps\n\n"
            "## Output Format\n"
            "```json\n"
            "{\n"
            '  "scores": {"correctness": N, "security": N, ...},\n'
            '  "overall_score": N,\n'
            '  "critical_issues": ["..."],\n'
            '  "suggestions": ["..."],\n'
            '  "approved": true/false\n'
            "}\n"
            "```\n"
        ),
        "config": {
            "model": "claude-sonnet-4-5-20250929",
            "temperature": 0.1,
            "max_tokens": 2048,
        },
        "labels": ["code-review", "quality"],
    },
    {
        "name": "spec-generation-v1",
        "prompt": (
            "You are a technical architect for the Omni Quantum Elite platform.\n\n"
            "## Task\n"
            "Generate a detailed technical specification for:\n\n"
            "{{feature_description}}\n\n"
            "## Context\n"
            "- System: {{system_name}}\n"
            "- Existing architecture: {{architecture_context}}\n"
            "- Constraints: {{constraints}}\n\n"
            "## Specification Template\n"
            "1. **Overview** — What this feature does and why\n"
            "2. **Requirements** — Functional and non-functional\n"
            "3. **API Design** — Endpoints, request/response schemas\n"
            "4. **Data Model** — Database schema changes\n"
            "5. **Architecture** — Component diagram, data flow\n"
            "6. **Security Considerations** — Auth, encryption, access control\n"
            "7. **Performance Targets** — Latency, throughput, resource limits\n"
            "8. **Testing Strategy** — Unit, integration, e2e test plans\n"
            "9. **Rollout Plan** — Feature flags, migration steps\n"
            "10. **Monitoring** — Metrics, alerts, dashboards needed\n"
        ),
        "config": {
            "model": "claude-sonnet-4-5-20250929",
            "temperature": 0.4,
            "max_tokens": 4096,
        },
        "labels": ["specification", "architecture"],
    },
    {
        "name": "bug-fix-v1",
        "prompt": (
            "You are a debugging specialist for the Omni Quantum Elite platform.\n\n"
            "## Bug Report\n"
            "{{bug_description}}\n\n"
            "## Error Details\n"
            "- Error message: {{error_message}}\n"
            "- Stack trace:\n```\n{{stack_trace}}\n```\n"
            "- Affected file(s): {{affected_files}}\n"
            "- Reproduction steps: {{repro_steps}}\n\n"
            "## Analysis Framework\n"
            "1. **Root Cause Analysis**\n"
            "   - Identify the exact line(s) causing the issue\n"
            "   - Explain why it fails\n"
            "   - Classify: logic error, race condition, null reference, type error, etc.\n\n"
            "2. **Impact Assessment**\n"
            "   - What functionality is broken?\n"
            "   - Are there downstream effects?\n"
            "   - Data corruption risk?\n\n"
            "3. **Fix Implementation**\n"
            "   - Provide the minimal correct fix\n"
            "   - Explain why this fix is correct\n"
            "   - Note any regression risks\n\n"
            "4. **Prevention**\n"
            "   - What test would have caught this?\n"
            "   - Should we add validation/guards?\n"
        ),
        "config": {
            "model": "claude-sonnet-4-5-20250929",
            "temperature": 0.2,
            "max_tokens": 3072,
        },
        "labels": ["bug-fix", "debugging"],
    },
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@dataclass
class LangfuseSession:
    """Holds authenticated session state for Langfuse API calls."""

    client: httpx.Client
    base_url: str
    auth_token: str


def wait_for_langfuse() -> None:
    """Block until Langfuse health endpoint responds 200."""
    log.info("waiting_for_langfuse", url=LANGFUSE_URL)
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = httpx.get(f"{LANGFUSE_URL}/api/public/health", timeout=5)
            if resp.status_code == 200:
                log.info("langfuse_healthy", attempt=attempt)
                return
        except httpx.ConnectError:
            pass
        except httpx.TimeoutException:
            pass
        log.debug(
            "langfuse_not_ready", attempt=attempt, max_retries=MAX_RETRIES
        )
        time.sleep(RETRY_INTERVAL)
    log.error("langfuse_timeout", max_retries=MAX_RETRIES)
    sys.exit(1)


def create_admin_account(client: httpx.Client) -> str:
    """Create admin account and return auth token."""
    log.info("creating_admin_account", email=LANGFUSE_ADMIN_EMAIL)

    resp = client.post(
        f"{LANGFUSE_URL}/api/auth/signup",
        json={
            "name": "Omni Quantum Admin",
            "email": LANGFUSE_ADMIN_EMAIL,
            "password": LANGFUSE_ADMIN_PASSWORD,
        },
    )

    if resp.status_code == 200:
        log.info("admin_account_created")
    elif resp.status_code in (409, 422):
        log.info("admin_account_exists")
    else:
        log.warning(
            "signup_unexpected_status",
            status_code=resp.status_code,
            body=resp.text,
        )

    resp = client.post(
        f"{LANGFUSE_URL}/api/auth/callback/credentials",
        json={
            "email": LANGFUSE_ADMIN_EMAIL,
            "password": LANGFUSE_ADMIN_PASSWORD,
        },
    )
    if resp.status_code != 200:
        log.error(
            "login_failed", status_code=resp.status_code, body=resp.text
        )
        sys.exit(1)

    token = resp.json().get(
        "token", resp.cookies.get("next-auth.session-token", "")
    )
    log.info("authenticated_successfully")
    return token


def create_project(
    session: LangfuseSession, name: str, description: str = ""
) -> dict[str, Any]:
    """Create a Langfuse project and return its metadata including API keys."""
    log.info("creating_project", project=name)

    resp = session.client.post(
        f"{session.base_url}/api/projects",
        headers={"Authorization": f"Bearer {session.auth_token}"},
        json={"name": name},
    )

    if resp.status_code in (200, 201):
        project: dict[str, Any] = resp.json()
        log.info(
            "project_created", project=name, id=project.get("id", "unknown")
        )
    elif resp.status_code == 409:
        log.info("project_exists", project=name)
        list_resp = session.client.get(
            f"{session.base_url}/api/projects",
            headers={"Authorization": f"Bearer {session.auth_token}"},
        )
        projects = list_resp.json() if list_resp.status_code == 200 else []
        if isinstance(projects, dict):
            projects = projects.get("data", projects.get("projects", []))
        project = next((p for p in projects if p.get("name") == name), {})
    else:
        log.warning(
            "project_create_unexpected",
            project=name,
            status_code=resp.status_code,
        )
        project = {"name": name}

    project_id = project.get("id", "")

    if project_id:
        keys_resp = session.client.post(
            f"{session.base_url}/api/projects/{project_id}/api-keys",
            headers={"Authorization": f"Bearer {session.auth_token}"},
            json={"note": f"Auto-generated for {name}"},
        )
        if keys_resp.status_code in (200, 201):
            keys = keys_resp.json()
            project["public_key"] = keys.get("publicKey", "")
            project["secret_key"] = keys.get("secretKey", "")
            log.info("api_keys_generated", project=name)
        else:
            log.warning(
                "api_key_generation_failed",
                project=name,
                status_code=keys_resp.status_code,
            )
            project["public_key"] = ""
            project["secret_key"] = ""
    else:
        project["public_key"] = ""
        project["secret_key"] = ""

    return project


def store_keys_in_vault(
    vault_client: hvac.Client,
    project_name: str,
    public_key: str,
    secret_key: str,
) -> None:
    """Store project API keys in Vault KV v2."""
    path = f"langfuse/projects/{project_name}"
    log.info(
        "storing_keys_in_vault",
        path=f"secret/data/{path}",
        project=project_name,
    )

    vault_client.secrets.kv.v2.create_or_update_secret(
        path=path,
        secret={
            "public_key": public_key,
            "secret_key": secret_key,
            "langfuse_url": LANGFUSE_URL,
            "project_name": project_name,
        },
        mount_point="secret",
    )
    log.info("keys_stored", project=project_name)


def configure_trace_sampling(
    session: LangfuseSession, project_id: str
) -> None:
    """Configure trace sampling rules for a project.

    Sampling strategy:
    - 100% for traces tagged with error or failed status
    - 100% for traces tagged "critical"
    - 10% for routine queries (everything else)
    """
    log.info("configuring_sampling", project_id=project_id)

    sampling_config = {
        "samplingRules": [
            {
                "name": "all-errors",
                "description": "Capture 100% of error traces",
                "sampleRate": 1.0,
                "condition": {"status": "error"},
            },
            {
                "name": "critical-tasks",
                "description": "Capture 100% of critical task traces",
                "sampleRate": 1.0,
                "condition": {"tags": ["critical"]},
            },
            {
                "name": "routine-default",
                "description": "Sample 10% of routine queries",
                "sampleRate": 0.1,
                "condition": {},
            },
        ]
    }

    resp = session.client.patch(
        f"{session.base_url}/api/projects/{project_id}",
        headers={"Authorization": f"Bearer {session.auth_token}"},
        json={"settings": sampling_config},
    )

    if resp.status_code in (200, 201, 204):
        log.info("sampling_configured", project_id=project_id)
    else:
        log.warning(
            "sampling_config_api_unsupported",
            status_code=resp.status_code,
            note="sampling may need SDK-level implementation",
        )


def create_prompt_template(
    session: LangfuseSession,
    project_public_key: str,
    project_secret_key: str,
    template: dict[str, Any],
) -> None:
    """Create a versioned prompt template in Langfuse prompt management."""
    name = template["name"]
    log.info("creating_prompt_template", template=name)

    resp = session.client.post(
        f"{session.base_url}/api/public/v2/prompts",
        auth=(project_public_key, project_secret_key),
        json={
            "name": name,
            "prompt": template["prompt"],
            "config": template.get("config", {}),
            "labels": template.get("labels", []),
            "type": "text",
        },
    )

    if resp.status_code in (200, 201):
        version = resp.json().get("version", 1)
        log.info("template_created", template=name, version=version)
    elif resp.status_code == 409:
        log.info("template_exists", template=name)
    else:
        log.warning(
            "template_create_failed",
            template=name,
            status_code=resp.status_code,
            body=resp.text,
        )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    """Initialize Langfuse with all projects, keys, and prompt templates."""
    log.info("initialization_starting", system="13", component="langfuse")

    if not LANGFUSE_ADMIN_PASSWORD:
        log.error("missing_config", var="LANGFUSE_ADMIN_PASSWORD")
        sys.exit(1)

    # Step 1: Wait for Langfuse
    wait_for_langfuse()

    # Step 2: Connect to Vault
    log.info("connecting_to_vault", addr=VAULT_ADDR)
    vault_client = hvac.Client(url=VAULT_ADDR, token=VAULT_TOKEN)
    if not vault_client.is_authenticated():
        log.error("vault_auth_failed")
        sys.exit(1)
    log.info("vault_connected")

    # Step 3: Create admin account and authenticate
    client = httpx.Client(timeout=30)
    auth_token = create_admin_account(client)
    session = LangfuseSession(
        client=client, base_url=LANGFUSE_URL, auth_token=auth_token
    )

    # Step 4: Create projects and store keys
    log.info("creating_projects", count=len(PROJECTS))
    project_keys: dict[str, dict[str, Any]] = {}

    for project_def in PROJECTS:
        project = create_project(
            session, project_def["name"], project_def["description"]
        )
        project_keys[project_def["name"]] = project

        if project.get("public_key") and project.get("secret_key"):
            store_keys_in_vault(
                vault_client,
                project_def["name"],
                project["public_key"],
                project["secret_key"],
            )

        if project.get("id"):
            configure_trace_sampling(session, project["id"])

    # Step 5: Create prompt templates for the main pipeline project
    log.info("creating_prompt_templates", count=len(PROMPT_TEMPLATES))
    pipeline_project = project_keys.get("omni-pipeline", {})
    pub_key = pipeline_project.get("public_key", "")
    sec_key = pipeline_project.get("secret_key", "")

    if pub_key and sec_key:
        for template in PROMPT_TEMPLATES:
            create_prompt_template(session, pub_key, sec_key, template)
    else:
        log.warning(
            "skipping_templates", reason="no API keys for omni-pipeline"
        )

    # Step 6: Summary
    log.info(
        "initialization_complete",
        projects_created=len(PROJECTS),
        prompt_templates=len(PROMPT_TEMPLATES),
        vault_path_pattern="secret/data/langfuse/projects/{name}",
        langfuse_url=LANGFUSE_URL,
    )

    client.close()


if __name__ == "__main__":
    main()
