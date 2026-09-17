# Direct Google / Veo Provider

This adapter calls Veo 3.1 directly through the Gemini Developer API instead of routing Google video through an aggregator.

Verified against official Google AI documentation on 2026-09-17.

## Credential

```bash
GEMINI_API_KEY=...
```

`GOOGLE_API_KEY` is accepted as a compatibility alias.

Keep the key server-side. Do not expose it in browser code.

## Supported V1 lanes

The adapter currently supports the common direct Veo 3.1 request shapes for:

- text-to-video
- image-to-video using `image`
- first/last-frame interpolation using `image` + `lastFrame`
- asset reference images on Veo 3.1 Standard/Fast using `referenceImages`

V1 intentionally does not enable video extension. Google only accepts Veo-generated source videos for that path and it deserves a separate provenance contract.

## Current pricing encoded for preflight

Official Gemini Developer API pricing checked 2026-09-17:

| Model | 720p | 1080p | 4k |
| --- | ---: | ---: | ---: |
| `veo-3.1-lite-generate-preview` | $0.05/s | $0.08/s | n/a |
| `veo-3.1-fast-generate-preview` | $0.10/s | $0.12/s | $0.30/s |
| `veo-3.1-generate-preview` | $0.40/s | $0.40/s | $0.60/s |

Veo 3.1 audio is always on. Google states Veo is charged only when generation succeeds.

The pricing source is stored in job provenance and should be periodically refreshed rather than treated as permanent.

## Current capability constraints enforced

- aspect ratio: `16:9` or `9:16`
- duration: 4, 6, or 8 seconds
- 1080p requires 8 seconds
- 4k requires 8 seconds
- Lite does not support 4k
- Standard/Fast support up to 3 asset reference images
- Lite does not support `referenceImages`
- reference-image jobs require 8 seconds
- one output video per request
- `lastFrame` requires an initial `image`

## Job shape

The provider keeps Google's REST request body intact so we do not lose provider-specific functionality:

```json
{
  "version": "1.0",
  "provider": "google-veo",
  "model": "veo-3.1-lite-generate-preview",
  "request": {
    "instances": [
      {
        "prompt": "Natural handheld creator movement."
      }
    ],
    "parameters": {
      "aspectRatio": "9:16",
      "durationSeconds": "4",
      "resolution": "720p",
      "numberOfVideos": 1
    }
  },
  "rights_approved": true,
  "approved_for_spend": false,
  "max_provider_cost_usd": 0.30
}
```

Image/reference jobs use Google's documented `inlineData` image objects. Asset preparation should happen before the provider call; the provider does not fetch arbitrary external URLs into base64.

## Commands

Dry-run with local price/capability validation, no key needed:

```bash
python ugc-studio/providers/google-veo/client.py --job job.json
```

Estimate only:

```bash
python ugc-studio/providers/google-veo/client.py --job job.json --estimate
```

Live:

```bash
python ugc-studio/providers/google-veo/client.py \
  --job job.json \
  --live \
  --outdir ./google-veo-output
```

Live mode requires:
- `rights_approved=true`
- `approved_for_spend=true`
- `max_provider_cost_usd`
- API key
- `--live`

The local official-rate estimate must fit under the approved cap before submission.

## Async lifecycle

Direct REST submission:

```text
POST /v1beta/models/{model}:predictLongRunning
       ↓
operation.name
       ↓
GET /v1beta/{operation.name}
       ↓
done=true
       ↓
response.generateVideoResponse.generatedSamples[].video.uri
```

The adapter polls every 10 seconds by default, matching Google's examples, and then immediately downloads completed media when an output directory is supplied.

## Retention

Google documents Veo generated-video retention of 2 days. Copy outputs to storage we control immediately after completion.

## Cost reconciliation

Unlike OpenRouter, the current direct Veo response does not expose a per-job `usage.cost` field in the documented video flow. The adapter therefore records a **derived billable cost** from:

```text
official $/second × requested duration
```

for successful jobs, and zero for a failed generation because Google documents successful-generation-only billing.

Keep this cost basis distinct from OpenRouter's provider-reported actual `usage.cost` and Higgsfield's authenticated request quote.

## Sources

- https://ai.google.dev/gemini-api/docs/veo
- https://ai.google.dev/gemini-api/docs/pricing
