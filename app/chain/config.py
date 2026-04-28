"""Chain configuration for Gensyn Testnet contract writes."""

from __future__ import annotations

from dataclasses import dataclass

from eth_utils import to_checksum_address

from app.config.settings import Settings, get_settings

GENSYN_TESTNET_CHAIN_ID = 685685
DEFAULT_NATIVE_TEST_PAYOUT_MAX_WEI = 1_000_000_000_000


@dataclass(frozen=True)
class ChainConfig:
    rpc_url: str
    chain_id: int
    explorer_base_url: str
    agent_registry_address: str
    task_registry_address: str
    receipt_registry_address: str
    reputation_vault_address: str = "0x0000000000000000000000000000000000000000"
    native_test_payouts_enabled: bool = False
    native_test_payout_wei: int = 1_000_000_000
    native_test_payout_max_wei: int = DEFAULT_NATIVE_TEST_PAYOUT_MAX_WEI
    writer_private_key: str = ""

    @classmethod
    def from_settings(cls, settings: Settings | None = None) -> "ChainConfig":
        resolved = settings or get_settings()
        return cls(
            rpc_url=resolved.gensyn_rpc_url,
            chain_id=resolved.gensyn_chain_id,
            explorer_base_url=resolved.gensyn_explorer_base_url,
            agent_registry_address=to_checksum_address(
                resolved.signal_agent_registry_address
            ),
            task_registry_address=to_checksum_address(
                resolved.signal_task_registry_address
            ),
            receipt_registry_address=to_checksum_address(
                resolved.signal_receipt_registry_address
            ),
            reputation_vault_address=to_checksum_address(
                resolved.signal_reputation_vault_address
            ),
            native_test_payouts_enabled=resolved.signal_count_native_test_payouts,
            native_test_payout_wei=resolved.native_test_payout_wei,
            native_test_payout_max_wei=resolved.native_test_payout_max_wei,
            writer_private_key=normalize_private_key(resolved.chain_writer_private_key),
        )

    def validate_testnet(self) -> None:
        if self.chain_id != GENSYN_TESTNET_CHAIN_ID:
            raise ValueError("Gensyn Testnet chain id must be 685685")
        if self.native_test_payout_wei < 0:
            raise ValueError("native test payout wei must be non-negative")
        if self.native_test_payout_max_wei > DEFAULT_NATIVE_TEST_PAYOUT_MAX_WEI:
            raise ValueError("native test payout max exceeds hard cap")
        if self.native_test_payout_wei > self.native_test_payout_max_wei:
            raise ValueError("native test payout exceeds configured max")


def normalize_private_key(private_key: str) -> str:
    if not private_key:
        return ""
    return private_key if private_key.startswith("0x") else f"0x{private_key}"
