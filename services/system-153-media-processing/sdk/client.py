"""SDK client placeholder for media-processing."""

from dataclasses import dataclass


@dataclass
class System153Client:
    base_url: str

    def health_url(self) -> str:
        return f"{self.base_url}/health"
