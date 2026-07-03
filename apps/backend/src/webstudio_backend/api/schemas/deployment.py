"""Office deployment wizard API schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field

from webstudio_backend.api.schemas.network import NetworkValidationCheckEntry


class IpStrategyRecommendationEntry(BaseModel):
    recommended: str
    label: str
    rationale: str
    alternative: str
    alternative_rationale: str


class OfficeDeploymentStatusResponse(BaseModel):
    completed: bool
    completed_at: str | None = None
    summary_available: bool
    summary: dict | None = None


class OfficeDeploymentDetectionResponse(BaseModel):
    generated_at: str
    overall_status: str
    checks: list[NetworkValidationCheckEntry] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    ip_strategy: IpStrategyRecommendationEntry | None = None
    server_lan_ip: str
    hostname: str
    data_root: str
    api_port: int


class OfficeDeploymentApplyResponse(BaseModel):
    saved_settings: dict[str, str] = Field(default_factory=dict)
    created_directories: list[str] = Field(default_factory=list)
    messages: list[str] = Field(default_factory=list)


class OfficeDeploymentCompleteResponse(BaseModel):
    detection: OfficeDeploymentDetectionResponse
    apply: OfficeDeploymentApplyResponse
    summary: dict
    completed: bool
    completed_at: str
