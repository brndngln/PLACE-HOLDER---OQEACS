"""SDK client placeholder for supply-chain-security-suite."""

from dataclasses import dataclass


@dataclass
class System75Client:
    base_url: str

    def health_url(self) -> str:
        return f"{self.base_url}/health"
