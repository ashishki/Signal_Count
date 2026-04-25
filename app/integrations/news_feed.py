from __future__ import annotations

from app.schemas.contracts import ThesisRequest


class NewsFeedProvider:
    async def fetch_headlines(self, request: ThesisRequest) -> list[str]:
        return [
            (
                f"{request.asset} remains in focus as operators reassess the next "
                f"{request.horizon_days}-day setup"
            ),
            (
                f"Signal Count demo context: {request.asset} thesis under review "
                "with bounded local inputs"
            ),
        ]
