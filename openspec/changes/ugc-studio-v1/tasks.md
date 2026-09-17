# UGC Studio v1 Tasks

## Phase 0: contracts and visual shell
- [x] PRD, OpenSpec, architecture, CreativeSpec and creator/rights schemas.
- [x] Campaign Studio prototype with reference/creator/product selectors.
- [x] Variation controls, ranked concept cards, and render-cost preview states.

## Phase 1: local domain + reference intelligence
- [x] Atomic filesystem repositories for campaigns, creators, references, specs, jobs, artifacts, QA, performance, and revocation state.
- [ ] Finish JSON Schema validation at every ingestion/write boundary.
- [x] Rights evaluator and request-specific creator rights resolution.
- [x] CampaignBrief + ReferenceAnalysis -> CreativeSpec batch generator.
- [x] ReferenceObservation, scene segmentation, optional transcription, semantic labels, and final ReferenceAnalysis.
- [x] Optional multimodal semantic-label adapter with fail-closed credential behavior.
- [x] End-to-end no-spend integration coverage.

## Phase 2: hosted/direct render paths
Providers remain independent and evidence-driven. No provider is automatically preferred before comparable benchmark data exists.

- [x] Dated fal registry for Wan/Kling/Seedance and cost formulas.
- [x] Direct fal runner with explicit rights + spend gates.
- [x] Provider-ready Wan/Kling/Seedance/Kling-Motion job compilation.
- [x] Model-aware prompt compiler with prompt strategy/version provenance.
- [x] Native Higgsfield API adapter with authenticated request quote, polling, cancellation, webhooks, download and provenance.
- [x] Keep Higgsfield catalog account/model-doc driven instead of hard-coding the shared catalog.
- [x] Native OpenRouter async video adapter with live catalog preflight and completed `usage.cost` reconciliation.
- [x] Native direct Google Veo 3.1 adapter with official-rate preflight, long-running operation polling and provenance.
- [x] Native Gemini Omni Flash adapter through the Interactions API.
- [x] Keep Veo Lite as the cheap Google baseline and Gemini Omni as the stronger/default Google video candidate.
- [x] Provider-neutral first-benchmark compiler for equivalent creator I2V jobs across fal Wan, OpenRouter Seedance Fast, Veo Lite, and Gemini Omni.
- [x] Normalize the first benchmark to common 4/6/8-second, 720p, 9:16, native-audio targets.
- [x] Keep every compiled benchmark job spend-disabled and preserve rights/prompt/pricing provenance.
- [x] Refuse to label motion-transfer jobs comparable until provider semantics can be normalized honestly.
- [ ] Run first credentialed video benchmark.
- [ ] Add self-host Wan worker configuration.
- [ ] Add direct/open identity-still worker.

## Phase 3: deterministic app capture
- [x] Playwright capture runner, declarative actions, vertical presets and provenance.
- [ ] Pointer/touch visualization.
- [ ] Maestro mobile capture lane.

## Phase 4: deterministic assembly
- [x] Remotion timeline, creator/app/B-roll sequencing, captions, CTA and audio controls.
- [x] Local asset staging and FFmpeg H.264/AAC/loudness/faststart normalization.
- [ ] Background-music ducking.

## Phase 5: cost/quality routing
- [x] Capability/tier/cost routing and dry-run budgets.
- [x] Retry/escalation policy with rights/source/UI hard stops.
- [x] Benchmark ledger for attempts, QA, estimates/actual spend, usable seconds and prompt strategy.
- [x] Failed generations count as spend with zero usable seconds.
- [x] Measured pass-rate and cost-per-usable-second routing after minimum sample threshold.
- [x] Static priors remain until sufficient measured samples exist.
- [x] Cross-provider no-spend preflight comparison preserving unlike evidence types.
- [x] Machine-readable ProviderPreflightComparison schema.
- [x] Emit an offline provider-cost comparison with each first-benchmark bundle.
- [x] Normalize provider/model/cost provenance across fal, OpenRouter, Google Veo and Gemini Omni when recording benchmark events.
- [x] Ingest OpenRouter provider-reported actual cost and Google Veo post-success derived billable cost when provider provenance exposes them.
- [x] Record paid generation failures even when no artifact exists for QA.
- [ ] Benchmark fal vs Higgsfield vs OpenRouter vs Google Veo/Omni on equivalent approved shots.
- [ ] Allow automatic cross-provider routing only after comparable measurements exist.

