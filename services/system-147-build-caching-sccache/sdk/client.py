import httpx


class Client:
    def __init__(self, base_url: str = "http://localhost:10147"):
        self.base_url = base_url.rstrip("/")

    async def health(self) -> dict:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{self.base_url}/health")
            response.raise_for_status()
            return response.json()

    async def info(self) -> dict:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{self.base_url}/info")
            response.raise_for_status()
            return response.json()
