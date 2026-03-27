// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Script.sol";
import "../src/AgentRegistry.sol";

/**
 * @notice Deploy AgentRegistry to local Anvil and register the first agent.
 * Usage: forge script script/DeployLocal.s.sol --rpc-url http://localhost:8545 --broadcast --private-key 0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80
 */
contract DeployLocalScript is Script {
    function run() external {
        // Anvil default private key #0
        uint256 deployerPrivateKey = 0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80;

        vm.startBroadcast(deployerPrivateKey);

        AgentRegistry registry = new AgentRegistry();
        console.log("AgentRegistry deployed at:", address(registry));

        // Register AgentProof-Alpha
        uint256 tokenId = registry.registerAgent(
            "AgentProof-Alpha",
            "ipfs://QmAgentProofManifest"
        );
        console.log("Agent registered with token ID:", tokenId);

        // Complete a task to bump reputation
        registry.recordTaskCompleted(tokenId);
        console.log("Task completed, reputation updated");

        AgentRegistry.AgentInfo memory info = registry.getAgent(tokenId);
        console.log("Reputation score:", info.reputationScore);
        console.log("Tasks completed:", info.tasksCompleted);

        vm.stopBroadcast();
    }
}
