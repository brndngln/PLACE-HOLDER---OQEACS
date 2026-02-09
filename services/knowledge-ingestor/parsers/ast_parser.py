"""Tree-sitter AST parsing engine for multi-language code analysis.

Extracts functions, classes, methods, and other structural elements from source
code using tree-sitter grammars. Computes cyclomatic complexity and detects
common design patterns via heuristic analysis.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import structlog
from tree_sitter_languages import get_language, get_parser

logger = structlog.get_logger()

# ─────────────────────────────────────────────────────────────────────────────
# Language → node types mapping
# ─────────────────────────────────────────────────────────────────────────────

LANGUAGE_NODE_TYPES: Dict[str, List[str]] = {
    "python": [
        "function_definition",
        "class_definition",
        "decorated_definition",
    ],
    "javascript": [
        "function_declaration",
        "class_declaration",
        "method_definition",
        "arrow_function",
        "export_statement",
    ],
    "typescript": [
        "function_declaration",
        "class_declaration",
        "method_definition",
        "arrow_function",
        "export_statement",
    ],
    "go": [
        "function_declaration",
        "method_declaration",
        "type_declaration",
    ],
    "rust": [
        "function_item",
        "impl_item",
        "struct_item",
        "enum_item",
        "trait_item",
    ],
    "c": [
        "function_definition",
        "struct_specifier",
        "enum_specifier",
    ],
    "cpp": [
        "function_definition",
        "class_specifier",
        "template_declaration",
    ],
    "java": [
        "method_declaration",
        "class_declaration",
        "interface_declaration",
    ],
}

BRANCH_NODE_TYPES = {
    "if_statement", "elif_clause", "else_clause",
    "for_statement", "for_in_statement", "for_range_clause",
    "while_statement",
    "try_statement", "except_clause", "catch_clause",
    "match_statement", "case_clause", "switch_case",
    "conditional_expression", "ternary_expression",
    "if_expression", "match_expression",
    "short_var_declaration",
    "binary_expression",
}

LANGUAGE_ALIASES: Dict[str, str] = {
    "c++": "cpp",
    "js": "javascript",
    "ts": "typescript",
    "py": "python",
}


@dataclass
class CodeChunk:
    """A parsed chunk of source code with metadata."""

    name: str
    kind: str  # function, class, method, struct, trait, enum, impl, type, module
    language: str
    file_path: str
    signature: str
    docstring: str
    body: str
    start_line: int
    end_line: int
    line_count: int
    parent_name: Optional[str]
    imports: List[str]
    complexity: int
    pattern_tags: List[str]
    content_hash: str

    def embedding_text(self) -> str:
        """Concatenate signature + docstring + first 200 tokens of body for embedding."""
        parts = []
        if self.signature:
            parts.append(self.signature)
        if self.docstring:
            parts.append(self.docstring)
        body_tokens = self.body.split()[:200]
        if body_tokens:
            parts.append(" ".join(body_tokens))
        return "\n".join(parts)

    def to_metadata(self) -> Dict[str, Any]:
        """Convert to metadata dict for Qdrant payload."""
        return {
            "name": self.name,
            "kind": self.kind,
            "language": self.language,
            "file_path": self.file_path,
            "function_name": self.name,
            "function_signature": self.signature,
            "docstring": self.docstring[:500] if self.docstring else "",
            "start_line": self.start_line,
            "end_line": self.end_line,
            "line_count": self.line_count,
            "parent_name": self.parent_name or "",
            "imports": self.imports,
            "complexity": self.complexity,
            "pattern_tags": self.pattern_tags,
            "content_hash": self.content_hash,
        }


class ASTParser:
    """Multi-language AST parser using tree-sitter grammars."""

    def __init__(self) -> None:
        self._parsers: Dict[str, Any] = {}
        self._languages: Dict[str, Any] = {}

    def _resolve_language(self, language: str) -> str:
        """Resolve language aliases to canonical names."""
        lang = language.lower().strip()
        return LANGUAGE_ALIASES.get(lang, lang)

    def _get_parser(self, language: str) -> Tuple[Any, Any]:
        """Get or create a tree-sitter parser for the given language."""
        lang = self._resolve_language(language)
        if lang not in self._parsers:
            try:
                ts_language = get_language(lang)
                parser = get_parser(lang)
                self._languages[lang] = ts_language
                self._parsers[lang] = parser
            except Exception as e:
                logger.error("parser_init_failed", language=lang, error=str(e))
                raise ValueError(f"Unsupported language: {lang}") from e
        return self._parsers[lang], self._languages[lang]

    def parse_file(
        self,
        source_code: str,
        language: str,
        file_path: str,
        max_chunk_lines: int = 500,
    ) -> List[CodeChunk]:
        """Parse a source file and extract code chunks.

        Args:
            source_code: The raw source text.
            language: Programming language name.
            file_path: Path within the repository.
            max_chunk_lines: Maximum lines per chunk before sub-splitting.

        Returns:
            List of CodeChunk objects extracted from the file.
        """
        lang = self._resolve_language(language)
        node_types = LANGUAGE_NODE_TYPES.get(lang)
        if not node_types:
            return self._fallback_file_chunk(source_code, language, file_path)

        try:
            parser, ts_lang = self._get_parser(lang)
        except ValueError:
            return self._fallback_file_chunk(source_code, language, file_path)

        tree = parser.parse(source_code.encode("utf-8"))
        root = tree.root_node
        source_lines = source_code.split("\n")
        file_imports = self._extract_imports(root, lang)

        chunks: List[CodeChunk] = []
        self._walk_tree(
            node=root,
            node_types=set(node_types),
            source_code=source_code,
            source_lines=source_lines,
            language=lang,
            file_path=file_path,
            file_imports=file_imports,
            parent_name=None,
            chunks=chunks,
            max_chunk_lines=max_chunk_lines,
        )

        if not chunks:
            return self._fallback_file_chunk(source_code, language, file_path)

        return chunks

    def _walk_tree(
        self,
        node: Any,
        node_types: set,
        source_code: str,
        source_lines: List[str],
        language: str,
        file_path: str,
        file_imports: List[str],
        parent_name: Optional[str],
        chunks: List[CodeChunk],
        max_chunk_lines: int,
    ) -> None:
        """Recursively walk AST and extract target node types."""
        if node.type in node_types:
            chunk = self._extract_chunk(
                node=node,
                source_code=source_code,
                source_lines=source_lines,
                language=language,
                file_path=file_path,
                file_imports=file_imports,
                parent_name=parent_name,
                max_chunk_lines=max_chunk_lines,
            )
            if chunk:
                if isinstance(chunk, list):
                    chunks.extend(chunk)
                else:
                    chunks.append(chunk)

                current_parent = chunk[0].name if isinstance(chunk, list) else chunk.name
                for child in node.children:
                    self._walk_tree(
                        child, node_types, source_code, source_lines,
                        language, file_path, file_imports, current_parent,
                        chunks, max_chunk_lines,
                    )
                return

        for child in node.children:
            self._walk_tree(
                child, node_types, source_code, source_lines,
                language, file_path, file_imports, parent_name,
                chunks, max_chunk_lines,
            )

    def _extract_chunk(
        self,
        node: Any,
        source_code: str,
        source_lines: List[str],
        language: str,
        file_path: str,
        file_imports: List[str],
        parent_name: Optional[str],
        max_chunk_lines: int,
    ) -> Optional[CodeChunk | List[CodeChunk]]:
        """Extract a CodeChunk from an AST node."""
        name = self._extract_name(node, language)
        if not name:
            name = f"anonymous_{node.start_point[0]}"

        start_line = node.start_point[0] + 1
        end_line = node.end_point[0] + 1
        body = source_code[node.start_byte:node.end_byte]
        line_count = end_line - start_line + 1

        signature = self._extract_signature(node, source_code, language)
        docstring = self._extract_docstring(node, source_code, language)
        kind = self._classify_kind(node, language)
        complexity = self._compute_complexity(node)
        pattern_tags = self._detect_patterns(node, source_code, language, name)
        content_hash = hashlib.sha256(body.encode("utf-8")).hexdigest()[:16]

        chunk = CodeChunk(
            name=name,
            kind=kind,
            language=language,
            file_path=file_path,
            signature=signature,
            docstring=docstring,
            body=body,
            start_line=start_line,
            end_line=end_line,
            line_count=line_count,
            parent_name=parent_name,
            imports=file_imports,
            complexity=complexity,
            pattern_tags=pattern_tags,
            content_hash=content_hash,
        )

        if line_count > max_chunk_lines:
            return self._split_large_chunk(chunk, max_chunk_lines)

        return chunk

    def _extract_name(self, node: Any, language: str) -> Optional[str]:
        """Extract the name of a function/class/struct from its AST node."""
        if node.type == "decorated_definition":
            for child in node.children:
                if child.type in ("function_definition", "class_definition"):
                    return self._extract_name(child, language)

        if node.type == "export_statement":
            for child in node.children:
                name = self._extract_name(child, language)
                if name:
                    return name

        name_field = node.child_by_field_name("name")
        if name_field:
            return name_field.text.decode("utf-8")

        declarator = node.child_by_field_name("declarator")
        if declarator:
            name_field = declarator.child_by_field_name("name") or declarator.child_by_field_name("declarator")
            if name_field:
                inner_name = name_field.child_by_field_name("name") if hasattr(name_field, "child_by_field_name") else None
                return (inner_name or name_field).text.decode("utf-8")

        return None

    def _extract_signature(self, node: Any, source_code: str, language: str) -> str:
        """Extract the function/method signature (first line or up to body)."""
        text = source_code[node.start_byte:node.end_byte]
        first_line = text.split("\n")[0].strip()

        if language in ("python",):
            body_node = node.child_by_field_name("body")
            if body_node:
                sig_end = body_node.start_byte - node.start_byte
                sig = source_code[node.start_byte:node.start_byte + sig_end].strip()
                sig = sig.rstrip(":")
                return sig
            return first_line

        if language in ("go", "rust", "c", "cpp", "java"):
            body_node = node.child_by_field_name("body")
            if body_node:
                sig = source_code[node.start_byte:body_node.start_byte].strip()
                return sig.rstrip("{").strip()

        return first_line

    def _extract_docstring(self, node: Any, source_code: str, language: str) -> str:
        """Extract docstring or leading comment from a node."""
        if language == "python":
            body = node.child_by_field_name("body")
            if body and body.children:
                first_stmt = body.children[0]
                if first_stmt.type == "expression_statement":
                    expr = first_stmt.children[0] if first_stmt.children else None
                    if expr and expr.type == "string":
                        doc = expr.text.decode("utf-8")
                        doc = doc.strip("\"'").strip()
                        return doc

        if language in ("javascript", "typescript", "java", "go", "rust", "c", "cpp"):
            prev = node.prev_sibling
            if prev and prev.type == "comment":
                comment = prev.text.decode("utf-8")
                comment = re.sub(r"^(//|/\*|\*/|\*)", "", comment, flags=re.MULTILINE).strip()
                return comment

        return ""

    def _classify_kind(self, node: Any, language: str) -> str:
        """Classify the node into a semantic kind."""
        type_map = {
            "function_definition": "function",
            "function_declaration": "function",
            "function_item": "function",
            "method_definition": "method",
            "method_declaration": "method",
            "class_definition": "class",
            "class_declaration": "class",
            "class_specifier": "class",
            "interface_declaration": "interface",
            "struct_specifier": "struct",
            "struct_item": "struct",
            "enum_specifier": "enum",
            "enum_item": "enum",
            "trait_item": "trait",
            "impl_item": "impl",
            "type_declaration": "type",
            "template_declaration": "template",
            "decorated_definition": "function",
            "arrow_function": "function",
            "export_statement": "function",
        }
        return type_map.get(node.type, "unknown")

    def _compute_complexity(self, node: Any) -> int:
        """Compute cyclomatic complexity: 1 + number of branching nodes."""
        count = 0

        def _walk(n: Any) -> None:
            nonlocal count
            if n.type in BRANCH_NODE_TYPES:
                count += 1
            for child in n.children:
                _walk(child)

        _walk(node)
        return 1 + count

    def _detect_patterns(
        self, node: Any, source_code: str, language: str, name: str
    ) -> List[str]:
        """Detect design patterns via heuristic analysis of AST structure."""
        body_text = source_code[node.start_byte:node.end_byte]
        tags: List[str] = []

        # Singleton: class with _instance + __new__
        if "_instance" in body_text and "__new__" in body_text:
            tags.append("singleton")

        # Factory: function returning different types based on input
        if re.search(r"(if|match|switch).*return\s+\w+\(", body_text, re.DOTALL):
            if name.lower().endswith(("factory", "create", "build", "make")):
                tags.append("factory")

        # Observer: subscribe/notify/observers
        observer_keywords = {"subscribe", "notify", "observers", "listeners", "emit", "on_event"}
        body_lower = body_text.lower()
        if sum(1 for kw in observer_keywords if kw in body_lower) >= 2:
            tags.append("observer")

        # Builder: chained set_* returning self
        if re.search(r"def\s+set_\w+.*return\s+self", body_text, re.DOTALL):
            tags.append("builder")
        if re.search(r"\.set_\w+\(.*\)\s*\.", body_text):
            tags.append("builder")

        # Repository: class with CRUD methods
        crud = {"get", "find", "create", "update", "delete", "save", "list", "fetch"}
        method_names = set(re.findall(r"def\s+(\w+)", body_text))
        if len(method_names & crud) >= 3:
            tags.append("repository")

        # Decorator: function taking and returning a function
        if language == "python":
            if re.search(r"def\s+\w+\(.*func.*\).*:\s*.*def\s+wrapper", body_text, re.DOTALL):
                tags.append("decorator-pattern")

        return tags

    def _extract_imports(self, root: Any, language: str) -> List[str]:
        """Extract import statements from the file root."""
        imports: List[str] = []

        def _walk(node: Any) -> None:
            if node.type in (
                "import_statement", "import_from_statement",
                "import_declaration", "use_declaration",
                "include", "preproc_include",
            ):
                imports.append(node.text.decode("utf-8").strip())
            for child in node.children:
                _walk(child)

        _walk(root)
        return imports[:50]  # cap to avoid huge import lists

    def _split_large_chunk(
        self, chunk: CodeChunk, max_lines: int
    ) -> List[CodeChunk]:
        """Split a chunk exceeding max_lines into sub-chunks."""
        lines = chunk.body.split("\n")
        sub_chunks: List[CodeChunk] = []
        total_lines = len(lines)
        part = 0

        for start in range(0, total_lines, max_lines):
            end = min(start + max_lines, total_lines)
            sub_body = "\n".join(lines[start:end])
            part += 1
            content_hash = hashlib.sha256(sub_body.encode("utf-8")).hexdigest()[:16]
            sub_chunks.append(
                CodeChunk(
                    name=f"{chunk.name}_part{part}",
                    kind=chunk.kind,
                    language=chunk.language,
                    file_path=chunk.file_path,
                    signature=chunk.signature if part == 1 else f"{chunk.name} (part {part})",
                    docstring=chunk.docstring if part == 1 else "",
                    body=sub_body,
                    start_line=chunk.start_line + start,
                    end_line=chunk.start_line + end - 1,
                    line_count=end - start,
                    parent_name=chunk.parent_name,
                    imports=chunk.imports if part == 1 else [],
                    complexity=chunk.complexity if part == 1 else 1,
                    pattern_tags=chunk.pattern_tags if part == 1 else [],
                    content_hash=content_hash,
                )
            )

        return sub_chunks

    def _fallback_file_chunk(
        self, source_code: str, language: str, file_path: str
    ) -> List[CodeChunk]:
        """Fall back to file-level chunking when AST parsing yields nothing."""
        content_hash = hashlib.sha256(source_code.encode("utf-8")).hexdigest()[:16]
        lines = source_code.split("\n")
        return [
            CodeChunk(
                name=file_path.split("/")[-1],
                kind="module",
                language=self._resolve_language(language),
                file_path=file_path,
                signature=f"// File: {file_path}",
                docstring="",
                body=source_code,
                start_line=1,
                end_line=len(lines),
                line_count=len(lines),
                parent_name=None,
                imports=[],
                complexity=1,
                pattern_tags=[],
                content_hash=content_hash,
            )
        ]

    @staticmethod
    def supported_languages() -> List[str]:
        """Return list of supported language names."""
        return list(LANGUAGE_NODE_TYPES.keys())
