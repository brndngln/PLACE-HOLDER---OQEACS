from __future__ import annotations

import re

from src.models import CircularDependency, DependencyRule, Violation


class DependencyChecker:
    def check_dependencies(self, rules: list[DependencyRule], imports_map: dict[str, list[str]]) -> list[Violation]:
        violations: list[Violation] = []
        for src, imports in imports_map.items():
            for imp in imports:
                for rule in rules:
                    if re.search(rule.source_pattern, src) and re.search(rule.forbidden_pattern, imp):
                        violations.append(Violation(rule="dependency", file=src, message=f"Forbidden dependency on {imp}: {rule.reason}", severity="high"))
        return violations

    def detect_circular_dependencies(self, imports_map: dict[str, list[str]]) -> list[CircularDependency]:
        cycles: list[CircularDependency] = []
        seen: set[tuple[str, ...]] = set()
        path: list[str] = []
        in_path: set[str] = set()
        visited: set[str] = set()

        def normalize_cycle(cycle: list[str]) -> tuple[str, ...]:
            variants: list[tuple[str, ...]] = []
            for i in range(len(cycle)):
                rotated = tuple(cycle[i:] + cycle[:i])
                reversed_rotated = tuple(list(reversed(cycle[i:] + cycle[:i])))
                variants.append(rotated)
                variants.append(reversed_rotated)
            return min(variants)

        def dfs(node: str) -> None:
            visited.add(node)
            path.append(node)
            in_path.add(node)

            for dep in imports_map.get(node, []):
                if dep in in_path:
                    start = path.index(dep)
                    cycle_nodes = path[start:].copy()
                    if len(cycle_nodes) > 1:
                        signature = normalize_cycle(cycle_nodes)
                        if signature not in seen:
                            seen.add(signature)
                            cycles.append(CircularDependency(cycle=list(signature)))
                elif dep not in visited:
                    dfs(dep)

            in_path.remove(node)
            path.pop()

        for node in imports_map:
            if node not in visited:
                dfs(node)

        return cycles
