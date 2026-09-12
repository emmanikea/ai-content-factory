# UGC Studio v1 Tasks

## Phase 0: contracts and visual shell

- [x] Write PRD.
- [x] Write OpenSpec proposal.
- [x] Define architecture and migration path.
- [ ] Add CreativeSpec JSON Schema.
- [ ] Add Creator + rights JSON Schema.
- [ ] Build visual Campaign Studio prototype with demo data.
- [ ] Add reference / creator / product selectors.
- [ ] Add variation controls and combinatorial estimate.
- [ ] Add ranked concept review cards.
- [ ] Add render-cost preview states.

Exit condition: the workflow is understandable and clickable before provider integration.

## Phase 1: local domain layer

- [ ] Add filesystem repositories for campaigns, creators, references, specs, jobs, and artifacts.
- [ ] Add schema validation.
- [ ] Add rights-policy evaluator.
- [ ] Add CreativeSpec generator interface.
- [ ] Add reference-analysis result format.
- [ ] Add cost estimator.
- [ ] Add provider capability registry.

Exit condition: campaign -> CreativeSpec -> approval -> render plan can run without spending on media.

## Phase 2: existing Higgsfield path behind adapter

- [ ] Wrap existing Higgsfield/media-worker behavior in provider interface.
- [ ] Keep current UGC and product-pan workflows working.
- [ ] Record provider, model, cost estimate, prompt/config, and artifact provenance.
- [ ] Route one CreativeSpec shot through existing media worker.
- [ ] Add dry-run output for every planned render job.

Exit condition: the new domain layer can produce existing outputs without changing the existing provider behavior.

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

## Phase 5: multi-provider routing

- [ ] Add one reference/motion-transfer provider.
- [ ] Add one premium reference-to-video provider.
- [ ] Add one low-cost/open worker path.
- [ ] Add provider scoring by capability, cost, latency, and QA history.
- [ ] Add fallback/retry policy.
- [ ] Add per-campaign budget cap.

Exit condition: provider selection is configuration rather than application code.

## Phase 6: creator identity system

- [ ] Add creator onboarding checklist.
- [ ] Add canonical identity/reference set.
- [ ] Add voice-reference storage contract.
- [ ] Add wardrobe/location presets.
- [ ] Add performance-reference library.
- [ ] Enforce rights on every render request.
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
- app capture framework
- Remotion assembly
- QA framework
- tests

Requires external credentials/assets or human decisions:
- paid provider keys/auth
- creator consent documents and approved reference media
- creator voice/identity source assets
- production app login flows where authentication is needed
- final social-platform publishing credentials
- legal review of creator NIL/commission agreements
