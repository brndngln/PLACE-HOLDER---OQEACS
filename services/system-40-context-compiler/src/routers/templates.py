"""GET/POST /api/v1/templates — Context template management."""
from fastapi import APIRouter, HTTPException
import structlog

from src.models import ContextTemplate

logger = structlog.get_logger()
router = APIRouter(prefix="/api/v1", tags=["templates"])

_templates: dict[str, ContextTemplate] = {
    "default-generate": ContextTemplate(
        id="default-generate",
        name="Default Code Generation",
        task_type="generate",
        agent_role="developer",
        token_budget_override=128000,
    ),
    "default-review": ContextTemplate(
        id="default-review",
        name="Default Code Review",
        task_type="review",
        agent_role="reviewer",
        token_budget_override=64000,
    ),
    "default-fix": ContextTemplate(
        id="default-fix",
        name="Default Bug Fix",
        task_type="fix",
        agent_role="developer",
        token_budget_override=96000,
    ),
    "security-audit": ContextTemplate(
        id="security-audit",
        name="Security Audit",
        task_type="review",
        agent_role="security",
        tags=["soc2", "pci_dss"],
        token_budget_override=128000,
    ),
}


@router.get("/templates", response_model=list[ContextTemplate])
async def list_templates() -> list[ContextTemplate]:
    """List all context templates."""
    return list(_templates.values())


@router.get("/templates/{template_id}", response_model=ContextTemplate)
async def get_template(template_id: str) -> ContextTemplate:
    """Get a specific context template."""
    template = _templates.get(template_id)
    if template is None:
        raise HTTPException(status_code=404, detail=f"Template {template_id} not found")
    return template


@router.post("/templates", response_model=ContextTemplate)
async def create_template(template: ContextTemplate) -> ContextTemplate:
    """Create a new context template."""
    import uuid

    template.id = template.id or str(uuid.uuid4())
    _templates[template.id] = template
    logger.info("template_created", template_id=template.id, name=template.name)
    return template
