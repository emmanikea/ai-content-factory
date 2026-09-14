# AI Content / UGC Factory

**Turn product, creator and reference inputs into reviewable UGC/Reels without tying the factory to one expensive creative suite.**

The current system separates creative planning, rights, generation, QA, approval and assembly so each layer can improve independently.

## Current runtime policy

**Higgsfield runtime is disabled.**

The repository may contain historical Higgsfield code/research from the original prototype, but active agents and workflows must not call the Higgsfield CLI/API/MCP or use it as an automatic fallback. The default repository policy is:

```bash
ENABLE_HIGGSFIELD_RUNTIME=0
```

Do not change that switch merely to get a generation to run.

The preferred media stack is now:

```text
creative/reference/creator inputs
            |
            v
    CreativeSpec + rights
            |
            v
      production planner
            |
   +--------+----------------+
   |                         |
   v                         v
local deterministic       ComfyUI
Playwright/Remotion       workflows
FFmpeg                         |
   |                 open/local models
   |                 reusable recipes
   |                         |
   +------------+------------+
                |
                v
             QA gates
                |
                v
        approval / assembly
                |
                v
     benchmark + learning loop
```

Direct hosted models through fal remain an **optional alternative lane** while we benchmark Comfy/self-hosted workflows. The decision metric is not provider preference; it is **cost per usable approved second**.

## Product direction

UGC Studio owns the workflow rather than outsourcing the whole creative pipeline to a vendor.

Current capabilities include:

- reference-video observation and semantic analysis,
- creator identity packs and rights checks,
- CreativeSpec generation and ranking,
- model/cost planning,
- direct Wan/Kling/Seedance job compilation through fal,
- deterministic Playwright app capture,
- deterministic Remotion/FFmpeg Reel assembly,
- technical + semantic video QA,
- retry/escalation policy,
- benchmark accounting for cost, pass rate and usable seconds,
- a Comfy-first workflow-authoring layer for reusable local/self-hosted media pipelines.

The current detailed handoff is:

`ugc-studio/HANDOFF.md`

## ComfyUI

ComfyUI is the preferred reusable image/video/audio workflow engine.

Start here:

- `docs/ugc-factory/COMFY_WORKFLOW_STACK.md` — architecture, source hierarchy, workflow families and promotion rules.
- `.claude/skills/comfy-ugc-factory/SKILL.md` — instructions for coding agents building or improving Comfy workflows.
- `ugc-studio/providers/comfy/workflow-registry.json` — capability-level research/candidate/validated status.
- `ugc-studio/providers/comfy/README.md` — local bootstrap and project recipe workflow.

### Core rule

Do not fabricate large Comfy graphs from memory.

Agents should:

```text
survey current models/nodes
        -> find a working official template
        -> reproduce it on the target environment
        -> inspect real slots/schemas
        -> capture a reusable project recipe
        -> run representative inputs
        -> QA + benchmark
        -> promote to validated
```

The primary upstream sources are the official Comfy CLI skills and `Comfy-Org/workflow_templates`. Community workflows are useful references, but they are not treated as current node-schema truth.

### Default Comfy configuration

`.env.example` defaults to:

```bash
COMFY_WHERE=local
COMFY_LOCAL_URL=http://127.0.0.1:8188
COMFY_ALLOW_SPEND=0
```

The objective is to make open/local/self-hosted workflows economical enough for repeated UGC production. Paid Comfy partner nodes require deliberate spend approval rather than being silently enabled.

## UGC Studio pipeline

```text
Reference video
  -> ReferenceObservation
  -> semantic enrichment
  -> ReferenceAnalysis

Creator assets + agreement
  -> CreatorIdentityPack
  -> request-specific rights decision
  -> render asset manifest

CampaignBrief + ReferenceAnalysis
  -> CreativeSpec batch
  -> rank / plan
  -> generation route
  -> QA
  -> Reel assembly
  -> final QA
  -> benchmark ledger
  -> measured routing history
```

Read:

- `docs/ugc-factory/PRD.md`
- `docs/ugc-factory/CREATOR_AND_REFERENCE_PIPELINE.md`
- `docs/ugc-factory/DIRECT_MODEL_EXECUTION_PLAN.md`
- `docs/ugc-factory/END_TO_END_RUNBOOK.md`
- `docs/ugc-factory/COMFY_WORKFLOW_STACK.md`

## Repository layout

```text
.archon/
  scripts/ugc/                 # provider-neutral UGC planning, rights, QA, routing, benchmarks
  scripts/factory/             # original catalog-factory prototype; some paths are legacy
  workflows/                   # Archon workflows; legacy Higgsfield-specific flows are being retired

ugc-studio/
  HANDOFF.md
  schemas/                     # CampaignBrief, CreativeSpec, creator/reference/QA contracts
  examples/
  capture/                     # Playwright app capture
  assembly/                    # Remotion + FFmpeg final Reel
  providers/
    model-registry.json
    research-sources.json
    fal/                       # existing direct hosted execution lane
    comfy/                     # Comfy workflow registry, recipes and validation guidance

catalog-site/                  # original product-catalog demo/review surface
sample-videos/                 # historical curated demo output
docs/ugc-factory/              # current architecture/research/runbooks
```

## Important economics

The factory should not use an expensive video model for an entire Reel when only a few seconds require synthetic generation.

A normal Reel can combine:

- real/deterministic app capture,
- owned product footage,
- one or more short synthetic creator shots,
- generated or licensed audio,
- captions and CTA rendered deterministically,
- deterministic final edit/encoding.

For generated segments, measure:

```text
provider/workflow
model/checkpoint
recipe/prompt strategy
attempt count
compute/provider cost
QA result
approved usable seconds
```

Then compare:

`cost per usable approved second`

A nominally cheap model that fails repeatedly can be more expensive than a higher-priced model with a strong pass rate.

## Safety gates around spending

The direct fal renderer already requires explicit live/spend gates. Comfy partner-node spending follows the same principle.

A successful architecture should make it difficult for an agent to spend by accident:

- Higgsfield runtime disabled,
- paid Comfy nodes disabled by default,
- direct hosted rendering requires explicit approval,
- cheap planning/QA work happens before expensive generation,
- human approval remains available before expensive fan-out.

## Historical Higgsfield material

The original prototype proved the factory pattern using Higgsfield. That work is useful as research, but it is no longer the runtime architecture.

`docs/ugc-factory/HIGGSFIELD_SKILLS_RESEARCH.md` may still be used to extract provider-neutral creative lessons. `.claude/skills/higgsfield/SKILL.md` is research-only and explicitly forbids runtime calls.

If Higgsfield is ever reconsidered, it should return only through an explicit policy/benchmark decision—not because an old script happened to exist.

## Next build milestone

The next Comfy milestone is to take the highest-value capability candidates in `ugc-studio/providers/comfy/workflow-registry.json`, reproduce them on a real Comfy environment, capture project-owned recipes, run UGC Studio QA, and promote only the proven ones to `validated`.

Priority order:

1. product + creator keyframe composition / product placement,
2. cheap product I2V,
3. consistent creator I2V,
4. exact-audio talking creator / lip-sync,
5. licensed motion transfer,
6. cleanup/upscale/interpolation.
