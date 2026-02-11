from __future__ import annotations

import uuid

from src.models import PromptVersion


class PromptVersionManager:
    def __init__(self) -> None:
        self._versions: dict[str, PromptVersion] = {}

    def create_version(self, name: str, system_prompt: str, template: str) -> PromptVersion:
        same_name = [v for v in self._versions.values() if v.name == name]
        version_num = max([v.version for v in same_name], default=0) + 1
        item = PromptVersion(
            id=str(uuid.uuid4()),
            name=name,
            system_prompt=system_prompt,
            template=template,
            version=version_num,
            token_count=len(system_prompt.split()) + len(template.split()),
        )
        self._versions[item.id] = item
        return item

    def get_version(self, prompt_id: str) -> PromptVersion | None:
        return self._versions.get(prompt_id)

    def list_versions(self) -> list[PromptVersion]:
        return sorted(self._versions.values(), key=lambda x: (x.name, x.version))

    def rollback(self, name: str, target_version: int) -> PromptVersion | None:
        candidates = [v for v in self._versions.values() if v.name == name and v.version == target_version]
        return candidates[0] if candidates else None
