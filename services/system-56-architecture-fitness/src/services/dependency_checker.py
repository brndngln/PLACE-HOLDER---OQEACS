from __future__ import annotations

import re

import networkx as nx

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
        graph = nx.DiGraph()
        for src, deps in imports_map.items():
            for dep in deps:
                graph.add_edge(src, dep)
        cycles = []
        for cycle in nx.simple_cycles(graph):
            if len(cycle) > 1:
                cycles.append(CircularDependency(cycle=cycle))
        return cycles
