"""SDK client placeholder for database-migration-safety."""

from dataclasses import dataclass


@dataclass
class System122Client:
    base_url: str

    def health_url(self) -> str:
        return f"{self.base_url}/health"
