from __future__ import annotations

import ast
from pathlib import Path

SDK_REQUIREMENTS = {
    "omni-quantum-systems/system-45-email-service/sdk/client.py": ("ListmonkClient", {"send_transactional", "create_subscriber", "list_campaigns", "get_campaign_stats"}),
    "omni-quantum-systems/system-47-support-center/sdk/client.py": ("ChatwootClient", {"list_conversations", "get_conversation", "send_message", "assign_agent", "add_label", "create_contact", "search_contacts"}),
    "omni-quantum-systems/system-48-web-analytics/sdk/client.py": ("PlausibleClient", {"get_stats", "get_breakdown", "track_event", "list_sites"}),
    "omni-quantum-systems/system-50-feature-flags/sdk/client.py": ("UnleashClient", {"is_enabled", "get_variant", "list_flags", "get_flag_details"}),
    "omni-quantum-systems/system-51-error-tracking/sdk/client.py": ("GlitchTipClient", {"list_issues", "get_issue", "resolve_issue", "list_projects", "get_project_stats"}),
    "omni-quantum-systems/system-52-search-engine/sdk/client.py": ("MeilisearchClient", {"search", "index_document", "index_batch", "delete_document", "get_index_stats"}),
    "omni-quantum-systems/system-55-audit-logger/sdk/client.py": ("AuditClient", {"log", "log_batch", "query", "timeline", "actor_history", "summary", "export"}),
    "omni-quantum-systems/system-58-translation-management/sdk/client.py": ("TolgeeClient", {"list_projects", "get_translations", "create_key", "update_translation", "export_translations", "import_translations"}),
}


def function_names(class_node: ast.ClassDef) -> set[str]:
    return {n.name for n in class_node.body if isinstance(n, ast.FunctionDef)}


def has_retry_decorator(fn: ast.FunctionDef) -> bool:
    for decorator in fn.decorator_list:
        if isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Name) and decorator.func.id == "retry":
            return True
    return False


def validate_file(path: Path, class_name: str, required_methods: set[str]) -> list[str]:
    failures: list[str] = []
    content = path.read_text()
    tree = ast.parse(content)

    class_node = next((n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == class_name), None)
    if class_node is None:
        return [f"{path}: class {class_name} missing"]

    methods = function_names(class_node)
    missing = required_methods - methods
    if missing:
        failures.append(f"{path}: missing public methods {sorted(missing)}")

    if "_get" not in methods or "_post" not in methods:
        failures.append(f"{path}: internal _get/_post methods required")
    else:
        fn_map = {n.name: n for n in class_node.body if isinstance(n, ast.FunctionDef)}
        if not has_retry_decorator(fn_map["_get"]):
            failures.append(f"{path}: _get must use @retry")
        if not has_retry_decorator(fn_map["_post"]):
            failures.append(f"{path}: _post must use @retry")

    required_tokens = ("httpx", "structlog", "stop_after_attempt", "wait_exponential")
    for token in required_tokens:
        if token not in content:
            failures.append(f"{path}: missing token {token}")

    return failures


def main() -> int:
    failures: list[str] = []
    for file_path, (class_name, required_methods) in SDK_REQUIREMENTS.items():
        failures.extend(validate_file(Path(file_path), class_name, required_methods))

    if failures:
        print("SDK conformance failures:")
        print("\n".join(failures))
        return 1

    print("SDK conformance OK for all 8 systems (structure + retry semantics).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
