# UGC Factory Status and Next Steps

Last updated: 2026-09-17

This is the current project checkpoint for the AI Content Factory / UGC Studio work. It is intentionally written as the place to answer four questions:

1. What have we already built?
2. What decisions are currently locked?
3. What is unfinished or blocked?
4. What should happen next, in order?

## Current branch and PR state

### PR #5 — UGC Studio v1

- Branch: `feat/ugc-studio-v1`
- Base: `main`
- State: open draft
- Current head reviewed: `db63ce75e8d98f72d264f3d93f8aa23952f240e7`
- Scope: provider-independent UGC generation, creator/reference rights, direct-provider execution, deterministic capture/assembly, QA, benchmark learning.

PR #5 has continued moving after PR #6 was created. Its newer work includes additional direct-provider execution paths and a first-class Higgsfield API lane.

That creates an intentional architecture conflict with PR #6, where the current decision is to keep Higgsfield runtime disabled.

### PR #6 — Comfy-first UGC runtime

- Branch: `feat/comfy-first-ugc`
- Base: `feat/ugc-studio-v1`
- State: open draft
- Current pre-documentation head: `f35ffe4f4ed4ee15c290e01b14c4cad6134ed25d`
- Scope: Comfy-first workflow architecture, Higgsfield runtime retirement, workflow registry/agent skill, provider-policy CI, preflight quote contract.

At this checkpoint, the branches are **diverged**:

- PR #6 is 25 commits ahead of its merge base with PR #5.
- PR #6 is 10 commits behind the latest PR #5.
- Shared merge base: `5bcf8a1016614bb5a01f7a4156d18e9cb7012e8c`.

The latest tests run on the current PR #6 implementation before this documentation-only update were green:

- UGC Studio tests: success
- Provider Policy: success

## Product direction

Build a provider-neutral UGC/Reels production factory where we own the creative logic, rights, workflow definitions, QA, assembly, storage, and performance learning.

Generation engines are replaceable execution layers.

Target architecture:

```text
campaign / product / creator / reference inputs
                    |
                    v
          rights + CreativeSpec
                    |
                    v
            production planner
                    |
                    v
          preflight execution quote
                    |
             explicit spend gate
                    |
       +------------+-------------+
       |            |             |
       v            v             v
 deterministic    ComfyUI      direct APIs
 Playwright       preferred     optional
 Remotion         local/self    hosted
 FFmpeg           hosted
       |            |             |
       +------------+-------------+
                    |
                    v
                   QA
                    |
                    v
             human approval
                    |
                    v
        final assembly + storage
                    |
                    v
          benchmark / learning
```

Primary metric:

`cost per usable approved second`

## Decisions currently locked

### 1. Higgsfield runtime stays off

Higgsfield can be used as research material, but it is not currently an execution provider.

Allowed:

- public Higgsfield docs,
- public Higgsfield skills,
- model capability research,
- prompt/workflow/UX research.

Disabled:

- Higgsfield API generation,
- Higgsfield CLI generation,
- Higgsfield MCP generation,
- Higgsfield SDK generation,
- automatic Higgsfield fallback,
- spending Higgsfield credits.

Default policy remains:

```bash
ENABLE_HIGGSFIELD_RUNTIME=0
COMFY_WHERE=local
COMFY_ALLOW_SPEND=0
```

### 2. Comfy is the preferred reusable generative workflow layer

Use current official Comfy skills, templates, live node schemas, and proven graphs.

Agents should not invent large workflow JSON from memory.

Workflow promotion path:

```text
official/current working graph
  -> reproduce it
  -> capture project-owned recipe
  -> parameterize
  -> run QA
  -> benchmark
  -> promote candidate -> validated
  -> allow automatic routing
```

### 3. Exact product/UI media stays deterministic when possible

Use Playwright, Remotion, FFmpeg, owned media, or real product/app capture instead of asking a video model to recreate exact UI/product truth.

### 4. Paid execution requires an explicit spend gate

Planning and quoting are no-spend operations.

A paid route does not become approved merely because it is selected by a router.

### 5. Provider/model price alone does not decide routing

The decision metric is measured:

`cost per usable approved second`

