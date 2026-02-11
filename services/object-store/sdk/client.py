import httpx
import structlog
from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_exponential

logger = structlog.get_logger()


class MinioClient:
    """SDK client for the Object-Store service (MinIO S3-compatible API)."""

    def __init__(
        self,
        base_url: str = "http://omni-minio:9000",
        api_token: str = "",
    ):
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

    # ── Public methods ──────────────────────────────────────────────

    def list_buckets(self) -> dict:
        """List all buckets in the object store."""
        logger.info("minio.list_buckets")
        return self._get("/minio/buckets")

    def create_bucket(self, name: str) -> dict:
        """Create a new bucket with the given name."""
        logger.info("minio.create_bucket", bucket=name)
        return self._post("/minio/buckets", data={"name": name})

    def list_objects(self, bucket: str, prefix: str | None = None) -> dict:
        """List objects in a bucket, optionally filtered by prefix."""
        logger.info("minio.list_objects", bucket=bucket, prefix=prefix)
        params: dict = {}
        if prefix is not None:
            params["prefix"] = prefix
        return self._get(f"/minio/buckets/{bucket}/objects", **params)

    def get_presigned_url(
        self, bucket: str, key: str, expires: int = 3600
    ) -> dict:
        """Generate a presigned URL for downloading an object."""
        logger.info(
            "minio.get_presigned_url",
            bucket=bucket,
            key=key,
            expires=expires,
        )
        return self._get(
            f"/minio/buckets/{bucket}/presigned", key=key, expires=expires
        )

    def bucket_stats(self, bucket: str) -> dict:
        """Get statistics (object count, total size) for a bucket."""
        logger.info("minio.bucket_stats", bucket=bucket)
        return self._get(f"/minio/buckets/{bucket}/stats")
