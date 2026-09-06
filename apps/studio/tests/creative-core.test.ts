import assert from "node:assert/strict";
import test from "node:test";

import { preflightGeneration } from "../lib/creative/preflight";
import { routeCreativeBrief } from "../lib/creative/workflow-router";
import type {
  AssetLock,
  ConsentCheck,
  CreativeBrief,
  ModelContract,
  ProductionPlan,
} from "../lib/creative/types";
import type { GenerationRequest } from "../lib/generation/types";

function makeBrief(overrides: Partial<CreativeBrief> = {}): CreativeBrief {
  return {
    id: "brief-1",
    projectId: "project-1",
    intent: "cinematic_video",
    concept: "A controlled cinematic product reveal.",
    deliverables: [
      {
        kind: "video",
        durationSeconds: 8,
        aspectRatio: "16:9",
        resolution: "1080p",
      },
    ],
    ...overrides,
  };
}

function makePlan(
  brief: CreativeBrief,
  overrides: Partial<ProductionPlan> = {},
): ProductionPlan {
  const workflow = overrides.workflow ?? brief.intent;
  const mediaType =
    workflow === "product_still" || workflow === "image_edit"
      ? "image"
      : "video";

  return {
    id: "plan-1",
    briefId: brief.id,
    workflow,
    routeReason: "test route",
    assets: [],
    sceneContext: brief.concept,
    shots: [{ index: 1, durationSeconds: 8, action: "Reveal the subject." }],
    continuityLocks: [],
    output: {
      mediaType,
      durationSeconds: mediaType === "video" ? 8 : undefined,
      aspectRatio: "16:9",
      resolution: "1080p",
    },
    renderStrategy: { stage: "final" },
    plannerVersion: "test-planner-v1",
    ...overrides,
  };
}

function makeModel(overrides: Partial<ModelContract> = {}): ModelContract {
  return {
    provider: "openrouter",
    model: "test/video-model",
    mediaType: "video",
    capabilities: {
      textToMedia: true,
      imageReferences: 2,
      videoReferences: 1,
      audioReferences: 1,
      firstFrame: true,
      lastFrame: true,
      imageEdit: false,
      videoEdit: true,
      videoExtend: false,
      nativeAudio: true,
      identityReference: true,
    },
    aspectRatios: ["16:9", "9:16"],
    resolutions: ["720p", "1080p"],
    durationSeconds: { min: 4, max: 15 },
    snapshotAt: "2026-09-06T00:00:00Z",
    ...overrides,
  };
}

function runPreflight(options?: {
  brief?: CreativeBrief;
  plan?: ProductionPlan;
  model?: ModelContract;
  request?: Partial<GenerationRequest>;
  assetLocks?: AssetLock[];
  consentChecks?: ConsentCheck[];
  resolvedReferenceCounts?: { image?: number; video?: number; audio?: number };
  estimatedCostUsd?: number;
}) {
  const brief = options?.brief ?? makeBrief();
  const plan = options?.plan ?? makePlan(brief);
  const model = options?.model ?? makeModel();

  return preflightGeneration({
    brief,
    plan,
    compiled: {
      compilerId: "test-compiler",
      compilerVersion: "1.0.0",
      model,
      requiredLocks: [],
      request: {
        prompt: "Controlled cinematic reveal.",
        provider: model.provider,
        model: model.model,
        idempotencyKey: "test:creative:1",
        duration: plan.output.durationSeconds,
        aspectRatio: plan.output.aspectRatio,
        resolution: plan.output.resolution,
        ...(options?.request ?? {}),
      },
    },
    assetLocks: options?.assetLocks,
    consentChecks: options?.consentChecks,
    resolvedReferenceCounts: options?.resolvedReferenceCounts,
    estimatedCostUsd: options?.estimatedCostUsd,
  });
}

test("product still brief routes to the product-still workflow", () => {
  const brief = makeBrief({
    intent: "product_still",
    deliverables: [{ kind: "image", aspectRatio: "1:1", resolution: "2k" }],
  });

  const route = routeCreativeBrief(brief);
  assert.equal(route.workflow, "product_still");
  assert.match(route.reason, /Product still intent/);
});

test("UGC ad brief routes to the UGC workflow", () => {
  const brief = makeBrief({ intent: "ugc_ad" });
  assert.equal(routeCreativeBrief(brief).workflow, "ugc_ad");
});

test("workflow router rejects an incompatible deliverable media type", () => {
  const brief = makeBrief({
    intent: "video_edit",
    deliverables: [{ kind: "image" }],
  });

  assert.throws(
    () => routeCreativeBrief(brief),
    /video_edit requires at least one video deliverable/,
  );
});

