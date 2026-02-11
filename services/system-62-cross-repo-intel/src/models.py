from __future__ import annotations

from pydantic import BaseModel, Field


class ServiceRelationship(BaseModel):
    provider: str
    consumer: str
    api_endpoint: str
    contract_schema: dict = Field(default_factory=dict)


class APIContract(BaseModel):
    service: str
    endpoint: str
    method: str
    request_schema: dict = Field(default_factory=dict)
    response_schema: dict = Field(default_factory=dict)
    version: str = "v1"


class ContractChange(BaseModel):
    service: str
    endpoint: str
    change_type: str
    breaking: bool
    description: str
    migration_steps: list[str] = Field(default_factory=list)


class ImpactMap(BaseModel):
    changed_service: str
    affected_services: list[str]
    total_consumers: int
    breaking_changes_count: int


class MigrationPlan(BaseModel):
    affected_service: str
    changes: list[ContractChange]
    generated_code: str
    estimated_effort: str


class ServiceGraph(BaseModel):
    nodes: list[str]
    edges: list[tuple[str, str]]
    total_services: int
    total_relationships: int
