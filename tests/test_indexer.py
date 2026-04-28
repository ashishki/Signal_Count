import asyncio
from pathlib import Path

from eth_abi import encode

from app.indexer.chain_events import (
    EVENT_DEFINITIONS,
    ChainEventPoller,
    event_topic,
)
from app.indexer.scheduler import ChainIndexerScheduler
from app.store import JobStore


class FakeRpcTransport:
    def __init__(self, logs: list[dict[str, object]]) -> None:
        self.logs = logs
        self.calls: list[tuple[str, list[object]]] = []

    def call(self, method: str, params: list[object]) -> object:
        self.calls.append((method, params))
        if method == "eth_getLogs":
            return self.logs
        raise AssertionError(f"unexpected rpc method: {method}")


def test_indexer_projects_receipt_events(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'jobs.db'}"
    transport = FakeRpcTransport(
        logs=[
            _log(
                "TaskCreated",
                [7, _bytes32("11"), "signal-count://jobs/job-123/task"],
                log_index=0,
            ),
            _log(
                "ContributionRecorded",
                [
                    7,
                    "0x00000000000000000000000000000000000000a1",
                    "risk",
                    _bytes32("22"),
                    _bytes32("33"),
                    "signal-count://jobs/job-123/contributions/risk",
                ],
                log_index=1,
            ),
            _log(
                "VerificationRecorded",
                [
                    7,
                    "0x00000000000000000000000000000000000000b1",
                    _bytes32("44"),
                    850_000,
                ],
                log_index=2,
            ),
            _log(
                "ReputationRecorded",
                [
                    7,
                    "0x00000000000000000000000000000000000000a1",
                    "risk",
                    850_000,
                    85_000_000,
                    1_000_000_000,
                    "signal-count://jobs/job-123/reputation/risk",
                ],
                log_index=3,
            ),
            _log(
                "TaskFinalized",
                [7, _bytes32("55")],
                log_index=4,
            ),
        ]
    )
    poller = ChainEventPoller(
        transport=transport,
        contract_addresses=["0x000000000000000000000000000000000000c001"],
    )

    events = poller.poll(from_block=100, to_block=105)

    assert [event.event_name for event in events] == [
        "TaskCreated",
        "ContributionRecorded",
        "VerificationRecorded",
        "ReputationRecorded",
        "TaskFinalized",
    ]
    store = JobStore(database_url=database_url)
    asyncio.run(store.store_indexed_chain_events([*events, events[1]]))

    restarted_store = JobStore(database_url=database_url)
    projection = asyncio.run(restarted_store.get_indexed_chain_projection())

    assert projection.tasks[7].finalized is True
    assert projection.tasks[7].task_hash == "0x" + "11" * 32
    assert projection.tasks[7].memo_hash == "0x" + "55" * 32
    assert len(projection.contributions) == 1
    assert projection.contributions[0].role == "risk"
    assert projection.contributions[0].ree_receipt_hash == "0x" + "33" * 32
    assert len(projection.verifications) == 1
    assert projection.verifications[0].score == 0.85
    assert projection.agent_leaderboard[0].to_dict() == {
        "agent_wallet": "0x00000000000000000000000000000000000000A1",
        "node_role": "risk",
        "reputation_points": 85.0,
        "recorded_contributions": 1,
        "total_verifier_score": 0.85,
        "native_test_payout_wei": 1_000_000_000,
        "source": "indexed_chain",
    }
    assert projection.to_dict()["tasks"][0]["source"] == "indexed_chain"
    assert transport.calls[0][1][0]["fromBlock"] == "0x64"


def test_scheduler_indexes_confirmed_blocks_and_updates_cursor(tmp_path: Path) -> None:
    store = JobStore(database_url=f"sqlite:///{tmp_path / 'jobs.db'}")
    transport = ScheduledRpcTransport(
        latest_block=112,
        block_hashes={100: _block_hash("aa"), 101: _block_hash("bb")},
        logs=[
            _log(
                "TaskCreated",
                [7, _bytes32("11"), "signal-count://jobs/job-123/task"],
                block_number=100,
                block_hash=_block_hash("aa"),
                log_index=0,
            )
        ],
    )
    scheduler = ChainIndexerScheduler(
        store=store,
        poller=ChainEventPoller(
            transport=transport,
            contract_addresses=["0x000000000000000000000000000000000000c001"],
        ),
        start_block=100,
        confirmations=11,
        reorg_window=2,
    )

    result = asyncio.run(scheduler.run_once())

    assert result.status == "ok"
    assert result.safe_block == 101
    assert result.from_block == 100
    assert result.events_indexed == 1
    cursor = asyncio.run(store.get_indexer_cursor("gensyn-testnet"))
    assert cursor is not None
    assert cursor.last_indexed_block == 101
    assert cursor.status == "ok"
    assert asyncio.run(store.get_indexed_chain_block_hashes(100, 101)) == {
        100: _block_hash("aa"),
        101: _block_hash("bb"),
    }


