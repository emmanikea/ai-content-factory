# UGC Studio v1 Tasks

## Phase 0: contracts and visual shell

- [x] Write PRD.
- [x] Write OpenSpec proposal.
- [x] Define architecture and migration path.
- [x] Add CreativeSpec JSON Schema.
- [x] Add Creator + rights JSON Schema.
- [x] Build visual Campaign Studio prototype with demo data.
- [x] Add reference / creator / product selectors.
- [x] Add variation controls and combinatorial estimate.
- [x] Add ranked concept review cards.
- [x] Add render-cost preview states.

Exit condition: the workflow is understandable and clickable before provider integration.

## Phase 1: local domain + reference intelligence

- [ ] Add filesystem repositories for campaigns, creators, references, specs, jobs, and artifacts.
- [ ] Add full JSON Schema runtime validation.
- [x] Add rights-policy evaluator.
- [ ] Add CreativeSpec generator interface.
- [x] Add final ReferenceAnalysis result format.
- [x] Add factual ReferenceObservation schema.
- [x] Add deterministic ffprobe/ffmpeg reference observer.
- [x] Add scene-cut segmentation and optional keyframe extraction.
- [x] Add optional transcript JSON and local Whisper CLI ingestion.
- [x] Add strict semantic-label schema for observed segments.
- [x] Add observation + semantic-label -> ReferenceAnalysis compiler.
- [x] Keep reference rights separate from semantic interpretation.
- [ ] Add automatic multimodal semantic-label adapter.
- [x] Add dry-run cost estimator.
- [x] Add provider capability contract.

Exit condition: campaign -> reference observation/analysis -> CreativeSpec -> approval -> render plan can run without spending on media.

## Phase 2: direct-model render path

The default production path calls underlying models directly. Higgsfield remains optional for proprietary features or benchmark/fallback cases where it proves better economics.

- [x] Add dated direct-model registry with Wan, Kling, Seedance capabilities and pricing formulas.
- [x] Add cost/quality router that excludes Higgsfield by default.
- [x] Add direct fal provider runner with explicit live/spend gates.
- [x] Compile CreativeSpec creator shots into provider-ready Wan/Kling/Seedance/Kling-Motion jobs.
- [x] Require explicit rights approval in compiled/live jobs.
- [x] Pin current `@fal-ai/client` dependency.
- [x] Research Higgsfield's public skills repo as an optional knowledge/benchmark layer.
- [x] Record Higgsfield upstream version/commit/license and relevant skill/reference paths.
- [x] Add dated model pricing/source ledger and machine-readable research-source registry.
- [x] Add model-aware prompt compiler informed by public provider/Higgsfield prompting guidance.
- [x] Store prompt compiler version/strategy in direct-job provenance.
- [ ] Run first credentialed direct-model render.
- [ ] Add actual-cost reconciliation after provider completion.
- [ ] Add self-hostable Wan worker configuration for high-volume cost reduction.
- [ ] Add direct/open identity-still generation worker.
- [x] Keep the existing Higgsfield worker optional rather than a default router target.

Exit condition: a CreativeSpec can render without requiring a Higgsfield subscription or Higgsfield credits.

## Phase 3: deterministic app capture

- [x] Add Playwright capture runner.
- [x] Add declarative capture script format.
- [x] Add vertical viewport/video presets.
- [ ] Add optional pointer/touch visualization.
- [ ] Add Maestro mobile capture contract.
- [x] Store capture provenance and version metadata.

Exit condition: a CreativeSpec can include real product/app interactions as timed shots.

## Phase 4: deterministic assembly

- [x] Add Remotion project pinned to current matching package versions.
- [x] Implement 1080x1920 UGC timeline component.
- [x] Add timed captions.
- [x] Support creator/app/B-roll video inserts through the same clip contract.
- [x] Add CTA overlay/card.
- [x] Support clip audio/mute/volume controls.
- [ ] Add background music ducking.
- [x] Add final loudness normalization.
- [x] Add explicit FFmpeg output-normalization wrapper.
- [x] Add artifact-preparation step for local Remotion static assets.

