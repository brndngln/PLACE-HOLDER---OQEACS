"""
Neo4j GraphRAG: Pattern Query API (v2)
Omni Quantum Elite AI Coding System

Design pattern knowledge graph API consumed by Token Infinity.
Provides LiteLLM-based pattern recommendation, pattern CRUD, anti-pattern
detection, example retrieval, and graph statistics over Neo4j.

Port: 7475
Label: omni.quantum.component: neo4j-graphrag-api
"""

from __future__ import annotations

import os
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx
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
logger = structlog.get_logger("neo4j_graphrag.pattern_query_api_v2")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
NEO4J_URI: str = os.getenv("NEO4J_URI", "bolt://omni-neo4j:7687")
NEO4J_USER: str = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD: str = os.getenv("NEO4J_PASSWORD", "${NEO4J_PASSWORD}")
LITELLM_URL: str = os.getenv("LITELLM_URL", "http://omni-litellm:4000")
LITELLM_MODEL: str = os.getenv("LITELLM_MODEL", "gpt-4o-mini")

SERVICE_NAME: str = "neo4j-graphrag-api"
SERVICE_VERSION: str = "2.0.0"
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
# Pydantic models
# ---------------------------------------------------------------------------


class RecommendRequest(BaseModel):
    """POST body for /patterns/recommend."""
    task: str = Field(..., min_length=3, max_length=2000)
    language: Optional[str] = None
    limit: int = Field(default=5, ge=1, le=20)


class PatternSummary(BaseModel):
    name: str
    description: str
    category: str = ""
    complexity: str = ""
    confidence: float = 0.0


class RecommendResponse(BaseModel):
    task_description: str
    language: Optional[str] = None
    keywords: List[str] = Field(default_factory=list)
    patterns: List[PatternSummary] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class PatternDetailResponse(BaseModel):
    name: str
    description: str
    category: str = ""
    complexity: str = ""
    when_to_use: str = ""
    when_not_to_use: str = ""
    trade_offs: str = ""
    implementation_notes: str = ""
    related_patterns: List[Dict[str, Any]] = Field(default_factory=list)
    anti_patterns: List[Dict[str, Any]] = Field(default_factory=list)
    code_templates: Dict[str, str] = Field(default_factory=dict)


class PatternListItem(BaseModel):
    name: str
    description: str
    category: str = ""
    complexity: str = ""


class ExampleResponse(BaseModel):
    pattern_name: str
    codebase: str
    component: str = ""
    file_path: str = ""
    description: str = ""


class AntiPatternResponse(BaseModel):
    name: str
    description: str
    severity: str = ""
    fixed_by: str = ""


class GraphStatsResponse(BaseModel):
    patterns: int = 0
    categories: int = 0
    languages: int = 0
    codebases: int = 0
    anti_patterns: int = 0
    relationships: int = 0
    timestamp: str = ""


# ---------------------------------------------------------------------------
# Neo4j driver with retry
# ---------------------------------------------------------------------------
_driver: Optional[AsyncDriver] = None


async def get_driver() -> AsyncDriver:
    global _driver
    if _driver is None:
        _driver = AsyncGraphDatabase.driver(
            NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD)
        )
    return _driver


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=0.5, min=0.5, max=5),
    retry=retry_if_exception_type(Exception),
    reraise=True,
)
async def run_query(cypher: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """Execute a Cypher query with retry and return list of record dicts."""
    driver = await get_driver()
    async with driver.session() as session:
        result = await session.run(cypher, parameters=params or {})
        records = await result.data()
        return records


# ---------------------------------------------------------------------------
# LiteLLM keyword extraction
# ---------------------------------------------------------------------------

KEYWORD_EXTRACTION_PROMPT = """Extract design pattern keywords from this software task description.
Return ONLY a JSON array of lowercase keyword strings. No explanation.
Focus on: architectural patterns, design patterns, data access patterns, concurrency patterns,
resilience patterns, caching strategies, API styles, messaging patterns, security patterns.

Task: {task}

Examples of keywords: ["singleton", "factory", "repository", "circuit-breaker", "caching",
"rate-limiting", "retry", "event-driven", "rest", "grpc", "saga", "cqrs"]

JSON array:"""


async def extract_keywords_llm(task: str) -> List[str]:
    """Use LiteLLM proxy to extract pattern keywords from task description."""
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"{LITELLM_URL}/v1/chat/completions",
                json={
                    "model": LITELLM_MODEL,
                    "messages": [
                        {"role": "system", "content": "You extract design pattern keywords. Respond only with a JSON array."},
                        {"role": "user", "content": KEYWORD_EXTRACTION_PROMPT.format(task=task)},
                    ],
                    "temperature": 0.1,
                    "max_tokens": 200,
                },
            )
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"].strip()
            # Parse the JSON array from the response
            import json
            if content.startswith("["):
                keywords = json.loads(content)
                return [str(k).lower().strip() for k in keywords if isinstance(k, str)]
    except Exception as exc:
        logger.warning("llm_keyword_extraction_failed", error=str(exc))

    # Fallback: simple keyword extraction
    return extract_keywords_fallback(task)


