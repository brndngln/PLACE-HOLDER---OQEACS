"""
Neo4j GraphRAG: Pattern Query API
Omni Quantum Elite AI Coding System

Design pattern knowledge graph API consumed by Token Infinity.
Provides NLP-based pattern recommendation, pattern detail retrieval,
relationship traversal, anti-pattern detection, SOLID principle mapping,
and shortest-path queries over a Neo4j design pattern knowledge graph.

Port: 7475
Label: omni.quantum.component: neo4j-graphrag-api
"""

from __future__ import annotations

import os
import re
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, Optional

import structlog
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from neo4j import AsyncGraphDatabase, AsyncDriver
from prometheus_client import (
    CollectorRegistry,
    Counter,
    Histogram,
    generate_latest,
)
from pydantic import BaseModel, Field
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

# ---------------------------------------------------------------------------
# Structured logging
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
logger = structlog.get_logger("neo4j_graphrag.pattern_query_api")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
NEO4J_URI: str = os.getenv("NEO4J_URI", "bolt://omni-neo4j:7687")
NEO4J_USER: str = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD: str = os.getenv("NEO4J_PASSWORD", "quantum_elite_2024")

SERVICE_NAME: str = "neo4j-graphrag-api"
SERVICE_VERSION: str = "1.0.0"
SERVICE_PORT: int = 7475

# ---------------------------------------------------------------------------
# Prometheus metrics
# ---------------------------------------------------------------------------
registry = CollectorRegistry()

PATTERN_QUERIES_TOTAL = Counter(
    "pattern_queries_total",
    "Total pattern queries executed",
    labelnames=["endpoint", "status"],
    registry=registry,
)
PATTERN_RECOMMENDATIONS_TOTAL = Counter(
    "pattern_recommendations_total",
    "Total pattern recommendation requests",
    labelnames=["language", "status"],
    registry=registry,
)
PATTERN_QUERY_LATENCY = Histogram(
    "pattern_query_latency_seconds",
    "Latency of pattern queries in seconds",
    labelnames=["endpoint"],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
    registry=registry,
)

# ---------------------------------------------------------------------------
# NLP keyword extraction helpers
# ---------------------------------------------------------------------------

# Common English stop words to filter out of task descriptions
_STOP_WORDS: set[str] = {
    "a", "an", "the", "is", "it", "of", "in", "to", "and", "or", "for",
    "on", "at", "by", "with", "from", "that", "this", "be", "are", "was",
    "were", "been", "being", "have", "has", "had", "do", "does", "did",
    "will", "would", "could", "should", "may", "might", "shall", "can",
    "not", "no", "but", "if", "when", "how", "what", "which", "who",
    "where", "why", "all", "each", "every", "some", "any", "few", "more",
    "most", "other", "into", "over", "such", "than", "too", "very", "just",
    "about", "above", "after", "again", "also", "am", "as", "because",
    "before", "between", "both", "during", "he", "her", "here", "him",
    "his", "i", "me", "my", "need", "needs", "now", "only", "our", "out",
    "own", "same", "she", "so", "them", "then", "there", "these", "they",
    "those", "through", "up", "use", "using", "want", "we", "you", "your",
}

# Domain-specific synonym mappings to broaden search coverage
_SYNONYM_MAP: dict[str, list[str]] = {
    "create": ["factory", "builder", "creation", "construct", "instantiate"],
    "object": ["instance", "entity", "class", "component"],
    "notify": ["observer", "event", "publish", "subscribe", "listener"],
    "event": ["observer", "publish", "subscribe", "listener", "notification"],
    "wrap": ["decorator", "wrapper", "proxy", "adapter"],
    "convert": ["adapter", "bridge", "mapper", "transform"],
    "decouple": ["mediator", "observer", "facade", "abstraction"],
    "state": ["state", "memento", "snapshot", "finite"],
    "tree": ["composite", "hierarchy", "recursive", "nested"],
    "undo": ["memento", "command", "rollback", "restore"],
    "command": ["command", "action", "request", "execute", "handler"],
    "iterate": ["iterator", "traversal", "cursor", "collection"],
    "cache": ["flyweight", "pool", "memoize", "cache"],
    "single": ["singleton", "unique", "global", "shared"],
    "global": ["singleton", "registry", "shared"],
    "async": ["async", "promise", "future", "reactor", "callback"],
    "concurrent": ["thread", "lock", "pool", "semaphore", "barrier"],
    "api": ["facade", "gateway", "proxy", "interface"],
    "interface": ["adapter", "facade", "bridge", "abstract"],
    "algorithm": ["strategy", "template", "policy", "behavior"],
    "behaviour": ["strategy", "state", "chain", "visitor"],
    "behavior": ["strategy", "state", "chain", "visitor"],
    "structure": ["composite", "decorator", "bridge", "flyweight"],
    "simplify": ["facade", "adapter", "mediator", "proxy"],
    "chain": ["chain", "middleware", "pipeline", "handler"],
    "template": ["template", "skeleton", "hook", "framework"],
    "copy": ["prototype", "clone", "duplicate"],
    "clone": ["prototype", "clone", "duplicate"],
    "flexible": ["strategy", "abstract", "factory", "plugin"],
    "plugin": ["strategy", "abstract", "factory", "plugin"],
    "lazy": ["proxy", "lazy", "virtual", "deferred"],
    "access": ["proxy", "facade", "gateway", "guard"],
    "request": ["command", "handler", "chain", "mediator"],
    "microservice": ["facade", "gateway", "proxy", "mediator", "saga"],
    "distributed": ["saga", "event", "cqrs", "mediator"],
}


def extract_keywords(text: str) -> list[str]:
    """Extract meaningful keywords from a task description.

    Tokenises the input text, removes stop words, and expands tokens
    through a domain-specific synonym map to produce a broad set of
    search terms relevant to design patterns.

    Args:
        text: Free-form task description.

    Returns:
        Deduplicated list of keywords suitable for full-text or
        CONTAINS searches.
    """
    tokens = re.findall(r"[a-zA-Z]{2,}", text.lower())
    keywords: list[str] = []
    seen: set[str] = set()

    for token in tokens:
        if token in _STOP_WORDS:
            continue
        if token not in seen:
            keywords.append(token)
            seen.add(token)
        # Expand via synonyms
        for synonym in _SYNONYM_MAP.get(token, []):
            if synonym not in seen:
                keywords.append(synonym)
                seen.add(synonym)

    return keywords


