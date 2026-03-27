// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Script.sol";
import "../src/AgentRegistry.sol";

contract DeployScript is Script {
    function run() external {
        uint256 deployerPrivateKey = vm.envUint("OPERATOR_PRIVATE_KEY");

        vm.startBroadcast(deployerPrivateKey);

        AgentRegistry registry = new AgentRegistry();
        console.log("AgentRegistry deployed at:", address(registry));

        // Register the first agent
        uint256 tokenId = registry.registerAgent(
            "AgentProof-Alpha",
            "ipfs://agent-manifest-placeholder"
        );
        console.log("Agent registered with token ID:", tokenId);

        vm.stopBroadcast();
    }
}
