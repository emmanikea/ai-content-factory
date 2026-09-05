# Open Generation Stack

## Goal

Remove Higgsfield as a hard dependency while preserving the factory's existing explore -> approve -> render workflow.

The system should support two compute paths behind one contract:

1. **Hosted/premium** via OpenRouter's asynchronous video API.
2. **Self-hosted/bulk** via ComfyUI running on a local or rented GPU worker.

The frontend and Archon workflows must never call a model vendor directly. They submit a `GenerationRequest` to the generation router.

## Architecture

```text
Studio UI / Archon
        |
        v
Generation Router
   |          |
   v          v
OpenRouter   ComfyUI
(hosted)     (self-hosted GPU)
   |          |
   +----+-----+
        v
 Job + Cost Ledger
        |
        v
Asset Storage / Review Gate / QA
```

## Routing policy

- `draft`: cheapest configured provider/model that satisfies the request.
- `standard`: prefer self-hosted ComfyUI when healthy; OpenRouter fallback.
- `quality`: prefer configured premium OpenRouter model.
- `max`: fan-out is planned, but V1 intentionally submits one provider job to avoid accidental spend.

Routing must remain explicit and auditable. Every job stores requested tier, selected provider, selected model, duration, resolution, aspect ratio, status, timestamps, provider job ID, and cost when available.

## V1 scope

- Next.js internal studio under `apps/studio`.
- Generate form with prompt, model, tier, aspect ratio, duration, resolution, and audio toggle.
- OpenRouter adapter using `POST /api/v1/videos` and `GET /api/v1/videos/{id}`.
- ComfyUI adapter using `POST /prompt` and `GET /history/{prompt_id}`.
- Provider-agnostic router.
- Environment-based model aliases instead of model names embedded throughout the UI.
- Agent instructions in `AGENTS.md` plus a reusable content-studio skill.
- Existing Archon/Higgsfield code remains untouched during this migration so output can be compared safely.

## V2

- Persist jobs, assets, characters and references in Postgres.
- Cloudflare R2/S3 asset storage.
- Character library and consent/provenance metadata.
- Reference-video ingestion.
- Imported ComfyUI H3 / LTX workflows.
- RunPod or equivalent autoscaling worker lifecycle.
- Automatic provider health checks and overflow routing.
- Cost-per-usable-clip analytics, including retries.
- Automated visual QA and model comparison.

## Data model

Core entities:

- `characters`: persistent synthetic or consented real-person identities.
- `references`: image/video/audio assets and usage permissions.
- `generation_jobs`: one provider attempt.
- `generation_assets`: outputs attached to a job.
- `quality_reviews`: automatic or human QA scores.
- `content_items`: the higher-level social/ad unit assembled from one or more outputs.

For a real person's likeness or voice, store consent/provenance metadata with the character/reference rather than relying on operator memory.

## Provider contract

A provider must implement:

```ts
interface VideoProvider {
  submit(request: GenerationRequest): Promise<GenerationJob>;
  get(jobId: string): Promise<GenerationJob>;
}
```

Provider-specific request fields belong in `providerOptions`. Do not leak them into unrelated UI or workflow code.

## OpenRouter

OpenRouter is the fastest V1 path because the current video API normalizes multiple hosted models behind one asynchronous lifecycle:

- submit: `POST /api/v1/videos`
- poll: `GET /api/v1/videos/{id}`
- capabilities: `GET /api/v1/videos/models`

Model capabilities must be discovered/validated before production submission. Do not assume duration, resolution or reference support is portable between models.

## ComfyUI

ComfyUI is the self-hosted execution engine, not the user-facing product. The studio submits a workflow JSON plus injected inputs to a ComfyUI server. The actual H3/LTX graphs live under `workflows/comfy/` and can be replaced independently of the app.

V1 intentionally accepts a workflow JSON configured on the server. We should not invent model graphs in application code.

## Cost strategy

1. Start OpenRouter-first to validate workflows without GPU operations work.
2. Record every provider attempt and cost.
3. Add ComfyUI worker(s) once actual monthly usage makes self-hosting worthwhile.
4. Compare **cost per accepted clip**, not raw generation price.
5. Keep expensive generations behind the existing human approval gate where appropriate.

## Agent tooling

- `AGENTS.md`: shared contract for Codex and other repo agents.
- `.claude/skills/content-studio/SKILL.md`: Claude Code workflow guidance.
- Existing Archon skill/workflows stay available for multi-agent implementation and review.
- MCP is optional for V1. REST APIs are sufficient. Add MCP wrappers later for high-value operations such as `generate_video`, `get_generation`, `list_costs`, and worker controls.

## Safety / provenance

The platform is designed for synthetic characters and consented digital twins. It must not silently remove provenance or consent records. Avoid workflows whose purpose is to misrepresent a non-consenting real person. Reference media should be owned, licensed, permitted, or used only as high-level creative/motion reference when appropriate.
