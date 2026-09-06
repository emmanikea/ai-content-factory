import { expectedMediaTypeForWorkflow } from "./workflow-router";
import type {
  AssetLock,
  ModelContract,
  PreflightCheck,
  PreflightContext,
  PreflightResult,
  PreflightSeverity,
} from "./types";

const SEVERITY_RANK: Record<PreflightSeverity, number> = {
  pass: 0,
  warn: 1,
  block: 2,
};

function resultStatus(checks: PreflightCheck[]): PreflightSeverity {
  return checks.reduce<PreflightSeverity>(
    (current, check) =>
      SEVERITY_RANK[check.status] > SEVERITY_RANK[current]
        ? check.status
        : current,
    "pass",
  );
}

function check(
  checks: PreflightCheck[],
  code: string,
  status: PreflightSeverity,
  message: string,
) {
  checks.push({ code, status, message });
}

function validateEnumValue(
  checks: PreflightCheck[],
  code: string,
  label: string,
  value: string | undefined,
  allowed: string[] | undefined,
) {
  if (!value) return;
  if (!allowed?.length) {
    check(
      checks,
      code,
      "warn",
      `Model contract does not declare supported ${label} values.`,
    );
    return;
  }
  if (!allowed.includes(value)) {
    check(
      checks,
      code,
      "block",
      `${label} ${value} is not supported by the selected model.`,
    );
    return;
  }
  check(checks, code, "pass", `${label} ${value} is supported.`);
}

function validateReferenceCount(
  checks: PreflightCheck[],
  kind: "image" | "video" | "audio",
  count: number,
  limit: number | undefined,
) {
  if (count <= 0) return;
  const code = `${kind}_reference_limit`;
  if (limit === undefined || limit <= 0) {
    check(
      checks,
      code,
      "block",
      `Selected model does not declare support for ${kind} references.`,
    );
    return;
  }
  if (count > limit) {
    check(
      checks,
      code,
      "block",
      `${count} ${kind} references exceed the selected model limit of ${limit}.`,
    );
    return;
  }
  check(
    checks,
    code,
    "pass",
    `${count} ${kind} reference${count === 1 ? "" : "s"} fit the model contract.`,
  );
}

function validateRequiredLocks(
  checks: PreflightCheck[],
  requiredIds: Set<string>,
  assetLocks: AssetLock[] | undefined,
) {
  if (!requiredIds.size) return;

  const byId = new Map((assetLocks ?? []).map((lock) => [lock.id, lock]));
  for (const id of requiredIds) {
    const lock = byId.get(id);
    if (!lock) {
      check(
        checks,
        `asset_lock:${id}`,
        "block",
        `Required asset lock ${id} was not provided to preflight.`,
      );
      continue;
    }
    if (lock.approvalStatus !== "approved") {
      check(
        checks,
        `asset_lock:${id}`,
        "block",
        `Required asset lock ${lock.alias} is ${lock.approvalStatus}, not approved.`,
      );
      continue;
    }
    check(
      checks,
      `asset_lock:${id}`,
      "pass",
      `Required asset lock ${lock.alias} is approved at revision ${lock.revision}.`,
    );
  }
}

