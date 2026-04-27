from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DemoFixture:
    fixture_id: str
    title: str
    thesis: str
    asset: str
    horizon_days: int

    def to_dict(self) -> dict[str, object]:
        return {
            "fixture_id": self.fixture_id,
            "title": self.title,
            "thesis": self.thesis,
            "asset": self.asset,
            "horizon_days": self.horizon_days,
        }


_FIXTURES = (
    DemoFixture(
        fixture_id="eth-etf-flow",
        title="ETH ETF Flow Case",
        thesis="ETH can rally on improving ETF flows and stable liquidity.",
        asset="ETH",
        horizon_days=30,
    ),
)


def list_demo_fixtures() -> list[DemoFixture]:
    return list(_FIXTURES)


def get_demo_fixture(fixture_id: str) -> DemoFixture:
    for fixture in _FIXTURES:
        if fixture.fixture_id == fixture_id:
            return fixture
    raise KeyError(f"Unknown demo fixture: {fixture_id}")
