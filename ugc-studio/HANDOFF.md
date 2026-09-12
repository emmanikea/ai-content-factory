# UGC Studio Handoff

Last updated: 2026-09-12
Branch: `feat/ugc-studio-v1`
PR: #5

## Product direction

Build a UGC/Reels production system that owns the creative workflow and calls underlying models directly. Higgsfield is optional and disabled by default as a rendering dependency.

Higgsfield's public skills repo is now treated separately as a useful **knowledge/benchmark upstream**.

```text
exact UI / owned media -> deterministic local capture/composition
cheap draft video      -> Wan direct
standard creator shot  -> Kling Standard direct
licensed motion        -> Kling Motion direct
premium/reference      -> Seedance / Kling premium
high-volume future     -> self-host Wan2.2 Animate
Higgsfield runtime     -> proprietary-only / benchmark / explicit fallback
Higgsfield skills      -> prompt/model/workflow research source
```

## Higgsfield skills research snapshot

Upstream: `https://github.com/higgsfield-ai/skills`

Reviewed:
- version `0.12.0`
- commit `d071406147a37b835bed09543d85ab3e9bd85c7d`
- commit date 2026-09-11
- MIT license

Optional terminal-agent install:

```bash
npx skills add higgsfield-ai/skills
```

or:

```bash
gh skill install higgsfield-ai/skills
```

Use the installed skills to research current Higgsfield behavior or run optional benchmarks. Do not let installation change our default direct-model router.

Durable derived notes are stored in:
- `docs/ugc-factory/HIGGSFIELD_SKILLS_RESEARCH.md`
- `docs/ugc-factory/MODEL_PRICING_AND_SOURCES.md`
- `ugc-studio/providers/research-sources.json`

## Important Higgsfield-derived lessons already adopted

- Keep generation prompts concise and concrete.
- For image-to-video, prompt motion/performance/camera rather than redescribing the reference frame.
- Treat provider/model media schemas as contracts instead of guessing parameters.
- Represent Hook, Setting, Creator/Avatar, Product and Reference as reusable creative primitives.
- Separate reference-driven creative from block-composed Hook + Setting creative.
- Maintain reusable processed reference analysis rather than repeatedly re-understanding a source video.
- Creator identity onboarding should contain diverse clean references across angle, lighting, expression and distance.
- Batch creative variants at the concept/spec layer, then render only a ranked frontier.
- Keep post-render attention/retention/creative analysis as part of the eventual feedback loop.

The direct fal job builder now uses `.archon/scripts/ugc/prompt_compiler.py`, which compiles different prompt shapes for:
- normal image-to-video creator shots
- licensed motion transfer
- Seedance-style multimodal reference generation

Prompt compiler strategy/version are persisted in job provenance.

## Implemented

### Product/contracts
- UGC PRD + direct-model execution plan
- OpenSpec proposal/design/tasks
- CreativeSpec schema
- Creator/rights schema
- ReferenceAnalysis schema
- CreatorIdentityPack schema

### Rights and live safeguards
- creator rights-policy evaluator
- blocks literal motion transfer from `creative_dna_only` references
- direct job compilation requires `rights_approved: true`
- live provider execution independently requires `rights_approved: true`
- live provider execution also requires `approved_for_spend: true`
- `FAL_KEY` is runtime-only; never store it in the repo

### Direct model router
- dated model registry with pricing/capability metadata
- Wan direct for draft/cost-first generation
- Kling Standard direct for normal creator shots
- Kling Motion direct for licensed/owned motion transfer
- Seedance/Kling premium for premium/reference-heavy work
- Higgsfield excluded from default routing
- per-concept budget cap
- alternatives returned in dry-run plan

### Pricing/research provenance
- dated Markdown pricing ledger
- structured model registry with verification dates and source URLs
- machine-readable research-source registry
- upstream Higgsfield skills version/commit/license captured
- historical job pricing should never be overwritten with current rates

### Prompt compiler
- motion-first I2V guidance
- licensed motion-transfer guidance
- structured multimodal reference guidance
- prompt length cap
- native-audio vs later-lip-sync dialogue handling
- compiler strategy/version saved to job provenance

### fal execution
- `@fal-ai/client` pinned to `1.10.1`
- provider-ready job compiler for Wan I2V, Kling I2V, Kling Motion and Seedance reference-to-video
- renderer is dry-run unless `--live`
- completed live jobs write provenance and download the output asset

### App capture
- Playwright `1.63.0`
- declarative actions: goto/click/tap/fill/press/wait/wait_for/scroll/screenshot
- mobile/vertical capture defaults
- recorded video + capture provenance

### Reel assembly
- Remotion + CLI `4.0.523`
- React/ReactDOM `19.3.0`
- 1080x1920 composition
- creator/app/B-roll clip sequencing
- timed captions
- CTA overlay
- per-clip audio controls
- local asset staging into Remotion public media
- FFmpeg 1080x1920/H.264/AAC normalization + loudness normalization + faststart

### QA retry policy
- one same-tier retry for stochastic failures
- structural quality failures may escalate one quality tier
- budget is checked before another attempt
- rights/source/UI failures stop and are never routed around

### Tests
- creator rights tests
- direct routing/cost tests
- direct job rights guards
- Creative-DNA vs licensed motion-transfer guards
- retry/escalation tests
- model-aware prompt compiler tests
- GitHub Actions workflow

## No paid work has been run

No direct provider generation has been submitted from this branch.

## First live benchmark

Use one synthetic or explicitly consented creator identity image and one 5-second creator hook.

1. Build/confirm creator rights record.
2. Produce assets manifest with `rights_approved: true` and evidence reference.
3. Compile the CreativeSpec shot into a direct fal job.
4. Inspect generated prompt strategy + provider payload + estimated cost.
5. Deliberately set `approved_for_spend: true`.
6. Run with `FAL_KEY` and `--live`.
7. Score the result.
8. Compare Wan 3.0 720p vs Kling 3 Standard using equivalent creative direction.
9. Escalate to Kling Pro/Seedance only if measured quality warrants it.
10. Optionally benchmark a comparable Higgsfield render after checking current Higgsfield credit cost.

Track:
- raw provider cost
- source pricing snapshot/date
- prompt compiler strategy/version
- number of attempts
- identity consistency
- face/hands/body quality
- motion adherence
- lip sync/audio where relevant
- human pass/fail
- cost per usable approved second

## Remaining autonomous slices

1. Creator identity-pack importer/builder.
2. Automated reference video segmentation/transcription into ReferenceAnalysis.
3. Identity/lip-sync/final-timeline QA scorers.
4. Measured provider pass-rate database replacing static quality priors.
5. Self-host Wan2.2 Animate worker + GPU cost benchmark.
6. Maestro mobile capture lane.
7. Performance analytics feedback into creative ranking.
8. Periodic upstream-model/pricing refresh utility.

## External inputs still needed for real production

- `FAL_KEY` or another direct-provider credential
- approved creator reference assets
- licensed/owned motion clips for literal motion transfer
- production app auth/capture instructions where login is required
- GPU target when self-host benchmarking begins
- legal review of final creator NIL/AI-use/commission agreements

## Merge policy

Keep PR #5 draft until fixture capture + assembly are verified end-to-end and the first provider-ready direct job has been inspected. Live spending is not required to merge the architecture, but the rights and spend gates must remain intact.
