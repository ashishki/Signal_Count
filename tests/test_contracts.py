import pytest
from pydantic import ValidationError

from app.schemas.contracts import FinalMemo, SpecialistResponse, ThesisRequest


def test_thesis_request_schema_validation() -> None:
    valid = ThesisRequest.model_validate(
        {
            "thesis": "NVDA outperforms SPY over the next 30 days",
            "asset": "NVDA",
            "horizon_days": 30,
        }
    )

    assert valid.thesis.startswith("NVDA")
    assert valid.asset == "NVDA"
    assert valid.horizon_days == 30

    with pytest.raises(ValidationError):
        ThesisRequest.model_validate({"asset": "NVDA", "horizon_days": 30})

    with pytest.raises(ValidationError):
        ThesisRequest.model_validate({"thesis": "x", "horizon_days": 30})

    with pytest.raises(ValidationError):
        ThesisRequest.model_validate({"thesis": "x", "asset": "NVDA"})


def test_specialist_response_schema_requires_provenance_fields() -> None:
    valid = SpecialistResponse.model_validate(
        {
            "job_id": "job-123",
            "node_role": "risk",
            "peer_id": "peer-risk-1",
            "summary": "Downside is underpriced.",
            "scenario_view": {"bull": 0.2, "base": 0.5, "bear": 0.3},
            "signals": ["valuation rich"],
            "risks": ["earnings miss"],
            "confidence": 0.64,
            "citations": ["headline-1"],
            "timestamp": "2026-04-17T12:00:00Z",
        }
    )

    assert valid.job_id == "job-123"
    assert valid.peer_id == "peer-risk-1"
    assert valid.scenario_view.base == 0.5

    for missing_field in ("job_id", "node_role", "peer_id", "summary", "scenario_view"):
        payload = {
            "job_id": "job-123",
            "node_role": "risk",
            "peer_id": "peer-risk-1",
            "summary": "Downside is underpriced.",
            "scenario_view": {"bull": 0.2, "base": 0.5, "bear": 0.3},
            "signals": [],
            "risks": [],
            "confidence": 0.64,
            "citations": [],
            "timestamp": "2026-04-17T12:00:00Z",
        }
        payload.pop(missing_field)

        with pytest.raises(ValidationError):
            SpecialistResponse.model_validate(payload)


def test_final_memo_schema_contains_required_sections() -> None:
    memo = FinalMemo.model_validate(
        {
            "job_id": "job-123",
            "normalized_thesis": "Will NVDA outperform SPY over 30 days?",
            "scenarios": {"bull": 0.3, "base": 0.45, "bear": 0.25},
            "supporting_evidence": ["earnings momentum"],
            "opposing_evidence": ["valuation stretched"],
            "catalysts": ["earnings beat", "AI demand"],
            "risks": ["multiple compression"],
            "invalidation_triggers": ["guidance miss"],
            "confidence_rationale": "Specialists agree on direction but not magnitude.",
            "provenance": [
                {
                    "node_role": "regime",
                    "peer_id": "peer-regime-1",
                    "timestamp": "2026-04-17T12:00:00Z",
                }
            ],
            "partial": False,
            "partial_reason": None,
        }
    )

    assert memo.normalized_thesis.endswith("30 days?")
    assert memo.scenarios.bull == 0.3
    assert memo.supporting_evidence == ["earnings momentum"]
    assert memo.opposing_evidence == ["valuation stretched"]
    assert memo.catalysts == ["earnings beat", "AI demand"]
    assert memo.risks == ["multiple compression"]
    assert memo.invalidation_triggers == ["guidance miss"]
    assert memo.confidence_rationale.startswith("Specialists agree")
    assert memo.provenance[0].node_role == "regime"
