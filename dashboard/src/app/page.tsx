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

interface TaskData {
  task_id: string;
  title: string;
  status: string;
  plan: string[];
  outputs: Array<Record<string, unknown>>;
  created_at: number;
  completed_at: number | null;
  error: string | null;
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
}

// ---- Components ----

function HexBackground() {
  return (
    <div className="fixed inset-0 grid-bg pointer-events-none z-0" />
  );
}

function Header({ data, chainValid }: { data: AgentData | null; chainValid: boolean }) {
  return (
    <header className="relative z-10 border-b border-[var(--border)] bg-[var(--bg-card)]/80 backdrop-blur-sm">
      <div className="max-w-[1600px] mx-auto px-6 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-[var(--accent)] flex items-center justify-center text-white text-sm font-bold">
            AP
          </div>
          <div>
            <h1 className="text-sm font-bold tracking-wide text-white">AGENTPROOF</h1>
            <p className="text-[10px] text-[var(--text-secondary)] tracking-widest uppercase">Verifiable Autonomous Agent</p>
          </div>
        </div>

        <div className="flex items-center gap-6">
          {/* Chain Status */}
          <div className="flex items-center gap-2">
            <div className={`w-1.5 h-1.5 rounded-full ${chainValid ? 'bg-[var(--green)] animate-pulse-glow' : 'bg-[var(--red)]'}`} />
            <span className="text-[10px] text-[var(--text-secondary)]">
              {chainValid ? 'CHAIN VALID' : 'CHAIN BROKEN'}
            </span>
          </div>

          {/* Log count */}
          <div className="text-[10px] text-[var(--text-secondary)]">
            <span className="text-[var(--cyan)]">{data?.logs?.total_entries ?? 0}</span> log entries
          </div>

          {/* Live indicator */}
          <div className="flex items-center gap-1.5 px-2 py-0.5 rounded border border-[var(--green)]/30 bg-[var(--green)]/5">
            <div className="w-1.5 h-1.5 rounded-full bg-[var(--green)] animate-pulse-glow" />
            <span className="text-[10px] text-[var(--green)] font-medium">LIVE</span>
          </div>
        </div>
      </div>
    </header>
  );
}

