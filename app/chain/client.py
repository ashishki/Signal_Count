"""Minimal Gensyn Testnet contract transaction builders."""

from __future__ import annotations

from dataclasses import dataclass

from eth_abi import encode
from eth_account import Account
from eth_utils import keccak, to_checksum_address

from app.chain.config import ChainConfig

DEFAULT_CREATE_TASK_GAS = 250_000
DEFAULT_RECORD_CONTRIBUTION_GAS = 350_000
DEFAULT_RECORD_REPUTATION_GAS = 250_000
DEFAULT_RECORD_REPUTATION_PAYOUT_GAS = 300_000


@dataclass(frozen=True)
class SignedContractTransaction:
    transaction: dict[str, object]
    raw_transaction: str
    transaction_hash: str


class SignalContractsClient:
    def __init__(self, config: ChainConfig) -> None:
        config.validate_testnet()
        self._config = config

    def build_create_task_transaction(
        self,
        *,
        task_hash: str,
        metadata_uri: str,
        nonce: int,
        gas_price_wei: int,
        gas: int = DEFAULT_CREATE_TASK_GAS,
    ) -> dict[str, object]:
        return self._base_transaction(
            to=self._config.task_registry_address,
            data=_encode_call(
                "createTask(bytes32,string)",
                ["bytes32", "string"],
                [_bytes32(task_hash), metadata_uri],
            ),
            nonce=nonce,
            gas=gas,
            gas_price_wei=gas_price_wei,
        )

    def sign_create_task_transaction(
        self,
        *,
        task_hash: str,
        metadata_uri: str,
        nonce: int,
        gas_price_wei: int,
        gas: int = DEFAULT_CREATE_TASK_GAS,
    ) -> SignedContractTransaction:
        transaction = self.build_create_task_transaction(
            task_hash=task_hash,
            metadata_uri=metadata_uri,
            nonce=nonce,
            gas_price_wei=gas_price_wei,
            gas=gas,
        )
        return self._sign_transaction(transaction)

    def build_record_contribution_transaction(
        self,
        *,
        task_id: int,
        agent: str,
        role: str,
        output_hash: str,
        ree_receipt_hash: str,
        metadata_uri: str,
        nonce: int,
        gas_price_wei: int,
        gas: int = DEFAULT_RECORD_CONTRIBUTION_GAS,
    ) -> dict[str, object]:
        return self._base_transaction(
            to=self._config.receipt_registry_address,
            data=_encode_call(
                "recordContribution(uint256,address,string,bytes32,bytes32,string)",
                ["uint256", "address", "string", "bytes32", "bytes32", "string"],
                [
                    task_id,
                    to_checksum_address(agent),
                    role,
                    _bytes32(output_hash),
                    _bytes32(ree_receipt_hash),
                    metadata_uri,
                ],
            ),
            nonce=nonce,
            gas=gas,
            gas_price_wei=gas_price_wei,
        )

    def sign_record_contribution_transaction(
        self,
        *,
        task_id: int,
        agent: str,
        role: str,
        output_hash: str,
        ree_receipt_hash: str,
        metadata_uri: str,
        nonce: int,
        gas_price_wei: int,
        gas: int = DEFAULT_RECORD_CONTRIBUTION_GAS,
    ) -> SignedContractTransaction:
        transaction = self.build_record_contribution_transaction(
            task_id=task_id,
            agent=agent,
            role=role,
            output_hash=output_hash,
            ree_receipt_hash=ree_receipt_hash,
            metadata_uri=metadata_uri,
            nonce=nonce,
            gas_price_wei=gas_price_wei,
            gas=gas,
        )
        return self._sign_transaction(transaction)

    def build_record_reputation_transaction(
        self,
        *,
        task_id: int,
        agent: str,
        role: str,
        score: int,
        points: int,
        metadata_uri: str,
        nonce: int,
        gas_price_wei: int,
        gas: int = DEFAULT_RECORD_REPUTATION_GAS,
    ) -> dict[str, object]:
        return self._base_transaction(
            to=self._config.reputation_vault_address,
            data=_encode_call(
                "recordReputation(uint256,address,string,uint256,uint256,string)",
                ["uint256", "address", "string", "uint256", "uint256", "string"],
                [
                    task_id,
                    to_checksum_address(agent),
                    role,
                    score,
                    points,
                    metadata_uri,
                ],
            ),
            nonce=nonce,
            gas=gas,
            gas_price_wei=gas_price_wei,
        )

    def sign_record_reputation_transaction(
        self,
        *,
        task_id: int,
        agent: str,
        role: str,
        score: int,
        points: int,
        metadata_uri: str,
        nonce: int,
        gas_price_wei: int,
        gas: int = DEFAULT_RECORD_REPUTATION_GAS,
    ) -> SignedContractTransaction:
        transaction = self.build_record_reputation_transaction(
            task_id=task_id,
            agent=agent,
            role=role,
            score=score,
            points=points,
            metadata_uri=metadata_uri,
            nonce=nonce,
            gas_price_wei=gas_price_wei,
            gas=gas,
        )
        return self._sign_transaction(transaction)

    def build_record_reputation_payout_transaction(
        self,
        *,
        task_id: int,
        agent: str,
        role: str,
        score: int,
        points: int,
        payout_wei: int,
        metadata_uri: str,
        nonce: int,
        gas_price_wei: int,
        gas: int = DEFAULT_RECORD_REPUTATION_PAYOUT_GAS,
    ) -> dict[str, object]:
        return self._base_transaction(
            to=self._config.reputation_vault_address,
            data=_encode_call(
                (
                    "recordReputationWithNativeTestPayout("
                    "uint256,address,string,uint256,uint256,uint256,string)"
                ),
                [
                    "uint256",
                    "address",
                    "string",
                    "uint256",
                    "uint256",
                    "uint256",
                    "string",
                ],
                [
                    task_id,
                    to_checksum_address(agent),
                    role,
                    score,
                    points,
                    payout_wei,
                    metadata_uri,
                ],
            ),
            nonce=nonce,
            gas=gas,
            gas_price_wei=gas_price_wei,
            value=payout_wei,
        )

    def sign_record_reputation_payout_transaction(
        self,
        *,
        task_id: int,
        agent: str,
        role: str,
        score: int,
        points: int,
        payout_wei: int,
        metadata_uri: str,
        nonce: int,
        gas_price_wei: int,
        gas: int = DEFAULT_RECORD_REPUTATION_PAYOUT_GAS,
    ) -> SignedContractTransaction:
        transaction = self.build_record_reputation_payout_transaction(
            task_id=task_id,
            agent=agent,
            role=role,
            score=score,
            points=points,
            payout_wei=payout_wei,
            metadata_uri=metadata_uri,
            nonce=nonce,
            gas_price_wei=gas_price_wei,
            gas=gas,
        )
        return self._sign_transaction(transaction)

    def _base_transaction(
        self,
        *,
        to: str,
        data: str,
        nonce: int,
        gas: int,
        gas_price_wei: int,
        value: int = 0,
    ) -> dict[str, object]:
        return {
            "to": to_checksum_address(to),
            "value": value,
            "data": data,
            "nonce": nonce,
            "chainId": self._config.chain_id,
            "gas": gas,
            "gasPrice": gas_price_wei,
        }

    def _sign_transaction(
        self,
        transaction: dict[str, object],
    ) -> SignedContractTransaction:
        if not self._config.writer_private_key:
            raise ValueError("chain writer private key is not configured")

        signed = Account.sign_transaction(
            transaction,
            private_key=self._config.writer_private_key,
        )
        return SignedContractTransaction(
            transaction=transaction,
            raw_transaction=f"0x{signed.raw_transaction.hex()}",
            transaction_hash=f"0x{signed.hash.hex()}",
        )


def _encode_call(signature: str, types: list[str], values: list[object]) -> str:
    selector = keccak(text=signature)[:4]
    encoded_args = encode(types, values)
    return f"0x{(selector + encoded_args).hex()}"


def _bytes32(value: str) -> bytes:
    if value.startswith("sha256:"):
        normalized = value.removeprefix("sha256:")
    else:
        normalized = value.removeprefix("0x")
    if len(normalized) != 64:
        raise ValueError("bytes32 value must be 32 bytes")
    return bytes.fromhex(normalized)
