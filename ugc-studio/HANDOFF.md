# UGC Studio Handoff

Last updated: 2026-09-12
Branch: `feat/ugc-studio-v1`
PR: #5

## Product direction

Build a UGC/Reels production system that owns the creative workflow and calls underlying models directly. Higgsfield is optional and disabled by default as a rendering dependency.

Higgsfield's public skills repo is treated separately as a useful **knowledge/benchmark upstream**.

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

Use installed skills to research current Higgsfield behavior or run optional benchmarks. Do not let installation change the default direct-model router.

Durable notes:
- `docs/ugc-factory/HIGGSFIELD_SKILLS_RESEARCH.md`
- `docs/ugc-factory/MODEL_PRICING_AND_SOURCES.md`
- `docs/ugc-factory/CREATOR_AND_REFERENCE_PIPELINE.md`
- `ugc-studio/providers/research-sources.json`

## Implemented

### Product/contracts
- UGC PRD + direct-model execution plan
- OpenSpec proposal/design/tasks
- CreativeSpec schema
- Creator/rights schema
- CreatorIdentityPack schema
- factual ReferenceObservation schema
- ReferenceSemanticLabels schema
- final ReferenceAnalysis schema

### Creator identity ingestion

`.archon/scripts/ugc/build_identity_pack.py` now builds a portable creator pack from an explicit manifest.

It:
- requires active consent for real/founder identities
- requires an agreement reference for real/founder identities
- blocks motion-transfer samples unless creator rights explicitly allow `motion_transfer`
- hashes local assets with SHA-256
- records size/MIME and best-effort ffprobe media metadata
- accepts remote references without silently downloading them
- records identity-view coverage and onboarding warnings
- leaves `semantic_identity_review_required: true` rather than claiming file existence proves identity quality

Current onboarding target: roughly 8-12 varied clean identity images, while remaining provider-neutral.

Example:
`ugc-studio/examples/creator-import.example.json`

### Reference intelligence

Reference analysis now has a strict two-stage boundary:

```text
video
  -> factual observation
  -> semantic enrichment
  -> final ReferenceAnalysis
```

`.archon/scripts/ugc/observe_reference.py` provides deterministic observation:
- ffprobe duration/dimensions/FPS/audio
- source SHA-256
- ffmpeg scene-change candidates
- observed segment boundaries
- optional midpoint keyframes
- optional transcript JSON ingestion
- optional local OpenAI Whisper CLI transcription

It intentionally does **not** infer hook/app-demo/creator/CTA meaning from cuts.

`.archon/scripts/ugc/build_reference_analysis.py` combines factual observations with strict semantic labels from a multimodal agent or human reviewer.

It:
- requires every observed segment to be labeled exactly once
- validates shot types
- calculates pacing from observed segment duration
- keeps rights separate from visual interpretation
- only enables literal motion reference use for `licensed_performance_transfer` or `owned_source`
- can print the semantic-enrichment prompt for an external multimodal agent

Example semantic labels:
`ugc-studio/examples/reference-semantics.example.json`

Automatic multimodal semantic-label API integration is still pending. The schema, prompt, and compiler boundary are complete.

### Rights and live safeguards
- creator rights-policy evaluator
- public/third-party `creative_dna_only` references cannot become literal motion-transfer sources
- direct job compilation requires `rights_approved: true`
- live provider execution independently requires `rights_approved: true`
- live execution also requires `approved_for_spend: true`
- `FAL_KEY` remains runtime-only

### Direct model router
- dated pricing/capability registry
- Wan direct for draft/cost-first generation
- Kling Standard for normal creator shots
- Kling Motion for licensed/owned motion transfer
- Seedance/Kling premium for premium/reference-heavy work
- Higgsfield excluded from default routing
- budget cap + alternatives + retry escalation

### Prompt compiler
`.archon/scripts/ugc/prompt_compiler.py`
- motion-first I2V guidance
- licensed motion-transfer guidance
- structured multimodal reference guidance
- prompt length cap
- native-audio vs later-lip-sync handling
- prompt strategy/version saved to job provenance

