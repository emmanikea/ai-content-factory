# UGC Studio Handoff

Last updated: 2026-09-17
Branch: `feat/comfy-first-ugc`
Stacked on: `feat/ugc-studio-v1` / PR #5

## Product direction

Build a UGC/Reels production system that owns the creative workflow, uses deterministic footage where possible, and treats generative models/workflows as swappable execution layers.

**Higgsfield runtime is disabled.** It is not a default route, fallback, benchmark execution path or agent generation tool. Higgsfield docs/skills may remain as research material only.

Default policy:

```bash
ENABLE_HIGGSFIELD_RUNTIME=0
COMFY_WHERE=local
COMFY_ALLOW_SPEND=0
```

## Current architecture

```text
Reference video
  -> factual observation
  -> semantic enrichment
  -> ReferenceAnalysis

Creator assets + agreement
  -> CreatorIdentityPack
  -> request-specific rights decision
  -> render asset manifest

CampaignBrief + ReferenceAnalysis
  -> CreativeSpec batch
  -> concept ranking
  -> normalized preflight execution quote
  -> explicit spend gate when paid
  -> execution route
       -> deterministic Playwright/Remotion/FFmpeg where exact media is better
       -> validated Comfy local/self-hosted workflow where available
       -> explicitly approved direct hosted model when benchmarked/needed
  -> deterministic + semantic QA
  -> final Reel assembly
  -> final QA
  -> benchmark ledger
  -> measured routing history
```

Primary metric:

`cost per usable approved second`

## Read first

- `README.md`
- `docs/ugc-factory/PRD.md`
- `docs/ugc-factory/CREATOR_AND_REFERENCE_PIPELINE.md`
- `docs/ugc-factory/DIRECT_MODEL_EXECUTION_PLAN.md`
- `docs/ugc-factory/END_TO_END_RUNBOOK.md`
- `docs/ugc-factory/COMFY_WORKFLOW_STACK.md`
- `docs/ugc-factory/HIGGSFIELD_API_RESEARCH.md`
- `.claude/skills/comfy-ugc-factory/SKILL.md`
- `ugc-studio/providers/comfy/BOOTSTRAP.md`
- `ugc-studio/providers/comfy/workflow-registry.json`
- `ugc-studio/schemas/execution-quote.schema.json`

## What changed in the Comfy-first pass

### Runtime policy

- root `.env.example` makes Comfy local-first and disables paid Comfy partner-node spending by default,
- Higgsfield runtime is explicitly disabled,
- model registry contains a first-class Comfy workflow-engine entry,
- Higgsfield remains only as disabled historical/future policy metadata,
- root README no longer tells operators to install/call Higgsfield.

### Agent knowledge

Repository skill:

`.claude/skills/comfy-ugc-factory/SKILL.md`

It teaches agents to:

1. use current official Comfy skills/live schemas,
2. search official templates before choosing a model/graph,
3. reproduce a working graph before editing it,
4. capture project-owned reusable recipes,
5. validate output through UGC Studio QA,
6. record compute/cost/retries/provenance,
7. promote workflows only after validation.

The old `.claude/skills/higgsfield/SKILL.md` is research-only and explicitly forbids runtime calls.

### Comfy workflow registry

`ugc-studio/providers/comfy/workflow-registry.json`

Initial capability families:

- product + creator composition / product placement,
- product I2V,
- creator I2V,
- exact-audio talking creator,
- motion transfer,
- realism/cleanup.

Statuses are `research`, `candidate`, `validated`, or `deprecated`. No experimental graph becomes an automatic production route merely because it exists.

### Upstream sources reviewed

Primary official sources:

- `Comfy-Org/comfy-cli` bundled agent skills,
- `Comfy-Org/workflow_templates`,
- `Comfy-Org/comfy-mcp` as optional agent control surface.

Community production reference:

- `digitalinnovator/comfyui-production-workflows` for UGC + voice, prebuilt-audio UGC, Wan Animate motion/trend transfer, Qwen product placement, realism enhancement and InfiniTalk talking avatars.

Official sources/live node schemas remain authoritative. Community graphs are patterns to reproduce/adapt, not blindly copied production dependencies.

### Higgsfield API docs — research only

Current developer docs were reviewed on 2026-09-17. They do **not** justify re-enabling Higgsfield runtime, because successful API generations are still billed through Higgsfield credits.

Useful patterns were extracted into `docs/ugc-factory/HIGGSFIELD_API_RESEARCH.md`:

- quote/estimate before spend,
- async execution IDs and terminal states,
- cancellation where supported,
- bounded worker-pool concurrency,
- backoff + jitter instead of tight polling/retry loops,
- project-owned storage rather than treating provider output URLs as permanent assets,
- model-specific schemas as higher-authority evidence than generic catalogs.

The first adopted contract is:

- `.archon/scripts/ugc/preflight_quote.py`
- `ugc-studio/schemas/execution-quote.schema.json`

The preflight quote has no Higgsfield enable switch, never marks spend approved, and rejects an injected Higgsfield route.

### Legacy spend paths retired

The old catalog prototype entry points are inert:

- `.archon/workflows/content-factory-explore.yaml`
- `.archon/workflows/content-factory-render.yaml`
- `.archon/scripts/media_worker.py`
- `.archon/scripts/factory/factory_seed.py`
- `.archon/scripts/factory/factory_render.py`
- `.archon/scripts/factory/animate_concept.py`
- `.archon/scripts/factory/animate_ugc.py`

