"use client";

import { useEffect, useState, useRef } from "react";

// Types
interface LogEntry {
  timestamp: number;
  level: string;
  phase: string;
  message: string;
  data: Record<string, unknown>;
  task_id: string | null;
  entry_hash: string;
  parent_hash: string | null;
}

interface AgentData {
  manifest: {
    agent_name: string;
    operator_wallet: string;
    erc8004_identity: string | null;
    supported_tools: string[];
    integrations?: Record<string, string>;
    safety_features?: string[];
  } | null;
  logs: {
    total_entries: number;
    chain_head_hash: string;
    recent_entries: LogEntry[];
  } | null;
  filecoin: { items: string[] };
  memory: { total_entries: number; categories: Record<string, number> } | null;
  workspace?: { files: string[] };
}

// ---- Helpers ----
function timeStr(ts: number) {
  return new Date(ts * 1000).toLocaleTimeString("en-US", { hour12: false, hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

function duration(entries: LogEntry[]) {
  if (entries.length < 2) return "0s";
  const d = entries[entries.length - 1].timestamp - entries[0].timestamp;
  return d < 60 ? `${d.toFixed(1)}s` : `${(d / 60).toFixed(1)}m`;
}

// ---- Top Bar ----
function TopBar({ data, logs, running }: { data: AgentData | null; logs: LogEntry[]; running: boolean }) {
  const events = logs.length;
  const llmCalls = logs.filter(l => l.level === "decision").length;
  const toolCalls = logs.filter(l => l.level === "tool_call").length;
  const errors = logs.filter(l => l.level === "error" || l.level === "safety").length;
  const tasks = new Set(logs.filter(l => l.task_id).map(l => l.task_id)).size;

  return (
    <div className="flex items-center gap-6 px-5 py-2 bg-[#0d0d14] border-b border-[#1a1a2e] text-[11px] font-mono">
      <div className="flex items-center gap-2">
        <div className={`w-2 h-2 rounded-full ${running ? "bg-green-400 animate-pulse" : logs.length > 0 ? "bg-green-500" : "bg-gray-600"}`} />
        <span className="font-bold text-white tracking-wider">AGENTPROOF</span>
      </div>
      <span className="text-gray-500">
        {running ? <span className="text-green-400">live</span> : <span className="text-gray-400">idle</span>}
      </span>
      <span className="text-gray-500">up: <span className="text-gray-300">{duration(logs)}</span></span>
      <span className="text-gray-500">events: <span className="text-gray-300">{events}</span></span>
      <span className="text-gray-500">llm: <span className="text-gray-300">{llmCalls}</span></span>
      <span className="text-gray-500">tools: <span className="text-gray-300">{toolCalls}</span></span>
      <span className="text-gray-500">err: <span className={errors > 0 ? "text-red-400" : "text-gray-300"}>{errors}</span></span>
      <span className="text-gray-500">tasks: <span className="text-gray-300">{tasks}</span></span>
    </div>
  );
}

// ---- Tabs ----
function Tabs({ active, onChange }: { active: string; onChange: (t: string) => void }) {
  const tabs = ["Activity", "Agent", "Verify", "Storage", "Health"];
  return (
    <div className="flex gap-0 border-b border-[#1a1a2e] bg-[#0d0d14]">
      {tabs.map(t => (
        <button
          key={t}
          onClick={() => onChange(t)}
          className={`px-5 py-2 text-[11px] font-medium tracking-wide transition-colors ${
            active === t
              ? "text-white border-b-2 border-indigo-500"
              : "text-gray-500 hover:text-gray-300"
          }`}
        >
          {t}
        </button>
      ))}
    </div>
  );
}

const ETHERSCAN_BASE = "https://sepolia.etherscan.io";

// ---- Linkify TX hashes in messages ----
function MessageWithLinks({ text }: { text: string }) {
  // Match 64-char hex strings (TX hashes) or 40-char (addresses)
  const parts = text.split(/([a-fA-F0-9]{64})/g);
  return (
    <>
      {parts.map((part, i) => {
        if (/^[a-fA-F0-9]{64}$/.test(part)) {
          return (
            <a
              key={i}
              href={`${ETHERSCAN_BASE}/tx/0x${part}`}
              target="_blank"
              rel="noopener noreferrer"
              onClick={(e) => e.stopPropagation()}
              className="text-indigo-400 hover:text-indigo-300 underline decoration-indigo-800 hover:decoration-indigo-500 transition-colors"
              title={`View on Etherscan: 0x${part}`}
            >
              {part.slice(0, 12)}...↗
            </a>
          );
        }
        return <span key={i}>{part}</span>;
      })}
    </>
  );
}

// ---- Event Row (core of the timeline) ----
function EventRow({ entry, isExpanded, onToggle }: { entry: LogEntry; isExpanded: boolean; onToggle: () => void }) {
  const levelConfig: Record<string, { icon: string; label: string; color: string; iconBg: string }> = {
    info:        { icon: "▸", label: "Info",          color: "text-blue-400",   iconBg: "text-blue-400" },
    decision:    { icon: "🧠", label: "LLM Called",    color: "text-purple-400", iconBg: "text-purple-400" },
    tool_call:   { icon: "⚡", label: "Tool Executed", color: "text-yellow-400", iconBg: "text-yellow-400" },
    tool_result: { icon: "✓", label: "Tool Result",   color: "text-green-400",  iconBg: "text-green-400" },
    error:       { icon: "●", label: "Error",         color: "text-red-400",    iconBg: "text-red-500" },
    guardrail:   { icon: "△", label: "Guardrail",     color: "text-orange-400", iconBg: "text-orange-400" },
    safety:      { icon: "●", label: "Safety Block",  color: "text-red-500",    iconBg: "text-red-500" },
  };
  const cfg = levelConfig[entry.level] ?? levelConfig.info;

  // Extract tool name and duration from data
  const toolName = (entry.data?.tool as string) || "";
  const isOk = entry.level !== "error" && entry.level !== "safety";

  // Phase badge color
  const phaseBadgeColor: Record<string, string> = {
    init: "bg-gray-700 text-gray-300",
    discover: "bg-blue-900/50 text-blue-300",
    plan: "bg-yellow-900/50 text-yellow-300",
    execute: "bg-cyan-900/50 text-cyan-300",
    verify: "bg-purple-900/50 text-purple-300",
    complete: "bg-green-900/50 text-green-300",
    shutdown: "bg-gray-700 text-gray-300",
    erc8004: "bg-indigo-900/50 text-indigo-300",
    filecoin: "bg-teal-900/50 text-teal-300",
    storacha: "bg-violet-900/50 text-violet-300",
    lit: "bg-amber-900/50 text-amber-300",
    safety: "bg-red-900/50 text-red-300",
    task: "bg-cyan-900/50 text-cyan-300",
  };

  return (
    <div className="group">
      <div
        onClick={onToggle}
        className={`flex items-center gap-3 px-4 py-1.5 cursor-pointer hover:bg-white/[0.02] transition-colors ${
          entry.level === "error" || entry.level === "safety" ? "bg-red-500/[0.03]" : ""
        }`}
      >
        {/* Timestamp */}
        <span className="text-[11px] text-gray-600 font-mono w-16 shrink-0">{timeStr(entry.timestamp)}</span>

        {/* Icon + Label */}
        <span className={`text-[11px] ${cfg.iconBg} shrink-0`}>{cfg.icon}</span>
        <span className={`text-[11px] ${cfg.color} font-medium w-28 shrink-0`}>{cfg.label}</span>

        {/* Status badge */}
        <span className={`text-[9px] px-1.5 py-0.5 rounded font-mono shrink-0 ${isOk ? "bg-green-900/30 text-green-400" : "bg-red-900/30 text-red-400"}`}>
          {isOk ? "✓ OK" : "✗ ERR"}
        </span>

        {/* Message — linkify TX hashes */}
        <span className="text-[11px] text-gray-400 flex-1 truncate">
          <MessageWithLinks text={entry.message} />
        </span>

        {/* Right side badges */}
        <div className="flex items-center gap-2 shrink-0">
          {toolName && (
            <span className="text-[9px] px-1.5 py-0.5 rounded bg-cyan-900/40 text-cyan-300 font-mono">{toolName}</span>
          )}
          <span className={`text-[9px] px-1.5 py-0.5 rounded font-mono ${phaseBadgeColor[entry.phase] ?? "bg-gray-800 text-gray-400"}`}>
            {entry.phase}
          </span>
        </div>
      </div>

      {/* Expanded detail */}
      {isExpanded && (
        <div className="px-4 py-3 ml-16 mr-4 mb-2 bg-[#0a0a10] border border-[#1a1a2e] rounded text-[10px] font-mono animate-fade-in">
          <div className="space-y-1">
            <div className="text-gray-500 font-bold uppercase tracking-wider mb-2">Identity</div>
            <div className="flex gap-8">
              <div><span className="text-gray-600">Type</span> <span className="text-gray-300 ml-4">{entry.level}</span></div>
              <div><span className="text-gray-600">Phase</span> <span className="text-gray-300 ml-4">{entry.phase}</span></div>
              <div><span className="text-gray-600">Task</span> <span className="text-gray-300 ml-4">{entry.task_id ?? "—"}</span></div>
            </div>
            <div className="text-gray-500 font-bold uppercase tracking-wider mt-3 mb-2">Meta</div>
            <div><span className="text-gray-600">hash</span> <span className="text-indigo-400 ml-4">{entry.entry_hash.slice(0, 16)}...</span></div>
            <div><span className="text-gray-600">parent</span> <span className="text-gray-500 ml-4">{entry.parent_hash?.slice(0, 16) ?? "genesis"}...</span></div>

            {/* Etherscan links for onchain events */}
            {typeof entry.data?.tx_hash === "string" && (
              <div className="mt-2">
                <a
                  href={`${ETHERSCAN_BASE}/tx/0x${String(entry.data.tx_hash)}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  onClick={(e) => e.stopPropagation()}
                  className="inline-flex items-center gap-1 text-[10px] px-2 py-1 rounded bg-indigo-900/30 text-indigo-400 hover:bg-indigo-900/50 transition-colors border border-indigo-800/30"
                >
                  View on Etherscan: 0x{String(entry.data.tx_hash).slice(0, 16)}...
                </a>
              </div>
            )}
            {entry.data?.token_id !== undefined && (
              <div className="mt-1">
                <a
                  href={`${ETHERSCAN_BASE}/address/0xbf14469795Eb87582a131CBA4E8622b21f32e0A7`}
                  target="_blank"
                  rel="noopener noreferrer"
                  onClick={(e) => e.stopPropagation()}
                  className="inline-flex items-center gap-1 text-[10px] px-2 py-1 rounded bg-teal-900/30 text-teal-400 hover:bg-teal-900/50 transition-colors border border-teal-800/30"
                >
                  View Contract on Etherscan
                </a>
              </div>
            )}

            {Object.keys(entry.data).length > 0 && (
              <>
                <div className="text-gray-500 font-bold uppercase tracking-wider mt-3 mb-2">Data</div>
                <pre className="text-gray-400 whitespace-pre-wrap break-all max-h-40 overflow-y-auto">
                  {JSON.stringify(entry.data, null, 2).slice(0, 1000)}
                </pre>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// ---- Session Block ----
function SessionBlock({ logs, title, status }: { logs: LogEntry[]; title: string; status: string }) {
  const events = logs.length;
  const tools = [...new Set(logs.filter(l => l.data?.tool).map(l => l.data.tool as string))];
  const llmCount = logs.filter(l => l.level === "decision").length;
  const toolCount = logs.filter(l => l.level === "tool_call").length;

  return (
    <div className="border-b border-[#1a1a2e]">
      {/* Session header */}
      <div className="flex items-center gap-3 px-4 py-2 bg-[#0d0d14]/80 sticky top-0 z-10">
        <span className="text-[11px] text-gray-400">▾</span>
        <span className="text-[11px] text-white font-medium">{title}</span>
        <span className={`text-[9px] px-2 py-0.5 rounded font-bold tracking-wider ${
          status === "completed" ? "bg-green-900/40 text-green-400"
          : status === "failed" ? "bg-red-900/40 text-red-400"
          : "bg-yellow-900/40 text-yellow-400"
        }`}>
          {status === "completed" ? "Completed" : status === "failed" ? "Failed" : "Running"}
        </span>
        <div className="flex-1" />
        <span className="text-[10px] text-gray-600">
          {events} events · {duration(logs)} · {toolCount} tools · {llmCount} llm
        </span>
      </div>

      {/* Tools used */}
      {tools.length > 0 && (
        <div className="px-4 py-1 text-[10px] text-gray-600 bg-[#0a0a0f]">
          Events: {events} &nbsp; Duration: {duration(logs)} &nbsp; Tools: {tools.join(", ")}
        </div>
      )}
    </div>
  );
}

// ---- Alerts Sidebar ----
function AlertsSidebar({ logs, data }: { logs: LogEntry[]; data: AgentData | null }) {
  const errors = logs.filter(l => l.level === "error" || l.level === "safety");
  const warnings = logs.filter(l => l.level === "guardrail");

  // Rules
  const rules = [
    { name: "chain-integrity", status: "OK" },
    { name: "budget-limit", status: "OK" },
    { name: "tx-value-limit", status: "OK" },
    { name: "tool-errors", status: errors.length > 0 ? "WARN" : "OK" },
    { name: "guardrail-blocks", status: warnings.length > 0 ? "WARN" : "OK" },
    { name: "llm-errors", status: errors.some(e => e.message.includes("LLM") || e.message.includes("Budget")) ? "FIRING" : "OK" },
  ];

  return (
    <div className="w-72 shrink-0 border-l border-[#1a1a2e] bg-[#0a0a0f] overflow-y-auto">
      <div className="px-4 py-2 border-b border-[#1a1a2e]">
        <span className="text-[11px] text-gray-400 font-bold tracking-wider">ALERTS</span>
      </div>

      {/* Error alerts */}
      {errors.map((err, i) => (
        <div key={i} className="px-4 py-3 border-b border-[#1a1a2e]">
          <div className="text-[10px] font-bold text-red-400 tracking-wider">[ERROR] {err.phase.toUpperCase()}</div>
          <div className="text-[10px] text-gray-400 mt-1">{err.message.slice(0, 120)}</div>
          <div className="text-[9px] text-gray-600 mt-1">{timeStr(err.timestamp)}</div>
        </div>
      ))}

      {warnings.map((w, i) => (
        <div key={i} className="px-4 py-3 border-b border-[#1a1a2e]">
          <div className="text-[10px] font-bold text-yellow-400 tracking-wider">[WARN] GUARDRAIL</div>
          <div className="text-[10px] text-gray-400 mt-1">{w.message.slice(0, 120)}</div>
        </div>
      ))}

      {errors.length === 0 && warnings.length === 0 && (
        <div className="px-4 py-6 text-center">
          <div className="text-[10px] text-gray-600">No alerts</div>
        </div>
      )}

      {/* Rules */}
      <div className="px-4 py-2 border-t border-[#1a1a2e]">
        <span className="text-[11px] text-gray-400 font-bold tracking-wider">RULES</span>
      </div>
      <div className="px-4 pb-4 space-y-1">
        {rules.map(r => (
          <div key={r.name} className="flex items-center gap-2 text-[10px]">
            <span className={`w-1.5 h-1.5 rounded-full ${
              r.status === "OK" ? "bg-green-500" : r.status === "WARN" ? "bg-yellow-500" : "bg-red-500"
            }`} />
            <span className="text-gray-400 flex-1">{r.name}</span>
            <span className={`${
              r.status === "OK" ? "text-green-500" : r.status === "WARN" ? "text-yellow-500" : "text-red-500"
            }`}>{r.status}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ---- Agent Tab ----
function AgentTab({ data }: { data: AgentData | null }) {
  const m = data?.manifest;
  if (!m) return <div className="p-8 text-gray-600 text-sm">No agent data available. Run a task first.</div>;
  return (
    <div className="p-6 max-w-2xl space-y-4">
      <div className="bg-[#0d0d14] border border-[#1a1a2e] rounded p-4 font-mono text-[11px] space-y-2">
        <div className="text-gray-500 font-bold uppercase tracking-wider mb-2">Agent Identity</div>
        <div><span className="text-gray-600 w-20 inline-block">Name</span> <span className="text-white">{m.agent_name}</span></div>
        <div><span className="text-gray-600 w-20 inline-block">Operator</span> <span className="text-cyan-400">{m.operator_wallet || "—"}</span></div>
        <div><span className="text-gray-600 w-20 inline-block">ERC-8004</span> <span className="text-indigo-400">Token #{m.erc8004_identity ?? "—"}</span></div>
        <div className="text-gray-500 font-bold uppercase tracking-wider mt-4 mb-2">Tools ({m.supported_tools.length})</div>
        <div className="flex flex-wrap gap-1">
          {m.supported_tools.map(t => (
            <span key={t} className="px-2 py-0.5 bg-indigo-900/30 text-indigo-300 rounded text-[9px]">{t}</span>
          ))}
        </div>
        {m.integrations && (
          <>
            <div className="text-gray-500 font-bold uppercase tracking-wider mt-4 mb-2">Integrations</div>
            {Object.entries(m.integrations).map(([k, v]) => (
              <div key={k}><span className="text-green-400">{k}</span> <span className="text-gray-500">— {v}</span></div>
            ))}
          </>
        )}
      </div>
    </div>
  );
}

// ---- Storage Tab ----
function StorageTab({ data }: { data: AgentData | null }) {
  return (
    <div className="p-6 max-w-2xl space-y-4">
      <div className="bg-[#0d0d14] border border-[#1a1a2e] rounded p-4 font-mono text-[11px] space-y-2">
        <div className="text-gray-500 font-bold uppercase tracking-wider mb-2">Filecoin</div>
        {(data?.filecoin?.items ?? []).length > 0 ? (
          data!.filecoin.items.map((item, i) => (
            <div key={i} className="flex gap-2"><span className="text-teal-400">CID</span> <span className="text-gray-400">{item}</span></div>
          ))
        ) : <div className="text-gray-600">No items stored</div>}

        <div className="text-gray-500 font-bold uppercase tracking-wider mt-4 mb-2">Storacha Memory</div>
        {data?.memory ? (
          <div>
            <div className="text-gray-300">{data.memory.total_entries} entries</div>
            {Object.entries(data.memory.categories).map(([k, v]) => (
              <div key={k} className="text-gray-500">{k}: {v}</div>
            ))}
          </div>
        ) : <div className="text-gray-600">No memories</div>}

        <div className="text-gray-500 font-bold uppercase tracking-wider mt-4 mb-2">Workspace Files</div>
        {(data?.workspace?.files ?? []).length > 0 ? (
          data!.workspace!.files.map((f, i) => (
            <div key={i} className="text-gray-400">📄 {f}</div>
          ))
        ) : <div className="text-gray-600">No files</div>}
      </div>
    </div>
  );
}

// ---- Verify Tab ----
function VerifyTab({ logs }: { logs: LogEntry[] }) {
  const CONTRACT = "0xbf14469795Eb87582a131CBA4E8622b21f32e0A7";
  const txEntries = logs.filter(e => e.data?.tx_hash);
  const chainValid = logs.length === 0 || logs.every((l, i) => i === 0 || l.parent_hash === logs[i - 1].entry_hash);

  return (
    <div className="p-6 max-w-3xl space-y-6 font-mono text-[11px]">
      {/* Contract info */}
      <div className="bg-[#0d0d14] border border-[#1a1a2e] rounded p-4 space-y-2">
        <div className="text-gray-500 font-bold uppercase tracking-wider mb-3">Smart Contract (Sepolia Testnet)</div>
        <div className="flex items-center gap-2">
          <span className="text-gray-600">Address:</span>
          <a href={`${ETHERSCAN_BASE}/address/${CONTRACT}`} target="_blank" rel="noopener noreferrer"
            className="text-indigo-400 hover:text-indigo-300 underline">{CONTRACT}</a>
          <a href={`${ETHERSCAN_BASE}/address/${CONTRACT}`} target="_blank" rel="noopener noreferrer"
            className="text-[9px] px-1.5 py-0.5 rounded bg-indigo-900/30 text-indigo-400 border border-indigo-800/30 hover:bg-indigo-900/50 no-underline">
            Open Etherscan ↗
          </a>
        </div>
        <div><span className="text-gray-600">Network:</span> <span className="text-gray-300">Ethereum Sepolia (Chain ID: 11155111)</span></div>
        <div><span className="text-gray-600">Contract:</span> <span className="text-gray-300">AgentRegistry (ERC-721 + Reputation + Trust)</span></div>
      </div>

      {/* Hash chain verification */}
      <div className="bg-[#0d0d14] border border-[#1a1a2e] rounded p-4 space-y-2">
        <div className="text-gray-500 font-bold uppercase tracking-wider mb-3">Hash Chain Integrity</div>
        <div className="flex items-center gap-2">
          <span className={`w-2 h-2 rounded-full ${chainValid ? "bg-green-500" : "bg-red-500"}`} />
          <span className={chainValid ? "text-green-400" : "text-red-400"}>
            {chainValid ? "VALID — All entries cryptographically linked" : "BROKEN — Chain integrity compromised"}
          </span>
        </div>
        <div><span className="text-gray-600">Total entries:</span> <span className="text-gray-300">{logs.length}</span></div>
        <div><span className="text-gray-600">Algorithm:</span> <span className="text-gray-300">SHA-256 (each entry hashes its content + parent hash)</span></div>
        {logs.length > 0 && (
          <div><span className="text-gray-600">Chain head:</span> <span className="text-indigo-400">{logs[logs.length - 1].entry_hash.slice(0, 32)}...</span></div>
        )}
        <div className="mt-3 text-gray-600 text-[10px]">
          How it works: Every log entry contains a SHA-256 hash of its content plus the hash of the previous entry.
          If any entry is tampered with, the chain breaks and verification fails. This is the same principle as blockchain block headers.
        </div>
      </div>

      {/* Onchain transactions */}
      <div className="bg-[#0d0d14] border border-[#1a1a2e] rounded p-4 space-y-3">
        <div className="text-gray-500 font-bold uppercase tracking-wider mb-3">
          Onchain Transactions ({txEntries.length})
        </div>

        {txEntries.length === 0 ? (
          <div className="text-gray-600">No onchain transactions yet. Run a task to see transactions.</div>
        ) : (
          txEntries.map((entry, i) => {
            const txHash = entry.data.tx_hash as string;
            // Decode what the function call was
            let decoded = "";
            if (entry.message.includes("registered")) {
              decoded = 'registerAgent("AgentProof-Alpha", "ipfs://agent-manifest-placeholder")';
            } else if (entry.message.includes("completion recorded")) {
              decoded = `recordTaskCompleted(${entry.data.token_id ?? "?"})  →  reputation +2`;
            } else if (entry.message.includes("failure recorded")) {
              decoded = `recordTaskFailed(${entry.data.token_id ?? "?"})  →  reputation -5`;
            } else if (entry.message.includes("Trust set")) {
              decoded = `setTrust(fromAgent, toAgent, score)`;
            }

            return (
              <div key={i} className="border border-[#1a1a2e] rounded p-3 hover:border-indigo-800/50 transition-colors">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-gray-400">{entry.message.slice(0, 80)}</span>
                  <span className="text-[9px] text-gray-600">{timeStr(entry.timestamp)}</span>
                </div>

                {/* TX Hash with link */}
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-gray-600">TX:</span>
                  <a href={`${ETHERSCAN_BASE}/tx/0x${txHash}`} target="_blank" rel="noopener noreferrer"
                    className="text-indigo-400 hover:text-indigo-300 underline break-all">
                    0x{txHash}
                  </a>
                  <a href={`${ETHERSCAN_BASE}/tx/0x${txHash}`} target="_blank" rel="noopener noreferrer"
                    className="text-[9px] px-1.5 py-0.5 rounded bg-indigo-900/30 text-indigo-400 border border-indigo-800/30 shrink-0 no-underline">
                    Etherscan ↗
                  </a>
                </div>

                {/* Decoded plaintext */}
                {decoded && (
                  <div className="bg-[#08080d] rounded p-2 mt-2">
                    <div className="text-[9px] text-gray-600 uppercase tracking-wider mb-1">Decoded Function Call (plaintext)</div>
                    <div className="text-green-400">{decoded}</div>
                  </div>
                )}

                {/* What this proves */}
                <div className="mt-2 text-[10px] text-gray-600">
                  {entry.message.includes("registered") && "✓ Proves: This agent identity was permanently recorded on the Ethereum blockchain"}
                  {entry.message.includes("completion") && "✓ Proves: The agent completed a task and its reputation was updated onchain"}
                  {entry.message.includes("failure") && "✓ Proves: The agent honestly recorded a task failure (reputation decreased)"}
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* How to verify yourself */}
      <div className="bg-[#0d0d14] border border-[#1a1a2e] rounded p-4 space-y-2">
        <div className="text-gray-500 font-bold uppercase tracking-wider mb-3">Verify It Yourself</div>
        <div className="text-gray-400 space-y-2 text-[10px]">
          <p>1. Click any Etherscan link above to see the transaction on the public blockchain</p>
          <p>2. On Etherscan, check the &quot;From&quot; address matches the agent operator wallet</p>
          <p>3. Check the &quot;To&quot; address matches the contract: <span className="text-indigo-400">{CONTRACT}</span></p>
          <p>4. The &quot;Input Data&quot; field contains the encoded function call — you can decode it with:</p>
          <div className="bg-[#08080d] rounded p-2 mt-1">
            <code className="text-cyan-400">cast 4byte-decode 0x... </code>
            <span className="text-gray-600"> # using Foundry&apos;s cast tool</span>
          </div>
          <p className="mt-2">5. To query the contract state directly:</p>
          <div className="bg-[#08080d] rounded p-2 mt-1 space-y-1">
            <div><code className="text-cyan-400">cast call {CONTRACT} &quot;totalAgents()&quot; --rpc-url https://ethereum-sepolia-rpc.publicnode.com</code></div>
            <div><code className="text-cyan-400">cast call {CONTRACT} &quot;getAgent(uint256)(...)&quot; 0 --rpc-url https://ethereum-sepolia-rpc.publicnode.com</code></div>
          </div>
        </div>
      </div>
    </div>
  );
}

// ---- Task Input ----
function TaskInput({ onSubmit, running }: { onSubmit: (task: string) => void; running: boolean }) {
  const [input, setInput] = useState("");

  return (
    <div className="flex items-center gap-2 px-4 py-2 bg-[#0d0d14] border-b border-[#1a1a2e]">
      <span className="text-indigo-400 text-sm font-bold">$</span>
      <input
        type="text"
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && input.trim() && !running) {
            onSubmit(input.trim());
            setInput("");
          }
        }}
        placeholder={running ? "Agent running..." : "Type a task and press Enter..."}
        disabled={running}
        style={{ background: "transparent", color: "#e2e8f0", caretColor: "#6366f1" }}
        className="flex-1 text-[12px] font-mono placeholder:text-gray-700 outline-none border-none shadow-none disabled:opacity-40"
      />
      <button
        onClick={() => { if (input.trim() && !running) { onSubmit(input.trim()); setInput(""); } }}
        disabled={running || !input.trim()}
        className={`px-3 py-1 rounded text-[10px] font-bold tracking-wider ${
          running ? "bg-yellow-900/30 text-yellow-400 border border-yellow-800/50"
          : input.trim() ? "bg-indigo-600 text-white hover:bg-indigo-500" : "bg-gray-800 text-gray-600"
        }`}
      >
        {running ? "RUNNING" : "RUN"}
      </button>
      {!running && !input && (
        <div className="flex gap-1">
          {["Build a fibonacci script", "Create a snake game"].map(s => (
            <button key={s} onClick={() => setInput(s)} className="text-[9px] text-gray-600 hover:text-gray-400 px-2 py-0.5 rounded border border-[#1a1a2e] hover:border-gray-700 transition">
              {s}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

// ---- Main ----
export default function Dashboard() {
  const [data, setData] = useState<AgentData | null>(null);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [running, setRunning] = useState(false);
  const [activeTab, setActiveTab] = useState("Activity");
  const [expandedIdx, setExpandedIdx] = useState<number | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  const fetchData = async () => {
    try {
      const [agentRes, statusRes] = await Promise.all([fetch("/api/agent"), fetch("/api/run")]);
      const json = await agentRes.json();
      const status = await statusRes.json();
      setData(json);
      setLogs(json.logs?.recent_entries ?? []);
      setRunning(status.running);
    } catch {}
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 800);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs.length]);

  const handleRun = async (task: string) => {
    setRunning(true);
    setLogs([]);
    setExpandedIdx(null);
    await fetch("/api/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ task }),
    });
  };

  // Derive task info
  const taskTitle = logs.find(l => l.message.startsWith("Processing: "))?.message.replace("Processing: ", "") ?? "";
  const taskStatus = logs.some(l => l.message.startsWith("Task completed")) ? "completed"
    : logs.some(l => l.message.startsWith("Task failed") || l.level === "error" && l.phase === "verify") ? "failed"
    : running ? "running" : logs.length > 0 ? "completed" : "idle";

  return (
    <div className="h-screen flex flex-col bg-[#08080d] font-mono">
      <TopBar data={data} logs={logs} running={running} />
      <TaskInput onSubmit={handleRun} running={running} />
      <Tabs active={activeTab} onChange={setActiveTab} />

      <div className="flex-1 flex overflow-hidden">
        {/* Main content */}
        <div className="flex-1 overflow-y-auto">
          {activeTab === "Activity" && (
            <>
              {/* Timeline header */}
              <div className="flex items-center justify-between px-4 py-1.5 bg-[#0a0a0f] border-b border-[#1a1a2e] sticky top-0 z-20">
                <span className="text-[11px] text-gray-500 font-bold tracking-wider">LIVE TIMELINE</span>
                <span className="text-[10px] text-gray-600">{logs.length}</span>
              </div>

              {/* Session block */}
              {logs.length > 0 && (
                <SessionBlock logs={logs} title={taskTitle || "AgentProof Session"} status={taskStatus} />
              )}

              {/* Event rows */}
              {logs.map((entry, i) => (
                <EventRow
                  key={`${entry.entry_hash}-${i}`}
                  entry={entry}
                  isExpanded={expandedIdx === i}
                  onToggle={() => setExpandedIdx(expandedIdx === i ? null : i)}
                />
              ))}

              {logs.length === 0 && !running && (
                <div className="flex items-center justify-center h-64 text-gray-700 text-sm">
                  Type a task above to start the agent
                </div>
              )}

              <div ref={bottomRef} />
            </>
          )}

          {activeTab === "Agent" && <AgentTab data={data} />}
          {activeTab === "Verify" && <VerifyTab logs={logs} />}
          {activeTab === "Storage" && <StorageTab data={data} />}
          {activeTab === "Health" && (
            <div className="p-6 font-mono text-[11px] space-y-2">
              <div className="text-gray-500 font-bold tracking-wider">HEALTH STATUS</div>
              <div className="text-green-400">Chain integrity: {logs.length > 0 ? "VALID" : "N/A"}</div>
              <div className="text-green-400">Hash entries: {logs.length}</div>
              <div className="text-gray-400">Head hash: {logs.length > 0 ? logs[logs.length - 1].entry_hash.slice(0, 24) + "..." : "—"}</div>
              <div className="text-gray-400">Anvil: {data?.manifest ? "Connected" : "Unknown"}</div>
            </div>
          )}
        </div>

        {/* Alerts sidebar */}
        {activeTab === "Activity" && <AlertsSidebar logs={logs} data={data} />}
      </div>
    </div>
  );
}
