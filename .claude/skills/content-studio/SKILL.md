---
name: content-studio
description: Use when building, operating, debugging, or extending the AI Content Factory generation stack, including creative orchestration, prompt compilation, OpenRouter video, ComfyUI workflows, characters, references, routing, cost controls, QA, or GPU workers.
---

# AI Content Factory Studio

Read these before making changes:

- `docs/OPEN_GENERATION_STACK.md`
- `docs/CONTENT_FACTORY_V2.md`
- `docs/HIGGSFIELD_ARCHITECTURE_TEARDOWN.md`
- `docs/CREATIVE_ORCHESTRATION_SPEC.md`
- `AGENTS.md`

## Mental model

The product owns the workflow. Models are replaceable workers.

There are two distinct routing layers:

```text
brief
  -> creative orchestration
     -> workflow / assets / production plan / prompt compiler / preflight
        -> GenerationRequest
           -> generation router
              -> OpenRouter OR ComfyUI
                 -> output -> QA -> approval/library
```

**Creative orchestration decides what should be generated. The generation router decides where/how an already-compiled job executes.**

Never put production-planning or model-specific prompt doctrine inside provider adapters.

## Creative orchestration

Treat the raw generation prompt as a compiled artifact, not the canonical creative brief.

Target flow:

```text
CreativeBrief
  -> ProductionPlan
  -> model/workflow compiler
  -> preflight
  -> GenerationRequest[]
```

The plan should carry stable asset/reference bindings and continuity locks. Compilers may differ by model family because reference grammar, camera control, edit modes, negative/positive constraints and timing syntax differ across models.

When adding orchestration:

1. preserve the existing direct `/api/generate` execution path
2. keep `GenerationRequest` small and provider-neutral
3. version planners/compilers
4. persist route reason and compiler version
5. validate capabilities before paid submission
6. diagnose failures before paid retries

## Common tasks

### Add a hosted model

Do not create a new provider for every OpenRouter model. Confirm the model and capabilities from current provider metadata, then configure/select its model slug through the existing OpenRouter adapter.

Also update or refresh the model contract used by creative preflight. A model name alone is not evidence that it supports the required references, duration, resolution or edit mode.

### Add a self-hosted model

1. Build/test the graph in ComfyUI.
2. Export **API-format** workflow JSON.
3. Store it under `workflows/comfy/<model>/<workflow>.json`.
4. Document required custom nodes/checkpoints separately; never commit model weights.
5. Add bindings/config rather than hard-coding node IDs throughout the application.
6. Publish a tested model/workflow capability contract for orchestration/preflight.
7. Test with dry-run/mock infrastructure before real GPU spend.

### Change creative routing

Change the creative/workflow router, not provider adapters.

Routing should consider user intent, deliverable, edit-vs-generation, required assets/references, identity/brand locks, and output requirements. Persist the route reason so it can be evaluated later.

### Change execution routing

Edit the central generation router only. Execution routing should consider requested tier, provider availability, capability, cost, and eventually queue health. Keep paid multi-model fan-out explicitly opt-in.

### Add or change prompt logic

Use a versioned compiler. Do not expand a single universal system prompt.

A compiler may emit:

- prompt text
- provider options
- reference-role bindings
- frame bindings
- server-owned ComfyUI workflow/binding selections

Keep final compiler templates server-side so clients and external agents cannot bypass tested production rules.

### Generation debugging

Check in order:

1. creative brief / selected workflow
2. resolved asset locks and references
3. production plan
4. selected model contract
5. compiled request
6. preflight result
7. selected execution provider/model
8. provider response/job ID
9. polling status
10. output retrieval/storage
11. QA diagnosis
12. cost ledger

Do not retry paid generations blindly. A provider retry and a creative repair are different operations.

## Provider contracts

Keep the portable `GenerationRequest` small. Put provider-specific settings in `providerOptions`.

OpenRouter uses its async video lifecycle. ComfyUI uses its prompt queue/history lifecycle. Treat both as asynchronous jobs.

The orchestration layer may use richer `ModelContract` metadata, but provider adapters remain responsible only for execution translation.

## Agent/MCP direction

MCP is not required to generate video; the server-side REST adapters are the application path. Add MCP later as an agent convenience layer around safe high-level factory operations such as:

- `create_brief`
- `plan_generation`
- `preflight_generation`
- `submit_generation`
- `get_generation`
- `review_generation`
- `repair_generation`
- `list_generation_costs`
- `list_characters`
- `start_worker`
- `stop_worker`

MCP tools must call the same application services rather than bypassing persistence, consent, cost controls, idempotency, QA, or provenance.

## Spend safety

Before any change that can multiply paid calls, state the fan-out explicitly and add a limit. Tests must never submit real generation jobs.

Use draft/proof/final as production stages when appropriate: validate composition/reference behavior cheaply before an expensive final render. Do not assume all stages need the same model.
