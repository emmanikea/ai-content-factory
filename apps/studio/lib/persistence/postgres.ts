import postgres from "postgres";

import type { Character, CharacterReference, GenerationRecord, Project } from "@/lib/domain/types";
import type { ContentFactoryStore } from "./store";

let client: ReturnType<typeof postgres> | undefined;

function db() {
  const url = process.env.DATABASE_URL;
  if (!url) throw new Error("DATABASE_URL is not configured");
  client ??= postgres(url, {
    max: Number(process.env.DATABASE_POOL_SIZE ?? 5),
    idle_timeout: 20,
    connect_timeout: 15,
    prepare: false,
  });
  return client;
}

function iso(value: Date | string) {
  return new Date(value).toISOString();
}

function isoOptional(value: Date | string | null | undefined) {
  return value == null ? undefined : iso(value);
}

function mapCharacter(row: any): Character {
  return {
    id: row.id,
    name: row.name,
    slug: row.slug,
    kind: row.kind,
    description: row.description ?? undefined,
    voiceProfileId: row.voice_profile_id ?? undefined,
    consentStatus: row.consent_status,
    consentNotes: row.consent_notes ?? undefined,
    metadata: row.metadata ?? {},
    createdAt: iso(row.created_at),
    updatedAt: iso(row.updated_at),
  };
}

function mapReference(row: any): CharacterReference {
  return {
    id: row.id,
    characterId: row.character_id ?? undefined,
    kind: row.kind,
    storageKey: row.storage_key,
    sourceUrl: row.source_url ?? undefined,
    label: row.label ?? undefined,
    consentVerified: Boolean(row.consent_verified),
    metadata: row.metadata ?? {},
    createdAt: iso(row.created_at),
  };
}

function mapProject(row: any): Project {
  return {
    id: row.id,
    name: row.name,
    projectType: row.project_type,
    status: row.status,
    metadata: row.metadata ?? {},
    createdAt: iso(row.created_at),
    updatedAt: iso(row.updated_at),
  };
}

function mapGeneration(row: any): GenerationRecord {
  return {
    id: row.id,
    projectId: row.project_id ?? undefined,
    characterId: row.character_id ?? undefined,
    idempotencyKey: row.idempotency_key ?? undefined,
    provider: row.provider,
    providerJobId: row.provider_job_id ?? undefined,
    model: row.model ?? undefined,
    tier: row.tier,
    status: row.status,
    prompt: row.prompt,
    requestJson: row.request_json ?? {},
    responseJson: row.response_json ?? {},
    attemptNumber: row.attempt_number,
    durationSeconds: row.duration_seconds == null ? undefined : Number(row.duration_seconds),
    resolution: row.resolution ?? undefined,
    aspectRatio: row.aspect_ratio ?? undefined,
    estimatedCostUsd: row.estimated_cost_usd == null ? undefined : Number(row.estimated_cost_usd),
    actualCostUsd: row.actual_cost_usd == null ? undefined : Number(row.actual_cost_usd),
    startedAt: isoOptional(row.started_at),
    completedAt: isoOptional(row.completed_at),
    createdAt: iso(row.created_at),
    updatedAt: iso(row.updated_at),
  };
}

