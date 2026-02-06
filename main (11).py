#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                       MCP DATABASE SCHEMA SERVICE                            ║
╟──────────────────────────────────────────────────────────────────────────────╢
║ This microservice exposes metadata about the PostgreSQL database schemas.    ║
║ It allows agents to discover tables, column definitions, indexes and        ║
║ relationships (foreign keys) for generating code or answering queries.       ║
║ Queries are read-only and executed via asyncpg with parameterized SQL to    ║
║ ensure security.  The service provides health, readiness and metrics        ║
║ endpoints compliant with the Omni Quantum standards.                         ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations

import dataclasses
import os
from datetime import datetime
from typing import Dict, List, Optional

import asyncpg
import structlog
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from prometheus_client import Counter, Histogram, make_asgi_app


# ════════════════════════════════════════════════════════════════════
# ENUMS AND DATA MODELS
# ════════════════════════════════════════════════════════════════════


class SchemaStatus(str):
    """Enumeration of schema operation status."""

    OK = "OK"
    NOT_FOUND = "NOT_FOUND"
    ERROR = "ERROR"


@dataclasses.dataclass
class TableInfo:
    """Internal representation of a table."""

    id: str
    name: str
    schema: str
    created_at: datetime = dataclasses.field(default_factory=datetime.utcnow)


class ListTablesResponse(BaseModel):
    status: SchemaStatus = Field(...)
    tables: List[str] = Field(default_factory=list)


class ColumnDefinition(BaseModel):
    name: str
    data_type: str
    is_nullable: bool
    default: Optional[str] = None


class TableSchemaResponse(BaseModel):
    status: SchemaStatus = Field(...)
    columns: List[ColumnDefinition] = Field(default_factory=list)


class IndexInfo(BaseModel):
    name: str
    columns: List[str]
    is_unique: bool


class IndexesResponse(BaseModel):
    status: SchemaStatus = Field(...)
    indexes: List[IndexInfo] = Field(default_factory=list)


class RelationshipInfo(BaseModel):
    table: str
    column: str
    foreign_table: str
    foreign_column: str


class RelationshipsResponse(BaseModel):
    status: SchemaStatus = Field(...)
    relationships: List[RelationshipInfo] = Field(default_factory=list)


# ════════════════════════════════════════════════════════════════════
# REPOSITORY LAYER
# ════════════════════════════════════════════════════════════════════


