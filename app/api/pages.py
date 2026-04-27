from __future__ import annotations

from html import escape
from pathlib import Path
from string import Template
from urllib.parse import parse_qs

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import ValidationError

from app.api.jobs import create_completed_job_submission
from app.demo.fixtures import DemoFixture, get_demo_fixture, list_demo_fixtures
from app.rendering.memo import render_memo_html
from app.schemas.contracts import FinalMemo, ThesisRequest
from app.store import JobRecord, JobStore


router = APIRouter()
_TEMPLATE_PATH = Path(__file__).resolve().parent.parent / "templates" / "index.html"


def _get_job_store(request: Request) -> JobStore:
    return request.app.state.job_store  # type: ignore[no-any-return]


def _get_coordinator(request: Request):
    coordinator = getattr(request.app.state, "coordinator_service", None)
    if coordinator is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Coordinator service is not configured.",
        )
    return coordinator


def _get_memo_synthesizer(request: Request):
    synthesizer = getattr(request.app.state, "memo_synthesis_service", None)
    if synthesizer is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Memo synthesis service is not configured.",
        )
    return synthesizer


@router.get("/", response_class=HTMLResponse)
async def home_page(request: Request) -> HTMLResponse:
    store = _get_job_store(request)
    latest_job = await store.get_latest_job()
    template = Template(_TEMPLATE_PATH.read_text())
    html = template.safe_substitute(
        fixture_cards=_render_fixture_cards(),
        latest_job_panel=_render_latest_job_panel(latest_job),
    )
    return HTMLResponse(content=html)


@router.post("/demo/submit")
async def submit_demo_job(
    request: Request,
) -> RedirectResponse:
    form = await _parse_urlencoded_body(request)
    await create_completed_job_submission(
        payload=_build_thesis_request(form),
        store=_get_job_store(request),
        coordinator=_get_coordinator(request),
        synthesizer=_get_memo_synthesizer(request),
    )
    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/demo/replay/{fixture_id}")
async def replay_demo_fixture(
    fixture_id: str,
    request: Request,
) -> RedirectResponse:
    try:
        fixture = get_demo_fixture(fixture_id)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    await create_completed_job_submission(
        payload=_fixture_to_request(fixture),
        store=_get_job_store(request),
        coordinator=_get_coordinator(request),
        synthesizer=_get_memo_synthesizer(request),
    )
    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)


def _render_fixture_cards() -> str:
    cards: list[str] = []
    for fixture in list_demo_fixtures():
        cards.append(
            "\n".join(
                [
                    '<article class="fixture-card">',
                    f"<h3>{escape(fixture.title)}</h3>",
                    f"<p>{escape(fixture.thesis)}</p>",
                    '<dl class="fixture-meta">',
                    f"<div><dt>Asset</dt><dd>{escape(fixture.asset)}</dd></div>",
                    (
                        "<div><dt>Horizon</dt><dd>"
                        f"{fixture.horizon_days} days</dd></div>"
                    ),
                    "</dl>",
                    f'<form action="/demo/replay/{escape(fixture.fixture_id)}" method="post">',
                    '<button type="submit">Replay Fixture</button>',
                    "</form>",
                    "</article>",
                ]
            )
        )
    return "\n".join(cards)


def _render_latest_job_panel(latest_job: JobRecord | None) -> str:
    if latest_job is None or latest_job.memo is None:
        return (
            '<section class="job-panel empty">'
            "<h2>Latest Job</h2>"
            "<p>No completed jobs yet. Submit a thesis to generate the first memo.</p>"
            "</section>"
        )

    memo_html = render_memo_html(FinalMemo.model_validate(latest_job.memo))
    thesis = escape(str(latest_job.payload.get("thesis", "")))
    asset = escape(str(latest_job.payload.get("asset", "")))
    horizon_days = escape(str(latest_job.payload.get("horizon_days", "")))

    return "\n".join(
        [
            '<section class="job-panel">',
            "<h2>Latest Job</h2>",
            f'<p class="job-id">Job ID: <code>{escape(latest_job.job_id)}</code></p>',
            '<div class="job-request">',
            "<h3>Submitted Thesis</h3>",
            f"<p>{thesis}</p>",
            (
                '<p class="job-meta">'
                f"Asset: <strong>{asset}</strong> "
                f"· Horizon: <strong>{horizon_days} days</strong></p>"
            ),
            "</div>",
            '<div class="job-memo">',
            memo_html,
            "</div>",
            _render_run_metadata(latest_job.run_metadata),
            '<section class="node-participation">',
            "<h3>Run Evidence</h3>",
            '<table class="ledger-table">',
            (
                "<thead><tr><th>Role</th><th>Peer</th><th>Service</th>"
                "<th>Transport</th><th>Status</th><th>Latency (ms)</th>"
                "<th>Dispatch target</th></tr></thead>"
            ),
            f"<tbody>{_render_node_rows(latest_job.provenance_ledger)}</tbody>",
            "</table>",
            "</section>",
            _render_topology(latest_job.topology_snapshot),
            "</section>",
        ]
    )


