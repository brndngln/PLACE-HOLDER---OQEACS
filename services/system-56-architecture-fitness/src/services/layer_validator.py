from __future__ import annotations

from src.models import LayerDefinition, Violation


class LayerValidator:
    def validate_layers(self, layers: list[LayerDefinition], imports_map: dict[str, list[str]]) -> list[Violation]:
        layer_index = {l.name: l for l in layers}
        violations: list[Violation] = []
        for src, deps in imports_map.items():
            src_layer = self._infer_layer(src)
            if src_layer not in layer_index:
                continue
            allowed = set(layer_index[src_layer].allowed_dependencies)
            for dep in deps:
                dep_layer = self._infer_layer(dep)
                if dep_layer and dep_layer != src_layer and dep_layer not in allowed:
                    violations.append(
                        Violation(
                            rule="layer",
                            file=src,
                            message=f"Layer {src_layer} cannot depend on {dep_layer}",
                            severity="medium",
                        )
                    )
        return violations

    @staticmethod
    def _infer_layer(path: str) -> str:
        p = path.replace("\\", "/").replace(".", "/").lower()
        parts = [segment for segment in p.split("/") if segment]
        for layer in ["controllers", "services", "repositories", "domain", "infra"]:
            if layer in parts:
                return layer
        return ""
