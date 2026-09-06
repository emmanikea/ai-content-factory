import type { ConsentStatus } from "../domain/types";
import type {
  GenerationProvider,
  GenerationRequest,
} from "../generation/types";

export type CreativeIntent =
  | "product_still"
  | "product_to_video"
  | "ugc_ad"
  | "cinematic_video"
  | "reference_video"
  | "image_edit"
  | "video_edit";

export type WorkflowKind = CreativeIntent;
export type MediaType = "image" | "video" | "audio" | "3d";
export type RenderStage = "draft" | "proof" | "final";

export interface DeliverableSpec {
  kind: MediaType;
  count?: number;
  durationSeconds?: number;
  aspectRatio?: string;
  resolution?: string;
  platform?: string;
}

export interface CreativeConstraint {
  kind:
    | "must_include"
    | "must_preserve"
    | "must_avoid"
    | "brand"
    | "legal"
    | "custom";
  statement: string;
  severity?: "required" | "preferred";
}

export interface CreativeBrief {
  id: string;
  projectId: string;
  intent: CreativeIntent;
  objective?: string;
  concept: string;
  audience?: string;
  platform?: string;
  deliverables: DeliverableSpec[];
  characterIds?: string[];
  referenceIds?: string[];
  brandLockId?: string;
  constraints?: CreativeConstraint[];
  budget?: {
    maxEstimatedUsd?: number;
    optimization?: "quality" | "balanced" | "cost";
  };
}

export interface LockInvariant {
  kind:
    | "identity"
    | "appearance"
    | "geometry"
    | "text"
    | "color"
    | "spatial"
    | "continuity"
    | "custom";
  statement: string;
  severity?: "required" | "preferred";
}

export interface AssetLock {
  id: string;
  alias: string;
  kind:
    | "character"
    | "product"
    | "location"
    | "wardrobe"
    | "prop"
    | "style"
    | "audio";
  referenceIds: string[];
  canonicalDescription?: string;
  invariants: LockInvariant[];
  revision: number;
  approvalStatus: "draft" | "approved" | "invalidated";
}

export interface AssetLockBinding {
  assetLockId: string;
  alias: string;
  role?: string;
  required?: boolean;
}

export interface SpatialRelation {
  subject: string;
  relation: string;
  object?: string;
  value?: string;
}

export interface ShotPlan {
  index: number;
  durationSeconds?: number;
  framing?: string;
  optics?: string;
  camera?: string;
  action: string;
  endState?: string;
  activeAssetLockIds?: string[];
}

export interface PerformancePlan {
  direction?: string;
  dialogue?: string[];
  beats?: string[];
}

export interface LightingPlan {
  direction?: string;
  palette?: string[];
  continuity?: string;
}

export interface AudioPlan {
  dialogue?: string[];
  music?: string;
  ambience?: string;
  soundEffects?: string[];
  requireNativeAudio?: boolean;
}

export interface OutputSpec {
  mediaType: MediaType;
  count?: number;
  durationSeconds?: number;
  aspectRatio?: string;
  resolution?: string;
}

export interface RenderStrategy {
  stage: RenderStage;
  requiresHumanApprovalBeforeNext?: boolean;
  allowModelChangeBetweenStages?: boolean;
}

export interface ContinuityLock {
  kind:
    | "identity"
    | "wardrobe"
    | "product"
    | "location"
    | "headcount"
    | "spatial"
    | "screen_direction"
    | "prop_ownership"
    | "lighting"
    | "camera"
    | "audio"
    | "custom";
  assetLockId?: string;
  statement: string;
  severity: "required" | "preferred";
}

export interface ProductionPlan {
  id: string;
  briefId: string;
  workflow: WorkflowKind;
  routeReason: string;
  assets: AssetLockBinding[];
  sceneContext: string;
  openingState?: string;
  spatialLayout?: SpatialRelation[];
  shots: ShotPlan[];
  performance?: PerformancePlan;
  lighting?: LightingPlan;
  materialPhysics?: string[];
  audio?: AudioPlan;
  continuityLocks: ContinuityLock[];
  output: OutputSpec;
  renderStrategy: RenderStrategy;
  plannerVersion: string;
}

export interface ModelContract {
  provider: GenerationProvider;
  model: string;
  mediaType: MediaType;
  capabilities: {
    textToMedia: boolean;
    imageReferences?: number;
    videoReferences?: number;
    audioReferences?: number;
    firstFrame?: boolean;
    lastFrame?: boolean;
    imageEdit?: boolean;
    videoEdit?: boolean;
    videoExtend?: boolean;
    nativeAudio?: boolean;
    identityReference?: boolean;
    textRendering?: "weak" | "usable" | "strong";
  };
  aspectRatios?: string[];
  resolutions?: string[];
  durationSeconds?: { min: number; max: number };
  costClass?: "low" | "medium" | "high";
  latencyClass?: "fast" | "medium" | "slow";
  snapshotAt: string;
}

export interface CompiledGeneration {
  compilerId: string;
  compilerVersion: string;
  model: ModelContract;
  request: GenerationRequest;
  requiredLocks: string[];
  notes?: string[];
}

export type PreflightSeverity = "pass" | "warn" | "block";

export interface PreflightCheck {
  code: string;
  status: PreflightSeverity;
  message: string;
}

export interface PreflightAdjustment {
  field: string;
  from?: string | number | boolean;
  to: string | number | boolean;
  reason: string;
}

export interface PreflightResult {
  status: PreflightSeverity;
  checks: PreflightCheck[];
  adjustments?: PreflightAdjustment[];
}

export interface ConsentCheck {
  characterId: string;
  kind: "real_person" | "synthetic" | "brand_mascot";
  consentStatus: ConsentStatus;
}

export interface PreflightContext {
  brief: CreativeBrief;
  plan: ProductionPlan;
  compiled: CompiledGeneration;
  assetLocks?: AssetLock[];
  consentChecks?: ConsentCheck[];
  estimatedCostUsd?: number;
  resolvedReferenceCounts?: {
    image?: number;
    video?: number;
    audio?: number;
  };
}

export type FailureClass =
  | "identity_drift"
  | "reference_mismatch"
  | "product_distortion"
  | "text_corruption"
  | "composition_failure"
  | "camera_failure"
  | "motion_failure"
  | "physics_failure"
  | "hand_object_failure"
  | "spatial_continuity_failure"
  | "lip_sync_failure"
  | "audio_failure"
  | "style_mismatch"
  | "provider_failure";

export interface RepairPlan {
  sourceJobId: string;
  failureClass: FailureClass;
  change: string;
  preserve: string[];
  reason: string;
}
