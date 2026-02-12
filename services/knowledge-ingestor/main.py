"""Knowledge Ingestor — Core ingestion pipeline for the Omni Quantum Elite knowledge layer.

Ingests Git repositories, academic papers, technical blogs, and post-mortems into
Qdrant vector collections with rich metadata from AST parsing. All operations are
traced via Langfuse and reported through Prometheus metrics.
"""

from __future__ import annotations

import asyncio
import hashlib
import os
import shutil
import tempfile
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from enum import Enum
from fnmatch import fnmatch
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
import structlog
import tiktoken
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from bs4 import BeautifulSoup
from fastapi import FastAPI, HTTPException
from git import Repo as GitRepo
from langfuse import Langfuse
from markdownify import markdownify
from minio import Minio
from prometheus_client import Counter, Gauge, Histogram, generate_latest
from pydantic import BaseModel, Field
from pypdf import PdfReader
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams
from starlette.responses import Response
from tenacity import retry, stop_after_attempt, wait_exponential

from parsers.ast_parser import ASTParser

logger = structlog.get_logger()

# ─────────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────────

QDRANT_URL = os.getenv("QDRANT_URL", "http://omni-qdrant:6333")
LITELLM_URL = os.getenv("LITELLM_URL", "http://omni-litellm:4000")
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "omni-minio:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin")
MATTERMOST_WEBHOOK_URL = os.getenv("MATTERMOST_WEBHOOK_URL", "http://omni-mattermost-webhook:8066")
LANGFUSE_URL = os.getenv("LANGFUSE_URL", "http://omni-langfuse:3000")
LANGFUSE_PUBLIC_KEY = os.getenv("LANGFUSE_PUBLIC_KEY", "")
LANGFUSE_SECRET_KEY = os.getenv("LANGFUSE_SECRET_KEY", "")
WORKSPACE_DIR = os.getenv("WORKSPACE_DIR", "/workspace")
TEMP_DIR = os.getenv("TEMP_DIR", "/tmp/ingestor")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
EMBEDDING_DIM = 1536
KNOWLEDGE_BUCKET = "omni-knowledge-base"
DEFAULT_CONCURRENCY = 3

# ─────────────────────────────────────────────────────────────────────────────
# Prometheus Metrics
# ─────────────────────────────────────────────────────────────────────────────

INGESTION_DOCUMENTS = Counter(
    "ingestion_documents_total", "Total documents ingested", ["source", "collection"]
)
INGESTION_CHUNKS = Counter(
    "ingestion_chunks_total", "Total chunks created", ["source", "collection"]
)
INGESTION_EMBEDDINGS = Counter(
    "ingestion_embeddings_total", "Total embeddings generated", ["source", "collection"]
)
INGESTION_ERRORS = Counter(
    "ingestion_errors_total", "Total ingestion errors", ["source", "error_type"]
)
INGESTION_DURATION = Histogram(
    "ingestion_duration_seconds", "Ingestion duration", ["source"]
)
INGESTION_QUEUE_DEPTH = Gauge(
    "ingestion_queue_depth", "Current queue depth"
)

# ─────────────────────────────────────────────────────────────────────────────
# Pydantic Models
# ─────────────────────────────────────────────────────────────────────────────


class ChunkStrategy(str, Enum):
    AST = "ast"
    FILE = "file"
    FUNCTION = "function"
    CLASS = "class"


class RepositoryRequest(BaseModel):
    """Request to ingest a Git repository."""
    source_url: str
    source_name: str
    source_category: str = "general"
    branch: str = "main"
    languages: List[str] = Field(default_factory=lambda: ["python"])
    file_patterns: List[str] = Field(default_factory=lambda: ["*.*"])
    exclude_patterns: List[str] = Field(default_factory=list)
    collection: str = "elite_codebases"
    chunk_strategy: ChunkStrategy = ChunkStrategy.AST
    max_files: Optional[int] = None
    tags: List[str] = Field(default_factory=list)


class PaperRequest(BaseModel):
    """Request to ingest an academic paper."""
    pdf_url: str
    title: str
    authors: List[str] = Field(default_factory=list)
    year: int = 2024
    venue: str = ""
    domain: str = "computer-science"
    tags: List[str] = Field(default_factory=list)


class BlogRequest(BaseModel):
    """Request to ingest a technical blog post."""
    url: str
    source: str = ""
    domain: str = "engineering"
    tags: List[str] = Field(default_factory=list)


class PostmortemRequest(BaseModel):
    """Request to ingest a post-mortem."""
    url: str
    source: str = ""
    incident_date: Optional[str] = None
    impact: str = ""
    root_cause: str = ""
    resolution: str = ""
    lessons_learned: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)


