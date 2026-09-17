# Direct Google / Veo 3.1 Integration Decision

Last verified: 2026-09-17

## Decision

Keep a direct Google Veo lane even though Veo is also available through OpenRouter.

Reasons:
- user already has a Gemini API key;
- direct Veo 3.1 Lite is currently very inexpensive at 720p;
- direct integration gives us a clean benchmark against aggregator economics;
- Google exposes first/last-frame and asset-reference workflows directly;
- the provider's pricing and capability constraints are explicit enough to validate before spend.

## Current documented pricing

Paid Gemini Developer API, per generated second:

| Model | 720p | 1080p | 4k |
| --- | ---: | ---: | ---: |
| Veo 3.1 Lite | $0.05 | $0.08 | n/a |
| Veo 3.1 Fast | $0.10 | $0.12 | $0.30 |
| Veo 3.1 Standard | $0.40 | $0.40 | $0.60 |

Native audio is always on for Veo 3.1. Google documents that a video is charged only if generation succeeds.

This makes a 4-second 720p Lite clip roughly $0.20 before any taxes/account-specific considerations.

## Current capability rules used by V1

- 9:16 and 16:9
- 4, 6, or 8 seconds
- 1080p requires 8 seconds
- 4k requires 8 seconds
- Lite: 720p/1080p, text-to-video + image-to-video
- Fast/Standard: 720p/1080p/4k plus up to 3 asset reference images
- reference-image generation requires 8 seconds
- first/last-frame interpolation supported
- one video per request
- generated videos retained by Google for 2 days, so copy them immediately

V1 intentionally excludes Veo video extension because Google requires a previously Veo-generated source video and that deserves its own provenance contract.

## Direct REST lifecycle

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
      ↓
download with x-goog-api-key
```

Google's examples poll around every 10 seconds.

## Cost semantics

Do not collapse this into the same evidence type as other providers.

```text
Higgsfield -> authenticated request-specific quote
OpenRouter -> live catalog preview + completed provider usage.cost
Google Veo -> dated official per-second rate × requested seconds
```

For a successful direct Google job, the adapter records a derived billable cost from the official rate snapshot. For an API-reported failed generation, it records zero derived billable cost based on Google's successful-generation-only billing note.

## Identity/reference implications

Veo 3.1 Standard/Fast can accept up to three asset reference images. This can be useful for creator consistency experiments, but the canonical identity remains `CreatorIdentityPack`.

Provider flow:

```text
CreatorIdentityPack
      ↓
approved selected reference assets
      ↓
Google inlineData/referenceImages
      ↓
Veo output
      ↓
identity/anatomy QA
```

We should benchmark this against normal first-frame image-to-video rather than assume multiple reference images improve identity consistency.

## Security / asset preparation

The direct provider job keeps Google's documented REST request structure. Image inputs are expected as Google `inlineData` objects. The provider core does not fetch arbitrary URLs and turn them into base64; that should happen in our controlled asset-preparation layer so provider execution does not become an SSRF surface.

## Benchmark priority

Veo 3.1 Lite 720p should be included in the first low-cost creator-video benchmark because its current $0.05/sec rate is competitive with the cheapest hosted options we have found.

Compare:
- direct Veo Lite
- OpenRouter low-cost Wan/Seedance/Veo route
- fal Wan/Kling
- Higgsfield equivalent route if credentials are added

Track the same QA and usable-second metrics for all of them.

## Sources

- https://ai.google.dev/gemini-api/docs/veo
- https://ai.google.dev/gemini-api/docs/pricing
