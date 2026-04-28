from app.rendering.memo import render_memo_html, render_memo_markdown
from app.schemas.contracts import (
    FinalMemo,
    MemoEvidenceSource,
    ProvenanceRecord,
    ScenarioView,
)


def test_markdown_renderer_uses_fixed_section_headings() -> None:
    rendered = render_memo_markdown(_memo())

    expected_headings = [
        "## Thesis",
        "## Scenarios",
        "## Supporting Evidence",
        "## Opposing Evidence",
        "## Catalysts",
        "## Risks",
        "## Invalidation Triggers",
        "## Confidence Rationale",
        "## Provenance",
    ]

    assert rendered.count("## ") == len(expected_headings)
    for heading in expected_headings:
        assert heading in rendered


def test_html_renderer_shows_partial_warning() -> None:
    rendered = render_memo_html(
        _memo(
            partial=True,
            partial_reason="Missing specialist roles: risk",
        )
    )

    assert 'class="memo-warning"' in rendered
    assert 'role="alert"' in rendered
    assert "Partial coverage warning." in rendered
    assert "Missing specialist roles: risk" in rendered


def test_memo_evidence_renders_source_hash() -> None:
    rendered = render_memo_html(
        _memo(
            evidence_sources=[
                MemoEvidenceSource(
                    text="Regime liquidity supports upside.",
                    source_role="regime",
                    peer_id="peer-regime-test",
                    output_hash=(
                        "0xabcdeabcdeabcdeabcdeabcdeabcdeabcdeabcdeabcdeabcdeabcdeabcdeabcde"
                    ),
                )
            ]
        )
    )

    assert 'data-source-role="regime"' in rendered
    assert (
        'data-output-hash="0xabcdeabcdeabcdeabcdeabcdeabcdeabcdeabcdeabcdeabcdeabcdeabcdeabcde"'
        in rendered
    )
    assert "source: regime / peer-regime-test / 0xabcdeabcd" in rendered


def _memo(
    *,
    partial: bool = False,
    partial_reason: str | None = None,
    evidence_sources: list[MemoEvidenceSource] | None = None,
) -> FinalMemo:
    return FinalMemo(
        job_id="job-render-1",
        normalized_thesis="Will ETH validate this thesis over 30 days: ETF flows improve?",
        scenarios=ScenarioView(bull=0.42, base=0.36, bear=0.22),
        supporting_evidence=[
            "Regime liquidity supports upside.",
            "ETF flow narrative remains constructive.",
        ],
        opposing_evidence=["A support break would invalidate the thesis."],
        catalysts=[
            "ETF flows remain constructive.",
            "Liquidity stays supportive.",
        ],
        risks=["Macro volatility can pressure beta assets."],
        invalidation_triggers=["ETH loses the recent support range."],
        confidence_rationale=(
            "Average specialist confidence is 0.70 with all specialist roles represented."
        ),
        provenance=[
            ProvenanceRecord(
                node_role="regime",
                peer_id="peer-regime-test",
                timestamp="2026-04-24T00:00:00Z",
            ),
            ProvenanceRecord(
                node_role="narrative",
                peer_id="peer-narrative-test",
                timestamp="2026-04-24T00:01:00Z",
            ),
        ],
        evidence_sources=evidence_sources or [],
        partial=partial,
        partial_reason=partial_reason,
    )
