"""SDK client placeholder for framework-doc-indexer."""

from dataclasses import dataclass


@dataclass
class System94Client:
    base_url: str

    def health_url(self) -> str:
        return f"{self.base_url}/health"
