"""Reputation update and payout multiplier policy."""

from __future__ import annotations

REPUTATION_ALPHA: float = 0.3
INITIAL_REPUTATION: float = 0.7
SLASH_THRESHOLD: float = 0.4
FULL_PAYOUT_REPUTATION: float = 0.7
BONUS_REPUTATION: float = 1.0
MAX_MULTIPLIER: float = 1.6
THRESHOLD_MULTIPLIER: float = SLASH_THRESHOLD


def update_reputation(*, current: float, verifier_score: float) -> float:
    current_clamped = _clamp_unit(current)
    score_clamped = _clamp_unit(verifier_score)
    updated = (
        REPUTATION_ALPHA * score_clamped + (1.0 - REPUTATION_ALPHA) * current_clamped
    )
    return round(_clamp_unit(updated), 6)


def payout_multiplier(reputation: float) -> float:
    rep = _clamp_unit(reputation)
    if rep < SLASH_THRESHOLD:
        return 0.0
    if rep <= FULL_PAYOUT_REPUTATION:
        return _linear(
            x=rep,
            x0=SLASH_THRESHOLD,
            y0=THRESHOLD_MULTIPLIER,
            x1=FULL_PAYOUT_REPUTATION,
            y1=1.0,
        )
    return _linear(
        x=rep,
        x0=FULL_PAYOUT_REPUTATION,
        y0=1.0,
        x1=BONUS_REPUTATION,
        y1=MAX_MULTIPLIER,
    )


def payout_wei(*, reputation: float, base_wei: int) -> int:
    if base_wei < 0:
        raise ValueError("base_wei must be non-negative")
    multiplier = payout_multiplier(reputation)
    if multiplier == 0.0:
        return 0
    return int(base_wei * multiplier)


def _clamp_unit(value: float) -> float:
    if value < 0.0:
        return 0.0
    if value > 1.0:
        return 1.0
    return float(value)


def _linear(*, x: float, x0: float, y0: float, x1: float, y1: float) -> float:
    if x1 == x0:
        return y0
    return y0 + (y1 - y0) * (x - x0) / (x1 - x0)
