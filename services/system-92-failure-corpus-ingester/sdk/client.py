"""SDK client placeholder for failure-corpus-ingester."""

from dataclasses import dataclass


@dataclass
class System92Client:
    base_url: str

    def health_url(self) -> str:
        return f"{self.base_url}/health"
