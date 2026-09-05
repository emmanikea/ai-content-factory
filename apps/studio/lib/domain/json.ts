import type { JsonObject } from "./types";

/**
 * Convert API/provider data into a JSON-safe object before persistence.
 * Undefined object properties are dropped the same way JSON serialization would drop them.
 */
export function toJsonObject(value: unknown): JsonObject {
  const serialized = JSON.stringify(value ?? {});
  const parsed = JSON.parse(serialized) as unknown;
  if (!parsed || Array.isArray(parsed) || typeof parsed !== "object") return {};
  return parsed as JsonObject;
}
