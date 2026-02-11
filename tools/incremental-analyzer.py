#!/usr/bin/env python3
# ╔══════════════════════════════════════════════════════════════════════════════════════╗
# ║  INCREMENTAL ANALYSIS ENGINE — Only Analyze Changed Files + Dependents             ║
# ║  OMNI QUANTUM ELITE v3.0                                                           ║
# ╚══════════════════════════════════════════════════════════════════════════════════════╝

import argparse
import ast
import hashlib
import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set

import redis
import structlog

logger = structlog.get_logger()

REDIS_URL = os.getenv("REDIS_URL", "redis://omni-redis:6379")
HASH_KEY = "omni:file_hashes"
DEPS_KEY = "omni:dep_graph"

@dataclass
class FileInfo:
    path: str
    hash: str
    imports: List[str] = field(default_factory=list)
    changed: bool = False

class IncrementalAnalyzer:
    def __init__(self, workspace: str, use_cache: bool = True):
        self.workspace = Path(workspace).resolve()
        self.use_cache = use_cache
        self.redis: Optional[redis.Redis] = None
        self.file_hashes: Dict[str, str] = {}
        self.dep_graph: Dict[str, Set[str]] = {}  # file -> set of files that depend on it
        
        if use_cache:
            try:
                self.redis = redis.from_url(REDIS_URL, decode_responses=True)
                self.redis.ping()
                self._load_cache()
            except Exception as e:
                logger.warning("redis_unavailable", error=str(e))
                self.redis = None

    def _load_cache(self):
        """Load existing hashes and dependency graph from Redis."""
        if not self.redis:
            return
        
        hashes = self.redis.hgetall(HASH_KEY)
        self.file_hashes = hashes or {}
        
        deps_raw = self.redis.hgetall(DEPS_KEY)
        for path, deps_json in (deps_raw or {}).items():
            self.dep_graph[path] = set(json.loads(deps_json))
        
        logger.info("cache_loaded", files=len(self.file_hashes), deps=len(self.dep_graph))

    def _save_cache(self):
        """Persist hashes and dependency graph to Redis."""
        if not self.redis:
            return
        
        if self.file_hashes:
            self.redis.hset(HASH_KEY, mapping=self.file_hashes)
        
        for path, deps in self.dep_graph.items():
            self.redis.hset(DEPS_KEY, path, json.dumps(list(deps)))
        
        logger.info("cache_saved", files=len(self.file_hashes), deps=len(self.dep_graph))

    def _compute_hash(self, filepath: Path) -> str:
        """Compute SHA-256 hash of file contents."""
        try:
            content = filepath.read_bytes()
            return hashlib.sha256(content).hexdigest()
        except Exception:
            return ""

    def _extract_python_imports(self, filepath: Path) -> List[str]:
        """Extract imports from Python file using AST."""
        imports = []
        try:
            content = filepath.read_text()
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name.split('.')[0])
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.append(node.module.split('.')[0])
        except Exception as e:
            logger.debug("python_parse_failed", file=str(filepath), error=str(e))
        return imports

    def _extract_js_imports(self, filepath: Path) -> List[str]:
        """Extract imports from JavaScript/TypeScript file using regex."""
        imports = []
        try:
            content = filepath.read_text()
            # ES6 imports: import x from 'y'
            es6_pattern = r"import\s+.*?\s+from\s+['\"]([^'\"]+)['\"]"
            imports.extend(re.findall(es6_pattern, content))
            # CommonJS: require('x')
            cjs_pattern = r"require\s*\(\s*['\"]([^'\"]+)['\"]\s*\)"
            imports.extend(re.findall(cjs_pattern, content))
        except Exception as e:
            logger.debug("js_parse_failed", file=str(filepath), error=str(e))
        return imports

    def _resolve_import_to_file(self, import_name: str, source_file: Path) -> Optional[str]:
        """Try to resolve an import name to an actual file path."""
        source_dir = source_file.parent
        
        # Try relative paths
        candidates = [
            source_dir / f"{import_name}.py",
            source_dir / import_name / "__init__.py",
            self.workspace / "src" / f"{import_name}.py",
            self.workspace / "src" / import_name / "__init__.py",
            self.workspace / f"{import_name}.py",
        ]
        
        for candidate in candidates:
            if candidate.exists():
                return str(candidate.relative_to(self.workspace))
        
        return None

    def scan_workspace(self) -> Dict[str, FileInfo]:
        """Scan all relevant files in workspace."""
        files: Dict[str, FileInfo] = {}
        
        extensions = {'.py', '.js', '.ts', '.jsx', '.tsx'}
        exclude_dirs = {'node_modules', '.git', '.venv', '__pycache__', 'dist', 'build'}
        
        for root, dirs, filenames in os.walk(self.workspace):
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            
            for filename in filenames:
                ext = Path(filename).suffix
                if ext not in extensions:
                    continue
                
                filepath = Path(root) / filename
                rel_path = str(filepath.relative_to(self.workspace))
                
                file_hash = self._compute_hash(filepath)
                
                if ext == '.py':
                    imports = self._extract_python_imports(filepath)
                elif ext in {'.js', '.ts', '.jsx', '.tsx'}:
                    imports = self._extract_js_imports(filepath)
                else:
                    imports = []
                
                # Check if file changed
                old_hash = self.file_hashes.get(rel_path, "")
                changed = (old_hash != file_hash) if old_hash else True
                
                files[rel_path] = FileInfo(
                    path=rel_path,
                    hash=file_hash,
                    imports=imports,
                    changed=changed,
                )
                
                # Update hash cache
                self.file_hashes[rel_path] = file_hash
        
        return files

    def build_dependency_graph(self, files: Dict[str, FileInfo]):
        """Build reverse dependency graph (who depends on whom)."""
        self.dep_graph.clear()
        
        for rel_path, info in files.items():
            for imp in info.imports:
                resolved = self._resolve_import_to_file(imp, self.workspace / rel_path)
                if resolved and resolved in files:
                    if resolved not in self.dep_graph:
                        self.dep_graph[resolved] = set()
                    self.dep_graph[resolved].add(rel_path)

    def get_affected_files(self, changed_files: List[str]) -> Set[str]:
        """Get all files affected by changes (changed + dependents)."""
        affected = set(changed_files)
        to_process = list(changed_files)
        
        while to_process:
            current = to_process.pop()
            dependents = self.dep_graph.get(current, set())
            for dep in dependents:
                if dep not in affected:
                    affected.add(dep)
                    to_process.append(dep)
        
        return affected

    def analyze(self, explicit_changed: Optional[List[str]] = None) -> Dict:
        """Main analysis entry point."""
        logger.info("scan_started", workspace=str(self.workspace))
        
        # Scan all files
        files = self.scan_workspace()
        logger.info("scan_complete", total_files=len(files))
        
        # Build dependency graph
        self.build_dependency_graph(files)
        logger.info("deps_built", edges=sum(len(v) for v in self.dep_graph.values()))
        
        # Determine changed files
        if explicit_changed:
            changed = [f for f in explicit_changed if f in files]
        else:
            changed = [path for path, info in files.items() if info.changed]
        
        logger.info("changes_detected", changed_count=len(changed))
        
        if not changed:
            self._save_cache()
            return {
                "changed_files": [],
                "affected_files": [],
                "total_files": len(files),
                "analysis_required": [],
            }
        
        # Get all affected files
        affected = self.get_affected_files(changed)
        
        # Save updated cache
        self._save_cache()
        
        result = {
            "changed_files": sorted(changed),
            "affected_files": sorted(affected),
            "total_files": len(files),
            "analysis_required": sorted(affected),
            "skipped_files": sorted(set(files.keys()) - affected),
            "reduction_percent": round((1 - len(affected) / len(files)) * 100, 1) if files else 0,
        }
        
        logger.info("analysis_complete",
                   changed=len(changed),
                   affected=len(affected),
                   skipped=len(result["skipped_files"]),
                   reduction_percent=result["reduction_percent"])
        
        return result

def main():
    parser = argparse.ArgumentParser(description="Incremental Analysis Engine")
    parser.add_argument("--workspace", default=".", help="Workspace directory")
    parser.add_argument("--changed", nargs="*", help="Explicitly specify changed files")
    parser.add_argument("--no-cache", action="store_true", help="Disable Redis cache")
    parser.add_argument("--output", help="Output JSON file")
    parser.add_argument("--list-only", action="store_true", help="Only list files to analyze (one per line)")
    args = parser.parse_args()
    
    analyzer = IncrementalAnalyzer(
        workspace=args.workspace,
        use_cache=not args.no_cache,
    )
    
    result = analyzer.analyze(explicit_changed=args.changed)
    
    if args.list_only:
        for f in result["analysis_required"]:
            print(f)
    elif args.output:
        with open(args.output, 'w') as f:
            json.dump(result, f, indent=2)
        print(f"Results written to {args.output}")
    else:
        print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
