"""Verifier service for signed specialist executions."""

from __future__ import annotations

from eth_account import Account
from eth_account.messages import encode_defunct

from app.evaluation.attestations import verification_attestation_hash
from app.evaluation.scoring import score_specialist_response
from app.identity.canonical import canonical_json_bytes
from app.identity.hashing import canonical_json_hash
from app.identity.signing import verify_signed_execution
from app.schemas.contracts import (
    SignedAgentExecution,
    SpecialistResponse,
    TaskSpec,
    VerificationAttestation,
)


class VerifierService:
    """Score specialist outputs and reject invalid execution envelopes."""

    def __init__(
        self,
        *,
        acceptance_threshold: float = 0.5,
        verifier_private_key: str = "",
    ) -> None:
        self._acceptance_threshold = acceptance_threshold
        self._verifier_private_key = verifier_private_key

    def verify_signed_execution(
        self,
        signed_execution: SignedAgentExecution,
    ) -> VerificationAttestation:
        response = signed_execution.response
        if not verify_signed_execution(signed_execution):
            return self._sign_if_configured(
                VerificationAttestation(
                    job_id=response.job_id,
                    node_role=response.node_role,
                    peer_id=response.peer_id,
                    status="rejected",
                    score=0.0,
                    reasons=["invalid_signature"],
                    signer=signed_execution.signature.signer,
                    agent_wallet=signed_execution.identity.wallet,
                    output_hash=signed_execution.signature.output_hash,
                    ree_receipt_hash=response.ree_receipt_hash,
                    receipt_status=response.receipt_status,
                )
            )

        return self.verify_response(
            task=signed_execution.task,
            response=response,
            signer=signed_execution.signature.signer,
            output_hash=signed_execution.signature.output_hash,
        )

    def verify_response(
        self,
        *,
        task: TaskSpec,
        response: SpecialistResponse,
        signer: str | None = None,
        output_hash: str | None = None,
    ) -> VerificationAttestation:
        breakdown = score_specialist_response(response, task)
        score = breakdown.total
        reasons = _score_reasons(response=response, score=score)
        status = "accepted" if score >= self._acceptance_threshold else "rejected"
        if status == "rejected":
            reasons.append("score_below_threshold")

        return self._sign_if_configured(
            VerificationAttestation(
                job_id=response.job_id,
                node_role=response.node_role,
                peer_id=response.peer_id,
                status=status,
                score=score,
                reasons=reasons,
                signer=signer,
                agent_wallet=response.agent_wallet or signer,
                output_hash=output_hash or canonical_json_hash(response),
                ree_receipt_hash=response.ree_receipt_hash,
                receipt_status=response.receipt_status,
            )
        )

    def verify_responses(
        self,
        *,
        task: TaskSpec,
        responses: list[SpecialistResponse],
    ) -> list[VerificationAttestation]:
        return [
            self.verify_response(task=task, response=response) for response in responses
        ]

    def _sign_if_configured(
        self,
        attestation: VerificationAttestation,
    ) -> VerificationAttestation:
        if not self._verifier_private_key:
            return attestation

        attestation_hash = verification_attestation_hash(attestation)
        signer = Account.from_key(self._verifier_private_key).address
        message = encode_defunct(
            primitive=canonical_json_bytes(
                {
                    "domain": "signal-count.verifier-attestation",
                    "attestation_hash": attestation_hash,
                }
            )
        )
        signed = Account.sign_message(message, private_key=self._verifier_private_key)
        return attestation.model_copy(
            update={
                "verifier": signer,
                "attestation_hash": attestation_hash,
                "verifier_signature": f"0x{signed.signature.hex()}",
                "signature_algorithm": "eip191",
            }
        )


def _score_reasons(response: SpecialistResponse, score: float) -> list[str]:
    reasons = [f"deterministic_score={score:.4f}"]
    if response.receipt_status:
        reasons.append(f"receipt_status={response.receipt_status}")
    if response.citations:
        reasons.append("citations_present")
    if response.risks:
        reasons.append("risks_present")
    return reasons
