"""SDK client placeholder for video-forge."""

from dataclasses import dataclass


@dataclass
class System169Client:
    base_url: str

    def health_url(self) -> str:
        return f"{self.base_url}/health"
