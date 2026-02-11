from pydantic import BaseModel, Field

class CreateCampaignRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    campaign_type: str = "custom"
    channels: list[str] = Field(default_factory=list)
    description: str = ""

class GenerateAdCopyRequest(BaseModel):
    product_description: str = Field(min_length=1)
    target_audience: str = Field(min_length=1)
    tone: str = "professional"
    channel: str = "email"
    variant_count: int = Field(default=5, ge=1, le=10)

class CreateLeadRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    source: str = "other"
    first_name: str | None = None
    last_name: str | None = None
    company: str | None = None
    job_title: str | None = None
    industry: str | None = None
    company_size: int | None = None

class RecordActivityRequest(BaseModel):
    activity_type: str
    metadata: dict = Field(default_factory=dict)

class CreateAudienceRequest(BaseModel):
    name: str
    description: str = ""
    segment_rules: list[dict] = Field(default_factory=list)

class CreateSequenceRequest(BaseModel):
    campaign_id: str
    name: str
    trigger_event: str = "signup"

class CreateLandingPageRequest(BaseModel):
    title: str
    slug: str
    html_content: str
    campaign_id: str | None = None
    redirect_url: str | None = None

class CreateCompetitorRequest(BaseModel):
    name: str
    website: str | None = None
