from __future__ import annotations

import re
from pathlib import Path

from src.models import StyleProfile, StyleRule


class StyleAnalyzer:
    def analyze_repo(self, path: str) -> StyleProfile:
        repo = Path(path)
        py_files = [p for p in repo.rglob("*.py") if p.is_file()]
        naming = self._detect_naming(py_files)
        import_style = self._detect_import_style(py_files)
        error_pattern = self._detect_error_patterns(py_files)
        docstyle = self._detect_docstring_style(py_files)
        indent = self._detect_indentation(py_files)
        rules = [
            StyleRule(name="naming", pattern=naming, description="Project naming convention", auto_fix=True),
            StyleRule(name="imports", pattern=import_style, description="Import ordering/grouping", auto_fix=False),
            StyleRule(name="docstring", pattern=docstyle, description="Docstring convention", auto_fix=False),
        ]
        return StyleProfile(
            id=repo.name or "profile",
            repo_name=repo.name or "repo",
            naming_convention=naming,
            import_style=import_style,
            error_pattern=error_pattern,
            logging_pattern="structlog" if any("structlog" in f.read_text(errors="ignore") for f in py_files[:20]) else "logging",
            test_style="pytest",
            docstring_style=docstyle,
            type_hint_usage="strict" if any("->" in f.read_text(errors="ignore") for f in py_files[:20]) else "mixed",
            indent_style=indent,
            max_line_length=120,
            rules=rules,
        )

    def _detect_naming(self, files: list[Path]) -> str:
        snake = camel = pascal = 0
        for f in files[:200]:
            text = f.read_text(errors="ignore")
            snake += len(re.findall(r"\b[a-z]+(?:_[a-z0-9]+)+\b", text))
            camel += len(re.findall(r"\b[a-z]+(?:[A-Z][a-z0-9]+)+\b", text))
            pascal += len(re.findall(r"\b[A-Z][a-z0-9]+(?:[A-Z][a-z0-9]+)+\b", text))
        if snake >= camel and snake >= pascal:
            return "snake_case"
        if camel >= pascal:
            return "camelCase"
        return "PascalCase"

    def _detect_import_style(self, files: list[Path]) -> str:
        grouped = 0
        for f in files[:100]:
            lines = f.read_text(errors="ignore").splitlines()
            for i, line in enumerate(lines[:-1]):
                if line.startswith("import") and lines[i + 1].strip() == "":
                    grouped += 1
        return "grouped" if grouped > 3 else "inline"

    def _detect_error_patterns(self, files: list[Path]) -> str:
        broad = 0
        typed = 0
        for f in files[:200]:
            text = f.read_text(errors="ignore")
            broad += text.count("except Exception") + text.count("except:")
            typed += text.count("except ValueError") + text.count("except KeyError")
        return "typed_exceptions" if typed >= broad else "broad_exceptions"

    def _detect_docstring_style(self, files: list[Path]) -> str:
        triple_double = 0
        triple_single = 0
        for f in files[:200]:
            text = f.read_text(errors="ignore")
            triple_double += text.count('"""')
            triple_single += text.count("'''")
        return "triple_double" if triple_double >= triple_single else "triple_single"

    def _detect_indentation(self, files: list[Path]) -> str:
        tabs = spaces = 0
        for f in files[:100]:
            for line in f.read_text(errors="ignore").splitlines():
                if line.startswith("\t"):
                    tabs += 1
                elif line.startswith("    "):
                    spaces += 1
        return "spaces" if spaces >= tabs else "tabs"
