"""Explorer URL helpers for Gensyn Testnet evidence."""

from __future__ import annotations


def explorer_tx_url(tx_hash: str, base_url: str) -> str:
    return f"{base_url.rstrip('/')}/tx/{tx_hash}"


def explorer_address_url(address: str, base_url: str) -> str:
    return f"{base_url.rstrip('/')}/address/{address}"
