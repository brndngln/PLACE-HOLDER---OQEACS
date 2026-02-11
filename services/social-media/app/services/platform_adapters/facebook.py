from datetime import datetime, timezone


class FacebookAdapter:
    async def publish_post(self, post: dict) -> str:
        return f"facebook-{post.get('id', 'post')}"

    async def delete_post(self, platform_post_id: str) -> bool:
        return bool(platform_post_id)

    async def get_post_metrics(self, platform_post_id: str) -> dict:
        return {"platform_post_id": platform_post_id, "impressions": 1200, "likes": 84, "comments": 9, "shares": 12}

    async def get_account_metrics(self, account: dict) -> dict:
        return {"account_id": account.get("id"), "followers": account.get("follower_count", 0), "updated_at": datetime.now(timezone.utc).isoformat()}

    async def get_trending(self) -> list[dict]:
        return [{"topic": "agentic coding", "velocity": 0.92}, {"topic": "ai delivery", "velocity": 0.85}]

    async def get_interactions(self, since: datetime) -> list[dict]:
        return [{"id": "int-1", "since": since.isoformat(), "content": "Great post"}]

    async def reply_to(self, platform_post_id: str, text: str) -> str:
        return f"reply-{platform_post_id}"

    async def get_user_posts(self, handle: str, count: int) -> list[dict]:
        return [{"handle": handle, "text": f"sample {idx}", "engagement_rate": 0.04 + idx * 0.005} for idx in range(min(count, 20))]
