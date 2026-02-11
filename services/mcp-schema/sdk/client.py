import httpx
import structlog
from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_exponential

logger = structlog.get_logger()


class MCPSchemaClient:
    def __init__(self, base_url: str = "http://omni-mcp-schema:8328", api_token: str = ""):
        self._client = httpx.Client(
            base_url=base_url,
            headers={"Authorization": f"Bearer {api_token}"},
            timeout=30.0,
        )

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    def _get(self, path: str, **params) -> dict:
        r = self._client.get(path, params=params)
        r.raise_for_status()
        return r.json()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    def _post(self, path: str, data: dict) -> dict:
        r = self._client.post(path, json=data)
        r.raise_for_status()
        return r.json()

    def get_schema(self, database: str, table: str | None = None) -> dict:
        """Get the schema for a database, optionally scoped to a specific table."""
        params = {}
        if table is not None:
            params["table"] = table
        logger.info("getting_schema", database=database, table=table)
        return self._get(f"/api/v1/schemas/{database}", **params)

    def list_databases(self) -> dict:
        """List all available databases."""
        logger.info("listing_databases")
        return self._get("/api/v1/databases")

    def list_tables(self, database: str) -> dict:
        """List all tables in a given database."""
        logger.info("listing_tables", database=database)
        return self._get(f"/api/v1/databases/{database}/tables")

    def query_schema(self, query: str) -> dict:
        """Query the schema registry with a natural-language or structured query."""
        logger.info("querying_schema", query=query)
        return self._post("/api/v1/schemas/query", {"query": query})
