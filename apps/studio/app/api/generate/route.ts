import { NextResponse } from "next/server";

import { toJsonObject } from "@/lib/domain/json";
import type { Character, GenerationRecord } from "@/lib/domain/types";
import { estimateGenerationCost } from "@/lib/generation/costs";
import { selectProvider, submitGeneration } from "@/lib/generation/router";
import type { GenerationProvider, GenerationRequest, GenerationTier } from "@/lib/generation/types";
import { getStore } from "@/lib/persistence/store";
import { resolveImageReferenceIds } from "@/lib/references/resolve";

const validProviders = new Set<GenerationProvider>(["openrouter", "comfyui"]);
const validTiers = new Set<GenerationTier>(["draft", "standard", "quality", "max"]);

function validateHttpsUrl(raw: string) {
  const url = new URL(raw);
  if (url.protocol !== "https:") throw new Error(`reference URLs must use HTTPS: ${raw}`);
}

function reusedResponse(record: GenerationRecord | undefined) {
  if (!record) return undefined;
  return {
    id: `factory:${record.id}`,
    factoryJobId: record.id,
    provider: record.provider,
    providerJobId: record.providerJobId ?? "",
    model: record.model,
    status: record.status,
    estimatedCostUsd: record.estimatedCostUsd,
    playbackUrl: record.status === "completed" ? `/api/generations/${record.id}/content?index=0` : undefined,
    reused: true,
  };
}

