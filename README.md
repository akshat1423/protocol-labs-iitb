# AgentProof

**Verifiable Autonomous AI Agent with Onchain Identity**

AgentProof is an autonomous AI agent that operates with a verifiable onchain identity (ERC-8004), produces cryptographic hash-chained execution logs, stores persistent state on decentralized storage, and manages funds through programmable wallet guardrails — all without human intervention.

## Architecture

```
┌─────────────────────────────────────────────────┐
│            AgentProof Dashboard (Next.js)         │
│     Real-time activity feed + kill switch          │
└────────────────────┬────────────────────────────┘
                     │ WebSocket
┌────────────────────▼────────────────────────────┐
│            Agent Orchestrator (Python)             │
│   ┌──────────┐ ┌────────┐ ┌──────────────────┐   │
│   │ Discovery │→│Planner │→│ Executor (8 tools)│  │
│   └──────────┘ └────────┘ └──────────────────┘   │
│   ┌──────────┐ ┌────────┐ ┌──────────────────┐   │
│   │ Verifier │ │Guardrail│ │ Hash-Chain Logger│   │
│   └──────────┘ └────────┘ └──────────────────┘   │
└──┬───────┬──────────┬────────────┬──────────────┘
   │       │          │            │
   ▼       ▼          ▼            ▼
ERC-8004  Lit       Filecoin    Storacha
Identity  Wallet    State       Memory
```

## Sponsor Technologies

| Sponsor | Technology | Integration |
|---------|-----------|-------------|
| **Ethereum Foundation** | ERC-8004 | Onchain agent identity, reputation tracking, inter-agent trust scores |
| **Filecoin Foundation** | Synapse SDK | Agent state + execution log storage on Calibration Testnet |
| **Storacha** | Storacha | Persistent agent memory across sessions and devices |
| **Lit Protocol** | Vincent API | Non-custodial wallet with programmable tx guardrails |

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- Foundry (auto-installed via `foundryup`)

### Setup

```bash
# Clone and enter project
cd agentproof

# Set up Python environment
cd agent && python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt && cd ..

# Set up dashboard
cd dashboard && npm install && cd ..

# Install Foundry (if needed)
curl -L https://foundry.paradigm.xyz | bash && foundryup

# Install contract dependencies
cd contracts && forge install OpenZeppelin/openzeppelin-contracts && cd ..
```

### Run Demo (No API Keys Needed)

```bash
./run.sh demo
```

### Full Setup with Local Blockchain

```bash
# Terminal 1: Start local testnet
./run.sh anvil

# Terminal 2: Deploy contracts
./run.sh deploy

# Terminal 3: Run integration tests
./run.sh test

# Terminal 4: Run multi-agent demo
./run.sh multi

# Terminal 5: Start dashboard
./run.sh dashboard
```

### Run with Real Claude API

```bash
cp agent/.env.example agent/.env
# Edit agent/.env with your ANTHROPIC_API_KEY
./run.sh run "Build a smart contract that tracks carbon credits"
```

## Features

### Autonomous Agent Loop
- **Discover** — Identifies tasks from data sources autonomously
- **Plan** — LLM-powered task decomposition into actionable steps
- **Execute** — Multi-tool orchestration (8 tools: GitHub, code, web, blockchain, Filecoin, Storacha, identity, wallet)
- **Verify** — Self-validates outputs before marking complete
- **Record** — Updates onchain reputation based on outcomes

### Verifiable Execution
- SHA-256 hash-chained execution logs (`agent_log.json`)
- Every decision, tool call, and result is logged with cryptographic linkage
- Chain integrity verifiable at any time

### Safety & Guardrails
- Compute budget enforcement (USD + API call limits)
- Transaction value limits (configurable per-agent)
- Dangerous command blocking
- System path protection
- Kill switch (pause/resume via dashboard or API)
- Daily transaction caps via Lit Protocol

### Multi-Agent Trust
- Agents register ERC-8004 identities onchain
- Evaluator agents review and rate builder agents
- Trust scores stored onchain and queryable
- Trust-gated collaboration (only interact with agents above threshold)

## Project Structure

```
agentproof/
├── agent/                    # Python autonomous agent
│   ├── core/
│   │   ├── agent.py          # Main autonomous loop
│   │   ├── runner.py          # Unified builder (wires all integrations)
│   │   ├── guardrails.py      # Safety checks + kill switch
│   │   ├── logger.py          # Hash-chained execution logger
│   │   ├── llm.py             # Claude/OpenAI LLM client
│   │   ├── models.py          # Data models (Task, LogEntry, Budget)
│   │   ├── server.py          # WebSocket server for dashboard
│   │   ├── demo.py            # Demo with mock LLM
│   │   ├── multi_agent_demo.py # Multi-agent trust demo
│   │   └── integration_test.py # Full integration test suite
│   ├── integrations/
│   │   ├── erc8004.py         # ERC-8004 onchain identity
│   │   ├── filecoin_storage.py # Filecoin state persistence
│   │   ├── storacha_memory.py  # Persistent agent memory
│   │   └── lit_wallet.py       # Lit Protocol wallet
│   └── tools/
│       ├── github_tool.py     # GitHub API operations
│       ├── code_tool.py       # Code generation + execution
│       ├── web_tool.py        # HTTP fetch operations
│       └── blockchain_tool.py # Onchain read/write
├── contracts/                 # Solidity smart contracts
│   ├── src/AgentRegistry.sol  # ERC-721 agent identity + reputation + trust
│   ├── test/AgentRegistry.t.sol # 9 passing tests
│   └── script/                # Deployment scripts
├── dashboard/                 # Next.js real-time monitoring
│   └── src/
│       ├── app/page.tsx       # Main dashboard
│       ├── components/        # StatusBar, IdentityPanel, LogViewer, TaskList
│       └── hooks/             # WebSocket hook
├── agent.json                 # DevSpot Agent Manifest
├── run.sh                     # Quick start script
└── README.md
```

## Hackathon Tracks

- **Agent Only: Let the Agent Cook** — Fully autonomous agent with ERC-8004 identity
- **Agents With Receipts (ERC-8004)** — Onchain trust framework for agent coordination
- **AI & Robotics** — Verifiable AI with human oversight
- **Filecoin** — Decentralized state storage via Synapse SDK
- **Lit Protocol: NextGen AI Apps** — Vincent-powered agent wallet
- **Storacha** — Persistent agent memory
- **Infrastructure & Digital Rights** — Data ownership and verifiable computation
- **Community Vote Bounty** — Vote for us!

## License
MIT
