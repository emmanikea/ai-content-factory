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
  projectId?: string;
  characterId?: string;
  referenceIds?: string[];
  idempotencyKey?: string;
  tier?: GenerationTier;
  provider?: GenerationProvider;
  model?: string;
  duration?: number;
  resolution?: string;
  aspectRatio?: string;
  generateAudio?: boolean;
  /** Portable visual references. OpenRouter currently accepts public HTTPS image URLs here. */
  inputReferences?: Array<{ url: string }>;
  frameImages?: Array<{ url: string; frameType: "first_frame" | "last_frame" }>;
  providerOptions?: Record<string, unknown>;
}

export interface GenerationJob {
  id: string;
  factoryJobId?: string;
  provider: GenerationProvider;
  providerJobId: string;
  model?: string;
  status: GenerationStatus;
  pollingUrl?: string;
  outputUrls?: string[];
  playbackUrl?: string;
  error?: string;
  estimatedCostUsd?: number;
  raw?: unknown;
}

export interface VideoProvider {
  submit(request: GenerationRequest): Promise<GenerationJob>;
  get(providerJobId: string): Promise<GenerationJob>;
}
