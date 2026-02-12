#!/usr/bin/env python3
"""
Dependency checker for the Omni verification pipeline.

This checker is intentionally offline-first and repository-aware:
- Python imports are validated against stdlib, local modules, and declared
  package manifests (requirements/pyproject), not the current interpreter.
- Node imports are validated against declared package.json dependencies, not
  globally installed npm packages.
"""

from __future__ import annotations

import ast
import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, List, Set


EXCLUDED_DIRS = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "archive",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
}

JS_EXTENSIONS = {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"}
PY_EXTENSIONS = {".py"}
SCAN_ROOT_PREFIXES = {"services", "omni-quantum-systems", "tools", "financial"}


PYTHON_IMPORT_ALIASES = {
    "git": "gitpython",
    "yaml": "pyyaml",
    "pil": "pillow",
    "cv2": "opencv-python",
    "dotenv": "python-dotenv",
    "dateutil": "python-dateutil",
    "bs4": "beautifulsoup4",
    "sklearn": "scikit-learn",
    "crypto": "pycryptodome",
    "google": "google-api-python-client",
    "sentry_sdk": "sentry-sdk",
    "starlette": "fastapi",
}

NODE_BUILTINS = {
    "assert",
    "buffer",
    "child_process",
    "crypto",
    "dns",
    "events",
    "fs",
    "http",
    "https",
    "net",
    "os",
    "path",
    "stream",
    "timers",
    "tls",
    "url",
    "util",
    "zlib",
}


def should_skip_dir(dirname: str) -> bool:
    return dirname in EXCLUDED_DIRS or dirname.startswith(".cache")


def iter_files(root: Path, extensions: Set[str]) -> Iterable[Path]:
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if not should_skip_dir(d)]
        for filename in filenames:
            path = Path(dirpath) / filename
            if path.suffix.lower() in extensions:
                yield path


def has_manifest_ancestor(path: Path, repo_root: Path) -> bool:
    cur = path.parent
    while True:
        if (cur / "requirements.txt").exists() or (cur / "pyproject.toml").exists():
            # Avoid using repo-root requirements.txt as a blanket manifest for
            # deeply nested service/config scripts.
            if cur == repo_root and len(path.relative_to(repo_root).parts) > 2:
                return False
            return True
        if cur == repo_root or cur.parent == cur:
            return False
        cur = cur.parent


def has_package_json_ancestor(path: Path, repo_root: Path) -> bool:
    cur = path.parent
    while True:
        if (cur / "package.json").exists():
            return True
        if cur == repo_root or cur.parent == cur:
            return False
        cur = cur.parent


def normalize_package_name(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name.strip().lower())


def parse_python_requirements(root: Path) -> Set[str]:
    packages: Set[str] = set()
    req_pattern = re.compile(r"^\s*([A-Za-z0-9_.-]+)(?:\[.*\])?\s*(?:==|>=|<=|>|<|~=|!=)")
    for req_file in root.rglob("requirements*.txt"):
        if any(part in EXCLUDED_DIRS for part in req_file.parts):
            continue
        try:
            for line in req_file.read_text(encoding="utf-8", errors="ignore").splitlines():
                stripped = line.strip()
                if not stripped or stripped.startswith("#"):
                    continue
                m = req_pattern.match(stripped)
                if m:
                    packages.add(normalize_package_name(m.group(1)))
        except OSError:
            continue
    return packages


def parse_pyproject_dependencies(root: Path) -> Set[str]:
    packages: Set[str] = set()
    for pyproject in root.rglob("pyproject.toml"):
        if any(part in EXCLUDED_DIRS for part in pyproject.parts):
            continue
        try:
            text = pyproject.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue

        # Lightweight extraction without adding a TOML dependency.
        # Handles common forms like:
        # dependencies = ["fastapi>=0.100", ...]
        # [tool.poetry.dependencies]
        # fastapi = "^0.115"
        for match in re.finditer(r'dependencies\s*=\s*\[(.*?)\]', text, flags=re.S):
            block = match.group(1)
            for dep in re.findall(r'"([^"]+)"', block):
                name = dep.split(";")[0].strip().split("[")[0]
                if name and re.match(r"^[A-Za-z0-9_.-]+", name):
                    packages.add(normalize_package_name(name))

        in_poetry = False
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("["):
                in_poetry = stripped == "[tool.poetry.dependencies]"
                continue
            if in_poetry and "=" in stripped and not stripped.startswith("python"):
                key = stripped.split("=", 1)[0].strip().strip('"').strip("'")
                if re.match(r"^[A-Za-z0-9_.-]+$", key):
                    packages.add(normalize_package_name(key))
    return packages


def find_local_python_modules(root: Path) -> Set[str]:
    modules: Set[str] = set()
    for path in iter_files(root, PY_EXTENSIONS):
        if path.name == "__init__.py":
            modules.add(path.parent.name)
        modules.add(path.stem)
        modules.add(path.parent.name)
    # Explicit roots frequently used in imports
    modules.update(
        {
            "app",
            "models",
            "routes",
            "services",
            "utils",
            "config",
            "src",
        }
    )
    return modules


