export type GenerationProvider = "openrouter" | "comfyui";
export type GenerationTier = "draft" | "standard" | "quality" | "max";
export type GenerationStatus =
  | "queued"
  | "running"
  | "completed"
  | "failed"
  | "cancelled"
  | "expired";

export interface GenerationRequest {
  prompt: string;
  tier?: GenerationTier;
  provider?: GenerationProvider;
  model?: string;
  duration?: number;
  resolution?: string;
  aspectRatio?: string;
  generateAudio?: boolean;
  inputReferences?: Array<{ url: string; type?: "image" | "video" | "audio" }>;
  frameImages?: Array<{ url: string; type: "first_frame" | "last_frame" }>;
  providerOptions?: Record<string, unknown>;
}

export interface GenerationJob {
  id: string;
  provider: GenerationProvider;
  providerJobId: string;
  model?: string;
  status: GenerationStatus;
  pollingUrl?: string;
  outputUrls?: string[];
  error?: string;
  estimatedCostUsd?: number;
  raw?: unknown;
}

export interface VideoProvider {
  submit(request: GenerationRequest): Promise<GenerationJob>;
  get(providerJobId: string): Promise<GenerationJob>;
}
