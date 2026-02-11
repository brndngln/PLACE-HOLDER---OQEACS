from __future__ import annotations

from pathlib import Path

from src.models import DependencyRule, FitnessResult, LayerDefinition
from src.services.dependency_checker import DependencyChecker
from src.services.layer_validator import LayerValidator


class FitnessEvaluator:
    def evaluate(self, rules: list[DependencyRule], codebase_path: str, layers: list[LayerDefinition]) -> FitnessResult:
        imports_map = self._collect_imports(Path(codebase_path))
        checker = DependencyChecker()
        layer_validator = LayerValidator()

        violations = []
        violations.extend(checker.check_dependencies(rules, imports_map))
        violations.extend(layer_validator.validate_layers(layers, imports_map))
        violations.extend(
            [
                v
                for c in checker.detect_circular_dependencies(imports_map)
                for v in [
                    type("Tmp", (), {"rule": "cycle", "file": c.cycle[0], "message": f"Circular dependency: {' -> '.join(c.cycle)}", "severity": "high"})()
                ]
            ]
        )
        # normalize temp objects
        normalized = []
        for v in violations:
            if hasattr(v, "dict"):
                normalized.append(v)
            else:
                from src.models import Violation

                normalized.append(Violation(rule=v.rule, file=v.file, message=v.message, severity=v.severity))

        score = max(0.0, round(100 - len(normalized) * 8, 2))
        return FitnessResult(score=score, violations=normalized)

    def _collect_imports(self, path: Path) -> dict[str, list[str]]:
        imports: dict[str, list[str]] = {}
        for f in path.rglob("*.py"):
            rel = str(f.relative_to(path))
            deps: list[str] = []
            text = f.read_text(errors="ignore")
            for line in text.splitlines():
                line = line.strip()
                if line.startswith("from "):
                    deps.append(line.split()[1])
                elif line.startswith("import "):
                    deps.extend(x.strip() for x in line.replace("import", "", 1).split(","))
            imports[rel] = deps
        return imports
