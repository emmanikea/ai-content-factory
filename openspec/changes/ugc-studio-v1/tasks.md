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

## Phase 1: local domain layer

- [ ] Add filesystem repositories for campaigns, creators, references, specs, jobs, and artifacts.
- [ ] Add full JSON Schema runtime validation.
- [x] Add rights-policy evaluator.
- [ ] Add CreativeSpec generator interface.
- [x] Add reference-analysis result format.
- [x] Add dry-run cost estimator.
- [x] Add provider capability contract.

Exit condition: campaign -> CreativeSpec -> approval -> render plan can run without spending on media.

## Phase 2: direct-model render path

The default production path calls underlying models directly. Higgsfield remains optional for proprietary features or benchmark/fallback cases where it proves better economics.

- [x] Add dated direct-model registry with Wan, Kling, Seedance capabilities and pricing formulas.
- [x] Add cost/quality router that excludes Higgsfield by default.
- [x] Add direct fal provider runner with explicit live/spend gates.
- [x] Compile CreativeSpec creator shots into provider-ready Wan/Kling/Seedance/Kling-Motion jobs.
- [x] Pin current `@fal-ai/client` dependency.
- [ ] Run first credentialed direct-model render.
- [ ] Add actual-cost reconciliation after provider completion.
- [ ] Add self-hostable Wan worker configuration for high-volume cost reduction.
- [ ] Add direct/open identity-still generation worker.
- [ ] Keep the existing Higgsfield worker as optional only.

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
- [ ] Add background music ducking and loudness normalization.
- [ ] Add explicit FFmpeg output-normalization wrapper.
- [ ] Add artifact-preparation step for local Remotion static assets.

Exit condition: mixed creator + app + B-roll shots compile into a final Reel without asking a video model to create the edit.

## Phase 5: cost/quality routing

- [x] Score providers using capability, tier, configured quality and estimated cost.
- [x] Prefer low-cost/open paths for draft iteration.
- [x] Promote premium jobs to premium models by explicit tier.
- [ ] Replace static quality priors with measured QA pass rates.
- [ ] Add fallback/retry escalation policy.
- [x] Enforce per-concept render budget cap.
- [ ] Compare direct-model cost and QA against Higgsfield on the same test set.

Exit condition: provider selection is driven by measured quality-per-usable-dollar, not platform preference.

## Phase 6: creator identity system

- [ ] Add creator onboarding checklist.
- [ ] Add canonical identity/reference pack builder.
- [ ] Add voice-reference storage contract.
- [ ] Add wardrobe/location presets.
- [ ] Add performance-reference library.
- [x] Enforce explicit creator rights before render planning.
- [ ] Add revocation behavior.

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

## Autonomous vs external-input boundary

Implemented or implementable without paid generation:
- domain contracts and schemas
- Campaign Studio UI
- reference-analysis structure
- rights enforcement
- direct-model registry and router
- provider-ready job compilation
- spend-gated fal runner
- app-capture framework
- Remotion assembly
- unit/CI tests

Requires external credentials/assets or human decisions for live production:
- `FAL_KEY` or equivalent direct-provider credentials
- one approved creator identity/reference pack
- licensed/owned performance clips for literal motion transfer
- production app login flows where authentication is needed
- GPU infrastructure if self-hosting Wan2.2 Animate
- final legal review of creator NIL/commission agreements
- publishing credentials when automatic distribution is added
