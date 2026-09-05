import { comfyUiProvider } from "./providers/comfyui";
import { openRouterProvider } from "./providers/openrouter";
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
  if (request.provider) return request.provider;

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
  return providers[providerName].submit(request);
}

export async function getGeneration(
  providerName: GenerationProvider,
  providerJobId: string,
) {
  return providers[providerName].get(providerJobId);
}
