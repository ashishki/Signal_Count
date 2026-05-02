"""Read-only chain verification helpers for persisted transaction receipts."""

from __future__ import annotations

from dataclasses import dataclass

from app.chain.broadcaster import JsonRpcTransport
from app.chain.config import ChainConfig


@dataclass(frozen=True)
class ChainTxVerification:
    tx_hash: str
    status: str
    rpc_status: str
    block_number: int | None = None
    transaction_index: int | None = None
    error: str = ""

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "tx_hash": self.tx_hash,
            "status": self.status,
            "rpc_status": self.rpc_status,
        }
        if self.block_number is not None:
            payload["block_number"] = self.block_number
        if self.transaction_index is not None:
            payload["transaction_index"] = self.transaction_index
        if self.error:
            payload["error"] = self.error
        return payload


class GensynChainTxVerifier:
    def __init__(
        self,
        *,
        config: ChainConfig,
        transport: JsonRpcTransport | None = None,
    ) -> None:
        config.validate_testnet()
        self._transport = transport or JsonRpcTransport(config.rpc_url)

    def verify_transaction(self, tx_hash: str) -> ChainTxVerification:
        try:
            result = self._transport.call("eth_getTransactionReceipt", [tx_hash])
        except Exception:
            return ChainTxVerification(
                tx_hash=tx_hash,
                status="present",
                rpc_status="rpc_unavailable",
                error="Gensyn Testnet RPC receipt lookup failed",
            )

        if result is None:
            return ChainTxVerification(
                tx_hash=tx_hash,
                status="missing",
                rpc_status="not_found",
            )
        if not isinstance(result, dict):
            return ChainTxVerification(
                tx_hash=tx_hash,
                status="present",
                rpc_status="invalid_response",
                error="Gensyn Testnet RPC receipt response was not an object",
            )

        try:
            receipt_status = _hex_to_int(result.get("status"))
        except ValueError:
            return ChainTxVerification(
                tx_hash=tx_hash,
                status="present",
                rpc_status="invalid_response",
                error="Gensyn Testnet RPC receipt status was not valid hex",
            )

        return ChainTxVerification(
            tx_hash=tx_hash,
            status="verified" if receipt_status == 1 else "failed",
            rpc_status="confirmed" if receipt_status == 1 else "reverted",
            block_number=_optional_hex_to_int(result.get("blockNumber")),
            transaction_index=_optional_hex_to_int(result.get("transactionIndex")),
        )


def _optional_hex_to_int(value: object) -> int | None:
    if value is None:
        return None
    try:
        return _hex_to_int(value)
    except ValueError:
        return None


def _hex_to_int(value: object) -> int:
    if not isinstance(value, str) or not value.startswith("0x"):
        raise ValueError("expected hex string")
    return int(value, 16)
