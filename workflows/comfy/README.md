# ComfyUI Workflows

This directory is for tested, API-format ComfyUI workflow JSON used by the self-hosted generation path.

## Rules

- Do not commit model weights, private identity datasets, API keys, signed URLs, or generated private media.
- Do not paste workflow graphs into TypeScript source.
- One directory per model/family, e.g. `h3/`, `ltx-2.5/`.
- Include a small README beside each workflow documenting checkpoints, custom nodes, minimum VRAM, inputs, outputs, and known limitations.
- Export the **API format** from ComfyUI after the workflow works interactively.
- Keep node-ID bindings in config/metadata so the application does not need to understand the graph.

## Expected lifecycle

The Studio's ComfyUI adapter submits:

```json
{
  "prompt": { "...": "exported API workflow" },
  "client_id": "ai-content-factory-studio"
}
```

to `POST /prompt`, stores the returned `prompt_id`, and polls `/history/{prompt_id}` for completion.

## Planned first workflows

1. MiniMax H3 text-to-video.
2. MiniMax H3 reference/image-driven video where the released workflow supports it.
3. LTX-2.5 lower-cost/draft generation.
4. Upscale / interpolation / repair as separate post-processing workflows rather than hiding them inside every generation.

Do not fabricate these graphs from memory. Import and validate the current upstream workflow for the exact model/checkpoint being deployed, then pin the custom-node dependencies.