def _render_run_metadata(run_metadata: dict[str, object]) -> str:
    if not run_metadata:
        return (
            '<section class="run-metadata">'
            "<h3>Run Metadata</h3>"
            "<p>No run metadata recorded.</p>"
            "</section>"
        )

    keys = (
        "run_mode",
        "transport",
        "axl_local_base_url",
        "axl_topology_path",
        "axl_mcp_router_url",
    )
    rows = "".join(
        (
            "<tr>"
            f"<th>{escape(key)}</th>"
            f"<td><code>{escape(str(run_metadata.get(key, '')))}</code></td>"
            "</tr>"
        )
        for key in keys
        if run_metadata.get(key)
    )
    dispatch_targets = run_metadata.get("dispatch_targets", [])
    if isinstance(dispatch_targets, list) and dispatch_targets:
        rows += (
            "<tr><th>dispatch_targets</th>"
            f"<td><code>{escape(', '.join(str(item) for item in dispatch_targets))}</code></td></tr>"
        )
    return (
        '<section class="run-metadata">'
        "<h3>Run Metadata</h3>"
        '<table class="ledger-table">'
        f"<tbody>{rows}</tbody>"
        "</table>"
        "</section>"
    )


def _render_node_rows(provenance_ledger: list[dict[str, object]]) -> str:
    if not provenance_ledger:
        return (
            '<tr><td colspan="4">No node participation recorded for this job.</td></tr>'
        )

    rows: list[str] = []
    for record in provenance_ledger:
        rows.append(
            (
                "<tr>"
                f"<td>{escape(str(record.get('node_role', '')))}</td>"
                f"<td>{escape(str(record.get('peer_id', '')))}</td>"
                f"<td>{escape(str(record.get('service_name', '')))}</td>"
                f"<td>{escape(str(record.get('transport', '')))}</td>"
                f"<td>{escape(str(record.get('status', '')))}</td>"
                f"<td>{escape(str(record.get('latency_ms', '')))}</td>"
                f"<td><code>{escape(str(record.get('dispatch_target', '')))}</code></td>"
                "</tr>"
            )
        )
    return "".join(rows)


def _render_topology(topology_snapshot: dict[str, object] | None) -> str:
    if topology_snapshot is None:
        return (
            '<section class="topology-panel"><h3>Topology Snapshot</h3>'
            "<p>No topology snapshot recorded.</p></section>"
        )

    peers_value = topology_snapshot.get("peers", [])
    peers = peers_value if isinstance(peers_value, list) else []
    peer_items = "".join(
        f"<li>{escape(str(peer))}</li>" for peer in peers if isinstance(peer, str)
    )
    local_peer = escape(
        str(
            topology_snapshot.get("local_peer_id")
            or topology_snapshot.get("our_public_key")
            or ""
        )
    )
    mode = escape(str(topology_snapshot.get("mode", "live-axl")))
    tree_value = topology_snapshot.get("tree", [])
    tree = tree_value if isinstance(tree_value, list) else []
    tree_items = "".join(
        f"<li><code>{escape(str(node.get('public_key', '')))}</code></li>"
        for node in tree
        if isinstance(node, dict)
    )
    return (
        '<section class="topology-panel">'
        "<h3>Topology Snapshot</h3>"
        f"<p>Mode: <code>{mode}</code></p>"
        f"<p>Local peer: <code>{local_peer}</code></p>"
        f"<ul>{peer_items}</ul>"
        f"<ul>{tree_items}</ul>"
        "</section>"
    )


async def _parse_urlencoded_body(request: Request) -> dict[str, str]:
    body = (await request.body()).decode("utf-8")
    parsed = parse_qs(body, keep_blank_values=True)
    return {key: values[0] if values else "" for key, values in parsed.items()}


def _build_thesis_request(form: dict[str, str]) -> ThesisRequest:
    try:
        return ThesisRequest.model_validate(
            {
                "thesis": form.get("thesis", ""),
                "asset": form.get("asset", ""),
                "horizon_days": form.get("horizon_days", ""),
            }
        )
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=exc.errors(),
        ) from exc


def _fixture_to_request(fixture: DemoFixture) -> ThesisRequest:
    return ThesisRequest(
        thesis=fixture.thesis,
        asset=fixture.asset,
        horizon_days=fixture.horizon_days,
    )
