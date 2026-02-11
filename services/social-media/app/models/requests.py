from pydantic import BaseModel, Field

class ConnectAccountRequest(BaseModel):
    platform: str
    account_handle: str
    credentials: dict = Field(default_factory=dict)

class GenerateContentRequest(BaseModel):
    topic: str
    platforms: list[str]
    content_pillar: str = "educational"
    tone: str = "professional"
    include_hashtags: bool = True

class CreatePostRequest(BaseModel):
    text: str
    platform: str
    account_id: str
    media_urls: list[str] = Field(default_factory=list)
    format: str = "text"
    scheduled_at: str | None = None

class RepurposeRequest(BaseModel):
    source_post_id: str
    target_platforms: list[str]

class HashtagResearchRequest(BaseModel):
    topic: str
    platform: str
    count: int = Field(default=10, ge=1, le=50)
