"""Confirmed-block indexer scheduler with shallow reorg repair."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

from app.indexer.chain_events import ChainEventPoller, IndexedChainBlock


@dataclass(frozen=True)
class ChainIndexerCursor:
    name: str
    last_indexed_block: int
    last_safe_block: int
    status: str
    error: str | None = None


@dataclass(frozen=True)
class ChainIndexerRunResult:
    status: str
    latest_block: int | None
    safe_block: int | None
    from_block: int | None
    to_block: int | None
    events_indexed: int
    reorg_from_block: int | None = None
    error: str | None = None


class ChainIndexerScheduler:
    def __init__(
        self,
        *,
        store: object,
        poller: ChainEventPoller,
        cursor_name: str = "gensyn-testnet",
        start_block: int = 0,
        confirmations: int = 12,
        reorg_window: int = 24,
    ) -> None:
        if confirmations < 0:
            raise ValueError("confirmations must be non-negative")
        if reorg_window < 1:
            raise ValueError("reorg_window must be at least 1")
        self._store = store
        self._poller = poller
        self._cursor_name = cursor_name
        self._start_block = start_block
        self._confirmations = confirmations
        self._reorg_window = reorg_window

    async def run_once(self) -> ChainIndexerRunResult:
        cursor = await self._get_cursor()
        try:
            latest_block = self._poller.latest_block_number()
            safe_block = latest_block - self._confirmations
            if safe_block < self._start_block:
                await self._save_cursor(
                    last_indexed_block=cursor.last_indexed_block,
                    last_safe_block=safe_block,
                    status="up_to_date",
                    error=None,
                )
                return ChainIndexerRunResult(
                    status="up_to_date",
                    latest_block=latest_block,
                    safe_block=safe_block,
                    from_block=None,
                    to_block=None,
                    events_indexed=0,
                )

            normal_from = max(self._start_block, cursor.last_indexed_block + 1)
            repair_from = max(
                self._start_block,
                cursor.last_indexed_block - self._reorg_window + 1,
            )
            header_from = min(normal_from, repair_from)
            headers = self._poller.block_headers(
                from_block=header_from,
                to_block=safe_block,
            )
            reorg_from = await self._find_reorg_start(headers)
            if reorg_from is not None:
                await self._store.delete_indexed_chain_from_block(reorg_from)
                from_block = reorg_from
            else:
                from_block = normal_from

            await self._store.store_indexed_chain_blocks(headers)
            events = []
            if from_block <= safe_block:
                events = self._poller.poll(from_block=from_block, to_block=safe_block)
                await self._store.store_indexed_chain_events(events)

            await self._save_cursor(
                last_indexed_block=safe_block,
                last_safe_block=safe_block,
                status="ok",
                error=None,
            )
            return ChainIndexerRunResult(
                status="ok",
                latest_block=latest_block,
                safe_block=safe_block,
                from_block=from_block if from_block <= safe_block else None,
                to_block=safe_block if from_block <= safe_block else None,
                events_indexed=len(events),
                reorg_from_block=reorg_from,
            )
        except Exception as exc:
            await self._save_cursor(
                last_indexed_block=cursor.last_indexed_block,
                last_safe_block=cursor.last_safe_block,
                status="failed",
                error=str(exc),
            )
            return ChainIndexerRunResult(
                status="failed",
                latest_block=None,
                safe_block=None,
                from_block=None,
                to_block=None,
                events_indexed=0,
                error=str(exc),
            )

    async def run_forever(
        self,
        *,
        poll_interval_seconds: float = 30.0,
        stop_event: asyncio.Event | None = None,
    ) -> None:
        if poll_interval_seconds <= 0:
            raise ValueError("poll_interval_seconds must be positive")

        while stop_event is None or not stop_event.is_set():
            await self.run_once()
            if stop_event is None:
                await asyncio.sleep(poll_interval_seconds)
                continue
            try:
                await asyncio.wait_for(
                    stop_event.wait(),
                    timeout=poll_interval_seconds,
                )
            except TimeoutError:
                continue

    async def _get_cursor(self) -> ChainIndexerCursor:
        cursor = await self._store.get_indexer_cursor(self._cursor_name)
        if cursor is not None:
            return cursor
        return ChainIndexerCursor(
            name=self._cursor_name,
            last_indexed_block=self._start_block - 1,
            last_safe_block=self._start_block - 1,
            status="new",
        )

    async def _find_reorg_start(
        self,
        headers: list[IndexedChainBlock],
    ) -> int | None:
        if not headers:
            return None
        stored = await self._store.get_indexed_chain_block_hashes(
            headers[0].block_number,
            headers[-1].block_number,
        )
        for header in headers:
            previous_hash = stored.get(header.block_number)
            if previous_hash is not None and previous_hash != header.block_hash:
                return header.block_number
        return None

    async def _save_cursor(
        self,
        *,
        last_indexed_block: int,
        last_safe_block: int,
        status: str,
        error: str | None,
    ) -> None:
        await self._store.save_indexer_cursor(
            ChainIndexerCursor(
                name=self._cursor_name,
                last_indexed_block=last_indexed_block,
                last_safe_block=last_safe_block,
                status=status,
                error=error,
            )
        )