# Synonym map for fallback keyword extraction
SYNONYM_MAP: Dict[str, List[str]] = {
    "singleton": ["singleton", "single instance", "global instance"],
    "factory": ["factory", "factory method", "abstract factory", "create object"],
    "builder": ["builder", "step-by-step construction", "fluent builder"],
    "prototype": ["prototype", "clone", "copy object"],
    "adapter": ["adapter", "wrapper", "translate interface"],
    "decorator": ["decorator", "wrapper", "add behavior", "middleware"],
    "facade": ["facade", "simplify interface", "unified api"],
    "proxy": ["proxy", "surrogate", "lazy load", "access control"],
    "observer": ["observer", "event", "publish subscribe", "pubsub", "listener"],
    "strategy": ["strategy", "algorithm", "interchangeable", "policy"],
    "command": ["command", "action", "undo redo", "transaction"],
    "iterator": ["iterator", "traverse", "cursor", "pagination"],
    "repository": ["repository", "data access", "persistence", "crud"],
    "unit-of-work": ["unit of work", "transaction", "batch commit"],
    "circuit-breaker": ["circuit breaker", "fault tolerance", "resilience"],
    "retry": ["retry", "backoff", "exponential backoff", "resilience"],
    "bulkhead": ["bulkhead", "isolation", "partition", "blast radius"],
    "saga": ["saga", "distributed transaction", "compensation", "choreography"],
    "cqrs": ["cqrs", "command query", "read model", "write model"],
    "event-sourcing": ["event sourcing", "event store", "replay"],
    "api-gateway": ["api gateway", "gateway", "routing", "aggregation"],
    "rate-limiter": ["rate limit", "throttle", "quota", "token bucket"],
    "cache-aside": ["cache aside", "lazy load cache", "cache"],
    "write-through": ["write through", "cache write"],
    "read-through": ["read through", "cache read"],
    "mutex": ["mutex", "lock", "mutual exclusion", "synchronization"],
    "semaphore": ["semaphore", "concurrent limit", "resource pool"],
    "actor-model": ["actor", "message passing", "erlang", "akka"],
    "pipeline": ["pipeline", "chain", "stage", "data flow"],
    "middleware": ["middleware", "interceptor", "filter chain"],
    "specification": ["specification", "business rule", "criteria", "query object"],
}

STOP_WORDS = frozenset({
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "shall", "can", "need", "must", "ought",
    "i", "me", "my", "we", "our", "you", "your", "he", "she", "it",
    "they", "them", "their", "this", "that", "these", "those", "which",
    "who", "whom", "what", "where", "when", "why", "how", "all", "each",
    "every", "both", "few", "more", "most", "other", "some", "such",
    "no", "nor", "not", "only", "own", "same", "so", "than", "too",
    "very", "just", "but", "and", "or", "if", "then", "else", "for",
    "on", "off", "in", "out", "up", "down", "to", "from", "by", "at",
    "of", "with", "about", "into", "through", "during", "before",
    "after", "above", "below", "between", "under", "over", "again",
    "use", "using", "build", "create", "make", "implement", "want",
    "service", "system", "application", "app", "code", "write",
})


