# Direct-Model UGC Factory Execution Plan

## Goal

Build a high-volume UGC/Reels factory that can approach the quality of premium creative suites without making Higgsfield the default render backend.

The system owns the workflow. Underlying models are replaceable workers.

## Core rule

Use the cheapest deterministic or direct-model path that can meet the shot's quality requirement.

Higgsfield is optional. It is reserved for:
- proprietary Higgsfield-only capabilities that materially outperform our direct stack
- benchmark comparisons
- emergency fallback when direct routes fail quality gates

It is not the default renderer.

## Production lanes

### Lane 0: deterministic, effectively zero model cost

Use for anything that should be exact rather than hallucinated.

- web/mobile app capture
- product screenshots
- owned footage
- captions
- motion graphics
- CTA cards
- transitions
- audio mix
- final timeline assembly

Preferred stack:
- Playwright for web capture
- Maestro/Appium for mobile capture
- Remotion for composition
- FFmpeg for normalization/transcoding

### Lane 1: self-host/local

Use when volume makes hosted inference uneconomic or when we want tighter control.

Target components:
- Wan2.2 Animate for motion transfer/character replacement
- InfiniteYou / PuLID-class identity-preserving still generation
- LivePortrait-class facial motion
- MuseTalk-class lip sync

This lane is not required to ship V1. It becomes increasingly valuable as render volume grows.

### Lane 2: direct hosted models, default production lane

#### Wan direct
Default cost-first video worker.

Use for:
- inexpensive image-to-video
- B-roll
- generic creator shots that pass identity QA
- fast concept testing

Current reference pricing checked 2026-09-12 on fal:
- Wan 3.0: $0.05/s 480p, $0.10/s 720p, $0.20/s 1080p

#### Kling direct
Default quality/consistency worker for creator shots.

Use for:
- image-to-video with strong subject consistency
- creator reaction shots
- first/last-frame controlled motion
- motion transfer from licensed/owned footage

Current reference pricing checked 2026-09-12 on fal:
- Kling 3 Standard I2V/T2V: $0.084/s audio off, $0.126/s audio on
- Kling 3 Standard Motion Control: $0.126/s
- Kling 3 Pro I2V: $0.112/s audio off, $0.168/s audio on

#### Seedance direct
Premium route for difficult multimodal/reference-heavy shots.

Use for:
- complex shot direction
- multiple multimodal references
- scenes where native audio/reference integration matters
- premium rerender after lower-cost routes fail QA

Current reference pricing checked 2026-09-12 on fal:
- Seedance 2.5 720p with audio: approximately $0.473/s for standard 16:9 output
- reference-video pricing is token based and may differ because reference duration is billed

Seedance is not the first choice for every creator shot because quality per usable dollar matters more than raw model capability.

### Lane 3: Higgsfield optional

Use only when the feature is actually Higgsfield-specific or benchmark results justify the premium.

Examples:
- Soul ID / Soul workflows
- proprietary Higgsfield camera/creative tooling
- a shot type where Higgsfield produces materially higher usable-pass rates than direct models

The router must never choose Higgsfield simply because Higgsfield is already integrated.

## Routing policy

For each ShotSpec:

1. Can this be deterministic?
   - yes -> local capture/assembly
2. Does the shot require literal motion/performance transfer?
   - yes -> verify rights -> self-host Wan Animate or direct Kling Motion
3. Is this a normal creator/B-roll shot?
   - draft -> Wan direct
   - standard -> compare Wan and Kling by estimated usable cost
   - premium -> Kling Pro or Seedance based on requirements
4. Did QA fail?
   - retry same route once if the failure is stochastic
   - otherwise escalate one quality tier
5. Did all direct routes fail?
   - Higgsfield may be used if enabled for the campaign

## Cost philosophy

Do not optimize cost per raw generation. Optimize cost per usable approved second.

Track:
- provider quoted cost
- retries
- QA pass/fail
- identity score
- lip-sync score
- product/UI accuracy
- human approval

A model that costs twice as much but passes four times as often is cheaper in production.

## Example 18-second Reel

```text
0.0-2.5   creator hook       -> Kling/Wan direct
2.5-8.0   app demo           -> Playwright capture
8.0-10.5  creator reaction   -> Kling/Wan direct
10.5-15.5 app demo           -> Playwright capture
15.5-18.0 CTA/caption        -> Remotion
```

Only 5 seconds require generative human video.

At $0.084/s, five seconds of Kling Standard without native audio is roughly $0.42 before retries. At $0.10/s, five seconds of Wan 3.0 720p is roughly $0.50 before retries.

The entire finished Reel should not be sent to an expensive video generator when deterministic editing is better.

## Execution order

### Slice A: direct routing foundation
- model registry with capabilities and price formulas
- current-price metadata with verification date
- router that selects direct models before Higgsfield
- campaign flag `allow_higgsfield_fallback`, default false
- cost estimate per shot and per Reel

### Slice B: live direct adapter
- fal adapter using official `@fal-ai/client`
- explicit `--live` flag required before spending
- FAL_KEY only on server/runtime
- provenance written for every job
- downloadable result artifact

### Slice C: reference and identity layer
- ReferenceAnalysis schema
- creative-DNA extraction mode
- licensed-performance-transfer mode
- reusable Creator identity pack
- identity QA

### Slice D: product/app capture
- Playwright capture job format
- vertical viewport presets
- scripted click/scroll/tap sequences
- exported MP4/WebM segments

### Slice E: final assembly
- Remotion 9:16 timeline
- caption tracks
- creator/app/B-roll placement
- CTA overlays
- audio mix
- FFmpeg output normalization

### Slice F: open-source/self-host lane
- Wan2.2 Animate worker contract
- GPU deployment benchmark
- local/open identity generation
- local lip sync
- cost comparison against hosted direct inference

## V1 completion definition

A campaign is V1-complete when the system can:

1. ingest product + creator + reference
2. generate ranked CreativeSpecs
3. estimate render cost without spending
4. block unlicensed identity/performance use
5. route creator shots to Wan/Kling/Seedance directly
6. capture real app footage
7. assemble the final Reel deterministically
8. QA the final output
9. record exact model/provider/cost/provenance
10. use Higgsfield only when explicitly enabled
