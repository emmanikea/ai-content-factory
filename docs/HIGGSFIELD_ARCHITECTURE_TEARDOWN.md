# Higgsfield Architecture Teardown

Status: research/design reference for AI Content Factory V2

This document reverse-engineers the **publicly observable** architecture behind Higgsfield's current agent skills, CLI-facing workflows, prompt-building tutorials, and the third-party OSideMedia reconstruction. It is not a claim that we possess Higgsfield's private system prompt or backend source.

The goal is narrower and more useful: identify the production patterns that explain why Higgsfield feels more capable than a simple model picker, then decide what the Content Factory should **adopt, improve, or avoid**.

## 1. Evidence levels

Use these labels throughout this document.

- **A — official/public implementation:** Higgsfield's own `higgsfield-ai/skills` repository, CLI-facing contracts, official docs, and published workflow instructions.
- **B — official/public workflow evidence:** Higgsfield tutorials that publish exact generated prompts and downloadable Claude skills, but do not expose the private backend enhancer itself.
- **C — third-party reconstruction:** OSideMedia's `higgsfield-ai-prompt-skill`. Useful because it consolidates and tests public Higgsfield behavior, but it is not authoritative for private internals.
- **D — Content Factory inference:** architecture we infer from A–C and should validate through our own experiments.

Primary sources:

- https://github.com/higgsfield-ai/skills
- https://github.com/higgsfield-ai/cli
- https://higgsfield.ai/blog/Seedance-4k
- https://higgsfield.ai/blog/Santiago-breakdown
- https://higgsfield.ai/blog/case4k
- https://higgsfield.ai/blog/seedance-prompting-guide
- https://github.com/OSideMedia/higgsfield-ai-prompt-skill

## 2. The important finding

Higgsfield is not best understood as:

```text
prompt -> model -> image/video
```

The public architecture is much closer to:

```text
user intent
   |
   v
intent / workflow router
   |
   +--> specialist skill
   |      - product photoshoot
   |      - marketplace cards
   |      - brand kit
   |      - generic generation
   |      - Soul identity
   |      - marketing studio
   |      - etc.
   |
   v
context + asset resolver
   |
   v
prompt / production-plan compiler
   |
   v
model capability + schema preflight
   |
   v
execution surface (CLI/API)
   |
   v
generation model
   |
   v
QA / approval / iteration
```

The core product advantage is therefore not one secret prompt. It is the **system around prompts**.

## 3. Layer 1 — intent routing, not one universal prompt

**Evidence: A**

The official skill bundle routes requests into specialist workflows rather than asking one giant system prompt to understand everything.

Examples from the official skills:

- generic image/video/audio/3D -> `higgsfield-generate`
- product photography -> `higgsfield-product-photoshoot`
- marketplace listing assets -> `higgsfield-marketplace-cards`
- visual identity / brand systems -> `higgsfield-brandkit`
- consistent identity -> Soul workflow
- branded ads / UGC -> Marketing Studio path inside generation

The routing rules are intentionally semantic. Product Photoshoot says to choose a mode by **intent, not surface keyword**, and includes explicit tie-breakers such as platform/format taking priority over scene wording.

### What to adopt

Build a first-class `CreativeIntent` / `WorkflowKind` layer above the current generation router. Do not make providers or individual model names the primary user-facing decision.

Examples for our product:

- `product_still`
- `product_lifestyle`
- `ugc_ad`
- `talking_creator`
- `cinematic_scene`
- `social_carousel`
- `marketplace_listing`
- `brand_asset`
- `image_edit`
- `video_edit`
- `reference_to_video`

### What to improve

Higgsfield's public skills still encode many routing decisions as prose. We should make the route decision inspectable and persisted:

```text
brief -> intent -> selected workflow -> reason -> compiler version -> execution plan
```

That gives us reproducibility, analytics, and the ability to measure whether routing decisions were actually good.

### What to avoid

Do not turn every model into its own product workflow. A model is an execution capability, not a user goal.

## 4. Layer 2 — asset-first production

**Evidence: B**

Higgsfield's filmmaking tutorials repeatedly use the same production rule: build and lock the **characters, locations, and props** before generating scenes.

The Santiago workflow explicitly treats a screenplay as an asset-discovery mechanism: the script tells the system which reusable entities must exist. Character sheets, location sheets, wardrobe/prop sheets, and named Elements are created first and reused across shots.

The public prompt-builder workflow uses matching tags such as `@character`, `@location`, and `@prop`, so prompt construction and reference attachment share the same names.

### What to adopt

Our existing V2 `characters` and `references` entities are the correct foundation, but they should become part of a richer **Asset Lock** system.

An Asset Lock should capture:

- canonical identity/reference IDs
- role: character / product / location / wardrobe / prop / style / audio
- exact reusable description
- approved source assets
- variant relationship
- provenance + consent where relevant
- invariants that must survive generation

