'''Pydantic models shared by API routes and service logic.'''
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class FlexiblePayload(BaseModel):
    '''Accept any JSON object while preserving type safety.'''

    model_config = ConfigDict(extra="allow")

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(exclude_none=True)


class HealthResponse(BaseModel):
    '''Health payload.'''

    status: str
    service: str
    version: str


class GenericResponse(BaseModel):
    '''Generic API response payload.'''

    operation: str
    ok: bool = True
    data: dict[str, Any] = Field(default_factory=dict)
