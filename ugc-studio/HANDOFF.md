# UGC Studio Handoff

Last updated: 2026-09-17  
Branch: `feat/ugc-studio-v1`  
PR: #5

## Product direction

UGC Studio is provider-independent. We own creative intelligence, creator identity/rights, deterministic app capture, assembly, QA, and the learning loop. fal, OpenRouter, Google, Higgsfield and future self-hosted workers compete underneath that layer.

```text
ReferenceAnalysis + CreatorIdentityPack + CampaignBrief
                     ↓
              CreativeSpec variants
                     ↓
               concept ranking
                     ↓
              provider candidates
        fal | OpenRouter | Google | Higgsfield | self-host
                     ↓
          provider-appropriate preflight
                     ↓
               explicit spend gate
                     ↓
                   render
                     ↓
                     QA
                     ↓
           cost per usable approved second
```

## Provider status

### fal
Implemented direct paths for Wan I2V, Kling I2V, Kling Motion and Seedance reference-to-video. Live jobs require rights approval, spend approval, runtime `FAL_KEY`, and `--live`.

### Higgsfield
First-class hosted provider, but not automatically preferred.

Files:
- `ugc-studio/providers/higgsfield/client.py`
- `ugc-studio/providers/higgsfield/README.md`
- `docs/ugc-factory/HIGGSFIELD_API_INTEGRATION.md`

Key behavior:
- authenticated request-specific `credits` + `usd` estimate before generation
- explicit provider cost cap
- async submission/polling
- cancellation primitive
- webhook support
- artifact download/provenance
- catalog intentionally not hard-coded because account/model-specific docs are authoritative

### OpenRouter
First-class hosted video provider, also not automatically preferred.

Files:
- `ugc-studio/providers/openrouter/client.py`
- `ugc-studio/providers/openrouter/README.md`
- `docs/ugc-factory/OPENROUTER_VIDEO_INTEGRATION.md`

Current API lifecycle:
- `POST /api/v1/videos`
- `GET /api/v1/videos/{id}`
- `GET /api/v1/videos/{id}/content?index=0`
- live model/capability/pricing discovery through `GET /api/v1/videos/models`

OpenRouter does not currently document a Higgsfield-style authoritative per-request video estimate endpoint. Therefore the adapter:
- snapshots live model capabilities and `pricing_skus`
- validates documented parameters where possible
- requires `expected_cost_usd` + `max_provider_cost_usd` for live submission
- requires `rights_approved=true` + `approved_for_spend=true`
- records final provider-reported `usage.cost` as actual spend
- records any actual overage instead of hiding it
- supports terminal callbacks and authenticated downloads

The completed `usage.cost` is especially useful for our benchmark ledger.

### Direct Google/Veo
Not implemented yet. This is the next provider slice because `GEMINI_API_KEY` is already available.

## Existing core factory

### Reference intelligence
- `observe_reference.py`
- `build_reference_analysis.py`
- `enrich_reference_semantics.py`

Scene cuts/factual metadata stay separate from semantic creative interpretation. Public references default to `creative_dna_only`; literal performance transfer requires licensed/owned rights.

### Creator identity and rights
- `build_identity_pack.py`
- `prepare_creator_assets.py`
- `creator-identity-pack.schema.json`

The canonical creator record is provider-neutral. Provider-specific identity IDs remain secondary bindings.

### Creative generation/ranking
- `generate_creative_specs.py`
- `rank_creative_specs.py`

Campaigns expand creator × hook × CTA × location × outfit up to a configured cap. Ranking uses observable structure, cost, optional measured history and shortlist diversity; it is not presented as a virality prediction.

### Product truth
- `ugc-studio/capture/` uses Playwright for real app/UI capture.
- `ugc-studio/assembly/` uses Remotion + FFmpeg for the final Reel.

Generative models should not recreate exact app UI by default.

### QA + learning
- `qa_video.py`
- `enrich_video_qa.py`
- `benchmark_metrics.py`
- `retry_policy.py`

Failed paid generations count as spend with zero usable seconds. Measured provider quality only replaces static priors after enough samples.

Primary metric: **cost per usable approved second**.

## Credential convention

Root `.env.example` documents:

```text
OPENROUTER_API_KEY
GEMINI_API_KEY
FAL_KEY
HF_CREDENTIALS
NVIDIA_API_KEY
OPENAI_API_KEY
```

Real secrets stay in a local `.env` or deployed environment-variable store such as Vercel, never GitHub.

## No paid generation has been triggered from this branch

Every provider path remains dry-run/spend-gated by default.

## Benchmark order

Use one approved/synthetic creator asset and one 4–5 second hook:

1. compile comparable provider requests
2. perform provider-appropriate preflight
3. inspect current pricing/capability assumptions
4. explicitly approve a small spend envelope
5. render equivalent versions
6. deterministic + visual QA
7. record actual provider cost when exposed
8. calculate usable seconds and cost per usable approved second
9. only then change automatic routing preference

## Remaining high-value work

1. Direct Google/Veo provider adapter.
2. Cross-provider preflight normalization while preserving provider-specific semantics.
3. First small fal/OpenRouter/Higgsfield/Google benchmark.
4. Creator-rights revocation propagation.
5. Audio-aware lip-sync QA.
6. Ground-truth app/UI correctness QA.
7. Background-music ducking.
8. Maestro mobile capture.
9. Self-host Wan worker/benchmark.
10. Published social/ad performance ingestion.

## Merge policy

Keep PR #5 draft until fixture capture + assembly are verified end-to-end and at least one provider-ready benchmark path has been inspected. Live spending is not required to merge architecture. Rights/spend gates must remain intact.
