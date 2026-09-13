# UGC Studio End-to-End Runbook

Last updated: 2026-09-12

This is the canonical operator/terminal-agent path for the current V1 branch.

The pipeline is designed so nearly everything can run without paid video generation. Paid inference appears only after concept generation, rights resolution, routing, and explicit spend approval.

## 0. Optional: install Higgsfield skills as a research layer

The direct-model router does not require Higgsfield.

For a terminal agent that should be able to inspect Higgsfield's current public playbook:

```bash
npx skills add higgsfield-ai/skills
```

or:

```bash
gh skill install higgsfield-ai/skills
```

Installing the skills does not change default routing. See `HIGGSFIELD_SKILLS_RESEARCH.md`.

## 1. Observe a reference Reel

For public/third-party inspiration, default to `creative_dna_only`:

```bash
python .archon/scripts/ugc/observe_reference.py ./input/reel.mp4 \
  --id ref-001 \
  --rights-mode creative_dna_only \
  --keyframes-dir ./ugc-studio/.runtime/ref-001-keyframes \
  --out ./ugc-studio/.runtime/ref-001-observation.json
```

Optional transcription:

```bash
# Existing transcript JSON
python .archon/scripts/ugc/observe_reference.py ./input/reel.mp4 \
  --id ref-001 \
  --rights-mode creative_dna_only \
  --transcript-json ./input/reel-transcript.json \
  --keyframes-dir ./ugc-studio/.runtime/ref-001-keyframes \
  --out ./ugc-studio/.runtime/ref-001-observation.json

# Or local Whisper CLI if installed
python .archon/scripts/ugc/observe_reference.py ./input/reel.mp4 \
  --id ref-001 \
  --rights-mode creative_dna_only \
  --whisper \
  --keyframes-dir ./ugc-studio/.runtime/ref-001-keyframes \
  --out ./ugc-studio/.runtime/ref-001-observation.json
```

## 2. Add semantic creative understanding

### Automatic optional path

If a Gemini key is available:

```bash
uv run .archon/scripts/ugc/enrich_reference_semantics.py \
  ./ugc-studio/.runtime/ref-001-observation.json \
  --out ./ugc-studio/.runtime/ref-001-semantics.json \
  --provenance-out ./ugc-studio/.runtime/ref-001-semantics-provenance.json
```

### Manual/provider-neutral path

```bash
python .archon/scripts/ugc/build_reference_analysis.py \
  ./ugc-studio/.runtime/ref-001-observation.json \
  --print-prompt
```

Have a multimodal agent/human return `ReferenceSemanticLabels` JSON.

Then compile the final analysis:

```bash
python .archon/scripts/ugc/build_reference_analysis.py \
  ./ugc-studio/.runtime/ref-001-observation.json \
  --semantics ./ugc-studio/.runtime/ref-001-semantics.json \
  --out ./ugc-studio/.runtime/ref-001-analysis.json
```

Public `creative_dna_only` references remain structurally reusable but cannot become literal motion sources.

## 3. Build a portable creator identity pack

Start from a manifest based on:

`ugc-studio/examples/creator-import.example.json`

```bash
python .archon/scripts/ugc/build_identity_pack.py \
  ./input/creator-import.json \
  --out ./ugc-studio/.runtime/creator-pack.json
```

Inspect the resulting warnings and rights snapshot before continuing.

## 4. Define a campaign

Example:

`ugc-studio/examples/bordereta-campaign.example.json`

Important campaign variables:

- product / category
- audience
- platform
- creator pool
- hooks
- CTAs
- locations
- outfits
- app/product capture instruction
- quality tier
- resolution
- max render cost
- native audio setting
- maximum number of CreativeSpecs

## 5. Generate the CreativeSpec batch

```bash
python .archon/scripts/ugc/generate_creative_specs.py \
  ./ugc-studio/examples/bordereta-campaign.example.json \
  ./ugc-studio/.runtime/ref-001-analysis.json \
  --out ./ugc-studio/.runtime/specs.json \
  --split-dir ./ugc-studio/.runtime/specs
```

This step is deterministic and does not call a video model.

It combines:

```text
creator × hook × CTA × location × outfit
```

up to `max_specs`, while reusing the abstract structure/timing from `ReferenceAnalysis`.

## 6. Plan model routing and cost before spending

For one generated spec:

```bash
python .archon/scripts/ugc/model_router.py \
  ./ugc-studio/.runtime/specs/<concept-id>.json \
  --out ./ugc-studio/.runtime/<concept-id>-plan.json
```

Optional measured benchmark history:

```bash
python .archon/scripts/ugc/model_router.py \
  ./ugc-studio/.runtime/specs/<concept-id>.json \
  --metrics ./ugc-studio/.runtime/model-benchmark-summary.json \
  --out ./ugc-studio/.runtime/<concept-id>-plan.json
```

Higgsfield remains excluded unless `--allow-higgsfield` is deliberately supplied.

## 7. Resolve creator rights for the exact render

For a normal creator shot:

