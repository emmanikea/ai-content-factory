---
name: content-studio
description: Use when building, operating, debugging, or extending the AI Content Factory generation stack, including OpenRouter video, ComfyUI workflows, characters, references, routing, cost controls, QA, or GPU workers.
---

# AI Content Factory Studio

Read `docs/OPEN_GENERATION_STACK.md` and `AGENTS.md` before making changes.

## Mental model

The product owns the workflow. Models are replaceable workers.

```text
operator/agent -> generation router -> OpenRouter OR ComfyUI -> output -> QA -> approval/library
```

Never couple product UI directly to a named model or vendor.

## Common tasks

### Add a hosted model

Do not create a new provider for every OpenRouter model. Confirm the model and capabilities from OpenRouter's current video model endpoint, then configure/select its model slug through the existing OpenRouter adapter.

### Add a self-hosted model

1. Build/test the graph in ComfyUI.
2. Export **API-format** workflow JSON.
3. Store it under `workflows/comfy/<model>/<workflow>.json`.
4. Document required custom nodes/checkpoints separately; never commit model weights.
5. Add bindings/config rather than hard-coding node IDs throughout the application.
6. Test with dry-run/mock infrastructure before real GPU spend.

### Change routing

Edit the central generation router only. Routing should consider requested tier, provider availability, capability, cost, and eventually queue health. Keep paid multi-model fan-out explicitly opt-in.

### Generation debugging

Check in order:

1. request validation
2. selected provider/model
3. provider response/job ID
4. polling status
5. output retrieval
6. storage
7. QA
8. cost ledger

Do not retry paid generations blindly.

## Provider contracts

Keep the portable request small. Put provider-specific settings in `providerOptions`.

OpenRouter uses the async video lifecycle (`POST /api/v1/videos`, poll the returned job). ComfyUI uses its prompt queue/history lifecycle. Treat both as asynchronous jobs.

## Agent/MCP direction

MCP is not required to generate video; the server-side REST adapters are the application path. Add MCP later as an agent convenience layer around safe high-level operations such as:

- `generate_video`
- `get_generation`
- `list_generation_costs`
- `list_characters`
- `start_worker`
- `stop_worker`

MCP tools must call the same application services rather than bypassing cost controls.

## Spend safety

Before any change that can multiply paid calls, state the fan-out explicitly and add a limit. Tests must never submit real generation jobs.
