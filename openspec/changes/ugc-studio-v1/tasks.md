# UGC Studio v1 Tasks

## Phase 0: contracts and visual shell
- [x] PRD, OpenSpec, architecture, CreativeSpec and creator/rights schemas.
- [x] Campaign Studio prototype with reference/creator/product selectors.
- [x] Variation controls, ranked concept cards, and render-cost preview states.

## Phase 1: local domain + reference intelligence
- [x] Atomic filesystem repositories for campaigns, creators, references, specs, jobs, artifacts, QA, and performance.
- [ ] Finish JSON Schema validation at every ingestion/write boundary.
- [x] Rights evaluator and request-specific creator rights resolution.
- [x] CampaignBrief + ReferenceAnalysis -> CreativeSpec batch generator.
- [x] ReferenceObservation, scene segmentation, optional transcription, semantic labels, and final ReferenceAnalysis.
- [x] Optional multimodal semantic-label adapter with fail-closed credential behavior.
- [x] End-to-end no-spend integration coverage.

## Phase 2: hosted/direct render paths
Providers remain independent and evidence-driven. No hosted provider is automatically preferred before comparable benchmark data exists.

- [x] Dated fal registry for Wan/Kling/Seedance and cost formulas.
- [x] Direct fal runner with explicit rights + spend gates.
- [x] Provider-ready Wan/Kling/Seedance/Kling-Motion job compilation.
- [x] Model-aware prompt compiler with prompt strategy/version provenance.
- [x] Higgsfield skills research as a prompt/workflow knowledge source.
- [x] Native Higgsfield shared-lifecycle adapter.
- [x] Higgsfield authenticated preflight estimate (`credits` + `usd`) before live generation.
- [x] Higgsfield request submission, polling/backoff, cancellation primitive, webhook support, output download, and provenance.
- [x] Higgsfield provider model kept catalog-agnostic because account/model docs are authoritative.
- [x] Native OpenRouter async video provider adapter.
- [x] OpenRouter live catalog preflight/parameter validation through `/api/v1/videos/models`.
- [x] OpenRouter actual-cost reconciliation from completed `usage.cost`.
- [x] OpenRouter callback, polling, authenticated download, provenance, and spend/budget guards.
- [ ] Run first credentialed video benchmark.
- [ ] Add direct Google/Veo video provider adapter.
- [ ] Add self-host Wan worker configuration.
- [ ] Add direct/open identity-still worker.

## Phase 3: deterministic app capture
- [x] Playwright capture runner, declarative actions, vertical presets, provenance.
- [ ] Pointer/touch visualization.
- [ ] Maestro mobile capture lane.

## Phase 4: deterministic assembly
- [x] Remotion timeline, creator/app/B-roll sequencing, captions, CTA, audio controls.
- [x] Local asset staging and FFmpeg H.264/AAC/loudness/faststart normalization.
- [ ] Background-music ducking.

## Phase 5: cost/quality routing
- [x] Capability/tier/cost routing and dry-run budgets.
- [x] Retry/escalation policy with rights/source/UI hard stops.
- [x] Benchmark ledger for attempts, QA, estimates/actual spend, usable seconds, and prompt strategy.
- [x] Failed generations count as spend with zero usable seconds.
- [x] Measured pass-rate and cost-per-usable-second routing after minimum sample threshold.
- [x] Static priors remain until sufficient measured samples exist.
- [ ] Benchmark fal vs Higgsfield vs OpenRouter vs direct Google on equivalent approved shots.
- [ ] Add cross-provider preflight normalization without pretending unlike estimate mechanisms are equivalent.
- [ ] Allow automatic cross-provider routing only after comparable measurements exist.

## Phase 6: creator identity system
- [x] CreatorIdentityPack schema, onboarding guidance, voice/wardrobe/location/performance contracts.
- [x] Portable pack builder/importer and source hashing/provenance.
- [x] Explicit motion-transfer permissions.
- [x] Creator-pack -> render-assets resolver.
- [x] Optional visual identity-consistency QA.
- [ ] Revocation propagation through derived jobs/artifacts.
- [ ] Optional Higgsfield Soul binding importer; keep it non-portable and secondary to the canonical pack.

## Phase 7: QA and concept ranking
- [x] QAResult schema.
- [x] Deterministic duration/resolution/aspect/audio/black-frame checks.
- [x] Optional sampled-frame identity/anatomy/text/artifact checks.
- [x] Final-Reel deterministic/sampled-frame QA profile.
- [x] Pre-render CreativeSpec ranking using structure, cost, optional measured history, and shortlist diversity.
- [ ] Audio-aware lip-sync QA.
- [ ] Ground-truth app/UI correctness comparison.
- [ ] Automatically persist every QA result with its artifact.

## Phase 8: feedback loop
- [x] Model-generation benchmark/performance contract.
- [ ] Published social/ad performance event contract.
- [ ] Analytics ingestion and CreativeSpec-dimension attribution.
- [ ] Hook/creator/format/CTA summaries.
- [ ] Feed campaign performance into future concept generation/ranking.

## Provider policy

```text
CreativeSpec
    ↓
rights / assets
    ↓
provider candidates
    ├── fal
    ├── OpenRouter
    ├── Google
    ├── Higgsfield
    └── self-host
    ↓
provider-appropriate preflight / budget gate
    ↓
render
    ↓
actual cost + QA
    ↓
benchmark ledger
    ↓
cost per usable approved second
```

Higgsfield has an authenticated request-specific estimate. OpenRouter video exposes live catalog `pricing_skus` and completed `usage.cost`, but no documented equivalent authoritative per-request estimate endpoint. Keep those mechanisms distinct in provenance and UI.

## Knowledge-source refresh policy
Periodically re-check:
- `higgsfield-ai/skills`
- Higgsfield API shared lifecycle and account/model-specific docs
- OpenRouter video catalog/lifecycle/pricing semantics
- fal/Google model schemas and pricing
- self-host compute economics

Historical job provenance must keep the estimate/rate/catalog assumptions that existed when the job ran.

## External production inputs
- provider credentials (`FAL_KEY`, `OPENROUTER_API_KEY`, `GEMINI_API_KEY`; `HF_CREDENTIALS` when Higgsfield is benchmarked)
- approved creator/reference assets and agreement evidence
- licensed/owned performance clips for literal transfer
- production app auth/capture instructions where needed
- GPU target for self-host benchmarking
- final legal review of creator NIL/AI-use/commission language
