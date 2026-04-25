from __future__ import annotations

from pydantic import BaseModel, Field


class ThesisRequest(BaseModel):
    thesis: str = Field(min_length=1)
    asset: str = Field(min_length=1)
    horizon_days: int = Field(gt=0)


class ScenarioView(BaseModel):
    bull: float
    base: float
    bear: float


class ProvenanceRecord(BaseModel):
    node_role: str = Field(min_length=1)
    peer_id: str = Field(min_length=1)
    timestamp: str = Field(min_length=1)


class SpecialistResponse(BaseModel):
    job_id: str = Field(min_length=1)
    node_role: str = Field(min_length=1)
    peer_id: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    scenario_view: ScenarioView
    signals: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    citations: list[str] = Field(default_factory=list)
    timestamp: str = Field(min_length=1)


class FinalMemo(BaseModel):
    job_id: str = Field(min_length=1)
    normalized_thesis: str = Field(min_length=1)
    scenarios: ScenarioView
    supporting_evidence: list[str] = Field(default_factory=list)
    opposing_evidence: list[str] = Field(default_factory=list)
    catalysts: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    invalidation_triggers: list[str] = Field(default_factory=list)
    confidence_rationale: str = ""
    provenance: list[ProvenanceRecord] = Field(default_factory=list)
    partial: bool = False
    partial_reason: str | None = None
