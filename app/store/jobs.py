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

from app.observability.tracing import get_tracer
from app.schemas.contracts import FinalMemo, ThesisRequest

_ReturnT = TypeVar("_ReturnT")


def text(statement: str) -> str:
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
