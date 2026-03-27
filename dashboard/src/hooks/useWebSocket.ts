"use client";

import { useEffect, useRef, useState, useCallback } from "react";

interface AgentState {
  identity: {
    agent_name: string;
    operator_wallet: string;
    erc8004_identity: string | null;
    supported_tools: string[];
  };
  budget: {
    spent_usd: number;
    max_usd: number;
    llm_calls: string;
    tool_calls: string;
    budget_remaining_pct: number;
  };
  tasks: Array<{
    task_id: string;
    title: string;
    status: string;
    plan: string[];
    created_at: number;
    completed_at: number | null;
    error: string | null;
  }>;
  current_task: {
    task_id: string;
    title: string;
    status: string;
  } | null;
  running: boolean;
  paused: boolean;
  log_count: number;
  chain_valid: boolean;
}

interface LogEntry {
  timestamp: number;
  level: string;
  phase: string;
  message: string;
  data: Record<string, unknown>;
  task_id: string | null;
  parent_hash: string | null;
  entry_hash: string;
}

export function useAgentWebSocket(url: string = "ws://localhost:8765") {
  const ws = useRef<WebSocket | null>(null);
  const [connected, setConnected] = useState(false);
  const [state, setState] = useState<AgentState | null>(null);
  const [logs, setLogs] = useState<LogEntry[]>([]);

  useEffect(() => {
    const connect = () => {
      try {
        ws.current = new WebSocket(url);

        ws.current.onopen = () => setConnected(true);
        ws.current.onclose = () => {
          setConnected(false);
          setTimeout(connect, 3000); // Reconnect
        };

        ws.current.onmessage = (event) => {
          const msg = JSON.parse(event.data);

          if (msg.type === "state") {
            setState(msg.data);
          } else if (msg.type === "logs") {
            setLogs(msg.data);
          } else if (msg.type === "log") {
            setLogs((prev) => [...prev, msg.data].slice(-500));
          } else if (msg.type === "status") {
            setState((prev) =>
              prev ? { ...prev, ...msg.data } : prev
            );
          }
        };
      } catch {
        setTimeout(connect, 3000);
      }
    };

    connect();
    return () => ws.current?.close();
  }, [url]);

  const sendCommand = useCallback((action: string, data?: Record<string, unknown>) => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify({ action, ...data }));
    }
  }, []);

  const pause = useCallback(() => sendCommand("pause"), [sendCommand]);
  const resume = useCallback(() => sendCommand("resume"), [sendCommand]);
  const addTask = useCallback(
    (title: string, description: string) =>
      sendCommand("add_task", { title, description }),
    [sendCommand]
  );

  return { connected, state, logs, pause, resume, addTask, sendCommand };
}