def compute_keyword_score(text: str, keywords: list[str]) -> float:
    """Compute a relevance score based on keyword overlap.

    The score is the fraction of keywords found in the target text,
    yielding a value between 0.0 and 1.0.

    Args:
        text: Text to match against (e.g. pattern description).
        keywords: List of search keywords.

    Returns:
        Relevance score from 0.0 to 1.0.
    """
    if not keywords:
        return 0.0
    text_lower = text.lower()
    matches = sum(1 for kw in keywords if kw in text_lower)
    return round(matches / len(keywords), 4)


# ---------------------------------------------------------------------------
# Pydantic response/request models
# ---------------------------------------------------------------------------

class TradeOffDetail(BaseModel):
    """A single trade-off associated with a pattern."""
    benefit: str
    cost: str
    context: Optional[str] = None


class AntiPatternDetail(BaseModel):
    """An anti-pattern warning associated with a pattern."""
    name: str
    description: Optional[str] = None
    why_bad: Optional[str] = None
    better_alternative: Optional[str] = None


class RelatedPatternBrief(BaseModel):
    """Brief summary of a related pattern."""
    name: str
    relationship_type: Optional[str] = None
    description: Optional[str] = None


class PatternRecommendation(BaseModel):
    """A single pattern recommendation with scoring."""
    name: str
    description: Optional[str] = None
    intent: Optional[str] = None
    when_to_use: Optional[str] = None
    complexity: Optional[str] = None
    confidence: float = Field(..., ge=0.0, le=1.0, description="Relevance confidence score")
    complementary_patterns: list[RelatedPatternBrief] = Field(default_factory=list)
    trade_offs: list[TradeOffDetail] = Field(default_factory=list)
    anti_pattern_warnings: list[AntiPatternDetail] = Field(default_factory=list)


class RecommendationResponse(BaseModel):
    """Response for GET /patterns/recommend."""
    task: str
    language: Optional[str] = None
    keywords_extracted: list[str]
    recommendations: list[PatternRecommendation]
    total_results: int


class ImplementationDetail(BaseModel):
    """Language-specific implementation details."""
    language: str
    code_template: Optional[str] = None
    notes: Optional[str] = None
    idioms: Optional[str] = None
    caveats: Optional[str] = None


class PrincipleDetail(BaseModel):
    """A design principle linked to a pattern."""
    name: str
    relationship: str  # "supports" or "violates"
    how: Optional[str] = None
    when: Optional[str] = None
    why: Optional[str] = None


class RelatedPatternDetail(BaseModel):
    """A related pattern with full relationship context."""
    name: str
    description: Optional[str] = None
    relationship_type: Optional[str] = None
    frequency: Optional[str] = None
    example_context: Optional[str] = None
    evolution_trigger: Optional[str] = None


class PatternDetailResponse(BaseModel):
    """Full pattern detail response for GET /patterns/{name}."""
    name: str
    description: Optional[str] = None
    intent: Optional[str] = None
    when_to_use: Optional[str] = None
    when_not_to_use: Optional[str] = None
    complexity: Optional[str] = None
    frequency: Optional[str] = None
    category: Optional[str] = None
    implementations: list[ImplementationDetail] = Field(default_factory=list)
    principles: list[PrincipleDetail] = Field(default_factory=list)
    trade_offs: list[TradeOffDetail] = Field(default_factory=list)
    anti_patterns: list[AntiPatternDetail] = Field(default_factory=list)
    related_patterns: list[RelatedPatternDetail] = Field(default_factory=list)
    commonly_used_with: list[RelatedPatternDetail] = Field(default_factory=list)
    evolves_to: list[RelatedPatternDetail] = Field(default_factory=list)


class RelatedPatternsResponse(BaseModel):
    """Response for GET /patterns/{name}/related."""
    pattern: str
    related_to: list[RelatedPatternDetail] = Field(default_factory=list)
    commonly_used_with: list[RelatedPatternDetail] = Field(default_factory=list)
    evolves_to: list[RelatedPatternDetail] = Field(default_factory=list)
    evolves_from: list[RelatedPatternDetail] = Field(default_factory=list)


class ImplementationResponse(BaseModel):
    """Response for GET /patterns/{name}/implementations/{language}."""
    pattern: str
    language: str
    implementation: Optional[ImplementationDetail] = None


class AntiPatternMatch(BaseModel):
    """A matched anti-pattern with associated design patterns."""
    anti_pattern_name: str
    description: Optional[str] = None
    why_bad: Optional[str] = None
    better_alternative: Optional[str] = None
    associated_patterns: list[str] = Field(default_factory=list)
    confidence: float = Field(..., ge=0.0, le=1.0)


class AntiPatternResponse(BaseModel):
    """Response for GET /patterns/anti-patterns."""
    code_description: str
    keywords_extracted: list[str]
    anti_patterns: list[AntiPatternMatch]
    total_results: int


class PrinciplePatternEntry(BaseModel):
    """A pattern that supports or violates a principle."""
    name: str
    description: Optional[str] = None
    relationship: str
    how: Optional[str] = None
    when: Optional[str] = None
    why: Optional[str] = None


class PrincipleResponse(BaseModel):
    """Response for GET /patterns/for-principle/{principle}."""
    principle: str
    supporting_patterns: list[PrinciplePatternEntry] = Field(default_factory=list)
    violating_patterns: list[PrinciplePatternEntry] = Field(default_factory=list)


class PathNode(BaseModel):
    """A node in the shortest path result."""
    name: str
    type: str


class PathRelationship(BaseModel):
    """A relationship in the shortest path result."""
    type: str
    properties: dict[str, Any] = Field(default_factory=dict)


class PathResponse(BaseModel):
    """Response for POST /patterns/path."""
    from_pattern: str
    to_pattern: str
    path_found: bool
    path_length: int = 0
    nodes: list[PathNode] = Field(default_factory=list)
    relationships: list[PathRelationship] = Field(default_factory=list)


class HealthResponse(BaseModel):
    """Standard health check response."""
    status: str
    service: str
    version: str
    timestamp: str
    neo4j_connected: bool


# ---------------------------------------------------------------------------
# Neo4j driver singleton
# ---------------------------------------------------------------------------

_driver: Optional[AsyncDriver] = None


