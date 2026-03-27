import { NextResponse } from "next/server";
import { readFileSync, existsSync, readdirSync } from "fs";
import { join } from "path";

const AGENT_ROOT = join(process.cwd(), "..");

export const dynamic = "force-dynamic";

export async function GET() {
  try {
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

    // Read workspace files
    const workspaceDir = join(AGENT_ROOT, "agent_workspace");
    let workspaceFiles: string[] = [];
    if (existsSync(workspaceDir)) {
      workspaceFiles = readdirSync(workspaceDir).filter(f => !f.startsWith('.'));
    }

    return NextResponse.json({
      manifest,
      logs,
      filecoin: { items: filecoinItems },
      memory,
      workspace: { files: workspaceFiles },
      timestamp: Date.now(),
    });
  } catch (error) {
    return NextResponse.json(
      { error: "Failed to read agent state", details: String(error) },
      { status: 500 }
    );
  }
}