## Phase 6: creator identity system
- [x] CreatorIdentityPack schema, onboarding guidance, voice/wardrobe/location/performance contracts.
- [x] Portable pack builder/importer and source hashing/provenance.
- [x] Explicit motion-transfer permissions.
- [x] Creator-pack -> render-assets resolver.
- [x] Optional visual identity-consistency QA.
- [x] Separate current creator revocation state from immutable historical CreatorIdentityPack rights snapshots.
- [x] Block new render-asset preparation when a creator is currently revoked.
- [x] Propagate effective revocation to stored jobs by clearing rights/spend approval.
- [x] Mark derived artifacts as blocked from reuse and requiring distribution review.
- [x] Support future-effective revocation records plus later explicit propagation.
- [ ] Optional Higgsfield Soul binding importer; keep it non-portable and secondary to the canonical pack.

## Phase 7: QA and concept ranking
- [x] QAResult schema.
- [x] Deterministic duration/resolution/aspect/audio/black-frame checks.
- [x] Optional sampled-frame identity/anatomy/text/artifact checks.
- [x] Final-Reel deterministic/sampled-frame QA profile.
- [x] Pre-render CreativeSpec ranking using structure, cost, optional measured history and shortlist diversity.
- [ ] Audio-aware lip-sync QA.
- [ ] Ground-truth app/UI correctness comparison.
- [ ] Automatically persist every QA result with its artifact record.

## Phase 8: feedback loop
- [x] Model-generation benchmark/performance contract.
- [ ] Published social/ad performance event contract.
- [ ] Analytics ingestion and CreativeSpec-dimension attribution.
- [ ] Hook/creator/format/CTA summaries.
- [ ] Feed campaign performance into future concept generation/ranking.

## Provider cost evidence

```text
fal         -> dated configured model pricing formulas
Higgsfield  -> authenticated request-specific quote (credits + usd)
OpenRouter  -> live pricing_skus preview + completed provider usage.cost
Google Veo  -> dated official $/second formula; successful jobs billed
Google Omni -> approximate official effective 720p video-output rate; input tokens separate
self-host   -> measured compute cost when benchmarked
```

Do not flatten these into one claim of equal precision. `compare_provider_preflight.py` preserves the evidence type; `benchmark_metrics.py` preserves the estimate/actual-cost source after generation.

## First benchmark contract

`.archon/scripts/ugc/build_provider_benchmark_jobs.py` accepts one rights-approved `creator_generated` shot and emits the comparable jobs that the available media representations permit.

- Hosted HTTPS image -> fal/OpenRouter.
- Local/base64 image -> Google Veo/Omni.
- Arbitrary creator media is never silently downloaded or uploaded.
- Every generated job starts with `approved_for_spend=false`.
- Motion-transfer and >8-second shots are excluded from the first apples-to-apples test.

Runbook: `docs/ugc-factory/FIRST_PROVIDER_BENCHMARK.md`.
Benchmark recording: `docs/ugc-factory/BENCHMARK_LEDGER_RECORDING.md`.
Revocation: `docs/ugc-factory/CREATOR_REVOCATION.md`.

## Knowledge-source refresh policy
Periodically re-check:
- `higgsfield-ai/skills`
- Higgsfield API/model-specific docs
- OpenRouter video catalog/lifecycle/pricing
- fal and Google model schemas/pricing, including Google's recommended default video model
- self-host compute economics

Historical provenance must keep the rate/catalog/quote assumptions that existed when each attempt ran.

## External production inputs
- provider credentials (`FAL_KEY`, `OPENROUTER_API_KEY`, `GEMINI_API_KEY`; `HF_CREDENTIALS` when Higgsfield is benchmarked)
- an approved or synthetic creator asset for the first live benchmark
- explicit small spend approval before any live provider call
- licensed/owned performance clips for literal transfer
- production app auth/capture instructions where needed
- GPU target for self-host benchmarking
- final legal review of creator NIL/AI-use/commission language
