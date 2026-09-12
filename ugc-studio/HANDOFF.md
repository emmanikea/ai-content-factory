# UGC Studio Handoff

Last updated: 2026-09-12
Branch: `feat/ugc-studio-v1`
PR: #5

## Product direction

Build a UGC/Reels production system that owns the creative workflow and calls underlying models directly. Higgsfield is optional and disabled by default.

Default routing philosophy:

```text
exact UI / owned media -> deterministic local capture/composition
cheap draft video      -> Wan direct
standard creator shot  -> Kling Standard direct
licensed motion        -> Kling Motion direct
premium/reference      -> Seedance / Kling premium
high-volume future     -> self-host Wan2.2 Animate
Higgsfield             -> proprietary-only / benchmark / explicit fallback
```

## Implemented

### Product/contracts
- `docs/ugc-factory/PRD.md`
- `docs/ugc-factory/DIRECT_MODEL_EXECUTION_PLAN.md`
- `openspec/changes/ugc-studio-v1/*`
- `ugc-studio/schemas/creative-spec.schema.json`
- `ugc-studio/schemas/creator.schema.json`
- `ugc-studio/schemas/reference-analysis.schema.json`

### Rights
- `.archon/scripts/ugc/rights.py`
- blocks inactive/expired/unapproved creator transformations
- blocks literal motion/character transfer from `creative_dna_only` references

### Direct model router
- `ugc-studio/providers/model-registry.json`
- `.archon/scripts/ugc/model_router.py`
- `.archon/scripts/ugc/plan_render.py` compatibility CLI
- direct Wan/Kling/Seedance pricing formulas are configuration data
- Higgsfield is not an enabled default provider

### fal execution
- `ugc-studio/providers/fal/`
- `@fal-ai/client` pinned to `1.10.1`
- `.archon/scripts/ugc/build_fal_job.py`
- provider-ready jobs for Wan I2V, Kling I2V, Kling Motion, Seedance reference-to-video
- `render.mjs` is dry-run unless `--live`
- live additionally requires `approved_for_spend: true` and `FAL_KEY`
- completed jobs write provenance and download the output asset

### App capture
- `ugc-studio/capture/`
- Playwright `1.63.0`
- declarative actions: goto/click/tap/fill/press/wait/wait_for/scroll/screenshot
- vertical capture defaults
- provenance JSON

### Reel assembly
- `ugc-studio/assembly/`
- Remotion + CLI pinned to `4.0.523`
- React/ReactDOM `19.3.0`
- 1080x1920 composition
- timed creator/app/B-roll clips
- captions
- CTA overlay
- per-clip audio controls

### Tests
- `.archon/scripts/ugc/test_rights.py`
- `.archon/scripts/ugc/test_model_router.py`
- `.github/workflows/ugc-studio-tests.yml`
- latest CI pass: successful on 2026-09-12

## No paid work has been run

No direct provider generation has been submitted from this branch.

The first paid test requires:
1. `FAL_KEY` in the runtime environment
2. an approved creator/reference image URL
3. a selected CreativeSpec shot
4. a compiled job whose `approved_for_spend` is deliberately changed to `true`
5. `node render.mjs --job <job.json> --live`

Do not put API keys in the repo.

## Recommended first live benchmark

Use one approved synthetic or consented creator image and one 5-second creator hook.

Run the same creative direction through:
1. Wan 3.0 720p
2. Kling 3 Standard
3. Kling 3 Pro or Seedance only if needed

Record:
- raw generation price
- retries required
- identity consistency
- facial realism
- hands/body
- lip sync/audio if enabled
- human usable/pass result

The metric is `cost per usable approved second`, not cost per generation.

## Next autonomous code slices

1. Artifact preparation for Remotion local/static media.
2. FFmpeg final normalization and loudness pass.
3. Retry/escalation policy driven by QA result.
4. Creator identity-pack builder and canonical references.
5. Automated reference-video segmentation/transcription -> ReferenceAnalysis.
6. Self-host Wan2.2 Animate worker contract and GPU benchmark.
7. Replace static model-quality priors with measured pass-rate data.
8. Connect performance analytics back to CreativeSpec dimensions.

## Inputs still needed for real production

- direct provider credentials
- approved creator reference assets
- licensed/owned performance clips when literal motion transfer is desired
- production app authentication/capture instructions where login is required
- legal review of final creator NIL/AI-use/commission agreement language

## Merge policy

Keep this PR draft until:
- first direct-model job is successfully compiled and dry-run inspected
- assembly local-asset path is validated
- capture + assembly can complete end-to-end on fixture media

Live provider spending is not required before the architecture can be merged, but the spend gate must remain intact.
