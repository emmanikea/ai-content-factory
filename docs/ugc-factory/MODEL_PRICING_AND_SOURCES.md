# UGC Studio Model Pricing and Source Ledger

Last verified: 2026-09-12
Currency: USD unless explicitly stated otherwise

## Purpose

Video-model pricing changes quickly. This file is a dated research ledger, not a permanent billing contract.

The application should use structured provider pricing metadata where possible and record the price/estimate used for each job in provenance.

Before a meaningful production benchmark, re-verify the routes being tested.

## Core metric

Do not optimize for cheapest raw generation.

Optimize for:

`cost per usable approved second`

Track at minimum:

- quoted/estimated generation cost
- actual provider charge when accessible
- generated seconds
- retries
- QA pass/fail
- human approval
- usable seconds
- identity quality
- motion adherence
- lip sync/audio quality when relevant

A $0.10/s model that takes three attempts can be more expensive than a $0.17/s model that passes once.

## Direct hosted models

### Wan 3.0 Image-to-Video via fal

Source:
`https://fal.ai/models/alibaba/wan-3.0/image-to-video`

Pricing checked 2026-09-12:

| Resolution | Reference rate |
|---|---:|
| 480p | $0.05 / output second |
| 720p | $0.10 / output second |
| 1080p | $0.20 / output second |

Current use in UGC Studio:

- draft/cost-first creator animation
- B-roll
- inexpensive I2V concepts
- benchmark against Kling for normal UGC creator shots

Example:

5 seconds at 720p ≈ `$0.50` before retries.

### Kling 3 Standard Image-to-Video via fal

Source:
`https://fal.ai/models/fal-ai/kling-video/v3/standard/image-to-video`

Pricing checked 2026-09-12:

| Mode | Reference rate |
|---|---:|
| audio off | $0.084 / second |
| audio on | $0.126 / second |
| voice control | $0.154 / second |

Current use:

- standard creator/reaction shot
- strong default benchmark for realistic UGC
- start-frame identity anchor

Example:

5 seconds, audio off ≈ `$0.42` before retries.

### Kling 3 Pro Image-to-Video via fal

Source:
`https://fal.ai/models/fal-ai/kling-video/v3/pro/image-to-video`

Pricing checked 2026-09-12:

| Mode | Reference rate |
|---|---:|
| audio off | $0.112 / second |
| audio on | $0.168 / second |
| voice control | $0.196 / second |

Use:

- escalation when Standard misses identity/motion/quality gates
- premium UGC shot when measured pass rate justifies it

### Kling Motion Control via fal

Sources:

- `https://fal.ai/models/fal-ai/kling-video/v3/standard/motion-control`
- `https://fal.ai/models/fal-ai/kling-video/v3/pro/motion-control`

Pricing checked 2026-09-12:

| Route | Reference rate |
|---|---:|
| Kling 3 Standard Motion | $0.126 / second |
| Kling 3 Pro Motion | $0.168 / second |
| Kling 2.6 Standard Motion | about $0.07 / second |

Use:

- owned/licensed performance transfer only
- creator reaction/performance reuse where rights permit

Literal transfer is blocked for `creative_dna_only` references.

### Seedance 2.5 Reference-to-Video via fal

Source:
`https://fal.ai/models/bytedance/seedance-2.5/reference-to-video`

Pricing checked 2026-09-12:

Pricing is token-based rather than a simple flat per-second number.

Current registry formula for 480p/720p reference-to-video:

- `$0.0214 / 1000 tokens`
- nominal 24 FPS
- reference-video billing includes input reference duration
- video-reference multiplier observed/documented at `0.6`

Useful published/reference examples checked during research:

- approximately `$0.473/s` for a typical 720p 16:9 generated output with audio
- approximately `$0.2205/s` at 480p for comparable output
- 10-second 720p output using image/audio references only: roughly `$4.62`
- 10-second output + 8-second input video reference: roughly `$4.99`
- 30-second output + 10-second input video reference: roughly `$11.09`

1080p pricing can be materially higher and endpoint-specific. Re-check before production use rather than extrapolating from this ledger.

Use:

- premium/reference-heavy shots
- multimodal image/video/audio references
- complex motion or scene direction
- escalation when cheaper routes fail quality gates

## Self-host lane

### Wan2.2 Animate

Source:
`https://github.com/Wan-Video/Wan2.2`

