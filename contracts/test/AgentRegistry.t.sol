// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Test.sol";
import "../src/AgentRegistry.sol";

contract AgentRegistryTest is Test {
    AgentRegistry public registry;
    address public operator = address(0x1);
    address public operator2 = address(0x2);

    function setUp() public {
        registry = new AgentRegistry();
    }

    function test_RegisterAgent() public {
        vm.prank(operator);
        uint256 tokenId = registry.registerAgent("TestAgent", "ipfs://test");

        assertEq(tokenId, 0);
        assertEq(registry.ownerOf(0), operator);

        AgentRegistry.AgentInfo memory info = registry.getAgent(0);
        assertEq(info.name, "TestAgent");
        assertEq(info.operator, operator);
        assertEq(info.reputationScore, 50);
        assertTrue(info.active);
    }

    function test_RecordTaskCompleted() public {
        vm.startPrank(operator);
        uint256 tokenId = registry.registerAgent("TestAgent", "ipfs://test");
        registry.recordTaskCompleted(tokenId);
        vm.stopPrank();

        AgentRegistry.AgentInfo memory info = registry.getAgent(tokenId);
        assertEq(info.tasksCompleted, 1);
        assertEq(info.reputationScore, 52); // 50 + 2
    }

    function test_RecordTaskFailed() public {
        vm.startPrank(operator);
        uint256 tokenId = registry.registerAgent("TestAgent", "ipfs://test");
        registry.recordTaskFailed(tokenId);
        vm.stopPrank();

        AgentRegistry.AgentInfo memory info = registry.getAgent(tokenId);
        assertEq(info.tasksFailed, 1);
        assertEq(info.reputationScore, 45); // 50 - 5
    }

    function test_SetTrust() public {
        vm.prank(operator);
        uint256 agent1 = registry.registerAgent("Agent1", "ipfs://1");

        vm.prank(operator2);
        uint256 agent2 = registry.registerAgent("Agent2", "ipfs://2");

        vm.prank(operator);
        registry.setTrust(agent1, agent2, 80);

        assertEq(registry.trustScores(agent1, agent2), 80);
    }

    function test_ReputationCap() public {
        vm.startPrank(operator);
        uint256 tokenId = registry.registerAgent("TestAgent", "ipfs://test");

        // Complete 30 tasks to try to exceed cap
        for (uint i = 0; i < 30; i++) {
            registry.recordTaskCompleted(tokenId);
        }
        vm.stopPrank();

        AgentRegistry.AgentInfo memory info = registry.getAgent(tokenId);
        assertEq(info.reputationScore, 100); // Capped at 100
    }

    function test_OnlyOperatorCanRecord() public {
        vm.prank(operator);
        uint256 tokenId = registry.registerAgent("TestAgent", "ipfs://test");

        vm.prank(operator2);
        vm.expectRevert("Not operator");
        registry.recordTaskCompleted(tokenId);
    }

    function test_MeetsReputationThreshold() public {
        vm.prank(operator);
        uint256 tokenId = registry.registerAgent("TestAgent", "ipfs://test");

        assertTrue(registry.meetsReputationThreshold(tokenId, 50));
        assertFalse(registry.meetsReputationThreshold(tokenId, 51));
    }

    function test_DeactivateAgent() public {
        vm.startPrank(operator);
        uint256 tokenId = registry.registerAgent("TestAgent", "ipfs://test");
        registry.deactivateAgent(tokenId);
        vm.stopPrank();

        assertFalse(registry.meetsReputationThreshold(tokenId, 0));
    }

    function test_MultipleAgentsSameOperator() public {
        vm.startPrank(operator);
        registry.registerAgent("Agent1", "ipfs://1");
        registry.registerAgent("Agent2", "ipfs://2");
        registry.registerAgent("Agent3", "ipfs://3");
        vm.stopPrank();

        uint256[] memory agentIds = registry.getOperatorAgents(operator);
        assertEq(agentIds.length, 3);
    }
}
