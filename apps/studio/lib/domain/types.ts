export type JsonPrimitive = string | number | boolean | null;
export type JsonValue = JsonPrimitive | JsonObject | JsonValue[];
export interface JsonObject {
  [key: string]: JsonValue;
}

export type CharacterKind = "real_person" | "synthetic" | "brand_mascot";
export type ConsentStatus = "not_required" | "pending" | "verified" | "revoked";
export type ReferenceKind = "image" | "video" | "audio" | "performance" | "location" | "wardrobe";

export interface Character {
  id: string;
  name: string;
  slug: string;
  kind: CharacterKind;
  description?: string;
  voiceProfileId?: string;
  consentStatus: ConsentStatus;
  consentNotes?: string;
  metadata?: JsonObject;
  createdAt: string;
  updatedAt: string;
}

export interface CharacterReference {
  id: string;
  characterId?: string;
  kind: ReferenceKind;
  storageKey: string;
  sourceUrl?: string;
  label?: string;
  consentVerified: boolean;
  metadata?: JsonObject;
  createdAt: string;
}

export interface Project {
  id: string;
  name: string;
  projectType: string;
  status: string;
  metadata?: JsonObject;
  createdAt: string;
  updatedAt: string;
}

export interface GenerationRecord {
  id: string;
  projectId?: string;
  characterId?: string;
  idempotencyKey?: string;
  provider: string;
  providerJobId?: string;
  model?: string;
  tier: string;
  status: string;
  prompt: string;
  requestJson: JsonObject;
  responseJson?: JsonObject;
  attemptNumber: number;
  durationSeconds?: number;
  resolution?: string;
  aspectRatio?: string;
  estimatedCostUsd?: number;
  actualCostUsd?: number;
  startedAt?: string;
  completedAt?: string;
  createdAt: string;
  updatedAt: string;
}

export interface Asset {
  id: string;
  projectId?: string;
  generationJobId?: string;
  characterId?: string;
  kind: "image" | "video" | "audio" | "thumbnail" | "caption" | "other";
  storageKey: string;
  sourceUrl?: string;
  mimeType?: string;
  provenance: JsonObject;
  createdAt: string;
}