def extract_keywords_fallback(task: str) -> List[str]:
    """Extract pattern keywords from task description using synonym matching."""
    task_lower = task.lower()
    keywords: List[str] = []

    for pattern_key, synonyms in SYNONYM_MAP.items():
        for synonym in synonyms:
            if synonym in task_lower:
                keywords.append(pattern_key)
                break

    # Also extract individual meaningful words for fulltext search
    import re
    words = re.findall(r"[a-z]+(?:-[a-z]+)*", task_lower)
    extra = [w for w in words if w not in STOP_WORDS and len(w) > 2]
    keywords.extend(extra)

    return list(dict.fromkeys(keywords))  # deduplicate preserving order


# ---------------------------------------------------------------------------
# Cypher query builders
# ---------------------------------------------------------------------------

RECOMMEND_CYPHER = """
CALL db.index.fulltext.queryNodes('pattern_search', $search_text)
YIELD node AS p, score
WHERE score > 0.5
WITH p, score
OPTIONAL MATCH (p)-[:BELONGS_TO]->(c:Category)
RETURN p.name AS name,
       p.description AS description,
       COALESCE(c.name, p.category_name, '') AS category,
       COALESCE(p.complexity, '') AS complexity,
       score AS confidence
ORDER BY score DESC
LIMIT $limit
"""

RECOMMEND_BY_CATEGORY_CYPHER = """
MATCH (p:Pattern)-[:BELONGS_TO]->(c:Category)
WHERE c.name = $category
RETURN p.name AS name,
       p.description AS description,
       c.name AS category,
       COALESCE(p.complexity, '') AS complexity,
       1.0 AS confidence
ORDER BY p.name
LIMIT $limit
"""

ALL_PATTERNS_CYPHER = """
MATCH (p:Pattern)
OPTIONAL MATCH (p)-[:BELONGS_TO]->(c:Category)
RETURN p.name AS name,
       p.description AS description,
       COALESCE(c.name, p.category_name, '') AS category,
       COALESCE(p.complexity, '') AS complexity
ORDER BY category, name
"""

PATTERN_DETAIL_CYPHER = """
MATCH (p:Pattern {name: $name})
OPTIONAL MATCH (p)-[:BELONGS_TO]->(c:Category)
OPTIONAL MATCH (p)-[r1:OFTEN_COMBINED_WITH]-(related:Pattern)
OPTIONAL MATCH (ap:AntiPattern)-[:FIXED_BY]->(p)
RETURN p,
       COALESCE(c.name, p.category_name, '') AS category,
       collect(DISTINCT {name: related.name, description: related.description}) AS related_patterns,
       collect(DISTINCT {name: ap.name, description: ap.description, severity: ap.severity}) AS anti_patterns
"""

PATTERN_EXAMPLES_CYPHER = """
MATCH (p:Pattern {name: $name})-[impl:IMPLEMENTED_IN]->(cb:Codebase)
RETURN cb.name AS codebase,
       COALESCE(impl.component, '') AS component,
       COALESCE(impl.file_path, '') AS file_path,
       COALESCE(cb.description, '') AS description
ORDER BY cb.name
"""

ALL_ANTIPATTERNS_CYPHER = """
MATCH (ap:AntiPattern)
OPTIONAL MATCH (ap)-[:FIXED_BY]->(p:Pattern)
RETURN ap.name AS name,
       ap.description AS description,
       COALESCE(ap.severity, '') AS severity,
       COALESCE(p.name, '') AS fixed_by
ORDER BY ap.severity DESC, ap.name
"""

ANTIPATTERNS_FOR_TASK_CYPHER = """
CALL db.index.fulltext.queryNodes('pattern_search', $search_text)
YIELD node AS p, score
WHERE score > 0.3
WITH p
MATCH (ap:AntiPattern)-[:FIXED_BY]->(p)
RETURN DISTINCT ap.name AS name,
       ap.description AS description,
       COALESCE(ap.severity, '') AS severity,
       p.name AS fixed_by
ORDER BY ap.severity DESC
"""

