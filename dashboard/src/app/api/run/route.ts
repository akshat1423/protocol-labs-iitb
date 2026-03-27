import { NextResponse } from "next/server";
import { spawn } from "child_process";
import { join } from "path";
import { existsSync, unlinkSync, rmSync } from "fs";

const AGENT_ROOT = join(process.cwd(), "..");

export const dynamic = "force-dynamic";

// Track if agent is running
let agentProcess: ReturnType<typeof spawn> | null = null;
let agentRunning = false;

export async function POST(request: Request) {
  const body = await request.json();
  const task = body.task;

  if (!task || typeof task !== "string") {
    return NextResponse.json({ error: "Missing task" }, { status: 400 });
  }

  if (agentRunning) {
    return NextResponse.json({ error: "Agent is already running" }, { status: 409 });
  }

  // Clean previous state
  const cleanPaths = ["agent_log.json", "filecoin_state", "storacha_memory", "agent_workspace"];
  for (const p of cleanPaths) {
    const full = join(AGENT_ROOT, p);
    if (existsSync(full)) {
      try {
        rmSync(full, { recursive: true, force: true });
      } catch {}
    }
  }

  // Find the venv python
  const pythonPath = join(AGENT_ROOT, "agent", "venv", "bin", "python3");
  const python = existsSync(pythonPath) ? pythonPath : "python3";

  agentRunning = true;

  agentProcess = spawn(python, ["-m", "agent.core.run_gemini", "--task", task], {
    cwd: AGENT_ROOT,
    env: { ...process.env, PYTHONUNBUFFERED: "1" },
    stdio: ["ignore", "pipe", "pipe"],
  });

  agentProcess.on("close", () => {
    agentRunning = false;
    agentProcess = null;
  });

  agentProcess.on("error", () => {
    agentRunning = false;
    agentProcess = null;
  });

  return NextResponse.json({ status: "started", task });
}

export async function GET() {
  return NextResponse.json({ running: agentRunning });
}
