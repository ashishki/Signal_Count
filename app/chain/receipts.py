"""Local chain receipt data structures."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.chain.explorer import explorer_tx_url


@dataclass(frozen=True)
class ChainReceipt:
    kind: str
    status: str
    tx_hash: str | None = None
    explorer_url: str | None = None
    error: str | None = None
    role: str | None = None
    agent: str | None = None
    ree_receipt_hash: str | None = None
    ree_status: str | None = None
    verifier_score: float | None = None
    reputation_points: float | None = None
    native_test_payout_wei: int | None = None

    @classmethod
    def confirmed(
        cls,
        *,
        kind: str,
        tx_hash: str,
        explorer_base_url: str,
        role: str | None = None,
        agent: str | None = None,
        ree_receipt_hash: str | None = None,
        ree_status: str | None = None,
        verifier_score: float | None = None,
        reputation_points: float | None = None,
        native_test_payout_wei: int | None = None,
    ) -> "ChainReceipt":
        return cls(
            kind=kind,
            status="confirmed",
            tx_hash=tx_hash,
            explorer_url=explorer_tx_url(tx_hash, explorer_base_url),
            role=role,
            agent=agent,
            ree_receipt_hash=ree_receipt_hash,
            ree_status=ree_status,
            verifier_score=verifier_score,
            reputation_points=reputation_points,
            native_test_payout_wei=native_test_payout_wei,
        )

    @classmethod
    def failed(
        cls,
        *,
        kind: str,
        error: str,
        role: str | None = None,
    ) -> "ChainReceipt":
        return cls(kind=kind, status="failed", error=error, role=role)

    def to_dict(self) -> dict[str, object]:
        return {
            key: value
            for key, value in {
                "kind": self.kind,
                "status": self.status,
                "tx_hash": self.tx_hash,
                "explorer_url": self.explorer_url,
                "error": self.error,
                "role": self.role,
                "agent": self.agent,
                "ree_receipt_hash": self.ree_receipt_hash,
                "ree_status": self.ree_status,
                "verifier_score": self.verifier_score,
                "reputation_points": self.reputation_points,
                "native_test_payout_wei": self.native_test_payout_wei,
            }.items()
            if value is not None
        }


@dataclass(frozen=True)
class JobChainReceipts:
    receipt_status: str
    receipts: list[ChainReceipt] = field(default_factory=list)

    def to_metadata(self) -> dict[str, object]:
        return {
            "receipt_status": self.receipt_status,
            "chain_receipts": [receipt.to_dict() for receipt in self.receipts],
        }
