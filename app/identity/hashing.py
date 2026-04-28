"""Ethereum-compatible Keccak hashing helpers."""

from __future__ import annotations

from typing import Any

from eth_utils import keccak

from app.identity.canonical import canonical_json_bytes


def keccak256(data: bytes) -> bytes:
    """Return Ethereum-compatible Keccak-256 bytes."""
    return keccak(data)


def keccak256_hex(data: bytes) -> str:
    """Return a 0x-prefixed Ethereum-compatible Keccak-256 digest."""
    return f"0x{keccak256(data).hex()}"


def canonical_json_hash(value: Any) -> str:
    """Hash canonical JSON for a transport-safe Python value."""
    return keccak256_hex(canonical_json_bytes(value))
