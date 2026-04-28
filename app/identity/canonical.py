"""Deterministic JSON canonicalization for signed Signal Count artifacts."""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel


def canonical_json(value: Any) -> str:
    """Return stable compact JSON text for transport-safe data."""
    return json.dumps(
        _jsonable(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def canonical_json_bytes(value: Any) -> bytes:
    """Return UTF-8 bytes for stable hash/signature input."""
    return canonical_json(value).encode("utf-8")


def _jsonable(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    return value
