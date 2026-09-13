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

- [x] Add atomic filesystem repositories for campaigns, creators, references, specs, jobs, artifacts, QA, and performance records.
- [ ] Add full JSON Schema runtime validation to all ingestion/write boundaries.
- [x] Add rights-policy evaluator.
- [x] Add deterministic CreativeSpec batch generator from CampaignBrief + ReferenceAnalysis.
- [x] Add CampaignBrief JSON Schema.
- [x] Add final ReferenceAnalysis result format.
- [x] Add factual ReferenceObservation schema.
- [x] Add deterministic ffprobe/ffmpeg reference observer.
- [x] Add scene-cut segmentation and optional keyframe extraction.
- [x] Add optional transcript JSON and local Whisper CLI ingestion.
- [x] Add strict semantic-label schema for observed segments.
- [x] Add observation + semantic-label -> ReferenceAnalysis compiler.
- [x] Keep reference rights separate from semantic interpretation.
- [x] Add optional automatic multimodal semantic-label adapter with fail-closed credential behavior.
- [x] Validate automatic semantic labels through the same final ReferenceAnalysis compiler.
- [x] Add dry-run cost estimator.
- [x] Add provider capability contract.
- [x] Add end-to-end no-spend integration coverage from campaign/reference to provider-ready job.

Exit condition: campaign -> reference observation/analysis -> CreativeSpec -> approval -> render plan can run without spending on media.

## Phase 2: direct-model render path

The default production path calls underlying models directly. Higgsfield remains optional for proprietary features or benchmark/fallback cases where it proves better economics.

- [x] Add dated direct-model registry with Wan, Kling, Seedance capabilities and pricing formulas.
- [x] Add cost/quality router that excludes Higgsfield by default.
- [x] Add direct fal provider runner with explicit live/spend gates.
- [x] Compile CreativeSpec creator shots into provider-ready Wan/Kling/Seedance/Kling-Motion jobs.
- [x] Require explicit rights approval in compiled/live jobs.
- [x] Derive normal creator render rights approval from CreatorIdentityPack rather than hand-entering it.
- [x] Preserve rights-decision evidence in render provenance.
- [x] Fix product/category allow-list semantics so a populated category restriction cannot be bypassed by an empty product list.
- [x] Pin current `@fal-ai/client` dependency.
- [x] Research Higgsfield's public skills repo as an optional knowledge/benchmark layer.
- [x] Record Higgsfield upstream version/commit/license and relevant skill/reference paths.
- [x] Add dated model pricing/source ledger and machine-readable research-source registry.
- [x] Add model-aware prompt compiler informed by public provider/Higgsfield prompting guidance.
- [x] Store prompt compiler version/strategy in direct-job provenance.
- [ ] Run first credentialed direct-model render.
- [ ] Add provider actual-cost reconciliation after completion where the provider exposes billable usage.
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
- [x] Add benchmark ledger for attempts, QA status, estimated/actual spend, usable seconds, and prompt strategy.
- [x] Count failed generations as spend with zero usable seconds.
- [x] Add measured pass-rate / cost-per-usable-second routing after a minimum sample threshold.
- [x] Keep static quality priors until enough measured samples exist.
- [x] Add cost-aware fallback/retry escalation policy.
- [x] Do not retry around rights, source, or deterministic UI failures.
- [x] Enforce per-concept render budget cap.
- [ ] Compare direct-model cost and QA against Higgsfield on the same live test set.

Exit condition: provider selection is driven by measured quality-per-usable-dollar once sufficient benchmark evidence exists.

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
- [x] Add creator-pack -> render-assets resolver with date/product/platform/transformation rights checks.
- [x] Add optional visual identity consistency QA when local canonical references and a vision credential are available.
- [ ] Add revocation propagation behavior through derived jobs/artifacts.

Exit condition: an approved creator can safely become a reusable production asset.

## Phase 7: QA and ranking

- [x] Add QAResult schema.
- [x] Add deterministic video QA for duration, resolution, vertical aspect, audio presence, and black frames.
- [x] Keep technically valid clips in `needs_review` until semantic quality checks actually run.
- [x] Add optional sampled-frame visual QA for identity consistency, anatomy, captions/text, and obvious visual artifacts.
- [ ] Add audio-aware lip-sync QA.
- [ ] Add ground-truth product/UI correctness comparison.
- [x] Add final-Reel deterministic/sampled-frame QA profile.
- [ ] Automatically persist every QA result alongside its artifact record.
- [ ] Rank concepts before render by expected quality, novelty, cost, and performance history.

Exit condition: the system rejects obvious bad outputs before human approval and learns which routes produce usable output.

## Phase 8: feedback loop

- [x] Define a model-generation performance event/benchmark contract.
- [ ] Define social/ad performance event contract for published creatives.
- [ ] Ingest platform/ad analytics manually or through connectors.
- [ ] Link published performance to CreativeSpec dimensions.
- [ ] Calculate hook/creator/format/CTA performance summaries.
- [ ] Feed campaign performance learnings into the next concept generation/ranking pass.

Exit condition: the system becomes a creative learning loop rather than a generation queue.

## Knowledge-source refresh policy

During active development, periodically re-check:

- `higgsfield-ai/skills` version/commit and relevant generate/Marketing Studio/Soul docs
- direct provider model schemas
- direct provider pricing
- optional Higgsfield credit/job economics if benchmarking it

Do not overwrite historical job provenance with new pricing or new recommendations. Every benchmark preserves the source/rate assumptions that existed when it ran.

## Autonomous vs external-input boundary

Implemented without paid video generation:
- domain contracts and schemas
- Campaign Studio UI
- atomic local domain store
- factual reference observation and segmentation
- optional local/JSON transcription ingestion
- reference semantic-label contract + compiler
- optional credentialed vision semantic-enrichment adapter
- rights enforcement
- creator identity-pack contract + builder
- creator-pack rights resolver for render assets
- campaign -> CreativeSpec batch generation
- direct-model registry and router
- provider-ready job compilation
- model-aware prompt compiler
- dated pricing and research-source ledger
- rights + spend-gated fal runner
- app-capture framework
- local-media staging
- Remotion assembly
- FFmpeg normalization
- deterministic + optional semantic visual QA
- benchmark ledger and measured routing
- retry/escalation policy
- unit/CI + no-spend integration tests
- end-to-end operator/agent runbook

Requires external credentials/assets or human decisions for live production:
- `FAL_KEY` or equivalent direct-provider credentials
- one approved creator identity/reference pack
- licensed/owned performance clips for literal motion transfer
- vision/model credential for automatic semantic labeling/visual QA; manual review remains supported without one
- production app login flows where authentication is needed
- GPU infrastructure if self-hosting Wan2.2 Animate
- final legal review of creator NIL/AI-use/commission agreements
- publishing credentials when automatic distribution is added
