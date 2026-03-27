"use client";

interface IdentityPanelProps {
  identity: {
    agent_name: string;
    operator_wallet: string;
    erc8004_identity: string | null;
    supported_tools: string[];
  } | null;
  budget: {
    spent_usd: number;
    max_usd: number;
    llm_calls: string;
    tool_calls: string;
    budget_remaining_pct: number;
  } | null;
}

export function IdentityPanel({ identity, budget }: IdentityPanelProps) {
  return (
    <div className="bg-agent-card border border-agent-border rounded-lg p-4">
      <h2 className="text-sm font-semibold text-gray-400 mb-3">AGENT IDENTITY</h2>

      {identity && (
        <div className="space-y-2">
          <div>
            <span className="text-xs text-gray-500">Name</span>
            <p className="text-sm text-white">{identity.agent_name}</p>
          </div>
          <div>
            <span className="text-xs text-gray-500">Operator</span>
            <p className="text-xs text-agent-cyan font-mono truncate">
              {identity.operator_wallet || "Not connected"}
            </p>
          </div>
          <div>
            <span className="text-xs text-gray-500">ERC-8004 ID</span>
            <p className="text-xs text-agent-accent font-mono">
              {identity.erc8004_identity ?? "Not registered"}
            </p>
          </div>
          <div>
            <span className="text-xs text-gray-500">Tools</span>
            <div className="flex flex-wrap gap-1 mt-1">
              {identity.supported_tools.map((tool) => (
                <span key={tool} className="px-2 py-0.5 text-xs bg-agent-accent/10 text-agent-accent rounded">
                  {tool}
                </span>
              ))}
            </div>
          </div>
        </div>
      )}

      {budget && (
        <div className="mt-4 pt-3 border-t border-agent-border">
          <h3 className="text-xs font-semibold text-gray-400 mb-2">COMPUTE BUDGET</h3>
          <div className="space-y-2">
            <div>
              <div className="flex justify-between text-xs mb-1">
                <span className="text-gray-500">Spent</span>
                <span className="text-white">${budget.spent_usd} / ${budget.max_usd}</span>
              </div>
              <div className="h-1.5 bg-agent-border rounded-full overflow-hidden">
                <div
                  className="h-full bg-agent-accent rounded-full transition-all"
                  style={{ width: `${100 - budget.budget_remaining_pct}%` }}
                />
              </div>
            </div>
            <div className="flex justify-between text-xs">
              <span className="text-gray-500">LLM Calls</span>
              <span className="text-gray-300">{budget.llm_calls}</span>
            </div>
            <div className="flex justify-between text-xs">
              <span className="text-gray-500">Tool Calls</span>
              <span className="text-gray-300">{budget.tool_calls}</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
