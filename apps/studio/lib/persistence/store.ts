import type { Character, CharacterReference, GenerationRecord, Project } from "@/lib/domain/types";

export interface ContentFactoryStore {
  createCharacter(input: Omit<Character, "id" | "createdAt" | "updatedAt">): Promise<Character>;
  listCharacters(): Promise<Character[]>;
  addReference(input: Omit<CharacterReference, "id" | "createdAt">): Promise<CharacterReference>;
  listReferences(characterId?: string): Promise<CharacterReference[]>;
  createProject(input: Omit<Project, "id" | "createdAt" | "updatedAt">): Promise<Project>;
  listProjects(): Promise<Project[]>;
  createGeneration(input: Omit<GenerationRecord, "id" | "createdAt" | "updatedAt">): Promise<GenerationRecord>;
  updateGeneration(id: string, patch: Partial<GenerationRecord>): Promise<GenerationRecord | undefined>;
  getGeneration(id: string): Promise<GenerationRecord | undefined>;
  listGenerations(limit?: number): Promise<GenerationRecord[]>;
}

const characters = new Map<string, Character>();
const references = new Map<string, CharacterReference>();
const projects = new Map<string, Project>();
const generations = new Map<string, GenerationRecord>();

function id() {
  return crypto.randomUUID();
}

function now() {
  return new Date().toISOString();
}

export const memoryStore: ContentFactoryStore = {
  async createCharacter(input) {
    const timestamp = now();
    const row: Character = { ...input, id: id(), createdAt: timestamp, updatedAt: timestamp };
    characters.set(row.id, row);
    return row;
  },
  async listCharacters() {
    return [...characters.values()].sort((a, b) => b.createdAt.localeCompare(a.createdAt));
  },
  async addReference(input) {
    const row: CharacterReference = { ...input, id: id(), createdAt: now() };
    references.set(row.id, row);
    return row;
  },
  async listReferences(characterId) {
    return [...references.values()].filter((row) => !characterId || row.characterId === characterId);
  },
  async createProject(input) {
    const timestamp = now();
    const row: Project = { ...input, id: id(), createdAt: timestamp, updatedAt: timestamp };
    projects.set(row.id, row);
    return row;
  },
  async listProjects() {
    return [...projects.values()].sort((a, b) => b.createdAt.localeCompare(a.createdAt));
  },
  async createGeneration(input) {
    const timestamp = now();
    const row: GenerationRecord = { ...input, id: id(), createdAt: timestamp, updatedAt: timestamp };
    generations.set(row.id, row);
    return row;
  },
  async updateGeneration(idValue, patch) {
    const existing = generations.get(idValue);
    if (!existing) return undefined;
    const updated = { ...existing, ...patch, id: existing.id, updatedAt: now() };
    generations.set(idValue, updated);
    return updated;
  },
  async getGeneration(idValue) {
    return generations.get(idValue);
  },
  async listGenerations(limit = 100) {
    return [...generations.values()]
      .sort((a, b) => b.createdAt.localeCompare(a.createdAt))
      .slice(0, limit);
  },
};

// V2 keeps persistence behind this boundary. Memory is intentionally the default so the
// Studio can run before a database is configured. A Postgres adapter should implement this
// interface and be selected here once DATABASE_URL/SUPABASE_URL is present.
export function getStore(): ContentFactoryStore {
  return memoryStore;
}
