import { NextResponse } from "next/server";

import { getGeneration } from "@/lib/generation/router";
import type { GenerationProvider } from "@/lib/generation/types";
import { getStore } from "@/lib/persistence/store";

export async function GET(
  _request: Request,
  context: { params: Promise<{ id: string }> },
) {
  try {
    const { id } = await context.params;
    const store = getStore();
    const record = await store.getGeneration(id);
    if (!record) return NextResponse.json({ error: "generation not found" }, { status: 404 });
    if (!record.providerJobId) return NextResponse.json(record);

    const provider = record.provider as GenerationProvider;
    const providerJob = await getGeneration(provider, record.providerJobId);
    const updated = await store.updateGeneration(record.id, {
      status: providerJob.status,
      responseJson: (providerJob.raw ?? {}) as Record<string, unknown>,
      model: providerJob.model ?? record.model,
    });

    return NextResponse.json({
      ...updated,
      outputUrls: providerJob.outputUrls,
      providerError: providerJob.error,
    });
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Could not refresh generation" },
      { status: 500 },
    );
  }
}
