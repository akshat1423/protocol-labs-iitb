#!/bin/bash
# AgentProof — Quick Start Script
# Usage: ./run.sh [demo|test|multi|dashboard|anvil|deploy]

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Colors
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
NC='\033[0m'

case "${1:-demo}" in
  demo)
    echo -e "${CYAN}Running AgentProof Demo (mock LLM, no API keys needed)${NC}"
    source agent/venv/bin/activate
    python -m agent.core.demo
    ;;

  test)
    echo -e "${CYAN}Running Integration Tests (requires Anvil on localhost:8545)${NC}"
    source agent/venv/bin/activate
    python -m agent.core.integration_test
    ;;

  multi)
    echo -e "${CYAN}Running Multi-Agent Trust Demo (requires Anvil on localhost:8545)${NC}"
    source agent/venv/bin/activate
    python -m agent.core.multi_agent_demo
    ;;

  dashboard)
    echo -e "${CYAN}Starting Dashboard (http://localhost:3000)${NC}"
    cd dashboard && npm run dev
    ;;

  anvil)
    echo -e "${CYAN}Starting Local Anvil Testnet${NC}"
    source ~/.zshenv 2>/dev/null || true
    anvil --port 8545
    ;;

  deploy)
    echo -e "${CYAN}Deploying AgentRegistry to local Anvil${NC}"
    source ~/.zshenv 2>/dev/null || true
    cd contracts
    forge script script/DeployLocal.s.sol \
      --rpc-url http://localhost:8545 \
      --broadcast \
      --private-key 0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80
    ;;

  contracts-test)
    echo -e "${CYAN}Running Solidity Tests${NC}"
    source ~/.zshenv 2>/dev/null || true
    cd contracts && forge test -vv
    ;;

  gemini)
    echo -e "${CYAN}Running AgentProof with Gemini API${NC}"
    source agent/venv/bin/activate
    python -m agent.core.run_gemini --task "${2:-}"
    ;;

  run)
    echo -e "${CYAN}Running AgentProof with Gemini (default LLM)${NC}"
    source agent/venv/bin/activate
    python -m agent.core.run_gemini --task "${2:-}"
    ;;

  *)
    echo -e "${YELLOW}AgentProof — Verifiable Autonomous AI Agent${NC}"
    echo ""
    echo "Usage: ./run.sh <command>"
    echo ""
    echo "Commands:"
    echo "  demo           Run demo with mock LLM (default)"
    echo "  gemini [task]  Run with Gemini API (needs GEMINI_API_KEY)"
    echo "  run [task]     Same as gemini"
    echo "  test           Run integration tests (needs Anvil)"
    echo "  multi          Run multi-agent trust demo (needs Anvil)"
    echo "  dashboard      Start Next.js dashboard"
    echo "  anvil          Start local Anvil testnet"
    echo "  deploy         Deploy contracts to Anvil"
    echo "  contracts-test Run Solidity tests"
    ;;
esac
