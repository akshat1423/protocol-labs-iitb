"use client";

import { useEffect, useRef } from "react";

interface LogEntry {
  timestamp: number;
  level: string;
  phase: string;
  message: string;
  data: Record<string, unknown>;
  entry_hash: string;
}

interface LogViewerProps {
  logs: LogEntry[];
}

const levelColors: Record<string, string> = {
  info: "text-blue-400",
  decision: "text-yellow-400",
  tool_call: "text-cyan-400",
  tool_result: "text-green-400",
  error: "text-red-400",
  guardrail: "text-purple-400",
  safety: "text-red-500 font-bold",
};

const levelIcons: Record<string, string> = {
  info: "i",
  decision: "?",
  tool_call: ">",
  tool_result: "<",
  error: "!",
  guardrail: "#",
  safety: "X",
};

export function LogViewer({ logs }: LogViewerProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs.length]);

  return (
    <div className="bg-agent-card border border-agent-border rounded-lg flex flex-col h-full">
      <div className="flex items-center justify-between px-4 py-2 border-b border-agent-border">
        <h2 className="text-sm font-semibold text-gray-400">EXECUTION LOG</h2>
        <span className="text-xs text-gray-500">{logs.length} entries</span>
      </div>

      <div className="flex-1 overflow-y-auto p-2 space-y-0.5 font-mono text-xs">
        {logs.map((log, i) => {
          const time = new Date(log.timestamp * 1000).toLocaleTimeString();
          const color = levelColors[log.level] || "text-gray-400";
          const icon = levelIcons[log.level] || " ";

          return (
            <div key={i} className="flex gap-2 hover:bg-white/5 px-2 py-0.5 rounded group">
              <span className="text-gray-600 shrink-0">{time}</span>
              <span className={`${color} shrink-0 w-3 text-center`}>{icon}</span>
              <span className="text-gray-500 shrink-0 w-16">{log.phase}</span>
              <span className="text-gray-300 flex-1">{log.message}</span>
              <span className="text-gray-700 shrink-0 hidden group-hover:block font-mono">
                {log.entry_hash.slice(0, 8)}
              </span>
            </div>
          );
        })}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
