"""News feed provider adapter."""

from __future__ import annotations

from datetime import UTC, datetime

from app.identity.hashing import canonical_json_hash
from app.schemas.contracts import ThesisRequest


class NewsFeedProvider:
    async def fetch_headlines(self, request: ThesisRequest) -> list[str]:
        return [
            (
                f"{request.asset} liquidity narrative improves while derivatives "
                "risk remains unresolved"
            ),
            (
                f"Signal Count fixture desk flags {request.asset} support break "
                "as the counter-thesis"
            ),
        ]

    async def fetch_source_metadata(
        self,
        request: ThesisRequest,
        headlines: list[str],
    ) -> list[dict[str, str]]:
        return [
            _fixture_source_metadata(
                source_url=(
                    f"fixture://signal-count/news-headline/v1/{request.asset}/{index}"
                ),
                payload={
                    "asset": request.asset,
                    "horizon_days": request.horizon_days,
                    "headline": headline,
                },
            )
            for index, headline in enumerate(headlines, start=1)
        ]


def _fixture_source_metadata(
    *,
    source_url: str,
    payload: dict[str, object],
) -> dict[str, str]:
    return {
        "source_type": "fixture",
        "source_quality": "fixture source",
        "source_url": source_url,
        "retrieved_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "source_hash": canonical_json_hash(payload),
    }
