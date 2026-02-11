"""SDK client placeholder for push-notifications."""

from dataclasses import dataclass


@dataclass
class System127Client:
    base_url: str

    def health_url(self) -> str:
        return f"{self.base_url}/health"
