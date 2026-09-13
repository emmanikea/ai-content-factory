# UGC Studio Handoff

Last updated: 2026-09-12
Branch: `feat/ugc-studio-v1`
PR: #5

## Product direction

Build a UGC/Reels production system that owns the creative workflow and calls underlying models directly. Higgsfield is optional and disabled by default as a rendering dependency.

Higgsfield's public skills repo is treated separately as a useful knowledge/benchmark upstream.

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

## Read first

- `docs/ugc-factory/PRD.md`
- `docs/ugc-factory/DIRECT_MODEL_EXECUTION_PLAN.md`
- `docs/ugc-factory/HIGGSFIELD_SKILLS_RESEARCH.md`
- `docs/ugc-factory/MODEL_PRICING_AND_SOURCES.md`
- `docs/ugc-factory/CREATOR_AND_REFERENCE_PIPELINE.md`
- `docs/ugc-factory/END_TO_END_RUNBOOK.md`
- `openspec/changes/ugc-studio-v1/tasks.md`

## Higgsfield knowledge snapshot

Upstream: `https://github.com/higgsfield-ai/skills`

Reviewed:
- version `0.12.0`
- commit `d071406147a37b835bed09543d85ab3e9bd85c7d`
- commit date 2026-09-11
- MIT license

Optional agent install:

```bash
npx skills add higgsfield-ai/skills
# or
gh skill install higgsfield-ai/skills
```

Installing the skills must not change the direct-model routing policy.

## Current implemented pipeline

```text
Reference video
  -> ReferenceObservation
  -> semantic enrichment
  -> ReferenceAnalysis

Creator assets + agreement
  -> CreatorIdentityPack
  -> request-specific rights decision
  -> render asset manifest

CampaignBrief
  + ReferenceAnalysis
  -> CreativeSpec batch
  -> dry model/cost plan
  -> selected shot job
  -> explicit spend gate
  -> direct model render
  -> deterministic + semantic QA
  -> deterministic Reel assembly
  -> final QA
  -> benchmark ledger
  -> measured routing history
```

The complete command sequence is in `docs/ugc-factory/END_TO_END_RUNBOOK.md`.

## Reference intelligence

### Factual observation

`.archon/scripts/ugc/observe_reference.py`

Records:
- ffprobe duration, dimensions, FPS, audio
- source SHA-256
- ffmpeg scene-change candidates
- segment boundaries
- optional keyframes
- optional transcript JSON
- optional local Whisper CLI transcript

It does not invent semantic roles from scene cuts.

### Semantic enrichment

`.archon/scripts/ugc/build_reference_analysis.py`
- validates semantic labels against observed segments
- requires every segment labeled exactly once
- calculates pacing from observed timing
- preserves `creative_dna_only` vs licensed/owned rights boundary

`.archon/scripts/ugc/enrich_reference_semantics.py`
- optional Gemini/keyframe adapter
- fails closed without a vision credential
- validates output through the same ReferenceAnalysis compiler
- dry-run mode available

Schemas:
- `ugc-studio/schemas/reference-observation.schema.json`
- `ugc-studio/schemas/reference-semantic-labels.schema.json`
- `ugc-studio/schemas/reference-analysis.schema.json`

## Creator identity and rights

`.archon/scripts/ugc/build_identity_pack.py`
- provider-neutral identity pack
- active consent + agreement reference required for real/founder creators
- local source hashing/provenance
- remote sources are not silently fetched
- motion-transfer samples require explicit creator transformation permission
- warns on weak identity-view coverage without claiming semantic quality

`.archon/scripts/ugc/prepare_creator_assets.py`
- derives render approval from the pack for exact product/category/platform/date/transformations
- product/category scope only becomes unrestricted when both lists are empty
- selected motion sample must itself be approved
- preserves agreement evidence and decision inputs for render provenance

Schema:
`ugc-studio/schemas/creator-identity-pack.schema.json`

Example:
`ugc-studio/examples/creator-import.example.json`

## CreativeSpec batch generation

`.archon/scripts/ugc/generate_creative_specs.py`

Input:
- CampaignBrief
- ReferenceAnalysis

It expands:

```text
creator × hook × CTA × location × outfit
```

up to `max_specs`.

It reuses abstract reference timing/roles, not third-party identity or protected content. App-demo beats become `app_capture`; creator beats become direct creator generation. Literal motion is blocked for `creative_dna_only` references and only enabled for licensed/owned references.

Schemas/examples:
- `ugc-studio/schemas/campaign-brief.schema.json`
- `ugc-studio/schemas/creative-spec.schema.json`
- `ugc-studio/examples/bordereta-campaign.example.json`
- `ugc-studio/examples/reference-analysis.example.json`

## Local persistence

`.archon/scripts/ugc/local_store.py`

Collections:
- campaigns
- creators
- references
- specs
- jobs
- artifacts
- qa
- performance

Writes are atomic and support expected-version conflict checks. This is the V1 migration seam to a future Postgres + R2 implementation.

`ugc-studio/data/` is runtime data and is gitignored.

## Model routing and prompt intelligence

`.archon/scripts/ugc/model_router.py`

