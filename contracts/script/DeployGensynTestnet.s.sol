// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {SignalAgentRegistry} from "../src/SignalAgentRegistry.sol";
import {SignalReceiptRegistry} from "../src/SignalReceiptRegistry.sol";
import {SignalTaskRegistry} from "../src/SignalTaskRegistry.sol";

interface Vm {
    function envUint(string calldata name) external returns (uint256);
    function startBroadcast(uint256 privateKey) external;
    function stopBroadcast() external;
}

contract DeployGensynTestnet {
    uint256 private constant GENSYN_TESTNET_CHAIN_ID = 685685;
    Vm private constant vm =
        Vm(address(uint160(uint256(keccak256("hevm cheat code")))));

    SignalAgentRegistry public agentRegistry;
    SignalTaskRegistry public taskRegistry;
    SignalReceiptRegistry public receiptRegistry;

    function run()
        external
        returns (
            SignalAgentRegistry deployedAgentRegistry,
            SignalTaskRegistry deployedTaskRegistry,
            SignalReceiptRegistry deployedReceiptRegistry
        )
    {
        require(
            block.chainid == GENSYN_TESTNET_CHAIN_ID,
            "wrong Gensyn Testnet chain id"
        );

        uint256 deployerPrivateKey = vm.envUint("DEPLOYER_PRIVATE_KEY");

        vm.startBroadcast(deployerPrivateKey);
        agentRegistry = new SignalAgentRegistry();
        taskRegistry = new SignalTaskRegistry();
        receiptRegistry = new SignalReceiptRegistry();
        vm.stopBroadcast();

        return (agentRegistry, taskRegistry, receiptRegistry);
    }
}

