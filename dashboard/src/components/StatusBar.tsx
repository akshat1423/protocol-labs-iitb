"use client";

interface StatusBarProps {
  connected: boolean;
  running: boolean;
  paused: boolean;
  chainValid: boolean;
  onPause: () => void;
  onResume: () => void;
}

export function StatusBar({ connected, running, paused, chainValid, onPause, onResume }: StatusBarProps) {
  return (
    <div className="flex items-center justify-between px-6 py-3 bg-agent-card border-b border-agent-border">
      <div className="flex items-center gap-4">
        <h1 className="text-lg font-bold text-white">AgentProof</h1>
        <span className="text-xs text-gray-500">Verifiable Autonomous Agent</span>
      </div>

      <div className="flex items-center gap-4">
        {/* Connection status */}
        <div className="flex items-center gap-2">
          <div className={`w-2 h-2 rounded-full ${connected ? "bg-agent-green animate-pulse-green" : "bg-agent-red"}`} />
          <span className="text-xs text-gray-400">{connected ? "Connected" : "Disconnected"}</span>
        </div>

        {/* Agent status */}
        <div className="flex items-center gap-2">
          <div className={`w-2 h-2 rounded-full ${
            paused ? "bg-agent-yellow" : running ? "bg-agent-green animate-pulse-green" : "bg-gray-500"
          }`} />
          <span className="text-xs text-gray-400">
            {paused ? "Paused" : running ? "Running" : "Stopped"}
          </span>
        </div>

        {/* Chain validity */}
        <div className="flex items-center gap-2">
          <span className={`text-xs ${chainValid ? "text-agent-green" : "text-agent-red"}`}>
            {chainValid ? "Chain Valid" : "Chain Invalid"}
          </span>
        </div>

        {/* Kill switch */}
        <button
          onClick={paused ? onResume : onPause}
          className={`px-3 py-1 text-xs font-medium rounded ${
            paused
              ? "bg-agent-green/20 text-agent-green hover:bg-agent-green/30"
              : "bg-agent-red/20 text-agent-red hover:bg-agent-red/30"
          }`}
        >
          {paused ? "Resume" : "Pause"}
        </button>
      </div>
    </div>
  );
}
