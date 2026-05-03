"""RPC adapters for chain analyst snapshots."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Protocol

from app.nodes.chain_analyst.events import ChainState


class RPCAdapter(Protocol):
    def fetch_chain_state(self, *, block_number: int | None = None) -> ChainState: ...


class FixtureRPC:
    def __init__(self, snapshot_path: str | Path):
        path = Path(snapshot_path)
        raw = json.loads(path.read_text())
        self._state = ChainState.from_dict(raw)

    def fetch_chain_state(self, *, block_number: int | None = None) -> ChainState:
        if block_number is None or block_number >= self._state.block_number:
            events = self._sorted(self._state.events)
            return ChainState(
                block_number=self._state.block_number,
                block_timestamp=self._state.block_timestamp,
                chain_id=self._state.chain_id,
                contract_addresses=self._state.contract_addresses,
                events=events,
            )

        cap = block_number
        filtered = tuple(e for e in self._state.events if e.block_number <= cap)
        return ChainState(
            block_number=cap,
            block_timestamp=self._block_timestamp_at(cap),
            chain_id=self._state.chain_id,
            contract_addresses=self._state.contract_addresses,
            events=self._sorted(filtered),
        )

    def _block_timestamp_at(self, block_number: int) -> int:
        delta_blocks = self._state.block_number - block_number
        return self._state.block_timestamp - 12 * delta_blocks

    @staticmethod
    def _sorted(events) -> tuple:
        return tuple(sorted(events, key=lambda e: (e.block_number, e.log_index)))


class JsonRpcClient:
    def __init__(self, *, rpc_url: str, contract_addresses: dict[str, str]):
        self._rpc_url = rpc_url
        self._contract_addresses = dict(contract_addresses)

    def fetch_chain_state(self, *, block_number: int | None = None) -> ChainState:
        raise NotImplementedError(
            "JsonRpcClient must be wired to an indexer-backed log decoder."
        )