Retries, failed generations, QA failures, and unusable output count against the route.

## What has been implemented

### A. Reference intelligence

Implemented in PR #5:

- factual reference observation,
- duration/dimensions/FPS/audio/source hashing,
- scene-change and segment extraction,
- optional keyframes/transcript evidence,
- semantic ReferenceAnalysis,
- separation of creative inspiration from literal motion/performance transfer.

Important files include:

- `.archon/scripts/ugc/observe_reference.py`
- `.archon/scripts/ugc/build_reference_analysis.py`
- `.archon/scripts/ugc/enrich_reference_semantics.py`

### B. Creator identity and rights

Implemented:

- portable CreatorIdentityPack,
- creator/reference provenance,
- request-specific rights evaluation,
- product/category/platform/date/transformation scope,
- active revocation handling,
- stored-job rights/spend clearing when applicable,
- prevention of unauthorized literal likeness/performance reuse.

Important files include:

- `.archon/scripts/ugc/build_identity_pack.py`
- `.archon/scripts/ugc/prepare_creator_assets.py`

### C. CreativeSpec generation

Implemented:

- CampaignBrief -> multiple CreativeSpec variants,
- variation across creators, hooks, CTAs, locations, outfits,
- source-type assignment for deterministic vs generated shots.

Important file:

- `.archon/scripts/ugc/generate_creative_specs.py`

### D. Routing and cost planning

Implemented:

- provider/model registry,
- model capability filtering,
- estimated generation cost,
- measured pass-rate support,
- measured cost-per-usable-second support,
- quality-tier routing,
- dry production planning,
- budget-cap blocking.

Important file:

- `.archon/scripts/ugc/model_router.py`

### E. Provider-neutral preflight quote

Implemented in PR #6:

- normalized quote schema,
- line-item cost estimates,
- expected usable cost,
- budget cap,
- quote provenance,
- authoritative/non-authoritative estimate flag,
- explicit spend-required state,
- `spend_approved=false` at preflight,
- rejection of injected Higgsfield runtime routes.

Important files:

- `.archon/scripts/ugc/preflight_quote.py`
- `.archon/scripts/ugc/test_preflight_quote.py`
- `ugc-studio/schemas/execution-quote.schema.json`

### F. Direct hosted provider work

PR #5 includes direct hosted execution/benchmark work for routes including:

- fal,
- OpenRouter,
- Google Veo,
- Gemini/Google multimodal video paths.

The hosted lane remains useful for:

- benchmarks,
- temporary capacity,
- models not available locally,
- cases where measured hosted economics outperform self-hosting.

Any newer PR #5 Higgsfield execution work must be removed, disabled, or isolated when PR #5 and PR #6 are reconciled.

### G. Deterministic product/app capture

Implemented:

- Playwright vertical app capture,
- declarative click/tap/fill/wait/scroll actions,
- capture provenance.

Location:

- `ugc-studio/capture/`

### H. Final assembly

Implemented:

- Remotion timeline assembly,
- FFmpeg normalization,
- creator/app/B-roll sequencing,
- captions,
- CTA,
- audio controls,
- 1080x1920 output path,
- loudness/faststart handling.

Location:

- `ugc-studio/assembly/`

### I. QA and benchmark learning

Implemented:

- deterministic video QA,
- optional semantic/visual QA,
- identity/anatomy/text checks,
- provider-neutral benchmark metrics,
- retry policy,
- failed paid attempts counted as spend with zero usable seconds,
- measured pass-rate / usable-second economics feeding routing after enough samples.

Important files:

- `.archon/scripts/ugc/qa_video.py`
- `.archon/scripts/ugc/enrich_video_qa.py`
- `.archon/scripts/ugc/benchmark_metrics.py`
- `.archon/scripts/ugc/retry_policy.py`

### J. Comfy-first workflow system

Implemented in PR #6:

- Comfy as a first-class workflow engine in the model registry,
- local/self-hosted default policy,
- no paid Comfy partner nodes by default,
- project Comfy agent skill,
- Comfy bootstrap guide,
- workflow registry,
- official upstream source snapshot,
- community workflow reference research,
- workflow promotion states: `research`, `candidate`, `validated`, `deprecated`.

