import { NextResponse } from "next/server";

import { toJsonObject } from "@/lib/domain/json";
import { getGeneration } from "@/lib/generation/router";
import type { GenerationProvider } from "@/lib/generation/types";
import { getStore } from "@/lib/persistence/store";

const providers = new Set<GenerationProvider>(["openrouter", "comfyui"]);
const terminalStatuses = new Set(["completed", "failed", "cancelled", "expired"]);

export async function GET(
  _request: Request,
  context: { params: Promise<{ id: string }> },
) {
  try {
    const { id } = await context.params;
    const store = getStore();
    const record = await store.getGeneration(id);
    if (!record) return NextResponse.json({ error: "generation not found" }, { status: 404 });

    if (terminalStatuses.has(record.status)) {
      return NextResponse.json({
        ...record,
        playbackUrl: record.status === "completed" ? `/api/generations/${record.id}/content?index=0` : undefined,
      });
    }
    if (!record.providerJobId) return NextResponse.json(record);
    if (!providers.has(record.provider as GenerationProvider)) {
      return NextResponse.json({ error: `unsupported stored provider: ${record.provider}` }, { status: 500 });
    }

    const provider = record.provider as GenerationProvider;
    const providerJob = await getGeneration(provider, record.providerJobId);
    const now = new Date().toISOString();
    const updated = await store.updateGeneration(record.id, {
      status: providerJob.status,
      responseJson: toJsonObject(providerJob.raw ?? {}),
      model: providerJob.model ?? record.model,
      startedAt: providerJob.status === "running" && !record.startedAt ? now : record.startedAt,
      completedAt: terminalStatuses.has(providerJob.status) ? now : record.completedAt,
    });

    return NextResponse.json({
      ...updated,
      providerError: providerJob.error,
      playbackUrl: providerJob.status === "completed"
        ? `/api/generations/${record.id}/content?index=0`
        : undefined,
    });
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Could not refresh generation" },
      { status: 502 },
    );
  }
}