class BatchRequest(BaseModel):
    """Request to trigger batch ingestion from sources-config.yaml."""
    concurrency: int = DEFAULT_CONCURRENCY


class IngestionSummary(BaseModel):
    """Summary of an ingestion job."""
    job_id: str
    source_name: str
    status: str
    files_processed: int = 0
    chunks_created: int = 0
    embeddings_generated: int = 0
    errors: int = 0
    duration_seconds: float = 0.0
    started_at: str = ""
    completed_at: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str


# ─────────────────────────────────────────────────────────────────────────────
# Ingestion Engine
# ─────────────────────────────────────────────────────────────────────────────

class IngestionEngine:
    """Core engine handling all ingestion operations."""

    def __init__(self) -> None:
        self.ast_parser = ASTParser()
        self.qdrant: Optional[QdrantClient] = None
        self.minio_client: Optional[Minio] = None
        self.http_client: Optional[httpx.AsyncClient] = None
        self.langfuse: Optional[Langfuse] = None
        self.tokenizer = tiktoken.get_encoding("cl100k_base")
        self._jobs: Dict[str, IngestionSummary] = {}
        self._embedding_cache: Dict[str, List[float]] = {}

    async def initialize(self) -> None:
        """Initialize all external connections."""
        self.qdrant = QdrantClient(url=QDRANT_URL, timeout=60)
        self.minio_client = Minio(
            MINIO_ENDPOINT,
            access_key=MINIO_ACCESS_KEY,
            secret_key=MINIO_SECRET_KEY,
            secure=False,
        )
        self.http_client = httpx.AsyncClient(timeout=60.0)
        if LANGFUSE_PUBLIC_KEY:
            try:
                self.langfuse = Langfuse(
                    public_key=LANGFUSE_PUBLIC_KEY,
                    secret_key=LANGFUSE_SECRET_KEY,
                    host=LANGFUSE_URL,
                )
            except Exception as e:
                logger.warning("langfuse_init_failed", error=str(e))

        self._ensure_minio_bucket()
        self._ensure_qdrant_collections()
        os.makedirs(WORKSPACE_DIR, exist_ok=True)
        os.makedirs(TEMP_DIR, exist_ok=True)
        logger.info("ingestion_engine_initialized")

    def _ensure_minio_bucket(self) -> None:
        """Create MinIO bucket if it doesn't exist."""
        try:
            if not self.minio_client.bucket_exists(KNOWLEDGE_BUCKET):
                self.minio_client.make_bucket(KNOWLEDGE_BUCKET)
                logger.info("minio_bucket_created", bucket=KNOWLEDGE_BUCKET)
        except Exception as e:
            logger.warning("minio_bucket_check_failed", error=str(e))

    def _ensure_qdrant_collections(self) -> None:
        """Ensure all target Qdrant collections exist."""
        collections = [
            "elite_codebases", "design_patterns", "anti_patterns",
            "human_feedback", "academic_papers", "project_context",
            "codebase_embeddings",
        ]
        existing = {c.name for c in self.qdrant.get_collections().collections}
        for coll in collections:
            if coll not in existing:
                self.qdrant.create_collection(
                    collection_name=coll,
                    vectors_config=VectorParams(size=EMBEDDING_DIM, distance=Distance.COSINE),
                )
                logger.info("qdrant_collection_created", collection=coll)

    async def shutdown(self) -> None:
        """Clean up connections."""
        if self.http_client:
            await self.http_client.aclose()
        if self.langfuse:
            try:
                self.langfuse.flush()
            except Exception:
                pass

    # ── Embedding generation ──────────────────────────────────────────────

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    async def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding via LiteLLM, with caching to avoid regeneration."""
        text_hash = hashlib.sha256(text.encode()).hexdigest()
        if text_hash in self._embedding_cache:
            return self._embedding_cache[text_hash]

        truncated = " ".join(text.split()[:8000])
        resp = await self.http_client.post(
            f"{LITELLM_URL}/embeddings",
            json={"model": EMBEDDING_MODEL, "input": truncated},
        )
        resp.raise_for_status()
        embedding = resp.json()["data"][0]["embedding"]
        self._embedding_cache[text_hash] = embedding

        if len(self._embedding_cache) > 10000:
            keys = list(self._embedding_cache.keys())[:5000]
            for k in keys:
                del self._embedding_cache[k]

        return embedding

    # ── Deduplication ─────────────────────────────────────────────────────

    def _check_dedup(
        self, collection: str, file_path: str, function_name: str, content_hash: str
    ) -> Optional[str]:
        """Check if a chunk already exists. Returns 'skip', 'update', or None (new)."""
        try:
            results = self.qdrant.scroll(
                collection_name=collection,
                scroll_filter={
                    "must": [
                        {"key": "file_path", "match": {"value": file_path}},
                        {"key": "function_name", "match": {"value": function_name}},
                    ]
                },
                limit=1,
                with_payload=True,
            )
            points = results[0]
            if points:
                existing_hash = points[0].payload.get("content_hash", "")
                if existing_hash == content_hash:
                    return "skip"
                return "update"
        except Exception:
            pass
        return None

    # ── Text chunking helpers ─────────────────────────────────────────────

    def _chunk_text(self, text: str, max_tokens: int = 500) -> List[str]:
        """Split text into chunks of approximately max_tokens, respecting paragraph boundaries."""
        paragraphs = text.split("\n\n")
        chunks: List[str] = []
        current: List[str] = []
        current_tokens = 0

        for para in paragraphs:
            para_tokens = len(self.tokenizer.encode(para))
            if current_tokens + para_tokens > max_tokens and current:
                chunks.append("\n\n".join(current))
                current = []
                current_tokens = 0
            current.append(para)
            current_tokens += para_tokens

        if current:
            chunks.append("\n\n".join(current))

        return chunks

    # ── Repository ingestion ──────────────────────────────────────────────

    async def ingest_repository(self, req: RepositoryRequest) -> IngestionSummary:
        """Ingest a Git repository: clone, parse, embed, upsert to Qdrant."""
        job_id = str(uuid.uuid4())[:8]
        job = IngestionSummary(
            job_id=job_id,
            source_name=req.source_name,
            status="running",
            started_at=datetime.now(timezone.utc).isoformat(),
        )
        self._jobs[job_id] = job
        INGESTION_QUEUE_DEPTH.inc()

        trace = None
        if self.langfuse:
            trace = self.langfuse.trace(name=f"ingest_repo_{req.source_name}")

        start = time.time()
        repo_dir = os.path.join(WORKSPACE_DIR, req.source_name)

        try:
            # 1. Clone or update
            if os.path.exists(repo_dir):
                logger.info("repo_update", source=req.source_name, path=repo_dir)
                repo = GitRepo(repo_dir)
                repo.remotes.origin.pull()
            else:
                logger.info("repo_clone", source=req.source_name, url=req.source_url)
                GitRepo.clone_from(
                    req.source_url, repo_dir,
                    branch=req.branch, depth=1,
                )

            # 2. Walk file tree
            files_to_process: List[Path] = []
            for root, _dirs, filenames in os.walk(repo_dir):
                rel_root = os.path.relpath(root, repo_dir)
                if any(fnmatch(rel_root, ep.rstrip("/*")) for ep in req.exclude_patterns):
                    continue
                if ".git" in root.split(os.sep):
                    continue
                for fname in filenames:
                    rel_path = os.path.join(rel_root, fname)
                    if any(fnmatch(rel_path, ep) for ep in req.exclude_patterns):
                        continue
                    if any(fnmatch(fname, fp) for fp in req.file_patterns):
                        files_to_process.append(Path(root) / fname)

            if req.max_files:
                files_to_process = files_to_process[:req.max_files]

            logger.info("files_found", source=req.source_name, count=len(files_to_process))

            # 3. Process each file
            dedup_stats = {"skipped": 0, "updated": 0, "inserted": 0}
            for file_path in files_to_process:
                try:
                    source_code = file_path.read_text(encoding="utf-8", errors="replace")
                    if not source_code.strip():
                        continue

                    rel_path = str(file_path.relative_to(repo_dir))
                    lang = self._detect_language(file_path.suffix, req.languages)

                    if req.chunk_strategy == ChunkStrategy.AST and lang:
                        chunks = self.ast_parser.parse_file(source_code, lang, rel_path)
                    else:
                        chunks = self.ast_parser._fallback_file_chunk(source_code, lang or "text", rel_path)

                    job.files_processed += 1
                    INGESTION_DOCUMENTS.labels(source=req.source_name, collection=req.collection).inc()

                    for chunk in chunks:
                        dedup = self._check_dedup(
                            req.collection, chunk.file_path, chunk.name, chunk.content_hash
                        )
                        if dedup == "skip":
                            dedup_stats["skipped"] += 1
                            continue

                        embedding_text = chunk.embedding_text()
                        embedding = await self._generate_embedding(embedding_text)

                        metadata = chunk.to_metadata()
                        metadata["source_name"] = req.source_name
                        metadata["source_category"] = req.source_category
                        metadata["source_url"] = req.source_url
                        metadata["tags"] = req.tags + chunk.pattern_tags
                        metadata["ingested_at"] = datetime.now(timezone.utc).isoformat()

                        point_id = uuid.uuid4().hex
                        self.qdrant.upsert(
                            collection_name=req.collection,
                            points=[
                                PointStruct(
                                    id=point_id,
                                    vector=embedding,
                                    payload=metadata,
                                )
                            ],
                        )

                        job.chunks_created += 1
                        job.embeddings_generated += 1
                        INGESTION_CHUNKS.labels(source=req.source_name, collection=req.collection).inc()
                        INGESTION_EMBEDDINGS.labels(source=req.source_name, collection=req.collection).inc()

                        if dedup == "update":
                            dedup_stats["updated"] += 1
                        else:
                            dedup_stats["inserted"] += 1

                except Exception as e:
                    job.errors += 1
                    INGESTION_ERRORS.labels(source=req.source_name, error_type="file_parse").inc()
                    logger.error("file_process_error", file=str(file_path), error=str(e))

            # 4. Store raw repo metadata in MinIO
            self._store_source_metadata(req.source_name, {
                "source_url": req.source_url,
                "source_name": req.source_name,
                "branch": req.branch,
                "languages": req.languages,
                "collection": req.collection,
                "files_processed": job.files_processed,
                "chunks_created": job.chunks_created,
                "dedup_stats": dedup_stats,
                "ingested_at": datetime.now(timezone.utc).isoformat(),
            })

            job.status = "completed"

        except Exception as e:
            job.status = "failed"
            job.errors += 1
            INGESTION_ERRORS.labels(source=req.source_name, error_type="repo_clone").inc()
            logger.error("repo_ingestion_failed", source=req.source_name, error=str(e))

        finally:
            duration = time.time() - start
            job.duration_seconds = round(duration, 2)
            job.completed_at = datetime.now(timezone.utc).isoformat()
            INGESTION_DURATION.labels(source=req.source_name).observe(duration)
            INGESTION_QUEUE_DEPTH.dec()
            if trace:
                trace.update(output={"status": job.status, "chunks": job.chunks_created})

        logger.info(
            "repo_ingestion_complete",
            source=req.source_name,
            status=job.status,
            files=job.files_processed,
            chunks=job.chunks_created,
            errors=job.errors,
            duration=job.duration_seconds,
        )
        return job

    # ── Paper ingestion ───────────────────────────────────────────────────

    async def ingest_paper(self, req: PaperRequest) -> IngestionSummary:
        """Ingest an academic paper PDF into the academic_papers collection."""
        job_id = str(uuid.uuid4())[:8]
        job = IngestionSummary(
            job_id=job_id,
            source_name=req.title,
            status="running",
            started_at=datetime.now(timezone.utc).isoformat(),
        )
        self._jobs[job_id] = job
        INGESTION_QUEUE_DEPTH.inc()
        start = time.time()

        trace = None
        if self.langfuse:
            trace = self.langfuse.trace(name=f"ingest_paper_{req.title[:40]}")

        try:
            # Download PDF
            resp = await self.http_client.get(req.pdf_url, follow_redirects=True)
            resp.raise_for_status()
            pdf_path = os.path.join(TEMP_DIR, f"{job_id}.pdf")
            with open(pdf_path, "wb") as f:
                f.write(resp.content)

            # Extract text
            reader = PdfReader(pdf_path)
            full_text = ""
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    full_text += text + "\n"

            if not full_text.strip():
                raise ValueError("No text extracted from PDF")

            # Split into sections
            sections = self._split_paper_sections(full_text)
            job.files_processed = 1

            for section_name, section_text in sections.items():
                if not section_text.strip():
                    continue

                text_chunks = self._chunk_text(section_text, max_tokens=500)
                for i, chunk_text in enumerate(text_chunks):
                    embedding = await self._generate_embedding(chunk_text)
                    content_hash = hashlib.sha256(chunk_text.encode()).hexdigest()[:16]

                    metadata = {
                        "title": req.title,
                        "authors": req.authors,
                        "year": req.year,
                        "venue": req.venue,
                        "domain": req.domain,
                        "section": section_name,
                        "chunk_index": i,
                        "content": chunk_text[:2000],
                        "content_hash": content_hash,
                        "tags": req.tags,
                        "source_url": req.pdf_url,
                        "ingested_at": datetime.now(timezone.utc).isoformat(),
                    }

                    point_id = uuid.uuid4().hex
                    self.qdrant.upsert(
                        collection_name="academic_papers",
                        points=[PointStruct(id=point_id, vector=embedding, payload=metadata)],
                    )
                    job.chunks_created += 1
                    job.embeddings_generated += 1

            INGESTION_DOCUMENTS.labels(source=req.title, collection="academic_papers").inc()
            INGESTION_CHUNKS.labels(source=req.title, collection="academic_papers").inc(job.chunks_created)
            INGESTION_EMBEDDINGS.labels(source=req.title, collection="academic_papers").inc(job.embeddings_generated)

            # Store PDF in MinIO
            minio_path = f"papers/{req.domain}/{os.path.basename(req.pdf_url)}"
            self._upload_to_minio(pdf_path, minio_path)
            os.remove(pdf_path)

            job.status = "completed"

        except Exception as e:
            job.status = "failed"
            job.errors += 1
            INGESTION_ERRORS.labels(source=req.title, error_type="paper_ingest").inc()
            logger.error("paper_ingestion_failed", title=req.title, error=str(e))

        finally:
            duration = time.time() - start
            job.duration_seconds = round(duration, 2)
            job.completed_at = datetime.now(timezone.utc).isoformat()
            INGESTION_DURATION.labels(source=req.title).observe(duration)
            INGESTION_QUEUE_DEPTH.dec()
            if trace:
                trace.update(output={"status": job.status, "chunks": job.chunks_created})

        return job

    def _split_paper_sections(self, text: str) -> Dict[str, str]:
        """Split paper text into logical sections."""
        section_headers = [
            "abstract", "introduction", "background", "related work",
            "methodology", "method", "approach", "architecture",
            "implementation", "evaluation", "results", "experiments",
            "discussion", "conclusion", "references", "appendix",
        ]
        sections: Dict[str, str] = {}
        current_section = "abstract"
        current_text: List[str] = []

        for line in text.split("\n"):
            line_lower = line.strip().lower()
            matched = False
            for header in section_headers:
                if line_lower == header or line_lower.startswith(f"{header}:") or line_lower.startswith(f"{header}."):
                    if current_text:
                        sections[current_section] = "\n".join(current_text)
                    current_section = header
                    current_text = []
                    matched = True
                    break
            if not matched:
                current_text.append(line)

        if current_text:
            sections[current_section] = "\n".join(current_text)

        return sections

    # ── Blog ingestion ────────────────────────────────────────────────────

    async def ingest_blog(self, req: BlogRequest) -> IngestionSummary:
        """Ingest a technical blog post into elite_codebases collection."""
        job_id = str(uuid.uuid4())[:8]
        job = IngestionSummary(
            job_id=job_id,
            source_name=req.url,
            status="running",
            started_at=datetime.now(timezone.utc).isoformat(),
        )
        self._jobs[job_id] = job
        INGESTION_QUEUE_DEPTH.inc()
        start = time.time()

        trace = None
        if self.langfuse:
            trace = self.langfuse.trace(name=f"ingest_blog_{req.source}")

        try:
            resp = await self.http_client.get(req.url, follow_redirects=True)
            resp.raise_for_status()
            html = resp.text

            soup = BeautifulSoup(html, "html.parser")
            for tag in soup(["nav", "footer", "header", "aside", "script", "style", "noscript"]):
                tag.decompose()

            article = soup.find("article") or soup.find("main") or soup.find("div", class_="post") or soup.body
            if not article:
                raise ValueError("No article content found")

            title_tag = soup.find("title")
            title = title_tag.get_text(strip=True) if title_tag else req.url
            published_tag = soup.find("time")
            published_date = published_tag.get("datetime", "") if published_tag else ""

            markdown = markdownify(str(article), strip=["img", "a"])
            markdown = "\n".join(line for line in markdown.split("\n") if line.strip())

            text_chunks = self._chunk_text(markdown, max_tokens=500)
            job.files_processed = 1

            for i, chunk_text in enumerate(text_chunks):
                embedding = await self._generate_embedding(chunk_text)
                content_hash = hashlib.sha256(chunk_text.encode()).hexdigest()[:16]

                metadata = {
                    "source": req.source,
                    "domain": req.domain,
                    "url": req.url,
                    "title": title,
                    "published_date": published_date,
                    "chunk_index": i,
                    "content": chunk_text[:2000],
                    "content_hash": content_hash,
                    "tags": req.tags,
                    "kind": "blog",
                    "ingested_at": datetime.now(timezone.utc).isoformat(),
                }

                point_id = uuid.uuid4().hex
                self.qdrant.upsert(
                    collection_name="elite_codebases",
                    points=[PointStruct(id=point_id, vector=embedding, payload=metadata)],
                )
                job.chunks_created += 1
                job.embeddings_generated += 1

            INGESTION_DOCUMENTS.labels(source=req.source or req.url, collection="elite_codebases").inc()
            INGESTION_CHUNKS.labels(source=req.source or req.url, collection="elite_codebases").inc(job.chunks_created)
            INGESTION_EMBEDDINGS.labels(source=req.source or req.url, collection="elite_codebases").inc(job.embeddings_generated)

            job.status = "completed"

        except Exception as e:
            job.status = "failed"
            job.errors += 1
            INGESTION_ERRORS.labels(source=req.url, error_type="blog_ingest").inc()
            logger.error("blog_ingestion_failed", url=req.url, error=str(e))

        finally:
            duration = time.time() - start
            job.duration_seconds = round(duration, 2)
            job.completed_at = datetime.now(timezone.utc).isoformat()
            INGESTION_DURATION.labels(source=req.url).observe(duration)
            INGESTION_QUEUE_DEPTH.dec()
            if trace:
                trace.update(output={"status": job.status, "chunks": job.chunks_created})

        return job

    # ── Post-mortem ingestion ─────────────────────────────────────────────

    async def ingest_postmortem(self, req: PostmortemRequest) -> IngestionSummary:
        """Ingest a post-mortem report into the anti_patterns collection."""
        job_id = str(uuid.uuid4())[:8]
        job = IngestionSummary(
            job_id=job_id,
            source_name=req.url,
            status="running",
            started_at=datetime.now(timezone.utc).isoformat(),
        )
        self._jobs[job_id] = job
        INGESTION_QUEUE_DEPTH.inc()
        start = time.time()

        trace = None
        if self.langfuse:
            trace = self.langfuse.trace(name=f"ingest_postmortem_{req.source}")

        try:
            resp = await self.http_client.get(req.url, follow_redirects=True)
            resp.raise_for_status()
            html = resp.text

            soup = BeautifulSoup(html, "html.parser")
            for tag in soup(["nav", "footer", "header", "aside", "script", "style", "noscript"]):
                tag.decompose()

            article = soup.find("article") or soup.find("main") or soup.body
            title_tag = soup.find("title")
            title = title_tag.get_text(strip=True) if title_tag else req.url

            markdown = markdownify(str(article), strip=["img"])
            markdown = "\n".join(line for line in markdown.split("\n") if line.strip())

            text_chunks = self._chunk_text(markdown, max_tokens=500)
            job.files_processed = 1

            for i, chunk_text in enumerate(text_chunks):
                embedding = await self._generate_embedding(chunk_text)
                content_hash = hashlib.sha256(chunk_text.encode()).hexdigest()[:16]

                metadata = {
                    "source": req.source,
                    "url": req.url,
                    "title": title,
                    "incident_date": req.incident_date or "",
                    "impact": req.impact,
                    "root_cause": req.root_cause,
                    "resolution": req.resolution,
                    "lessons_learned": req.lessons_learned,
                    "chunk_index": i,
                    "content": chunk_text[:2000],
                    "content_hash": content_hash,
                    "tags": req.tags,
                    "kind": "postmortem",
                    "ingested_at": datetime.now(timezone.utc).isoformat(),
                }

                point_id = uuid.uuid4().hex
                self.qdrant.upsert(
                    collection_name="anti_patterns",
                    points=[PointStruct(id=point_id, vector=embedding, payload=metadata)],
                )
                job.chunks_created += 1
                job.embeddings_generated += 1

            INGESTION_DOCUMENTS.labels(source=req.source or req.url, collection="anti_patterns").inc()
            INGESTION_CHUNKS.labels(source=req.source or req.url, collection="anti_patterns").inc(job.chunks_created)
            INGESTION_EMBEDDINGS.labels(source=req.source or req.url, collection="anti_patterns").inc(job.embeddings_generated)

            job.status = "completed"

        except Exception as e:
            job.status = "failed"
            job.errors += 1
            INGESTION_ERRORS.labels(source=req.url, error_type="postmortem_ingest").inc()
            logger.error("postmortem_ingestion_failed", url=req.url, error=str(e))

        finally:
            duration = time.time() - start
            job.duration_seconds = round(duration, 2)
            job.completed_at = datetime.now(timezone.utc).isoformat()
            INGESTION_DURATION.labels(source=req.url).observe(duration)
            INGESTION_QUEUE_DEPTH.dec()
            if trace:
                trace.update(output={"status": job.status, "chunks": job.chunks_created})

        return job

    # ── Batch ingestion ───────────────────────────────────────────────────

    async def run_batch(self, concurrency: int = DEFAULT_CONCURRENCY) -> Dict[str, Any]:
        """Run batch ingestion from sources-config.yaml."""
        import yaml

        config_path = os.path.join(os.path.dirname(__file__), "config", "sources-config.yaml")
        if not os.path.exists(config_path):
            raise HTTPException(status_code=404, detail="sources-config.yaml not found")

        with open(config_path) as f:
            config = yaml.safe_load(f)

        semaphore = asyncio.Semaphore(concurrency)
        results: List[IngestionSummary] = []

        async def _ingest_with_semaphore(coro):
            async with semaphore:
                return await coro

        tasks = []

        # Repositories
        for repo in config.get("repositories", []):
            req = RepositoryRequest(
                source_url=repo["source_url"],
                source_name=repo["source_name"],
                source_category=repo.get("source_category", "general"),
                branch=repo.get("branch", "main"),
                languages=repo.get("languages", ["python"]),
                file_patterns=repo.get("file_patterns", ["*.*"]),
                exclude_patterns=repo.get("exclude_patterns", []),
                collection=repo.get("collection", "elite_codebases"),
                chunk_strategy=ChunkStrategy(repo.get("chunk_strategy", "ast")),
                tags=repo.get("tags", []),
            )
            tasks.append(_ingest_with_semaphore(self.ingest_repository(req)))

        # Post-mortems
        for pm in config.get("postmortems", []):
            req = PostmortemRequest(
                url=pm["url"],
                source=pm.get("source", ""),
                tags=pm.get("tags", []),
            )
            tasks.append(_ingest_with_semaphore(self.ingest_postmortem(req)))

        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)

        completed = sum(1 for r in results if isinstance(r, IngestionSummary) and r.status == "completed")
        failed = sum(1 for r in results if isinstance(r, Exception) or (isinstance(r, IngestionSummary) and r.status == "failed"))

        return {
            "total_sources": len(tasks),
            "completed": completed,
            "failed": failed,
            "concurrency": concurrency,
        }

    # ── Source deletion ───────────────────────────────────────────────────

    async def delete_source(self, source_name: str) -> Dict[str, str]:
        """Remove a source from Qdrant and MinIO."""
        collections = ["elite_codebases", "academic_papers", "anti_patterns", "codebase_embeddings"]
        deleted_points = 0

        for collection in collections:
            try:
                self.qdrant.delete(
                    collection_name=collection,
                    points_selector={
                        "filter": {
                            "must": [{"key": "source_name", "match": {"value": source_name}}]
                        }
                    },
                )
                deleted_points += 1
            except Exception:
                pass

        # Remove workspace dir
        repo_dir = os.path.join(WORKSPACE_DIR, source_name)
        if os.path.exists(repo_dir):
            shutil.rmtree(repo_dir, ignore_errors=True)

        # Remove MinIO objects
        try:
            prefix = f"{source_name}/"
            objects = self.minio_client.list_objects(KNOWLEDGE_BUCKET, prefix=prefix, recursive=True)
            for obj in objects:
                self.minio_client.remove_object(KNOWLEDGE_BUCKET, obj.object_name)
        except Exception:
            pass

        logger.info("source_deleted", source=source_name)
        return {"status": "deleted", "source": source_name}

    # ── Status and history ────────────────────────────────────────────────

    def get_status(self) -> Dict[str, Any]:
        """Return current job status and queue depth."""
        running = [j for j in self._jobs.values() if j.status == "running"]
        return {
            "running_jobs": len(running),
            "total_jobs": len(self._jobs),
            "queue_depth": len(running),
            "jobs": [j.model_dump() for j in running],
        }

    def get_history(self, days: int = 30) -> List[Dict[str, Any]]:
        """Return ingestion history for the last N days."""
        cutoff = datetime.now(timezone.utc).timestamp() - (days * 86400)
        history = []
        for job in self._jobs.values():
            try:
                started = datetime.fromisoformat(job.started_at).timestamp()
                if started >= cutoff:
                    history.append(job.model_dump())
            except Exception:
                history.append(job.model_dump())
        return sorted(history, key=lambda x: x.get("started_at", ""), reverse=True)

    def get_stats(self) -> Dict[str, Any]:
        """Return aggregated ingestion statistics."""
        collection_counts: Dict[str, int] = {}
        collections = ["elite_codebases", "academic_papers", "anti_patterns", "design_patterns",
                       "human_feedback", "codebase_embeddings", "project_context"]
        for coll in collections:
            try:
                info = self.qdrant.get_collection(coll)
                collection_counts[coll] = info.points_count
            except Exception:
                collection_counts[coll] = 0

        total_docs = sum(collection_counts.values())
        total_jobs = len(self._jobs)
        completed_jobs = sum(1 for j in self._jobs.values() if j.status == "completed")
        total_chunks = sum(j.chunks_created for j in self._jobs.values())
        total_embeddings = sum(j.embeddings_generated for j in self._jobs.values())

        return {
            "total_documents": total_docs,
            "total_embeddings": total_embeddings,
            "total_chunks": total_chunks,
            "total_jobs": total_jobs,
            "completed_jobs": completed_jobs,
            "collection_counts": collection_counts,
        }

    # ── Helpers ───────────────────────────────────────────────────────────

    def _detect_language(self, suffix: str, languages: List[str]) -> Optional[str]:
        """Detect language from file extension."""
        ext_map = {
            ".py": "python", ".pyx": "python",
            ".js": "javascript", ".mjs": "javascript", ".jsx": "javascript",
            ".ts": "typescript", ".tsx": "typescript",
            ".go": "go",
            ".rs": "rust",
            ".c": "c", ".h": "c",
            ".cpp": "cpp", ".cc": "cpp", ".cxx": "cpp", ".hpp": "cpp",
            ".java": "java",
        }
        detected = ext_map.get(suffix.lower())
        if detected and detected in languages:
            return detected
        if detected:
            return detected
        return languages[0] if languages else None

    def _store_source_metadata(self, source_name: str, metadata: Dict[str, Any]) -> None:
        """Store source metadata in MinIO."""
        import io
        import json

        data = json.dumps(metadata, indent=2).encode("utf-8")
        try:
            self.minio_client.put_object(
                KNOWLEDGE_BUCKET,
                f"{source_name}/metadata.json",
                io.BytesIO(data),
                len(data),
                content_type="application/json",
            )
        except Exception as e:
            logger.warning("minio_store_failed", source=source_name, error=str(e))

    def _upload_to_minio(self, local_path: str, remote_path: str) -> None:
        """Upload a file to MinIO."""
        try:
            self.minio_client.fput_object(KNOWLEDGE_BUCKET, remote_path, local_path)
        except Exception as e:
            logger.warning("minio_upload_failed", path=remote_path, error=str(e))


# ─────────────────────────────────────────────────────────────────────────────
# FastAPI Application
# ─────────────────────────────────────────────────────────────────────────────

engine = IngestionEngine()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await engine.initialize()
    logger.info("knowledge_ingestor_started", port=9420)
    yield
    await engine.shutdown()


app = FastAPI(
    title="Knowledge Ingestor",
    description="Core ingestion pipeline for the Omni Quantum Elite knowledge layer",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/health", response_model=HealthResponse)
async def health():
    """Health check endpoint."""
    return HealthResponse(status="healthy", service="knowledge-ingestor", version="1.0.0")


@app.get("/ready")
async def ready():
    """Readiness check — verifies Qdrant and MinIO connectivity."""
    errors = []
    try:
        engine.qdrant.get_collections()
    except Exception as e:
        errors.append(f"qdrant: {e}")
    try:
        engine.minio_client.bucket_exists(KNOWLEDGE_BUCKET)
    except Exception as e:
        errors.append(f"minio: {e}")
    if errors:
        raise HTTPException(status_code=503, detail={"errors": errors})
    return {"status": "ready"}


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    return Response(content=generate_latest(), media_type="text/plain; charset=utf-8")


@app.post("/ingest/repository", response_model=IngestionSummary)
async def ingest_repository(req: RepositoryRequest):
    """Ingest a Git repository into Qdrant."""
    return await engine.ingest_repository(req)


@app.post("/ingest/paper", response_model=IngestionSummary)
async def ingest_paper(req: PaperRequest):
    """Ingest an academic paper PDF."""
    return await engine.ingest_paper(req)


@app.post("/ingest/blog", response_model=IngestionSummary)
async def ingest_blog(req: BlogRequest):
    """Ingest a technical blog post."""
    return await engine.ingest_blog(req)


@app.post("/ingest/postmortem", response_model=IngestionSummary)
async def ingest_postmortem(req: PostmortemRequest):
    """Ingest a post-mortem report."""
    return await engine.ingest_postmortem(req)


@app.post("/ingest/batch")
async def ingest_batch(req: BatchRequest = BatchRequest()):
    """Trigger batch ingestion from sources-config.yaml."""
    return await engine.run_batch(req.concurrency)


@app.get("/ingest/status")
async def ingest_status():
    """Current ingestion jobs and queue depth."""
    return engine.get_status()


@app.get("/ingest/history")
async def ingest_history(days: int = 30):
    """Ingestion history for the last N days."""
    return engine.get_history(days)


@app.get("/ingest/stats")
async def ingest_stats():
    """Total docs, embeddings, per-collection counts."""
    return engine.get_stats()


@app.delete("/ingest/{source_name}")
async def delete_source(source_name: str):
    """Remove a source from Qdrant and MinIO."""
    return await engine.delete_source(source_name)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9420)