Default routes:
- draft -> Wan direct
- standard creator -> Kling Standard direct
- motion transfer -> Kling Motion
- premium/reference-heavy -> premium Kling / Seedance
- deterministic UI/graphics -> local tools
- Higgsfield excluded unless explicitly enabled

`.archon/scripts/ugc/prompt_compiler.py`
- image-to-video prompts focus on motion/performance/camera
- motion-transfer prompts treat the licensed reference as timing/performance source
- Seedance jobs use compact multimodal direction
- compiler strategy/version saved in job provenance

Dated pricing/capabilities:
`ugc-studio/providers/model-registry.json`

## Direct fal path

`.archon/scripts/ugc/build_fal_job.py`
`ugc-studio/providers/fal/`

Supported provider-ready jobs:
- Wan I2V
- Kling I2V
- Kling Motion
- Seedance reference-to-video

A live job requires all of:

```text
rights_approved = true
approved_for_spend = true
FAL_KEY at runtime
--live
```

No paid generation has been triggered from this branch.

## Deterministic app capture and assembly

App capture:
`ugc-studio/capture/`
- Playwright 1.63.0
- vertical capture presets
- declarative click/tap/fill/press/wait/scroll/screenshot actions
- provenance

Assembly:
`ugc-studio/assembly/`
- Remotion/CLI 4.0.523
- React/ReactDOM 19.3.0
- 1080x1920 timeline
- creator/app/B-roll sequencing
- captions + CTA
- local asset staging
- FFmpeg H.264/AAC normalization
- loudness normalization
- faststart

## QA

Schema:
`ugc-studio/schemas/qa-result.schema.json`

`.archon/scripts/ugc/qa_video.py`
- deterministic duration/resolution/aspect/audio/black-frame checks
- technically valid output remains `needs_review`, not automatically pass
- structural failures stop

`.archon/scripts/ugc/enrich_video_qa.py`
- optional sampled-frame vision QA
- can compare against local canonical creator references
- evaluates visible identity drift, anatomy, text/caption problems and visual artifacts
- cannot override deterministic hard failures
- deliberately leaves lip sync unresolved because sampled stills do not prove it

## Benchmark learning loop

`.archon/scripts/ugc/benchmark_metrics.py`

Records:
- provider/model
- prompt strategy/version
- attempt number
- estimate vs actual cost
- QA status/score
- usable seconds
- failure codes

Failed generations count as spend and zero usable seconds.

`model_router.py` can consume the benchmark summary. Measured routing only activates after at least 5 attempts for a model; before that static quality priors remain.

Primary metric:

`cost per usable approved second`

## Retry policy

`.archon/scripts/ugc/retry_policy.py`
- one same-tier retry for stochastic defects
- structural quality issues may escalate one tier
- checks budget before retry
- rights/source/deterministic UI failures cannot be routed around

## Tests

`.github/workflows/ugc-studio-tests.yml`

Coverage includes:
- creator/reference rights
- product/category scope
- direct routing and pricing formulas
- measured routing threshold
- prompt compiler
- live/spend guards
- creator identity pack
- creator rights-to-assets resolution
- reference observation/analysis
- automatic semantic-label adapter guards
- local atomic store
- deterministic + semantic visual QA merge behavior
- benchmark usable-cost accounting
- CreativeSpec variation generation
- end-to-end no-spend campaign/reference -> plan -> rights -> provider job integration

## First live benchmark

Still intentionally external-gated.

Use one real approved or synthetic creator and one 5-second hook:

1. create/inspect CreatorIdentityPack
2. derive rights-approved render assets
3. generate/select CreativeSpec
4. inspect route and cost
5. compile direct provider job
6. dry-run it
7. deliberately approve spend
8. render Wan/Kling equivalent versions
9. deterministic QA + visual QA
10. record every attempt/cost/result in benchmark ledger
11. compare cost per usable second
12. only escalate to premium/Seedance/Higgsfield when the evidence supports it

## Remaining autonomous work

Highest-value remaining code slices:
1. JSON Schema validation at ingestion/write boundaries
2. concept ranking using cost + novelty + reference fit + available performance history
3. creator-rights revocation propagation through stored jobs/artifacts
4. audio-aware lip-sync QA
5. ground-truth app/UI correctness QA
6. background-music ducking
7. Maestro mobile capture lane
8. self-host Wan2.2 Animate worker/benchmark contract
9. social/ad performance event ingestion and learning loop
10. automated provider actual-cost reconciliation where supported

## External production inputs

Still needed for real production:
- direct provider credential such as `FAL_KEY`
- actual approved creator images/voice/performance samples
- actual agreement/rights record references
- licensed/owned motion clips for literal performance transfer
- real reference Reel(s)
- production app auth/capture instructions if login is required
- optional vision credential for automatic semantic enrichment/visual QA
- GPU target when self-host benchmarking begins
- legal review of the final creator NIL/AI-use/commission contract language

## Merge policy

Keep PR #5 draft until the fixture capture + assembly path is verified end-to-end and the first provider-ready job has been inspected. Live spending is not required to merge the architecture. Rights/spend gates must remain intact.