def test_scheduler_repairs_shallow_reorg(tmp_path: Path) -> None:
    store = JobStore(database_url=f"sqlite:///{tmp_path / 'jobs.db'}")
    first_transport = ScheduledRpcTransport(
        latest_block=111,
        block_hashes={100: _block_hash("aa")},
        logs=[
            _log(
                "TaskCreated",
                [7, _bytes32("11"), "signal-count://jobs/job-123/task"],
                block_number=100,
                block_hash=_block_hash("aa"),
                log_index=0,
                tx_index=1,
            )
        ],
    )
    scheduler = ChainIndexerScheduler(
        store=store,
        poller=ChainEventPoller(
            transport=first_transport,
            contract_addresses=["0x000000000000000000000000000000000000c001"],
        ),
        start_block=100,
        confirmations=11,
        reorg_window=4,
    )
    first_result = asyncio.run(scheduler.run_once())
    assert first_result.events_indexed == 1

    reorg_transport = ScheduledRpcTransport(
        latest_block=111,
        block_hashes={100: _block_hash("cc")},
        logs=[
            _log(
                "TaskCreated",
                [8, _bytes32("22"), "signal-count://jobs/job-456/task"],
                block_number=100,
                block_hash=_block_hash("cc"),
                log_index=0,
                tx_index=2,
            )
        ],
    )
    reorg_scheduler = ChainIndexerScheduler(
        store=store,
        poller=ChainEventPoller(
            transport=reorg_transport,
            contract_addresses=["0x000000000000000000000000000000000000c001"],
        ),
        start_block=100,
        confirmations=11,
        reorg_window=4,
    )

    result = asyncio.run(reorg_scheduler.run_once())
    projection = asyncio.run(store.get_indexed_chain_projection())

    assert result.reorg_from_block == 100
    assert list(projection.tasks) == [8]
    assert projection.tasks[8].task_hash == "0x" + "22" * 32


def test_scheduler_records_rpc_failure(tmp_path: Path) -> None:
    store = JobStore(database_url=f"sqlite:///{tmp_path / 'jobs.db'}")
    scheduler = ChainIndexerScheduler(
        store=store,
        poller=ChainEventPoller(
            transport=FailingRpcTransport(),
            contract_addresses=["0x000000000000000000000000000000000000c001"],
        ),
        start_block=100,
        confirmations=2,
        reorg_window=2,
    )

    result = asyncio.run(scheduler.run_once())
    cursor = asyncio.run(store.get_indexer_cursor("gensyn-testnet"))

    assert result.status == "failed"
    assert cursor is not None
    assert cursor.status == "failed"
    assert cursor.error == "rpc unavailable"


class ScheduledRpcTransport:
    def __init__(
        self,
        *,
        latest_block: int,
        block_hashes: dict[int, str],
        logs: list[dict[str, object]],
    ) -> None:
        self.latest_block = latest_block
        self.block_hashes = block_hashes
        self.logs = logs
        self.calls: list[tuple[str, list[object]]] = []

    def call(self, method: str, params: list[object]) -> object:
        self.calls.append((method, params))
        if method == "eth_blockNumber":
            return hex(self.latest_block)
        if method == "eth_getBlockByNumber":
            block_number = int(str(params[0]), 16)
            return {"hash": self.block_hashes[block_number]}
        if method == "eth_getLogs":
            request = params[0]
            assert isinstance(request, dict)
            from_block = int(str(request["fromBlock"]), 16)
            to_block = int(str(request["toBlock"]), 16)
            return [
                log
                for log in self.logs
                if from_block <= int(str(log["blockNumber"]), 16) <= to_block
            ]
        raise AssertionError(f"unexpected rpc method: {method}")


class FailingRpcTransport:
    def call(self, method: str, params: list[object]) -> object:
        del method, params
        raise RuntimeError("rpc unavailable")


def _log(
    event_name: str,
    values: list[object],
    *,
    block_number: int = 101,
    block_hash: str = "",
    log_index: int,
    tx_index: int | None = None,
) -> dict[str, object]:
    definition = next(
        definition for definition in EVENT_DEFINITIONS if definition.name == event_name
    )
    resolved_tx_index = tx_index if tx_index is not None else log_index + 1
    return {
        "address": "0x000000000000000000000000000000000000c001",
        "blockNumber": hex(block_number),
        "blockHash": block_hash,
        "transactionHash": f"0x{resolved_tx_index:064x}",
        "logIndex": hex(log_index),
        "topics": [event_topic(event_name)],
        "data": "0x" + encode(definition.arg_types, values).hex(),
    }


def _bytes32(fill: str) -> bytes:
    return bytes.fromhex(fill * 32)


def _block_hash(fill: str) -> str:
    return "0x" + fill * 32
