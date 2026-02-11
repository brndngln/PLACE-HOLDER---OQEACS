from __future__ import annotations

from src.models import ComponentSpec, DesignTokens, GeneratedComponent
from src.services.accessibility_checker import AccessibilityChecker


class ComponentGenerator:
    def generate(self, spec: ComponentSpec, framework: str, tokens: DesignTokens) -> GeneratedComponent:
        props = ", ".join(spec.props) if spec.props else "props"
        if framework.lower() == "react":
            code = (
                f"export function {spec.name}({{ {props} }}) {{\n"
                f"  return (\n"
                f"    <section className=\"{spec.name.lower()}\">\n"
                f"      <h2>{spec.description}</h2>\n"
                f"      <button aria-label=\"{spec.name} action\">Action</button>\n"
                f"    </section>\n"
                f"  );\n"
                f"}}\n"
            )
        else:
            code = f"<!-- {spec.name} component for {framework} -->"

        css = (
            f".{spec.name.lower()} {{ padding: {tokens.spacing.get('md', '16px')}; "
            f"color: {tokens.colors.get('text', '#111')}; background: {tokens.colors.get('background', '#fff')}; }}"
        )
        report = AccessibilityChecker().check(code)
        return GeneratedComponent(code=code, framework=framework, a11y_score=report.score, responsive=True, css=css)