GRAPH_STATS_CYPHER = """
MATCH (p:Pattern) WITH count(p) AS patterns
MATCH (c:Category) WITH patterns, count(c) AS categories
MATCH (l:Language) WITH patterns, categories, count(l) AS languages
MATCH (cb:Codebase) WITH patterns, categories, languages, count(cb) AS codebases
MATCH (ap:AntiPattern) WITH patterns, categories, languages, codebases, count(ap) AS anti_patterns
MATCH ()-[r]->() WITH patterns, categories, languages, codebases, anti_patterns, count(r) AS relationships
RETURN patterns, categories, languages, codebases, anti_patterns, relationships
"""


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("starting_pattern_query_api", version=SERVICE_VERSION, port=SERVICE_PORT)
    driver = await get_driver()
    try:
        info = await driver.get_server_info()
        logger.info("neo4j_connected", server=str(info.address), agent=info.agent)
    except Exception as exc:
        logger.error("neo4j_connection_failed", error=str(exc))
    yield
    logger.info("shutting_down_pattern_query_api")
    if _driver is not None:
        await _driver.close()


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Neo4j GraphRAG Pattern Query API",
    description="Design pattern knowledge graph API for Omni Quantum Elite",
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
# Middleware: request timing
# ---------------------------------------------------------------------------

