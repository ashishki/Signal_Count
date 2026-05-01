// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

contract SignalReceiptRegistry {
    struct Contribution {
        uint256 taskId;
        address agent;
        string role;
        bytes32 outputHash;
        bytes32 reeReceiptHash;
        string metadataURI;
    }

    struct Verification {
        uint256 taskId;
        address verifier;
        bytes32 verdictHash;
        uint256 score;
    }

    event ContributionRecorded(
        uint256 taskId,
        address agent,
        string role,
        bytes32 outputHash,
        bytes32 reeReceiptHash,
        string metadataURI
    );
    event VerificationRecorded(
        uint256 taskId,
        address verifier,
        bytes32 verdictHash,
        uint256 score
    );

    Contribution[] private contributions;
    Verification[] private verifications;

    function recordContribution(
        uint256 taskId,
        address agent,
        string calldata role,
        bytes32 outputHash,
        bytes32 reeReceiptHash,
        string calldata metadataURI
    ) external returns (uint256 contributionId) {
        require(taskId != 0, "task id required");
        require(agent != address(0), "agent required");
        require(bytes(role).length != 0, "role required");
        require(outputHash != bytes32(0), "output hash required");

        contributionId = contributions.length;
        contributions.push(
            Contribution({
                taskId: taskId,
                agent: agent,
                role: role,
                outputHash: outputHash,
                reeReceiptHash: reeReceiptHash,
                metadataURI: metadataURI
            })
        );

        emit ContributionRecorded(
            taskId,
            agent,
            role,
            outputHash,
            reeReceiptHash,
            metadataURI
        );
    }

    function recordVerification(
        uint256 taskId,
        address verifier,
        bytes32 verdictHash,
        uint256 score
    ) external returns (uint256 verificationId) {
        require(taskId != 0, "task id required");
        require(verifier != address(0), "verifier required");
        require(verdictHash != bytes32(0), "verdict hash required");

        verificationId = verifications.length;
        verifications.push(
            Verification({
                taskId: taskId,
                verifier: verifier,
                verdictHash: verdictHash,
                score: score
            })
        );

        emit VerificationRecorded(taskId, verifier, verdictHash, score);
    }

    function contributionCount() external view returns (uint256) {
        return contributions.length;
    }

    function verificationCount() external view returns (uint256) {
        return verifications.length;
    }

    function getContribution(
        uint256 contributionId
    ) external view returns (Contribution memory) {
        return contributions[contributionId];
    }

    function getVerification(
        uint256 verificationId
    ) external view returns (Verification memory) {
        return verifications[verificationId];
    }
}

