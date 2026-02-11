"""Impact analysis service for semantic code changes."""

from __future__ import annotations

from collections import deque

from src.models import (
    AffectedEntity,
    BreakingChange,
    CodeEntity,
    EntityType,
    ImpactReport,
    SuggestedTest,
)


class ImpactAnalyzer:
    """Analyzes blast radius and risk for proposed code changes."""

    def __init__(self, graph_store: dict[str, object]) -> None:
        self._graph_store = graph_store

    def analyze_impact(
        self,
        *,
        repo_id: str,
        file_path: str,
        function_name: str,
        change_description: str,
    ) -> ImpactReport:
        graph = self._graph_store.get(repo_id)
        if graph is None:
            return ImpactReport(analysis_summary="Graph not found")

        target = self._find_target_entity(graph.entities, file_path, function_name)
        if target is None:
            return ImpactReport(analysis_summary="Target entity not found")

        dependents = self._find_dependents(graph.entities, graph.relationships, target.id)
        breaking = self._identify_breaking_changes(target, dependents, change_description)
        suggested = self._suggest_tests(target, dependents)
        risk = self._calculate_risk_score(dependents, breaking)

        summary = (
            f"Change to {target.name} affects {len(dependents)} entities; "
            f"{len(breaking)} potential breaking changes detected."
        )

        return ImpactReport(
            affected_entities=dependents,
            risk_score=risk,
            breaking_changes=breaking,
            suggested_tests=suggested,
            analysis_summary=summary,
            total_affected=len(dependents),
            max_depth=max((e.distance for e in dependents), default=0),
        )

    def get_dependents(self, repo_id: str, entity_id: str) -> list[AffectedEntity]:
        graph = self._graph_store.get(repo_id)
        if graph is None:
            return []
        return self._find_dependents(graph.entities, graph.relationships, entity_id)

    @staticmethod
    def _find_target_entity(
        entities: list[CodeEntity], file_path: str, function_name: str
    ) -> CodeEntity | None:
        normalized = file_path.replace("\\", "/")
        for entity in entities:
            if entity.name == function_name and entity.file_path.replace("\\", "/").endswith(normalized):
                return entity
        for entity in entities:
            if entity.name == function_name:
                return entity
        return None

    @staticmethod
    def _find_dependents(entities: list[CodeEntity], relationships: list, entity_id: str) -> list[AffectedEntity]:
        entity_map = {e.id: e for e in entities}
        reverse_edges: dict[str, list[str]] = {}
        for rel in relationships:
            reverse_edges.setdefault(rel.target_id, []).append(rel.source_id)
            reverse_edges.setdefault(rel.source_id, [])

        q: deque[tuple[str, int]] = deque([(entity_id, 0)])
        seen: set[str] = {entity_id}
        affected: list[AffectedEntity] = []

        while q:
            current, distance = q.popleft()
            for dep in reverse_edges.get(current, []):
                if dep in seen:
                    continue
                seen.add(dep)
                q.append((dep, distance + 1))
                ent = entity_map.get(dep)
                if ent is None:
                    continue
                impact_type = "direct" if distance == 0 else "transitive"
                affected.append(
                    AffectedEntity(
                        entity_id=ent.id,
                        name=ent.name,
                        entity_type=ent.entity_type,
                        file_path=ent.file_path,
                        distance=distance + 1,
                        impact_type=impact_type,
                    )
                )

        affected.sort(key=lambda x: (x.distance, x.name))
        return affected

    @staticmethod
    def _identify_breaking_changes(
        target: CodeEntity,
        affected: list[AffectedEntity],
        change_description: str,
    ) -> list[BreakingChange]:
        lower = change_description.lower()
        breaking_terms = ["rename", "remove", "delete", "signature", "return type", "behavior change"]
        is_breaking = any(term in lower for term in breaking_terms)

        breaks: list[BreakingChange] = []
        if not is_breaking:
            return breaks

        for ent in affected[:25]:
            severity = "high" if ent.distance == 1 else "medium"
            breaks.append(
                BreakingChange(
                    entity_id=ent.entity_id,
                    entity_name=ent.name,
                    file_path=ent.file_path,
                    reason=f"Dependent on changed symbol {target.name}",
                    severity=severity,
                    suggested_fix="Update caller to new signature/behavior and add regression test.",
                )
            )
        return breaks

    @staticmethod
    def _suggest_tests(target: CodeEntity, affected: list[AffectedEntity]) -> list[SuggestedTest]:
        tests: list[SuggestedTest] = []
        tests.append(
            SuggestedTest(
                test_name=f"test_{target.name}_behavior",
                test_file=f"tests/test_{target.name}.py",
                reason="Changed target function/class should be regression-tested.",
                exists=False,
                priority="high",
            )
        )
        for ent in affected[:10]:
            if ent.entity_type in (EntityType.FUNCTION, EntityType.CLASS):
                tests.append(
                    SuggestedTest(
                        test_name=f"test_{ent.name}_integration",
                        test_file=f"tests/test_{ent.name}_integration.py",
                        reason=f"Dependent {ent.name} may break due to upstream change.",
                        exists=False,
                        priority="high" if ent.distance == 1 else "medium",
                    )
                )
        return tests

    @staticmethod
    def _calculate_risk_score(affected: list[AffectedEntity], breaking: list[BreakingChange]) -> float:
        if not affected and not breaking:
            return 0.05
        direct = sum(1 for a in affected if a.distance == 1)
        transitive = sum(1 for a in affected if a.distance > 1)
        base = min(0.95, 0.1 + direct * 0.06 + transitive * 0.02)
        penalty = min(0.25, len(breaking) * 0.01)
        return max(0.0, min(1.0, round(base + penalty, 3)))
