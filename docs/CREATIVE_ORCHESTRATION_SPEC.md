# Creative Orchestration Specification

Status: design contract for the next implementation slice

This document turns the Higgsfield architecture teardown into a provider-neutral design that fits the current AI Content Factory V2 without rewriting the working generation stack.

## 1. Design rule

The current generation stack is an **execution layer**. Keep it that way.

```text
Creative orchestration
    decides WHAT to make
          |
          v
GenerationRequest
          |
          v
Generation router
    decides WHERE/HOW to execute
```

Do not move creative planning, shot decomposition, brand state, or prompt-engineering rules into `providers/openrouter.ts` or `providers/comfyui.ts`.

## 2. Existing seam

Today the portable execution contract is:

```ts
GenerationRequest {
  prompt
  projectId?
  characterId?
  referenceIds?
  idempotencyKey?
  tier?
  provider?
  model?
  duration?
  resolution?
  aspectRatio?
  generateAudio?
  inputReferences?
  frameImages?
  providerOptions?
}
```

This is useful precisely because it is small. The orchestration layer should compile down into this contract rather than replacing it.

## 3. Proposed domain objects

### CreativeBrief

Represents user/business intent before model-specific decisions.

```ts
interface CreativeBrief {
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
```

Initial `CreativeIntent` values should be deliberately small:

```text
product_still
product_to_video
ugc_ad
cinematic_video
reference_video
image_edit
video_edit
```

Add intents only when they correspond to a real workflow with different planning/compilation needs.

### AssetLock

Canonical production reference that must remain stable across generations.

```ts
interface AssetLock {
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
```

Use stable internal IDs even if human-facing aliases resemble Higgsfield-style `@name` tags.

### ProductionPlan

Provider/model-neutral description of the production task.

```ts
interface ProductionPlan {
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
```

A `ProductionPlan` is the canonical creative record. A generated prompt is not.

### ShotPlan

```ts
interface ShotPlan {
  index: number;
  durationSeconds?: number;
  framing?: string;
  optics?: string;
  camera?: string;
  action: string;
  endState?: string;
  activeAssetLockIds?: string[];
}
```

Not every model requires shot-level structure. The compiler is free to flatten this into prose for simpler models.

### ContinuityLock

```ts
interface ContinuityLock {
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
```

These are the structured equivalent of production prompt locks. QA should eventually score lock compliance.

## 4. Model Contract Registry

The current provider router mostly selects by configured provider + tier. Add a separate capability layer that answers:

> Which execution targets can satisfy this ProductionPlan?

Suggested shape:

```ts
interface ModelContract {
  provider: GenerationProvider;
  model: string;
  mediaType: "image" | "video" | "audio" | "3d";
  capabilities: {
    textToMedia: boolean;
    imageReferences?: number;
    videoReferences?: number;
    audioReferences?: number;
    firstFrame?: boolean;
    lastFrame?: boolean;
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
```

Provider metadata is the preferred source. Tested local ComfyUI workflows can publish their own contracts.

Never infer capabilities only from a model display name.

## 5. Workflow Router

The workflow router operates before provider selection.

```text
CreativeBrief
  |
  +-- intent
  +-- deliverable
  +-- available assets
  +-- reference needs
  +-- brand / identity requirements
  +-- edit vs generation
  v
WorkflowKind
```

Example mappings:

| Brief | Workflow |
| --- | --- |
| clean catalog image from product ref | `product_still` |
| approved product still -> moving ad | `product_to_video` |
| avatar/product/hook ad | `ugc_ad` |
| multi-shot narrative | `cinematic_video` |
| preserve source/reference performance | `reference_video` |
| modify source image | `image_edit` |
| modify existing clip | `video_edit` |

The router returns a reason. Persist it.

## 6. Compiler interface

A compiler turns a model-neutral plan into one or more execution requests.

```ts
interface PromptCompiler {
  id: string;
  version: string;
  supports(plan: ProductionPlan, model: ModelContract): boolean;
  compile(
    plan: ProductionPlan,
    model: ModelContract,
  ): Promise<CompiledGeneration[]>;
}
```

```ts
interface CompiledGeneration {
  compilerId: string;
  compilerVersion: string;
  model: ModelContract;
  request: GenerationRequest;
  requiredLocks: string[];
  notes?: string[];
}
```

Do not let the browser own final compiler templates. The server should own/version them.

## 7. Compiler families

Start with four families rather than model-per-file sprawl.

### A. Generic image compiler

For product concepts, reference edits, lifestyle stills, and general image generation.

Can vary output grammar by model contract but should share a common plan structure.

### B. Structured video compiler

For Seedance-like/Kling-like models that benefit from explicit camera/action/continuity instructions.

Potential compilation order:

```text
scene context
active references
opening state
shot structure
optics
camera
beats/action
performance
lighting/material/physics
audio
continuity locks
output settings
```

This is our own schema, not a requirement to copy an exact external prompt scaffold.

### C. Reference/video-edit compiler

Optimized for preserving source motion, identity, timing, or performance while changing only requested properties.

Core rule: distinguish **preserve** vs **change** fields explicitly.

### D. ComfyUI graph compiler

Does not need to emit a long prose prompt. It may compile the plan into:

- server-owned workflow ID
- prompt text
- reference bindings
- frame bindings
- LoRA / control inputs
- sampler/settings values

The output still compiles into the existing `GenerationRequest` + provider options boundary.

## 8. Preflight

Preflight happens after compilation and before `submitGeneration()`.

