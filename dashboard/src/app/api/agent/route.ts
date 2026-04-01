import { NextResponse } from "next/server";
import { readFileSync, existsSync, readdirSync } from "fs";
import { join } from "path";

const AGENT_ROOT = join(process.cwd(), "..");
const AGENT_API_URL = process.env.AGENT_API_URL;

export const dynamic = "force-dynamic";

async function getStateFromAPI() {
  const res = await fetch(`${AGENT_API_URL}/state`, {
    cache: "no-store",
    signal: AbortSignal.timeout(8000),
  });
  if (!res.ok) throw new Error(`API returned ${res.status}`);
  return res.json();
}

function getStateFromDisk() {
  // Read agent.json manifest
  const manifestPath = join(AGENT_ROOT, "agent.json");
  const manifest = existsSync(manifestPath)
    ? JSON.parse(readFileSync(manifestPath, "utf-8"))
    : null;

  // Read agent_log.json
  const logPath = join(AGENT_ROOT, "agent_log.json");
  let logs = null;
  if (existsSync(logPath)) {
    const raw = JSON.parse(readFileSync(logPath, "utf-8"));
    logs = {
      total_entries: raw.total_entries ?? 0,
      chain_head_hash: raw.chain_head_hash ?? "",
      recent_entries: (raw.entries ?? []).slice(-200),
    };
  }

  // Read filecoin state
  const stateDir = join(AGENT_ROOT, "filecoin_state");
  let filecoinItems: string[] = [];
  if (existsSync(stateDir)) {
    filecoinItems = readdirSync(stateDir).filter((f: string) => f.endsWith(".json"));
  }

  // Read storacha memory
  const memoryPath = join(AGENT_ROOT, "storacha_memory", "memories.json");
  let memory = null;
  if (existsSync(memoryPath)) {
    const raw = JSON.parse(readFileSync(memoryPath, "utf-8"));
    const categories: Record<string, number> = {};
    for (const v of Object.values(raw) as Array<{ category?: string }>) {
      const cat = v?.category || "unknown";
      categories[cat] = (categories[cat] || 0) + 1;
    }
    memory = { total_entries: Object.keys(raw).length, categories };
  }

  // Read workspace files with content
  const workspaceDir = join(AGENT_ROOT, "agent_workspace");
  let workspaceFiles: Array<{ name: string; content: string; size: number }> = [];
  if (existsSync(workspaceDir)) {
    const names = readdirSync(workspaceDir).filter(f => !f.startsWith('.'));
    workspaceFiles = names.map(name => {
      try {
        const content = readFileSync(join(workspaceDir, name), "utf-8");
        return { name, content: content.slice(0, 5000), size: content.length };
      } catch {
        return { name, content: "", size: 0 };
      }
    });
  }

  // Read agent registry
  const registryPath = join(AGENT_ROOT, "agent_registry.json");
  let agentRegistry = null;
  if (existsSync(registryPath)) {
    agentRegistry = JSON.parse(readFileSync(registryPath, "utf-8"));
  }

  return {
    manifest,
    logs,
    filecoin: { items: filecoinItems },
    memory,
    workspace: { files: workspaceFiles },
    agentRegistry,
    timestamp: Date.now(),
  };
}

export async function GET() {
  try {
    if (AGENT_API_URL) {
      const data = await getStateFromAPI();
      return NextResponse.json(data);
    }
    return NextResponse.json(getStateFromDisk());
  } catch (error) {
    return NextResponse.json(
      { error: "Failed to read agent state", details: String(error) },
      { status: 500 }
    );
  }
}
