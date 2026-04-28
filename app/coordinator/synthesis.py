"""Final memo synthesis service."""

from __future__ import annotations

import json
from time import perf_counter
from typing import Any, Protocol

from pydantic import ValidationError

from app.coordinator.service import CoordinatorDispatchResult
from app.observability.metrics import get_metrics
from app.observability.tracing import get_tracer
from app.identity.hashing import canonical_json_hash
from app.schemas.contracts import (
    FinalMemo,
    MemoEvidenceSource,
    ProvenanceRecord,
    ScenarioView,
    SpecialistResponse,
    ThesisRequest,
)


class MemoLLMClient(Protocol):
    async def complete(self, model: str, messages: list[dict[str, str]]) -> str: ...


class MemoSynthesisService:
    """Combine specialist responses into a schema-valid final memo."""

    def __init__(
        self,
        llm_client: MemoLLMClient,
        model: str = "gpt-4o",
    ) -> None:
        self._llm_client = llm_client
        self._model = model

    async def synthesize(
        self,
        job_id: str,
        request: ThesisRequest,
        dispatch_result: CoordinatorDispatchResult,
    ) -> FinalMemo:
        metrics = get_metrics()
        counter = metrics.counter("memo_synthesis_requests_total")
        histogram = metrics.histogram("memo_synthesis_latency_ms")
        started_at = perf_counter()
        provenance = self._build_provenance(dispatch_result.responses)
        normalized_thesis = self._normalize_forecast_question(request)
        partial = dispatch_result.partial or bool(dispatch_result.rejected_responses)
        partial_reason = self._build_partial_reason(dispatch_result)

        try:
            llm_text = await self._call_llm(
                job_id=job_id,
                request=request,
                responses=dispatch_result.responses,
                normalized_thesis=normalized_thesis,
            )
            memo = self._parse_llm_memo(
                llm_text=llm_text,
                job_id=job_id,
                normalized_thesis=normalized_thesis,
                provenance=provenance,
                partial=partial,
                partial_reason=partial_reason,
                dispatch_result=dispatch_result,
            )
            counter.add(1.0, operation="memo.synthesize", outcome="success")
        except (ValidationError, ValueError, TypeError, RuntimeError):
            memo = self._fallback_memo(
                job_id=job_id,
                normalized_thesis=normalized_thesis,
                responses=dispatch_result.responses,
                provenance=provenance,
                partial=partial,
                partial_reason=partial_reason,
                dispatch_result=dispatch_result,
            )
            counter.add(1.0, operation="memo.synthesize", outcome="fallback")
        except Exception:
            counter.add(1.0, operation="memo.synthesize", outcome="error")
            raise
        finally:
            histogram.record(
                _elapsed_ms(started_at),
                operation="memo.synthesize",
            )

        return memo

    async def _call_llm(
        self,
        job_id: str,
        request: ThesisRequest,
        responses: list[SpecialistResponse],
        normalized_thesis: str,
    ) -> str:
        tracer = get_tracer()
        with tracer.span("memo_synthesis.llm"):
            return await self._llm_client.complete(
                model=self._model,
                messages=self._build_messages(
                    job_id=job_id,
                    request=request,
                    responses=responses,
                    normalized_thesis=normalized_thesis,
                ),
            )

    def _build_messages(
        self,
        job_id: str,
        request: ThesisRequest,
        responses: list[SpecialistResponse],
        normalized_thesis: str,
    ) -> list[dict[str, str]]:
        response_payload = [
            {
                "node_role": response.node_role,
                "summary": response.summary,
                "scenario_view": response.scenario_view.model_dump(),
                "signals": response.signals,
                "risks": response.risks,
                "confidence": response.confidence,
                "citations": response.citations,
            }
            for response in responses
        ]
        return [
            {
                "role": "system",
                "content": (
                    "You are the Signal Count final memo synthesizer. "
                    "Return compact JSON only that conforms to the FinalMemo "
                    "schema. Preserve material disagreement between specialists."
                ),
            },
            {
                "role": "user",
                "content": (
                    # Thesis text is model input for the synthesis task only; it
                    # is not copied into logs, span attributes, or metrics.
                    "Synthesize one final memo from these specialist outputs. "
                    "Use concise bullets for catalysts, risks, and invalidation "
                    "triggers. Return keys: job_id, normalized_thesis, scenarios, "
                    "supporting_evidence, opposing_evidence, catalysts, risks, "
                    "invalidation_triggers, confidence_rationale, provenance, "
                    "partial, partial_reason. The scenarios object must contain "
                    "bull, base, and bear numeric weights.\n"
                    f"job_id: {job_id}\n"
                    f"asset: {request.asset}\n"
                    f"horizon_days: {request.horizon_days}\n"
                    f"normalized_thesis: {normalized_thesis}\n"
                    "specialist_outputs:\n"
                    f"{json.dumps(response_payload, separators=(',', ':'))}"
                ),
            },
        ]

    def _parse_llm_memo(
        self,
        llm_text: str,
        job_id: str,
        normalized_thesis: str,
        provenance: list[ProvenanceRecord],
        partial: bool,
        partial_reason: str | None,
        dispatch_result: CoordinatorDispatchResult,
    ) -> FinalMemo:
        payload = self._load_json_object(llm_text)
        payload["job_id"] = job_id
        payload["normalized_thesis"] = normalized_thesis
        payload["provenance"] = [record.model_dump() for record in provenance]
        payload["verification_attestations"] = [
            attestation.model_dump()
            for attestation in dispatch_result.verification_attestations
        ]
        payload["evidence_sources"] = [
            source.model_dump()
            for source in self._evidence_sources(dispatch_result.responses)
        ]
        payload["opposing_evidence"] = self._compact_unique(
            [
                *payload.get("opposing_evidence", []),
                *self._rejected_evidence(dispatch_result),
            ]
        )
        payload["partial"] = partial
        payload["partial_reason"] = partial_reason
        return FinalMemo.model_validate(payload)

    def _load_json_object(self, llm_text: str) -> dict[str, Any]:
        json_text = llm_text.strip()
        if json_text.startswith("```"):
            json_text = json_text.split("\n", 1)[1].rsplit("```", 1)[0].strip()

        payload = json.loads(json_text)
        if not isinstance(payload, dict):
            raise ValueError("LLM memo response must be a JSON object")
        return payload

    def _fallback_memo(
        self,
        job_id: str,
        normalized_thesis: str,
        responses: list[SpecialistResponse],
        provenance: list[ProvenanceRecord],
        partial: bool,
        partial_reason: str | None,
        dispatch_result: CoordinatorDispatchResult,
    ) -> FinalMemo:
        return FinalMemo(
            job_id=job_id,
            normalized_thesis=normalized_thesis,
            scenarios=self._average_scenarios(responses),
            supporting_evidence=self._supporting_evidence(responses),
            opposing_evidence=self._compact_unique(
                [
                    *self._opposing_evidence(responses),
                    *self._rejected_evidence(dispatch_result),
                ]
            ),
            catalysts=self._compact_unique(
                signal for response in responses for signal in response.signals
            ),
            risks=self._compact_unique(
                risk for response in responses for risk in response.risks
            ),
            invalidation_triggers=[
                response.summary
                for response in responses
                if response.node_role == "risk"
            ],
            confidence_rationale=self._confidence_rationale(responses, partial),
            provenance=provenance,
            evidence_sources=self._evidence_sources(responses),
            verification_attestations=dispatch_result.verification_attestations,
            partial=partial,
            partial_reason=partial_reason,
        )

    def _build_provenance(
        self,
        responses: list[SpecialistResponse],
    ) -> list[ProvenanceRecord]:
        return [
            ProvenanceRecord(
                node_role=response.node_role,
                peer_id=response.peer_id,
                timestamp=response.timestamp,
            )
            for response in responses
        ]

    def _normalize_forecast_question(self, request: ThesisRequest) -> str:
        return (
            f"Will {request.asset} validate this thesis over "
            f"{request.horizon_days} days: {request.thesis}"
        )

    def _average_scenarios(self, responses: list[SpecialistResponse]) -> ScenarioView:
        if not responses:
            return ScenarioView(bull=0.0, base=0.0, bear=0.0)

        total = len(responses)
        return ScenarioView(
            bull=sum(response.scenario_view.bull for response in responses) / total,
            base=sum(response.scenario_view.base for response in responses) / total,
            bear=sum(response.scenario_view.bear for response in responses) / total,
        )

    def _compact_unique(self, values: Any) -> list[str]:
        compacted: list[str] = []
        seen: set[str] = set()
        for value in values:
            if not isinstance(value, str):
                continue
            item = value.strip()
            if not item or item in seen:
                continue
            seen.add(item)
            compacted.append(item)
        return compacted[:8]

    def _supporting_evidence(self, responses: list[SpecialistResponse]) -> list[str]:
        return self._compact_unique(
            signal
            for response in responses
            if response.node_role in {"regime", "narrative"}
            for signal in [response.summary, *response.signals]
        )

    def _opposing_evidence(self, responses: list[SpecialistResponse]) -> list[str]:
        return self._compact_unique(
            item
            for response in responses
            if response.node_role == "risk" or response.risks
            for item in [response.summary, *response.risks]
        )

    def _evidence_sources(
        self,
        responses: list[SpecialistResponse],
    ) -> list[MemoEvidenceSource]:
        sources: list[MemoEvidenceSource] = []
        for response in responses:
            output_hash = canonical_json_hash(response)
            for item in [response.summary, *response.signals, *response.risks]:
                if item.strip():
                    sources.append(
                        MemoEvidenceSource(
                            text=item,
                            source_role=response.node_role,
                            peer_id=response.peer_id,
                            output_hash=output_hash,
                        )
                    )
        return sources

    def _confidence_rationale(
        self,
        responses: list[SpecialistResponse],
        partial: bool,
    ) -> str:
        if not responses:
            return "No specialist responses were available, so confidence is minimal."
        average_confidence = sum(response.confidence for response in responses) / len(
            responses
        )
        coverage = "partial specialist coverage" if partial else "all specialist roles"
        return (
            f"Average specialist confidence is {average_confidence:.2f} with "
            f"{coverage} represented in the memo."
        )

    def _rejected_evidence(
        self,
        dispatch_result: CoordinatorDispatchResult,
    ) -> list[str]:
        attestation_by_role = {
            attestation.node_role: attestation
            for attestation in dispatch_result.verification_attestations
        }
        return [
            (
                f"Rejected {response.node_role} output from {response.peer_id}: "
                f"{response.summary} "
                f"(score={attestation_by_role[response.node_role].score:.2f}; "
                f"reasons={', '.join(attestation_by_role[response.node_role].reasons)})"
            )
            for response in dispatch_result.rejected_responses
            if response.node_role in attestation_by_role
        ]

    def _build_partial_reason(
        self,
        dispatch_result: CoordinatorDispatchResult,
    ) -> str | None:
        missing_roles = dispatch_result.missing_roles
        rejected_roles = [
            response.node_role for response in dispatch_result.rejected_responses
        ]
        if not missing_roles and not rejected_roles:
            return None
        reasons = []
        if missing_roles:
            reasons.append(f"Missing specialist roles: {', '.join(missing_roles)}")
        if rejected_roles:
            reasons.append(f"Rejected specialist roles: {', '.join(rejected_roles)}")
        return "; ".join(reasons)


def _elapsed_ms(started_at: float) -> float:
    return round((perf_counter() - started_at) * 1000, 3)
