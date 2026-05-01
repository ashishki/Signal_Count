// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {SignalAgentRegistry} from "../src/SignalAgentRegistry.sol";
import {SignalReceiptRegistry} from "../src/SignalReceiptRegistry.sol";
import {SignalReputationVault} from "../src/SignalReputationVault.sol";
import {SignalTaskRegistry} from "../src/SignalTaskRegistry.sol";

interface Vm {
    function expectEmit(
        bool checkTopic1,
        bool checkTopic2,
        bool checkTopic3,
        bool checkData
    ) external;
}

contract SignalContractsTest {
    Vm private constant vm =
        Vm(address(uint160(uint256(keccak256("hevm cheat code")))));

    event AgentRegistered(
        address agent,
        bytes32 peerIdHash,
        string role,
        string metadataURI
    );
    event TaskCreated(uint256 taskId, bytes32 taskHash, string metadataURI);
    event ContributionRecorded(
        uint256 taskId,
        address agent,
        string role,
        bytes32 outputHash,
        bytes32 reeReceiptHash,
        string metadataURI
    );
    event ReputationRecorded(
        uint256 taskId,
        address agent,
        string role,
        uint256 score,
        uint256 points,
        uint256 nativeTestPayoutWei,
        string metadataURI
    );

    function testRegisterAgent() public {
        SignalAgentRegistry registry = new SignalAgentRegistry();
        bytes32 peerIdHash = keccak256("peer-risk-1");

        vm.expectEmit(false, false, false, true);
        emit AgentRegistered(
            address(this),
            peerIdHash,
            "risk",
            "ipfs://agent-risk"
        );

        registry.registerAgent(peerIdHash, "risk", "ipfs://agent-risk");

        (
            bytes32 storedPeerIdHash,
            string memory role,
            string memory metadataURI,
            bool registered
        ) = registry.agents(address(this));
        require(storedPeerIdHash == peerIdHash, "peer id hash mismatch");
        require(_same(role, "risk"), "role mismatch");
        require(_same(metadataURI, "ipfs://agent-risk"), "metadata mismatch");
        require(registered, "agent not registered");
    }

    function testRecordContribution() public {
        SignalTaskRegistry taskRegistry = new SignalTaskRegistry();
        SignalReceiptRegistry receiptRegistry = new SignalReceiptRegistry();
        bytes32 taskHash = keccak256("task-123");
        bytes32 outputHash = keccak256("risk-output");
        bytes32 reeReceiptHash = bytes32(0);

        vm.expectEmit(false, false, false, true);
        emit TaskCreated(1, taskHash, "ipfs://task-123");

        uint256 taskId = taskRegistry.createTask(taskHash, "ipfs://task-123");
        require(taskId == 1, "task id mismatch");

        vm.expectEmit(false, false, false, true);
        emit ContributionRecorded(
            taskId,
            address(this),
            "risk",
            outputHash,
            reeReceiptHash,
            "ipfs://risk-output"
        );

        uint256 contributionId = receiptRegistry.recordContribution(
            taskId,
            address(this),
            "risk",
            outputHash,
            reeReceiptHash,
            "ipfs://risk-output"
        );

        require(contributionId == 0, "contribution id mismatch");
        require(receiptRegistry.contributionCount() == 1, "count mismatch");
    }

    function testRecordReputation() public {
        SignalTaskRegistry taskRegistry = new SignalTaskRegistry();
        SignalReputationVault reputationVault = new SignalReputationVault();
        uint256 taskId = taskRegistry.createTask(
            keccak256("task-123"),
            "ipfs://task-123"
        );
        uint256 score = 850000;
        uint256 points = 85000000;

        require(
            reputationVault.recorder() == address(this),
            "recorder mismatch"
        );

        vm.expectEmit(false, false, false, true);
        emit ReputationRecorded(
            taskId,
            address(this),
            "risk",
            score,
            points,
            0,
            "ipfs://reputation-risk"
        );

        uint256 recordId = reputationVault.recordReputation(
            taskId,
            address(this),
            "risk",
            score,
            points,
            "ipfs://reputation-risk"
        );

        require(recordId == 0, "record id mismatch");
        require(reputationVault.recordCount() == 1, "count mismatch");
    }

    function testRecordReputationWithNativeTestPayout() public {
        SignalReputationVault reputationVault = new SignalReputationVault();
        uint256 payoutWei = 1_000_000_000;

        vm.expectEmit(false, false, false, true);
        emit ReputationRecorded(
            1,
            address(this),
            "risk",
            850000,
            85000000,
            payoutWei,
            "ipfs://reputation-risk"
        );

        uint256 recordId = reputationVault.recordReputationWithNativeTestPayout{
            value: payoutWei
        }(
            1,
            payable(address(this)),
            "risk",
            850000,
            85000000,
            payoutWei,
            "ipfs://reputation-risk"
        );

        require(recordId == 0, "record id mismatch");
        SignalReputationVault.ReputationRecord memory record = reputationVault
            .getRecord(recordId);
        require(
            record.nativeTestPayoutWei == payoutWei,
            "native payout mismatch"
        );
    }

    function testRecordReputationRejectsOversizedNativeTestPayout() public {
        SignalReputationVault reputationVault = new SignalReputationVault();
        uint256 payoutWei = reputationVault.MAX_NATIVE_TEST_PAYOUT_WEI() + 1;

        try
            reputationVault.recordReputationWithNativeTestPayout{
                value: payoutWei
            }(
                1,
                payable(address(this)),
                "risk",
                850000,
                85000000,
                payoutWei,
                "ipfs://reputation-risk"
            )
        {
            revert("oversized payout succeeded");
        } catch {}

        require(reputationVault.recordCount() == 0, "unexpected record");
    }

    function testRecordReputationRejectsNonRecorder() public {
        SignalReputationVault reputationVault = new SignalReputationVault();
        ReputationAttacker attacker = new ReputationAttacker();

        try
            attacker.record(
                reputationVault,
                1,
                address(this),
                "risk",
                850000,
                85000000,
                "ipfs://reputation-risk"
            )
        {
            revert("non-recorder write succeeded");
        } catch {}

        require(reputationVault.recordCount() == 0, "unexpected record");
    }

    function _same(
        string memory left,
        string memory right
    ) private pure returns (bool) {
        return keccak256(bytes(left)) == keccak256(bytes(right));
    }

    receive() external payable {}
}

contract ReputationAttacker {
    function record(
        SignalReputationVault reputationVault,
        uint256 taskId,
        address agent,
        string calldata role,
        uint256 score,
        uint256 points,
        string calldata metadataURI
    ) external {
        reputationVault.recordReputation(
            taskId,
            agent,
            role,
            score,
            points,
            metadataURI
        );
    }
}