```bash
python .archon/scripts/ugc/prepare_creator_assets.py \
  ./ugc-studio/.runtime/creator-pack.json \
  --product-id bordereta \
  --product-category apps \
  --platform instagram \
  --transform face_generation \
  --transform script_change \
  --require-remote \
  --out ./ugc-studio/.runtime/creator-assets.json
```

For licensed motion transfer, also request `motion_transfer` and select an approved performance sample.

This is the normal source of `rights_approved: true`; do not hand-author that flag as a shortcut.

## 8. Compile a provider-ready creator shot

```bash
python .archon/scripts/ugc/build_fal_job.py \
  ./ugc-studio/.runtime/specs/<concept-id>.json \
  --shot s1 \
  --assets ./ugc-studio/.runtime/creator-assets.json \
  --out ./ugc-studio/.runtime/<concept-id>-s1-job.json
```

The resulting job preserves:

- selected model/provider
- price estimate
- quality tier/resolution/aspect ratio
- prompt compiler version/strategy
- creator/reference provenance
- rights decision/evidence

It defaults to `approved_for_spend: false`.

## 9. Dry-run the provider request

```bash
cd ugc-studio/providers/fal
npm install
node render.mjs --job ../../.runtime/<concept-id>-s1-job.json
```

No credential or spend is required for dry-run inspection.

## 10. Live render only after explicit approval

Requirements:

```text
rights_approved = true
approved_for_spend = true
FAL_KEY present at runtime
--live explicitly supplied
```

Then:

```bash
FAL_KEY=... node render.mjs \
  --job ../../.runtime/<concept-id>-s1-job.json \
  --outdir ../../.runtime/renders/<concept-id>/s1 \
  --live
```

Never store provider keys in the repo.

## 11. Capture app/product footage deterministically

Use `ugc-studio/capture/` for Playwright-driven web flows. The CreativeSpec's `app_capture` shots should become real product footage rather than generated UI.

Mobile capture will later use the Maestro lane.

## 12. Run first-stage deterministic QA

```bash
python .archon/scripts/ugc/qa_video.py \
  ./ugc-studio/.runtime/renders/<concept-id>/s1/asset.mp4 \
  --artifact-id <concept-id>-s1 \
  --profile creator_shot \
  --expected-duration 3.0 \
  --out ./ugc-studio/.runtime/<concept-id>-s1-qa.json
```

A structurally valid clip remains `needs_review`; it is not automatically approved.

## 13. Run optional semantic visual QA

With a vision credential:

```bash
uv run .archon/scripts/ugc/enrich_video_qa.py \
  ./ugc-studio/.runtime/<concept-id>-s1-qa.json \
  --video ./ugc-studio/.runtime/renders/<concept-id>/s1/asset.mp4 \
  --identity-pack ./ugc-studio/.runtime/creator-pack.json \
  --concept "creator hook shot" \
  --out ./ugc-studio/.runtime/<concept-id>-s1-qa-enriched.json
```

This can evaluate sampled visual evidence such as identity drift, anatomy and visible artifacts. It deliberately does not pretend sampled stills prove lip sync.

## 14. Assemble the final Reel

Use `ugc-studio/assembly/` to combine:

```text
creator shots
+ real app/product capture
+ B-roll/owned footage
+ captions
+ CTA
```

Remotion produces the timeline; the FFmpeg normalization wrapper produces the final H.264/AAC 1080x1920 social-ready MP4.

## 15. QA the final Reel

Run deterministic QA with `--profile final_reel`, then semantic visual QA if available.

A final publishing decision should not be inferred solely from a technically valid MP4.

## 16. Record the benchmark outcome

```bash
python .archon/scripts/ugc/benchmark_metrics.py \
  --root ./ugc-studio/data \
  record \
  --job ./ugc-studio/.runtime/<concept-id>-s1-job.json \
  --qa ./ugc-studio/.runtime/<concept-id>-s1-qa-enriched.json \
  --actual-cost <provider-charge-if-known> \
  --attempt 1
```

Summarize history:

```bash
python .archon/scripts/ugc/benchmark_metrics.py \
  --root ./ugc-studio/data \
  summarize \
  --out ./ugc-studio/.runtime/model-benchmark-summary.json
```

Failed generations count as cost with zero usable seconds.

After enough comparable observations, the router may use measured pass rate and cost-per-usable-second instead of relying only on static model priors.

## 17. Persist reusable objects

The local V1 store supports:

```bash
python .archon/scripts/ugc/local_store.py --root ./ugc-studio/data put creators creator-a ./ugc-studio/.runtime/creator-pack.json
python .archon/scripts/ugc/local_store.py --root ./ugc-studio/data put references ref-001 ./ugc-studio/.runtime/ref-001-analysis.json
python .archon/scripts/ugc/local_store.py --root ./ugc-studio/data put specs <concept-id> ./ugc-studio/.runtime/specs/<concept-id>.json
```

Writes are atomic and can be guarded by expected version. The store is a migration seam, not the long-term database.

## Current external gates

A production live test still needs:

- real approved creator assets + agreement reference
- hosted URLs/upload staging for direct hosted generation
- `FAL_KEY` or another direct-provider credential
- a real reference Reel for end-to-end analysis
- production app auth/capture instructions when required

Everything before the live provider request can be exercised without video-generation spend.