Exit condition: mixed creator + app + B-roll shots compile into a final Reel without asking a video model to create the edit.

## Phase 5: cost/quality routing

- [x] Score providers using capability, tier, configured quality and estimated cost.
- [x] Prefer low-cost/open paths for draft iteration.
- [x] Promote premium jobs to premium models by explicit tier.
- [ ] Replace static quality priors with measured QA pass rates.
- [x] Add cost-aware fallback/retry escalation policy.
- [x] Do not retry around rights, source, or deterministic UI failures.
- [x] Enforce per-concept render budget cap.
- [ ] Compare direct-model cost and QA against Higgsfield on the same test set.

Exit condition: provider selection is driven by measured quality-per-usable-dollar, not platform preference.

## Phase 6: creator identity system

- [x] Add creator onboarding checklist/guidance.
- [x] Define canonical creator identity-pack schema.
- [x] Define voice-reference storage contract inside identity pack.
- [x] Define wardrobe/location preset contract inside identity pack.
- [x] Define performance-reference library contract inside identity pack.
- [x] Enforce explicit creator rights before direct job compilation/render.
- [x] Add portable pack builder/importer.
- [x] Hash and record local asset provenance; leave remote assets un-fetched.
- [x] Require motion-transfer permission for performance samples marked transferable.
- [x] Add onboarding coverage warnings without pretending to perform semantic identity QA.
- [ ] Add semantic visual identity-reference QA.
- [ ] Add revocation propagation behavior.

Exit condition: an approved creator can safely become a reusable production asset.

## Phase 7: QA and ranking

- [ ] Extend visual QA to identity consistency.
- [ ] Add lip-sync QA.
- [ ] Add product/UI correctness checks.
- [ ] Add final timeline QA.
- [ ] Persist QA results per artifact.
- [ ] Rank concepts before render by expected quality, novelty, and cost.

Exit condition: the system rejects obvious bad outputs before a human sees them.

## Phase 8: feedback loop

- [ ] Define performance event contract.
- [ ] Ingest platform/ad analytics manually or through connectors.
- [ ] Link performance to CreativeSpec dimensions.
- [ ] Calculate hook/creator/format/CTA performance summaries.
- [ ] Feed learnings into the next generation/ranking pass.

Exit condition: the system becomes a creative learning loop rather than a generation queue.

## Knowledge-source refresh policy

During active development, periodically re-check:

- `higgsfield-ai/skills` version/commit and relevant generate/Marketing Studio/Soul docs
- direct provider model schemas
- direct provider pricing
- optional Higgsfield credit/job economics if benchmarking it

Do not overwrite historical job provenance with new pricing or new recommendations. Every benchmark should preserve the source/rate assumptions that existed when it ran.

## Autonomous vs external-input boundary

Implemented without paid generation:
- domain contracts and schemas
- Campaign Studio UI
- factual reference observation and segmentation
- optional local/JSON transcription ingestion
- reference semantic-label contract + compiler
- rights enforcement
- creator identity-pack contract + builder
- direct-model registry and router
- provider-ready job compilation
- model-aware prompt compiler
- dated pricing and research-source ledger
- rights + spend-gated fal runner
- app-capture framework
- local-media staging
- Remotion assembly
- FFmpeg normalization
- retry/escalation policy
- unit/CI tests

Requires external credentials/assets or human decisions for live production:
- `FAL_KEY` or equivalent direct-provider credentials
- one approved creator identity/reference pack
- licensed/owned performance clips for literal motion transfer
- multimodal model/provider credentials if automatic semantic labeling is enabled
- production app login flows where authentication is needed
- GPU infrastructure if self-hosting Wan2.2 Animate
- final legal review of creator NIL/AI-use/commission agreements
- publishing credentials when automatic distribution is added
