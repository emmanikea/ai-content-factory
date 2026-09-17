# OpenRouter Video Provider

OpenRouter is a first-class hosted video provider in UGC Studio. It gives us one async API over multiple video-model families while keeping model capability/pricing discovery live instead of hard-coded.

Verified against OpenRouter documentation on 2026-09-17.

## Credential

```bash
OPENROUTER_API_KEY=...
```

Keep it server-side. Do not expose it to browser/client code.

## Why the adapter queries the live catalog

Current video models differ in accepted durations, resolutions, aspect ratios, reference inputs, audio support, passthrough parameters, and pricing. OpenRouter exposes those differences through:

```text
GET /api/v1/videos/models
```

The adapter uses that endpoint as the model/capability snapshot before live submission.

## Commands

Dry-run, no key and no network call:

```bash
python ugc-studio/providers/openrouter/client.py --job job.json
```

Authenticated preflight, no generation:

```bash
python ugc-studio/providers/openrouter/client.py --job job.json --preflight
```

Inspect the current catalog:

```bash
python ugc-studio/providers/openrouter/client.py --catalog
python ugc-studio/providers/openrouter/client.py --catalog --model bytedance/seedance-2.0
```

Live generation:

```bash
python ugc-studio/providers/openrouter/client.py \
  --job job.json \
  --live \
  --outdir ./openrouter-output
```

## Spend safety

OpenRouter documents current model `pricing_skus` through the catalog and final actual cost through `usage.cost`. It does not document a Higgsfield-style authoritative per-request estimate endpoint for video.

For that reason live jobs require all of:

```text
rights_approved = true
approved_for_spend = true
expected_cost_usd = <current preview estimate>
max_provider_cost_usd = <explicit approved ceiling>
OPENROUTER_API_KEY
--live
```

The preflight rejects `expected_cost_usd > max_provider_cost_usd` and validates documented request settings against the current model descriptor when the descriptor exposes them.

The ceiling is a pre-submission control, not a provider-guaranteed hard billing limit. The completed response's `usage.cost` is stored as actual spend, and any actual overage is recorded explicitly rather than hidden.

## Async lifecycle

OpenRouter video jobs use:

```text
POST /api/v1/videos
      ↓
pending
      ↓
in_progress
      ↓
completed / failed / cancelled / expired
```

The returned `polling_url` points to the same job resource available at `GET /api/v1/videos/{id}`. The adapter uses bounded polling with a configurable timeout and preserves the job ID so a transient polling failure never implies a second paid generation.

## Download and actual cost

Completed jobs may expose authenticated `unsigned_urls`, or video can be downloaded at:

```text
GET /api/v1/videos/{id}/content?index=0
```

The download still requires the OpenRouter bearer token. The adapter writes `provenance.json` with:

- model
- live catalog snapshot
- pricing SKUs
- expected cost
- approved ceiling
- actual `usage.cost`
- BYOK state when returned
- rights/spend approval
- request/terminal payload

## Webhooks

Pass a public HTTPS URL as `callback_url` in the job or normalized request. OpenRouter sends terminal callbacks and provides `X-OpenRouter-Idempotency-Key`; production handlers should persist that key and process each terminal delivery once. If webhook signing is enabled, verify `X-OpenRouter-Signature` against the raw request body.

## Model inputs

OpenRouter normalizes common video fields including:

- `model`
- `prompt`
- `duration`
- `resolution`
- `aspect_ratio`
- `generate_audio`
- `frame_images`
- `input_references`
- `seed`
- `provider.options` for provider-specific controls

Reference-to-video example shapes are documented for models such as Seedance. Do not assume every model accepts every field; preflight against the live catalog.

## Routing policy

OpenRouter is integrated but not automatically preferred. Benchmark equivalent shots against fal, direct Google, Higgsfield and eventually self-hosting. Route on measured quality and cost per usable approved second rather than provider name or headline list price.

## Sources

- https://openrouter.ai/blog/announcements/video-generation/
- https://openrouter.ai/blog/tutorials/video-generation-api/
- https://openrouter.ai/blog/insights/seedance-2-5-review/
- https://openrouter.ai/api/v1/videos/models