The prompt compiler should consume references by ID, not rediscover or re-describe them from scratch each time.

### What to improve

Higgsfield's named Element system is excellent for humans. We should pair a human-readable alias with a stable internal ID:

```text
@maya -> reference_id=ref_01J...
@kitchen -> reference_id=ref_01K...
```

The alias can change; the underlying asset identity should not.

### What to avoid

Do not rely on the LLM remembering a character description across independent generations. Persist the lock and inject the exact canonical version.

## 5. Layer 3 — prompt compilation is model/workflow-specific

**Evidence: A + B**

The official Product Photoshoot skill says the agent should **not write the final GPT Image prompt itself**. It sends a short structured intent to a backend prompt enhancer holding mode-specific photography vocabulary and structural templates.

Marketplace Cards does the same thing: user intent and listing context are collected, while marketplace compliance rules and final prompt templates remain in a backend enhancer.

This is an architectural signal: the user-facing agent is not the final prompt authority.

For Seedance filmmaking, Higgsfield's public tutorials show a prompt-builder skill turning a scene into structured production instructions: shot framing, camera, action timing, references, lighting, continuity, and positive locks.

### What to adopt

Separate:

```text
Creative Brief
```

from:

```text
Compiled Prompt
```

The Content Factory should have model/workflow-specific prompt compilers:

```text
compile(ProductionPlan, ModelContract) -> CompiledGeneration
```

A compiler may output:

- a prose prompt
- structured JSON
- a ComfyUI binding payload
- reference-role mappings
- frame controls
- negative/positive constraints
- provider-specific options

The current `GenerationRequest.prompt` should remain the low-level execution field. It should not be the canonical representation of creative intent.

### What to improve

Version every compiler and store both the normalized plan and compiled output.

That enables:

- prompt A/B tests
- regression tests
- model migrations
- deterministic re-runs
- quality analysis by compiler version

### What to avoid

Do not maintain one giant universal prompt template. Different models respond to different grammar, reference mechanisms, negative constraints, timing syntax, and camera language.

## 6. Layer 4 — production blocks and positive locks

**Evidence: B + C**

Official Higgsfield examples expose a recurring long-form production grammar. Published Seedance examples contain sections such as:

- scene context
- format / shot structure
- optics / framing
- camera
- action
- lighting / style / material / physics
- audio
- continuity constraints
- positive locks

OSideMedia formalizes the same family of ideas into a larger block scaffold and a linter. Treat the exact 17-block reconstruction as **C evidence**, not as a private Higgsfield system prompt.

The important design principle is independent of the exact block count: production prompts work better when **state, spatial relationships, camera behavior, action, timing, audio, and invariants are separated instead of blended into one paragraph**.

### What to adopt

Our internal `ProductionPlan` should be structured, for example:

```text
scene_context
references[]
spatial_layout
opening_state
shot_structure[]
optics
camera
beats[]
performance
lighting
material_physics
audio
continuity_locks[]
output_settings
```

The model compiler decides which fields become literal prompt blocks.

### Positive locks

A particularly reusable concept is the positive lock: describe the desired invariant as a positive state rather than relying on unsupported negative prompting.

Examples of lock categories:

- identity
- wardrobe
- product geometry / label
- location topology
- screen direction
- headcount
- prop ownership
- camera continuity
- lighting continuity
- audio continuity

We should persist these as structured constraints and track lock violations in QA.

## 7. Layer 5 — live capability discovery beats static assumptions

**Evidence: A**

The official `higgsfield-generate` skill repeatedly instructs the agent to inspect the live model schema rather than inventing parameters. It separates models from workflows and validates media roles, duration, aspect ratio, resolution, mode, and other constraints before submission.

The public guidance also distinguishes models with similar names by actual capabilities rather than chronology. For example, a newer specialized model can have lower resolution or different reference modes than another version.

### What to adopt

Add a **Model Contract Registry** above provider adapters.

A contract should describe at minimum:

- provider + model ID
- media type
- input roles
- reference limits
- aspect ratios
- duration range
- resolutions
- audio support
- edit / extend capabilities
- text rendering ability
- identity/reference strength
- latency/cost class
- live availability timestamp

The creative router should select against capabilities, not hard-coded brand folklore.

### What to improve

Persist model-contract snapshots and detect drift. OSideMedia's spec-sync / drift approach is worth copying conceptually.

We should know when a provider changes:

- model IDs
- enums
- prices
- reference limits
- duration
- resolution

before paid jobs begin failing.

### What to avoid

Do not silently coerce impossible creative requests into a random provider/model combination. Return an explicit route adjustment or compile error.

## 8. Layer 6 — preflight before expensive generation

**Evidence: A + C**

Official Higgsfield skills verify model contracts before paid generation and include cost/confirmation gates in some application flows.

