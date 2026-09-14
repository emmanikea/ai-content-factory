# Comfy-First Workflow Stack

Last reviewed: 2026-09-14

## Decision

UGC Studio must not depend on Higgsfield at runtime.

Higgsfield is disabled and treated only as historical research/benchmark material unless a future operator deliberately re-enables it. No active Archon workflow, default route, agent skill, or production runbook should instruct an agent to spend Higgsfield credits.

ComfyUI is the preferred workflow layer for reusable image/video/audio pipelines because it can run open models locally or on self-hosted GPUs, exposes workflow graphs instead of hiding orchestration inside a vendor product, and has official CLI/MCP/agent tooling.

This does **not** mean every generation must run inside Comfy. Deterministic Playwright/Remotion/FFmpeg work stays deterministic, and direct hosted APIs such as fal may remain available when a benchmark shows they beat the local workflow on cost per usable approved second.

## Target architecture

```text
Campaign / Reference / Creator inputs
               |
               v
      CreativeSpec + rights gate
               |
               v
         production planner
               |
       +-------+--------+
       |                |
       v                v
  deterministic       ComfyUI
 Playwright/FFmpeg   workflow engine
       |                |
       |       +--------+--------+---------+
       |       |        |        |         |
       |     image    I2V/V2V   audio   lip-sync/
       |     edit      models    TTS     avatars
       |       |        |        |         |
       +-------+--------+--------+---------+
                       |
                       v
                  QA + approval
                       |
                       v
                Remotion assembly
                       |
                       v
              benchmark / learning
```

Hosted direct APIs are an alternate lane, not the center of the architecture:

```text
production planner -> fal/direct model -> same QA/benchmark contract
```

## Agent knowledge stack

Use sources in this order.

### 1. Official Comfy CLI skills — primary agent operating manual

Upstream: `Comfy-Org/comfy-cli/comfy_cli/skills/`

Important skills as of 2026-09-14:

- `comfy` — discovery, model selection, templates, workflow editing, recipes, run/download, local/cloud routing.
- `comfy-director` — narrative ads and multi-shot video: screenplay, shot planning, continuity, audio, conform and QC.
- `comfy-debug` — diagnose failed jobs from actual error codes and live node schemas.
- `comfy-relay` — media preview/review loop.
- `comfy-build` / `comfy-build-authoring` — build custom Comfy environments when a workflow needs a pinned node/model stack.
- `comfy-deploy` — deployment path when we deliberately want hosted/serverless Comfy execution.

These upstream skills change. Agents must inspect the installed/current version rather than assuming an old command surface.

### 2. Official Comfy workflow templates — primary graph source

Upstream: `Comfy-Org/workflow_templates`

Rule: **derive from a graph that already works before hand-authoring one.**

The official repository contains templates, reusable subgraph blueprints, model metadata, validation, and agent instructions. Candidate references currently relevant to UGC include:

- `templates/image_qwen_image_edit_2511.json` — reference-preserving image editing; useful for product placement, wardrobe/location edits, and product/creator composition.
- `blueprints/image_edit_qwen_2511.json` — reusable Qwen edit building block.
- `video_ltx2_5_i2v` — open/local image-to-video reference path.
- LTX image/audio-to-video templates — candidate talking/performance workflows where exact audio should drive the shot.
- Wan video-to-video / character replacement templates — candidate motion/performance transfer path.
- pose/depth/control preprocessors and interpolation utilities — continuity/control building blocks.

Template names are discovery hints, not pinned truth. Before using one, run the live Comfy template/node discovery commands and verify the required models/nodes against the target Comfy installation.

### 3. Community production workflows — reference/benchmark only

`digitalinnovator/comfyui-production-workflows` is useful because it publishes production-oriented examples for:

- AI UGC + voice cloning
- AI UGC + prebuilt audio
- Wan 2.2 Animate trend/motion transfer
- Qwen multi-character consistency
- Qwen product placement
- InfiniTalk talking avatars
- realism enhancement

Do not copy a community graph blindly into production. Use it to identify a useful pattern, compare it to current official templates/live schemas, then capture a project-owned recipe and validate it.

## How agents should build a workflow

The workflow-authoring loop is deliberately evidence-first:

