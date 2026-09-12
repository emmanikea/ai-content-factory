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
- [ ] Add schema validation.
- [x] Add rights-policy evaluator.
- [ ] Add CreativeSpec generator interface.
- [ ] Add reference-analysis result format.
- [x] Add dry-run cost estimator.
- [x] Add provider capability contract.

Exit condition: campaign -> CreativeSpec -> approval -> render plan can run without spending on media.

## Phase 2: direct-model render path

The default production path should call the underlying models directly rather than paying for Higgsfield as an intermediary. Higgsfield remains an optional benchmark/fallback for proprietary features such as Soul/Soul ID or when its economics are genuinely better for a specific job.

- [ ] Add direct Seedance adapter for premium multimodal/reference-to-video generation.
- [ ] Add direct Kling adapter for image-to-video and motion control.
- [ ] Add direct Wan adapter for motion transfer/character replacement.
- [ ] Add self-hostable Wan worker configuration for high-volume cost reduction.
- [ ] Add direct/open identity-still path for recurring creators.
- [ ] Record provider, model, actual quote, prompt/config, and artifact provenance.
- [ ] Route one CreativeSpec creator shot through a direct model adapter.
- [x] Add dry-run output for planned render jobs.
- [ ] Keep the existing Higgsfield worker as an optional adapter, not the default router target.

Exit condition: a CreativeSpec can render without requiring a Higgsfield subscription or Higgsfield credits.

## Phase 3: deterministic app capture

- [ ] Add Playwright capture runner.
- [ ] Add capture script format.
- [ ] Add vertical viewport presets.
- [ ] Add optional pointer/touch visualization.
- [ ] Add Maestro mobile capture contract.
- [ ] Store capture provenance and version.

Exit condition: a CreativeSpec can include real product/app interactions as timed shots.

## Phase 4: deterministic assembly

- [ ] Add Remotion project.
- [ ] Implement 9:16 UGC timeline component.
- [ ] Add captions.
- [ ] Add B-roll inserts.
- [ ] Add CTA overlay/card.
- [ ] Add audio mixing and normalization.
- [ ] Add FFmpeg output normalization.

Exit condition: mixed creator + app + B-roll shots compile into a final Reel without asking a video model to create the edit.

## Phase 5: cost/quality routing

- [ ] Score providers by capability, cost, latency, and QA history.
- [ ] Prefer low-cost/open paths for iteration.
- [ ] Promote winning concepts to premium models only when justified.
- [ ] Add fallback/retry policy.
- [ ] Add per-campaign budget cap.
- [ ] Compare direct-model cost and QA against Higgsfield on the same test set.

Exit condition: provider selection is driven by measured quality-per-dollar, not platform preference.

## Phase 6: creator identity system

- [ ] Add creator onboarding checklist.
- [ ] Add canonical identity/reference set.
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

Can be implemented autonomously now:
- domain contracts
- schemas
- UI
- reference-analysis structure
- rights enforcement logic
- provider interfaces
- dry-run planner
- direct-model adapters
- self-host worker configuration
- app capture framework
- Remotion assembly
- QA framework
- tests

Requires external credentials/assets or human decisions:
- direct provider API keys where applicable
- GPU infrastructure if self-hosting open video models
- creator consent documents and approved reference media
- creator voice/identity source assets
- production app login flows where authentication is needed
- final social-platform publishing credentials
- legal review of creator NIL/commission agreements
