"""Analyze routes for semantic graph and code meaning."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from src.models import AnalysisRequest, CodeMeaning, CodeMeaningRequest, GraphSummary, SemanticGraph
from src.services.graph_builder import GraphBuilder
from src.services.meaning_extractor import MeaningExtractor

router = APIRouter(prefix="/api/v1", tags=["analyze"])

_graph_builder: GraphBuilder | None = None
_meaning_extractor: MeaningExtractor | None = None


def wire(graph_builder: GraphBuilder, meaning_extractor: MeaningExtractor) -> None:
    global _graph_builder, _meaning_extractor  # noqa: PLW0603
    _graph_builder = graph_builder
    _meaning_extractor = meaning_extractor


@router.post("/analyze", response_model=SemanticGraph)
async def analyze(request: AnalysisRequest) -> SemanticGraph:
    if _graph_builder is None:
        raise HTTPException(status_code=503, detail="Graph builder unavailable")
    return await _graph_builder.build_graph(
        repo_path=request.repo_path,
        languages=request.languages,
        depth=request.depth,
        include_tests=request.include_tests,
    )


@router.get("/graph/{repo_id}", response_model=GraphSummary)
async def get_graph(repo_id: str) -> GraphSummary:
    if _graph_builder is None:
        raise HTTPException(status_code=503, detail="Graph builder unavailable")
    graph = _graph_builder.get_graph(repo_id)
    if graph is None:
        raise HTTPException(status_code=404, detail="Graph not found")

    top = sorted(
        graph.centrality_scores.items(), key=lambda kv: kv[1], reverse=True
    )[:10]
    top_entities = [{"entity_id": eid, "score": score} for eid, score in top]

    return GraphSummary(
        repo_id=graph.repo_id,
        file_count=graph.file_count,
        total_entities=graph.total_entities,
        total_relationships=len(graph.relationships),
        languages=graph.languages,
        generated_at=graph.generated_at,
        top_central_entities=top_entities,
    )


@router.post("/meaning", response_model=CodeMeaning)
async def code_meaning(request: CodeMeaningRequest) -> CodeMeaning:
    if _meaning_extractor is None:
        raise HTTPException(status_code=503, detail="Meaning extractor unavailable")
    return _meaning_extractor.extract_meaning(
        code=request.code,
        language=request.language,
        context=request.context,
    )
