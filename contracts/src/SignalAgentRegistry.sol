// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

contract SignalAgentRegistry {
    struct Agent {
        bytes32 peerIdHash;
        string role;
        string metadataURI;
        bool registered;
    }

    event AgentRegistered(
        address agent,
        bytes32 peerIdHash,
        string role,
        string metadataURI
    );

    mapping(address => Agent) public agents;

    function registerAgent(
        bytes32 peerIdHash,
        string calldata role,
        string calldata metadataURI
    ) external {
        require(peerIdHash != bytes32(0), "peer id hash required");
        require(bytes(role).length != 0, "role required");

        agents[msg.sender] = Agent({
            peerIdHash: peerIdHash,
            role: role,
            metadataURI: metadataURI,
            registered: true
        });

        emit AgentRegistered(msg.sender, peerIdHash, role, metadataURI);
    }
}

