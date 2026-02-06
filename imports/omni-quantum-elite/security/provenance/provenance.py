#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                             PROVENANCE TRACKING                              ║
╟──────────────────────────────────────────────────────────────────────────────╢
║ This module provides functions to add a provenance header to files and to    ║
║ persist provenance metadata into a PostgreSQL audit trail. A provenance      ║
║ record captures the model used to generate the file, the prompt version,     ║
║ generation timestamp, knowledge sources referenced, and the quality score.   ║
║ Generated files are not overwritten; instead, a new file with a configurable ║
║ suffix is created. Provenance records are stored in the `file_provenance`    ║
║ table in PostgreSQL, which is created on demand.                             ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations

import asyncio
import dataclasses
import json
import os
import sys
import uuid
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import List

import asyncpg
import structlog


###############################################################################
# Data Models
###############################################################################


@dataclasses.dataclass
class ProvenanceRecord:
    """Represents a provenance record for a generated file."""

    id: uuid.UUID
    file_path: str
    model: str
    prompt_version: str
    timestamp: datetime
    knowledge_sources: List[str]
    score: Decimal
    created_at: datetime = dataclasses.field(default_factory=datetime.utcnow)


###############################################################################
# Repository
###############################################################################


class ProvenanceRepository:
    """Repository for writing provenance records to PostgreSQL."""

    TABLE_NAME = "file_provenance"

    def __init__(self, dsn: str, logger: structlog.BoundLogger) -> None:
        self._dsn = dsn
        self._logger = logger
        self._pool: asyncpg.Pool | None = None

    async def _init_pool(self) -> None:
        if self._pool is None:
            self._pool = await asyncpg.create_pool(dsn=self._dsn)

    async def _ensure_table(self) -> None:
        assert self._pool is not None
        async with self._pool.acquire() as conn:
            await conn.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {self.TABLE_NAME} (
                    id UUID PRIMARY KEY,
                    file_path TEXT NOT NULL,
                    model TEXT NOT NULL,
                    prompt_version TEXT NOT NULL,
                    timestamp TIMESTAMPTZ NOT NULL,
                    knowledge_sources JSONB NOT NULL,
                    score DECIMAL(5,2) NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                """
            )

    async def insert(self, record: ProvenanceRecord) -> None:
        await self._init_pool()
        await self._ensure_table()
        assert self._pool is not None
        async with self._pool.acquire() as conn:
            await conn.execute(
                f"""
                INSERT INTO {self.TABLE_NAME} (id, file_path, model, prompt_version, timestamp, knowledge_sources, score, created_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                """,
                record.id,
                record.file_path,
                record.model,
                record.prompt_version,
                record.timestamp,
                json.dumps(record.knowledge_sources),
+                record.score,
                record.created_at,
            )

    async def close(self) -> None:
        if self._pool is not None:
            await self._pool.close()


###############################################################################
# Service
###############################################################################


class ProvenanceService:
    """Service layer for creating provenance entries and annotating files."""

    def __init__(self, repo: ProvenanceRepository, suffix: str = ".prov") -> None:
        self._repo = repo
        self._suffix = suffix
        self._logger = structlog.get_logger(__name__).bind(component="provenance_service")

    def _generate_header(self, metadata: ProvenanceRecord, comment_prefix: str = "# ") -> str:
        lines = [
            "╔══════════════════════════════════════════════════════════════╗",
            "║                        FILE PROVENANCE                       ║",
            f"║ Model: {metadata.model:<46}║",
            f"║ Prompt Version: {metadata.prompt_version:<35}║",
            f"║ Timestamp: {metadata.timestamp.isoformat():<39}║",
            f"║ Knowledge Sources: {', '.join(metadata.knowledge_sources):<23}║",
            f"║ Score: {metadata.score:<47}║",
            "╚══════════════════════════════════════════════════════════════╝",
            "",
        ]
        return os.linesep.join([comment_prefix + line for line in lines])

    def _determine_comment_prefix(self, file_suffix: str) -> str:
        ext = file_suffix.lower().strip('.')
        # Default to hash comments for most text files
        if ext in {"py", "sh", "bash", "yaml", "yml", "conf", "ini", "toml", "sql", "Dockerfile"}:
            return "# "
        if ext in {"js", "ts", "json"}:
            return "// "
        return "# "

    def annotate_file(self, input_path: Path, record: ProvenanceRecord) -> Path:
        """Insert provenance header into a copy of the file and return the new path."""
        comment_prefix = self._determine_comment_prefix(input_path.suffix or input_path.name)
        header = self._generate_header(record, comment_prefix=comment_prefix)
        new_path = input_path.with_suffix(input_path.suffix + self._suffix)
        with input_path.open("r", encoding="utf-8") as f_in, new_path.open("w", encoding="utf-8") as f_out:
            f_out.write(header)
            f_out.write(f_in.read())
        return new_path

    async def record_provenance(self, record: ProvenanceRecord) -> None:
        await self._repo.insert(record)


###############################################################################
# CLI
###############################################################################


async def main() -> None:
    if len(sys.argv) < 7:
        print(
            "Usage: provenance.py <file_path> <model> <prompt_version> <timestamp> <knowledge_sources_json> <score>",
            file=sys.stderr,
        )
        sys.exit(1)
    file_path = Path(sys.argv[1])
    model = sys.argv[2]
    prompt_version = sys.argv[3]
    timestamp = datetime.fromisoformat(sys.argv[4])
    knowledge_sources = json.loads(sys.argv[5]) if sys.argv[5].strip() else []
    score = Decimal(sys.argv[6])

    # Initialize logger
    structlog.configure(processors=[structlog.processors.JSONRenderer()])
    logger = structlog.get_logger(__name__).bind(component="provenance_cli")
    # Build record
    record = ProvenanceRecord(
        id=uuid.uuid4(),
        file_path=str(file_path),
        model=model,
        prompt_version=prompt_version,
        timestamp=timestamp,
        knowledge_sources=knowledge_sources,
        score=score,
    )
    # Determine DSN from env
    pg_host = os.getenv("PGHOST", "omni-postgres")
    pg_port = os.getenv("PGPORT", "5432")
    pg_user = os.getenv("PGUSER", "postgres")
    pg_password = os.getenv("PGPASSWORD", "postgres")
    pg_db = os.getenv("PGDATABASE", "omni")
    dsn = f"postgresql://{pg_user}:{pg_password}@{pg_host}:{pg_port}/{pg_db}"
    repo = ProvenanceRepository(dsn=dsn, logger=logger)
    service = ProvenanceService(repo=repo)
    # Annotate file
    new_path = service.annotate_file(file_path, record)
    logger.info("annotated_file", original=str(file_path), new=str(new_path))
    # Update record path to new file
    record.file_path = str(new_path)
    # Write to DB
    await service.record_provenance(record)
    await repo.close()
    logger.info("provenance_recorded", id=str(record.id))


if __name__ == "__main__":
    asyncio.run(main())