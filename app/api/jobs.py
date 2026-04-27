from __future__ import annotations

from typing import Protocol

from fastapi import APIRouter, HTTPException, Request, status

from app.coordinator.service import CoordinatorDispatchResult
from app.observability.provenance import NodeExecutionRecord
from app.schemas.contracts import FinalMemo, ThesisRequest
from app.store import JobStore


router = APIRouter()


class Coordinator(Protocol):
    async def dispatch(
        self,
        job_id: str,
        request: ThesisRequest,
    ) -> CoordinatorDispatchResult: ...


class MemoSynthesizer(Protocol):
    async def synthesize(
        self,
        job_id: str,
        request: ThesisRequest,
        dispatch_result: CoordinatorDispatchResult,
    ) -> FinalMemo: ...


def _get_job_store(request: Request) -> JobStore:
    return request.app.state.job_store  # type: ignore[no-any-return]


def _get_coordinator(request: Request) -> Coordinator:
    coordinator = getattr(request.app.state, "coordinator_service", None)
    if coordinator is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Coordinator service is not configured.",
        )
    return coordinator  # type: ignore[no-any-return]


def _get_memo_synthesizer(request: Request) -> MemoSynthesizer:
    synthesizer = getattr(request.app.state, "memo_synthesis_service", None)
    if synthesizer is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Memo synthesis service is not configured.",
        )
    return synthesizer  # type: ignore[no-any-return]


async def create_completed_job_submission(
    *,
    payload: ThesisRequest,
    store: JobStore,
    coordinator: Coordinator,
    synthesizer: MemoSynthesizer,
) -> dict[str, object]:
    job = await store.create_job(payload)
    dispatch_result = await coordinator.dispatch(job_id=job.job_id, request=payload)
    memo = await synthesizer.synthesize(
        job_id=job.job_id,
        request=payload,
        dispatch_result=dispatch_result,
    )
    await store.complete_job(
        job_id=job.job_id,
        memo=memo,
        provenance_ledger=_build_provenance_ledger(
            dispatch_result.node_execution_records
        ),
        topology_snapshot=dispatch_result.topology_snapshot,
        run_metadata=dispatch_result.run_metadata,
    )
    stored_job = await store.get_job(job.job_id)
    if stored_job is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Job could not be persisted.",
        )
    return {"job_id": stored_job.job_id, "status": stored_job.status}


@router.post("/jobs", status_code=status.HTTP_201_CREATED)
async def create_job(payload: ThesisRequest, request: Request) -> dict[str, object]:
    store = _get_job_store(request)
    coordinator = _get_coordinator(request)
    synthesizer = _get_memo_synthesizer(request)
    return await create_completed_job_submission(
        payload=payload,
        store=store,
        coordinator=coordinator,
        synthesizer=synthesizer,
    )


@router.get("/jobs/{job_id}")
async def get_job(job_id: str, request: Request) -> dict[str, object]:
    store = _get_job_store(request)
    job = await store.get_job(job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Job not found."
        )
    return job.to_dict()


def _build_provenance_ledger(
    node_execution_records: list[NodeExecutionRecord],
) -> list[dict[str, object]]:
    return [record.to_dict() for record in node_execution_records]