### fal execution
- `@fal-ai/client` pinned to `1.10.1`
- provider-ready jobs for Wan I2V, Kling I2V, Kling Motion and Seedance reference-to-video
- renderer is dry-run unless `--live`
- completed live jobs write provenance/download the asset

### App capture
- Playwright `1.63.0`
- declarative click/tap/fill/press/wait/scroll/screenshot actions
- vertical capture defaults
- capture provenance

### Reel assembly
- Remotion + CLI `4.0.523`
- React/ReactDOM `19.3.0`
- 1080x1920 composition
- creator/app/B-roll sequencing
- timed captions + CTA
- local asset staging
- FFmpeg H.264/AAC normalization, loudness normalization and faststart

### QA retry policy
- one same-tier retry for stochastic failures
- structural quality failures may escalate one tier
- budget checked before retry
- rights/source/UI failures stop and cannot be routed around

### Tests
Current unit coverage includes:
- creator rights
- reference rights modes
- direct routing/cost
- live/direct render guards
- retry/escalation
- prompt compiler
- creator identity-pack rights/provenance
- reference segmentation/compiler guards

GitHub Actions workflow: `.github/workflows/ugc-studio-tests.yml`.

## No paid work has been run

No direct provider generation has been submitted from this branch.

## Creator import workflow

```bash
python .archon/scripts/ugc/build_identity_pack.py \
  ./creator-import.json \
  --out ./creator-pack.json
```

For production, replace example URLs/agreement references with actual approved assets and records.

## Reference workflow

```bash
python .archon/scripts/ugc/observe_reference.py ./reel.mp4 \
  --id ref-001 \
  --rights-mode creative_dna_only \
  --keyframes-dir ./ref-001-keyframes \
  --out ./ref-001-observation.json

python .archon/scripts/ugc/build_reference_analysis.py \
  ./ref-001-observation.json \
  --print-prompt

# multimodal agent/human writes ref-001-semantics.json

python .archon/scripts/ugc/build_reference_analysis.py \
  ./ref-001-observation.json \
  --semantics ./ref-001-semantics.json \
  --out ./ref-001-analysis.json
```

Add `--whisper` to the observation command only when a local Whisper CLI is installed, or provide `--transcript-json` from another transcription system.

## First live benchmark

Use one synthetic or explicitly consented creator identity pack and one 5-second hook.

1. Build/inspect CreatorIdentityPack.
2. Confirm rights record and approved source asset.
3. Compile the CreativeSpec shot into a direct fal job.
4. Inspect prompt strategy, provider payload, and estimated cost.
5. Deliberately set `approved_for_spend: true`.
6. Run with `FAL_KEY` and `--live`.
7. Score output.
8. Compare Wan 3.0 720p vs Kling 3 Standard on equivalent direction.
9. Escalate only when measured quality warrants it.
10. Optionally benchmark comparable Higgsfield output after checking current credit cost.

Track raw provider cost, pricing snapshot/date, prompt compiler version, attempts, identity consistency, face/hands/body quality, motion adherence, audio/lip sync, human pass/fail and cost per usable approved second.

## Remaining autonomous slices

1. Automatic multimodal semantic-label adapter for ReferenceObservation.
2. Identity/lip-sync/final-timeline QA scorers.
3. Measured provider pass-rate database replacing static quality priors.
4. Actual provider cost reconciliation.
5. Self-host Wan2.2 Animate worker + GPU cost benchmark.
6. Maestro mobile capture lane.
7. Performance analytics feedback into creative ranking.
8. Periodic upstream-model/pricing refresh utility.
9. Creator-rights revocation propagation.

## External inputs still needed for real production

- `FAL_KEY` or another direct-provider credential
- actual approved creator reference assets
- actual creator agreement/rights record references
- licensed/owned motion clips for literal motion transfer
- production app auth/capture instructions where login is required
- multimodal provider credential if automatic semantic enrichment uses a paid API
- GPU target when self-host benchmarking begins
- legal review of final creator NIL/AI-use/commission language

## Merge policy

Keep PR #5 draft until fixture capture + assembly are verified end-to-end and the first provider-ready direct job has been inspected. Live spending is not required to merge the architecture, but rights/spend gates must remain intact.
