// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

/**
 * @title AgentRegistry (ERC-8004 Compatible)
 * @notice Onchain identity registry for autonomous AI agents.
 * Each agent is represented as an ERC-721 token with metadata,
 * reputation scores, and operator linkage.
 */
contract AgentRegistry is ERC721, Ownable {
    uint256 private _nextTokenId;

    struct AgentInfo {
        string name;
        address operator;
        string metadataURI;  // Points to agent.json on IPFS/Filecoin
        uint256 reputationScore;
        uint256 tasksCompleted;
        uint256 tasksFailed;
        uint256 registeredAt;
        bool active;
    }

    // tokenId => AgentInfo
    mapping(uint256 => AgentInfo) public agents;

    // operator => tokenIds
    mapping(address => uint256[]) public operatorAgents;

    // Agent trust: agentA => agentB => trust score (0-100)
    mapping(uint256 => mapping(uint256 => uint8)) public trustScores;

    // Validation records: agentId => validator => attestation hash
    mapping(uint256 => mapping(address => bytes32)) public validations;

    event AgentRegistered(uint256 indexed tokenId, string name, address indexed operator);
    event ReputationUpdated(uint256 indexed tokenId, uint256 newScore);
    event TrustUpdated(uint256 indexed fromAgent, uint256 indexed toAgent, uint8 score);
    event TaskCompleted(uint256 indexed tokenId, uint256 totalCompleted);
    event TaskFailed(uint256 indexed tokenId, uint256 totalFailed);
    event AgentValidated(uint256 indexed tokenId, address indexed validator, bytes32 attestation);
    event MetadataUpdated(uint256 indexed tokenId, string newURI);

    constructor() ERC721("AgentProof Identity", "AGENTID") Ownable(msg.sender) {}

    /**
     * @notice Register a new agent identity
     * @param name Human-readable agent name
     * @param metadataURI URI pointing to agent.json manifest
     */
    function registerAgent(
        string calldata name,
        string calldata metadataURI
    ) external returns (uint256) {
        uint256 tokenId = _nextTokenId++;
        _safeMint(msg.sender, tokenId);

        agents[tokenId] = AgentInfo({
            name: name,
            operator: msg.sender,
            metadataURI: metadataURI,
            reputationScore: 50,  // Start at neutral reputation
            tasksCompleted: 0,
            tasksFailed: 0,
            registeredAt: block.timestamp,
            active: true
        });

        operatorAgents[msg.sender].push(tokenId);

        emit AgentRegistered(tokenId, name, msg.sender);
        return tokenId;
    }

    /**
     * @notice Record a completed task (increases reputation)
     */
    function recordTaskCompleted(uint256 tokenId) external {
        require(_isOperator(tokenId, msg.sender), "Not operator");
        agents[tokenId].tasksCompleted++;

        // Increase reputation (capped at 100)
        uint256 newRep = agents[tokenId].reputationScore + 2;
        if (newRep > 100) newRep = 100;
        agents[tokenId].reputationScore = newRep;

        emit TaskCompleted(tokenId, agents[tokenId].tasksCompleted);
        emit ReputationUpdated(tokenId, newRep);
    }

    /**
     * @notice Record a failed task (decreases reputation)
     */
    function recordTaskFailed(uint256 tokenId) external {
        require(_isOperator(tokenId, msg.sender), "Not operator");
        agents[tokenId].tasksFailed++;

        // Decrease reputation (floor at 0)
        uint256 rep = agents[tokenId].reputationScore;
        uint256 newRep = rep > 5 ? rep - 5 : 0;
        agents[tokenId].reputationScore = newRep;

        emit TaskFailed(tokenId, agents[tokenId].tasksFailed);
        emit ReputationUpdated(tokenId, newRep);
    }

    /**
     * @notice Set trust score from one agent to another
     * @param fromAgent The evaluating agent
     * @param toAgent The agent being evaluated
     * @param score Trust score 0-100
     */
    function setTrust(uint256 fromAgent, uint256 toAgent, uint8 score) external {
        require(_isOperator(fromAgent, msg.sender), "Not operator of fromAgent");
        require(score <= 100, "Score must be 0-100");
        require(fromAgent != toAgent, "Cannot self-trust");

        trustScores[fromAgent][toAgent] = score;
        emit TrustUpdated(fromAgent, toAgent, score);
    }

    /**
     * @notice Third-party validation of agent capabilities
     */
    function validateAgent(uint256 tokenId, bytes32 attestation) external {
        validations[tokenId][msg.sender] = attestation;
        emit AgentValidated(tokenId, msg.sender, attestation);
    }

    /**
     * @notice Update agent metadata URI
     */
    function updateMetadata(uint256 tokenId, string calldata newURI) external {
        require(_isOperator(tokenId, msg.sender), "Not operator");
        agents[tokenId].metadataURI = newURI;
        emit MetadataUpdated(tokenId, newURI);
    }

    /**
     * @notice Deactivate an agent
     */
    function deactivateAgent(uint256 tokenId) external {
        require(_isOperator(tokenId, msg.sender), "Not operator");
        agents[tokenId].active = false;
    }

    /**
     * @notice Get full agent info
     */
    function getAgent(uint256 tokenId) external view returns (AgentInfo memory) {
        return agents[tokenId];
    }

    /**
     * @notice Get all agents for an operator
     */
    function getOperatorAgents(address operator) external view returns (uint256[] memory) {
        return operatorAgents[operator];
    }

    /**
     * @notice Check if an agent meets a minimum reputation threshold
     */
    function meetsReputationThreshold(uint256 tokenId, uint256 minScore) external view returns (bool) {
        return agents[tokenId].reputationScore >= minScore && agents[tokenId].active;
    }

    function _isOperator(uint256 tokenId, address addr) internal view returns (bool) {
        return agents[tokenId].operator == addr;
    }

    function totalAgents() external view returns (uint256) {
        return _nextTokenId;
    }
}
