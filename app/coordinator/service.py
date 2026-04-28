"""Coordinator dispatch workflow for specialist fan-out."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from time import perf_counter
from typing import Any, Protocol

from app.axl.registry import AXLRegistry
from app.evaluation.reputation import build_reputation_updates
from app.integrations.market_data import MarketDataProvider
from app.integrations.news_feed import NewsFeedProvider
from app.observability.provenance import NodeExecutionRecord
from app.orchestration.executor import ExecutionPlan, GraphExecutor
from app.orchestration.graph import DEFAULT_WORKFLOW_GRAPH, WorkflowGraph
from app.orchestration.state import build_graph_state
from app.schemas.contracts import (
    SpecialistResponse,
    TaskSpec,
    ThesisRequest,
    VerificationAttestation,
)


class AXLTransport(Protocol):
    async def fetch_topology(self) -> dict[str, Any]: ...

    async def dispatch_specialist(
        self,
        peer_id: str,
        service_name: str,
        payload: dict[str, Any],
    ) -> SpecialistResponse: ...


class ResponseVerifier(Protocol):
    def verify_responses(
        self,
        *,
        task: TaskSpec,
        responses: list[SpecialistResponse],
    ) -> list[VerificationAttestation]: ...


@dataclass(frozen=True)
class CoordinatorDispatchResult:
    responses: list[SpecialistResponse]
    topology_snapshot: dict[str, Any]
    market_snapshot: dict[str, Any]
    news_headlines: list[str]
    rejected_responses: list[SpecialistResponse] = field(default_factory=list)
    verification_attestations: list[VerificationAttestation] = field(
        default_factory=list
    )
    run_metadata: dict[str, Any] = field(default_factory=dict)
    node_execution_records: list[NodeExecutionRecord] = field(default_factory=list)
    partial: bool = False
    missing_roles: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class RoleDispatchOutcome:
    response: SpecialistResponse | None
    execution_record: NodeExecutionRecord


class CoordinatorService:
    def __init__(
        self,
        axl_client: AXLTransport,
        registry: AXLRegistry,
        market_data_provider: MarketDataProvider,
        news_feed_provider: NewsFeedProvider,
        llm_client: Any,
        verifier: ResponseVerifier | None = None,
        workflow_graph: WorkflowGraph = DEFAULT_WORKFLOW_GRAPH,
    ) -> None:
        self._axl_client = axl_client
        self._registry = registry
        self._market_data_provider = market_data_provider
        self._news_feed_provider = news_feed_provider
        self._llm_client = llm_client
        self._verifier = verifier
        self._workflow_graph = workflow_graph
        self._graph_executor = GraphExecutor(workflow_graph)
        self._execution_plan = self._graph_executor.build_plan()

    async def dispatch(
        self,
        job_id: str,
        request: ThesisRequest,
    ) -> CoordinatorDispatchResult:
        topology_snapshot = await self._axl_client.fetch_topology()
        run_mode = str(topology_snapshot.get("mode", "live-axl"))
        market_snapshot = await self._market_data_provider.fetch_snapshot(request)
        news_headlines = await self._news_feed_provider.fetch_headlines(request)

        roles = self._execution_plan.specialist_roles
        results = await asyncio.gather(
            *[
                self._dispatch_role(
                    role=role,
                    job_id=job_id,
                    request=request,
                    market_snapshot=market_snapshot,
                    news_headlines=news_headlines,
                    run_mode=run_mode,
                )
                for role in roles
            ]
        )

        responses: list[SpecialistResponse] = []
        missing_roles: list[str] = []
        node_execution_records: list[NodeExecutionRecord] = []
        for role, result in zip(roles, results, strict=True):
            node_execution_records.append(result.execution_record)
            if result.response is None:
                missing_roles.append(role)
                continue
            responses.append(result.response)

        rejected_responses: list[SpecialistResponse] = []
        verification_attestations: list[VerificationAttestation] = []
        if self._verifier is not None:
            responses, rejected_responses, verification_attestations = (
                self._verify_responses(
                    job_id=job_id,
                    request=request,
                    responses=responses,
                )
            )

        return CoordinatorDispatchResult(
            responses=responses,
            rejected_responses=rejected_responses,
            verification_attestations=verification_attestations,
            topology_snapshot=topology_snapshot,
            market_snapshot=market_snapshot,
            news_headlines=news_headlines,
            run_metadata=self._build_run_metadata(
                run_mode=run_mode,
                records=node_execution_records,
                missing_roles=missing_roles,
                verification_attestations=verification_attestations,
                execution_plan=self._execution_plan,
                verifier_ran=(
                    self._verifier is not None
                    and self._execution_plan.verifier_node_id is not None
                ),
                synthesis_ran=self._execution_plan.synthesis_node_id is not None,
            ),
            node_execution_records=node_execution_records,
            partial=bool(missing_roles or rejected_responses),
            missing_roles=missing_roles,
        )

    def _verify_responses(
        self,
        *,
        job_id: str,
        request: ThesisRequest,
        responses: list[SpecialistResponse],
    ) -> tuple[
        list[SpecialistResponse],
        list[SpecialistResponse],
        list[VerificationAttestation],
    ]:
        if self._verifier is None:
            return responses, [], []

        task = TaskSpec(
            job_id=job_id,
            thesis=request.thesis,
            asset=request.asset,
            horizon_days=request.horizon_days,
        )
        attestations = self._verifier.verify_responses(
            task=task,
            responses=responses,
        )
        attestation_by_role = {
            attestation.node_role: attestation for attestation in attestations
        }
        accepted: list[SpecialistResponse] = []
        rejected: list[SpecialistResponse] = []
        for response in responses:
            attestation = attestation_by_role.get(response.node_role)
            if attestation is not None and attestation.status == "accepted":
                accepted.append(response)
            else:
                rejected.append(response)
        return accepted, rejected, attestations

    async def _dispatch_role(
        self,
        role: str,
        job_id: str,
        request: ThesisRequest,
        market_snapshot: dict[str, Any],
        news_headlines: list[str],
        run_mode: str,
    ) -> RoleDispatchOutcome:
        peer_service = self._registry.get_service_for_role(role)
        dispatch_target = f"/mcp/{peer_service.peer_id}/{peer_service.service_name}"
        transport = (
            "offline-preview" if run_mode == "offline-demo-preview" else "axl-mcp"
        )
        payload = self._build_payload(
            role=role,
            job_id=job_id,
            request=request,
            market_snapshot=market_snapshot,
            news_headlines=news_headlines,
        )
        started_at = perf_counter()

        try:
            response = await self._axl_client.dispatch_specialist(
                peer_id=peer_service.peer_id,
                service_name=peer_service.service_name,
                payload=payload,
            )
        except TimeoutError:
            return RoleDispatchOutcome(
                response=None,
                execution_record=NodeExecutionRecord(
                    node_role=role,
                    peer_id=peer_service.peer_id,
                    status="timed_out",
                    latency_ms=_elapsed_ms(started_at),
                    service_name=peer_service.service_name,
                    transport=transport,
                    dispatch_target=dispatch_target,
                ),
            )
        except Exception:
            return RoleDispatchOutcome(
                response=None,
                execution_record=NodeExecutionRecord(
                    node_role=role,
                    peer_id=peer_service.peer_id,
                    status="error",
                    latency_ms=_elapsed_ms(started_at),
                    service_name=peer_service.service_name,
                    transport=transport,
                    dispatch_target=dispatch_target,
                ),
            )

        return RoleDispatchOutcome(
            response=response,
            execution_record=NodeExecutionRecord(
                node_role=role,
                peer_id=peer_service.peer_id,
                status="completed",
                latency_ms=_elapsed_ms(started_at),
                service_name=peer_service.service_name,
                transport=transport,
                dispatch_target=dispatch_target,
            ),
        )

    def _build_payload(
        self,
        role: str,
        job_id: str,
        request: ThesisRequest,
        market_snapshot: dict[str, Any],
        news_headlines: list[str],
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "job_id": job_id,
            "role": role,
            "asset": request.asset,
            "horizon_days": request.horizon_days,
            "thesis": request.thesis,
        }

        if role == "regime":
            payload["snapshot"] = market_snapshot
        elif role == "narrative":
            payload["headlines"] = news_headlines

        return payload

    def _build_run_metadata(
        self,
        run_mode: str,
        records: list[NodeExecutionRecord],
        missing_roles: list[str],
        verification_attestations: list[VerificationAttestation],
        execution_plan: ExecutionPlan,
        verifier_ran: bool,
        synthesis_ran: bool,
    ) -> dict[str, Any]:
        completed_roles = [
            record.node_role for record in records if record.status == "completed"
        ]
        rejected_roles = [
            attestation.node_role
            for attestation in verification_attestations
            if attestation.status == "rejected"
        ]
        graph_state = build_graph_state(
            graph=self._workflow_graph,
            completed_roles=completed_roles,
            missing_roles=missing_roles,
            rejected_roles=rejected_roles,
            verifier_ran=verifier_ran,
            synthesis_ran=synthesis_ran,
        )
        metadata: dict[str, Any] = {
            "run_mode": run_mode,
            "expected_roles": [record.node_role for record in records],
            "completed_roles": completed_roles,
            "missing_roles": missing_roles,
            "rejected_roles": rejected_roles,
            "verification_attestations": [
                attestation.model_dump() for attestation in verification_attestations
            ],
            "reputation_updates": [
                update.to_dict()
                for update in build_reputation_updates(verification_attestations)
            ],
            "execution_plan": execution_plan.to_dict(),
            "workflow_graph": self._workflow_graph.to_dict(),
            "graph_state": graph_state.to_dict(),
            "dispatch_targets": [
                record.dispatch_target for record in records if record.dispatch_target
            ],
        }
        transport_metadata = getattr(self._axl_client, "run_metadata", None)
        if callable(transport_metadata):
            metadata.update(transport_metadata())
        return metadata


def _elapsed_ms(started_at: float) -> float:
    return round((perf_counter() - started_at) * 1000, 3)
