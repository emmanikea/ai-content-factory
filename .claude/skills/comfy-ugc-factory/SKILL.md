---
name: comfy-ugc-factory
description: |
  Build, inspect, debug, and improve ComfyUI workflows for this UGC/Reels factory. Use for product
  placement, creator consistency, image-to-video, audio-driven talking creators, motion transfer,
  product video, UGC ads, workflow benchmarking, and Comfy workflow authoring. Higgsfield runtime is
  forbidden by default in this repository.
---

# Comfy UGC Factory

This repository is **Comfy-first and Higgsfield-off**.

Read `docs/ugc-factory/COMFY_WORKFLOW_STACK.md` before building or changing media workflows.

## Non-negotiable provider rule

Do not call the Higgsfield CLI, API, MCP, SDK, or paid runtime from this repo. Do not copy an old Higgsfield command merely because it exists in git history or a legacy file.

Higgsfield material may be read as historical product/prompt research only. Re-enabling runtime use requires an explicit human decision and repository policy change.

## Load the official Comfy skills first

If the installed Comfy CLI exposes its bundled skills, use the relevant current upstream skill rather than relying on memory:

- `comfy` for discovery, templates, workflow editing/recipes, running and downloading.
- `comfy-director` for ads/multi-shot narrative, continuity, dialogue/audio and QC planning.
- `comfy-debug` after a failed Comfy job.
- `comfy-relay` when reviewing/iterating generated media.
- `comfy-build*` when the target environment needs a custom/pinned model+node build.

The live CLI/schema wins over this file if commands have changed.

## Workflow-building rule: prove, then capture

Never invent a large Comfy graph from memory.

For each requested capability:

1. Define the contract: inputs, output type, duration/aspect, product/identity requirements, audio requirements and quality tier.
2. Survey live options before choosing a model:

```bash
comfy --json knowledge pick "<capability in the user's words>"
comfy --json templates ls --type <image|video|audio> --limit 20
comfy --json nodes search <term>
```

3. Prefer an **official working template** from `Comfy-Org/workflow_templates` when one matches.
4. Fetch it, inspect slots/node schemas, and smoke-test it on the target environment.
5. Turn the proven graph into a project-owned reusable recipe using `workflow capture` and explicit parameters.
6. Add complexity incrementally and re-run after each meaningful change.
7. Feed every output through the repo's QA + benchmark path.

## Preferred source order

1. Current live Comfy node/model schemas.
2. Official `Comfy-Org/workflow_templates` templates and blueprints.
3. Official Comfy CLI skills/knowledge.
4. Project-owned validated recipes in `ugc-studio/providers/comfy/recipes/`.
5. Community production workflows as patterns/benchmarks only.

Community graphs are never source of truth for current node names, schemas, model availability or pricing.

## Candidate UGC workflow families

Evaluate these families rather than forcing one model to do everything:

### Product / creator composition

Start with current official Qwen Image Edit workflows/blueprints. The goal is an approved keyframe where the creator, product, pose, location and framing are correct before spending compute on video.

Typical use:

```text
creator reference + product reference + scene instruction
  -> image edit/composition
  -> visual QA
  -> approved hero frame
```

### Product I2V / B-roll

Start with current official open/local LTX or Wan I2V templates. Keep motion prompts about movement/camera; do not redundantly redesign an already-approved frame.

### Creator I2V

Use an approved hero frame as the visual anchor. Favor short shots and continuity. Do not generate a full Reel as one expensive opaque video when only a few seconds need synthetic motion.

### Exact-audio talking creator

Prefer workflows where the **exact approved audio drives the video/lip movement**. Evaluate current official LTX image+audio-to-video paths and production-tested talking-avatar patterns such as InfiniTalk. Voice generation and lip-sync are separate quality gates unless the chosen workflow explicitly couples them and has been benchmarked.

### Motion/performance transfer

Only use licensed/owned motion references accepted by the existing rights layer. Evaluate current Wan V2V/Animate/character-replacement patterns. The motion reference supplies performance/timing; creator identity comes from approved creator assets.

### Realism / cleanup / finishing

Keep realism enhancement, upscale and interpolation downstream of creative approval when possible. Do not pay to upscale a shot that may be rejected for concept/identity/product fidelity.

## Recipe authoring

For reusable new work, prefer Comfy's current recipe path instead of committing mystery API JSON.

Example shape only — discover the real slots first:

```bash
comfy templates fetch <official-template> --out ref.json
comfy --json workflow slots ref.json
comfy --json run --workflow ref.json --where local --wait > run.json
comfy --json download --out-dir ./out < run.json

comfy --json workflow capture ref.json \
  --name <capability-name> \
  --param <real-prompt-slot>=prompt \
  --param <real-seed-slot>=seed \
  -o ugc-studio/providers/comfy/recipes/<capability>.recipe.json
```

Do not reuse slot IDs from this skill; they are intentionally placeholders.

For graph changes, use structured Comfy workflow operations and the live node schema. If a known-working graph exists, derive from it rather than retyping its wiring.

## Project workflow registry

Before using a project workflow, inspect:

`ugc-studio/providers/comfy/workflow-registry.json`

Statuses:

- `research` — useful upstream lead only.
- `candidate` — selected for local validation but not trusted yet.
- `validated` — reproduced on the declared target with dependencies/provenance captured.
- `deprecated` — do not use for new work.

Never route production work to `research` or `candidate` merely because the file exists.

## Local-first cost rule

Default `COMFY_WHERE=local`.

Open/local workflows may consume GPU compute but do not incur a model-vendor generation fee. Record measured GPU/hosting cost when available.

Paid Comfy partner nodes are allowed only behind explicit spend approval. Never solve an execution error by casually adding `--allow-spend`.

Direct fal routes can still be benchmarked as hosted alternatives. The planner should choose using measured `cost per usable approved second`, not brand preference.

## Quality loop

For every candidate recipe:

```text
working official/community reference
  -> reproduce
  -> parameterize
  -> run representative inputs
  -> deterministic QA
  -> visual/semantic QA
  -> human review where needed
  -> record cost/time/retries
  -> improve
  -> repeat
  -> promote to validated
```

For creator/product work, explicitly inspect:

- product shape/branding fidelity,
- face/identity consistency,
- hands/anatomy,
- text artifacts,
- lip-sync/audio match where applicable,
- temporal warping,
- continuity between shots,
- natural UGC framing rather than over-polished ad aesthetics.

## Narrative ads

For multi-shot ads, use the current `comfy-director` methodology: concept -> screenplay -> shot list -> continuity strategy -> audio -> production -> conform -> QC.

Do not render eight unrelated attractive clips and call it a story. Preserve the existing UGC Studio principle that deterministic app/product footage should remain deterministic and synthetic video should be used only where it adds value.

## Failure handling

If a job fails:

1. Read the structured CLI error/hint.
2. Use `comfy-debug` and live node schemas.
3. Do not guess at node names, enum values or wiring.
4. Do not switch to Higgsfield as an automatic fallback.
5. Do not switch to a paid partner node without spend approval.
6. Record the failed attempt when it incurred compute/provider cost.

## Done means reproducible

A workflow task is not complete because an image/video rendered once. Complete means another agent can reproduce it from repository state plus documented model/node dependencies, understand the inputs/outputs, run it through QA, and know whether it is experimental or validated.
