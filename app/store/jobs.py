"""SQLite-backed job persistence for thesis submissions."""

from __future__ import annotations

import asyncio
import json
import sqlite3
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import UTC, datetime
from os import getenv
from pathlib import Path
from threading import Lock
from typing import TypeVar
from uuid import uuid4

from app.evaluation.reputation import (
    ReputationLedgerEntry,
    build_reputation_leaderboard,
)
from app.indexer.chain_events import IndexedChainBlock, IndexedChainEvent
from app.indexer.projections import (
    ChainEventsProjection,
    build_chain_events_projection,
)
from app.indexer.scheduler import ChainIndexerCursor
from app.observability.tracing import get_tracer
from app.schemas.contracts import FinalMemo, ThesisRequest

_ReturnT = TypeVar("_ReturnT")


def text(statement: str) -> str:
    """Keep SQL statements explicit while using sqlite named parameters."""

    return statement


@dataclass(frozen=True)
class JobRecord:
    job_id: str
    status: str
    payload: dict[str, object]
    memo: dict[str, object] | None
    provenance_ledger: list[dict[str, object]]
    topology_snapshot: dict[str, object] | None
    run_metadata: dict[str, object]
    created_at: str

    def to_dict(self) -> dict[str, object]:
        return {
            "job_id": self.job_id,
            "status": self.status,
            "payload": self.payload,
            "memo": self.memo,
            "provenance_ledger": self.provenance_ledger,
            "topology_snapshot": self.topology_snapshot,
            "run_metadata": self.run_metadata,
            "created_at": self.created_at,
        }


