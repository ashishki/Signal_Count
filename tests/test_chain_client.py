from eth_account import Account
from eth_utils import keccak

from app.chain.client import SignalContractsClient
from app.chain.config import ChainConfig
from app.chain.explorer import explorer_tx_url

PRIVATE_KEY = "0x0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"


def test_build_create_task_transaction() -> None:
    client = SignalContractsClient(_config())
    task_hash = "0x" + "11" * 32

    signed = client.sign_create_task_transaction(
        task_hash=task_hash,
        metadata_uri="ipfs://task-123",
        nonce=7,
        gas_price_wei=501,
    )

    assert signed.transaction["to"] == "0x7b0ED22C93eBdF6Be5c3f6D6fC8F7B51fdFBd861"
    assert signed.transaction["chainId"] == 685685
    assert signed.transaction["nonce"] == 7
    assert signed.transaction["gasPrice"] == 501
    assert str(signed.transaction["data"]).startswith(
        "0x" + keccak(text="createTask(bytes32,string)")[:4].hex()
    )
    assert signed.raw_transaction.startswith("0x")
    assert Account.recover_transaction(signed.raw_transaction) == (
        "0xFCAd0B19bB29D4674531d6f115237E16AfCE377c"
    )


def test_build_record_contribution_accepts_sha256_ree_hash() -> None:
    client = SignalContractsClient(_config())

    signed = client.sign_record_contribution_transaction(
        task_id=1,
        agent="0xFCAd0B19bB29D4674531d6f115237E16AfCE377c",
        role="risk",
        output_hash="0x" + "22" * 32,
        ree_receipt_hash=(
            "sha256:36ae72fccc5e179a6986d0af614546170ed60be0d0ab953e05978a10c7a9dcb3"
        ),
        metadata_uri="ipfs://contribution-1",
        nonce=8,
        gas_price_wei=502,
    )

    assert signed.transaction["to"] == "0xb67E197538F2cF9d398c28ec85d4f99fb2e668cf"
    assert signed.transaction["chainId"] == 685685
    assert signed.transaction["nonce"] == 8
    assert str(signed.transaction["data"]).startswith(
        "0x"
        + keccak(
            text="recordContribution(uint256,address,string,bytes32,bytes32,string)"
        )[:4].hex()
    )
    assert Account.recover_transaction(signed.raw_transaction) == (
        "0xFCAd0B19bB29D4674531d6f115237E16AfCE377c"
    )


def test_build_record_reputation_transaction() -> None:
    client = SignalContractsClient(
        _config(reputation_vault_address="0x3a89E81bd2BAE43CbAB6C41c064057CFaa227C87")
    )

    signed = client.sign_record_reputation_transaction(
        task_id=1,
        agent="0xFCAd0B19bB29D4674531d6f115237E16AfCE377c",
        role="risk",
        score=850000,
        points=85000000,
        metadata_uri="ipfs://reputation-risk",
        nonce=9,
        gas_price_wei=503,
    )

    assert signed.transaction["to"] == "0x3A89e81Bd2Bae43cBab6C41C064057Cfaa227c87"
    assert signed.transaction["chainId"] == 685685
    assert signed.transaction["nonce"] == 9
    assert str(signed.transaction["data"]).startswith(
        "0x"
        + keccak(
            text="recordReputation(uint256,address,string,uint256,uint256,string)"
        )[:4].hex()
    )
    assert Account.recover_transaction(signed.raw_transaction) == (
        "0xFCAd0B19bB29D4674531d6f115237E16AfCE377c"
    )


def test_build_record_reputation_native_test_payout_transaction() -> None:
    client = SignalContractsClient(
        _config(
            reputation_vault_address="0x3a89E81bd2BAE43CbAB6C41c064057CFaa227C87",
            native_test_payouts_enabled=True,
            native_test_payout_wei=1_000_000_000,
        )
    )

    signed = client.sign_record_reputation_payout_transaction(
        task_id=1,
        agent="0xFCAd0B19bB29D4674531d6f115237E16AfCE377c",
        role="risk",
        score=850000,
        points=85000000,
        payout_wei=1_000_000_000,
        metadata_uri="ipfs://reputation-risk",
        nonce=10,
        gas_price_wei=504,
    )

    assert signed.transaction["value"] == 1_000_000_000
    assert str(signed.transaction["data"]).startswith(
        "0x"
        + keccak(
            text=(
                "recordReputationWithNativeTestPayout("
                "uint256,address,string,uint256,uint256,uint256,string)"
            )
        )[:4].hex()
    )
    assert Account.recover_transaction(signed.raw_transaction) == (
        "0xFCAd0B19bB29D4674531d6f115237E16AfCE377c"
    )


def test_explorer_tx_url() -> None:
    assert (
        explorer_tx_url(
            "0xabc123",
            "https://gensyn-testnet.explorer.alchemy.com/",
        )
        == "https://gensyn-testnet.explorer.alchemy.com/tx/0xabc123"
    )


def _config(
    *,
    reputation_vault_address: str = "0x0000000000000000000000000000000000000000",
    native_test_payouts_enabled: bool = False,
    native_test_payout_wei: int = 1_000_000_000,
) -> ChainConfig:
    return ChainConfig(
        rpc_url="https://gensyn-testnet.g.alchemy.com/public",
        chain_id=685685,
        explorer_base_url="https://gensyn-testnet.explorer.alchemy.com",
        agent_registry_address="0x9Aa7E223B5bd2384cea38F0d2464Aa6cbB0146A9",
        task_registry_address="0x7b0ED22C93eBdF6Be5c3f6D6fC8F7B51fdFBd861",
        receipt_registry_address="0xb67E197538F2cF9d398c28ec85d4f99fb2e668cf",
        reputation_vault_address=reputation_vault_address,
        native_test_payouts_enabled=native_test_payouts_enabled,
        native_test_payout_wei=native_test_payout_wei,
        writer_private_key=PRIVATE_KEY,
    )