@app.middleware("http")
async def timing_middleware(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    elapsed = time.perf_counter() - start
    response.headers["X-Process-Time"] = f"{elapsed:.4f}"
    return response


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.post("/patterns/recommend", response_model=RecommendResponse)
async def recommend_patterns(body: RecommendRequest):
    """Recommend design patterns for a task using LiteLLM keyword extraction."""
    t0 = time.perf_counter()
    language = body.language
    lang_label = language or "any"

    try:
        keywords = await extract_keywords_llm(body.task)

        if not keywords:
            PATTERN_RECOMMENDATIONS_TOTAL.labels(language=lang_label, status="no_keywords").inc()
            return RecommendResponse(
                task_description=body.task,
                language=language,
                keywords=[],
                patterns=[],
                warnings=["No relevant keywords extracted from task description."],
            )

        # Build fulltext search string from keywords
        search_text = " OR ".join(keywords[:10])

        records = await run_query(RECOMMEND_CYPHER, {"search_text": search_text, "limit": body.limit})

        # If language filter specified, try to boost patterns implemented in that language
        if language and records:
            lang_boost_query = """
            UNWIND $names AS pname
            MATCH (p:Pattern {name: pname})-[:HAS_TEMPLATE_FOR]->(l:Language {name: $lang})
            RETURN p.name AS name
            """
            boosted = await run_query(
                lang_boost_query,
                {"names": [r["name"] for r in records], "lang": language.lower()},
            )
            boosted_names = {r["name"] for r in boosted}
            # Move boosted patterns to the top while preserving relative order
            top = [r for r in records if r["name"] in boosted_names]
            rest = [r for r in records if r["name"] not in boosted_names]
            records = top + rest

        patterns = [
            PatternSummary(
                name=r["name"],
                description=r.get("description", ""),
                category=r.get("category", ""),
                complexity=r.get("complexity", ""),
                confidence=round(float(r.get("confidence", 0.0)), 3),
            )
            for r in records
        ]

        warnings: List[str] = []
        if len(patterns) == 0:
            warnings.append("No patterns matched the extracted keywords.")

        PATTERN_RECOMMENDATIONS_TOTAL.labels(language=lang_label, status="ok").inc()
        PATTERN_QUERY_LATENCY.labels(endpoint="recommend").observe(time.perf_counter() - t0)

        return RecommendResponse(
            task_description=body.task,
            language=language,
            keywords=keywords,
            patterns=patterns,
            warnings=warnings,
        )

    except Exception as exc:
        PATTERN_RECOMMENDATIONS_TOTAL.labels(language=lang_label, status="error").inc()
        logger.error("recommend_failed", error=str(exc), task=body.task[:100])
        raise HTTPException(status_code=500, detail=f"Recommendation failed: {exc}")


@app.get("/patterns", response_model=List[PatternListItem])
async def list_patterns(
    category: Optional[str] = Query(None, description="Filter by category name"),
    limit: int = Query(100, ge=1, le=200),
):
    """List all patterns, optionally filtered by category."""
    t0 = time.perf_counter()
    try:
        if category:
            records = await run_query(RECOMMEND_BY_CATEGORY_CYPHER, {"category": category, "limit": limit})
        else:
            records = await run_query(ALL_PATTERNS_CYPHER)
            records = records[:limit]

        PATTERN_QUERIES_TOTAL.labels(endpoint="list_patterns", status="ok").inc()
        PATTERN_QUERY_LATENCY.labels(endpoint="list_patterns").observe(time.perf_counter() - t0)

        return [
            PatternListItem(
                name=r["name"],
                description=r.get("description", ""),
                category=r.get("category", ""),
                complexity=r.get("complexity", ""),
            )
            for r in records
        ]
    except Exception as exc:
        PATTERN_QUERIES_TOTAL.labels(endpoint="list_patterns", status="error").inc()
        logger.error("list_patterns_failed", error=str(exc))
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/patterns/{name}", response_model=PatternDetailResponse)
async def get_pattern(name: str):
    """Get full detail for a single pattern including relationships and code templates."""
    t0 = time.perf_counter()
    try:
        records = await run_query(PATTERN_DETAIL_CYPHER, {"name": name})
        if not records:
            PATTERN_QUERIES_TOTAL.labels(endpoint="get_pattern", status="not_found").inc()
            raise HTTPException(status_code=404, detail=f"Pattern '{name}' not found")

        row = records[0]
        p = row["p"]

        # Extract code templates from pattern properties
        code_templates: Dict[str, str] = {}
        for key in p:
            if key.startswith("code_template_"):
                lang_name = key.replace("code_template_", "")
                code_templates[lang_name] = p[key]
            elif key == "test_template":
                code_templates["test"] = p[key]

        # Filter out empty related patterns
        related = [r for r in row.get("related_patterns", []) if r.get("name")]
        antis = [a for a in row.get("anti_patterns", []) if a.get("name")]

        PATTERN_QUERIES_TOTAL.labels(endpoint="get_pattern", status="ok").inc()
        PATTERN_QUERY_LATENCY.labels(endpoint="get_pattern").observe(time.perf_counter() - t0)

        return PatternDetailResponse(
            name=p.get("name", name),
            description=p.get("description", ""),
            category=row.get("category", ""),
            complexity=p.get("complexity", ""),
            when_to_use=p.get("when_to_use", ""),
            when_not_to_use=p.get("when_not_to_use", ""),
            trade_offs=p.get("trade_offs", ""),
            implementation_notes=p.get("implementation_notes", ""),
            related_patterns=related,
            anti_patterns=antis,
            code_templates=code_templates,
        )
    except HTTPException:
        raise
    except Exception as exc:
        PATTERN_QUERIES_TOTAL.labels(endpoint="get_pattern", status="error").inc()
        logger.error("get_pattern_failed", pattern=name, error=str(exc))
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/patterns/{name}/examples", response_model=List[ExampleResponse])
async def get_pattern_examples(name: str):
    """Get real-world codebase examples for a pattern."""
    t0 = time.perf_counter()
    try:
        records = await run_query(PATTERN_EXAMPLES_CYPHER, {"name": name})
        if not records:
            # Check if the pattern exists
            check = await run_query("MATCH (p:Pattern {name: $name}) RETURN p.name", {"name": name})
            if not check:
                raise HTTPException(status_code=404, detail=f"Pattern '{name}' not found")

        PATTERN_QUERIES_TOTAL.labels(endpoint="get_examples", status="ok").inc()
        PATTERN_QUERY_LATENCY.labels(endpoint="get_examples").observe(time.perf_counter() - t0)

        return [
            ExampleResponse(
                pattern_name=name,
                codebase=r.get("codebase", ""),
                component=r.get("component", ""),
                file_path=r.get("file_path", ""),
                description=r.get("description", ""),
            )
            for r in records
        ]
    except HTTPException:
        raise
    except Exception as exc:
        PATTERN_QUERIES_TOTAL.labels(endpoint="get_examples", status="error").inc()
        logger.error("get_examples_failed", pattern=name, error=str(exc))
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/antipatterns", response_model=List[AntiPatternResponse])
async def list_antipatterns():
    """List all known anti-patterns."""
    t0 = time.perf_counter()
    try:
        records = await run_query(ALL_ANTIPATTERNS_CYPHER)
        PATTERN_QUERIES_TOTAL.labels(endpoint="list_antipatterns", status="ok").inc()
        PATTERN_QUERY_LATENCY.labels(endpoint="list_antipatterns").observe(time.perf_counter() - t0)

        return [
            AntiPatternResponse(
                name=r["name"],
                description=r.get("description", ""),
                severity=r.get("severity", ""),
                fixed_by=r.get("fixed_by", ""),
            )
            for r in records
        ]
    except Exception as exc:
        PATTERN_QUERIES_TOTAL.labels(endpoint="list_antipatterns", status="error").inc()
        logger.error("list_antipatterns_failed", error=str(exc))
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/antipatterns/for-task", response_model=List[AntiPatternResponse])
async def antipatterns_for_task(
    task: str = Query(..., min_length=3, description="Task or code description"),
):
    """Find anti-patterns relevant to a task description."""
    t0 = time.perf_counter()
    try:
        keywords = await extract_keywords_llm(task)
        search_text = " OR ".join(keywords[:10]) if keywords else task
        records = await run_query(ANTIPATTERNS_FOR_TASK_CYPHER, {"search_text": search_text})

        PATTERN_QUERIES_TOTAL.labels(endpoint="antipatterns_for_task", status="ok").inc()
        PATTERN_QUERY_LATENCY.labels(endpoint="antipatterns_for_task").observe(time.perf_counter() - t0)

        return [
            AntiPatternResponse(
                name=r["name"],
                description=r.get("description", ""),
                severity=r.get("severity", ""),
                fixed_by=r.get("fixed_by", ""),
            )
            for r in records
        ]
    except Exception as exc:
        PATTERN_QUERIES_TOTAL.labels(endpoint="antipatterns_for_task", status="error").inc()
        logger.error("antipatterns_for_task_failed", error=str(exc))
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/graph/stats", response_model=GraphStatsResponse)
async def graph_stats():
    """Return counts of all node and relationship types in the pattern graph."""
    t0 = time.perf_counter()
    try:
        records = await run_query(GRAPH_STATS_CYPHER)
        if not records:
            return GraphStatsResponse(timestamp=datetime.now(timezone.utc).isoformat())

        row = records[0]
        PATTERN_QUERIES_TOTAL.labels(endpoint="graph_stats", status="ok").inc()
        PATTERN_QUERY_LATENCY.labels(endpoint="graph_stats").observe(time.perf_counter() - t0)

        return GraphStatsResponse(
            patterns=row.get("patterns", 0),
            categories=row.get("categories", 0),
            languages=row.get("languages", 0),
            codebases=row.get("codebases", 0),
            anti_patterns=row.get("anti_patterns", 0),
            relationships=row.get("relationships", 0),
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
    except Exception as exc:
        PATTERN_QUERIES_TOTAL.labels(endpoint="graph_stats", status="error").inc()
        logger.error("graph_stats_failed", error=str(exc))
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# Health / Ready / Metrics
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    """Liveness probe."""
    return {"status": "ok", "service": SERVICE_NAME, "version": SERVICE_VERSION}


@app.get("/ready")
async def ready():
    """Readiness probe — verifies Neo4j connectivity."""
    try:
        driver = await get_driver()
        async with driver.session() as session:
            result = await session.run("RETURN 1 AS n")
            await result.single()
        return {"status": "ready", "neo4j": "connected"}
    except Exception as exc:
        logger.error("readiness_check_failed", error=str(exc))
        return JSONResponse(
            status_code=503,
            content={"status": "not_ready", "neo4j": str(exc)},
        )


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    return Response(
        content=generate_latest(registry),
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )
