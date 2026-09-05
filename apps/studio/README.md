# Generation Studio

Internal operator UI for the open generation stack.

## Run locally

```bash
cd apps/studio
cp .env.example .env.local
npm install
npm run dev
```

Open `http://localhost:3000`.

## Fastest setup: OpenRouter only

Set:

```bash
OPENROUTER_API_KEY=...
OPENROUTER_VIDEO_MODEL=google/veo-3.1-lite
```

The Studio submits a video job to OpenRouter and returns immediately. Use **Refresh** to poll its current status. No GPU setup is required.

Before production use, query OpenRouter's current `/api/v1/videos/models` capabilities and constrain the UI to valid duration/resolution/aspect-ratio combinations for the selected model.

## Add ComfyUI

Run ComfyUI locally or on a rented GPU and set:

```bash
COMFYUI_BASE_URL=http://127.0.0.1:8188
```

The adapter expects an API-format ComfyUI workflow. Provide it server-side as either:

- `providerOptions.workflow`, or
- `COMFYUI_WORKFLOW_JSON`.

Do **not** copy random workflow JSON into application code. Export a tested API-format workflow from ComfyUI and version it under the repository's `workflows/comfy/` directory first.

If both backends are configured, Draft/Standard prefers ComfyUI and Quality/Max prefers OpenRouter unless the caller explicitly selects a provider.

## Current limitations

This is the first integration slice, not the completed product:

- Jobs are not persisted yet.
- Refresh is manual rather than background polling.
- Reference upload/storage UI is not implemented yet.
- Cost ledger is specified but not persisted yet.
- ComfyUI model workflows are intentionally not fabricated; a real tested H3/LTX graph must be imported.
- `max` does not fan out to multiple paid models yet; that is deliberately disabled until spend controls are in place.

See `../../docs/OPEN_GENERATION_STACK.md` for the implementation roadmap.