function validateModelCapabilities(
  checks: PreflightCheck[],
  context: PreflightContext,
  model: ModelContract,
) {
  const { brief, plan, compiled } = context;
  const { request } = compiled;
  const expectedMedia = expectedMediaTypeForWorkflow(plan.workflow);

  if (plan.output.mediaType !== expectedMedia) {
    check(
      checks,
      "plan_media_type",
      "block",
      `Workflow ${plan.workflow} expects ${expectedMedia} output but the plan requests ${plan.output.mediaType}.`,
    );
  } else {
    check(
      checks,
      "plan_media_type",
      "pass",
      `Plan output matches the ${plan.workflow} workflow.`,
    );
  }

  if (model.mediaType !== plan.output.mediaType) {
    check(
      checks,
      "model_media_type",
      "block",
      `Selected model produces ${model.mediaType}, not ${plan.output.mediaType}.`,
    );
  } else {
    check(
      checks,
      "model_media_type",
      "pass",
      `Selected model produces ${model.mediaType}.`,
    );
  }

  if (request.provider && request.provider !== model.provider) {
    check(
      checks,
      "provider_contract",
      "block",
      `Compiled request provider ${request.provider} does not match model contract provider ${model.provider}.`,
    );
  }

  if (request.model && request.model !== model.model) {
    check(
      checks,
      "model_contract",
      "block",
      `Compiled request model ${request.model} does not match model contract ${model.model}.`,
    );
  }

  if (
    !model.capabilities.textToMedia &&
    !(context.resolvedReferenceCounts?.image ||
      context.resolvedReferenceCounts?.video ||
      request.inputReferences?.length ||
      request.frameImages?.length)
  ) {
    check(
      checks,
      "text_to_media",
      "block",
      "Selected model requires source media but the compiled request contains no resolved visual reference.",
    );
  }

  if (plan.workflow === "image_edit" && !model.capabilities.imageEdit) {
    check(
      checks,
      "image_edit_capability",
      "block",
      "Image-edit workflow requires a model with image-edit capability.",
    );
  }

  if (plan.workflow === "video_edit" && !model.capabilities.videoEdit) {
    check(
      checks,
      "video_edit_capability",
      "block",
      "Video-edit workflow requires a model with video-edit capability.",
    );
  }

  const imageCount =
    context.resolvedReferenceCounts?.image ?? request.inputReferences?.length ?? 0;
  const videoCount = context.resolvedReferenceCounts?.video ?? 0;
  const audioCount = context.resolvedReferenceCounts?.audio ?? 0;

  validateReferenceCount(
    checks,
    "image",
    imageCount,
    model.capabilities.imageReferences,
  );
  validateReferenceCount(
    checks,
    "video",
    videoCount,
    model.capabilities.videoReferences,
  );
  validateReferenceCount(
    checks,
    "audio",
    audioCount,
    model.capabilities.audioReferences,
  );

  if (
    plan.workflow === "product_to_video" &&
    imageCount === 0 &&
    !request.frameImages?.length
  ) {
    check(
      checks,
      "product_source_reference",
      "block",
      "Product-to-video workflow requires an image reference or controlled frame input.",
    );
  }

  if (
    plan.workflow === "reference_video" &&
    imageCount === 0 &&
    videoCount === 0 &&
    !request.frameImages?.length
  ) {
    check(
      checks,
      "reference_video_source",
      "block",
      "Reference-video workflow requires at least one resolved image or video reference.",
    );
  }

  for (const frame of request.frameImages ?? []) {
    if (frame.frameType === "first_frame" && !model.capabilities.firstFrame) {
      check(
        checks,
        "first_frame_capability",
        "block",
        "Compiled request contains a first-frame control that the selected model does not support.",
      );
    }
    if (frame.frameType === "last_frame" && !model.capabilities.lastFrame) {
      check(
        checks,
        "last_frame_capability",
        "block",
        "Compiled request contains a last-frame control that the selected model does not support.",
      );
    }
  }

  const duration = request.duration ?? plan.output.durationSeconds;
  if (duration !== undefined) {
    if (!model.durationSeconds) {
      check(
        checks,
        "duration_contract",
        "warn",
        "Model contract does not declare a duration range.",
      );
    } else if (
      duration < model.durationSeconds.min ||
      duration > model.durationSeconds.max
    ) {
      check(
        checks,
        "duration_contract",
        "block",
        `Duration ${duration}s is outside the model range ${model.durationSeconds.min}-${model.durationSeconds.max}s.`,
      );
    } else {
      check(
        checks,
        "duration_contract",
        "pass",
        `Duration ${duration}s fits the model contract.`,
      );
    }
  }

  validateEnumValue(
    checks,
    "aspect_ratio_contract",
    "Aspect ratio",
    request.aspectRatio ?? plan.output.aspectRatio,
    model.aspectRatios,
  );
  validateEnumValue(
    checks,
    "resolution_contract",
    "Resolution",
    request.resolution ?? plan.output.resolution,
    model.resolutions,
  );

  if (
    (request.generateAudio || plan.audio?.requireNativeAudio) &&
    !model.capabilities.nativeAudio
  ) {
    check(
      checks,
      "native_audio_capability",
      "block",
      "The plan requires native audio but the selected model contract does not support it.",
    );
  }

  const totalShotDuration = plan.shots.reduce(
    (sum, shot) => sum + (shot.durationSeconds ?? 0),
    0,
  );
  if (
    plan.output.durationSeconds !== undefined &&
    totalShotDuration > plan.output.durationSeconds
  ) {
    check(
      checks,
      "shot_timing",
      "block",
      `Planned shot timing totals ${totalShotDuration}s, exceeding the ${plan.output.durationSeconds}s output duration.`,
    );
  }

  if (
    plan.renderStrategy.stage !== "draft" &&
    !compiled.request.idempotencyKey
  ) {
    check(
      checks,
      "idempotency",
      "block",
      `${plan.renderStrategy.stage} generation requires an idempotency key before paid submission.`,
    );
  } else if (
    plan.renderStrategy.stage === "draft" &&
    !compiled.request.idempotencyKey
  ) {
    check(
      checks,
      "idempotency",
      "warn",
      "Draft generation has no idempotency key; retries could create duplicate spend.",
    );
  }

  const maxSpend = brief.budget?.maxEstimatedUsd;
  if (maxSpend !== undefined) {
    if (context.estimatedCostUsd === undefined) {
      check(
        checks,
        "spend_cap",
        "warn",
        `Brief caps spend at $${maxSpend.toFixed(2)}, but no comparable estimate is available.`,
      );
    } else if (context.estimatedCostUsd > maxSpend) {
      check(
        checks,
        "spend_cap",
        "block",
        `Estimated cost $${context.estimatedCostUsd.toFixed(2)} exceeds the brief cap of $${maxSpend.toFixed(2)}.`,
      );
    } else {
      check(
        checks,
        "spend_cap",
        "pass",
        `Estimated cost $${context.estimatedCostUsd.toFixed(2)} is within the brief cap.`,
      );
    }
  }
}

export function preflightGeneration(context: PreflightContext): PreflightResult {
  const checks: PreflightCheck[] = [];
  const { brief, plan, compiled } = context;

  if (plan.briefId !== brief.id) {
    check(
      checks,
      "brief_plan_link",
      "block",
      "Production plan does not belong to the supplied creative brief.",
    );
  }

  validateModelCapabilities(checks, context, compiled.model);

  for (const consent of context.consentChecks ?? []) {
    if (
      consent.kind === "real_person" &&
      consent.consentStatus !== "verified"
    ) {
      check(
        checks,
        `consent:${consent.characterId}`,
        "block",
        `Real-person character ${consent.characterId} has consent status ${consent.consentStatus}.`,
      );
    } else {
      check(
        checks,
        `consent:${consent.characterId}`,
        "pass",
        consent.kind === "real_person"
          ? `Real-person character ${consent.characterId} has verified consent.`
          : `Character ${consent.characterId} does not require the real-person consent gate.`,
      );
    }
  }

  const requiredLockIds = new Set([
    ...plan.assets
      .filter((binding) => binding.required)
      .map((binding) => binding.assetLockId),
    ...compiled.requiredLocks,
  ]);
  validateRequiredLocks(checks, requiredLockIds, context.assetLocks);

  return {
    status: resultStatus(checks),
    checks,
  };
}