Important files:

- `.claude/skills/comfy-ugc-factory/SKILL.md`
- `docs/ugc-factory/COMFY_WORKFLOW_STACK.md`
- `ugc-studio/providers/comfy/README.md`
- `ugc-studio/providers/comfy/BOOTSTRAP.md`
- `ugc-studio/providers/comfy/UPSTREAM_SNAPSHOT.md`
- `ugc-studio/providers/comfy/workflow-registry.json`

Current workflow candidates include:

- Qwen Image Edit product/creator composition,
- product placement,
- LTX product I2V,
- creator I2V,
- LTX image+audio-to-video,
- exact-audio talking creator,
- Wan motion/performance transfer,
- character replacement,
- realism/cleanup,
- upscale/interpolation.

None is labeled `validated` without a real target-machine run.

### K. Higgsfield research without Higgsfield runtime

Reviewed current Higgsfield developer docs and retained useful provider-neutral ideas:

- estimate before spend,
- async execution IDs,
- terminal job states,
- cancellation,
- bounded concurrency,
- backoff + jitter,
- copy provider outputs to project-owned storage,
- prefer model-specific schemas over generic catalogs.

Important file:

- `docs/ugc-factory/HIGGSFIELD_API_RESEARCH.md`

These ideas were copied into our architecture, not into a Higgsfield runtime integration.

### L. Legacy Higgsfield runtime paths retired

Old catalog prototype paths were made inert so an agent cannot accidentally find an old command and spend Higgsfield credits.

A provider-policy CI check blocks known retired Higgsfield execution patterns from being reintroduced into active execution paths.

Important files:

- `.archon/scripts/ugc/check_provider_policy.py`
- `.github/workflows/provider-policy.yml`

## What is not finished

### Repository/branch reconciliation

This is the immediate blocker.

PR #5 moved after PR #6 was created. We need to reconcile the latest PR #5 into the Comfy-first branch and resolve provider policy intentionally.

Expected outcome after reconciliation:

- keep useful newer PR #5 provider-neutral work,
- keep Fal/OpenRouter/Google/direct lanes where useful,
- remove/disable active Higgsfield generation,
- preserve preflight/spend gates,
- preserve Comfy-first workflow policy,
- rerun all tests and provider-policy CI.

### Real Comfy execution

We have candidate workflow references and authoring policy, but no target GPU environment has been connected here.

Still required:

- install/launch current Comfy,
- install current Comfy CLI,
- install official project agent skills,
- resolve/download actual models,
- resolve required custom nodes,
- inspect live node schemas/slots,
- execute workflows,
- capture project-owned recipes from graphs that actually ran.

### Validated recipes

No candidate should become automatic routing until it runs and passes QA.

First recipes to validate:

1. Qwen product + creator composition.
2. LTX/Wan product I2V.
3. Creator I2V.
4. Exact-audio talking creator.
5. Wan motion/performance transfer.

### Comfy execution adapter

The next repo-side implementation should provide a provider-neutral adapter that can:

- load only `validated` project recipes for production,
- allow candidates only in explicit experimental mode,
- parameterize a recipe,
- submit asynchronously,
- preserve Comfy `prompt_id`,
- watch status,
- cancel where supported,
- download/normalize outputs,
- store provenance,
- send outputs into existing QA,
- record measured runtime/GPU economics,
- fail closed on paid partner nodes unless spend is explicitly approved.

### Project-owned artifact storage

The architecture decision exists, but the complete production path still needs to ensure accepted outputs are copied into canonical project-owned storage rather than depending on provider URLs.

### First complete end-to-end UGC ad

The project is not complete until one real example can travel through:

```text
product + approved creator/reference
  -> CreativeSpec
  -> preflight
  -> generation
  -> QA
  -> deterministic app/product footage
  -> Remotion/FFmpeg assembly
  -> final QA
  -> canonical artifact
  -> benchmark record
```

## Clear next steps

### P0 — Reconcile PR #5 and PR #6

Do this before more provider/runtime implementation.