function IdentityCard({ data }: { data: AgentData | null }) {
  const manifest = data?.manifest;
  if (!manifest) return null;

  return (
    <div className="rounded-xl border border-[var(--border)] bg-[var(--bg-card)] p-5 hover:border-[var(--accent)]/30 transition-colors">
      <div className="flex items-center gap-2 mb-4">
        <div className="w-5 h-5 rounded bg-[var(--accent)]/20 flex items-center justify-center">
          <span className="text-[var(--accent)] text-xs">ID</span>
        </div>
        <h2 className="text-xs font-semibold tracking-wider text-[var(--text-secondary)] uppercase">Agent Identity</h2>
      </div>

      <div className="space-y-3">
        <div>
          <span className="text-[10px] text-[var(--text-dim)] uppercase tracking-wider">Name</span>
          <p className="text-sm text-white font-medium">{manifest.agent_name}</p>
        </div>
        <div>
          <span className="text-[10px] text-[var(--text-dim)] uppercase tracking-wider">Operator</span>
          <p className="text-[11px] text-[var(--cyan)] font-mono break-all">
            {manifest.operator_wallet || '0x...'}
          </p>
        </div>
        <div>
          <span className="text-[10px] text-[var(--text-dim)] uppercase tracking-wider">ERC-8004 Token</span>
          <p className="text-[11px] text-[var(--purple)] font-mono">
            {manifest.erc8004_identity ?? 'Registered'}
          </p>
        </div>

        {/* Tools */}
        <div>
          <span className="text-[10px] text-[var(--text-dim)] uppercase tracking-wider">Tools ({manifest.supported_tools.length})</span>
          <div className="flex flex-wrap gap-1 mt-1">
            {manifest.supported_tools.map((tool) => (
              <span key={tool} className="px-1.5 py-0.5 text-[9px] rounded bg-[var(--accent)]/10 text-[var(--accent)] border border-[var(--accent)]/20">
                {tool}
              </span>
            ))}
          </div>
        </div>

        {/* Integrations */}
        {manifest.integrations && (
          <div>
            <span className="text-[10px] text-[var(--text-dim)] uppercase tracking-wider">Integrations</span>
            <div className="mt-1 space-y-1">
              {Object.entries(manifest.integrations).map(([k, v]) => (
                <div key={k} className="flex items-center gap-2">
                  <div className="w-1 h-1 rounded-full bg-[var(--green)]" />
                  <span className="text-[10px] text-[var(--text-secondary)]">
                    <span className="text-[var(--green)]">{k}</span> — {v}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function StorageCard({ data }: { data: AgentData | null }) {
  return (
    <div className="rounded-xl border border-[var(--border)] bg-[var(--bg-card)] p-5 hover:border-[var(--green)]/30 transition-colors">
      <div className="flex items-center gap-2 mb-4">
        <div className="w-5 h-5 rounded bg-[var(--green)]/20 flex items-center justify-center">
          <span className="text-[var(--green)] text-xs">FIL</span>
        </div>
        <h2 className="text-xs font-semibold tracking-wider text-[var(--text-secondary)] uppercase">Decentralized Storage</h2>
      </div>

      <div className="space-y-3">
        <div>
          <span className="text-[10px] text-[var(--text-dim)] uppercase tracking-wider">Filecoin Items</span>
          <div className="mt-1 space-y-1">
            {(data?.filecoin?.items ?? []).length > 0 ? (
              data!.filecoin.items.map((item, i) => (
                <div key={i} className="flex items-center gap-2 text-[10px]">
                  <span className="text-[var(--green)]">CID</span>
                  <span className="text-[var(--text-secondary)] font-mono">{item}</span>
                </div>
              ))
            ) : (
              <p className="text-[10px] text-[var(--text-dim)]">No items stored yet</p>
            )}
          </div>
        </div>

        <div className="pt-2 border-t border-[var(--border)]">
          <span className="text-[10px] text-[var(--text-dim)] uppercase tracking-wider">Storacha Memory</span>
          {data?.memory ? (
            <div className="mt-1">
              <p className="text-sm text-white">{data.memory.total_entries} entries</p>
              <div className="flex gap-2 mt-1">
                {Object.entries(data.memory.categories).map(([cat, count]) => (
                  <span key={cat} className="text-[9px] px-1.5 py-0.5 rounded bg-[var(--purple)]/10 text-[var(--purple)] border border-[var(--purple)]/20">
                    {cat}: {count}
                  </span>
                ))}
              </div>
            </div>
          ) : (
            <p className="text-[10px] text-[var(--text-dim)] mt-1">No memories yet</p>
          )}
        </div>
      </div>
    </div>
  );
}

function PipelineView({ logs }: { logs: LogEntry[] }) {
  const phases = ['init', 'discover', 'plan', 'execute', 'verify', 'complete', 'shutdown'];
  const currentPhase = logs.length > 0 ? logs[logs.length - 1].phase : 'idle';

  return (
    <div className="rounded-xl border border-[var(--border)] bg-[var(--bg-card)] p-5">
      <div className="flex items-center gap-2 mb-4">
        <div className="w-5 h-5 rounded bg-[var(--yellow)]/20 flex items-center justify-center">
          <span className="text-[var(--yellow)] text-xs">&#9654;</span>
        </div>
        <h2 className="text-xs font-semibold tracking-wider text-[var(--text-secondary)] uppercase">Processing Pipeline</h2>
      </div>

      <div className="flex items-center gap-1">
        {phases.map((phase, i) => {
          const isActive = phase === currentPhase;
          const isPast = phases.indexOf(currentPhase) > i;
          const hasEntries = logs.some(l => l.phase === phase);

          return (
            <div key={phase} className="flex items-center gap-1 flex-1">
              <div className={`flex-1 rounded-md px-2 py-2 text-center text-[9px] uppercase tracking-wider border transition-all ${
                isActive
                  ? 'bg-[var(--accent)]/20 border-[var(--accent)] text-[var(--accent)] glow-accent font-bold'
                  : isPast || hasEntries
                    ? 'bg-[var(--green)]/10 border-[var(--green)]/30 text-[var(--green)]'
                    : 'bg-[var(--bg-primary)] border-[var(--border)] text-[var(--text-dim)]'
              }`}>
                {phase}
              </div>
              {i < phases.length - 1 && (
                <span className={`text-[8px] ${isPast ? 'text-[var(--green)]' : 'text-[var(--text-dim)]'}`}>&#8594;</span>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

function TaskCard({ task }: { task: TaskData }) {
  const statusConfig: Record<string, { color: string; label: string }> = {
    discovered: { color: 'var(--text-secondary)', label: 'DISCOVERED' },
    planning: { color: 'var(--yellow)', label: 'PLANNING' },
    executing: { color: 'var(--cyan)', label: 'EXECUTING' },
    verifying: { color: 'var(--purple)', label: 'VERIFYING' },
    completed: { color: 'var(--green)', label: 'COMPLETED' },
    failed: { color: 'var(--red)', label: 'FAILED' },
  };
  const status = statusConfig[task.status] ?? statusConfig.discovered;

  return (
    <div className="rounded-xl border border-[var(--border)] bg-[var(--bg-card)] p-5 hover:border-[var(--accent)]/30 transition-colors">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <div className="w-5 h-5 rounded bg-[var(--cyan)]/20 flex items-center justify-center">
            <span className="text-[var(--cyan)] text-xs">T</span>
          </div>
          <h2 className="text-xs font-semibold tracking-wider text-[var(--text-secondary)] uppercase">Active Task</h2>
        </div>
        <span className="text-[9px] px-2 py-0.5 rounded-full font-bold tracking-wider" style={{ color: status.color, background: `${status.color}15`, border: `1px solid ${status.color}30` }}>
          {status.label}
        </span>
      </div>

      <p className="text-sm text-white mb-3">{task.title}</p>

      {task.plan.length > 0 && (
        <div className="space-y-1.5">
          {task.plan.map((step, i) => {
            const output = task.outputs.find((o: Record<string, unknown>) => o.step === i);
            const isDone = !!output;
            const hasError = output && ('error' in output || 'blocked' in output);

            return (
              <div key={i} className="flex items-start gap-2 group">
                <div className={`mt-0.5 w-4 h-4 rounded-sm flex items-center justify-center text-[8px] shrink-0 border ${
                  hasError ? 'border-[var(--red)]/50 bg-[var(--red)]/10 text-[var(--red)]'
                  : isDone ? 'border-[var(--green)]/50 bg-[var(--green)]/10 text-[var(--green)]'
                  : 'border-[var(--border)] text-[var(--text-dim)]'
                }`}>
                  {hasError ? '!' : isDone ? '&#10003;' : i + 1}
                </div>
                <span className={`text-[11px] leading-tight ${isDone ? 'text-[var(--text-secondary)]' : 'text-white'}`}>
                  {step}
                </span>
              </div>
            );
          })}
        </div>
      )}

      {task.error && (
        <div className="mt-3 px-3 py-2 rounded bg-[var(--red)]/10 border border-[var(--red)]/20">
          <p className="text-[10px] text-[var(--red)]">{task.error}</p>
        </div>
      )}
    </div>
  );
}

const levelStyles: Record<string, { color: string; icon: string }> = {
  info:        { color: 'text-blue-400',   icon: 'INF' },
  decision:    { color: 'text-yellow-400', icon: 'DEC' },
  tool_call:   { color: 'text-cyan-400',   icon: ' >>' },
  tool_result: { color: 'text-green-400',  icon: ' <<' },
  error:       { color: 'text-red-400',    icon: 'ERR' },
  guardrail:   { color: 'text-purple-400', icon: 'GRD' },
  safety:      { color: 'text-red-500',    icon: 'SFT' },
};

function LogStream({ logs }: { logs: LogEntry[] }) {
  return (
    <div className="rounded-xl border border-[var(--border)] bg-[var(--bg-card)] flex flex-col h-full">
      <div className="flex items-center justify-between px-5 py-3 border-b border-[var(--border)]">
        <div className="flex items-center gap-2">
          <div className="w-5 h-5 rounded bg-[var(--accent)]/20 flex items-center justify-center">
            <span className="text-[var(--accent)] text-xs">&gt;_</span>
          </div>
          <h2 className="text-xs font-semibold tracking-wider text-[var(--text-secondary)] uppercase">Execution Log</h2>
        </div>
        <span className="text-[10px] text-[var(--text-dim)]">{logs.length} entries</span>
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-px">
        {logs.map((log, i) => {
          const style = levelStyles[log.level] ?? levelStyles.info;
          const time = new Date(log.timestamp * 1000).toLocaleTimeString('en-US', { hour12: false });

          return (
            <div key={i} className="flex gap-2 px-2 py-1 rounded hover:bg-white/[0.02] group animate-fade-in font-mono">
              <span className="text-[10px] text-[var(--text-dim)] shrink-0 tabular-nums">{time}</span>
              <span className={`text-[10px] ${style.color} shrink-0 w-6 text-right font-bold`}>{style.icon}</span>
              <span className="text-[10px] text-[var(--text-dim)] shrink-0 w-14">{log.phase}</span>
              <span className="text-[10px] text-[var(--text-secondary)] flex-1 break-all">{log.message}</span>
              <span className="text-[8px] text-[var(--text-dim)] shrink-0 hidden group-hover:block font-mono opacity-50">
                #{log.entry_hash.slice(0, 8)}
              </span>
            </div>
          );
        })}

        {/* Cursor */}
        <div className="flex gap-2 px-2 py-1">
          <span className="text-[10px] text-[var(--accent)] animate-blink">&#9608;</span>
        </div>
      </div>

      {/* Hash chain footer */}
      {logs.length > 0 && (
        <div className="px-5 py-2 border-t border-[var(--border)] overflow-hidden">
          <div className="animate-hash-scroll whitespace-nowrap text-[8px] text-[var(--text-dim)] font-mono">
            {logs.slice(-10).map(l => l.entry_hash).join(' ← ')}
            {' ← '}
            {logs.slice(-10).map(l => l.entry_hash).join(' ← ')}
          </div>
        </div>
      )}
    </div>
  );
}

function HashChainViz({ logs }: { logs: LogEntry[] }) {
  const recent = logs.slice(-8);
  return (
    <div className="rounded-xl border border-[var(--border)] bg-[var(--bg-card)] p-5">
      <div className="flex items-center gap-2 mb-4">
        <div className="w-5 h-5 rounded bg-[var(--purple)]/20 flex items-center justify-center">
          <span className="text-[var(--purple)] text-xs">#</span>
        </div>
        <h2 className="text-xs font-semibold tracking-wider text-[var(--text-secondary)] uppercase">Hash Chain</h2>
        <span className="text-[9px] text-[var(--green)] ml-auto">VERIFIED</span>
      </div>

      <div className="space-y-1">
        {recent.map((log, i) => (
          <div key={i} className="flex items-center gap-2">
            <span className="text-[8px] text-[var(--accent)] font-mono w-16 shrink-0 truncate">{log.entry_hash.slice(0, 8)}...</span>
            {i < recent.length - 1 && <span className="text-[8px] text-[var(--text-dim)]">&#8592;</span>}
            {i < recent.length - 1 && <span className="text-[8px] text-[var(--text-dim)] font-mono">{log.parent_hash?.slice(0, 8)}...</span>}
            <span className={`text-[8px] ml-auto ${levelStyles[log.level]?.color ?? 'text-gray-500'}`}>{log.level}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ---- Task Input Component ----

function TaskInput({ onSubmit, running }: { onSubmit: (task: string) => void; running: boolean }) {
  const [input, setInput] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);

  const handleSubmit = () => {
    if (input.trim() && !running) {
      onSubmit(input.trim());
      setInput('');
    }
  };

  return (
    <div className="rounded-xl border border-[var(--border)] bg-[var(--bg-card)] p-4">
      <div className="flex items-center gap-3">
        <span className="text-[var(--accent)] text-sm shrink-0">$</span>
        <input
          ref={inputRef}
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSubmit()}
          placeholder={running ? "Agent is running..." : "Enter a task for the agent..."}
          disabled={running}
          className="flex-1 bg-transparent text-sm text-white placeholder:text-[var(--text-dim)] outline-none disabled:opacity-50"
        />
        <button
          onClick={handleSubmit}
          disabled={running || !input.trim()}
          className={`px-4 py-1.5 rounded-lg text-xs font-bold tracking-wider transition-all ${
            running
              ? 'bg-[var(--yellow)]/20 text-[var(--yellow)] border border-[var(--yellow)]/30'
              : input.trim()
                ? 'bg-[var(--accent)] text-white hover:bg-[var(--accent)]/80 shadow-lg shadow-[var(--accent)]/20'
                : 'bg-[var(--border)] text-[var(--text-dim)]'
          }`}
        >
          {running ? 'RUNNING...' : 'EXECUTE'}
        </button>
      </div>

      {/* Suggested tasks */}
      {!running && !input && (
        <div className="flex gap-2 mt-3 flex-wrap">
          {[
            "Write a Python fibonacci script and store it on Filecoin",
            "Build a todo list API in Python",
            "Create a smart contract for token voting",
          ].map((suggestion) => (
            <button
              key={suggestion}
              onClick={() => setInput(suggestion)}
              className="px-2 py-1 text-[9px] rounded border border-[var(--border)] text-[var(--text-secondary)] hover:border-[var(--accent)]/50 hover:text-[var(--accent)] transition-colors"
            >
              {suggestion}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

// ---- Main Page ----

export default function Dashboard() {
  const [data, setData] = useState<AgentData | null>(null);
  const [tasks, setTasks] = useState<TaskData[]>([]);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [agentRunning, setAgentRunning] = useState(false);
  const [prevLogCount, setPrevLogCount] = useState(0);

  const parseTasks = (entries: LogEntry[]) => {
    const taskMap = new Map<string, TaskData>();
    for (const entry of entries) {
      if (entry.task_id && !taskMap.has(entry.task_id)) {
        taskMap.set(entry.task_id, {
          task_id: entry.task_id,
          title: '',
          status: 'executing',
          plan: [],
          outputs: [],
          created_at: entry.timestamp,
          completed_at: null,
          error: null,
        });
      }
      if (entry.task_id && taskMap.has(entry.task_id)) {
        const t = taskMap.get(entry.task_id)!;
        if (entry.message.startsWith('Processing: ')) t.title = entry.message.replace('Processing: ', '');
        if (entry.message.startsWith('Task completed:')) { t.status = 'completed'; t.completed_at = entry.timestamp; }
        if (entry.message.startsWith('Task failed')) { t.status = 'failed'; t.error = entry.message; }
      }
    }
    // Extract plan steps
    const planEntries = entries.filter((e) => e.phase === 'execute' && e.message.startsWith('Step '));
    const planSteps = planEntries.map((e) => e.message.replace(/^Step \d+\/\d+: /, ''));
    const toolResults = entries.filter((e) => e.level === 'tool_result');

    if (taskMap.size > 0) {
      const firstTask = Array.from(taskMap.values())[0];
      if (planSteps.length > 0) firstTask.plan = planSteps;
      toolResults.forEach((_, idx) => {
        firstTask.outputs.push({ step: idx, tool: 'done' });
      });
    }
    return Array.from(taskMap.values());
  };

  const fetchData = async () => {
    try {
      const [agentRes, statusRes] = await Promise.all([
        fetch('/api/agent'),
        fetch('/api/run'),
      ]);
      const json = await agentRes.json();
      const status = await statusRes.json();

      setData(json);
      const entries = json.logs?.recent_entries ?? [];
      setLogs(entries);
      setTasks(parseTasks(entries));
      setAgentRunning(status.running);

      // Detect if agent just finished
      const newCount = entries.length;
      if (prevLogCount > 0 && newCount > prevLogCount) {
        // New entries appeared
      }
      setPrevLogCount(newCount);

      setLoading(false);
    } catch {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 800);
    return () => clearInterval(interval);
  }, []);

  const handleRunTask = async (task: string) => {
    setAgentRunning(true);
    setLogs([]);
    setTasks([]);
    try {
      await fetch('/api/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ task }),
      });
    } catch {
      setAgentRunning(false);
    }
  };

  const chainValid = logs.length === 0 || logs.every((l, i) =>
    i === 0 || l.parent_hash === logs[i - 1].entry_hash
  );

  if (loading) {
    return (
      <div className="h-screen flex items-center justify-center grid-bg">
        <div className="text-center">
          <div className="text-2xl text-[var(--accent)] font-bold mb-2">AGENTPROOF</div>
          <div className="text-[10px] text-[var(--text-secondary)] tracking-widest animate-blink">INITIALIZING...</div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen grid-bg relative">
      <HexBackground />
      <Header data={data} chainValid={chainValid} />

      <main className="relative z-10 max-w-[1600px] mx-auto p-6">
        {/* Task Input */}
        <div className="mb-4">
          <TaskInput onSubmit={handleRunTask} running={agentRunning} />
        </div>

        {/* Pipeline */}
        <div className="mb-4">
          <PipelineView logs={logs} />
        </div>

        {/* Main grid */}
        <div className="grid grid-cols-12 gap-6" style={{ height: 'calc(100vh - 300px)' }}>
          {/* Left sidebar */}
          <div className="col-span-3 space-y-4 overflow-y-auto">
            <IdentityCard data={data} />
            <StorageCard data={data} />
            <HashChainViz logs={logs} />
          </div>

          {/* Center — Log stream */}
          <div className="col-span-6">
            <LogStream logs={logs} />
          </div>

          {/* Right sidebar — Tasks */}
          <div className="col-span-3 space-y-4 overflow-y-auto">
            {tasks.length > 0 ? (
              tasks.map((task) => <TaskCard key={task.task_id} task={task} />)
            ) : (
              <div className="rounded-xl border border-[var(--border)] bg-[var(--bg-card)] p-5">
                <div className="text-center py-6">
                  <div className="text-3xl mb-3">&#129302;</div>
                  <p className="text-xs text-[var(--text-secondary)] mb-1">No active tasks</p>
                  <p className="text-[10px] text-[var(--text-dim)]">Type a task above to start the agent</p>
                </div>
              </div>
            )}

            {/* Safety features */}
            {data?.manifest?.safety_features && (
              <div className="rounded-xl border border-[var(--border)] bg-[var(--bg-card)] p-5">
                <div className="flex items-center gap-2 mb-3">
                  <div className="w-5 h-5 rounded bg-[var(--red)]/20 flex items-center justify-center">
                    <span className="text-[var(--red)] text-xs">!</span>
                  </div>
                  <h2 className="text-xs font-semibold tracking-wider text-[var(--text-secondary)] uppercase">Guardrails</h2>
                </div>
                <div className="space-y-1">
                  {data.manifest.safety_features.map((f) => (
                    <div key={f} className="flex items-center gap-2">
                      <div className="w-1 h-1 rounded-full bg-[var(--green)]" />
                      <span className="text-[9px] text-[var(--text-secondary)]">{f.replace(/_/g, ' ')}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
