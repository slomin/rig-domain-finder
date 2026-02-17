from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


Status = Literal["available", "taken", "unknown", "invalid"]
Method = Literal["rdap", "dns", "rdap+dns"]


class ToolOptions(BaseModel):
    model_config = ConfigDict(extra="forbid")

    timeout_ms: int = Field(default=2500, ge=100, le=30000)
    max_concurrency: int = Field(default=20, ge=1, le=200)
    batch_size: int = Field(default=200, ge=1, le=1000)
    prefer_rdap: bool = True
    enable_dns_fallback: bool = True
    treat_unknown_as_available: bool = False
    bootstrap_cache_path: str = ".rig_cache/rdap_dns.json"
    bootstrap_ttl_seconds: int = Field(default=604800, ge=60)
    rdap_fallback_base: str | None = None
    deterministic_mode: bool = False
    deterministic_seed: int = Field(default=17, ge=0)


class CheckDomainsInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tlds: list[str] = Field(min_length=1, max_length=3)
    slds: list[str] = Field(min_length=1, max_length=5000)
    options: ToolOptions = Field(default_factory=ToolOptions)


class DNSProbeEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dns_nxdomain: bool | None = None
    dns_ns: bool | None = None
    dns_soa: bool | None = None


class DomainResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    domain: str
    status: Status
    confidence: float = Field(ge=0.0, le=1.0)
    method: Method

    rdap_server: str | None = None
    rdap_http: int | None = None

    dns_nxdomain: bool | None = None
    dns_ns: bool | None = None
    dns_soa: bool | None = None

    error: str | None = None


class CheckDomainsOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    checked_at: str
    results: list[DomainResult]
    suggested_best: str | None = None