1. Bring the latest `feat/ugc-studio-v1` changes into `feat/comfy-first-ugc`.
2. Review every conflict involving providers, registries, spend policy, README/runbooks, and tests.
3. Preserve the explicit Higgsfield-off decision.
4. Keep useful Fal/OpenRouter/Google provider work.
5. Run provider-policy CI and all UGC tests.
6. Update this status document if the architecture changes.

### P1 — Finish Comfy runtime scaffolding

Can be done repo-side without claiming media validation.

1. Add a Comfy executor/adapter abstraction.
2. Add project recipe loading.
3. Enforce `validated`-only automatic production routing.
4. Add experimental mode for candidate recipes.
5. Normalize job lifecycle to:
   `planned -> approved -> queued -> running -> succeeded|failed|canceled`.
6. Persist execution/provenance metadata.
7. Connect outputs to existing QA and benchmark contracts.
8. Add tests for paid-node/spend-policy failures.

### P2 — Choose and prepare one GPU environment

Need one real target, not several.

1. Choose local GPU, rented GPU, or deliberate hosted Comfy target.
2. Install/verify current Comfy and `comfy-cli`.
3. Run:
   `comfy skills install --scope project`.
4. Verify an agent can discover templates/nodes/models and submit a trivial job.

### P3 — Validate the minimum UGC recipe set

Validate in this order:

1. **Qwen Image Edit** — real product naturally placed with creator.
2. **LTX/Wan I2V** — approved still -> short product/creator movement.
3. **Audio-driven creator video** — approved creator image + exact audio -> believable talking UGC.
4. **Wan motion transfer** — only for owned/licensed performance references.

For every workflow:

- start from a current working official graph,
- reproduce it on the actual environment,
- capture our own recipe,
- parameterize inputs,
- record model/node versions,
- record seed and attempts,
- run QA,
- record compute cost and latency,
- promote to `validated` only after repeatable success.

### P4 — Produce the first complete UGC ad

Target:

```text
product image
  -> Qwen placement/composition
  -> approved creator frame
  -> audio-driven creator shot
  -> product/app B-roll
  -> captions + CTA
  -> final vertical assembly
  -> QA
```

Success means we have a finished ad without Higgsfield runtime.

### P5 — Benchmark and automate routing

After enough real runs:

1. compare Comfy vs direct hosted APIs,
2. calculate pass rate,
3. calculate attempts per accepted output,
4. calculate actual cost,
5. calculate usable approved seconds,
6. use `cost per usable approved second` to route automatically.

### P6 — Merge sequence

Do not merge the current divergent stack blindly.

Preferred sequence after reconciliation and validation:

1. reconcile PR #6 with latest PR #5,
2. keep PR #6 green,
3. merge the Comfy-first policy/work into the UGC Studio branch or otherwise produce one coherent branch,
4. review the combined UGC Studio diff against `main`,
5. merge to `main` only when rights, spend, provider-policy, tests, docs, and at least the required runtime milestone are satisfactory.

## What can be done autonomously from the repo

No GPU required:

- branch reconciliation,
- remove/disable conflicting Higgsfield runtime code,
- Comfy adapter interface,
- recipe loader,
- job lifecycle contract,
- spend-policy enforcement,
- queue/concurrency contracts,
- provenance schema,
- storage handoff contract,
- tests,
- documentation,
- PR/handoff maintenance.

## What requires a real environment or operator input

Needs actual runtime/assets:

- GPU/Comfy environment,
- model downloads,
- custom-node resolution,
- real workflow execution,
- VRAM/latency measurement,
- visual quality review,
- approved creator assets,
- product reference assets,
- licensed motion references,
- production app authentication for protected capture,
- explicit approval for any paid benchmark.

## Immediate definition of done

The next major checkpoint is achieved when:

- latest PR #5 and PR #6 are reconciled,
- Higgsfield runtime is still off,
- CI is green,
- one Comfy GPU environment is connected,
- Qwen product composition is validated,
- one I2V workflow is validated,
- one exact-audio creator workflow is validated,
- a complete vertical UGC ad is assembled and passes QA,
- actual runtime/cost/pass-rate data is recorded.

At that point the project moves from **well-defined architecture + implementation scaffolding** to a **working production prototype**.
