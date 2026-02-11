"""SDK client placeholder for language-security-scanners."""

from dataclasses import dataclass


@dataclass
class System83Client:
    base_url: str

    def health_url(self) -> str:
        return f"{self.base_url}/health"