```ts
interface PreflightResult {
  status: "pass" | "warn" | "block";
  checks: PreflightCheck[];
  adjustments?: PreflightAdjustment[];
}
```

Minimum checks:

### Contract checks

- selected model still exists
- required reference roles are supported
- reference count <= model limit
- duration is legal
- aspect ratio is legal
- resolution is legal
- edit/extend/native-audio requirement is supported

### Factory checks

- project exists
- referenced assets exist
- real-person consent is verified
- asset locks are approved when workflow requires approval
- idempotency exists for production jobs

### Creative checks

- required locks are not contradictory
- shot timing fits requested duration
- required opening/end states are specified for controlled transitions
- source-edit workflows clearly distinguish preserved and changed properties

### Spend checks

- provider cost estimate available where possible
- estimated spend <= brief/job cap
- fan-out count is explicit

## 9. Draft / proof / final lifecycle

The existing `GenerationTier` is useful but should not carry all production semantics.

Add a render strategy to the plan:

```ts
interface RenderStrategy {
  stage: "draft" | "proof" | "final";
  requiresHumanApprovalBeforeNext?: boolean;
  allowModelChangeBetweenStages?: boolean;
}
```

Example:

```text
Draft  -> cheap storyboard/still/low-res motion
Proof  -> validate identity + composition + action
Final  -> high-resolution, expensive render
```

The same prompt compiler version can be used across stages while output contracts change.

## 10. QA diagnosis

The existing Content Factory already has QA/validation. Add a normalized failure taxonomy so routing and repair can learn from it.

Initial `FailureClass`:

```text
identity_drift
reference_mismatch
product_distortion
text_corruption
composition_failure
camera_failure
motion_failure
physics_failure
hand_object_failure
spatial_continuity_failure
lip_sync_failure
audio_failure
style_mismatch
provider_failure
```

Store:

```text
job
model
workflow
compiler version
failure class
severity
repair action
retry outcome
```

## 11. Repair planner

A repair is different from a retry.

```ts
interface RepairPlan {
  sourceJobId: string;
  failureClass: FailureClass;
  change: RepairChange;
  preserve: string[];
  reason: string;
}
```

Examples:

- identity drift -> strengthen identity lock/reference crop; preserve camera/action
- camera failure -> simplify/rewrite camera block; preserve subject/scene
- product distortion -> switch to stronger reference model or stronger product lock
- hand/object failure -> decompose action / use a better starting frame
- transient provider 5xx -> plain retry with identical inputs

The system should enforce the one-change principle where practical.

## 12. Persistence additions

Do not rush all of these into the database at once. The intended long-term entities are:

```text
creative_briefs
asset_locks
asset_lock_revisions
production_plans
compiled_generations
model_contract_snapshots
preflight_results
repair_plans
```

Minimum first slice can persist orchestration payloads as versioned JSON associated with `generation_jobs` while the schema settles.

Recommended generation-job metadata:

- creative brief ID
- production plan ID
- workflow kind
- route reason
- planner version
- compiler ID/version
- model-contract snapshot/version
- preflight status

## 13. Agent architecture

Do not create a giant agent that directly calls providers.

Recommended agent/skill split:

```text
content-director
  -> interprets brief / picks workflow

asset-director
  -> resolves characters/products/locations/refs/locks

production-planner
  -> builds scene/shot/continuity plan

prompt-compiler
  -> compiles plan for selected model family

preflight
  -> validates capability, cost, consent, structure

factory-executor
  -> calls existing factory API only

qa-director
  -> diagnoses output and proposes repair
```

These can initially be logical modules inside one service/agent skill. The important rule is separation of responsibilities, not process count.

## 14. MCP / CLI implication

If MCP or CLI tools are added, expose **high-level factory operations**, not raw provider bypasses.

Good:

```text
create_brief
plan_generation
compile_generation
preflight_generation
submit_generation
get_generation
review_generation
repair_generation
```

Bad:

```text
call_seedance_directly
run_random_comfy_graph
submit_openrouter_without_factory_job
```

Every execution path must preserve persistence, consent, spend, idempotency, QA, and provenance.

## 15. First implementation slice

The next code PR should be intentionally small:

1. add `apps/studio/lib/creative/types.ts`
2. define `CreativeBrief`, `ProductionPlan`, `ContinuityLock`, `ModelContract`, `CompiledGeneration`, `PreflightResult`
3. add a small `workflow-router.ts`
4. add `preflight.ts` with pure validation functions
5. add unit tests with no provider calls
6. keep the existing `/api/generate` path working unchanged
7. add a new internal planning path only after the types and tests stabilize

This creates the seam without prematurely building an autonomous director.

## 16. Initial acceptance tests

Before connecting orchestration to paid generation, tests should prove:

- product still brief routes to `product_still`
- UGC ad brief routes to `ugc_ad`
- video edit brief never routes to a text-to-video-only model
- real-person brief blocks without verified consent
- model contract rejects unsupported reference counts
- illegal duration/aspect/resolution blocks before provider submit
- same brief + planner/compiler version produces stable normalized plan fields
- changing a locked character revision invalidates dependent plan state
- provider adapters remain callable through existing direct execution path

## 17. Non-goals for the first slice

Do not yet:

- recreate every Higgsfield skill
- copy third-party prompt folklore wholesale
- add autonomous paid fan-out
- replace current Archon workflows
- remove Higgsfield fallback
- let clients upload arbitrary ComfyUI graphs
- build a learned router before we have benchmark data

The goal is a clean orchestration boundary that lets the factory become smarter without making the execution layer fragile.
