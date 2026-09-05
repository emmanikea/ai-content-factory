import { getOpenRouterVideoModel } from "./providers/openrouter";
import type { GenerationRequest } from "./types";

export interface CostEstimate {
  estimatedUsd?: number;
  basis: string;
}

export async function estimateGenerationCost(input: GenerationRequest): Promise<CostEstimate> {
  if (input.provider === "comfyui") {
    return { basis: "self-hosted: reconcile from GPU telemetry after completion" };
  }

  const modelId = input.model ?? process.env.OPENROUTER_VIDEO_MODEL;
  if (!modelId || !input.duration) {
    return { basis: "model or duration unavailable" };
  }

  try {
    const model = await getOpenRouterVideoModel(modelId);
    if (!model) return { basis: `live OpenRouter pricing unavailable for ${modelId}` };

    const pricing = model.pricing_skus ?? {};
    const resolutionKey = input.resolution ? `per-video-second-${input.resolution}` : undefined;
    const sku = resolutionKey && pricing[resolutionKey] != null
      ? resolutionKey
      : pricing["per-video-second"] != null
        ? "per-video-second"
        : undefined;

    if (!sku) {
      return { basis: `${modelId}: no directly comparable per-video-second SKU advertised` };
    }

    const rate = Number(pricing[sku]);
    if (!Number.isFinite(rate) || rate < 0) {
      return { basis: `${modelId}: invalid live price for ${sku}` };
    }

    return {
      estimatedUsd: Number((rate * input.duration).toFixed(6)),
      basis: `${modelId} x ${input.duration}s using live OpenRouter ${sku} pricing`,
    };
  } catch (error) {
    return {
      basis: `live pricing lookup failed: ${error instanceof Error ? error.message : "unknown error"}`,
    };
  }
}
