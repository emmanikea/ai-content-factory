import type {
  CreativeBrief,
  MediaType,
  WorkflowKind,
} from "./types";

export interface WorkflowRoute {
  workflow: WorkflowKind;
  reason: string;
}

const ROUTE_REASONS: Record<WorkflowKind, string> = {
  product_still: "Product still intent uses the product-still workflow.",
  product_to_video:
    "Product-to-video intent requires motion generation from approved product imagery.",
  ugc_ad:
    "UGC ad intent requires an advertising workflow with reusable character/product context.",
  cinematic_video:
    "Cinematic video intent requires shot, camera, timing, and continuity planning.",
  reference_video:
    "Reference-video intent requires a workflow that preserves supplied visual or performance references.",
  image_edit:
    "Image-edit intent requires preserving source-image properties while applying requested changes.",
  video_edit:
    "Video-edit intent requires preserving source-video properties while applying requested changes.",
};

const EXPECTED_MEDIA: Record<WorkflowKind, MediaType> = {
  product_still: "image",
  product_to_video: "video",
  ugc_ad: "video",
  cinematic_video: "video",
  reference_video: "video",
  image_edit: "image",
  video_edit: "video",
};

export function expectedMediaTypeForWorkflow(
  workflow: WorkflowKind,
): MediaType {
  return EXPECTED_MEDIA[workflow];
}

export function routeCreativeBrief(brief: CreativeBrief): WorkflowRoute {
  if (!brief.deliverables.length) {
    throw new Error("Creative brief must include at least one deliverable");
  }

  const workflow = brief.intent;
  const expectedMedia = expectedMediaTypeForWorkflow(workflow);
  const hasExpectedDeliverable = brief.deliverables.some(
    (deliverable) => deliverable.kind === expectedMedia,
  );

  if (!hasExpectedDeliverable) {
    throw new Error(
      `${workflow} requires at least one ${expectedMedia} deliverable`,
    );
  }

  return {
    workflow,
    reason: ROUTE_REASONS[workflow],
  };
}
