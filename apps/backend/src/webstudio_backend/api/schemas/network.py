"""Network administration API schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class NetworkValidationCheckEntry(BaseModel):
    key: str
    name: str
    status: str
    message: str
    detail: str = ""


class NetworkValidationResponse(BaseModel):
    generated_at: str
    overall_status: str
    topology: str
    checks: list[NetworkValidationCheckEntry] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    validation_scope: str = "standard"


class InfrastructureChecklistEntry(BaseModel):
    id: str
    item: str
    owner: str


class NetworkReportResponse(BaseModel):
    generated_at: str
    overall_status: str
    topology: str
    checks: list[NetworkValidationCheckEntry] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    server_lan_ip: str
    mdns_enabled: bool
    mdns_active: bool
    discovery_candidates: list[str] = Field(default_factory=list)
    api_port: int
    data_root: str
    multi_ssid_guidance: str
    validation_scope: str = "standard"
    api_bind_host: str | None = None
    infrastructure_checklist: list[InfrastructureChecklistEntry] = Field(default_factory=list)
    firewall_script: str | None = None
    validation_script: str | None = None
