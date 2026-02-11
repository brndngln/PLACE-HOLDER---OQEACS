#!/usr/bin/env python3
"""
Architecture Rule Enforcer

This script enforces architectural constraints defined in a YAML
configuration. It parses the Python codebase using the AST module,
builds an import graph and detects rule violations such as forbidden
layer dependencies and circular imports. When a violation is found,
the script prints a descriptive message and exits with a non‑zero
status code. Otherwise it exits with zero.
"""

from __future__ import annotations

import argparse
import ast
import os
import sys
from collections import defaultdict
from typing import Dict, List, Set, Tuple

try:
    import yaml  # type: ignore
except ImportError:
    yaml = None  # type: ignore


def load_rules(path: str) -> Dict:
    if yaml is None:
        raise RuntimeError("PyYAML is required to parse the rules file")
    with open(path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def get_layer(file_path: str) -> str:
    """Infer layer name based on path segments."""
    parts = file_path.split(os.sep)
    for segment in parts:
        lower = segment.lower()
        if lower in {"handler", "handlers"}:
            return "handler"
        if lower in {"service", "services"}:
            return "service"
        if lower in {"repository", "repositories", "repo", "repos"}:
            return "repository"
    return "unknown"


def build_module_map(root: str) -> Dict[str, str]:
    """Map module names (dotted) to file paths."""
    module_map = {}
    for dirpath, _, filenames in os.walk(root):
        for fname in filenames:
            if fname.endswith(".py"):
                path = os.path.join(dirpath, fname)
                rel = os.path.relpath(path, root)
                module = rel[:-3].replace(os.sep, ".")  # strip .py
                if os.path.basename(fname) == "__init__.py":
                    module = rel[:-12].replace(os.sep, ".")  # remove /__init__.py
                module_map[module] = rel
    return module_map


def parse_imports(file_path: str) -> List[Tuple[str, int]]:
    """Return a list of (imported_module, line_number) from a file."""
    imports: List[Tuple[str, int]] = []
    with open(file_path, "r", encoding="utf-8") as fh:
        try:
            tree = ast.parse(fh.read(), filename=file_path)
        except SyntaxError:
            return imports
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append((alias.name.split(".")[0], node.lineno))
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append((node.module.split(".")[0], node.lineno))
    return imports


def detect_circular(graph: Dict[str, Set[str]]) -> List[List[str]]:
    """Detect cycles in directed graph of module imports."""
    visited: Set[str] = set()
    stack: Set[str] = set()
    cycles: List[List[str]] = []

    def dfs(node: str, path: List[str]) -> None:
        visited.add(node)
        stack.add(node)
        path.append(node)
        for neighbor in graph.get(node, []):
            if neighbor not in visited:
                dfs(neighbor, path.copy())
            elif neighbor in stack:
                # Found a cycle
                cycle_start = path.index(neighbor)
                cycles.append(path[cycle_start:] + [neighbor])
        stack.remove(node)

    for node in graph:
        if node not in visited:
            dfs(node, [])
    return cycles


def main() -> None:
    parser = argparse.ArgumentParser(description="Architecture rule enforcer")
    parser.add_argument("--rules", default="rules.yml", help="Path to rules YAML file")
    parser.add_argument("root", nargs="?", default=".", help="Project root to analyze")
    args = parser.parse_args()
    rules = load_rules(args.rules)
    no_circular = bool(rules.get("no_circular", False))
    layer_rules = rules.get("layer_rules", {})
    root = os.path.abspath(args.root)

    # Build mapping of module -> file
    module_map = build_module_map(root)
    # Reverse mapping file -> module for quick lookup
    file_to_module = {v: k for k, v in module_map.items()}
    # Build import graph (file level)
    import_graph: Dict[str, Set[str]] = defaultdict(set)
    violations: List[str] = []

    for module, rel_path in module_map.items():
        file_path = os.path.join(root, rel_path)
        layer = get_layer(rel_path)
        imports = parse_imports(file_path)
        for imported, lineno in imports:
            # Resolve to module if local
            if imported in module_map:
                imported_path = module_map[imported]
                import_graph[rel_path].add(imported_path)
                imported_layer = get_layer(imported_path)
                # Check layer rule
                rules_for_layer = layer_rules.get(layer, {})
                forbidden = rules_for_layer.get("forbidden_imports", [])
                if imported_layer in forbidden:
                    violations.append(
                        f"Layer violation: {layer} importing {imported_layer} in {rel_path}:{lineno}"
                    )
            else:
                # External import; ignore
                pass
    # Detect circular dependencies
    if no_circular:
        cycles = detect_circular(import_graph)
        for cycle in cycles:
            formatted = " -> ".join(cycle)
            violations.append(f"Circular import detected: {formatted}")

    if violations:
        for v in violations:
            print(v)
        sys.exit(1)
    else:
        print("Architecture rules satisfied")
        sys.exit(0)


if __name__ == "__main__":
    main()