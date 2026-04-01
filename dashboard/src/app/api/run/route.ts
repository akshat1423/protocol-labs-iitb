import { NextResponse } from "next/server";
import { join } from "path";
import { existsSync, rmSync } from "fs";

const AGENT_ROOT = join(process.cwd(), "..");
const AGENT_API_URL = process.env.AGENT_API_URL;

export const dynamic = "force-dynamic";

let agentRunning = false;

export async function POST(request: Request) {
  const body = await request.json();
  const task = body.task;

  if (!task || typeof task !== "string") {
    return NextResponse.json({ error: "Missing task" }, { status: 400 });
  }

  // ── Railway / cloud: proxy to Python API ─────────────────────────────────
  if (AGENT_API_URL) {
    try {
      const res = await fetch(`${AGENT_API_URL}/run`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ task }),
        signal: AbortSignal.timeout(10000),
      });
      const data = await res.json();
      if (!res.ok) return NextResponse.json(data, { status: res.status });
      return NextResponse.json(data);
    } catch (e) {
      return NextResponse.json({ error: String(e) }, { status: 500 });
    }
  }

  // ── Local dev: spawn Python process ──────────────────────────────────────
  if (agentRunning) {
    return NextResponse.json({ error: "Agent is already running" }, { status: 409 });
  }

  const cleanPaths = ["agent_log.json", "filecoin_state", "storacha_memory", "agent_workspace"];
  for (const p of cleanPaths) {
    const full = join(AGENT_ROOT, p);
    if (existsSync(full)) {
      try { rmSync(full, { recursive: true, force: true }); } catch {}
    }
  }

  const { spawn } = await import("child_process");
  const pythonPath = join(AGENT_ROOT, "agent", "venv", "bin", "python3");
  const python = existsSync(pythonPath) ? pythonPath : "python3";

  agentRunning = true;
  const proc = spawn(python, ["-m", "agent.core.run_gemini", "--task", task], {
    cwd: AGENT_ROOT,
    env: { ...process.env, PYTHONUNBUFFERED: "1" },
    stdio: ["ignore", "pipe", "pipe"],
  });
  proc.on("close", () => { agentRunning = false; });
  proc.on("error", () => { agentRunning = false; });

  return NextResponse.json({ status: "started", task });
}

export async function GET() {
  if (AGENT_API_URL) {
    try {
      const res = await fetch(`${AGENT_API_URL}/running`, {
        cache: "no-store",
        signal: AbortSignal.timeout(5000),
      });
      return NextResponse.json(await res.json());
    } catch {
      return NextResponse.json({ running: false });
    }
  }
  return NextResponse.json({ running: agentRunning });
}
