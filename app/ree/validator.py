"""Local REE receipt validation.

Validation checks that the receipt is structurally complete and that the
declared receipt_hash recomputes correctly under the Gensyn SDK algorithm.
Only receipt_verified (full re-execution) would prove the inference actually
ran inside an REE.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.ree.receipts import ReeReceipt, compute_receipt_hash


@dataclass(frozen=True)
class ReeValidationResult:
    """Outcome of a local REE receipt consistency check."""

    receipt_hash: str
    expected_receipt_hash: str
    matches: bool

    @property
    def is_valid(self) -> bool:
        return self.matches


def validate_ree_receipt(receipt: ReeReceipt) -> ReeValidationResult:
    """Recompute the canonical receipt hash and compare it to the declared one."""
    expected = compute_receipt_hash(
        commit_hash=receipt.commit_hash,
        config_hash=receipt.config_hash,
        prompt_hash=receipt.prompt_hash,
        parameters_hash=receipt.parameters_hash,
        tokens_hash=receipt.tokens_hash,
    )
    return ReeValidationResult(
        receipt_hash=receipt.receipt_hash,
        expected_receipt_hash=expected,
        matches=receipt.receipt_hash.lower() == expected.lower(),
    )
