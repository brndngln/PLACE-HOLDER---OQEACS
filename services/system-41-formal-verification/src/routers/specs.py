"""POST /api/v1/spec/generate — Generate formal specifications from code."""
from fastapi import APIRouter, HTTPException
import structlog

from src.models import SpecGenerationRequest, SpecGenerationResult, ToolInfo

logger = structlog.get_logger()
router = APIRouter(prefix="/api/v1", tags=["specs"])


@router.post("/spec/generate", response_model=SpecGenerationResult)
async def generate_spec(request: SpecGenerationRequest) -> SpecGenerationResult:
    """Generate a TLA+/Dafny/CrossHair spec from source code."""
    from src.main import get_spec_generator

    generator = get_spec_generator()
    if generator is None:
        raise HTTPException(status_code=503, detail="Spec generator not initialized")
    return await generator.generate(request)


@router.get("/tools", response_model=list[ToolInfo])
async def list_tools() -> list[ToolInfo]:
    """List available verification tools and their status."""
    from src.services.tool_registry import list_tools as _list_tools

    return _list_tools()
