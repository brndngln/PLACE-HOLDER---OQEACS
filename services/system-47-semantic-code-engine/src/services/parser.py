"""Code parser service using tree-sitter for multi-language AST analysis."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import structlog
import tree_sitter

from src.config import settings
from src.models import CodeEntity, EntityType, Relationship, RelationshipType

logger = structlog.get_logger(__name__)

# Language file extensions mapping
LANGUAGE_EXTENSIONS: dict[str, list[str]] = {
    "python": [".py"],
    "typescript": [".ts", ".tsx"],
    "go": [".go"],
    "rust": [".rs"],
    "java": [".java"],
}

# tree-sitter node types per language
PYTHON_FUNCTION_TYPES = {"function_definition", "async_function_definition"}
PYTHON_CLASS_TYPES = {"class_definition"}
PYTHON_IMPORT_TYPES = {"import_statement", "import_from_statement"}

TS_FUNCTION_TYPES = {
    "function_declaration",
    "arrow_function",
    "method_definition",
    "function_signature",
}
TS_CLASS_TYPES = {"class_declaration"}
TS_INTERFACE_TYPES = {"interface_declaration", "type_alias_declaration"}
TS_IMPORT_TYPES = {"import_statement"}

GO_FUNCTION_TYPES = {"function_declaration", "method_declaration"}
GO_STRUCT_TYPES = {"type_declaration"}
GO_IMPORT_TYPES = {"import_declaration"}

RUST_FUNCTION_TYPES = {"function_item"}
RUST_STRUCT_TYPES = {"struct_item", "enum_item"}
RUST_IMPL_TYPES = {"impl_item"}
RUST_IMPORT_TYPES = {"use_declaration"}

JAVA_FUNCTION_TYPES = {"method_declaration", "constructor_declaration"}
JAVA_CLASS_TYPES = {"class_declaration", "interface_declaration", "enum_declaration"}
JAVA_IMPORT_TYPES = {"import_declaration"}


def _node_text(node: tree_sitter.Node, source: bytes) -> str:
    """Extract text content from a tree-sitter node."""
    return source[node.start_byte:node.end_byte].decode("utf-8", errors="replace")


def _calculate_cyclomatic_complexity(source_text: str, language: str) -> int:
    """Estimate cyclomatic complexity from source code."""
    complexity = 1
    branch_keywords: dict[str, list[str]] = {
        "python": ["if ", "elif ", "for ", "while ", "except ", "with ", " and ", " or "],
        "typescript": ["if ", "else if", "for ", "while ", "catch ", "case ", "&&", "||", "?"],
        "go": ["if ", "for ", "case ", "&&", "||", "select "],
        "rust": ["if ", "match ", "for ", "while ", "loop ", "&&", "||", "?"],
        "java": ["if ", "else if", "for ", "while ", "catch ", "case ", "&&", "||", "?"],
    }
    keywords = branch_keywords.get(language, branch_keywords["python"])
    for keyword in keywords:
        complexity += source_text.count(keyword)
    return max(1, complexity)


class CodeParser:
    """Multi-language code parser using tree-sitter for AST analysis.

    Parses source files to extract code entities (functions, classes, modules,
    variables, imports) along with their relationships.
    """

    def __init__(self) -> None:
        self._parser = tree_sitter.Parser()
        self._languages: dict[str, tree_sitter.Language] = {}
        self._initialized = False
        logger.info("code_parser.created")

    def _ensure_initialized(self) -> None:
        """Lazily initialize tree-sitter languages."""
        if self._initialized:
            return
        for lang_name in settings.supported_languages:
            try:
                language = tree_sitter.Language(lang_name)
                self._languages[lang_name] = language
                logger.info("tree_sitter.language_loaded", language=lang_name)
            except Exception as exc:
                logger.warning(
                    "tree_sitter.language_load_failed",
                    language=lang_name,
                    error=str(exc),
                )
        self._initialized = True

    def parse_file(self, file_path: str, language: str) -> list[CodeEntity]:
        """Parse a source file and extract all code entities.

        Args:
            file_path: Absolute or relative path to the source file.
            language: Programming language identifier (python, typescript, go, rust, java).

        Returns:
            List of extracted CodeEntity objects.
        """
        self._ensure_initialized()

        path = Path(file_path)
        if not path.exists():
            logger.warning("parser.file_not_found", file_path=file_path)
            return []

        try:
            source = path.read_bytes()
        except (OSError, PermissionError) as exc:
            logger.error("parser.read_error", file_path=file_path, error=str(exc))
            return []

        if not source.strip():
            logger.debug("parser.empty_file", file_path=file_path)
            return []

        max_bytes = settings.MAX_FILE_SIZE_KB * 1024
        if len(source) > max_bytes:
            logger.warning(
                "parser.file_too_large",
                file_path=file_path,
                size_kb=len(source) // 1024,
            )
            return []

        tree = self._parse_source(source, language)
        if tree is None:
            return self._fallback_parse(source, file_path, language)

        dispatch: dict[str, Any] = {
            "python": self._parse_python,
            "typescript": self._parse_typescript,
            "go": self._parse_go,
            "rust": self._parse_rust,
            "java": self._parse_java,
        }

        handler = dispatch.get(language)
        if handler is None:
            logger.warning("parser.unsupported_language", language=language)
            return []

        entities = handler(source, tree, file_path)
        logger.info(
            "parser.file_parsed",
            file_path=file_path,
            language=language,
            entity_count=len(entities),
        )
        return entities

    def _parse_source(self, source: bytes, language: str) -> tree_sitter.Tree | None:
        """Parse source bytes into a tree-sitter Tree."""
        lang_obj = self._languages.get(language)
        if lang_obj is None:
            logger.debug("parser.no_tree_sitter_language", language=language)
            return None
        try:
            self._parser.language = lang_obj
            tree = self._parser.parse(source)
            return tree
        except Exception as exc:
            logger.warning("parser.tree_sitter_parse_error", error=str(exc))
            return None

    def _fallback_parse(
        self, source: bytes, file_path: str, language: str
    ) -> list[CodeEntity]:
        """Regex-based fallback parser when tree-sitter is unavailable."""
        text = source.decode("utf-8", errors="replace")
        entities: list[CodeEntity] = []

        if language == "python":
            entities.extend(self._fallback_parse_python(text, file_path))
        elif language == "typescript":
            entities.extend(self._fallback_parse_typescript(text, file_path))
        elif language == "go":
            entities.extend(self._fallback_parse_go(text, file_path))
        elif language == "rust":
            entities.extend(self._fallback_parse_rust(text, file_path))
        elif language == "java":
            entities.extend(self._fallback_parse_java(text, file_path))

        logger.info(
            "parser.fallback_used",
            file_path=file_path,
            language=language,
            entity_count=len(entities),
        )
        return entities

    # ---- Python Parsing ----

    def _parse_python(
        self, source: bytes, tree: tree_sitter.Tree, file_path: str
    ) -> list[CodeEntity]:
        """Extract entities from Python source using tree-sitter AST."""
        entities: list[CodeEntity] = []
        text = source.decode("utf-8", errors="replace")

        self._walk_python_node(tree.root_node, source, file_path, text, entities, parent_id=None)

        # Extract import entities from root
        for child in tree.root_node.children:
            if child.type in PYTHON_IMPORT_TYPES:
                import_text = _node_text(child, source).strip()
                entities.append(
                    CodeEntity(
                        name=self._extract_python_import_name(import_text),
                        entity_type=EntityType.IMPORT,
                        file_path=file_path,
                        line_start=child.start_point[0] + 1,
                        line_end=child.end_point[0] + 1,
                        signature=import_text,
                        language="python",
                        complexity=1,
                    )
                )

        return entities

    def _walk_python_node(
        self,
        node: tree_sitter.Node,
        source: bytes,
        file_path: str,
        text: str,
        entities: list[CodeEntity],
        parent_id: str | None,
    ) -> None:
        """Recursively walk the Python AST to extract entities."""
        for child in node.children:
            if child.type in PYTHON_FUNCTION_TYPES:
                entity = self._extract_python_function(child, source, file_path, text, parent_id)
                entities.append(entity)
                # Walk body for nested definitions
                body = self._find_child_by_type(child, "block")
                if body:
                    self._walk_python_node(body, source, file_path, text, entities, entity.id)

            elif child.type in PYTHON_CLASS_TYPES:
                entity = self._extract_python_class(child, source, file_path, text, parent_id)
                entities.append(entity)
                body = self._find_child_by_type(child, "block")
                if body:
                    self._walk_python_node(body, source, file_path, text, entities, entity.id)

            elif child.type == "expression_statement":
                # Check for module-level variable assignments
                assignment = self._find_child_by_type(child, "assignment")
                if assignment:
                    var_entity = self._extract_python_variable(
                        assignment, source, file_path, parent_id
                    )
                    if var_entity:
                        entities.append(var_entity)
            else:
                self._walk_python_node(child, source, file_path, text, entities, parent_id)

    def _extract_python_function(
        self,
        node: tree_sitter.Node,
        source: bytes,
        file_path: str,
        text: str,
        parent_id: str | None,
    ) -> CodeEntity:
        """Extract a Python function entity from a tree-sitter node."""
        name_node = self._find_child_by_type(node, "identifier")
        name = _node_text(name_node, source) if name_node else "<anonymous>"

        params_node = self._find_child_by_type(node, "parameters")
        params_text = _node_text(params_node, source) if params_node else "()"

        return_type = ""
        return_node = self._find_child_by_type(node, "type")
        if return_node:
            return_type = f" -> {_node_text(return_node, source)}"

        is_async = node.type == "async_function_definition"
        prefix = "async def" if is_async else "def"
        signature = f"{prefix} {name}{params_text}{return_type}"

        docstring = self._extract_python_docstring(node, source)
        decorators = self._extract_python_decorators(node, source)

        func_text = _node_text(node, source)
        complexity = _calculate_cyclomatic_complexity(func_text, "python")

        annotations: dict[str, str] = {}
        if params_node:
            for param_child in params_node.children:
                if param_child.type in ("typed_parameter", "typed_default_parameter"):
                    param_name_node = self._find_child_by_type(param_child, "identifier")
                    type_node = self._find_child_by_type(param_child, "type")
                    if param_name_node and type_node:
                        annotations[_node_text(param_name_node, source)] = _node_text(
                            type_node, source
                        )

        return CodeEntity(
            name=name,
            entity_type=EntityType.FUNCTION,
            file_path=file_path,
            line_start=node.start_point[0] + 1,
            line_end=node.end_point[0] + 1,
            signature=signature,
            docstring=docstring,
            complexity=complexity,
            language="python",
            parent_id=parent_id,
            decorators=decorators,
            annotations=annotations,
        )

    def _extract_python_class(
        self,
        node: tree_sitter.Node,
        source: bytes,
        file_path: str,
        text: str,
        parent_id: str | None,
    ) -> CodeEntity:
        """Extract a Python class entity from a tree-sitter node."""
        name_node = self._find_child_by_type(node, "identifier")
        name = _node_text(name_node, source) if name_node else "<anonymous>"

        bases = ""
        arg_list = self._find_child_by_type(node, "argument_list")
        if arg_list:
            bases = _node_text(arg_list, source)
        signature = f"class {name}{bases}"

        docstring = self._extract_python_docstring(node, source)
        decorators = self._extract_python_decorators(node, source)

        return CodeEntity(
            name=name,
            entity_type=EntityType.CLASS,
            file_path=file_path,
            line_start=node.start_point[0] + 1,
            line_end=node.end_point[0] + 1,
            signature=signature,
            docstring=docstring,
            complexity=1,
            language="python",
            parent_id=parent_id,
            decorators=decorators,
        )

    def _extract_python_variable(
        self,
        node: tree_sitter.Node,
        source: bytes,
        file_path: str,
        parent_id: str | None,
    ) -> CodeEntity | None:
        """Extract a Python variable assignment entity."""
        left = node.children[0] if node.children else None
        if left is None:
            return None
        name = _node_text(left, source).strip()
        if not name or name.startswith("_") and not name.startswith("__"):
            return None
        return CodeEntity(
            name=name,
            entity_type=EntityType.VARIABLE,
            file_path=file_path,
            line_start=node.start_point[0] + 1,
            line_end=node.end_point[0] + 1,
            signature=_node_text(node, source).strip(),
            language="python",
            parent_id=parent_id,
            complexity=1,
        )

    def _extract_python_docstring(
        self, node: tree_sitter.Node, source: bytes
    ) -> str:
        """Extract the docstring from a Python function or class node."""
        body = self._find_child_by_type(node, "block")
        if body is None or not body.children:
            return ""
        first_stmt = body.children[0]
        if first_stmt.type == "expression_statement":
            expr = first_stmt.children[0] if first_stmt.children else None
            if expr and expr.type == "string":
                raw = _node_text(expr, source)
                return raw.strip().strip('"""').strip("'''").strip('"').strip("'").strip()
        return ""

    def _extract_python_decorators(
        self, node: tree_sitter.Node, source: bytes
    ) -> list[str]:
        """Extract decorators applied to a Python function or class."""
        decorators: list[str] = []
        for child in node.children:
            if child.type == "decorator":
                dec_text = _node_text(child, source).strip()
                if dec_text.startswith("@"):
                    dec_text = dec_text[1:]
                decorators.append(dec_text)
        return decorators

    def _extract_python_import_name(self, import_text: str) -> str:
        """Extract the module name from a Python import statement."""
        match = re.match(r"from\s+([\w.]+)\s+import", import_text)
        if match:
            return match.group(1)
        match = re.match(r"import\s+([\w.]+)", import_text)
        if match:
            return match.group(1)
        return import_text.strip()

    # ---- TypeScript Parsing ----

    def _parse_typescript(
        self, source: bytes, tree: tree_sitter.Tree, file_path: str
    ) -> list[CodeEntity]:
        """Extract entities from TypeScript source using tree-sitter AST."""
        entities: list[CodeEntity] = []
        self._walk_ts_node(tree.root_node, source, file_path, entities, parent_id=None)
        return entities

    def _walk_ts_node(
        self,
        node: tree_sitter.Node,
        source: bytes,
        file_path: str,
        entities: list[CodeEntity],
        parent_id: str | None,
    ) -> None:
        """Recursively walk the TypeScript AST."""
        for child in node.children:
            if child.type in TS_FUNCTION_TYPES:
                entity = self._extract_ts_function(child, source, file_path, parent_id)
                entities.append(entity)
                body = self._find_child_by_type(child, "statement_block")
                if body:
                    self._walk_ts_node(body, source, file_path, entities, entity.id)

            elif child.type in TS_CLASS_TYPES:
                entity = self._extract_ts_class(child, source, file_path, parent_id)
                entities.append(entity)
                body = self._find_child_by_type(child, "class_body")
                if body:
                    self._walk_ts_node(body, source, file_path, entities, entity.id)

            elif child.type in TS_INTERFACE_TYPES:
                entity = self._extract_ts_interface(child, source, file_path, parent_id)
                entities.append(entity)

            elif child.type in TS_IMPORT_TYPES:
                import_text = _node_text(child, source).strip()
                entities.append(
                    CodeEntity(
                        name=self._extract_ts_import_name(import_text),
                        entity_type=EntityType.IMPORT,
                        file_path=file_path,
                        line_start=child.start_point[0] + 1,
                        line_end=child.end_point[0] + 1,
                        signature=import_text,
                        language="typescript",
                        complexity=1,
                    )
                )

            elif child.type == "export_statement":
                self._walk_ts_node(child, source, file_path, entities, parent_id)

            elif child.type == "lexical_declaration":
                for decl_child in child.children:
                    if decl_child.type == "variable_declarator":
                        name_node = self._find_child_by_type(decl_child, "identifier")
                        if name_node:
                            arrow = self._find_child_by_type(decl_child, "arrow_function")
                            if arrow:
                                entity = self._extract_ts_function(
                                    decl_child, source, file_path, parent_id,
                                    override_name=_node_text(name_node, source),
                                )
                                entities.append(entity)
                            else:
                                entities.append(
                                    CodeEntity(
                                        name=_node_text(name_node, source),
                                        entity_type=EntityType.VARIABLE,
                                        file_path=file_path,
                                        line_start=decl_child.start_point[0] + 1,
                                        line_end=decl_child.end_point[0] + 1,
                                        signature=_node_text(decl_child, source).strip(),
                                        language="typescript",
                                        parent_id=parent_id,
                                        complexity=1,
                                    )
                                )
            else:
                self._walk_ts_node(child, source, file_path, entities, parent_id)

    def _extract_ts_function(
        self,
        node: tree_sitter.Node,
        source: bytes,
        file_path: str,
        parent_id: str | None,
        override_name: str | None = None,
    ) -> CodeEntity:
        """Extract a TypeScript function entity."""
        if override_name:
            name = override_name
        else:
            name_node = self._find_child_by_type(node, "identifier")
            name = _node_text(name_node, source) if name_node else "<anonymous>"

        first_line = _node_text(node, source).split("\n")[0].strip()
        func_text = _node_text(node, source)
        complexity = _calculate_cyclomatic_complexity(func_text, "typescript")

        # Extract JSDoc comment
        docstring = self._extract_preceding_comment(node, source)

        return CodeEntity(
            name=name,
            entity_type=EntityType.FUNCTION,
            file_path=file_path,
            line_start=node.start_point[0] + 1,
            line_end=node.end_point[0] + 1,
            signature=first_line,
            docstring=docstring,
            complexity=complexity,
            language="typescript",
            parent_id=parent_id,
        )

    def _extract_ts_class(
        self,
        node: tree_sitter.Node,
        source: bytes,
        file_path: str,
        parent_id: str | None,
    ) -> CodeEntity:
        """Extract a TypeScript class entity."""
        name_node = self._find_child_by_type(node, "type_identifier")
        if name_node is None:
            name_node = self._find_child_by_type(node, "identifier")
        name = _node_text(name_node, source) if name_node else "<anonymous>"
        first_line = _node_text(node, source).split("\n")[0].strip()
        docstring = self._extract_preceding_comment(node, source)

        return CodeEntity(
            name=name,
            entity_type=EntityType.CLASS,
            file_path=file_path,
            line_start=node.start_point[0] + 1,
            line_end=node.end_point[0] + 1,
            signature=first_line,
            docstring=docstring,
            complexity=1,
            language="typescript",
            parent_id=parent_id,
        )

    def _extract_ts_interface(
        self,
        node: tree_sitter.Node,
        source: bytes,
        file_path: str,
        parent_id: str | None,
    ) -> CodeEntity:
        """Extract a TypeScript interface or type alias entity."""
        name_node = self._find_child_by_type(node, "type_identifier")
        if name_node is None:
            name_node = self._find_child_by_type(node, "identifier")
        name = _node_text(name_node, source) if name_node else "<anonymous>"
        first_line = _node_text(node, source).split("\n")[0].strip()
        docstring = self._extract_preceding_comment(node, source)

        return CodeEntity(
            name=name,
            entity_type=EntityType.CLASS,
            file_path=file_path,
            line_start=node.start_point[0] + 1,
            line_end=node.end_point[0] + 1,
            signature=first_line,
            docstring=docstring,
            complexity=1,
            language="typescript",
            parent_id=parent_id,
        )

    def _extract_ts_import_name(self, import_text: str) -> str:
        """Extract module name from a TypeScript import statement."""
        match = re.search(r"""from\s+['"]([^'"]+)['"]""", import_text)
        if match:
            return match.group(1)
        match = re.search(r"""import\s+['"]([^'"]+)['"]""", import_text)
        if match:
            return match.group(1)
        return import_text.strip()

    # ---- Go Parsing ----

    def _parse_go(
        self, source: bytes, tree: tree_sitter.Tree, file_path: str
    ) -> list[CodeEntity]:
        """Extract entities from Go source using tree-sitter AST."""
        entities: list[CodeEntity] = []
        self._walk_go_node(tree.root_node, source, file_path, entities)
        return entities

    def _walk_go_node(
        self,
        node: tree_sitter.Node,
        source: bytes,
        file_path: str,
        entities: list[CodeEntity],
    ) -> None:
        """Recursively walk the Go AST."""
        for child in node.children:
            if child.type == "function_declaration":
                name_node = self._find_child_by_type(child, "identifier")
                name = _node_text(name_node, source) if name_node else "<anonymous>"
                first_line = _node_text(child, source).split("{")[0].strip()
                func_text = _node_text(child, source)
                complexity = _calculate_cyclomatic_complexity(func_text, "go")
                docstring = self._extract_preceding_comment(child, source)

                entities.append(
                    CodeEntity(
                        name=name,
                        entity_type=EntityType.FUNCTION,
                        file_path=file_path,
                        line_start=child.start_point[0] + 1,
                        line_end=child.end_point[0] + 1,
                        signature=first_line,
                        docstring=docstring,
                        complexity=complexity,
                        language="go",
                    )
                )

            elif child.type == "method_declaration":
                name_node = self._find_child_by_type(child, "field_identifier")
                name = _node_text(name_node, source) if name_node else "<anonymous>"
                first_line = _node_text(child, source).split("{")[0].strip()
                func_text = _node_text(child, source)
                complexity = _calculate_cyclomatic_complexity(func_text, "go")
                docstring = self._extract_preceding_comment(child, source)

                # Extract receiver type
                receiver = ""
                params = child.children[0] if child.children else None
                if params and params.type == "parameter_list":
                    receiver = _node_text(params, source)

                entities.append(
                    CodeEntity(
                        name=name,
                        entity_type=EntityType.FUNCTION,
                        file_path=file_path,
                        line_start=child.start_point[0] + 1,
                        line_end=child.end_point[0] + 1,
                        signature=first_line,
                        docstring=docstring,
                        complexity=complexity,
                        language="go",
                        annotations={"receiver": receiver} if receiver else {},
                    )
                )

            elif child.type == "type_declaration":
                for spec in child.children:
                    if spec.type == "type_spec":
                        type_name_node = self._find_child_by_type(spec, "type_identifier")
                        type_name = (
                            _node_text(type_name_node, source) if type_name_node else "<anonymous>"
                        )
                        spec_text = _node_text(spec, source).strip()
                        is_interface = "interface" in spec_text
                        docstring = self._extract_preceding_comment(child, source)

                        entities.append(
                            CodeEntity(
                                name=type_name,
                                entity_type=EntityType.CLASS,
                                file_path=file_path,
                                line_start=spec.start_point[0] + 1,
                                line_end=spec.end_point[0] + 1,
                                signature=f"type {spec_text}".split("{")[0].strip(),
                                docstring=docstring,
                                complexity=1,
                                language="go",
                                annotations={"kind": "interface" if is_interface else "struct"},
                            )
                        )

            elif child.type in GO_IMPORT_TYPES:
                import_text = _node_text(child, source).strip()
                imports = re.findall(r'"([^"]+)"', import_text)
                for imp in imports:
                    entities.append(
                        CodeEntity(
                            name=imp.split("/")[-1] if "/" in imp else imp,
                            entity_type=EntityType.IMPORT,
                            file_path=file_path,
                            line_start=child.start_point[0] + 1,
                            line_end=child.end_point[0] + 1,
                            signature=f'import "{imp}"',
                            language="go",
                            complexity=1,
                        )
                    )
            else:
                self._walk_go_node(child, source, file_path, entities)

    # ---- Rust Parsing ----

    def _parse_rust(
        self, source: bytes, tree: tree_sitter.Tree, file_path: str
    ) -> list[CodeEntity]:
        """Extract entities from Rust source using tree-sitter AST."""
        entities: list[CodeEntity] = []
        self._walk_rust_node(tree.root_node, source, file_path, entities, parent_id=None)
        return entities

    def _walk_rust_node(
        self,
        node: tree_sitter.Node,
        source: bytes,
        file_path: str,
        entities: list[CodeEntity],
        parent_id: str | None,
    ) -> None:
        """Recursively walk the Rust AST."""
        for child in node.children:
            if child.type == "function_item":
                name_node = self._find_child_by_type(child, "identifier")
                name = _node_text(name_node, source) if name_node else "<anonymous>"
                first_line = _node_text(child, source).split("{")[0].strip()
                func_text = _node_text(child, source)
                complexity = _calculate_cyclomatic_complexity(func_text, "rust")
                docstring = self._extract_preceding_comment(child, source)

                entities.append(
                    CodeEntity(
                        name=name,
                        entity_type=EntityType.FUNCTION,
                        file_path=file_path,
                        line_start=child.start_point[0] + 1,
                        line_end=child.end_point[0] + 1,
                        signature=first_line,
                        docstring=docstring,
                        complexity=complexity,
                        language="rust",
                        parent_id=parent_id,
                    )
                )

            elif child.type in ("struct_item", "enum_item"):
                name_node = self._find_child_by_type(child, "type_identifier")
                name = _node_text(name_node, source) if name_node else "<anonymous>"
                first_line = _node_text(child, source).split("{")[0].strip()
                docstring = self._extract_preceding_comment(child, source)

                entities.append(
                    CodeEntity(
                        name=name,
                        entity_type=EntityType.CLASS,
                        file_path=file_path,
                        line_start=child.start_point[0] + 1,
                        line_end=child.end_point[0] + 1,
                        signature=first_line,
                        docstring=docstring,
                        complexity=1,
                        language="rust",
                        parent_id=parent_id,
                        annotations={"kind": "struct" if child.type == "struct_item" else "enum"},
                    )
                )

            elif child.type == "impl_item":
                type_node = self._find_child_by_type(child, "type_identifier")
                impl_name = _node_text(type_node, source) if type_node else "<anonymous>"
                decl_list = self._find_child_by_type(child, "declaration_list")
                if decl_list:
                    self._walk_rust_node(
                        decl_list, source, file_path, entities, parent_id=impl_name
                    )

            elif child.type == "use_declaration":
                import_text = _node_text(child, source).strip()
                match = re.search(r"use\s+(.+);", import_text)
                import_path = match.group(1) if match else import_text
                name = import_path.split("::")[-1].strip().strip("{}").split(",")[0].strip()
                entities.append(
                    CodeEntity(
                        name=name if name else import_path,
                        entity_type=EntityType.IMPORT,
                        file_path=file_path,
                        line_start=child.start_point[0] + 1,
                        line_end=child.end_point[0] + 1,
                        signature=import_text,
                        language="rust",
                        complexity=1,
                    )
                )
            else:
                self._walk_rust_node(child, source, file_path, entities, parent_id)

    # ---- Java Parsing ----

    def _parse_java(
        self, source: bytes, tree: tree_sitter.Tree, file_path: str
    ) -> list[CodeEntity]:
        """Extract entities from Java source using tree-sitter AST."""
        entities: list[CodeEntity] = []
        self._walk_java_node(tree.root_node, source, file_path, entities, parent_id=None)
        return entities

    def _walk_java_node(
        self,
        node: tree_sitter.Node,
        source: bytes,
        file_path: str,
        entities: list[CodeEntity],
        parent_id: str | None,
    ) -> None:
        """Recursively walk the Java AST."""
        for child in node.children:
            if child.type in JAVA_FUNCTION_TYPES:
                name_node = self._find_child_by_type(child, "identifier")
                name = _node_text(name_node, source) if name_node else "<constructor>"
                first_line = _node_text(child, source).split("{")[0].strip()
                func_text = _node_text(child, source)
                complexity = _calculate_cyclomatic_complexity(func_text, "java")
                docstring = self._extract_preceding_comment(child, source)

                entities.append(
                    CodeEntity(
                        name=name,
                        entity_type=EntityType.FUNCTION,
                        file_path=file_path,
                        line_start=child.start_point[0] + 1,
                        line_end=child.end_point[0] + 1,
                        signature=first_line,
                        docstring=docstring,
                        complexity=complexity,
                        language="java",
                        parent_id=parent_id,
                    )
                )

            elif child.type in JAVA_CLASS_TYPES:
                name_node = self._find_child_by_type(child, "identifier")
                name = _node_text(name_node, source) if name_node else "<anonymous>"
                first_line = _node_text(child, source).split("{")[0].strip()
                docstring = self._extract_preceding_comment(child, source)

                entity = CodeEntity(
                    name=name,
                    entity_type=EntityType.CLASS,
                    file_path=file_path,
                    line_start=child.start_point[0] + 1,
                    line_end=child.end_point[0] + 1,
                    signature=first_line,
                    docstring=docstring,
                    complexity=1,
                    language="java",
                    parent_id=parent_id,
                    annotations={"kind": child.type.replace("_declaration", "")},
                )
                entities.append(entity)

                body = self._find_child_by_type(child, "class_body")
                if body:
                    self._walk_java_node(body, source, file_path, entities, entity.id)

            elif child.type in JAVA_IMPORT_TYPES:
                import_text = _node_text(child, source).strip()
                match = re.search(r"import\s+([\w.]+);", import_text)
                import_name = match.group(1) if match else import_text
                short_name = import_name.split(".")[-1]
                entities.append(
                    CodeEntity(
                        name=short_name,
                        entity_type=EntityType.IMPORT,
                        file_path=file_path,
                        line_start=child.start_point[0] + 1,
                        line_end=child.end_point[0] + 1,
                        signature=import_text,
                        language="java",
                        complexity=1,
                    )
                )

            elif child.type == "program":
                self._walk_java_node(child, source, file_path, entities, parent_id)
            else:
                self._walk_java_node(child, source, file_path, entities, parent_id)

    # ---- Fallback Regex Parsers ----

    def _fallback_parse_python(self, text: str, file_path: str) -> list[CodeEntity]:
        """Regex-based Python parser as fallback."""
        entities: list[CodeEntity] = []
        lines = text.split("\n")

        for i, line in enumerate(lines):
            stripped = line.strip()

            # Functions
            match = re.match(r"^(\s*)(async\s+)?def\s+(\w+)\s*\(([^)]*)\)", line)
            if match:
                indent, is_async, name, params = match.groups()
                prefix = "async def" if is_async else "def"
                end_line = self._find_block_end(lines, i, len(indent or ""))
                func_text = "\n".join(lines[i:end_line + 1])
                complexity = _calculate_cyclomatic_complexity(func_text, "python")
                docstring = self._extract_regex_docstring(lines, i)
                entities.append(
                    CodeEntity(
                        name=name,
                        entity_type=EntityType.FUNCTION,
                        file_path=file_path,
                        line_start=i + 1,
                        line_end=end_line + 1,
                        signature=f"{prefix} {name}({params})",
                        docstring=docstring,
                        complexity=complexity,
                        language="python",
                    )
                )

            # Classes
            match = re.match(r"^(\s*)class\s+(\w+)\s*(\([^)]*\))?:", line)
            if match:
                indent, name, bases = match.groups()
                end_line = self._find_block_end(lines, i, len(indent or ""))
                bases_str = bases if bases else ""
                docstring = self._extract_regex_docstring(lines, i)
                entities.append(
                    CodeEntity(
                        name=name,
                        entity_type=EntityType.CLASS,
                        file_path=file_path,
                        line_start=i + 1,
                        line_end=end_line + 1,
                        signature=f"class {name}{bases_str}",
                        docstring=docstring,
                        complexity=1,
                        language="python",
                    )
                )

            # Imports
            if stripped.startswith("import ") or stripped.startswith("from "):
                entities.append(
                    CodeEntity(
                        name=self._extract_python_import_name(stripped),
                        entity_type=EntityType.IMPORT,
                        file_path=file_path,
                        line_start=i + 1,
                        line_end=i + 1,
                        signature=stripped,
                        language="python",
                        complexity=1,
                    )
                )

        return entities

    def _fallback_parse_typescript(self, text: str, file_path: str) -> list[CodeEntity]:
        """Regex-based TypeScript parser as fallback."""
        entities: list[CodeEntity] = []
        lines = text.split("\n")

        for i, line in enumerate(lines):
            stripped = line.strip()

            # Function declarations
            match = re.match(
                r"^(export\s+)?(async\s+)?function\s+(\w+)\s*[<(]", stripped
            )
            if match:
                _, is_async, name = match.groups()
                end_line = self._find_brace_block_end(lines, i)
                func_text = "\n".join(lines[i:end_line + 1])
                complexity = _calculate_cyclomatic_complexity(func_text, "typescript")
                entities.append(
                    CodeEntity(
                        name=name,
                        entity_type=EntityType.FUNCTION,
                        file_path=file_path,
                        line_start=i + 1,
                        line_end=end_line + 1,
                        signature=stripped.split("{")[0].strip(),
                        complexity=complexity,
                        language="typescript",
                    )
                )

            # Arrow function const
            match = re.match(
                r"^(export\s+)?(const|let|var)\s+(\w+)\s*[:=].*=>", stripped
            )
            if match:
                _, _, name = match.groups()
                end_line = self._find_brace_block_end(lines, i)
                func_text = "\n".join(lines[i:end_line + 1])
                complexity = _calculate_cyclomatic_complexity(func_text, "typescript")
                entities.append(
                    CodeEntity(
                        name=name,
                        entity_type=EntityType.FUNCTION,
                        file_path=file_path,
                        line_start=i + 1,
                        line_end=end_line + 1,
                        signature=stripped.split("{")[0].strip().rstrip("=>").strip(),
                        complexity=complexity,
                        language="typescript",
                    )
                )

            # Class declarations
            match = re.match(r"^(export\s+)?(abstract\s+)?class\s+(\w+)", stripped)
            if match:
                _, _, name = match.groups()
                end_line = self._find_brace_block_end(lines, i)
                entities.append(
                    CodeEntity(
                        name=name,
                        entity_type=EntityType.CLASS,
                        file_path=file_path,
                        line_start=i + 1,
                        line_end=end_line + 1,
                        signature=stripped.split("{")[0].strip(),
                        complexity=1,
                        language="typescript",
                    )
                )

            # Interface declarations
            match = re.match(r"^(export\s+)?interface\s+(\w+)", stripped)
            if match:
                _, name = match.groups()
                end_line = self._find_brace_block_end(lines, i)
                entities.append(
                    CodeEntity(
                        name=name,
                        entity_type=EntityType.CLASS,
                        file_path=file_path,
                        line_start=i + 1,
                        line_end=end_line + 1,
                        signature=stripped.split("{")[0].strip(),
                        complexity=1,
                        language="typescript",
                    )
                )

            # Import statements
            if stripped.startswith("import "):
                entities.append(
                    CodeEntity(
                        name=self._extract_ts_import_name(stripped),
                        entity_type=EntityType.IMPORT,
                        file_path=file_path,
                        line_start=i + 1,
                        line_end=i + 1,
                        signature=stripped,
                        language="typescript",
                        complexity=1,
                    )
                )

        return entities

    def _fallback_parse_go(self, text: str, file_path: str) -> list[CodeEntity]:
        """Regex-based Go parser as fallback."""
        entities: list[CodeEntity] = []
        lines = text.split("\n")

        for i, line in enumerate(lines):
            stripped = line.strip()

            # Function declarations
            match = re.match(r"^func\s+(\w+)\s*\(", stripped)
            if match:
                name = match.group(1)
                end_line = self._find_brace_block_end(lines, i)
                func_text = "\n".join(lines[i:end_line + 1])
                complexity = _calculate_cyclomatic_complexity(func_text, "go")
                entities.append(
                    CodeEntity(
                        name=name,
                        entity_type=EntityType.FUNCTION,
                        file_path=file_path,
                        line_start=i + 1,
                        line_end=end_line + 1,
                        signature=stripped.split("{")[0].strip(),
                        complexity=complexity,
                        language="go",
                    )
                )

            # Method declarations
            match = re.match(r"^func\s+\([^)]+\)\s+(\w+)\s*\(", stripped)
            if match:
                name = match.group(1)
                end_line = self._find_brace_block_end(lines, i)
                func_text = "\n".join(lines[i:end_line + 1])
                complexity = _calculate_cyclomatic_complexity(func_text, "go")
                entities.append(
                    CodeEntity(
                        name=name,
                        entity_type=EntityType.FUNCTION,
                        file_path=file_path,
                        line_start=i + 1,
                        line_end=end_line + 1,
                        signature=stripped.split("{")[0].strip(),
                        complexity=complexity,
                        language="go",
                    )
                )

            # Struct/interface types
            match = re.match(r"^type\s+(\w+)\s+(struct|interface)\s*\{?", stripped)
            if match:
                name, kind = match.groups()
                end_line = self._find_brace_block_end(lines, i)
                entities.append(
                    CodeEntity(
                        name=name,
                        entity_type=EntityType.CLASS,
                        file_path=file_path,
                        line_start=i + 1,
                        line_end=end_line + 1,
                        signature=f"type {name} {kind}",
                        complexity=1,
                        language="go",
                        annotations={"kind": kind},
                    )
                )

        return entities

    def _fallback_parse_rust(self, text: str, file_path: str) -> list[CodeEntity]:
        """Regex-based Rust parser as fallback."""
        entities: list[CodeEntity] = []
        lines = text.split("\n")

        for i, line in enumerate(lines):
            stripped = line.strip()

            # Functions
            match = re.match(r"^(pub\s+)?(async\s+)?fn\s+(\w+)", stripped)
            if match:
                _, _, name = match.groups()
                end_line = self._find_brace_block_end(lines, i)
                func_text = "\n".join(lines[i:end_line + 1])
                complexity = _calculate_cyclomatic_complexity(func_text, "rust")
                entities.append(
                    CodeEntity(
                        name=name,
                        entity_type=EntityType.FUNCTION,
                        file_path=file_path,
                        line_start=i + 1,
                        line_end=end_line + 1,
                        signature=stripped.split("{")[0].strip(),
                        complexity=complexity,
                        language="rust",
                    )
                )

            # Structs / Enums
            match = re.match(r"^(pub\s+)?(struct|enum)\s+(\w+)", stripped)
            if match:
                _, kind, name = match.groups()
                end_line = self._find_brace_block_end(lines, i)
                entities.append(
                    CodeEntity(
                        name=name,
                        entity_type=EntityType.CLASS,
                        file_path=file_path,
                        line_start=i + 1,
                        line_end=end_line + 1,
                        signature=stripped.split("{")[0].strip(),
                        complexity=1,
                        language="rust",
                        annotations={"kind": kind},
                    )
                )

        return entities

    def _fallback_parse_java(self, text: str, file_path: str) -> list[CodeEntity]:
        """Regex-based Java parser as fallback."""
        entities: list[CodeEntity] = []
        lines = text.split("\n")

        for i, line in enumerate(lines):
            stripped = line.strip()

            # Class / Interface
            match = re.match(
                r"^(public\s+|private\s+|protected\s+)?(abstract\s+)?"
                r"(class|interface|enum)\s+(\w+)",
                stripped,
            )
            if match:
                _, _, kind, name = match.groups()
                end_line = self._find_brace_block_end(lines, i)
                entities.append(
                    CodeEntity(
                        name=name,
                        entity_type=EntityType.CLASS,
                        file_path=file_path,
                        line_start=i + 1,
                        line_end=end_line + 1,
                        signature=stripped.split("{")[0].strip(),
                        complexity=1,
                        language="java",
                        annotations={"kind": kind},
                    )
                )

            # Method declarations
            match = re.match(
                r"^(public|private|protected)?\s*(static\s+)?([\w<>\[\]]+)\s+(\w+)\s*\(",
                stripped,
            )
            if match and not stripped.startswith("class ") and not stripped.startswith("new "):
                _, _, return_type, name = match.groups()
                if name not in ("if", "for", "while", "switch", "catch"):
                    end_line = self._find_brace_block_end(lines, i)
                    func_text = "\n".join(lines[i:end_line + 1])
                    complexity = _calculate_cyclomatic_complexity(func_text, "java")
                    entities.append(
                        CodeEntity(
                            name=name,
                            entity_type=EntityType.FUNCTION,
                            file_path=file_path,
                            line_start=i + 1,
                            line_end=end_line + 1,
                            signature=stripped.split("{")[0].strip(),
                            complexity=complexity,
                            language="java",
                        )
                    )

        return entities

    # ---- Dependency Extraction ----

    def extract_dependencies(
        self, entity: CodeEntity, all_entities: list[CodeEntity], source_text: str
    ) -> list[Relationship]:
        """Extract dependency relationships for a given entity.

        Traces import usage, function calls, and variable references within
        the entity's source code scope.

        Args:
            entity: The code entity to analyze.
            all_entities: All entities in the project for cross-referencing.
            source_text: The full source text of the entity's file.

        Returns:
            List of Relationship objects representing dependencies.
        """
        relationships: list[Relationship] = []
        lines = source_text.split("\n")
        entity_lines = lines[entity.line_start - 1: entity.line_end]
        entity_text = "\n".join(entity_lines)

        # Build name -> entity lookup (excluding self)
        name_to_entity: dict[str, CodeEntity] = {}
        for other in all_entities:
            if other.id != entity.id:
                name_to_entity[other.name] = other

        # Check for function calls
        if entity.entity_type in (EntityType.FUNCTION, EntityType.CLASS):
            call_pattern = re.compile(r"\b(\w+)\s*\(")
            for match in call_pattern.finditer(entity_text):
                called_name = match.group(1)
                if called_name in name_to_entity:
                    target = name_to_entity[called_name]
                    if target.entity_type == EntityType.FUNCTION:
                        relationships.append(
                            Relationship(
                                source_id=entity.id,
                                target_id=target.id,
                                relationship_type=RelationshipType.CALLS,
                                weight=1.0,
                                metadata={"call_site": match.start()},
                            )
                        )

        # Check for variable/class usage
        if entity.entity_type == EntityType.FUNCTION:
            for other_name, other_entity in name_to_entity.items():
                if other_entity.entity_type in (EntityType.CLASS, EntityType.VARIABLE):
                    if re.search(rf"\b{re.escape(other_name)}\b", entity_text):
                        relationships.append(
                            Relationship(
                                source_id=entity.id,
                                target_id=other_entity.id,
                                relationship_type=RelationshipType.USES,
                                weight=0.5,
                            )
                        )

        # Check class inheritance
        if entity.entity_type == EntityType.CLASS and entity.signature:
            bases_match = re.search(r"\(([^)]+)\)", entity.signature)
            if bases_match:
                bases = [b.strip() for b in bases_match.group(1).split(",")]
                for base_name in bases:
                    base_name = base_name.split(".")[-1].strip()
                    if base_name in name_to_entity:
                        relationships.append(
                            Relationship(
                                source_id=entity.id,
                                target_id=name_to_entity[base_name].id,
                                relationship_type=RelationshipType.INHERITS,
                                weight=2.0,
                                metadata={"base_class": base_name},
                            )
                        )

        # Check decorator usage
        for dec_name in entity.decorators:
            clean_name = dec_name.split("(")[0].split(".")[-1]
            if clean_name in name_to_entity:
                relationships.append(
                    Relationship(
                        source_id=name_to_entity[clean_name].id,
                        target_id=entity.id,
                        relationship_type=RelationshipType.DECORATES,
                        weight=1.5,
                    )
                )

        return relationships

    # ---- Helper Methods ----

    @staticmethod
    def _find_child_by_type(
        node: tree_sitter.Node, child_type: str
    ) -> tree_sitter.Node | None:
        """Find the first child node with the given type."""
        for child in node.children:
            if child.type == child_type:
                return child
        return None

    def _extract_preceding_comment(
        self, node: tree_sitter.Node, source: bytes
    ) -> str:
        """Extract a comment block immediately preceding a node (JSDoc, godoc, etc.)."""
        prev = node.prev_sibling
        if prev is None:
            return ""
        if prev.type in ("comment", "block_comment"):
            text = _node_text(prev, source).strip()
            # Clean comment markers
            text = re.sub(r"^/\*\*?|\*/$", "", text)
            text = re.sub(r"^\s*\*\s?", "", text, flags=re.MULTILINE)
            text = re.sub(r"^//\s?", "", text, flags=re.MULTILINE)
            return text.strip()
        return ""

    @staticmethod
    def _find_block_end(lines: list[str], start: int, base_indent: int) -> int:
        """Find the end of an indentation-based block (Python)."""
        end = start
        for j in range(start + 1, len(lines)):
            stripped = lines[j].strip()
            if not stripped:
                continue
            current_indent = len(lines[j]) - len(lines[j].lstrip())
            if current_indent <= base_indent:
                break
            end = j
        return end

    @staticmethod
    def _find_brace_block_end(lines: list[str], start: int) -> int:
        """Find the end of a brace-delimited block."""
        depth = 0
        found_open = False
        for j in range(start, len(lines)):
            for ch in lines[j]:
                if ch == "{":
                    depth += 1
                    found_open = True
                elif ch == "}":
                    depth -= 1
                    if found_open and depth == 0:
                        return j
        return min(start + 1, len(lines) - 1)

    @staticmethod
    def _extract_regex_docstring(lines: list[str], func_line: int) -> str:
        """Extract docstring from lines following a function definition."""
        for j in range(func_line + 1, min(func_line + 5, len(lines))):
            stripped = lines[j].strip()
            if not stripped:
                continue
            if stripped.startswith('"""') or stripped.startswith("'''"):
                quote = stripped[:3]
                if stripped.count(quote) >= 2:
                    return stripped.strip(quote).strip()
                # Multi-line docstring
                doc_lines = [stripped.lstrip(quote)]
                for k in range(j + 1, len(lines)):
                    if quote in lines[k]:
                        doc_lines.append(lines[k].strip().rstrip(quote).strip())
                        return "\n".join(doc_lines).strip()
                    doc_lines.append(lines[k].strip())
                return "\n".join(doc_lines).strip()
            break
        return ""