Open-source/self-host lane for:

- motion transfer
- character replacement

Current internal model:
`Wan2.2-Animate-14B`

Pricing status:

**Not benchmarked yet.**

Do not claim self-hosting is cheaper until we measure:

- GPU type
- hourly GPU price or amortized owned-hardware cost
- initialization/model-load overhead
- seconds generated/hour
- failure/retry rate
- storage/egress
- operator overhead

Calculate:

`effective self-host $ / usable approved second`

then compare against direct hosted inference.

## Higgsfield economics

Sources:

- `https://higgsfield.ai/pricing`
- Higgsfield Help Center / credit policy
- Higgsfield model/CLI cost inspection
- Higgsfield public Seedance pricing article

### Important distinction

Higgsfield uses **credits**, and the effective dollar cost depends on the current plan / purchased credits.

Do not hardcode a permanent `$ per Higgsfield credit` in our system.

Instead, when benchmarking Higgsfield:

1. ask the Higgsfield CLI/platform for current job credit cost
2. record the plan/effective dollar-per-credit at that moment
3. convert to an estimated dollar cost
4. keep the raw credit cost in provenance as well

### Automation/CLI note

As reviewed 2026-09-12:

- Higgsfield CLI/MCP/automation jobs deduct credits
- website-only "Unlimited" style benefits should not be assumed to cover automated generation
- subscription credits can reset rather than roll over depending on the plan
- exact job cost is shown/inspectable before generation

This is another reason the UGC Factory should not depend on Higgsfield economics for its core route.

### Seedance 2.5 Higgsfield reference point

A Higgsfield public pricing article reviewed 2026-09-12 gave an example of approximately:

- 8s 720p: `52 credits`
- 8s 480p: `24 credits`

Do not directly compare these credit values to fal dollars without converting through the user's then-current Higgsfield plan.

## Higgsfield skills upstream

The public skills repo also contains model-choice and cost-inspection guidance:

`https://github.com/higgsfield-ai/skills`

Snapshot reviewed:

- version `0.12.0`
- commit `d071406147a37b835bed09543d85ab3e9bd85c7d`
- reviewed 2026-09-12

Relevant upstream behavior:

- Seedance 2.5 recommended by Higgsfield as the serious-video default
- Kling 3.0 positioned as a lower-cost/simple scene alternative
- their agents can inspect generation/workflow cost before submission

These recommendations are useful priors, not our routing truth.

## Internal structured pricing source

Machine-readable current registry:

`ugc-studio/providers/model-registry.json`

It contains:

- model ID
- capabilities
- recommended quality tier
- configured quality prior
- cost model/formula
- pricing verification date
- source URL

The router should use that structured file, not scrape this Markdown document.

## Pricing refresh procedure

Before a benchmark, a launch, or if more than ~2–4 weeks have passed during active model churn:

1. Check each direct provider endpoint used by the campaign.
2. Record new rate/formula and verification date.
3. Update `model-registry.json`.
4. Update this ledger if the economics materially changed.
5. Check Higgsfield credits only if it is part of the benchmark.
6. Never rewrite historical job provenance with current pricing.

## Benchmark table template

Use the same creator image, shot direction, duration and target output whenever possible.

| Date | Model | Route | Duration | Est. cost | Actual cost | Attempts | Human pass | Usable sec | Cost / usable sec | Notes |
|---|---|---:|---:|---:|---:|---:|---|---:|---:|---|
| YYYY-MM-DD | Wan 3.0 | fal | 5s | | | | | | | |
| YYYY-MM-DD | Kling 3 Std | fal | 5s | | | | | | | |
| YYYY-MM-DD | Kling 3 Pro | fal | 5s | | | | | | | |
| YYYY-MM-DD | Seedance 2.5 | fal | 5s | | | | | | | |
| YYYY-MM-DD | Higgsfield comparable | Higgsfield | 5s | credits + $ | | | | | | |

## Current architectural decision

Pricing is one input, not the only input.

Default philosophy remains:

```text
exact UI / editing       -> deterministic local
cheap exploration        -> Wan direct
standard creator UGC     -> Kling direct
licensed motion          -> Kling Motion direct
premium/reference-heavy  -> Seedance / premium route
self-host                -> benchmark at higher volume
Higgsfield               -> optional proprietary/benchmark/fallback
```
