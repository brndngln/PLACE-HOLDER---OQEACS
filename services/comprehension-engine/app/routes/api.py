from __future__ import annotations

import ast
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from app.models.requests import CreateAnalysisRequest

router = APIRouter()

ANALYSES: dict[str, dict[str, Any]] = {}
SUPPORTED_LANGUAGES = ["python", "javascript", "typescript", "go", "rust", "java", "ruby", "c", "cpp", "kotlin", "swift"]


def _detect_language(path: Path) -> str:
    ext = path.suffix.lower()
    return {
        ".py": "python",
        ".js": "javascript",
        ".ts": "typescript",
        ".go": "go",
        ".rs": "rust",
        ".java": "java",
        ".rb": "ruby",
        ".c": "c",
        ".cpp": "cpp",
        ".kt": "kotlin",
        ".swift": "swift",
    }.get(ext, "unknown")


def _scan_structure(base: Path) -> dict[str, Any]:
    files = []
    dep_graph = []
    languages: dict[str, int] = {}
    total_lines = 0
    entry_points: list[str] = []
    for file in base.rglob("*"):
        if not file.is_file():
            continue
        language = _detect_language(file)
        if language == "unknown":
            continue
        try:
            content = file.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        lines = len(content.splitlines())
        total_lines += lines
        languages[language] = languages.get(language, 0) + 1
        imports: list[str] = []
        exports: list[str] = []
        functions: list[str] = []
        classes: list[str] = []
        complexity = max(1, lines // 25)

        if language == "python":
            try:
                tree = ast.parse(content)
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        imports.extend(alias.name for alias in node.names)
                    if isinstance(node, ast.ImportFrom):
                        imports.append(node.module or "")
                    if isinstance(node, ast.FunctionDef):
                        functions.append(node.name)
                    if isinstance(node, ast.ClassDef):
                        classes.append(node.name)
                if '__name__ == "__main__"' in content:
                    entry_points.append(str(file.relative_to(base)))
            except SyntaxError:
                pass
        else:
            imports.extend(re.findall(r"import\s+([A-Za-z0-9_./-]+)", content))
            functions.extend(re.findall(r"function\s+([A-Za-z0-9_]+)", content))
            classes.extend(re.findall(r"class\s+([A-Za-z0-9_]+)", content))

        rel = file.relative_to(base).as_posix()
        for imp in imports:
            if imp:
                dep_graph.append({"source": rel, "target": imp, "import_type": "local" if imp.startswith(".") else "third_party"})

        files.append(
            {
                "path": rel,
                "language": language,
                "lines": lines,
                "complexity": complexity,
                "imports": imports,
                "exports": exports,
                "functions": functions,
                "classes": classes,
            }
        )

    avg_complexity = (sum(f["complexity"] for f in files) / len(files)) if files else 0.0
    return {
        "files": files,
        "dependency_graph": dep_graph,
        "entry_points": sorted(set(entry_points)),
        "total_lines": total_lines,
        "total_files": len(files),
        "languages": languages,
        "avg_complexity": round(avg_complexity, 2),
    }


def _detect_patterns(structure: dict[str, Any]) -> dict[str, Any]:
    frameworks = []
    evidence = []
    file_paths = [f["path"] for f in structure["files"]]
    python_files = [f for f in structure["files"] if f["language"] == "python"]
    joined = "\n".join(file_paths).lower()
    if any("fastapi" in " ".join(f["imports"]) for f in python_files):
        frameworks.append({"name": "FastAPI", "version": "unknown", "confidence": 0.9, "evidence": ["fastapi imports"]})
        evidence.append("fastapi imports")
    if "next.config" in joined or "pages/" in joined or "app/" in joined:
        frameworks.append({"name": "Next.js", "version": "unknown", "confidence": 0.7, "evidence": ["next.js file structure"]})
        evidence.append("next.js structure")

    architecture = "feature-based"
    if any("controllers/" in p for p in file_paths) and any("models/" in p for p in file_paths):
        architecture = "mvc"

    return {
        "frameworks": frameworks,
        "architecture": architecture,
        "architecture_confidence": 0.7,
        "orm": "sqlalchemy" if any("sqlalchemy" in " ".join(f["imports"]) for f in python_files) else "unknown",
        "auth_pattern": "jwt" if any("jwt" in " ".join(f["imports"]) for f in python_files) else "unknown",
        "state_management": "n/a",
        "testing_framework": "pytest" if any("test" in p for p in file_paths) else "unknown",
        "api_style": "rest",
        "evidence": evidence,
    }


def _extract_conventions(structure: dict[str, Any]) -> dict[str, Any]:
    names = []
    for f in structure["files"]:
        names.extend(f["functions"])
        names.extend(f["classes"])
    snake = sum(1 for n in names if "_" in n)
    camel = sum(1 for n in names if re.search(r"[a-z][A-Z]", n))
    naming = "snake_case" if snake >= camel else "camelCase"
    return {
        "naming_convention": naming,
        "file_organization": "feature-based",
        "import_style": "grouped",
        "error_handling": "exceptions",
        "logging_approach": "structured",
        "config_approach": "environment variables",
        "test_style": "pytest",
        "api_response_format": "json",
    }


def _profile_markdown(analysis_id: str, structure: dict[str, Any], patterns: dict[str, Any], conventions: dict[str, Any]) -> str:
    frameworks = ", ".join(f["name"] for f in patterns.get("frameworks", [])) or "Unknown"
    top_langs = sorted(structure["languages"].items(), key=lambda x: x[1], reverse=True)
    lang_summary = ", ".join(f"{k} ({v})" for k, v in top_langs) or "none"
    return (
        f"# Codebase Profile {analysis_id}\n\n"
        f"## Structure\n- Total files: {structure['total_files']}\n- Total lines: {structure['total_lines']}\n- Languages: {lang_summary}\n"
        f"\n## Patterns\n- Frameworks: {frameworks}\n- Architecture: {patterns['architecture']}\n- API style: {patterns['api_style']}\n"
        f"\n## Conventions\n- Naming: {conventions['naming_convention']}\n- Imports: {conventions['import_style']}\n- Error handling: {conventions['error_handling']}\n"
        f"\n## Guidance\nMatch existing conventions exactly. Keep changes incremental and test-backed."
    )


@router.post("/api/v1/analyses")
async def create_analysis(request: CreateAnalysisRequest) -> dict[str, Any]:
    analysis_id = f"ana-{uuid.uuid4().hex[:12]}"
    source_path = Path(request.local_path) if request.local_path else None
    if source_path is None:
        raise HTTPException(status_code=422, detail="repo_url flow requires git access; provide local_path")
    if not source_path.exists() or not source_path.is_dir():
        raise HTTPException(status_code=404, detail="local_path not found")

    structure = _scan_structure(source_path)
    patterns = _detect_patterns(structure)
    conventions = _extract_conventions(structure)
    profile = _profile_markdown(analysis_id, structure, patterns, conventions)

    now = datetime.now(timezone.utc).isoformat()
    ANALYSES[analysis_id] = {
        "analysis_id": analysis_id,
        "repo_url": request.repo_url,
        "local_path": str(source_path),
        "git_ref": request.git_ref,
        "status": "complete",
        "depth": request.depth,
        "created_at": now,
        "completed_at": now,
        "structure": structure,
        "patterns": patterns,
        "conventions": conventions,
        "profile_markdown": profile,
    }
    return {"analysis_id": analysis_id, "status": "queued" if request.depth == "quick" else "complete"}


@router.get("/api/v1/analyses")
async def list_analyses(page: int = Query(default=1, ge=1), per_page: int = Query(default=20, ge=1, le=100), status: str | None = None) -> dict[str, Any]:
    rows = list(ANALYSES.values())
    if status:
        rows = [r for r in rows if r["status"] == status]
    start = (page - 1) * per_page
    return {"items": rows[start : start + per_page], "total": len(rows), "page": page, "per_page": per_page}


@router.get("/api/v1/analyses/{analysis_id}")
async def get_analysis(analysis_id: str) -> dict[str, Any]:
    data = ANALYSES.get(analysis_id)
    if not data:
        raise HTTPException(status_code=404, detail="analysis not found")
    return data


@router.get("/api/v1/analyses/{analysis_id}/profile")
async def get_profile(analysis_id: str) -> dict[str, Any]:
    data = ANALYSES.get(analysis_id)
    if not data:
        raise HTTPException(status_code=404, detail="analysis not found")
    return {"analysis_id": analysis_id, "profile_markdown": data["profile_markdown"]}


@router.get("/api/v1/analyses/{analysis_id}/structure")
async def get_structure(analysis_id: str) -> dict[str, Any]:
    data = ANALYSES.get(analysis_id)
    if not data:
        raise HTTPException(status_code=404, detail="analysis not found")
    return data["structure"]


@router.get("/api/v1/analyses/{analysis_id}/patterns")
async def get_patterns(analysis_id: str) -> dict[str, Any]:
    data = ANALYSES.get(analysis_id)
    if not data:
        raise HTTPException(status_code=404, detail="analysis not found")
    return data["patterns"]


@router.get("/api/v1/analyses/{analysis_id}/conventions")
async def get_conventions(analysis_id: str) -> dict[str, Any]:
    data = ANALYSES.get(analysis_id)
    if not data:
        raise HTTPException(status_code=404, detail="analysis not found")
    return data["conventions"]


@router.post("/api/v1/analyses/{analysis_id}/update")
async def update_analysis(analysis_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    data = ANALYSES.get(analysis_id)
    if not data:
        raise HTTPException(status_code=404, detail="analysis not found")
    changed_files = payload.get("changed_files", [])
    data["updated_files"] = changed_files
    data["completed_at"] = datetime.now(timezone.utc).isoformat()
    return {"analysis_id": analysis_id, "updated_files": changed_files}


@router.post("/api/v1/analyses/{analysis_id}/validate")
async def validate_conventions(analysis_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    data = ANALYSES.get(analysis_id)
    if not data:
        raise HTTPException(status_code=404, detail="analysis not found")
    code = payload.get("code", "")
    file_path = payload.get("file_path", "")
    expected = data["conventions"]["naming_convention"]
    violations = []
    if expected == "snake_case" and re.search(r"def\s+[a-z]+[A-Z]", code):
        violations.append({"rule": "naming", "line": 1, "message": "Expected snake_case", "suggestion": "Rename functions using snake_case"})
    if expected == "camelCase" and re.search(r"def\s+[a-z]+_[a-z]", code):
        violations.append({"rule": "naming", "line": 1, "message": "Expected camelCase", "suggestion": "Rename functions using camelCase"})
    return {"compliant": not violations, "violations": violations, "conventions_checked": 4, "file_path": file_path}


@router.delete("/api/v1/analyses/{analysis_id}")
async def delete_analysis(analysis_id: str) -> dict[str, Any]:
    if analysis_id not in ANALYSES:
        raise HTTPException(status_code=404, detail="analysis not found")
    ANALYSES.pop(analysis_id)
    return {"deleted": True, "analysis_id": analysis_id}


@router.get("/api/v1/languages")
async def languages() -> dict[str, Any]:
    return {"supported_languages": SUPPORTED_LANGUAGES, "count": len(SUPPORTED_LANGUAGES)}
