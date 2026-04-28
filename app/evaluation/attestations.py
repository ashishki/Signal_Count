"""Verification attestation helpers."""

from __future__ import annotations

from app.identity.hashing import canonical_json_hash
from app.schemas.contracts import VerificationAttestation

_SIGNATURE_FIELDS = {
    "verifier",
    "attestation_hash",
    "verifier_signature",
    "signature_algorithm",
}


def verification_attestation_hash(attestation: VerificationAttestation) -> str:
    """Return a deterministic hash for recording a verifier verdict."""
    return canonical_json_hash(
        attestation.model_dump(mode="json", exclude=_SIGNATURE_FIELDS)
    )