OSideMedia goes further with a preflight linter that checks structural rules and model enums before credits are spent.

### What to adopt

Introduce a `preflight()` stage between compilation and execution.

Checks should include:

1. model supports required media roles
2. references are present and resolved
3. real-person consent/provenance passes
4. duration/aspect/resolution are legal
5. compiler output contains required blocks for that workflow
6. no contradictory locks
7. estimated spend <= configured cap
8. idempotency key exists for retryable production work

Preflight should never submit a generation.

### What to improve

Use preflight as a structured result, not only exceptions:

```text
PASS
WARN + adjustments
BLOCK + reasons
```

Persist the result so failed jobs can be distinguished from jobs that were correctly prevented from launching.

## 9. Layer 7 — state and approvals are product logic

**Evidence: A**

The official Brandkit skill is unusually revealing. It maintains durable state, explicit approval events, dependency relationships, invalidation rules, and deterministic tooling. It does not infer approval from successful generation.

A palette revision can invalidate a generated logo and downstream dependents. Typography changes do not necessarily invalidate the symbol. Only affected outputs are regenerated.

This is a dependency graph, not a chat history.

### What to adopt

Our current V2 `approval_events` and entities should evolve toward **dependency-aware creative state**.

For assets/plans, persist:

- revision
- approved status
- dependencies
- invalidated_by
- compiler version
- generation source

Changing a locked asset should invalidate only dependent work.

### What to improve

Create a reusable dependency mechanism across brand assets, characters, scenes, ads, and campaigns rather than hard-coding invalidation per workflow.

### What to avoid

Do not regenerate an entire campaign because one scene or reference failed.

## 10. Layer 8 — deterministic tools where generative models are weak

**Evidence: A**

Brandkit deliberately uses deterministic local SVG/HTML/PPTX/PDF tooling for exact copy, editable layout, previews, exports, and geometry checks. Generative models are used where generative variation is valuable, not as a universal hammer.

### What to adopt

The Content Factory should explicitly classify production operations:

**Generative:**
- image/video synthesis
- restyling
- scene variation
- ideation

**Deterministic:**
- text overlays
- subtitles
- logos
- final compositing
- resizing/cropping when no generative fill is needed
- manifests
- packaging/export
- analytics

### What to improve

The production planner should be allowed to choose a deterministic tool instead of a model. This saves cost and increases fidelity.

## 11. Layer 9 — evaluation and iteration are first-class

**Evidence: A + B + C**

Higgsfield's official repo includes eval scenarios. Official Seedance guidance says to review the full clip, change one thing per iteration, and scale resolution after the composition is correct.

OSideMedia extends this into failure-mode references, quality memory, filter memory, and preflight tooling.

### What to adopt

Our existing QA gate should evolve from generic scoring into **diagnosis -> targeted repair**.

A failed result should record a reason such as:

- identity drift
- product distortion
- text corruption
- motion failure
- camera instruction ignored
- spatial continuity break
- hand/object interaction failure
- lip-sync failure
- style mismatch
- reference bleed

Then the repair planner changes the smallest responsible input.

### What to improve

Measure quality at the level of:

```text
workflow + model + compiler version + failure class
```

This lets the router learn that one model is strong for product fidelity but weak for talking-head motion, for example.

### What to avoid

Blind retries. A retry with unchanged inputs is only justified for transient provider failures.

## 12. Layer 10 — cheap iteration before expensive final render

**Evidence: B**

Higgsfield's current Seedance guidance recommends proving composition/motion at lower resolution before scaling the same prompt to 1080p/4K.

This aligns with the original Content Factory's existing principle: cheap exploration before expensive rendering.

### What to adopt

Make `draft -> proof -> final` a production concept rather than only a provider tier.

Example:

```text
Draft: cheap still/storyboard or low-res clip
Proof: validate composition, identity, motion
Final: expensive high-res generation using locked plan
```

Do not assume that `draft` and `final` must use the same model.

## 13. What Higgsfield appears to keep private

The public skills explicitly state that some final prompt assembly remains on the backend:

- Product Photoshoot: mode-specific photography vocabulary and structural templates
- Marketplace Cards: marketplace compliance rules and prompt templates

Therefore we should not assume that cloning the public skills reproduces Higgsfield's exact production behavior.

What we *can* reproduce is the architecture:

```text
structured intent -> specialist compiler -> private/versioned templates -> model contract -> generation
```

For us, the compiler/templates are not hidden for secrecy's sake; they should live server-side/versioned so clients and agents cannot bypass quality, safety, or spend controls.

## 14. OSideMedia: what is valuable vs what needs caution

The OSideMedia project is valuable because it adds engineering discipline around public prompt knowledge:

- dispatcher + specialist sub-skills
- model guide / decision flow
- spec snapshots
- prompt linting
- failure-mode taxonomy
- quality/filter memory
- reusable templates
- production benchmarks
- explicit distinction between prompt construction and Higgsfield execution

