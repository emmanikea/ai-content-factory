import type {
  GenerationJob,
  GenerationRequest,
  GenerationStatus,
  VideoProvider,
} from "../types";

const BASE_URL = "https://openrouter.ai/api/v1";

function apiKey(): string {
  const key = process.env.OPENROUTER_API_KEY;
  if (!key) throw new Error("OPENROUTER_API_KEY is not configured");
  return key;
}

function headers(): HeadersInit {
  return {
    Authorization: `Bearer ${apiKey()}`,
    "Content-Type": "application/json",
    ...(process.env.OPENROUTER_SITE_URL
      ? { "HTTP-Referer": process.env.OPENROUTER_SITE_URL }
      : {}),
    ...(process.env.OPENROUTER_APP_NAME
      ? { "X-Title": process.env.OPENROUTER_APP_NAME }
      : {}),
  };
}

function mapStatus(status?: string): GenerationStatus {
  switch (status) {
    case "completed":
    case "failed":
    case "cancelled":
    case "expired":
      return status;
    case "running":
    case "processing":
    case "in_progress":
      return "running";
    default:
      return "queued";
  }
}

function normalize(raw: Record<string, any>, model?: string): GenerationJob {
  const urls = [
    ...(Array.isArray(raw.unsigned_urls) ? raw.unsigned_urls : []),
    ...(Array.isArray(raw.output_urls) ? raw.output_urls : []),
  ].filter(Boolean);

  return {
    id: `openrouter:${raw.id}`,
    provider: "openrouter",
    providerJobId: raw.id,
    model: raw.model ?? model,
    status: mapStatus(raw.status),
    pollingUrl: raw.polling_url,
    outputUrls: urls.length ? urls : undefined,
    error: raw.error?.message ?? (typeof raw.error === "string" ? raw.error : undefined),
    raw,
  };
}

async function request(path: string, init?: RequestInit) {
  const response = await fetch(`${BASE_URL}${path}`, {
    ...init,
    headers: { ...headers(), ...(init?.headers ?? {}) },
    cache: "no-store",
  });

  if (!response.ok) {
    const body = await response.text();
    throw new Error(`OpenRouter ${response.status}: ${body.slice(0, 1200)}`);
  }

  return response.json();
}

export const openRouterProvider: VideoProvider = {
  async submit(input: GenerationRequest): Promise<GenerationJob> {
    const model = input.model ?? process.env.OPENROUTER_VIDEO_MODEL;
    if (!model) {
      throw new Error("Set a model or configure OPENROUTER_VIDEO_MODEL");
    }

    const body: Record<string, unknown> = {
      model,
      prompt: input.prompt,
      ...(input.duration ? { duration: input.duration } : {}),
      ...(input.resolution ? { resolution: input.resolution } : {}),
      ...(input.aspectRatio ? { aspect_ratio: input.aspectRatio } : {}),
      ...(typeof input.generateAudio === "boolean"
        ? { generate_audio: input.generateAudio }
        : {}),
      ...(input.inputReferences?.length
        ? {
            input_references: input.inputReferences.map((reference) => ({
              type: "image_url",
              image_url: { url: reference.url },
            })),
          }
        : {}),
      ...(input.frameImages?.length
        ? {
            frame_images: input.frameImages.map((frame) => ({
              type: "image_url",
              image_url: { url: frame.url },
              frame_type: frame.frameType,
            })),
          }
        : {}),
      ...(input.providerOptions
        ? { provider: { options: input.providerOptions } }
        : {}),
    };

    const raw = await request("/videos", {
      method: "POST",
      body: JSON.stringify(body),
    });

    return normalize(raw, model);
  },

  async get(providerJobId: string): Promise<GenerationJob> {
    const raw = await request(`/videos/${encodeURIComponent(providerJobId)}`);
    return normalize(raw);
  },
};

export async function listOpenRouterVideoModels() {
  return request("/videos/models");
}
