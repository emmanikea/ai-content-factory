import assert from "node:assert/strict";
import test from "node:test";

import { toJsonObject } from "../lib/domain/json";
import { selectProvider } from "../lib/generation/router";
import { memoryStore } from "../lib/persistence/store";

function withEnv(
  values: Record<string, string | undefined>,
  fn: () => void | Promise<void>,
) {
  const previous = Object.fromEntries(
    Object.keys(values).map((key) => [key, process.env[key]]),
  );
  for (const [key, value] of Object.entries(values)) {
    if (value === undefined) delete process.env[key];
    else process.env[key] = value;
  }

  return Promise.resolve(fn()).finally(() => {
    for (const [key, value] of Object.entries(previous)) {
      if (value === undefined) delete process.env[key];
      else process.env[key] = value;
    }
  });
}

test("toJsonObject removes undefined values and preserves JSON data", () => {
  assert.deepEqual(
    toJsonObject({ prompt: "hello", optional: undefined, nested: { ok: true } }),
    { prompt: "hello", nested: { ok: true } },
  );
});

test("router prefers ComfyUI for standard work when both providers are configured", async () => {
  await withEnv(
    { OPENROUTER_API_KEY: "test", COMFYUI_BASE_URL: "http://127.0.0.1:8188" },
    () => {
      assert.equal(selectProvider({ prompt: "test", tier: "standard" }), "comfyui");
      assert.equal(selectProvider({ prompt: "test", tier: "quality" }), "openrouter");
    },
  );
});

test("router rejects an explicitly selected provider that is not configured", async () => {
  await withEnv(
    { OPENROUTER_API_KEY: undefined, COMFYUI_BASE_URL: undefined },
    () => {
      assert.throws(
        () => selectProvider({ prompt: "test", provider: "openrouter" }),
        /openrouter is not configured/,
      );
    },
  );
});

test("memory store enforces generation idempotency", async () => {
  const key = `test:${crypto.randomUUID()}`;
  const input = {
    idempotencyKey: key,
    provider: "openrouter",
    tier: "standard",
    status: "queued",
    prompt: "idempotency test",
    requestJson: {},
    responseJson: {},
    attemptNumber: 1,
  };

  const first = await memoryStore.createGeneration(input);
  const found = await memoryStore.getGenerationByIdempotencyKey(key);
  assert.equal(found?.id, first.id);
  await assert.rejects(() => memoryStore.createGeneration(input), /duplicate idempotency key/);
});

test("memory store supports character lookup used by consent enforcement", async () => {
  const character = await memoryStore.createCharacter({
    name: "Test Person",
    slug: `test-person-${crypto.randomUUID()}`,
    kind: "real_person",
    consentStatus: "verified",
    metadata: {},
  });

  assert.equal((await memoryStore.getCharacter(character.id))?.consentStatus, "verified");
});