def get_driver() -> AsyncDriver:
    """Return the global Neo4j async driver instance.

    Raises:
        RuntimeError: If the driver has not been initialised.

    Returns:
        The global AsyncDriver.
    """
    if _driver is None:
        raise RuntimeError("Neo4j driver not initialised")
    return _driver


# ---------------------------------------------------------------------------
# Retry-wrapped Neo4j query execution
# ---------------------------------------------------------------------------

@retry(
    retry=retry_if_exception_type(Exception),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=0.5, min=0.5, max=5.0),
    reraise=True,
)
async def execute_query(
    query: str,
    parameters: Optional[dict[str, Any]] = None,
    database: str = "neo4j",
) -> list[dict[str, Any]]:
    """Execute a Cypher query with automatic retry on transient failures.

    Opens an async session, runs the query, and returns all records as
    a list of dictionaries. Retries up to 3 times with exponential
    backoff on any exception.

    Args:
        query: The Cypher query string.
        parameters: Optional mapping of query parameters.
        database: Target Neo4j database name.

    Returns:
        List of record dictionaries.
    """
    driver = get_driver()
    async with driver.session(database=database) as session:
        result = await session.run(query, parameters or {})
        records = await result.data()
        return records


@retry(
    retry=retry_if_exception_type(Exception),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=0.5, min=0.5, max=5.0),
    reraise=True,
)
async def execute_single(
    query: str,
    parameters: Optional[dict[str, Any]] = None,
    database: str = "neo4j",
) -> Optional[dict[str, Any]]:
    """Execute a Cypher query and return a single record or None.

    Args:
        query: The Cypher query string.
        parameters: Optional mapping of query parameters.
        database: Target Neo4j database name.

    Returns:
        A single record dictionary, or None if no results.
    """
    driver = get_driver()
    async with driver.session(database=database) as session:
        result = await session.run(query, parameters or {})
        record = await result.single(strict=False)
        if record is None:
            return None
        return dict(record)


