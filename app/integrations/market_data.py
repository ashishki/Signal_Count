"""Market data provider adapter."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.identity.hashing import canonical_json_hash
from app.schemas.contracts import ThesisRequest


class MarketDataProvider:
    async def fetch_snapshot(self, request: ThesisRequest) -> dict[str, Any]:
        horizon_scale = min(request.horizon_days, 90) / 90
        snapshot = {
            "asset": request.asset,
            "price_return": round(0.02 + (horizon_scale * 0.06), 3),
            "volatility": round(0.15 + (horizon_scale * 0.1), 3),
        }
        snapshot["source_metadata"] = _fixture_source_metadata(
            source_url=(
                f"fixture://signal-count/market-snapshot/v1/"
                f"{request.asset}?horizon_days={request.horizon_days}"
            ),
            payload=snapshot,
        )
        return snapshot


def _fixture_source_metadata(
    *,
    source_url: str,
    payload: dict[str, Any],
) -> dict[str, str]:
    return {
        "source_type": "fixture",
        "source_quality": "fixture source",
        "source_url": source_url,
        "retrieved_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "source_hash": canonical_json_hash(payload),
    }
