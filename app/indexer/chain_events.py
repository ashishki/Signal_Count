"""Known Gensyn Testnet contract event decoding."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from eth_abi import decode
from eth_utils import keccak, to_checksum_address


@dataclass(frozen=True)
class EventDefinition:
    name: str
    signature: str
    arg_types: tuple[str, ...]
    arg_names: tuple[str, ...]

    @property
    def topic(self) -> str:
        return "0x" + keccak(text=self.signature).hex()


EVENT_DEFINITIONS: tuple[EventDefinition, ...] = (
    EventDefinition(
        name="TaskCreated",
        signature="TaskCreated(uint256,bytes32,string)",
        arg_types=("uint256", "bytes32", "string"),
        arg_names=("task_id", "task_hash", "metadata_uri"),
    ),
    EventDefinition(
        name="TaskFinalized",
        signature="TaskFinalized(uint256,bytes32)",
        arg_types=("uint256", "bytes32"),
        arg_names=("task_id", "memo_hash"),
    ),
    EventDefinition(
        name="ContributionRecorded",
        signature="ContributionRecorded(uint256,address,string,bytes32,bytes32,string)",
        arg_types=("uint256", "address", "string", "bytes32", "bytes32", "string"),
        arg_names=(
            "task_id",
            "agent",
            "role",
            "output_hash",
            "ree_receipt_hash",
            "metadata_uri",
        ),
    ),
    EventDefinition(
        name="VerificationRecorded",
        signature="VerificationRecorded(uint256,address,bytes32,uint256)",
        arg_types=("uint256", "address", "bytes32", "uint256"),
        arg_names=("task_id", "verifier", "verdict_hash", "score"),
    ),
    EventDefinition(
        name="ReputationRecorded",
        signature="ReputationRecorded(uint256,address,string,uint256,uint256,uint256,string)",
        arg_types=(
            "uint256",
            "address",
            "string",
            "uint256",
            "uint256",
            "uint256",
            "string",
        ),
        arg_names=(
            "task_id",
            "agent",
            "role",
            "score",
            "points",
            "native_test_payout_wei",
            "metadata_uri",
        ),
    ),
)

EVENTS_BY_TOPIC = {definition.topic: definition for definition in EVENT_DEFINITIONS}


@dataclass(frozen=True)
class IndexedChainEvent:
    event_name: str
    contract_address: str
    block_number: int
    block_hash: str
    transaction_hash: str
    log_index: int
    args: dict[str, object]

    @property
    def event_id(self) -> str:
        return f"{self.transaction_hash.lower()}:{self.log_index}"

    def to_dict(self) -> dict[str, object]:
        return {
            "event_id": self.event_id,
            "event_name": self.event_name,
            "contract_address": self.contract_address,
            "block_number": self.block_number,
            "block_hash": self.block_hash,
            "transaction_hash": self.transaction_hash,
            "log_index": self.log_index,
            "args": self.args,
            "source": "indexed_chain",
        }


@dataclass(frozen=True)
class IndexedChainBlock:
    block_number: int
    block_hash: str


class ChainEventPoller:
    def __init__(
        self,
        *,
        transport: object,
        contract_addresses: Sequence[str],
    ) -> None:
        self._transport = transport
        self._contract_addresses = [
            to_checksum_address(addr) for addr in contract_addresses
        ]

    def poll(
        self,
        *,
        from_block: int,
        to_block: int | str = "latest",
    ) -> list[IndexedChainEvent]:
        logs: list[dict[str, object]] = []
        for address in self._contract_addresses:
            result = self._transport.call(
                "eth_getLogs",
                [
                    {
                        "address": address,
                        "fromBlock": _block_tag(from_block),
                        "toBlock": _block_tag(to_block),
                        "topics": [
                            [definition.topic for definition in EVENT_DEFINITIONS]
                        ],
                    }
                ],
            )
            if isinstance(result, list):
                logs.extend(log for log in result if isinstance(log, dict))

        return decode_logs(logs)

    def latest_block_number(self) -> int:
        return _hex_to_int(self._transport.call("eth_blockNumber", []))

    def block_headers(
        self,
        *,
        from_block: int,
        to_block: int,
    ) -> list[IndexedChainBlock]:
        headers: list[IndexedChainBlock] = []
        for block_number in range(from_block, to_block + 1):
            result = self._transport.call(
                "eth_getBlockByNumber",
                [hex(block_number), False],
            )
            if not isinstance(result, dict):
                raise RuntimeError("Gensyn Testnet RPC returned invalid block header")
            block_hash = result.get("hash")
            if not isinstance(block_hash, str) or not block_hash.startswith("0x"):
                raise RuntimeError("Gensyn Testnet RPC returned invalid block hash")
            headers.append(
                IndexedChainBlock(block_number=block_number, block_hash=block_hash)
            )
        return headers


def decode_logs(logs: Iterable[dict[str, object]]) -> list[IndexedChainEvent]:
    events: list[IndexedChainEvent] = []
    for log in logs:
        decoded = decode_log(log)
        if decoded is not None:
            events.append(decoded)
    return sorted(events, key=lambda event: (event.block_number, event.log_index))


def decode_log(log: dict[str, object]) -> IndexedChainEvent | None:
    topics = log.get("topics")
    if not isinstance(topics, list) or not topics:
        return None
    topic = str(topics[0])
    definition = EVENTS_BY_TOPIC.get(topic)
    if definition is None:
        return None

    raw_data = str(log.get("data", "0x"))
    decoded_values = decode(
        list(definition.arg_types),
        bytes.fromhex(raw_data.removeprefix("0x")),
    )
    args = {
        name: _normalize_value(value)
        for name, value in zip(definition.arg_names, decoded_values, strict=True)
    }
    return IndexedChainEvent(
        event_name=definition.name,
        contract_address=to_checksum_address(str(log["address"])),
        block_number=_hex_to_int(log["blockNumber"]),
        block_hash=str(log.get("blockHash", "")),
        transaction_hash=str(log["transactionHash"]),
        log_index=_hex_to_int(log["logIndex"]),
        args=args,
    )


def event_topic(event_name: str) -> str:
    for definition in EVENT_DEFINITIONS:
        if definition.name == event_name:
            return definition.topic
    raise ValueError(f"Unknown event name: {event_name}")


def _normalize_value(value: object) -> object:
    if isinstance(value, bytes):
        return "0x" + value.hex()
    if isinstance(value, str) and value.startswith("0x") and len(value) == 42:
        return to_checksum_address(value)
    return value


def _block_tag(value: int | str) -> str:
    if isinstance(value, int):
        return hex(value)
    return value


def _hex_to_int(value: object) -> int:
    if isinstance(value, int):
        return value
    if not isinstance(value, str) or not value.startswith("0x"):
        raise ValueError("RPC log field must be a hex string")
    return int(value, 16)