1. **Define the capability contract.** Inputs, required output, quality constraints, target duration/aspect, identity/product fidelity, and whether audio must be exact.
2. **Survey live options.** Use `comfy knowledge pick`, `comfy templates ls`, `comfy nodes ls/search`, and the current model/node catalog.
3. **Start from an official working template when one matches.** Fetch it and inspect its slots. Do not recreate the graph from memory.
4. **Run a small smoke test before extending it.** Prove the base graph works on the actual target environment.
5. **Convert the proven graph into a project-owned reusable recipe.** Prefer `comfy workflow capture` + `workflow apply` for new reusable work. Parameterize prompts, source assets, seeds, dimensions, duration and other fields the factory must vary.
6. **Add only one capability at a time.** Product preservation, character consistency, motion, audio, lip sync, upscale and final conform are independently testable concerns.
7. **Validate output.** Use the UGC Studio deterministic + semantic QA pipeline; do not treat a successful Comfy job as an approved asset.
8. **Record provenance and economics.** Workflow/recipe version, model/checkpoint, node pack versions, seed, attempts, compute/provider cost, duration and QA outcome.
9. **Promote only after benchmarks.** A workflow becomes `validated` in our registry only after repeatable outputs on the target environment.

## Recipes, not mystery JSON

For new project-owned workflows, prefer Comfy's current recipe path:

```bash
# discover a working template
comfy --json templates ls --type video --limit 20
comfy templates fetch <template> --out ref.json
comfy --json workflow slots ref.json

# smoke test it
comfy --json run --workflow ref.json --where local --wait > run.json
comfy --json download --out-dir ./out < run.json

# capture the proven graph and lift fields the factory varies
comfy --json workflow capture ref.json \
  --name ugc-i2v \
  --param <prompt-slot>=prompt \
  --param <seed-slot>=seed \
  -o ugc-i2v.recipe.json
```

The exact slot IDs must come from the fetched graph/live schema; never paste example IDs from documentation into a production recipe.

## Workflow families we should build

The repository should converge on project-owned recipes for these capabilities:

| Capability | First sources to evaluate | Purpose |
|---|---|---|
| product/creator still edit | official Qwen Image Edit 2511 | put a real product into a believable creator scene without losing product identity |
| consistent creator angles | official reference/edit templates + Qwen | hero identity -> several approved framings |
| product I2V | official LTX 2.5 I2V, current Wan I2V | cheap product motion/B-roll |
| creator I2V | current open I2V with approved hero frame | short creator performance shots |
| audio-driven creator video | official LTX image+audio video references; compare community InfiniTalk | exact spoken audio/lip movement rather than invented voice |
| motion transfer | official Wan V2V/character-replacement references; Wan Animate | licensed/owned reference motion |
| product placement | official Qwen edit + community Qwen product-placement pattern | creator reliably holds/uses the real product |
| realism/cleanup | official edit/upscale paths + community realism pattern | skin, lighting, anatomy and product cleanup |
| upscale/interpolation | official upscalers/interpolation | final-quality finishing after content is approved |

## Cost policy

The default Comfy target is `local` or self-hosted open-model execution.

Paid Comfy partner nodes are not automatically allowed. If a workflow contains a paid partner node, the run must require the same explicit spend approval used by the direct-provider path. Agents must not add `--allow-spend` merely to make a failed job run.

The comparison metric remains:

`cost per usable approved second`

A cheap workflow that needs repeated re-renders can lose to a more expensive model with a much higher pass rate. The benchmark ledger decides after enough samples.

## Higgsfield policy

- No default route.
- No active workflow should instruct an agent to invoke the Higgsfield CLI/MCP/API.
- The repo's Higgsfield skill is research-only and must not be an executable generation skill.
- Historical Higgsfield-specific code can remain temporarily for archaeology, but active workflows must not call it.
- Future re-enablement requires an explicit repository policy change; it must not happen because an agent found an old command in a file.

## Promotion checklist for a Comfy workflow

A workflow may move from `candidate` to `validated` only when:

- it runs on the declared target (`local`/self-hosted/cloud),
- model/checkpoint and custom-node dependencies are documented,
- all variable fields are explicit recipe parameters/slots,
- inputs and outputs match the UGC Studio capability contract,
- at least one real output passes technical QA,
- identity/product/reference behavior has been visually reviewed where applicable,
- retries and failures are recorded,
- no hidden paid node can spend without the explicit spend gate,
- provenance is sufficient for another agent to reproduce the run.