### Adopt conceptually

- spec snapshots and drift detection
- linter/preflight
- failure taxonomy
- quality memory
- compiler-specific templates
- regression cases

### Validate experimentally before adopting as truth

- exact prompt word-count rules
- model-specific folklore not present in official docs
- claims labeled empirical/demo/reconstructed
- any exact 17-block requirement as mandatory across all models
- model rankings that can drift quickly

## 15. Copy / improve / avoid matrix

| Pattern | Decision | Content Factory version |
| --- | --- | --- |
| specialist skill routing | COPY | `CreativeIntent -> WorkflowKind` |
| asset-first references | COPY | Asset Locks backed by stable reference IDs |
| prompt enhancer layer | COPY | versioned model/workflow compilers |
| public model schema discovery | COPY | Model Contract Registry |
| positive continuity locks | COPY | structured invariants + QA checks |
| approval state | COPY | dependency-aware revisions/approvals |
| deterministic tooling | COPY | compositor/export/tool lane |
| one-change iteration | COPY | diagnosis-driven repair planner |
| low-res proof before final | COPY | explicit draft/proof/final lifecycle |
| prose-only routing | IMPROVE | persisted routing decision + reason |
| prose-only templates | IMPROVE | typed ProductionPlan + compiler versions |
| manual quality folklore | IMPROVE | benchmark data + cost per usable asset |
| vendor-centered execution | IMPROVE | provider-neutral execution contract |
| hidden backend templates | IMPROVE | server-owned but versioned/testable internally |
| giant universal system prompt | AVOID | small dispatcher + specialist compilers |
| hard-coded model assumptions | AVOID | live contracts + snapshots |
| blind paid retries | AVOID | classify failure first |
| re-describing identities each shot | AVOID | exact Asset Lock injection |
| image model for exact layout/copy | AVOID | deterministic tools |

## 16. Recommended Content Factory architecture

```text
                         +----------------------+
                         | Studio / Agent / API |
                         +----------+-----------+
                                    |
                                    v
                         +----------------------+
                         | Creative Brief       |
                         +----------+-----------+
                                    |
                                    v
                    +---------------+----------------+
                    | Intent + Workflow Router       |
                    +---------------+----------------+
                                    |
                                    v
                    +---------------+----------------+
                    | Context / Asset Resolver       |
                    | characters, products, refs,    |
                    | brand locks, locations, props  |
                    +---------------+----------------+
                                    |
                                    v
                    +---------------+----------------+
                    | Production Planner             |
                    | shots, beats, locks, settings  |
                    +---------------+----------------+
                                    |
                                    v
                    +---------------+----------------+
                    | Model / Workflow Compiler      |
                    +---------------+----------------+
                                    |
                                    v
                    +---------------+----------------+
                    | Preflight + Spend Gate         |
                    +---------------+----------------+
                                    |
                                    v
                    +---------------+----------------+
                    | Existing Generation Router     |
                    | OpenRouter / ComfyUI / future  |
                    +---------------+----------------+
                                    |
                                    v
                    +---------------+----------------+
                    | QA + Diagnosis + Repair        |
                    +---------------+----------------+
                                    |
                         +----------+----------+
                         | Human approval      |
                         +----------+----------+
                                    |
                                    v
                         Library / campaign / publish
```

The important boundary is this:

> **The creative orchestration layer decides what should be generated. The existing generation router decides where/how the already-compiled job executes.**

## 17. How this changes V2

The current V2 request starts too low in the stack:

```ts
GenerationRequest {
  prompt,
  references,
  tier,
  provider,
  model,
  ...
}
```

That is appropriate for an execution contract and should remain.

We should add a higher-level contract rather than expanding `GenerationRequest` until it becomes a universal object:

```text
CreativeBrief
    -> ProductionPlan
    -> CompiledGeneration[]
    -> GenerationRequest[]
```

See `docs/CREATIVE_ORCHESTRATION_SPEC.md` for the proposed seam.

## 18. First implementation order

1. Add typed `CreativeBrief`, `ProductionPlan`, locks, and compile result contracts.
2. Add a workflow router with a small initial set: product still, product-to-video, UGC ad, cinematic/reference video.
3. Add a model contract registry sourced from provider metadata + tested local ComfyUI capabilities.
4. Add compiler interfaces; keep the first compiler intentionally simple.
5. Add preflight with structured PASS/WARN/BLOCK results.
6. Persist compiler version, plan, route reason, and preflight result with jobs.
7. Wire existing QA outcomes into a failure taxonomy.
8. Add targeted repair plans.
9. Build benchmark cases and let model/compiler performance drive routing.

Do not start by recreating every Higgsfield skill. Build the orchestration primitives, then add workflows only when we have a real production use case.
