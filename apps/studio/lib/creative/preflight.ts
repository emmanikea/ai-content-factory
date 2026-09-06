import { expectedMediaTypeForWorkflow } from "./workflow-router";
import type {
  AssetLock,
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

function addCheck(
  checks: PreflightCheck[],
  code: string,
  status: PreflightSeverity,
  message: string,
) {
  checks.push({ code, status, message });
}

function resultStatus(checks: PreflightCheck[]): PreflightSeverity {
  return checks.reduce<PreflightSeverity>(
    (current, item) =>
      SEVERITY_RANK[item.status] > SEVERITY_RANK[current]
        ? item.status
        : current,
    "pass",
  );
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
    addCheck(
      checks,
      code,
      "warn",
      `Model contract does not declare supported ${label} values.`,
    );
  } else if (!allowed.includes(value)) {
    addCheck(
      checks,
      code,
      "block",
      `${label} ${value} is not supported by the selected model.`,
    );
  } else {
    addCheck(checks, code, "pass", `${label} ${value} is supported.`);
  }
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
    addCheck(
      checks,
      code,
      "block",
      `Selected model does not declare support for ${kind} references.`,
    );
  } else if (count > limit) {
    addCheck(
      checks,
      code,
      "block",
      `${count} ${kind} references exceed the selected model limit of ${limit}.`,
    );
  } else {
    addCheck(
      checks,
      code,
      "pass",
      `${count} ${kind} reference${count === 1 ? "" : "s"} fit the model contract.`,
    );
  }
}

function validateCharacters(checks: PreflightCheck[], context: PreflightContext) {
  const expectedIds = new Set(context.brief.characterIds ?? []);
  const byId = new Map(
    (context.consentChecks ?? []).map((item) => [item.characterId, item]),
  );

  for (const characterId of expectedIds) {
    if (!byId.has(characterId)) {
      addCheck(
        checks,
        `consent:${characterId}`,
        "block",
        `Character ${characterId} was not resolved into an authorization/consent check before preflight.`,
      );
    }
  }

  for (const consent of context.consentChecks ?? []) {
    if (
      consent.kind === "real_person" &&
      consent.consentStatus !== "verified"
    ) {
      addCheck(
        checks,
        `consent:${consent.characterId}`,
        "block",
        `Real-person character ${consent.characterId} has consent status ${consent.consentStatus}.`,
      );
    } else {
      addCheck(
        checks,
        `consent:${consent.characterId}`,
        "pass",
        consent.kind === "real_person"
          ? `Real-person character ${consent.characterId} has verified consent.`
          : `Character ${consent.characterId} does not require the real-person consent gate.`,
      );
    }
  }
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
      addCheck(
        checks,
        `asset_lock:${id}`,
        "block",
        `Required asset lock ${id} was not provided to preflight.`,
      );
    } else if (lock.approvalStatus !== "approved") {
      addCheck(
        checks,
        `asset_lock:${id}`,
        "block",
        `Required asset lock ${lock.alias} is ${lock.approvalStatus}, not approved.`,
      );
    } else {
      addCheck(
        checks,
        `asset_lock:${id}`,
        "pass",
        `Required asset lock ${lock.alias} is approved at revision ${lock.revision}.`,
      );
    }
  }
}

