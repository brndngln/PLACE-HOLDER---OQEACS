"""Graph builder service for constructing semantic code understanding graphs."""

from __future__ import annotations

import os
import re
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import networkx as nx
import structlog

from src.config import settings
from src.models import (
    AnalysisDepth,
    CodeEntity,
    EntityType,
    Relationship,
    RelationshipType,
    SemanticGraph,
)
from src.services.parser import LANGUAGE_EXTENSIONS, CodeParser

logger = structlog.get_logger(__name__)


# Directories to always skip during repo traversal
SKIP_DIRS: set[str] = {
    ".git",
    ".svn",
    ".hg",
    "node_modules",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    ".tox",
    "venv",
    ".venv",
    "env",
    ".env",
    "dist",
    "build",
    "target",
    ".next",
    ".nuxt",
    "vendor",
}

TEST_PATTERNS: set[str] = {
    "test_",
    "_test.",
    "tests/",
    "test/",
    "__tests__/",
    ".test.",
    ".spec.",
    "_spec.",
}


def _is_test_file(file_path: str) -> bool:
    """Check whether a file path appears to be a test file."""
    normalized = file_path.replace("\\", "/").lower()
    return any(pattern in normalized for pattern in TEST_PATTERNS)


def _language_for_extension(ext: str) -> str | None:
    """Map a file extension to a language name."""
    for lang, exts in LANGUAGE_EXTENSIONS.items():
        if ext in exts:
            return lang
    return None