# ---------------------------------------------------------------------------
# FastAPI lifespan
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup and shutdown.

    Initialises the Neo4j async driver on startup and ensures graceful
    closure on shutdown.
    """
    global _driver

    logger.info(
        "neo4j_graphrag_api_starting",
        port=SERVICE_PORT,
        version=SERVICE_VERSION,
        neo4j_uri=NEO4J_URI,
    )

    _driver = AsyncGraphDatabase.driver(
        NEO4J_URI,
        auth=(NEO4J_USER, NEO4J_PASSWORD),
        max_connection_pool_size=25,
        connection_acquisition_timeout=30.0,
    )

    # Verify connectivity
    try:
        await _driver.verify_connectivity()
        logger.info("neo4j_connected", uri=NEO4J_URI)
    except Exception as exc:
        logger.error("neo4j_connection_failed", uri=NEO4J_URI, error=str(exc))

    yield

    # Shutdown
    if _driver is not None:
        await _driver.close()
        logger.info("neo4j_driver_closed")

    logger.info("neo4j_graphrag_api_shutdown")


# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Neo4j GraphRAG -- Pattern Query API",
    description=(
        "Design pattern knowledge graph API for the Omni Quantum Elite AI "
        "Coding System. Provides NLP-based pattern recommendations, pattern "
        "detail retrieval, relationship traversal, anti-pattern detection, "
        "SOLID principle mapping, and shortest-path queries."
    ),
    version=SERVICE_VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Middleware: request latency tracking
# ---------------------------------------------------------------------------

@app.middleware("http")
async def track_request_latency(request: Request, call_next):
    """Middleware to measure and record request latency for all endpoints."""
    start = time.monotonic()
    response = await call_next(request)
    elapsed = time.monotonic() - start
    endpoint = request.url.path
    PATTERN_QUERY_LATENCY.labels(endpoint=endpoint).observe(elapsed)
    return response


# ---------------------------------------------------------------------------
# Endpoint 1: GET /patterns/recommend
# ---------------------------------------------------------------------------

@app.get("/patterns/recommend", response_model=RecommendationResponse)
async def recommend_patterns(
    task: str = Query(..., min_length=2, description="Task description for pattern recommendation"),
    language: Optional[str] = Query(None, description="Programming language filter"),
) -> RecommendationResponse:
    """Recommend design patterns for a given task description.

    Parses the task description to extract keywords, performs a full-text
    search against Pattern.description and Pattern.when_to_use, optionally
    filters by programming language, traverses RELATED_TO edges for
    complementary patterns, and includes trade-offs and anti-pattern
    warnings. Results are ranked by confidence score.

    Args:
        task: Free-form description of the programming task.
        language: Optional language to filter implementations by.

    Returns:
        Ranked list of pattern recommendations with confidence scores.
    """
    log = logger.bind(task=task, language=language)
    log.info("pattern_recommendation_requested")
    lang_label = language or "any"

    try:
        keywords = extract_keywords(task)
        if not keywords:
            PATTERN_RECOMMENDATIONS_TOTAL.labels(language=lang_label, status="empty_keywords").inc()
            return RecommendationResponse(
                task=task,
                language=language,
                keywords_extracted=[],
                recommendations=[],
                total_results=0,
            )

        # Build a WHERE clause that does a CONTAINS match on description
        # and when_to_use for each keyword
        contains_clauses = []
        params: dict[str, Any] = {}
        for idx, kw in enumerate(keywords):
            param_name = f"kw{idx}"
            params[param_name] = kw
            contains_clauses.append(
                f"(toLower(p.description) CONTAINS ${param_name} "
                f"OR toLower(p.when_to_use) CONTAINS ${param_name} "
                f"OR toLower(p.name) CONTAINS ${param_name} "
                f"OR toLower(p.intent) CONTAINS ${param_name})"
            )

        where_keyword = " OR ".join(contains_clauses)

        # Optional language filter via Implementation -> Language
        if language:
            params["lang"] = language.lower()
            cypher = f"""
                MATCH (p:Pattern)
                WHERE ({where_keyword})
                AND EXISTS {{
                    MATCH (p)-[:HAS_IMPLEMENTATION]->(impl:Implementation)-[:FOR_LANGUAGE]->(l:Language)
                    WHERE toLower(l.name) = $lang
                }}
                OPTIONAL MATCH (p)-[:BELONGS_TO]->(cat:Category)
                OPTIONAL MATCH (p)-[rt:RELATED_TO]->(rp:Pattern)
                OPTIONAL MATCH (p)-[:HAS_TRADEOFF]->(t:TradeOff)
                OPTIONAL MATCH (p)-[:ANTI_PATTERN_OF]->(ap:AntiPattern)
                RETURN p,
                       cat.name AS category,
                       collect(DISTINCT {{
                           name: rp.name,
                           relationship_type: rt.relationship_type,
                           description: rp.description
                       }}) AS related,
                       collect(DISTINCT {{
                           benefit: t.benefit,
                           cost: t.cost,
                           context: t.context
                       }}) AS tradeoffs,
                       collect(DISTINCT {{
                           name: ap.name,
                           description: ap.description,
                           why_bad: ap.why_bad,
                           better_alternative: ap.better_alternative
                       }}) AS antipatterns
            """
        else:
            cypher = f"""
                MATCH (p:Pattern)
                WHERE ({where_keyword})
                OPTIONAL MATCH (p)-[:BELONGS_TO]->(cat:Category)
                OPTIONAL MATCH (p)-[rt:RELATED_TO]->(rp:Pattern)
                OPTIONAL MATCH (p)-[:HAS_TRADEOFF]->(t:TradeOff)
                OPTIONAL MATCH (p)-[:ANTI_PATTERN_OF]->(ap:AntiPattern)
                RETURN p,
                       cat.name AS category,
                       collect(DISTINCT {{
                           name: rp.name,
                           relationship_type: rt.relationship_type,
                           description: rp.description
                       }}) AS related,
                       collect(DISTINCT {{
                           benefit: t.benefit,
                           cost: t.cost,
                           context: t.context
                       }}) AS tradeoffs,
                       collect(DISTINCT {{
                           name: ap.name,
                           description: ap.description,
                           why_bad: ap.why_bad,
                           better_alternative: ap.better_alternative
                       }}) AS antipatterns
            """

        records = await execute_query(cypher, params)

        recommendations: list[PatternRecommendation] = []
        for rec in records:
            p = rec.get("p", {})
            if isinstance(p, dict):
                p_props = p
            else:
                # neo4j Node object
                p_props = dict(p) if p else {}

            name = p_props.get("name", "")
            description = p_props.get("description", "") or ""
            intent = p_props.get("intent", "") or ""
            when_to_use = p_props.get("when_to_use", "") or ""

            # Compute confidence from keyword overlap across all searchable fields
            combined_text = f"{name} {description} {intent} {when_to_use}"
            confidence = compute_keyword_score(combined_text, keywords)
            if confidence <= 0.0:
                continue

            # Build complementary patterns
            related_raw = rec.get("related", [])
            complementary: list[RelatedPatternBrief] = []
            for r in related_raw:
                if isinstance(r, dict) and r.get("name"):
                    complementary.append(RelatedPatternBrief(
                        name=r["name"],
                        relationship_type=r.get("relationship_type"),
                        description=r.get("description"),
                    ))

            # Build trade-offs
            tradeoffs_raw = rec.get("tradeoffs", [])
            tradeoffs: list[TradeOffDetail] = []
            for t in tradeoffs_raw:
                if isinstance(t, dict) and (t.get("benefit") or t.get("cost")):
                    tradeoffs.append(TradeOffDetail(
                        benefit=t.get("benefit", ""),
                        cost=t.get("cost", ""),
                        context=t.get("context"),
                    ))

            # Build anti-pattern warnings
            ap_raw = rec.get("antipatterns", [])
            ap_warnings: list[AntiPatternDetail] = []
            for a in ap_raw:
                if isinstance(a, dict) and a.get("name"):
                    ap_warnings.append(AntiPatternDetail(
                        name=a["name"],
                        description=a.get("description"),
                        why_bad=a.get("why_bad"),
                        better_alternative=a.get("better_alternative"),
                    ))

            recommendations.append(PatternRecommendation(
                name=name,
                description=description or None,
                intent=intent or None,
                when_to_use=when_to_use or None,
                complexity=p_props.get("complexity"),
                confidence=confidence,
                complementary_patterns=complementary,
                trade_offs=tradeoffs,
                anti_pattern_warnings=ap_warnings,
            ))

        # Sort by confidence descending
        recommendations.sort(key=lambda r: r.confidence, reverse=True)

        PATTERN_RECOMMENDATIONS_TOTAL.labels(language=lang_label, status="success").inc()
        log.info("pattern_recommendations_returned", count=len(recommendations))

        return RecommendationResponse(
            task=task,
            language=language,
            keywords_extracted=keywords,
            recommendations=recommendations,
            total_results=len(recommendations),
        )

    except Exception as exc:
        PATTERN_RECOMMENDATIONS_TOTAL.labels(language=lang_label, status="error").inc()
        log.exception("pattern_recommendation_failed", error=str(exc))
        raise HTTPException(status_code=500, detail=f"Recommendation query failed: {exc}") from exc


# ---------------------------------------------------------------------------
# Endpoint 5: GET /patterns/anti-patterns
# (Registered before /patterns/{name} to avoid path parameter capture)
# ---------------------------------------------------------------------------

@app.get("/patterns/anti-patterns", response_model=AntiPatternResponse)
async def get_anti_patterns(
    code_description: str = Query(
        ...,
        min_length=2,
        description="Description of code to check for anti-patterns",
    ),
) -> AntiPatternResponse:
    """Match a code description against known anti-patterns.

    Extracts keywords from the description, searches AntiPattern nodes
    by description and name, and returns matches with the associated
    patterns that avoid the anti-pattern, along with better alternatives.

    Args:
        code_description: Free-form description of the code to analyse.

    Returns:
        Matched anti-patterns with confidence scores and recommendations.
    """
    log = logger.bind(code_description=code_description)
    log.info("anti_pattern_check_requested")

    try:
        keywords = extract_keywords(code_description)
        if not keywords:
            PATTERN_QUERIES_TOTAL.labels(endpoint="/patterns/anti-patterns", status="empty_keywords").inc()
            return AntiPatternResponse(
                code_description=code_description,
                keywords_extracted=[],
                anti_patterns=[],
                total_results=0,
            )

        # Build CONTAINS clauses for AntiPattern matching
        contains_clauses = []
        params: dict[str, Any] = {}
        for idx, kw in enumerate(keywords):
            param_name = f"kw{idx}"
            params[param_name] = kw
            contains_clauses.append(
                f"(toLower(ap.description) CONTAINS ${param_name} "
                f"OR toLower(ap.name) CONTAINS ${param_name} "
                f"OR toLower(ap.why_bad) CONTAINS ${param_name})"
            )

        where_clause = " OR ".join(contains_clauses)

        cypher = f"""
            MATCH (ap:AntiPattern)
            WHERE ({where_clause})
            OPTIONAL MATCH (p:Pattern)-[:ANTI_PATTERN_OF]->(ap)
            RETURN ap,
                   collect(DISTINCT p.name) AS associated_patterns
        """

        records = await execute_query(cypher, params)

        anti_patterns: list[AntiPatternMatch] = []
        for rec in records:
            ap = rec.get("ap", {})
            if isinstance(ap, dict):
                ap_props = ap
            else:
                ap_props = dict(ap) if ap else {}

            ap_name = ap_props.get("name", "")
            ap_desc = ap_props.get("description", "") or ""
            ap_why = ap_props.get("why_bad", "") or ""

            combined_text = f"{ap_name} {ap_desc} {ap_why}"
            confidence = compute_keyword_score(combined_text, keywords)
            if confidence <= 0.0:
                continue

            associated = rec.get("associated_patterns", [])
            # Filter out None values from associated patterns
            associated = [p for p in associated if p is not None]

            anti_patterns.append(AntiPatternMatch(
                anti_pattern_name=ap_name,
                description=ap_desc or None,
                why_bad=ap_why or None,
                better_alternative=ap_props.get("better_alternative"),
                associated_patterns=associated,
                confidence=confidence,
            ))

        # Sort by confidence descending
        anti_patterns.sort(key=lambda a: a.confidence, reverse=True)

        PATTERN_QUERIES_TOTAL.labels(endpoint="/patterns/anti-patterns", status="success").inc()
        log.info("anti_patterns_returned", count=len(anti_patterns))

        return AntiPatternResponse(
            code_description=code_description,
            keywords_extracted=keywords,
            anti_patterns=anti_patterns,
            total_results=len(anti_patterns),
        )

    except Exception as exc:
        PATTERN_QUERIES_TOTAL.labels(endpoint="/patterns/anti-patterns", status="error").inc()
        log.exception("anti_pattern_check_failed", error=str(exc))
        raise HTTPException(
            status_code=500,
            detail=f"Anti-pattern query failed: {exc}",
        ) from exc


# ---------------------------------------------------------------------------
# Endpoint 6: GET /patterns/for-principle/{principle}
# (Registered before /patterns/{name} to avoid path parameter capture)
# ---------------------------------------------------------------------------

@app.get("/patterns/for-principle/{principle}", response_model=PrincipleResponse)
async def get_patterns_for_principle(principle: str) -> PrincipleResponse:
    """Retrieve patterns that support or violate a given design principle.

    Searches for a Principle node by name and traverses the SUPPORTS
    and VIOLATES relationships to find all connected patterns.

    Args:
        principle: The principle name (e.g. 'Single Responsibility',
                   'Open/Closed', 'Liskov Substitution',
                   'Interface Segregation', 'Dependency Inversion').

    Returns:
        Lists of supporting and violating patterns for the principle.
    """
    log = logger.bind(principle=principle)
    log.info("principle_patterns_requested")

    try:
        cypher = """
            MATCH (prin:Principle)
            WHERE toLower(prin.name) = toLower($principle)

            OPTIONAL MATCH (sp:Pattern)-[s:SUPPORTS]->(prin)
            OPTIONAL MATCH (vp:Pattern)-[v:VIOLATES]->(prin)

            RETURN prin.name AS principle_name,
                   collect(DISTINCT {
                       name: sp.name,
                       description: sp.description,
                       how: s.how
                   }) AS supporting,
                   collect(DISTINCT {
                       name: vp.name,
                       description: vp.description,
                       when: v.when,
                       why: v.why
                   }) AS violating
        """

        record = await execute_single(cypher, {"principle": principle})

        if record is None or record.get("principle_name") is None:
            PATTERN_QUERIES_TOTAL.labels(
                endpoint="/patterns/for-principle/{principle}",
                status="not_found",
            ).inc()
            raise HTTPException(status_code=404, detail=f"Principle '{principle}' not found")

        supporting: list[PrinciplePatternEntry] = []
        for s in record.get("supporting", []):
            if isinstance(s, dict) and s.get("name"):
                supporting.append(PrinciplePatternEntry(
                    name=s["name"],
                    description=s.get("description"),
                    relationship="supports",
                    how=s.get("how"),
                ))

        violating: list[PrinciplePatternEntry] = []
        for v in record.get("violating", []):
            if isinstance(v, dict) and v.get("name"):
                violating.append(PrinciplePatternEntry(
                    name=v["name"],
                    description=v.get("description"),
                    relationship="violates",
                    when=v.get("when"),
                    why=v.get("why"),
                ))

        PATTERN_QUERIES_TOTAL.labels(
            endpoint="/patterns/for-principle/{principle}",
            status="success",
        ).inc()

        return PrincipleResponse(
            principle=record["principle_name"],
            supporting_patterns=supporting,
            violating_patterns=violating,
        )

    except HTTPException:
        raise
    except Exception as exc:
        PATTERN_QUERIES_TOTAL.labels(
            endpoint="/patterns/for-principle/{principle}",
            status="error",
        ).inc()
        log.exception("principle_patterns_failed", error=str(exc))
        raise HTTPException(
            status_code=500,
            detail=f"Principle patterns query failed: {exc}",
        ) from exc


# ---------------------------------------------------------------------------
# Endpoint 7: POST /patterns/path
# (Registered before /patterns/{name} to avoid path parameter capture)
# ---------------------------------------------------------------------------

@app.post("/patterns/path", response_model=PathResponse)
async def find_pattern_path(
    from_pattern: str = Query(..., alias="from", description="Source pattern name"),
    to_pattern: str = Query(..., alias="to", description="Target pattern name"),
) -> PathResponse:
    """Find the shortest path between two patterns.

    Uses Neo4j's shortestPath algorithm traversing RELATED_TO,
    EVOLVES_TO, and COMMONLY_USED_WITH relationships to discover
    the shortest connection between two design patterns.

    Args:
        from_pattern: Source pattern name (case-insensitive).
        to_pattern: Target pattern name (case-insensitive).

    Returns:
        The shortest path including all intermediate nodes and
        relationships, or an empty path if none exists.
    """
    log = logger.bind(from_pattern=from_pattern, to_pattern=to_pattern)
    log.info("pattern_path_requested")

    try:
        cypher = """
            MATCH (start:Pattern), (end:Pattern)
            WHERE toLower(start.name) = toLower($from) AND toLower(end.name) = toLower($to)
            MATCH path = shortestPath(
                (start)-[:RELATED_TO|EVOLVES_TO|COMMONLY_USED_WITH*..15]-(end)
            )
            RETURN path,
                   [n IN nodes(path) | {name: n.name, labels: labels(n)}] AS path_nodes,
                   [r IN relationships(path) | {type: type(r), properties: properties(r)}] AS path_rels,
                   length(path) AS path_length
        """

        record = await execute_single(
            cypher,
            {"from": from_pattern, "to": to_pattern},
        )

        if record is None:
            # Check if patterns exist
            check_cypher = """
                OPTIONAL MATCH (a:Pattern) WHERE toLower(a.name) = toLower($from)
                OPTIONAL MATCH (b:Pattern) WHERE toLower(b.name) = toLower($to)
                RETURN a.name AS from_exists, b.name AS to_exists
            """
            check = await execute_single(
                check_cypher,
                {"from": from_pattern, "to": to_pattern},
            )

            if check is None:
                PATTERN_QUERIES_TOTAL.labels(endpoint="/patterns/path", status="not_found").inc()
                raise HTTPException(
                    status_code=404,
                    detail=f"One or both patterns not found: '{from_pattern}', '{to_pattern}'",
                )

            if check.get("from_exists") is None:
                raise HTTPException(status_code=404, detail=f"Pattern '{from_pattern}' not found")
            if check.get("to_exists") is None:
                raise HTTPException(status_code=404, detail=f"Pattern '{to_pattern}' not found")

            # Both exist but no path between them
            PATTERN_QUERIES_TOTAL.labels(endpoint="/patterns/path", status="no_path").inc()
            return PathResponse(
                from_pattern=from_pattern,
                to_pattern=to_pattern,
                path_found=False,
                path_length=0,
                nodes=[],
                relationships=[],
            )

        # Parse path nodes
        path_nodes: list[PathNode] = []
        for node in record.get("path_nodes", []):
            if isinstance(node, dict):
                node_labels = node.get("labels", [])
                node_type = node_labels[0] if node_labels else "Unknown"
                path_nodes.append(PathNode(
                    name=node.get("name", ""),
                    type=node_type,
                ))

        # Parse path relationships
        path_rels: list[PathRelationship] = []
        for rel in record.get("path_rels", []):
            if isinstance(rel, dict):
                path_rels.append(PathRelationship(
                    type=rel.get("type", "UNKNOWN"),
                    properties=rel.get("properties", {}),
                ))

        PATTERN_QUERIES_TOTAL.labels(endpoint="/patterns/path", status="success").inc()

        return PathResponse(
            from_pattern=from_pattern,
            to_pattern=to_pattern,
            path_found=True,
            path_length=record.get("path_length", 0),
            nodes=path_nodes,
            relationships=path_rels,
        )

    except HTTPException:
        raise
    except Exception as exc:
        PATTERN_QUERIES_TOTAL.labels(endpoint="/patterns/path", status="error").inc()
        log.exception("pattern_path_failed", error=str(exc))
        raise HTTPException(
            status_code=500,
            detail=f"Path query failed: {exc}",
        ) from exc


# ---------------------------------------------------------------------------
# Endpoint 2: GET /patterns/{name}
# (Registered after static /patterns/* routes to avoid path capture)
# ---------------------------------------------------------------------------

@app.get("/patterns/{name}", response_model=PatternDetailResponse)
async def get_pattern_detail(name: str) -> PatternDetailResponse:
    """Retrieve full detail for a single design pattern.

    Executes a single Cypher query that collects all related data
    including category, implementations, principles (supports and
    violates), trade-offs, anti-patterns, related patterns,
    commonly-used-with patterns, and evolution targets.

    Args:
        name: The pattern name (case-insensitive match).

    Returns:
        Comprehensive pattern detail with all relationships.
    """
    log = logger.bind(pattern=name)
    log.info("pattern_detail_requested")

    try:
        cypher = """
            MATCH (p:Pattern)
            WHERE toLower(p.name) = toLower($name)

            OPTIONAL MATCH (p)-[:BELONGS_TO]->(cat:Category)

            OPTIONAL MATCH (p)-[:HAS_IMPLEMENTATION]->(impl:Implementation)-[:FOR_LANGUAGE]->(lang:Language)

            OPTIONAL MATCH (p)-[sp:SUPPORTS]->(sp_prin:Principle)
            OPTIONAL MATCH (p)-[vl:VIOLATES]->(vl_prin:Principle)

            OPTIONAL MATCH (p)-[:HAS_TRADEOFF]->(t:TradeOff)
            OPTIONAL MATCH (p)-[:ANTI_PATTERN_OF]->(ap:AntiPattern)

            OPTIONAL MATCH (p)-[rt:RELATED_TO]->(rp:Pattern)
            OPTIONAL MATCH (p)-[cuw:COMMONLY_USED_WITH]->(cup:Pattern)
            OPTIONAL MATCH (p)-[ev:EVOLVES_TO]->(ep:Pattern)

            RETURN p,
                   cat.name AS category,
                   collect(DISTINCT {
                       language: lang.name,
                       code_template: impl.code_template,
                       notes: impl.notes,
                       idioms: impl.idioms,
                       caveats: impl.caveats
                   }) AS implementations,
                   collect(DISTINCT {
                       name: sp_prin.name,
                       relationship: 'supports',
                       how: sp.how
                   }) AS supports,
                   collect(DISTINCT {
                       name: vl_prin.name,
                       relationship: 'violates',
                       when: vl.when,
                       why: vl.why
                   }) AS violates,
                   collect(DISTINCT {
                       benefit: t.benefit,
                       cost: t.cost,
                       context: t.context
                   }) AS tradeoffs,
                   collect(DISTINCT {
                       name: ap.name,
                       description: ap.description,
                       why_bad: ap.why_bad,
                       better_alternative: ap.better_alternative
                   }) AS antipatterns,
                   collect(DISTINCT {
                       name: rp.name,
                       description: rp.description,
                       relationship_type: rt.relationship_type
                   }) AS related,
                   collect(DISTINCT {
                       name: cup.name,
                       description: cup.description,
                       frequency: cuw.frequency,
                       example_context: cuw.example_context
                   }) AS commonly_used_with,
                   collect(DISTINCT {
                       name: ep.name,
                       description: ep.description,
                       evolution_trigger: ev.when
                   }) AS evolves_to
        """

        record = await execute_single(cypher, {"name": name})

        if record is None:
            PATTERN_QUERIES_TOTAL.labels(endpoint="/patterns/{name}", status="not_found").inc()
            raise HTTPException(status_code=404, detail=f"Pattern '{name}' not found")

        p = record.get("p", {})
        if isinstance(p, dict):
            p_props = p
        else:
            p_props = dict(p) if p else {}

        # Parse implementations
        impls_raw = record.get("implementations", [])
        implementations: list[ImplementationDetail] = []
        for i in impls_raw:
            if isinstance(i, dict) and i.get("language"):
                implementations.append(ImplementationDetail(
                    language=i["language"],
                    code_template=i.get("code_template"),
                    notes=i.get("notes"),
                    idioms=i.get("idioms"),
                    caveats=i.get("caveats"),
                ))

        # Parse principles (supports)
        principles: list[PrincipleDetail] = []
        for s in record.get("supports", []):
            if isinstance(s, dict) and s.get("name"):
                principles.append(PrincipleDetail(
                    name=s["name"],
                    relationship="supports",
                    how=s.get("how"),
                ))
        for v in record.get("violates", []):
            if isinstance(v, dict) and v.get("name"):
                principles.append(PrincipleDetail(
                    name=v["name"],
                    relationship="violates",
                    when=v.get("when"),
                    why=v.get("why"),
                ))

        # Parse trade-offs
        tradeoffs: list[TradeOffDetail] = []
        for t in record.get("tradeoffs", []):
            if isinstance(t, dict) and (t.get("benefit") or t.get("cost")):
                tradeoffs.append(TradeOffDetail(
                    benefit=t.get("benefit", ""),
                    cost=t.get("cost", ""),
                    context=t.get("context"),
                ))

        # Parse anti-patterns
        anti_patterns: list[AntiPatternDetail] = []
        for a in record.get("antipatterns", []):
            if isinstance(a, dict) and a.get("name"):
                anti_patterns.append(AntiPatternDetail(
                    name=a["name"],
                    description=a.get("description"),
                    why_bad=a.get("why_bad"),
                    better_alternative=a.get("better_alternative"),
                ))

        # Parse related patterns
        related: list[RelatedPatternDetail] = []
        for r in record.get("related", []):
            if isinstance(r, dict) and r.get("name"):
                related.append(RelatedPatternDetail(
                    name=r["name"],
                    description=r.get("description"),
                    relationship_type=r.get("relationship_type"),
                ))

        # Parse commonly used with
        commonly_used: list[RelatedPatternDetail] = []
        for c in record.get("commonly_used_with", []):
            if isinstance(c, dict) and c.get("name"):
                commonly_used.append(RelatedPatternDetail(
                    name=c["name"],
                    description=c.get("description"),
                    frequency=c.get("frequency"),
                    example_context=c.get("example_context"),
                ))

        # Parse evolves to
        evolves_to_list: list[RelatedPatternDetail] = []
        for e in record.get("evolves_to", []):
            if isinstance(e, dict) and e.get("name"):
                evolves_to_list.append(RelatedPatternDetail(
                    name=e["name"],
                    description=e.get("description"),
                    evolution_trigger=e.get("evolution_trigger"),
                ))

        PATTERN_QUERIES_TOTAL.labels(endpoint="/patterns/{name}", status="success").inc()

        return PatternDetailResponse(
            name=p_props.get("name", name),
            description=p_props.get("description"),
            intent=p_props.get("intent"),
            when_to_use=p_props.get("when_to_use"),
            when_not_to_use=p_props.get("when_not_to_use"),
            complexity=p_props.get("complexity"),
            frequency=p_props.get("frequency"),
            category=record.get("category"),
            implementations=implementations,
            principles=principles,
            trade_offs=tradeoffs,
            anti_patterns=anti_patterns,
            related_patterns=related,
            commonly_used_with=commonly_used,
            evolves_to=evolves_to_list,
        )

    except HTTPException:
        raise
    except Exception as exc:
        PATTERN_QUERIES_TOTAL.labels(endpoint="/patterns/{name}", status="error").inc()
        log.exception("pattern_detail_failed", error=str(exc))
        raise HTTPException(status_code=500, detail=f"Pattern detail query failed: {exc}") from exc


# ---------------------------------------------------------------------------
# Endpoint 3: GET /patterns/{name}/related
# ---------------------------------------------------------------------------

@app.get("/patterns/{name}/related", response_model=RelatedPatternsResponse)
async def get_related_patterns(name: str) -> RelatedPatternsResponse:
    """Retrieve all related patterns for a given pattern.

    Returns complementary, alternative, and prerequisite relationships
    via RELATED_TO, COMMONLY_USED_WITH, and EVOLVES_TO edges, plus
    reverse EVOLVES_TO (evolves-from) edges.

    Args:
        name: The pattern name (case-insensitive match).

    Returns:
        All related patterns grouped by relationship type.
    """
    log = logger.bind(pattern=name)
    log.info("related_patterns_requested")

    try:
        cypher = """
            MATCH (p:Pattern)
            WHERE toLower(p.name) = toLower($name)

            OPTIONAL MATCH (p)-[rt:RELATED_TO]->(rp:Pattern)
            OPTIONAL MATCH (p)-[cuw:COMMONLY_USED_WITH]->(cup:Pattern)
            OPTIONAL MATCH (p)-[ev:EVOLVES_TO]->(ep:Pattern)
            OPTIONAL MATCH (from_p:Pattern)-[ef:EVOLVES_TO]->(p)

            RETURN p.name AS pattern_name,
                   collect(DISTINCT {
                       name: rp.name,
                       description: rp.description,
                       relationship_type: rt.relationship_type
                   }) AS related_to,
                   collect(DISTINCT {
                       name: cup.name,
                       description: cup.description,
                       frequency: cuw.frequency,
                       example_context: cuw.example_context
                   }) AS commonly_used_with,
                   collect(DISTINCT {
                       name: ep.name,
                       description: ep.description,
                       evolution_trigger: ev.when
                   }) AS evolves_to,
                   collect(DISTINCT {
                       name: from_p.name,
                       description: from_p.description,
                       evolution_trigger: ef.when
                   }) AS evolves_from
        """

        record = await execute_single(cypher, {"name": name})

        if record is None or record.get("pattern_name") is None:
            PATTERN_QUERIES_TOTAL.labels(endpoint="/patterns/{name}/related", status="not_found").inc()
            raise HTTPException(status_code=404, detail=f"Pattern '{name}' not found")

        def parse_related(items: list[Any]) -> list[RelatedPatternDetail]:
            result: list[RelatedPatternDetail] = []
            for item in items:
                if isinstance(item, dict) and item.get("name"):
                    result.append(RelatedPatternDetail(
                        name=item["name"],
                        description=item.get("description"),
                        relationship_type=item.get("relationship_type"),
                        frequency=item.get("frequency"),
                        example_context=item.get("example_context"),
                        evolution_trigger=item.get("evolution_trigger"),
                    ))
            return result

        PATTERN_QUERIES_TOTAL.labels(endpoint="/patterns/{name}/related", status="success").inc()

        return RelatedPatternsResponse(
            pattern=record["pattern_name"],
            related_to=parse_related(record.get("related_to", [])),
            commonly_used_with=parse_related(record.get("commonly_used_with", [])),
            evolves_to=parse_related(record.get("evolves_to", [])),
            evolves_from=parse_related(record.get("evolves_from", [])),
        )

    except HTTPException:
        raise
    except Exception as exc:
        PATTERN_QUERIES_TOTAL.labels(endpoint="/patterns/{name}/related", status="error").inc()
        log.exception("related_patterns_failed", error=str(exc))
        raise HTTPException(status_code=500, detail=f"Related patterns query failed: {exc}") from exc


# ---------------------------------------------------------------------------
# Endpoint 4: GET /patterns/{name}/implementations/{language}
# ---------------------------------------------------------------------------

@app.get("/patterns/{name}/implementations/{language}", response_model=ImplementationResponse)
async def get_implementation(name: str, language: str) -> ImplementationResponse:
    """Retrieve a language-specific implementation for a pattern.

    Traverses the HAS_IMPLEMENTATION and FOR_LANGUAGE edges to find
    the implementation matching the requested language, including
    code template, notes, idioms, and caveats.

    Args:
        name: The pattern name (case-insensitive match).
        language: The programming language (case-insensitive match).

    Returns:
        Implementation details for the specified pattern and language.
    """
    log = logger.bind(pattern=name, language=language)
    log.info("implementation_requested")

    try:
        cypher = """
            MATCH (p:Pattern)-[:HAS_IMPLEMENTATION]->(impl:Implementation)-[:FOR_LANGUAGE]->(lang:Language)
            WHERE toLower(p.name) = toLower($name)
              AND toLower(lang.name) = toLower($language)
            RETURN p.name AS pattern_name,
                   lang.name AS language_name,
                   impl.code_template AS code_template,
                   impl.notes AS notes,
                   impl.idioms AS idioms,
                   impl.caveats AS caveats
        """

        record = await execute_single(cypher, {"name": name, "language": language})

        if record is None:
            # Distinguish: pattern doesn't exist vs. no implementation for language
            check_cypher = """
                MATCH (p:Pattern)
                WHERE toLower(p.name) = toLower($name)
                RETURN p.name AS pattern_name
            """
            check = await execute_single(check_cypher, {"name": name})
            if check is None:
                PATTERN_QUERIES_TOTAL.labels(
                    endpoint="/patterns/{name}/implementations/{language}",
                    status="not_found",
                ).inc()
                raise HTTPException(status_code=404, detail=f"Pattern '{name}' not found")

            PATTERN_QUERIES_TOTAL.labels(
                endpoint="/patterns/{name}/implementations/{language}",
                status="success",
            ).inc()
            return ImplementationResponse(
                pattern=check.get("pattern_name", name),
                language=language,
                implementation=None,
            )

        PATTERN_QUERIES_TOTAL.labels(
            endpoint="/patterns/{name}/implementations/{language}",
            status="success",
        ).inc()

        return ImplementationResponse(
            pattern=record.get("pattern_name", name),
            language=record.get("language_name", language),
            implementation=ImplementationDetail(
                language=record.get("language_name", language),
                code_template=record.get("code_template"),
                notes=record.get("notes"),
                idioms=record.get("idioms"),
                caveats=record.get("caveats"),
            ),
        )

    except HTTPException:
        raise
    except Exception as exc:
        PATTERN_QUERIES_TOTAL.labels(
            endpoint="/patterns/{name}/implementations/{language}",
            status="error",
        ).inc()
        log.exception("implementation_query_failed", error=str(exc))
        raise HTTPException(
            status_code=500,
            detail=f"Implementation query failed: {exc}",
        ) from exc


# ---------------------------------------------------------------------------
# Endpoint 8: GET /health
# ---------------------------------------------------------------------------

@app.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Service health check.

    Verifies that the API process is running and Neo4j connectivity is
    available. Returns healthy even if Neo4j is temporarily unreachable
    (the connection status is reported in the neo4j_connected field).

    Returns:
        Health status with Neo4j connectivity flag.
    """
    neo4j_ok = False
    try:
        driver = get_driver()
        await driver.verify_connectivity()
        neo4j_ok = True
    except Exception:
        logger.warning("health_check_neo4j_unreachable")

    return HealthResponse(
        status="healthy" if neo4j_ok else "degraded",
        service=SERVICE_NAME,
        version=SERVICE_VERSION,
        timestamp=datetime.now(timezone.utc).isoformat(),
        neo4j_connected=neo4j_ok,
    )


# ---------------------------------------------------------------------------
# Prometheus metrics endpoint
# ---------------------------------------------------------------------------

@app.get("/metrics")
async def metrics_endpoint() -> Response:
    """Expose Prometheus metrics in text exposition format.

    Returns:
        Prometheus text format metrics.
    """
    metrics_output = generate_latest(registry)
    return Response(
        content=metrics_output,
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )


# ---------------------------------------------------------------------------
# Global exception handler
# ---------------------------------------------------------------------------

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Global exception handler for unhandled errors.

    Logs the full exception and returns a sanitised 500 response.
    """
    logger.exception("unhandled_exception", path=request.url.path, error=str(exc))
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "service": SERVICE_NAME,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=SERVICE_PORT,
        log_level="info",
        access_log=True,
        reload=False,
        workers=1,
    )
