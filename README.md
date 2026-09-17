# AI Content Factory

**One product catalog in, a batch of human-approved AI video ads out.**

This repository is moving toward a **Comfy-first, provider-neutral UGC factory**. Archon coordinates work; ComfyUI is the preferred reusable generation/workflow layer; deterministic tools handle exact UI/product footage; direct hosted model APIs remain optional benchmark/fallback routes.

Higgsfield runtime is disabled. Its docs and public skills may be used as research inputs, but active workflows must not invoke Higgsfield CLI, MCP, SDK, or API.

## Current working branches

- `feat/ugc-studio-v1` — current UGC Studio architecture, rights, routing, QA, direct-model benchmark lane.
- `feat/comfy-first-ugc` — stacked Comfy-first pass: disables legacy Higgsfield runtime paths and adds Comfy workflow authoring, registry, provider-policy CI, and normalized execution preflight quotes.

## Core architecture

```text
catalog / campaign / creator / references
                |
                v
        CreativeSpec + rights
                |
                v
       preflight execution quote
                |
                v
          production planner
                |
     +----------+-----------+
     |          |           |
     v          v           v
 deterministic ComfyUI   direct API
 Playwright    local/      optional
 Remotion      self-hosted  hosted
 FFmpeg
     |          |           |
     +----------+-----------+
                |
                v
              QA
                |
                v
          human approval
                |
                v
        deterministic assembly
                |
                v
       benchmark / learning loop
```

Primary production metric:

`cost per usable approved second`

## Runtime policy

Default environment policy:

```bash
ENABLE_HIGGSFIELD_RUNTIME=0
COMFY_WHERE=local
COMFY_ALLOW_SPEND=0
```

No paid provider call should happen simply because an agent found an old command in the repository.

## Where to start

Read:

- `ugc-studio/HANDOFF.md`
- `docs/ugc-factory/PRD.md`
- `docs/ugc-factory/COMFY_WORKFLOW_STACK.md`
- `docs/ugc-factory/HIGGSFIELD_API_RESEARCH.md`
- `.claude/skills/comfy-ugc-factory/SKILL.md`
- `ugc-studio/providers/comfy/BOOTSTRAP.md`
- `ugc-studio/providers/comfy/workflow-registry.json`

## Comfy workflow policy

Agents should not fabricate node graphs from memory.

The workflow loop is:

1. inspect current official Comfy skills/live schemas,
2. find an official working template,
3. reproduce it on the target Comfy environment,
4. capture a project-owned parameterized recipe,
5. run technical + semantic QA,
6. record model/node/seed/cost/attempt provenance,
7. benchmark cost per usable approved second,
8. promote to `validated` only after repeatable success.

Candidate workflow families include:

- Qwen product/creator composition and product placement,
- LTX/Wan image-to-video,
- exact-audio talking creator video,
- Wan motion/performance transfer,
- realism/cleanup,
- upscale/interpolation.

## Preflight before spend

`.archon/scripts/ugc/preflight_quote.py` converts a dry production plan into `ugc-studio/schemas/execution-quote.schema.json`.

The quote contains line-item estimates, expected usable cost, budget blocking, quote provenance, and explicit spend state. It never pre-approves paid execution and rejects Higgsfield routes.

## Legacy prototype

The original Higgsfield-specific catalog scripts/workflows are retained only as inert historical stubs. Git history preserves their former implementation; they are not active generation paths.

## Status

This repository does not claim that a Comfy workflow is production-ready merely because documentation or a JSON graph exists. Actual workflow validation requires a target Comfy/GPU environment, real model/node resolution, executed outputs, QA, and recorded benchmarks.
