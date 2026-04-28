"""Markdown and HTML renderers for final memos."""

from __future__ import annotations

from html import escape

from app.schemas.contracts import FinalMemo

_DEFAULT_PARTIAL_REASON = (
    "One or more specialist responses were unavailable for this memo."
)


def render_memo_markdown(memo: FinalMemo) -> str:
    """Render a final memo with fixed markdown sections."""

    lines: list[str] = []
    if memo.partial:
        lines.extend(
            [
                "> Warning: Partial coverage.",
                f"> {memo.partial_reason or _DEFAULT_PARTIAL_REASON}",
                "",
            ]
        )

    lines.extend(
        [
            "## Thesis",
            memo.normalized_thesis,
            "",
            "## Scenarios",
            "| Scenario | Weight |",
            "| --- | ---: |",
            f"| Bull | {memo.scenarios.bull:.2f} |",
            f"| Base | {memo.scenarios.base:.2f} |",
            f"| Bear | {memo.scenarios.bear:.2f} |",
            "",
            "## Supporting Evidence",
            *_render_markdown_list(memo.supporting_evidence),
            "",
            "## Opposing Evidence",
            *_render_markdown_list(memo.opposing_evidence),
            "",
            "## Catalysts",
            *_render_markdown_list(memo.catalysts),
            "",
            "## Risks",
            *_render_markdown_list(memo.risks),
            "",
            "## Invalidation Triggers",
            *_render_markdown_list(memo.invalidation_triggers),
            "",
            "## Confidence Rationale",
            memo.confidence_rationale or "No confidence rationale provided.",
            "",
            "## Provenance",
            *_render_markdown_provenance(memo),
        ]
    )
    return "\n".join(lines)


def render_memo_html(memo: FinalMemo) -> str:
    """Render a final memo as simple semantic HTML."""

    warning_html = ""
    if memo.partial:
        warning_html = (
            '<div class="memo-warning" role="alert">'
            "<strong>Partial coverage warning.</strong>"
            f"<p>{escape(memo.partial_reason or _DEFAULT_PARTIAL_REASON)}</p>"
            "</div>"
        )

    return "\n".join(
        [
            '<article class="market-memo">',
            warning_html,
            "<section>",
            "<h2>Thesis</h2>",
            f"<p>{escape(memo.normalized_thesis)}</p>",
            "</section>",
            "<section>",
            "<h2>Scenarios</h2>",
            "<table>",
            "<thead><tr><th>Scenario</th><th>Weight</th></tr></thead>",
            "<tbody>",
            f"<tr><td>Bull</td><td>{memo.scenarios.bull:.2f}</td></tr>",
            f"<tr><td>Base</td><td>{memo.scenarios.base:.2f}</td></tr>",
            f"<tr><td>Bear</td><td>{memo.scenarios.bear:.2f}</td></tr>",
            "</tbody>",
            "</table>",
            "</section>",
            _render_html_section_with_sources(
                "Supporting Evidence",
                memo.supporting_evidence,
                memo,
            ),
            _render_html_section_with_sources(
                "Opposing Evidence",
                memo.opposing_evidence,
                memo,
            ),
            _render_html_section("Catalysts", memo.catalysts),
            _render_html_section("Risks", memo.risks),
            _render_html_section(
                "Invalidation Triggers",
                memo.invalidation_triggers,
            ),
            "<section>",
            "<h2>Confidence Rationale</h2>",
            f"<p>{escape(memo.confidence_rationale or 'No confidence rationale provided.')}</p>",
            "</section>",
            _render_html_section(
                "Provenance",
                [
                    (f"{record.node_role} via {record.peer_id} at {record.timestamp}")
                    for record in memo.provenance
                ],
            ),
            "</article>",
        ]
    )


def _render_markdown_list(items: list[str]) -> list[str]:
    if not items:
        return ["- None."]
    return [f"- {item}" for item in items]


def _render_markdown_provenance(memo: FinalMemo) -> list[str]:
    if not memo.provenance:
        return ["- None."]

    return [
        (f"- {record.node_role} via `{record.peer_id}` at `{record.timestamp}`")
        for record in memo.provenance
    ]


def _render_html_section(title: str, items: list[str]) -> str:
    return _render_html_section_with_sources(title, items, None)


def _render_html_section_with_sources(
    title: str,
    items: list[str],
    memo: FinalMemo | None,
) -> str:
    rendered_items = "".join(
        _render_evidence_item(item, memo) for item in (items or ["None."])
    )
    return f"<section><h2>{escape(title)}</h2><ul>{rendered_items}</ul></section>"


def _render_evidence_item(item: str, memo: FinalMemo | None) -> str:
    source = _find_source(item, memo) if memo is not None else None
    if source is None:
        return f"<li>{escape(item)}</li>"

    source_detail = " / ".join(
        value
        for value in (
            source.source_role,
            source.peer_id,
            _short_hash(source.output_hash),
        )
        if value
    )
    return (
        "<li "
        f'data-source-role="{escape(source.source_role)}" '
        f'data-output-hash="{escape(source.output_hash or "")}">'
        f"{escape(item)}"
        f' <span class="evidence-source">source: {escape(source_detail)}</span>'
        "</li>"
    )


def _find_source(item: str, memo: FinalMemo | None):
    if memo is None:
        return None
    return next(
        (source for source in memo.evidence_sources if source.text == item),
        None,
    )


def _short_hash(value: str | None) -> str:
    if not value:
        return ""
    return value[:12]