def find_python_imports(root: Path) -> Set[str]:
    imports: Set[str] = set()
    for path in iter_files(root, PY_EXTENSIONS):
        rel_parts = path.relative_to(root).parts
        if not rel_parts or rel_parts[0] not in SCAN_ROOT_PREFIXES:
            continue
        if "fixtures" in path.parts or "templates" in path.parts:
            continue
        if not has_manifest_ancestor(path, root):
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8", errors="ignore"), filename=str(path))
        except Exception:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.add(alias.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module.split(".")[0])
    return imports


def extract_js_import_roots(source: str) -> Set[str]:
    roots: Set[str] = set()
    patterns = [
        r"""import\s+(?:.+?\s+from\s+)?['"]([^'"]+)['"]""",
        r"""require\(\s*['"]([^'"]+)['"]\s*\)""",
    ]
    for pattern in patterns:
        for match in re.finditer(pattern, source):
            mod = match.group(1).strip()
            if not mod or mod.startswith((".", "/", "#")) or mod.startswith("@/"):
                continue
            if mod.startswith("node:"):
                mod = mod.split(":", 1)[1]
            if mod.startswith("@"):
                parts = mod.split("/")
                root = "/".join(parts[:2]) if len(parts) > 1 else mod
            else:
                root = mod.split("/", 1)[0]
            roots.add(root)
    return roots


def parse_node_manifests(root: Path) -> Set[str]:
    deps: Set[str] = set()
    for package_json in root.rglob("package.json"):
        if any(part in EXCLUDED_DIRS for part in package_json.parts):
            continue
        try:
            data = json.loads(package_json.read_text(encoding="utf-8", errors="ignore"))
        except Exception:
            continue
        for section in ("dependencies", "devDependencies", "peerDependencies", "optionalDependencies"):
            for name in data.get(section, {}) or {}:
                deps.add(name)
    return deps


def find_node_imports(root: Path) -> Set[str]:
    imports: Set[str] = set()
    for path in iter_files(root, JS_EXTENSIONS):
        rel_parts = path.relative_to(root).parts
        if not rel_parts or rel_parts[0] not in SCAN_ROOT_PREFIXES:
            continue
        if "fixtures" in path.parts or "templates" in path.parts:
            continue
        if not has_package_json_ancestor(path, root):
            continue
        try:
            source = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        imports.update(extract_js_import_roots(source))
    return imports


def python_missing(
    imports: Set[str],
    declared_packages: Set[str],
    local_modules: Set[str],
) -> List[str]:
    stdlib = set(sys.stdlib_module_names)
    missing: Set[str] = set()

    for mod in imports:
        lowered = mod.lower()
        if mod in stdlib or lowered in stdlib:
            continue

        normalized_mod = normalize_package_name(PYTHON_IMPORT_ALIASES.get(lowered, lowered))
        if normalized_mod in local_modules:
            continue
        if normalized_mod in declared_packages:
            continue

        missing.add(mod)

    return sorted(missing)


def node_missing(imports: Set[str], declared_packages: Set[str]) -> List[str]:
    missing = sorted(
        mod for mod in imports if mod not in declared_packages and mod not in NODE_BUILTINS
    )
    return missing


@dataclass
class Findings:
    missing_python: List[str] = field(default_factory=list)
    missing_node: List[str] = field(default_factory=list)
    malicious: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        out: dict = {}
        if self.missing_python:
            out["missing_python"] = self.missing_python
        if self.missing_node:
            out["missing_node"] = self.missing_node
        if self.malicious:
            out["malicious"] = self.malicious
        if not out:
            out["status"] = "ok"
        return out

    def has_issues(self) -> bool:
        return bool(self.missing_python or self.missing_node or self.malicious)


def main() -> None:
    root = Path.cwd()

    py_imports = find_python_imports(root)
    py_declared = parse_python_requirements(root) | parse_pyproject_dependencies(root)
    local_py_modules = {normalize_package_name(m) for m in find_local_python_modules(root)}
    missing_py = python_missing(py_imports, py_declared, local_py_modules)

    node_imports = find_node_imports(root)
    node_declared = parse_node_manifests(root)
    missing_node_mods = node_missing(node_imports, node_declared)

    known_malicious = {"pandas_pro", "urllib3n"}
    malicious = sorted(
        pkg
        for pkg in (
            set(normalize_package_name(i) for i in py_imports)
            | set(normalize_package_name(i) for i in node_imports)
            | set(normalize_package_name(i) for i in py_declared)
            | set(normalize_package_name(i) for i in node_declared)
        )
        if pkg in known_malicious
    )

    findings = Findings(
        missing_python=missing_py,
        missing_node=missing_node_mods,
        malicious=malicious,
    )
    print(json.dumps(findings.to_dict(), indent=2))
    sys.exit(1 if findings.has_issues() else 0)


if __name__ == "__main__":
    main()