export const postgresStore: ContentFactoryStore = {
  async createCharacter(input) {
    const sql = db();
    const [row] = await sql`
      insert into characters (name, slug, kind, description, voice_profile_id, consent_status, consent_notes, metadata)
      values (${input.name}, ${input.slug}, ${input.kind}, ${input.description ?? null}, ${input.voiceProfileId ?? null}, ${input.consentStatus}, ${input.consentNotes ?? null}, ${sql.json(input.metadata ?? {})})
      returning *
    `;
    return mapCharacter(row);
  },

  async getCharacter(id) {
    const rows = await db()`select * from characters where id = ${id} limit 1`;
    return rows.length ? mapCharacter(rows[0]) : undefined;
  },

  async listCharacters() {
    const rows = await db()`select * from characters order by created_at desc`;
    return rows.map(mapCharacter);
  },

  async addReference(input) {
    const sql = db();
    const [row] = await sql`
      insert into references (character_id, kind, storage_key, source_url, label, consent_verified, metadata)
      values (${input.characterId ?? null}, ${input.kind}, ${input.storageKey}, ${input.sourceUrl ?? null}, ${input.label ?? null}, ${input.consentVerified}, ${sql.json(input.metadata ?? {})})
      returning *
    `;
    return mapReference(row);
  },

  async listReferences(characterId) {
    const sql = db();
    const rows = characterId
      ? await sql`select * from references where character_id = ${characterId} order by created_at desc`
      : await sql`select * from references order by created_at desc`;
    return rows.map(mapReference);
  },

  async createProject(input) {
    const sql = db();
    const [row] = await sql`
      insert into projects (name, project_type, status, metadata)
      values (${input.name}, ${input.projectType}, ${input.status}, ${sql.json(input.metadata ?? {})})
      returning *
    `;
    return mapProject(row);
  },

  async getProject(id) {
    const rows = await db()`select * from projects where id = ${id} limit 1`;
    return rows.length ? mapProject(rows[0]) : undefined;
  },

  async listProjects() {
    const rows = await db()`select * from projects order by created_at desc`;
    return rows.map(mapProject);
  },

  async createGeneration(input) {
    const sql = db();
    const [row] = await sql`
      insert into generation_jobs (
        project_id, character_id, idempotency_key, provider, provider_job_id, model, tier, status, prompt,
        request_json, response_json, attempt_number, duration_seconds, resolution, aspect_ratio,
        estimated_cost_usd, actual_cost_usd, started_at, completed_at
      ) values (
        ${input.projectId ?? null}, ${input.characterId ?? null}, ${input.idempotencyKey ?? null},
        ${input.provider}, ${input.providerJobId ?? null}, ${input.model ?? null}, ${input.tier}, ${input.status}, ${input.prompt},
        ${sql.json(input.requestJson ?? {})}, ${sql.json(input.responseJson ?? {})}, ${input.attemptNumber},
        ${input.durationSeconds ?? null}, ${input.resolution ?? null}, ${input.aspectRatio ?? null},
        ${input.estimatedCostUsd ?? null}, ${input.actualCostUsd ?? null},
        ${input.startedAt ?? null}, ${input.completedAt ?? null}
      ) returning *
    `;
    return mapGeneration(row);
  },

  async updateGeneration(id, patch) {
    const sql = db();
    const currentRows = await sql`select * from generation_jobs where id = ${id} limit 1`;
    if (!currentRows.length) return undefined;
    const current = mapGeneration(currentRows[0]);
    const next = { ...current, ...patch };
    const [row] = await sql`
      update generation_jobs set
        project_id = ${next.projectId ?? null},
        character_id = ${next.characterId ?? null},
        idempotency_key = ${next.idempotencyKey ?? null},
        provider = ${next.provider},
        provider_job_id = ${next.providerJobId ?? null},
        model = ${next.model ?? null},
        tier = ${next.tier},
        status = ${next.status},
        prompt = ${next.prompt},
        request_json = ${sql.json(next.requestJson ?? {})},
        response_json = ${sql.json(next.responseJson ?? {})},
        attempt_number = ${next.attemptNumber},
        duration_seconds = ${next.durationSeconds ?? null},
        resolution = ${next.resolution ?? null},
        aspect_ratio = ${next.aspectRatio ?? null},
        estimated_cost_usd = ${next.estimatedCostUsd ?? null},
        actual_cost_usd = ${next.actualCostUsd ?? null},
        started_at = ${next.startedAt ?? null},
        completed_at = ${next.completedAt ?? null}
      where id = ${id}
      returning *
    `;
    return mapGeneration(row);
  },

  async getGeneration(id) {
    const rows = await db()`select * from generation_jobs where id = ${id} limit 1`;
    return rows.length ? mapGeneration(rows[0]) : undefined;
  },

  async getGenerationByIdempotencyKey(key) {
    const rows = await db()`select * from generation_jobs where idempotency_key = ${key} limit 1`;
    return rows.length ? mapGeneration(rows[0]) : undefined;
  },

  async listGenerations(limit = 100) {
    const rows = await db()`select * from generation_jobs order by created_at desc limit ${limit}`;
    return rows.map(mapGeneration);
  },
};
