# OpenRouter Video Integration Decision

Last verified: 2026-09-17

## Decision

OpenRouter is a **first-class hosted video provider** in UGC Studio, but not an automatically preferred provider.

Its value is different from fal or direct Google: one normalized async API gives us multiple model families plus a live capability/pricing catalog and final actual `usage.cost`.

```text
CreativeSpec
    ↓
rights/assets
    ↓
provider candidates
    ├── fal
    ├── OpenRouter
    ├── Google
    ├── Higgsfield
    └── self-host
    ↓
provider preflight
    ↓
explicit spend gate
    ↓
render
    ↓
QA
    ↓
benchmark ledger
```

## Current OpenRouter video lifecycle

```text
POST /api/v1/videos
    ↓
{id, polling_url, status}
    ↓
GET /api/v1/videos/{id}
    ↓
pending -> in_progress -> completed | failed | cancelled | expired
    ↓
GET /api/v1/videos/{id}/content?index=0
```

The same lifecycle currently supports video models such as Seedance, Veo, Wan and others.

## Capability discovery

Do not hard-code the OpenRouter video catalog.

Query:

```text
GET /api/v1/videos/models
```

The current model descriptor exposes model-specific capabilities such as:
- accepted durations
- resolutions
- aspect ratios
- frame-image/reference support
- audio support
- pricing SKUs
- provider-specific passthrough parameters

The adapter snapshots the selected model descriptor before a live job and validates documented parameters where possible.

## Cost behavior

This provider differs from Higgsfield.

### Higgsfield
Has an authenticated request-specific estimate endpoint returning `credits` + `usd` before generation.

### OpenRouter video
Current documentation recommends:
1. inspect `pricing_skus` from `/videos/models` before running a batch;
2. estimate from the selected configuration;
3. record the completed job's `usage.cost` as actual spend.

No Higgsfield-style authoritative per-request video estimate endpoint is currently documented.

Therefore OpenRouter live jobs require an explicit budget envelope:

```text
expected_cost_usd
max_provider_cost_usd
approved_for_spend = true
```

This is a pre-submission control, not a guarantee that OpenRouter itself will cap billing at that number. After completion, `usage.cost` becomes the authoritative observed spend for our ledger. Any overage is recorded explicitly.

## Actual cost reconciliation

OpenRouter gives us one useful advantage immediately: completed jobs can contain:

```json
{
  "usage": {
    "cost": 0.5,
    "is_byok": false
  }
}
```

That means the benchmark ledger can use provider-reported actual cost rather than only the preflight estimate.

## Webhooks

Requests can include `callback_url`. Terminal webhooks include an `X-OpenRouter-Idempotency-Key` and can be signed with `X-OpenRouter-Signature` when a signing secret is configured.

Production handling should:
1. verify the signature against the raw body when enabled;
2. store/dedupe the idempotency key;
3. persist state quickly;
4. move download/QA/storage work into the job worker.

## Normalized inputs

The video API normalizes common controls such as:
- model
- prompt
- duration
- resolution
- aspect ratio
- generate_audio
- frame_images
- input_references
- seed
- callback_url

Provider-specific controls remain available through `provider.options` and should be discovered from the current model descriptor instead of guessed.

## Data retention / download

The generated video is retrieved asynchronously and should be copied promptly to storage we control. OpenRouter's video flow is not compatible with Zero Data Retention because the generated output must be retained briefly for retrieval.

## Routing policy

Do not select OpenRouter merely because it aggregates many models.

Benchmark the same approved creative against equivalent provider/model routes and compare:
- provider-reported actual cost
- pass rate
- identity consistency
- anatomy/artifact QA
- motion/reference adherence
- audio/lip-sync when relevant
- usable approved seconds

Primary metric remains **cost per usable approved second**.

## Sources

- https://openrouter.ai/blog/announcements/video-generation/
- https://openrouter.ai/blog/tutorials/video-generation-api/
- https://openrouter.ai/blog/insights/seedance-2-5-review/
- https://openrouter.ai/api/v1/videos/models