class GraphBuilder:
    """Builds a semantic graph of an entire codebase.

    Walks the repository, parses all supported source files, resolves
    cross-file references (imports, call chains, inheritance), computes
    centrality metrics, and optionally persists the graph to Qdrant.
    """

    def __init__(self, parser: CodeParser | None = None) -> None:
        self._parser = parser or CodeParser()
        self._graphs: dict[str, SemanticGraph] = {}
        logger.info("graph_builder.created")

    def get_graph(self, repo_id: str) -> SemanticGraph | None:
        """Retrieve a previously built graph by its repo_id."""
        return self._graphs.get(repo_id)

    async def build_graph(
        self,
        repo_path: str,
        languages: list[str],
        depth: AnalysisDepth = AnalysisDepth.FULL,
        include_tests: bool = True,
    ) -> SemanticGraph:
        """Walk an entire repository, parse all files, and build a semantic graph.

        Args:
            repo_path: Absolute path to the repository root.
            languages: List of languages to analyze.
            depth: Analysis depth controlling how thorough the parsing is.
            include_tests: Whether to include test files.

        Returns:
            A fully populated SemanticGraph.
        """
        logger.info(
            "graph_builder.build_start",
            repo_path=repo_path,
            languages=languages,
            depth=depth.value,
        )

        repo_root = Path(repo_path)
        if not repo_root.is_dir():
            logger.error("graph_builder.invalid_repo_path", repo_path=repo_path)
            return SemanticGraph(
                file_count=0,
                total_entities=0,
                languages=languages,
            )

        # Discover files
        files = self._discover_files(repo_root, languages, include_tests)
        logger.info("graph_builder.files_discovered", count=len(files))

        # Parse all files
        all_entities: list[CodeEntity] = []
        file_sources: dict[str, str] = {}
        file_count = 0

        for file_path, language in files:
            entities = self._parser.parse_file(str(file_path), language)
            if entities:
                all_entities.extend(entities)
                file_count += 1
                try:
                    file_sources[str(file_path)] = file_path.read_text(
                        encoding="utf-8", errors="replace"
                    )
                except (OSError, PermissionError):
                    file_sources[str(file_path)] = ""

        logger.info(
            "graph_builder.parsing_complete",
            file_count=file_count,
            entity_count=len(all_entities),
        )

        # Build relationships
        relationships: list[Relationship] = []

        # Resolve imports -> definitions
        import_rels = self._resolve_imports(all_entities)
        relationships.extend(import_rels)

        # Detect function call chains
        if depth in (AnalysisDepth.STANDARD, AnalysisDepth.FULL):
            call_rels = self._detect_call_chains(all_entities, file_sources)
            relationships.extend(call_rels)

        # Detect inheritance hierarchies
        if depth == AnalysisDepth.FULL:
            inherit_rels = self._detect_inheritance(all_entities)
            relationships.extend(inherit_rels)

        # Deduplicate relationships
        relationships = self._deduplicate_relationships(relationships)

        # Calculate centrality using networkx
        centrality_scores = self._calculate_centrality(all_entities, relationships)

        # Build the graph object
        detected_languages = list({e.language for e in all_entities})
        graph = SemanticGraph(
            entities=all_entities,
            relationships=relationships,
            file_count=file_count,
            total_entities=len(all_entities),
            generated_at=datetime.now(timezone.utc),
            languages=detected_languages,
            centrality_scores=centrality_scores,
        )

        # Store in memory
        self._graphs[graph.repo_id] = graph

        # Persist to Qdrant
        await self._store_graph(graph)

        logger.info(
            "graph_builder.build_complete",
            repo_id=graph.repo_id,
            entities=len(all_entities),
            relationships=len(relationships),
            files=file_count,
        )

        return graph

    def _discover_files(
        self,
        repo_root: Path,
        languages: list[str],
        include_tests: bool,
    ) -> list[tuple[Path, str]]:
        """Walk the repository and collect all source files of interest.

        Returns:
            List of (file_path, language) tuples.
        """
        target_extensions: set[str] = set()
        for lang in languages:
            exts = LANGUAGE_EXTENSIONS.get(lang, [])
            target_extensions.update(exts)

        discovered: list[tuple[Path, str]] = []

        for dirpath, dirnames, filenames in os.walk(repo_root):
            # Prune skipped directories in-place
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]

            for filename in filenames:
                ext = Path(filename).suffix
                if ext not in target_extensions:
                    continue

                file_path = Path(dirpath) / filename

                if not include_tests and _is_test_file(str(file_path)):
                    continue

                language = _language_for_extension(ext)
                if language and language in languages:
                    discovered.append((file_path, language))

        return discovered

    def _resolve_imports(
        self, entities: list[CodeEntity]
    ) -> list[Relationship]:
        """Map import entities to their actual definitions.

        For each import entity, attempts to find a matching definition
        (function, class, module) by name across all entities.
        """
        relationships: list[Relationship] = []

        # Build lookup: name -> list of defining entities
        definitions: dict[str, list[CodeEntity]] = defaultdict(list)
        for entity in entities:
            if entity.entity_type != EntityType.IMPORT:
                definitions[entity.name].append(entity)

        # Resolve each import
        for entity in entities:
            if entity.entity_type != EntityType.IMPORT:
                continue

            import_name = entity.name
            # Direct name match
            if import_name in definitions:
                for target in definitions[import_name]:
                    relationships.append(
                        Relationship(
                            source_id=entity.id,
                            target_id=target.id,
                            relationship_type=RelationshipType.IMPORTS,
                            weight=1.0,
                            metadata={
                                "import_statement": entity.signature,
                                "resolved_to": target.file_path,
                            },
                        )
                    )
                continue

            # Try partial matching: "from foo.bar import baz" -> look for "baz"
            parts = import_name.split(".")
            for part in reversed(parts):
                if part in definitions:
                    for target in definitions[part]:
                        relationships.append(
                            Relationship(
                                source_id=entity.id,
                                target_id=target.id,
                                relationship_type=RelationshipType.IMPORTS,
                                weight=0.7,
                                metadata={
                                    "import_statement": entity.signature,
                                    "resolved_to": target.file_path,
                                    "partial_match": True,
                                },
                            )
                        )
                    break

        logger.info("graph_builder.imports_resolved", count=len(relationships))
        return relationships

    def _detect_call_chains(
        self,
        entities: list[CodeEntity],
        file_sources: dict[str, str],
    ) -> list[Relationship]:
        """Trace function call paths across all entities.

        For each function entity, scans its body for calls to other known
        functions and creates CALLS relationships.
        """
        relationships: list[Relationship] = []

        # Index functions by name
        function_index: dict[str, list[CodeEntity]] = defaultdict(list)
        for entity in entities:
            if entity.entity_type == EntityType.FUNCTION:
                function_index[entity.name].append(entity)

        # Scan each function body for calls
        call_pattern = re.compile(r"\b(\w+)\s*\(")

        for entity in entities:
            if entity.entity_type != EntityType.FUNCTION:
                continue

            source = file_sources.get(entity.file_path, "")
            if not source:
                continue

            lines = source.split("\n")
            body_lines = lines[entity.line_start - 1: entity.line_end]
            body_text = "\n".join(body_lines)

            seen_targets: set[str] = set()
            for match in call_pattern.finditer(body_text):
                called_name = match.group(1)
                if called_name == entity.name:
                    continue  # Skip self-recursion for now
                if called_name in function_index and called_name not in seen_targets:
                    seen_targets.add(called_name)
                    for target in function_index[called_name]:
                        if target.id != entity.id:
                            relationships.append(
                                Relationship(
                                    source_id=entity.id,
                                    target_id=target.id,
                                    relationship_type=RelationshipType.CALLS,
                                    weight=1.0,
                                    metadata={
                                        "caller_file": entity.file_path,
                                        "callee_file": target.file_path,
                                    },
                                )
                            )

        logger.info("graph_builder.call_chains_detected", count=len(relationships))
        return relationships

    def _detect_inheritance(
        self, entities: list[CodeEntity]
    ) -> list[Relationship]:
        """Map class inheritance hierarchies.

        Extracts base class names from class signatures and resolves them
        to known class entities.
        """
        relationships: list[Relationship] = []

        # Build class lookup
        class_index: dict[str, CodeEntity] = {}
        for entity in entities:
            if entity.entity_type == EntityType.CLASS:
                class_index[entity.name] = entity

        # Python: class Foo(Bar, Baz)
        python_bases = re.compile(r"class\s+\w+\(([^)]+)\)")
        # TypeScript/Java: class Foo extends Bar implements Baz
        ts_extends = re.compile(r"(?:extends|implements)\s+([\w,\s]+)")
        # Go: embedded structs (type Foo struct { Bar; ... })
        # Rust: trait implementations handled via impl blocks

        for entity in entities:
            if entity.entity_type != EntityType.CLASS:
                continue

            sig = entity.signature
            base_names: list[str] = []

            # Python style
            py_match = python_bases.search(sig)
            if py_match:
                raw_bases = py_match.group(1)
                base_names.extend(
                    b.strip().split(".")[-1]
                    for b in raw_bases.split(",")
                    if b.strip()
                )

            # TypeScript / Java style
            for ts_match in ts_extends.finditer(sig):
                raw = ts_match.group(1)
                base_names.extend(
                    b.strip() for b in raw.split(",") if b.strip()
                )

            for base_name in base_names:
                if base_name in class_index and base_name != entity.name:
                    relationships.append(
                        Relationship(
                            source_id=entity.id,
                            target_id=class_index[base_name].id,
                            relationship_type=RelationshipType.INHERITS,
                            weight=2.0,
                            metadata={"base_class": base_name},
                        )
                    )

            # Check for method overrides: methods in child with same name as
            # methods in parent
            for base_name in base_names:
                if base_name not in class_index:
                    continue
                parent = class_index[base_name]
                child_methods = {
                    e.name
                    for e in entities
                    if e.parent_id == entity.id and e.entity_type == EntityType.FUNCTION
                }
                parent_methods = {
                    e
                    for e in entities
                    if e.parent_id == parent.id and e.entity_type == EntityType.FUNCTION
                }
                for parent_method in parent_methods:
                    if parent_method.name in child_methods:
                        child_method = next(
                            (
                                e
                                for e in entities
                                if e.parent_id == entity.id
                                and e.name == parent_method.name
                                and e.entity_type == EntityType.FUNCTION
                            ),
                            None,
                        )
                        if child_method:
                            relationships.append(
                                Relationship(
                                    source_id=child_method.id,
                                    target_id=parent_method.id,
                                    relationship_type=RelationshipType.OVERRIDES,
                                    weight=1.5,
                                    metadata={"method_name": parent_method.name},
                                )
                            )

        logger.info("graph_builder.inheritance_detected", count=len(relationships))
        return relationships

    def _calculate_centrality(
        self,
        entities: list[CodeEntity],
        relationships: list[Relationship],
    ) -> dict[str, float]:
        """Compute centrality scores for all entities using networkx.

        Uses PageRank to identify the most critical code nodes -- those
        that are most depended upon or most central to the call graph.
        """
        if not entities:
            return {}

        G = nx.DiGraph()

        # Add nodes
        for entity in entities:
            G.add_node(
                entity.id,
                name=entity.name,
                entity_type=entity.entity_type.value,
                file_path=entity.file_path,
            )

        # Add edges
        for rel in relationships:
            if G.has_node(rel.source_id) and G.has_node(rel.target_id):
                G.add_edge(
                    rel.source_id,
                    rel.target_id,
                    weight=rel.weight,
                    relationship_type=rel.relationship_type.value,
                )

        # Compute PageRank
        try:
            pagerank = nx.pagerank(G, weight="weight", max_iter=100)
        except nx.PowerIterationFailedConvergence:
            logger.warning("graph_builder.pagerank_convergence_failed")
            pagerank = {node: 1.0 / len(G) for node in G.nodes()}

        # Also compute betweenness centrality for additional insight
        try:
            betweenness = nx.betweenness_centrality(G, weight="weight")
        except Exception:
            betweenness = {node: 0.0 for node in G.nodes()}

        # Combine: 60% PageRank + 40% betweenness (both normalized to [0,1])
        max_pr = max(pagerank.values()) if pagerank else 1.0
        max_bt = max(betweenness.values()) if betweenness and max(betweenness.values()) > 0 else 1.0

        combined: dict[str, float] = {}
        for node_id in G.nodes():
            pr_normalized = pagerank.get(node_id, 0.0) / max_pr if max_pr > 0 else 0.0
            bt_normalized = betweenness.get(node_id, 0.0) / max_bt if max_bt > 0 else 0.0
            combined[node_id] = round(0.6 * pr_normalized + 0.4 * bt_normalized, 6)

        logger.info(
            "graph_builder.centrality_calculated",
            node_count=len(combined),
            max_score=max(combined.values()) if combined else 0.0,
        )
        return combined

    async def _store_graph(self, graph: SemanticGraph) -> None:
        """Persist the semantic graph to Qdrant for vector-based retrieval.

        Stores each entity as a point with its metadata for later semantic
        search and retrieval.
        """
        try:
            from qdrant_client import QdrantClient
            from qdrant_client.models import Distance, PointStruct, VectorParams

            client = QdrantClient(url=settings.QDRANT_URL, timeout=30)
            collection_name = f"semantic_graph_{graph.repo_id}"

            # Create collection if it does not exist
            collections = client.get_collections().collections
            existing_names = {c.name for c in collections}
            if collection_name not in existing_names:
                client.create_collection(
                    collection_name=collection_name,
                    vectors_config=VectorParams(size=128, distance=Distance.COSINE),
                )

            # Store entities as points with simple hash-based vectors
            points: list[PointStruct] = []
            for i, entity in enumerate(graph.entities):
                # Generate a deterministic pseudo-vector from entity properties
                vector = self._entity_to_vector(entity)
                points.append(
                    PointStruct(
                        id=i,
                        vector=vector,
                        payload={
                            "entity_id": entity.id,
                            "name": entity.name,
                            "entity_type": entity.entity_type.value,
                            "file_path": entity.file_path,
                            "line_start": entity.line_start,
                            "line_end": entity.line_end,
                            "signature": entity.signature,
                            "docstring": entity.docstring[:500],
                            "complexity": entity.complexity,
                            "language": entity.language,
                            "centrality": graph.centrality_scores.get(entity.id, 0.0),
                        },
                    )
                )

            # Batch upsert
            batch_size = 100
            for start in range(0, len(points), batch_size):
                batch = points[start: start + batch_size]
                client.upsert(collection_name=collection_name, points=batch)

            logger.info(
                "graph_builder.qdrant_stored",
                collection=collection_name,
                points=len(points),
            )

        except ImportError:
            logger.warning("graph_builder.qdrant_client_not_available")
        except Exception as exc:
            logger.warning(
                "graph_builder.qdrant_store_failed",
                error=str(exc),
            )

    @staticmethod
    def _entity_to_vector(entity: CodeEntity) -> list[float]:
        """Generate a deterministic 128-dim pseudo-vector from entity metadata.

        This is a placeholder for a proper embedding model. In production,
        you would call an embedding API to get semantic vectors.
        """
        import hashlib

        # Combine key fields for hashing
        text = f"{entity.name}|{entity.entity_type.value}|{entity.signature}|{entity.docstring}"
        digest = hashlib.sha512(text.encode("utf-8")).digest()

        # Expand to 128 floats in [-1, 1]
        vector: list[float] = []
        for byte_val in digest:
            vector.append((byte_val / 127.5) - 1.0)
        # sha512 gives 64 bytes; double it
        digest2 = hashlib.sha512((text + "|v2").encode("utf-8")).digest()
        for byte_val in digest2:
            vector.append((byte_val / 127.5) - 1.0)

        return vector[:128]

    @staticmethod
    def _deduplicate_relationships(
        relationships: list[Relationship],
    ) -> list[Relationship]:
        """Remove duplicate relationships, keeping the one with highest weight."""
        seen: dict[tuple[str, str, str], Relationship] = {}
        for rel in relationships:
            key = (rel.source_id, rel.target_id, rel.relationship_type.value)
            existing = seen.get(key)
            if existing is None or rel.weight > existing.weight:
                seen[key] = rel
        return list(seen.values())