export async function POST(request: Request) {
  let factoryJobId: string | undefined;
  try {
    const body = (await request.json()) as GenerationRequest;

    if (!body.prompt?.trim()) {
      return NextResponse.json({ error: "prompt is required" }, { status: 400 });
    }
    if (body.provider && !validProviders.has(body.provider)) {
      return NextResponse.json({ error: "invalid provider" }, { status: 400 });
    }
    if (body.tier && !validTiers.has(body.tier)) {
      return NextResponse.json({ error: "invalid generation tier" }, { status: 400 });
    }
    if (body.duration != null && (!Number.isFinite(body.duration) || body.duration <= 0 || body.duration > 30)) {
      return NextResponse.json({ error: "duration must be between 1 and 30 seconds" }, { status: 400 });
    }

    const idempotencyKey = body.idempotencyKey?.trim();
    if (idempotencyKey && idempotencyKey.length > 200) {
      return NextResponse.json({ error: "idempotencyKey must be 200 characters or fewer" }, { status: 400 });
    }

    try {
      body.inputReferences?.forEach((reference) => validateHttpsUrl(reference.url));
      body.frameImages?.forEach((frame) => validateHttpsUrl(frame.url));
    } catch (error) {
      return NextResponse.json({ error: error instanceof Error ? error.message : "invalid reference URL" }, { status: 400 });
    }

    let normalized: GenerationRequest = {
      ...body,
      prompt: body.prompt.trim(),
      idempotencyKey: idempotencyKey || undefined,
    };
    const persistedRequest = { ...normalized };
    const store = getStore();

    if (normalized.projectId && !(await store.getProject(normalized.projectId))) {
      return NextResponse.json({ error: "project not found" }, { status: 404 });
    }

    let selectedCharacter: Character | undefined;
    if (normalized.characterId) {
      selectedCharacter = await store.getCharacter(normalized.characterId);
      if (!selectedCharacter) return NextResponse.json({ error: "character not found" }, { status: 404 });
      if (selectedCharacter.kind === "real_person" && selectedCharacter.consentStatus !== "verified") {
        return NextResponse.json(
          { error: `real-person character consent is ${selectedCharacter.consentStatus}; verified consent is required for generation` },
          { status: 409 },
        );
      }
      if (
        selectedCharacter.kind === "real_person" &&
        ((body.inputReferences?.length ?? 0) > 0 || (body.frameImages?.length ?? 0) > 0)
      ) {
        return NextResponse.json(
          { error: "real-person generation requires registered consent-verified referenceIds; raw external reference URLs are not allowed" },
          { status: 409 },
        );
      }
    }

    if (normalized.idempotencyKey) {
      const existing = await store.getGenerationByIdempotencyKey(normalized.idempotencyKey);
      const response = reusedResponse(existing);
      if (response) return NextResponse.json(response, { status: 200 });
    }

    if (normalized.referenceIds?.length) {
      try {
        const urls = await resolveImageReferenceIds(
          normalized.referenceIds,
          store,
          normalized.characterId,
        );
        normalized = {
          ...normalized,
          inputReferences: [
            ...(normalized.inputReferences ?? []),
            ...urls.map((url) => ({ url })),
          ],
        };
      } catch (error) {
        return NextResponse.json(
          { error: error instanceof Error ? error.message : "unable to resolve stored references" },
          { status: 409 },
        );
      }
    }

    const selectedProvider = selectProvider(normalized);
    const routed: GenerationRequest = { ...normalized, provider: selectedProvider };
    const cost = await estimateGenerationCost(routed);

    const spendCap = Number(process.env.STUDIO_MAX_ESTIMATED_COST_USD ?? "");
    if (
      Number.isFinite(spendCap) &&
      spendCap > 0 &&
      cost.estimatedUsd != null &&
      cost.estimatedUsd > spendCap
    ) {
      return NextResponse.json(
        {
          error: `estimated generation cost $${cost.estimatedUsd.toFixed(4)} exceeds STUDIO_MAX_ESTIMATED_COST_USD=$${spendCap.toFixed(4)}`,
          costBasis: cost.basis,
        },
        { status: 422 },
      );
    }

    const initialRecord: Omit<GenerationRecord, "id" | "createdAt" | "updatedAt"> = {
      projectId: routed.projectId,
      characterId: routed.characterId,
      idempotencyKey: routed.idempotencyKey,
      provider: selectedProvider,
      model: routed.model ?? (selectedProvider === "openrouter" ? process.env.OPENROUTER_VIDEO_MODEL : undefined),
      tier: routed.tier ?? "standard",
      status: "queued",
      prompt: routed.prompt,
      requestJson: toJsonObject({ ...persistedRequest, provider: selectedProvider }),
      responseJson: {},
      attemptNumber: 1,
      durationSeconds: routed.duration,
      resolution: routed.resolution,
      aspectRatio: routed.aspectRatio,
      estimatedCostUsd: cost.estimatedUsd,
    };

    let factoryJob;
    try {
      factoryJob = await store.createGeneration(initialRecord);
    } catch (error) {
      if (routed.idempotencyKey) {
        const existing = await store.getGenerationByIdempotencyKey(routed.idempotencyKey);
        const response = reusedResponse(existing);
        if (response) return NextResponse.json(response, { status: 200 });
      }
      throw error;
    }
    factoryJobId = factoryJob.id;

    try {
      const providerJob = await submitGeneration(routed);
      const now = new Date().toISOString();
      const updated = await store.updateGeneration(factoryJob.id, {
        provider: providerJob.provider,
        providerJobId: providerJob.providerJobId,
        model: providerJob.model ?? factoryJob.model,
        status: providerJob.status,
        responseJson: toJsonObject(providerJob.raw ?? {}),
        startedAt: providerJob.status === "running" ? now : factoryJob.startedAt,
        completedAt: providerJob.status === "completed" ? now : undefined,
      });

      return NextResponse.json(
        {
          ...providerJob,
          factoryJobId: factoryJob.id,
          estimatedCostUsd: cost.estimatedUsd,
          costBasis: cost.basis,
          persistenceWarning: updated ? undefined : "provider job submitted but factory record could not be updated",
          playbackUrl: providerJob.status === "completed"
            ? `/api/generations/${factoryJob.id}/content?index=0`
            : undefined,
        },
        { status: 202 },
      );
    } catch (error) {
      const message = error instanceof Error ? error.message : "Provider submission failed";
      await store.updateGeneration(factoryJob.id, {
        status: "failed",
        responseJson: toJsonObject({ error: message, stage: "provider_submission" }),
        completedAt: new Date().toISOString(),
      });
      return NextResponse.json({ error: message, factoryJobId: factoryJob.id }, { status: 502 });
    }
  } catch (error) {
    const message = error instanceof Error ? error.message : "Generation failed";
    return NextResponse.json({ error: message, ...(factoryJobId ? { factoryJobId } : {}) }, { status: 500 });
  }
}
