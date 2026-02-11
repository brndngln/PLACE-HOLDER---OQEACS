#!/usr/bin/env python3
"""
Dependency checker for the Omni verification pipeline.

This script inspects Python and Node.js dependencies for potential
hallucinations or typos. It parses Python source files to extract
imported modules and attempts to import them in the current
environment. Modules that cannot be imported are flagged as
non‑existent. For Node.js projects, it inspects `package.json`
dependencies and checks if they are installed globally via npm. It
also checks for known malicious package names. Any findings cause
the script to exit with a non‑zero status code.
"""

from __future__ import annotations

import ast
import json
import os
import subprocess
import sys
from typing import List, Set


def find_python_imports(root: str) -> Set[str]:
    """Recursively parse Python files and collect top‑level import names."""
    imports: Set[str] = set()
    for dirpath, _, filenames in os.walk(root):
        for name in filenames:
            if name.endswith(".py"):
                path = os.path.join(dirpath, name)
                try:
                    with open(path, "r", encoding="utf-8") as fh:
                        tree = ast.parse(fh.read(), filename=path)
                    for node in ast.walk(tree):
                        if isinstance(node, ast.Import):
                            for alias in node.names:
                                imports.add(alias.name.split(".")[0])
                        elif isinstance(node, ast.ImportFrom):
                            if node.module:
                                imports.add(node.module.split(".")[0])
                except Exception:
                    # Skip files with syntax errors
                    continue
    return imports


def check_python_modules(modules: Set[str]) -> List[str]:
    """Return a list of modules that cannot be imported."""
    missing = []
    for mod in modules:
        try:
            __import__(mod)
        except Exception:
            missing.append(mod)
    return missing


def find_node_dependencies(root: str) -> Set[str]:
    """Read package.json files and collect dependencies."""
    deps: Set[str] = set()
    pkg_path = os.path.join(root, "package.json")
    if os.path.isfile(pkg_path):
        try:
            data = json.loads(open(pkg_path, encoding="utf-8").read())
            for section in ["dependencies", "devDependencies", "peerDependencies"]:
                for name in data.get(section, {}):
                    deps.add(name)
        except Exception:
            pass
    return deps


def check_node_modules(modules: Set[str]) -> List[str]:
    """Return modules not found in npm global list."""
    missing: List[str] = []
    try:
        completed = subprocess.run(
            ["npm", "ls", "-g", "--depth=0", "--json"],
            check=False,
            capture_output=True,
            text=True,
        )
        installed = set()
        if completed.stdout:
            data = json.loads(completed.stdout)
            for name in data.get("dependencies", {}).keys():
                installed.add(name)
        for mod in modules:
            if mod not in installed:
                missing.append(mod)
    except Exception:
        # If npm is unavailable, skip check
        missing.extend(list(modules))
    return missing


def main() -> None:
    project_root = os.getcwd()
    python_imports = find_python_imports(project_root)
    missing_python = check_python_modules(python_imports)
    node_deps = find_node_dependencies(project_root)
    missing_node = check_node_modules(node_deps)
    known_malicious = {"pandas_pro", "urllib3n"}
    malicious = [m for m in python_imports.union(node_deps) if m in known_malicious]
    findings = {}
    if missing_python:
        findings["missing_python"] = missing_python
    if missing_node:
        findings["missing_node"] = missing_node
    if malicious:
        findings["malicious"] = malicious
    if findings:
        print(json.dumps(findings, indent=2))
        sys.exit(1)
    else:
        print(json.dumps({"status": "ok"}))
        sys.exit(0)


if __name__ == "__main__":
    main()