import type { GenerationRequest } from "./types";

export interface CostEstimate {
  estimatedUsd?: number;
  basis: string;
}

const perSecondUsd: Record<string, number> = {
  "bytedance/seedance-2.0-mini": 0.01345,
  "bytedance/seedance-1.5-pro": 0.02306,
  "bytedance/seedance-2.0-fast": 0.04035,
  "alibaba/wan-3.0": 0.0425,
  "minimax/h3": 0.05,
  "bytedance/seedance-2.0": 0.06726,
};

export function estimateGenerationCost(input: GenerationRequest): CostEstimate {
  if (input.provider === "comfyui") {
    return { basis: "self-hosted: estimate from GPU telemetry after completion" };
  }

  const model = input.model ?? process.env.OPENROUTER_VIDEO_MODEL;
  const rate = model ? perSecondUsd[model] : undefined;
  if (!rate || !input.duration) {
    return { basis: "provider rate or duration unavailable" };
  }

  return {
    estimatedUsd: Number((rate * input.duration).toFixed(6)),
    basis: `${model} x ${input.duration}s at configured reference rate`,
  };
}