They no longer generate media. Git history preserves the original prototype for archaeology.

A provider-policy CI check blocks known retired runtime command patterns from being reintroduced into active execution paths.

## Existing UGC Studio implementation retained from PR #5

### Reference intelligence

`.archon/scripts/ugc/observe_reference.py`

Records factual properties such as duration, dimensions, FPS, audio, source hash, scene-change candidates, segments, optional keyframes and transcript data.

`.archon/scripts/ugc/build_reference_analysis.py` and `enrich_reference_semantics.py` turn observed evidence into validated semantic structure while preserving the boundary between creative-DNA inspiration and literal licensed motion/performance transfer.

### Creator identity + rights

`.archon/scripts/ugc/build_identity_pack.py`

`.archon/scripts/ugc/prepare_creator_assets.py`

These preserve creator identity/reference provenance and derive request-specific permission for product/category/platform/date/transformation scope before literal likeness/performance use.

### CreativeSpec generation

`.archon/scripts/ugc/generate_creative_specs.py`

Expands campaign inputs across creator/hook/CTA/location/outfit combinations and maps shot roles to deterministic capture or generative execution types.

### Planning + preflight quote

`.archon/scripts/ugc/model_router.py`

`.archon/scripts/ugc/preflight_quote.py`

The router creates the dry execution plan. The preflight layer normalizes that plan into a stable quote contract containing line-item raw estimates, expected usable cost, budget-block state, quote source, and spend-gate state.

Current registry estimates are deliberately marked non-authoritative. Future direct-provider estimators or measured local GPU estimators can feed the same contract without changing product-facing approval logic.

### Direct hosted fallback/benchmark lane

`.archon/scripts/ugc/build_fal_job.py`

`ugc-studio/providers/fal/`

Current hosted routes include Wan, Kling and Seedance. They remain useful for benchmarks and cases where a validated local Comfy recipe is not yet competitive. They still require rights/spend/live gates before execution.

### Deterministic app capture + assembly

`ugc-studio/capture/`

- Playwright vertical capture,
- declarative click/tap/fill/wait/scroll actions,
- capture provenance.

`ugc-studio/assembly/`

- Remotion timeline,
- FFmpeg normalization,
- creator/app/B-roll sequencing,
- captions + CTA,
- loudness/faststart handling.

### QA + learning loop

`.archon/scripts/ugc/qa_video.py`

`.archon/scripts/ugc/enrich_video_qa.py`

`.archon/scripts/ugc/benchmark_metrics.py`

`.archon/scripts/ugc/retry_policy.py`

The benchmark ledger records provider/model or workflow identity, prompt strategy/version, attempt count, estimated/actual cost, QA status, usable seconds and failure codes. Failed paid attempts count as spend with zero usable seconds.

## Next Comfy milestone

Highest-value next terminal/GPU work:

1. install/verify current `comfy` CLI on the target machine,
2. run `comfy skills install --scope project` so agents get the official current skill set,
3. launch/connect local Comfy,
4. reproduce the official Qwen Image Edit 2511 product/reference composition path,
5. capture a project-owned parameterized recipe and validate product/creator fidelity,
6. reproduce an open/local LTX 2.5 product I2V path,
7. capture + validate that recipe,
8. evaluate exact-audio creator video using current official LTX audio-video paths versus InfiniTalk reference patterns,
9. evaluate Wan motion-transfer/character-replacement paths for licensed motion,
10. record measured GPU/runtime economics into the normalized execution-quote/benchmark layers,
11. benchmark each accepted recipe using the existing cost/pass-rate/usable-seconds ledger,
12. promote only proven recipes in `workflow-registry.json` from `candidate` to `validated`,
13. then add validated Comfy workflows to automatic routing.

## What can be done autonomously vs what needs the target machine

Already autonomous/repo-side:

- architecture and policy,
- workflow-source research,
- agent instructions,
- capability registry,
- normalized preflight quote contract,
- rights/CreativeSpec/QA/benchmark contracts,
- direct hosted adapter contracts,
- retirement of legacy spend paths.

Needs a machine/environment with current Comfy + models/GPU to claim real validation:

- install/launch Comfy,
- download/resolve model weights/custom nodes,
- run official templates,
- inspect actual live slots/node schemas,
- capture project recipes from graphs that really ran,
- benchmark latency/VRAM/compute cost/output quality.

Do not fabricate `validated` Comfy recipes from documentation alone.

## Provider policy CI

`.archon/scripts/ugc/check_provider_policy.py`

`.github/workflows/provider-policy.yml`

This protects against accidentally restoring known direct runtime command patterns in active scripts/workflows while still allowing historical research documents to mention Higgsfield.

## External production inputs still needed

- an actual target Comfy machine/GPU or explicitly chosen hosted Comfy target,
- approved creator/reference assets for realistic identity tests,
- real product references,
- licensed/owned motion references for literal motion transfer,
- production app auth/capture instructions when login is required,
- optional vision credential for semantic/visual QA,
- direct provider credentials only for routes intentionally benchmarked/approved.

## Merge policy

Keep this Comfy-first work stacked on PR #5 until:

- provider-policy CI passes,
- the UGC Studio tests remain green,
- no active workflow invokes the retired vendor runtime,
- the first Comfy candidate can be reproduced on the target environment before being labeled `validated`.