@dataclasses.dataclass
class SchemaRepository:
    """Repository for querying PostgreSQL schema information."""

    pool: asyncpg.Pool
    logger: structlog.BoundLogger = dataclasses.field(init=False)

    def __post_init__(self) -> None:
        self.logger = structlog.get_logger(__name__).bind(component="schema_repository")

    async def list_tables(self, schema: str) -> List[str]:
        query = """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = $1 AND table_type = 'BASE TABLE'
        ORDER BY table_name;
        """
        try:
            rows = await self.pool.fetch(query, schema)
            return [row["table_name"] for row in rows]
        except Exception as exc:  # noqa: B902
            self.logger.error("list_tables_error", schema=schema, error=str(exc))
            raise

    async def get_table_schema(self, schema: str, table: str) -> List[ColumnDefinition]:
        query = """
        SELECT column_name, data_type, is_nullable, column_default
        FROM information_schema.columns
        WHERE table_schema = $1 AND table_name = $2
        ORDER BY ordinal_position;
        """
        try:
            rows = await self.pool.fetch(query, schema, table)
            columns: List[ColumnDefinition] = []
            for row in rows:
                columns.append(
                    ColumnDefinition(
                        name=row["column_name"],
                        data_type=row["data_type"],
                        is_nullable=(row["is_nullable"] == "YES"),
                        default=row["column_default"],
                    )
                )
            return columns
        except Exception as exc:  # noqa: B902
            self.logger.error("table_schema_error", table=table, error=str(exc))
            raise

    async def get_indexes(self, schema: str, table: str) -> List[IndexInfo]:
        query = """
        SELECT
            i.relname AS index_name,
            ARRAY_AGG(a.attname) AS column_names,
            ix.indisunique AS is_unique
        FROM
            pg_class t
            JOIN pg_index ix ON t.oid = ix.indrelid
            JOIN pg_class i ON i.oid = ix.indexrelid
            JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = ANY(ix.indkey)
        WHERE
            t.relkind = 'r'
            AND t.relname = $1
            AND current_schema() = $2
        GROUP BY i.relname, ix.indisunique
        ORDER BY i.relname;
        """
        try:
            rows = await self.pool.fetch(query, table, schema)
            indexes: List[IndexInfo] = []
            for row in rows:
                indexes.append(
                    IndexInfo(
                        name=row["index_name"],
                        columns=row["column_names"],
                        is_unique=row["is_unique"],
                    )
                )
            return indexes
        except Exception as exc:  # noqa: B902
            self.logger.error("get_indexes_error", table=table, error=str(exc))
            raise

    async def get_relationships(self, schema: str, table: str) -> List[RelationshipInfo]:
        query = """
        SELECT
            kcu.table_name AS table_name,
            kcu.column_name AS column_name,
            ccu.table_name AS foreign_table_name,
            ccu.column_name AS foreign_column_name
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
          ON tc.constraint_name = kcu.constraint_name
         AND tc.table_schema = kcu.table_schema
        JOIN information_schema.constraint_column_usage ccu
          ON ccu.constraint_name = tc.constraint_name
         AND ccu.table_schema = tc.table_schema
        WHERE tc.constraint_type = 'FOREIGN KEY'
          AND tc.table_schema = $1
          AND tc.table_name = $2;
        """
        try:
            rows = await self.pool.fetch(query, schema, table)
            relations: List[RelationshipInfo] = []
            for row in rows:
                relations.append(
                    RelationshipInfo(
                        table=row["table_name"],
                        column=row["column_name"],
                        foreign_table=row["foreign_table_name"],
                        foreign_column=row["foreign_column_name"],
                    )
                )
            return relations
        except Exception as exc:  # noqa: B902
            self.logger.error("get_relationships_error", table=table, error=str(exc))
            raise


# ════════════════════════════════════════════════════════════════════
# SERVICE LAYER
# ════════════════════════════════════════════════════════════════════


@dataclasses.dataclass
class SchemaService:
    """Business service that orchestrates schema operations."""

    repository: SchemaRepository
    logger: structlog.BoundLogger = dataclasses.field(init=False)
    request_counter: Counter = dataclasses.field(init=False)
    latency_histogram: Histogram = dataclasses.field(init=False)

    def __post_init__(self) -> None:
        self.logger = structlog.get_logger(__name__).bind(component="schema_service")
        self.request_counter = Counter(
            "mcp_schema_requests_total", "Total schema service requests"
        )
        self.latency_histogram = Histogram(
            "mcp_schema_latency_seconds",
            "Latency of schema service requests",
            buckets=(0.05, 0.1, 0.25, 0.5, 1, 2, 5),
        )

    async def list_tables(self, schema: str) -> ListTablesResponse:
        self.request_counter.inc()
        timer = self.latency_histogram.time()
        async with timer:
            try:
                tables = await self.repository.list_tables(schema)
                status = SchemaStatus.OK if tables else SchemaStatus.NOT_FOUND
                return ListTablesResponse(status=status, tables=tables)
            except Exception:
                return ListTablesResponse(status=SchemaStatus.ERROR, tables=[])

    async def get_table_schema(self, schema: str, table: str) -> TableSchemaResponse:
        self.request_counter.inc()
        timer = self.latency_histogram.time()
        async with timer:
            try:
                columns = await self.repository.get_table_schema(schema, table)
                status = SchemaStatus.OK if columns else SchemaStatus.NOT_FOUND
                return TableSchemaResponse(status=status, columns=columns)
            except Exception:
                return TableSchemaResponse(status=SchemaStatus.ERROR, columns=[])

    async def get_indexes(self, schema: str, table: str) -> IndexesResponse:
        self.request_counter.inc()
        timer = self.latency_histogram.time()
        async with timer:
            try:
                indexes = await self.repository.get_indexes(schema, table)
                status = SchemaStatus.OK if indexes else SchemaStatus.NOT_FOUND
                return IndexesResponse(status=status, indexes=indexes)
            except Exception:
                return IndexesResponse(status=SchemaStatus.ERROR, indexes=[])

    async def get_relationships(self, schema: str, table: str) -> RelationshipsResponse:
        self.request_counter.inc()
        timer = self.latency_histogram.time()
        async with timer:
            try:
                relations = await self.repository.get_relationships(schema, table)
                status = SchemaStatus.OK if relations else SchemaStatus.NOT_FOUND
                return RelationshipsResponse(status=status, relationships=relations)
            except Exception:
                return RelationshipsResponse(status=SchemaStatus.ERROR, relationships=[])


