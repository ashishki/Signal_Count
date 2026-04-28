"""Market data provider adapter."""

from __future__ import annotations

from typing import Any

from app.schemas.contracts import ThesisRequest


class MarketDataProvider:
    async def fetch_snapshot(self, request: ThesisRequest) -> dict[str, Any]:
        horizon_scale = min(request.horizon_days, 90) / 90
        return {
            "asset": request.asset,
            "price_return": round(0.02 + (horizon_scale * 0.06), 3),
            "volatility": round(0.15 + (horizon_scale * 0.1), 3),
        }
