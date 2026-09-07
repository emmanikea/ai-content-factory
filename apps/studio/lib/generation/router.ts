import { comfyUiProvider, fetchComfyOutput } from "./providers/comfyui";
import { fetchOpenRouterContent, openRouterProvider } from "./providers/openrouter";
import type {
  GenerationProvider,
  GenerationRequest,
  VideoProvider,
} from "./types";

const providers: Record<GenerationProvider, VideoProvider> = {
  openrouter: openRouterProvider,
  comfyui: comfyUiProvider,
};

function configured(name: GenerationProvider): boolean {
  return name === "openrouter"
    ? Boolean(process.env.OPENROUTER_API_KEY)
    : Boolean(process.env.COMFYUI_BASE_URL);
}

export function selectProvider(request: GenerationRequest): GenerationProvider {
  if (request.provider) {
    if (!configured(request.provider)) {
      throw new Error(`${request.provider} is not configured`);
    }
    return request.provider;
  }

  const tier = request.tier ?? "standard";

  if ((tier === "draft" || tier === "standard") && configured("comfyui")) {
    return "comfyui";
  }

  if (configured("openrouter")) return "openrouter";
  if (configured("comfyui")) return "comfyui";

  throw new Error(
    "No generation provider is configured. Set OPENROUTER_API_KEY or COMFYUI_BASE_URL.",
  );
}

export async function submitGeneration(request: GenerationRequest) {
  const providerName = selectProvider(request);
  return providers[providerName].submit({ ...request, provider: providerName });
}

export async function getGeneration(
  providerName: GenerationProvider,
  providerJobId: string,
) {
  return providers[providerName].get(providerJobId);
}

export async function getGenerationContent(
  providerName: GenerationProvider,
  providerJobId: string,
  index = 0,
  range?: string,
) {
  return providerName === "openrouter"
    ? fetchOpenRouterContent(providerJobId, index, range)
    : fetchComfyOutput(providerJobId, index, range);
}
