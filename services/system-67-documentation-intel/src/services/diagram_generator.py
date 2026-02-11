from __future__ import annotations

import re

from src.models import DiagramSpec


class DiagramGenerator:
    def generate_architecture(self, code_path: str) -> DiagramSpec:
        import pathlib

        text = pathlib.Path(code_path).read_text(errors="ignore") if pathlib.Path(code_path).exists() else ""
        return self.generate_architecture_from_code(text)

    def generate_architecture_from_code(self, code: str) -> DiagramSpec:
        imports = re.findall(r"from\s+([a-zA-Z0-9_\.]+)\s+import|import\s+([a-zA-Z0-9_\.]+)", code)
        modules = sorted({a or b for a, b in imports if a or b})[:12]
        lines = ["graph TD", "  Source[Source File]"]
        for mod in modules:
            node = mod.replace(".", "_")
            lines.append(f"  Source --> {node}[{mod}]")
        if not modules:
            lines.append("  Source --> Runtime[Runtime]")
        return DiagramSpec(type="mermaid", content="\n".join(lines))