test("video edit preflight blocks a model without video-edit capability", () => {
  const brief = makeBrief({ intent: "video_edit" });
  const plan = makePlan(brief, { workflow: "video_edit" });
  const model = makeModel({
    capabilities: {
      ...makeModel().capabilities,
      videoEdit: false,
    },
  });

  const result = runPreflight({
    brief,
    plan,
    model,
    resolvedReferenceCounts: { video: 1 },
  });
  assert.equal(result.status, "block");
  assert.ok(
    result.checks.some(
      (item) => item.code === "video_edit_capability" && item.status === "block",
    ),
  );
});

test("video edit preflight blocks when the source video was not resolved", () => {
  const brief = makeBrief({ intent: "video_edit" });
  const plan = makePlan(brief, { workflow: "video_edit" });

  const result = runPreflight({ brief, plan });
  assert.equal(result.status, "block");
  assert.ok(
    result.checks.some(
      (item) => item.code === "video_edit_source" && item.status === "block",
    ),
  );
});

test("real-person generation blocks when consent is not verified", () => {
  const brief = makeBrief({ characterIds: ["person-1"] });
  const result = runPreflight({
    brief,
    consentChecks: [
      {
        characterId: "person-1",
        kind: "real_person",
        consentStatus: "pending",
      },
    ],
  });

  assert.equal(result.status, "block");
  assert.ok(
    result.checks.some(
      (item) => item.code === "consent:person-1" && item.status === "block",
    ),
  );
});

test("character generation blocks when authorization context was not resolved", () => {
  const brief = makeBrief({ characterIds: ["character-1"] });
  const result = runPreflight({ brief });

  assert.equal(result.status, "block");
  assert.ok(
    result.checks.some(
      (item) => item.code === "consent:character-1" && item.status === "block",
    ),
  );
});

test("preflight blocks reference counts above the selected model contract", () => {
  const result = runPreflight({ resolvedReferenceCounts: { image: 3 } });

  assert.equal(result.status, "block");
  assert.ok(
    result.checks.some(
      (item) => item.code === "image_reference_limit" && item.status === "block",
    ),
  );
});

test("preflight blocks illegal duration, aspect ratio, and resolution before submit", () => {
  const brief = makeBrief();
  const plan = makePlan(brief, {
    output: {
      mediaType: "video",
      durationSeconds: 20,
      aspectRatio: "21:9",
      resolution: "4k",
    },
    shots: [{ index: 1, durationSeconds: 20, action: "Long reveal." }],
  });

  const result = runPreflight({ brief, plan });

  assert.equal(result.status, "block");
  for (const code of [
    "duration_contract",
    "aspect_ratio_contract",
    "resolution_contract",
  ]) {
    assert.ok(
      result.checks.some((item) => item.code === code && item.status === "block"),
      `expected ${code} to block`,
    );
  }
});

test("compiled request must pin the model contract used by preflight", () => {
  const result = runPreflight({ request: { model: undefined } });

  assert.equal(result.status, "block");
  assert.ok(
    result.checks.some(
      (item) => item.code === "model_contract" && item.status === "block",
    ),
  );
});

test("compiled output settings cannot silently diverge from the production plan", () => {
  const result = runPreflight({ request: { resolution: "720p" } });

  assert.equal(result.status, "block");
  assert.ok(
    result.checks.some(
      (item) =>
        item.code === "compiled_resolution_mismatch" && item.status === "block",
    ),
  );
});

test("required asset locks must be present and approved", () => {
  const brief = makeBrief();
  const plan = makePlan(brief, {
    assets: [
      {
        assetLockId: "product-lock",
        alias: "@product",
        role: "product",
        required: true,
      },
    ],
  });

  const result = runPreflight({
    brief,
    plan,
    assetLocks: [
      {
        id: "product-lock",
        alias: "@product",
        kind: "product",
        referenceIds: ["ref-1"],
        invariants: [],
        revision: 1,
        approvalStatus: "draft",
      },
    ],
  });

  assert.equal(result.status, "block");
  assert.ok(
    result.checks.some(
      (item) => item.code === "asset_lock:product-lock" && item.status === "block",
    ),
  );
});

test("compliant final generation passes pure preflight", () => {
  const result = runPreflight({ estimatedCostUsd: 0.5 });
  assert.equal(result.status, "pass");
  assert.equal(result.checks.some((item) => item.status === "block"), false);
});