# ════════════════════════════════════════════════════════════════════
# APPLICATION SETUP
# ════════════════════════════════════════════════════════════════════


async def create_service() -> SchemaService:
    """Initialize repository and service."""
    pg_host = os.getenv("POSTGRES_HOST", "omni-postgres")
    pg_port = int(os.getenv("POSTGRES_PORT", "5432"))
    pg_user = os.getenv("POSTGRES_USER", "postgres")
    pg_password = os.getenv("POSTGRES_PASSWORD", "postgres")
    pg_database = os.getenv("POSTGRES_DB", "postgres")
    pool = await asyncpg.create_pool(
        host=pg_host,
        port=pg_port,
        user=pg_user,
        password=pg_password,
        database=pg_database,
        min_size=1,
        max_size=5,
    )
    repo = SchemaRepository(pool=pool)
    return SchemaService(repository=repo)


def create_app() -> FastAPI:
    app = FastAPI(title="MCP Schema", version="1.0.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    metrics_app = make_asgi_app()
    app.mount("/metrics", metrics_app)

    service: SchemaService = None  # type: ignore

    @app.on_event("startup")
    async def startup_event() -> None:
        nonlocal service
        service = await create_service()

    @app.on_event("shutdown")
    async def shutdown_event() -> None:
        nonlocal service
        # Properly close the pool
        if service and service.repository.pool:
            await service.repository.pool.close()

    @app.get("/api/v1/list_tables", response_model=ListTablesResponse)
    async def list_tables(schema: str = Query("public", description="Schema name")) -> ListTablesResponse:
        return await service.list_tables(schema)

    @app.get("/api/v1/get_table_schema", response_model=TableSchemaResponse)
    async def get_table_schema(schema: str = Query("public", description="Schema name"), table: str = Query(..., description="Table name")) -> TableSchemaResponse:
        return await service.get_table_schema(schema, table)

    @app.get("/api/v1/get_indexes", response_model=IndexesResponse)
    async def get_indexes(schema: str = Query("public", description="Schema name"), table: str = Query(..., description="Table name")) -> IndexesResponse:
        return await service.get_indexes(schema, table)

    @app.get("/api/v1/get_relationships", response_model=RelationshipsResponse)
    async def get_relationships(schema: str = Query("public", description="Schema name"), table: str = Query(..., description="Table name")) -> RelationshipsResponse:
        return await service.get_relationships(schema, table)

    @app.get("/health")
    async def health() -> Dict[str, str]:
        return {"status": "ok"}

    @app.get("/ready")
    async def ready() -> Dict[str, str]:
        # Check simple query to ensure DB is reachable
        try:
            # Use a small query to test connectivity
            async with asyncpg.create_pool(
                host=os.getenv("POSTGRES_HOST", "omni-postgres"),
                port=int(os.getenv("POSTGRES_PORT", "5432")),
                user=os.getenv("POSTGRES_USER", "postgres"),
                password=os.getenv("POSTGRES_PASSWORD", "postgres"),
                database=os.getenv("POSTGRES_DB", "postgres"),
                min_size=1,
                max_size=1,
            ) as tmp_pool:
                async with tmp_pool.acquire() as conn:
                    await conn.fetch("SELECT 1")
        except Exception:
            raise HTTPException(status_code=503, detail="PostgreSQL unavailable")
        return {"status": "ready"}

    return app


app = create_app()