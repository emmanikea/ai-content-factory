import { NextResponse } from "next/server";

import { estimateGenerationCost } from "@/lib/generation/costs";
import { submitGeneration } from "@/lib/generation/router";
import type { GenerationRequest } from "@/lib/generation/types";
import { getStore } from "@/lib/persistence/store";

export async function POST(request: Request) {
  try {
    const body = (await request.json()) as GenerationRequest;

    if (!body.prompt?.trim()) {
      return NextResponse.json({ error: "prompt is required" }, { status: 400 });
    }

    const normalized: GenerationRequest = {
      ...body,
      prompt: body.prompt.trim(),
    };

    const cost = estimateGenerationCost(normalized);
    const providerJob = await submitGeneration(normalized);
    const factoryJob = await getStore().createGeneration({
      projectId: normalized.projectId,
      characterId: normalized.characterId,
      provider: providerJob.provider,
      providerJobId: providerJob.providerJobId,
      model: providerJob.model ?? normalized.model,
      tier: normalized.tier ?? "standard",
      status: providerJob.status,
      prompt: normalized.prompt,
      requestJson: normalized as unknown as Record<string, unknown>,
      responseJson: (providerJob.raw ?? {}) as Record<string, unknown>,
      attemptNumber: 1,
      durationSeconds: normalized.duration,
      resolution: normalized.resolution,
      aspectRatio: normalized.aspectRatio,
      estimatedCostUsd: cost.estimatedUsd,
    });

    return NextResponse.json(
      {
        ...providerJob,
        factoryJobId: factoryJob.id,
        estimatedCostUsd: cost.estimatedUsd,
        costBasis: cost.basis,
      },
      { status: 202 },
    );
  } catch (error) {
    const message = error instanceof Error ? error.message : "Generation failed";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