export function preflightGeneration(context: PreflightContext): PreflightResult {
  const checks: PreflightCheck[] = [];
  const { brief, plan, compiled } = context;
  const { request, model } = compiled;
  const expectedMedia = expectedMediaTypeForWorkflow(plan.workflow);

  if (plan.briefId !== brief.id) {
    addCheck(
      checks,
      "brief_plan_link",
      "block",
      "Production plan does not belong to the supplied creative brief.",
    );
  }

  if (plan.output.mediaType !== expectedMedia) {
    addCheck(
      checks,
      "plan_media_type",
      "block",
      `Workflow ${plan.workflow} expects ${expectedMedia} output but the plan requests ${plan.output.mediaType}.`,
    );
  } else {
    addCheck(
      checks,
      "plan_media_type",
      "pass",
      `Plan output matches the ${plan.workflow} workflow.`,
    );
  }

  if (model.mediaType !== plan.output.mediaType) {
    addCheck(
      checks,
      "model_media_type",
      "block",
      `Selected model produces ${model.mediaType}, not ${plan.output.mediaType}.`,
    );
  } else {
    addCheck(
      checks,
      "model_media_type",
      "pass",
      `Selected model produces ${model.mediaType}.`,
    );
  }

  if (!request.provider) {
    addCheck(
      checks,
      "provider_contract",
      "block",
      "Compiled generation must pin the provider used by its validated model contract.",
    );
  } else if (request.provider !== model.provider) {
    addCheck(
      checks,
      "provider_contract",
      "block",
      `Compiled request provider ${request.provider} does not match model contract provider ${model.provider}.`,
    );
  }

  if (!request.model) {
    addCheck(
      checks,
      "model_contract",
      "block",
      "Compiled generation must pin the model used by preflight.",
    );
  } else if (request.model !== model.model) {
    addCheck(
      checks,
      "model_contract",
      "block",
      `Compiled request model ${request.model} does not match model contract ${model.model}.`,
    );
  }

  if (
    request.duration !== undefined &&
    plan.output.durationSeconds !== undefined &&
    request.duration !== plan.output.durationSeconds
  ) {
    addCheck(
      checks,
      "compiled_duration_mismatch",
      "block",
      `Compiled duration ${request.duration}s does not match planned duration ${plan.output.durationSeconds}s.`,
    );
  }
  if (
    request.aspectRatio !== undefined &&
    plan.output.aspectRatio !== undefined &&
    request.aspectRatio !== plan.output.aspectRatio
  ) {
    addCheck(
      checks,
      "compiled_aspect_ratio_mismatch",
      "block",
      `Compiled aspect ratio ${request.aspectRatio} does not match planned aspect ratio ${plan.output.aspectRatio}.`,
    );
  }
  if (
    request.resolution !== undefined &&
    plan.output.resolution !== undefined &&
    request.resolution !== plan.output.resolution
  ) {
    addCheck(
      checks,
      "compiled_resolution_mismatch",
      "block",
      `Compiled resolution ${request.resolution} does not match planned resolution ${plan.output.resolution}.`,
    );
  }

  const imageCount =
    context.resolvedReferenceCounts?.image ?? request.inputReferences?.length ?? 0;
  const videoCount = context.resolvedReferenceCounts?.video ?? 0;
  const audioCount = context.resolvedReferenceCounts?.audio ?? 0;
  const frameCount = request.frameImages?.length ?? 0;
  const hasVisualSource = imageCount > 0 || videoCount > 0 || frameCount > 0;

  if (!model.capabilities.textToMedia && !hasVisualSource) {
    addCheck(
      checks,
      "text_to_media",
      "block",
      "Selected model requires source media but the compiled request contains no resolved visual reference.",
    );
  }

  if (plan.workflow === "image_edit") {
    if (!model.capabilities.imageEdit) {
      addCheck(
        checks,
        "image_edit_capability",
        "block",
        "Image-edit workflow requires a model with image-edit capability.",
      );
    }
    if (imageCount === 0) {
      addCheck(
        checks,
        "image_edit_source",
        "block",
        "Image-edit workflow requires at least one resolved source image.",
      );
    }
  }

  if (plan.workflow === "video_edit") {
    if (!model.capabilities.videoEdit) {
      addCheck(
        checks,
        "video_edit_capability",
        "block",
        "Video-edit workflow requires a model with video-edit capability.",
      );
    }
    if (videoCount === 0) {
      addCheck(
        checks,
        "video_edit_source",
        "block",
        "Video-edit workflow requires at least one resolved source video.",
      );
    }
  }

  if (plan.workflow === "product_to_video" && imageCount === 0 && frameCount === 0) {
    addCheck(
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
    frameCount === 0
  ) {
    addCheck(
      checks,
      "reference_video_source",
      "block",
      "Reference-video workflow requires at least one resolved image or video reference.",
    );
  }

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

  for (const frame of request.frameImages ?? []) {
    if (frame.frameType === "first_frame" && !model.capabilities.firstFrame) {
      addCheck(
        checks,
        "first_frame_capability",
        "block",
        "Compiled request contains a first-frame control that the selected model does not support.",
      );
    }
    if (frame.frameType === "last_frame" && !model.capabilities.lastFrame) {
      addCheck(
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
      addCheck(
        checks,
        "duration_contract",
        "warn",
        "Model contract does not declare a duration range.",
      );
    } else if (
      duration < model.durationSeconds.min ||
      duration > model.durationSeconds.max
    ) {
      addCheck(
        checks,
        "duration_contract",
        "block",
        `Duration ${duration}s is outside the model range ${model.durationSeconds.min}-${model.durationSeconds.max}s.`,
      );
    } else {
      addCheck(
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
    addCheck(
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
    addCheck(
      checks,
      "shot_timing",
      "block",
      `Planned shot timing totals ${totalShotDuration}s, exceeding the ${plan.output.durationSeconds}s output duration.`,
    );
  }

  if (plan.renderStrategy.stage !== "draft" && !request.idempotencyKey) {
    addCheck(
      checks,
      "idempotency",
      "block",
      `${plan.renderStrategy.stage} generation requires an idempotency key before paid submission.`,
    );
  } else if (plan.renderStrategy.stage === "draft" && !request.idempotencyKey) {
    addCheck(
      checks,
      "idempotency",
      "warn",
      "Draft generation has no idempotency key; retries could create duplicate spend.",
    );
  }

  const maxSpend = brief.budget?.maxEstimatedUsd;
  if (maxSpend !== undefined) {
    if (context.estimatedCostUsd === undefined) {
      addCheck(
        checks,
        "spend_cap",
        "warn",
        `Brief caps spend at $${maxSpend.toFixed(2)}, but no comparable estimate is available.`,
      );
    } else if (context.estimatedCostUsd > maxSpend) {
      addCheck(
        checks,
        "spend_cap",
        "block",
        `Estimated cost $${context.estimatedCostUsd.toFixed(2)} exceeds the brief cap of $${maxSpend.toFixed(2)}.`,
      );
    } else {
      addCheck(
        checks,
        "spend_cap",
        "pass",
        `Estimated cost $${context.estimatedCostUsd.toFixed(2)} is within the brief cap.`,
      );
    }
  }

  validateCharacters(checks, context);

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