class JobStore:
    def __init__(self, database_url: str | None = None) -> None:
        self._database_url = database_url or getenv(
            "DATABASE_URL",
            "sqlite:///./signal_count.db",
        )
        self._database_path = self._parse_database_path(self._database_url)
        self._tracer = get_tracer()
        self._initialized = False
        self._init_lock = Lock()

    async def initialize(self) -> None:
        if self._initialized:
            return

        await self._run_sync(self._initialize_once_sync)

    async def create_job(self, payload: ThesisRequest) -> JobRecord:
        await self.initialize()

        job = JobRecord(
            job_id=str(uuid4()),
            status="pending",
            payload=payload.model_dump(mode="json"),
            memo=None,
            provenance_ledger=[],
            topology_snapshot=None,
            run_metadata={},
            created_at=datetime.now(tz=UTC).isoformat(),
        )
        await self._run_sync(self._insert_job_sync, job)
        return job

    async def complete_job(
        self,
        job_id: str,
        memo: FinalMemo,
        provenance_ledger: list[dict[str, object]] | None = None,
        topology_snapshot: dict[str, object] | None = None,
        run_metadata: dict[str, object] | None = None,
    ) -> None:
        await self.initialize()
        await self._run_sync(
            self._complete_job_sync,
            job_id,
            memo.model_dump(mode="json"),
            provenance_ledger or [],
            topology_snapshot,
            run_metadata or {},
        )

    async def get_job(self, job_id: str) -> JobRecord | None:
        await self.initialize()
        return await self._run_sync(self._get_job_sync, job_id)

    async def get_latest_job(self) -> JobRecord | None:
        await self.initialize()
        return await self._run_sync(self._get_latest_job_sync)

    async def get_reputation_leaderboard(self) -> list[ReputationLedgerEntry]:
        await self.initialize()
        return await self._run_sync(self._get_reputation_leaderboard_sync)

    async def store_indexed_chain_events(
        self,
        events: list[IndexedChainEvent],
    ) -> None:
        await self.initialize()
        await self._run_sync(self._store_indexed_chain_events_sync, events)

    async def store_indexed_chain_blocks(
        self,
        blocks: list[IndexedChainBlock],
    ) -> None:
        await self.initialize()
        await self._run_sync(self._store_indexed_chain_blocks_sync, blocks)

    async def get_indexed_chain_block_hashes(
        self,
        from_block: int,
        to_block: int,
    ) -> dict[int, str]:
        await self.initialize()
        return await self._run_sync(
            self._get_indexed_chain_block_hashes_sync,
            from_block,
            to_block,
        )

    async def delete_indexed_chain_from_block(self, block_number: int) -> None:
        await self.initialize()
        await self._run_sync(self._delete_indexed_chain_from_block_sync, block_number)

    async def get_indexed_chain_projection(self) -> ChainEventsProjection:
        await self.initialize()
        return await self._run_sync(self._get_indexed_chain_projection_sync)

    async def get_indexer_cursor(self, name: str) -> ChainIndexerCursor | None:
        await self.initialize()
        return await self._run_sync(self._get_indexer_cursor_sync, name)

    async def save_indexer_cursor(self, cursor: ChainIndexerCursor) -> None:
        await self.initialize()
        await self._run_sync(self._save_indexer_cursor_sync, cursor)

    async def _run_sync(
        self,
        function: Callable[..., _ReturnT],
        *args: object,
    ) -> _ReturnT:
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(function, *args)
            while not future.done():
                await asyncio.sleep(0.001)
            return future.result()

    def _initialize_sync(self) -> None:
        with self._tracer.span("db.jobs.initialize"):
            self._database_path.parent.mkdir(parents=True, exist_ok=True)
            with self._connect() as connection:
                connection.execute(
                    text(
                        """
                        CREATE TABLE IF NOT EXISTS jobs (
                            job_id TEXT PRIMARY KEY,
                            status TEXT NOT NULL,
                            thesis_payload TEXT NOT NULL,
                            memo TEXT,
                            provenance_ledger TEXT NOT NULL DEFAULT '[]',
                            topology_snapshot TEXT,
                            run_metadata TEXT NOT NULL DEFAULT '{}',
                            created_at TEXT NOT NULL
                        )
                        """
                    )
                )
                connection.execute(
                    text(
                        """
                        CREATE TABLE IF NOT EXISTS indexed_chain_events (
                            event_id TEXT PRIMARY KEY,
                            event_name TEXT NOT NULL,
                            contract_address TEXT NOT NULL,
                            block_number INTEGER NOT NULL,
                            block_hash TEXT NOT NULL DEFAULT '',
                            transaction_hash TEXT NOT NULL,
                            log_index INTEGER NOT NULL,
                            args_json TEXT NOT NULL,
                            indexed_at TEXT NOT NULL
                        )
                        """
                    )
                )
                connection.execute(
                    text(
                        """
                        CREATE TABLE IF NOT EXISTS indexed_chain_blocks (
                            block_number INTEGER PRIMARY KEY,
                            block_hash TEXT NOT NULL,
                            indexed_at TEXT NOT NULL
                        )
                        """
                    )
                )
                connection.execute(
                    text(
                        """
                        CREATE TABLE IF NOT EXISTS indexer_cursors (
                            name TEXT PRIMARY KEY,
                            last_indexed_block INTEGER NOT NULL,
                            last_safe_block INTEGER NOT NULL,
                            status TEXT NOT NULL,
                            error TEXT,
                            updated_at TEXT NOT NULL
                        )
                        """
                    )
                )
                columns = {
                    row["name"]
                    for row in connection.execute(
                        text("PRAGMA table_info(jobs)")
                    ).fetchall()
                }
                if "provenance_ledger" not in columns:
                    connection.execute(
                        text(
                            """
                            ALTER TABLE jobs
                            ADD COLUMN provenance_ledger TEXT NOT NULL DEFAULT '[]'
                            """
                        )
                    )
                if "topology_snapshot" not in columns:
                    connection.execute(
                        text(
                            """
                            ALTER TABLE jobs
                            ADD COLUMN topology_snapshot TEXT
                            """
                        )
                    )
                if "run_metadata" not in columns:
                    connection.execute(
                        text(
                            """
                            ALTER TABLE jobs
                            ADD COLUMN run_metadata TEXT NOT NULL DEFAULT '{}'
                            """
                        )
                    )
                connection.commit()

                event_columns = {
                    row["name"]
                    for row in connection.execute(
                        text("PRAGMA table_info(indexed_chain_events)")
                    ).fetchall()
                }
                if "block_hash" not in event_columns:
                    connection.execute(
                        text(
                            """
                            ALTER TABLE indexed_chain_events
                            ADD COLUMN block_hash TEXT NOT NULL DEFAULT ''
                            """
                        )
                    )
                connection.commit()

    def _initialize_once_sync(self) -> None:
        with self._init_lock:
            if self._initialized:
                return
            self._initialize_sync()
            self._initialized = True

    def _insert_job_sync(self, job: JobRecord) -> None:
        with self._tracer.span("db.jobs.insert"):
            with self._connect() as connection:
                connection.execute(
                    text(
                        """
                        INSERT INTO jobs (
                            job_id,
                            status,
                            thesis_payload,
                            memo,
                            provenance_ledger,
                            topology_snapshot,
                            run_metadata,
                            created_at
                        ) VALUES (
                            :job_id,
                            :status,
                            :thesis_payload,
                            :memo,
                            :provenance_ledger,
                            :topology_snapshot,
                            :run_metadata,
                            :created_at
                        )
                        """
                    ),
                    {
                        "job_id": job.job_id,
                        "status": job.status,
                        "thesis_payload": json.dumps(job.payload),
                        "memo": None,
                        "provenance_ledger": json.dumps(job.provenance_ledger),
                        "topology_snapshot": (
                            json.dumps(job.topology_snapshot)
                            if job.topology_snapshot is not None
                            else None
                        ),
                        "run_metadata": json.dumps(job.run_metadata),
                        "created_at": job.created_at,
                    },
                )
                connection.commit()

    def _complete_job_sync(
        self,
        job_id: str,
        memo: dict[str, object],
        provenance_ledger: list[dict[str, object]],
        topology_snapshot: dict[str, object] | None,
        run_metadata: dict[str, object],
    ) -> None:
        with self._tracer.span("db.jobs.complete"):
            with self._connect() as connection:
                connection.execute(
                    text(
                        """
                        UPDATE jobs
                        SET status = :status,
                            memo = :memo,
                            provenance_ledger = :provenance_ledger,
                            topology_snapshot = :topology_snapshot,
                            run_metadata = :run_metadata
                        WHERE job_id = :job_id
                        """
                    ),
                    {
                        "job_id": job_id,
                        "status": "completed",
                        "memo": json.dumps(memo),
                        "provenance_ledger": json.dumps(provenance_ledger),
                        "topology_snapshot": (
                            json.dumps(topology_snapshot)
                            if topology_snapshot is not None
                            else None
                        ),
                        "run_metadata": json.dumps(run_metadata),
                    },
                )
                connection.commit()

    def _get_job_sync(self, job_id: str) -> JobRecord | None:
        with self._tracer.span("db.jobs.get"):
            with self._connect() as connection:
                row = connection.execute(
                    text(
                        """
                        SELECT
                            job_id,
                            status,
                            thesis_payload,
                            memo,
                            provenance_ledger,
                            topology_snapshot,
                            run_metadata,
                            created_at
                        FROM jobs
                        WHERE job_id = :job_id
                        """
                    ),
                    {"job_id": job_id},
                ).fetchone()

        if row is None:
            return None

        return self._row_to_job_record(row)

    def _get_latest_job_sync(self) -> JobRecord | None:
        with self._tracer.span("db.jobs.latest"):
            with self._connect() as connection:
                row = connection.execute(
                    text(
                        """
                        SELECT
                            job_id,
                            status,
                            thesis_payload,
                            memo,
                            provenance_ledger,
                            topology_snapshot,
                            run_metadata,
                            created_at
                        FROM jobs
                        ORDER BY datetime(created_at) DESC, rowid DESC
                        LIMIT 1
                        """
                    )
                ).fetchone()

        if row is None:
            return None

        return self._row_to_job_record(row)

    def _get_reputation_leaderboard_sync(self) -> list[ReputationLedgerEntry]:
        with self._tracer.span("db.jobs.reputation"):
            with self._connect() as connection:
                rows = connection.execute(
                    text(
                        """
                        SELECT run_metadata
                        FROM jobs
                        WHERE status = 'completed'
                        ORDER BY datetime(created_at) ASC, rowid ASC
                        """
                    )
                ).fetchall()

        updates: list[dict[str, object]] = []
        for row in rows:
            run_metadata = json.loads(str(row["run_metadata"]))
            raw_updates = run_metadata.get("reputation_updates", [])
            if isinstance(raw_updates, list):
                updates.extend(
                    update for update in raw_updates if isinstance(update, dict)
                )
        return build_reputation_leaderboard(updates)

    def _store_indexed_chain_events_sync(
        self,
        events: list[IndexedChainEvent],
    ) -> None:
        indexed_at = datetime.now(tz=UTC).isoformat()
        with self._tracer.span("db.indexed_chain_events.store"):
            with self._connect() as connection:
                connection.executemany(
                    text(
                        """
                        INSERT OR IGNORE INTO indexed_chain_events (
                            event_id,
                            event_name,
                            contract_address,
                            block_number,
                            block_hash,
                            transaction_hash,
                            log_index,
                            args_json,
                            indexed_at
                        ) VALUES (
                            :event_id,
                            :event_name,
                            :contract_address,
                            :block_number,
                            :block_hash,
                            :transaction_hash,
                            :log_index,
                            :args_json,
                            :indexed_at
                        )
                        """
                    ),
                    [
                        {
                            "event_id": event.event_id,
                            "event_name": event.event_name,
                            "contract_address": event.contract_address,
                            "block_number": event.block_number,
                            "block_hash": event.block_hash,
                            "transaction_hash": event.transaction_hash,
                            "log_index": event.log_index,
                            "args_json": json.dumps(event.args),
                            "indexed_at": indexed_at,
                        }
                        for event in events
                    ],
                )
                connection.commit()

    def _store_indexed_chain_blocks_sync(
        self,
        blocks: list[IndexedChainBlock],
    ) -> None:
        indexed_at = datetime.now(tz=UTC).isoformat()
        with self._tracer.span("db.indexed_chain_blocks.store"):
            with self._connect() as connection:
                connection.executemany(
                    text(
                        """
                        INSERT OR REPLACE INTO indexed_chain_blocks (
                            block_number,
                            block_hash,
                            indexed_at
                        ) VALUES (
                            :block_number,
                            :block_hash,
                            :indexed_at
                        )
                        """
                    ),
                    [
                        {
                            "block_number": block.block_number,
                            "block_hash": block.block_hash,
                            "indexed_at": indexed_at,
                        }
                        for block in blocks
                    ],
                )
                connection.commit()

    def _get_indexed_chain_block_hashes_sync(
        self,
        from_block: int,
        to_block: int,
    ) -> dict[int, str]:
        with self._tracer.span("db.indexed_chain_blocks.hashes"):
            with self._connect() as connection:
                rows = connection.execute(
                    text(
                        """
                        SELECT block_number, block_hash
                        FROM indexed_chain_blocks
                        WHERE block_number BETWEEN :from_block AND :to_block
                        """
                    ),
                    {"from_block": from_block, "to_block": to_block},
                ).fetchall()
        return {int(row["block_number"]): str(row["block_hash"]) for row in rows}

    def _delete_indexed_chain_from_block_sync(self, block_number: int) -> None:
        with self._tracer.span("db.indexed_chain_events.prune"):
            with self._connect() as connection:
                connection.execute(
                    text(
                        """
                        DELETE FROM indexed_chain_events
                        WHERE block_number >= :block_number
                        """
                    ),
                    {"block_number": block_number},
                )
                connection.execute(
                    text(
                        """
                        DELETE FROM indexed_chain_blocks
                        WHERE block_number >= :block_number
                        """
                    ),
                    {"block_number": block_number},
                )
                connection.commit()

    def _get_indexed_chain_projection_sync(self) -> ChainEventsProjection:
        with self._tracer.span("db.indexed_chain_events.project"):
            with self._connect() as connection:
                rows = connection.execute(
                    text(
                        """
                        SELECT
                            event_name,
                            contract_address,
                            block_number,
                            block_hash,
                            transaction_hash,
                            log_index,
                            args_json
                        FROM indexed_chain_events
                        ORDER BY block_number ASC, log_index ASC
                        """
                    )
                ).fetchall()

        events = [
            IndexedChainEvent(
                event_name=str(row["event_name"]),
                contract_address=str(row["contract_address"]),
                block_number=int(row["block_number"]),
                block_hash=str(row["block_hash"]),
                transaction_hash=str(row["transaction_hash"]),
                log_index=int(row["log_index"]),
                args=json.loads(str(row["args_json"])),
            )
            for row in rows
        ]
        return build_chain_events_projection(events)

    def _get_indexer_cursor_sync(self, name: str) -> ChainIndexerCursor | None:
        with self._tracer.span("db.indexer_cursors.get"):
            with self._connect() as connection:
                row = connection.execute(
                    text(
                        """
                        SELECT
                            name,
                            last_indexed_block,
                            last_safe_block,
                            status,
                            error
                        FROM indexer_cursors
                        WHERE name = :name
                        """
                    ),
                    {"name": name},
                ).fetchone()
        if row is None:
            return None
        return ChainIndexerCursor(
            name=str(row["name"]),
            last_indexed_block=int(row["last_indexed_block"]),
            last_safe_block=int(row["last_safe_block"]),
            status=str(row["status"]),
            error=str(row["error"]) if row["error"] is not None else None,
        )

    def _save_indexer_cursor_sync(self, cursor: ChainIndexerCursor) -> None:
        updated_at = datetime.now(tz=UTC).isoformat()
        with self._tracer.span("db.indexer_cursors.save"):
            with self._connect() as connection:
                connection.execute(
                    text(
                        """
                        INSERT INTO indexer_cursors (
                            name,
                            last_indexed_block,
                            last_safe_block,
                            status,
                            error,
                            updated_at
                        ) VALUES (
                            :name,
                            :last_indexed_block,
                            :last_safe_block,
                            :status,
                            :error,
                            :updated_at
                        )
                        ON CONFLICT(name) DO UPDATE SET
                            last_indexed_block = excluded.last_indexed_block,
                            last_safe_block = excluded.last_safe_block,
                            status = excluded.status,
                            error = excluded.error,
                            updated_at = excluded.updated_at
                        """
                    ),
                    {
                        "name": cursor.name,
                        "last_indexed_block": cursor.last_indexed_block,
                        "last_safe_block": cursor.last_safe_block,
                        "status": cursor.status,
                        "error": cursor.error,
                        "updated_at": updated_at,
                    },
                )
                connection.commit()

    def _row_to_job_record(self, row: sqlite3.Row) -> JobRecord:
        memo = json.loads(row["memo"]) if row["memo"] is not None else None
        topology_snapshot = (
            json.loads(row["topology_snapshot"])
            if row["topology_snapshot"] is not None
            else None
        )
        return JobRecord(
            job_id=str(row["job_id"]),
            status=str(row["status"]),
            payload=json.loads(str(row["thesis_payload"])),
            memo=memo,
            provenance_ledger=json.loads(str(row["provenance_ledger"])),
            topology_snapshot=topology_snapshot,
            run_metadata=json.loads(str(row["run_metadata"])),
            created_at=str(row["created_at"]),
        )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._database_path)
        connection.row_factory = sqlite3.Row
        return connection

    @staticmethod
    def _parse_database_path(database_url: str) -> Path:
        prefix = "sqlite:///"
        if not database_url.startswith(prefix):
            raise ValueError("Only sqlite:/// database URLs are supported.")

        raw_path = database_url.removeprefix(prefix)
        if not raw_path:
            raise ValueError("DATABASE_URL must include a SQLite path.")

        if raw_path == ":memory:":
            raise ValueError("Use a temporary SQLite file instead of :memory:.")

        return Path(raw_path).expanduser()
