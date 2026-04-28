"""Application settings for Signal Count."""

from __future__ import annotations

from dataclasses import dataclass
from os import getenv


@dataclass(frozen=True)
class Settings:
    signal_count_offline_demo: bool = (
        getenv("SIGNAL_COUNT_OFFLINE_DEMO", "")
    ).lower() in {"1", "true", "yes"}
    signal_count_demo_llm: bool = (getenv("SIGNAL_COUNT_DEMO_LLM", "")).lower() in {
        "1",
        "true",
        "yes",
    }
    signal_count_offline_fail_role: str = getenv("SIGNAL_COUNT_OFFLINE_FAIL_ROLE", "")
    signal_count_chain_receipts: bool = (
        getenv("SIGNAL_COUNT_CHAIN_RECEIPTS", "")
    ).lower() in {"1", "true", "yes"}
    axl_local_base_url: str = getenv("AXL_LOCAL_BASE_URL", "http://127.0.0.1:9002")
    axl_topology_path: str = getenv("AXL_TOPOLOGY_PATH", "/topology")
    regime_peer_id: str = getenv("REGIME_PEER_ID", "peer-regime-example")
    regime_service_name: str = getenv("REGIME_SERVICE_NAME", "regime_analyst")
    narrative_peer_id: str = getenv("NARRATIVE_PEER_ID", "peer-narrative-example")
    narrative_service_name: str = getenv(
        "NARRATIVE_SERVICE_NAME",
        "narrative_analyst",
    )
    risk_peer_id: str = getenv("RISK_PEER_ID", "peer-risk-example")
    risk_service_name: str = getenv("RISK_SERVICE_NAME", "risk_analyst")
    axl_mcp_router_url: str = getenv("AXL_MCP_ROUTER_URL", "http://127.0.0.1:9003")
    axl_dispatch_timeout_seconds: float = float(
        getenv("AXL_DISPATCH_TIMEOUT_SECONDS", "30")
    )
    node_role: str = getenv("NODE_ROLE", "regime")
    node_service_name: str = getenv("NODE_SERVICE_NAME", "")
    node_public_url: str = getenv("NODE_PUBLIC_URL", "http://127.0.0.1:7101")
    node_wallet_address: str = getenv("NODE_WALLET_ADDRESS", "")
    gensyn_rpc_url: str = getenv(
        "GENSYN_RPC_URL",
        "https://gensyn-testnet.g.alchemy.com/public",
    )
    gensyn_chain_id: int = int(getenv("GENSYN_CHAIN_ID", "685685"))
    gensyn_explorer_base_url: str = getenv(
        "GENSYN_EXPLORER_BASE_URL",
        "https://gensyn-testnet.explorer.alchemy.com",
    )
    signal_agent_registry_address: str = getenv(
        "SIGNAL_AGENT_REGISTRY_ADDRESS",
        "0x9Aa7E223B5bd2384cea38F0d2464Aa6cbB0146A9",
    )
    signal_task_registry_address: str = getenv(
        "SIGNAL_TASK_REGISTRY_ADDRESS",
        "0x7b0ED22C93eBdF6Be5c3f6D6fC8F7B51fdFBd861",
    )
    signal_receipt_registry_address: str = getenv(
        "SIGNAL_RECEIPT_REGISTRY_ADDRESS",
        "0xb67E197538F2cF9d398c28ec85d4f99fb2e668cf",
    )
    signal_reputation_vault_address: str = getenv(
        "SIGNAL_REPUTATION_VAULT_ADDRESS",
        "0x0000000000000000000000000000000000000000",
    )
    signal_count_native_test_payouts: bool = (
        getenv("SIGNAL_COUNT_NATIVE_TEST_PAYOUTS", "")
    ).lower() in {"1", "true", "yes"}
    native_test_payout_wei: int = int(getenv("NATIVE_TEST_PAYOUT_WEI", "1000000000"))
    native_test_payout_max_wei: int = int(
        getenv("NATIVE_TEST_PAYOUT_MAX_WEI", "1000000000000")
    )
    chain_writer_private_key: str = getenv(
        "CHAIN_WRITER_PRIVATE_KEY",
        getenv("DEPLOYER_PRIVATE_KEY", ""),
    )
    signal_count_ree_enabled: bool = (
        getenv("SIGNAL_COUNT_REE_ENABLED", "")
    ).lower() in {"1", "true", "yes"}
    # Full path to ree.sh from github.com/gensyn-ai/ree (e.g. /opt/ree/ree.sh).
    gensyn_sdk_command: str = getenv("GENSYN_SDK_COMMAND", "ree.sh")
    ree_model: str = getenv("REE_MODEL", "Qwen/Qwen3-0.6B")
    ree_cpu_only: bool = (getenv("REE_CPU_ONLY", "")).lower() in {"1", "true", "yes"}
    verifier_private_key: str = getenv("VERIFIER_PRIVATE_KEY", "")


def get_settings() -> Settings:
    return Settings()
