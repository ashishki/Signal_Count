// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {SignalReputationVault} from "../src/SignalReputationVault.sol";

interface Vm {
    function envUint(string calldata name) external returns (uint256);
    function startBroadcast(uint256 privateKey) external;
    function stopBroadcast() external;
}

contract DeployReputationVault {
    uint256 private constant GENSYN_TESTNET_CHAIN_ID = 685685;
    Vm private constant vm =
        Vm(address(uint160(uint256(keccak256("hevm cheat code")))));

    SignalReputationVault public reputationVault;

    function run() external returns (SignalReputationVault deployedReputationVault) {
        require(
            block.chainid == GENSYN_TESTNET_CHAIN_ID,
            "wrong Gensyn Testnet chain id"
        );

        uint256 deployerPrivateKey = vm.envUint("DEPLOYER_PRIVATE_KEY");

        vm.startBroadcast(deployerPrivateKey);
        reputationVault = new SignalReputationVault();
        vm.stopBroadcast();

        return reputationVault;
    }
}
