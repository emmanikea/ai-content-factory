import type {
  GenerationJob,
  GenerationRequest,
  GenerationStatus,
  VideoProvider,
} from "../types";

const BASE_URL = "https://openrouter.ai/api/v1";
const MODEL_CACHE_MS = 5 * 60 * 1000;

export interface OpenRouterVideoModel {
  id: string;
  supported_durations?: number[];
  supported_resolutions?: string[];
  supported_aspect_ratios?: string[];
  supported_frame_images?: Array<"first_frame" | "last_frame">;
  pricing_skus?: Record<string, string>;
  allowed_passthrough_parameters?: string[];
}

let modelCache: { expiresAt: number; models: OpenRouterVideoModel[] } | undefined;

function apiKey(): string {
  const key = process.env.OPENROUTER_API_KEY;
  if (!key) throw new Error("OPENROUTER_API_KEY is not configured");
  return key;
}

function headers(includeJson = true): HeadersInit {
  return {
    Authorization: `Bearer ${apiKey()}`,
    ...(includeJson ? { "Content-Type": "application/json" } : {}),
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
  ].filter((value): value is string => typeof value === "string" && value.length > 0);

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

export async function listOpenRouterVideoModels(): Promise<OpenRouterVideoModel[]> {
  if (modelCache && modelCache.expiresAt > Date.now()) return modelCache.models;
  const raw = await request("/videos/models");
  const models = Array.isArray(raw?.data) ? raw.data as OpenRouterVideoModel[] : [];
  modelCache = { models, expiresAt: Date.now() + MODEL_CACHE_MS };
  return models;
}

export async function getOpenRouterVideoModel(modelId: string) {
  const models = await listOpenRouterVideoModels();
  return models.find((model) => model.id === modelId);
}

async function validateRequest(input: GenerationRequest, modelId: string) {
  const model = await getOpenRouterVideoModel(modelId);
  if (!model) throw new Error(`OpenRouter video model is not currently available: ${modelId}`);

  if (input.duration != null && model.supported_durations?.length) {
    const allowed = model.supported_durations.map(Number);
    if (!allowed.includes(Number(input.duration))) {
      throw new Error(`${modelId} does not support ${input.duration}s. Supported durations: ${allowed.join(", ")}`);
    }
  }
  if (input.resolution && model.supported_resolutions?.length && !model.supported_resolutions.includes(input.resolution)) {
    throw new Error(`${modelId} does not support ${input.resolution}. Supported resolutions: ${model.supported_resolutions.join(", ")}`);
  }
  if (input.aspectRatio && model.supported_aspect_ratios?.length && !model.supported_aspect_ratios.includes(input.aspectRatio)) {
    throw new Error(`${modelId} does not support ${input.aspectRatio}. Supported aspect ratios: ${model.supported_aspect_ratios.join(", ")}`);
  }
  if (input.frameImages?.length && model.supported_frame_images?.length) {
    for (const frame of input.frameImages) {
      if (!model.supported_frame_images.includes(frame.frameType)) {
        throw new Error(`${modelId} does not support ${frame.frameType} frame control`);
      }
    }
  }
}

export const openRouterProvider: VideoProvider = {
  async submit(input: GenerationRequest): Promise<GenerationJob> {
    const model = input.model ?? process.env.OPENROUTER_VIDEO_MODEL;
    if (!model) {
      throw new Error("Set a model or configure OPENROUTER_VIDEO_MODEL");
    }

    await validateRequest(input, model);

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

export async function fetchOpenRouterContent(
  providerJobId: string,
  index = 0,
  range?: string,
): Promise<Response> {
  const response = await fetch(
    `${BASE_URL}/videos/${encodeURIComponent(providerJobId)}/content?index=${index}`,
    {
      headers: {
        ...headers(false),
        ...(range ? { Range: range } : {}),
      },
      cache: "no-store",
      redirect: "follow",
    },
  );
  if (!response.ok && response.status !== 206) {
    const body = await response.text();
    throw new Error(`OpenRouter content ${response.status}: ${body.slice(0, 800)}`);
  }
  return response;
}
