// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

contract SignalTaskRegistry {
    struct Task {
        bytes32 taskHash;
        string metadataURI;
        bool exists;
        bool finalized;
        bytes32 memoHash;
    }

    event TaskCreated(uint256 taskId, bytes32 taskHash, string metadataURI);
    event TaskFinalized(uint256 taskId, bytes32 memoHash);

    uint256 public nextTaskId = 1;
    mapping(uint256 => Task) public tasks;

    function createTask(
        bytes32 taskHash,
        string calldata metadataURI
    ) external returns (uint256 taskId) {
        require(taskHash != bytes32(0), "task hash required");

        taskId = nextTaskId;
        nextTaskId += 1;

        tasks[taskId] = Task({
            taskHash: taskHash,
            metadataURI: metadataURI,
            exists: true,
            finalized: false,
            memoHash: bytes32(0)
        });

        emit TaskCreated(taskId, taskHash, metadataURI);
    }

    function finalizeTask(uint256 taskId, bytes32 memoHash) external {
        Task storage task = tasks[taskId];
        require(task.exists, "task not found");
        require(memoHash != bytes32(0), "memo hash required");

        task.finalized = true;
        task.memoHash = memoHash;

        emit TaskFinalized(taskId, memoHash);
    }
}

