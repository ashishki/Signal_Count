// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

contract SignalReputationVault {
    address public immutable recorder;
    uint256 public constant MAX_NATIVE_TEST_PAYOUT_WEI = 1_000_000_000_000;

    struct ReputationRecord {
        uint256 taskId;
        address agent;
        string role;
        uint256 score;
        uint256 points;
        uint256 nativeTestPayoutWei;
        string metadataURI;
    }

    event ReputationRecorded(
        uint256 taskId,
        address agent,
        string role,
        uint256 score,
        uint256 points,
        uint256 nativeTestPayoutWei,
        string metadataURI
    );

    ReputationRecord[] private records;

    constructor() {
        recorder = msg.sender;
    }

    function recordReputation(
        uint256 taskId,
        address agent,
        string calldata role,
        uint256 score,
        uint256 points,
        string calldata metadataURI
    ) external returns (uint256 recordId) {
        require(msg.sender == recorder, "recorder only");
        require(taskId != 0, "task id required");
        require(agent != address(0), "agent required");
        require(bytes(role).length != 0, "role required");
        require(score != 0, "verifier score required");
        require(points != 0, "points required");

        recordId = _recordReputation(
            taskId,
            agent,
            role,
            score,
            points,
            0,
            metadataURI
        );
    }

    function recordReputationWithNativeTestPayout(
        uint256 taskId,
        address payable agent,
        string calldata role,
        uint256 score,
        uint256 points,
        uint256 payoutWei,
        string calldata metadataURI
    ) external payable returns (uint256 recordId) {
        require(payoutWei <= MAX_NATIVE_TEST_PAYOUT_WEI, "payout exceeds cap");
        require(msg.value == payoutWei, "payout value mismatch");

        recordId = _recordReputation(
            taskId,
            agent,
            role,
            score,
            points,
            payoutWei,
            metadataURI
        );

        if (payoutWei != 0) {
            (bool sent, ) = agent.call{value: payoutWei}("");
            require(sent, "native test payout failed");
        }
    }

    function recordCount() external view returns (uint256) {
        return records.length;
    }

    function getRecord(
        uint256 recordId
    ) external view returns (ReputationRecord memory) {
        return records[recordId];
    }

    function _recordReputation(
        uint256 taskId,
        address agent,
        string calldata role,
        uint256 score,
        uint256 points,
        uint256 nativeTestPayoutWei,
        string calldata metadataURI
    ) private returns (uint256 recordId) {
        require(msg.sender == recorder, "recorder only");
        require(taskId != 0, "task id required");
        require(agent != address(0), "agent required");
        require(bytes(role).length != 0, "role required");
        require(score != 0, "verifier score required");
        require(points != 0, "points required");

        recordId = records.length;
        records.push(
            ReputationRecord({
                taskId: taskId,
                agent: agent,
                role: role,
                score: score,
                points: points,
                nativeTestPayoutWei: nativeTestPayoutWei,
                metadataURI: metadataURI
            })
        );

        emit ReputationRecorded(
            taskId,
            agent,
            role,
            score,
            points,
            nativeTestPayoutWei,
            metadataURI
        );
    }
}
