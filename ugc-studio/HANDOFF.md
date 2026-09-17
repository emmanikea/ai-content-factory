# UGC Studio Handoff

Last updated: 2026-09-17  
Branch: `feat/ugc-studio-v1`  
PR: #5

## Product direction

UGC Studio is provider-independent. We own creative intelligence, creator identity/rights, deterministic app capture, assembly, QA, and the learning loop. Providers compete underneath that layer.

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
First-class hosted provider, not automatically preferred.

- `ugc-studio/providers/higgsfield/client.py`
- `docs/ugc-factory/HIGGSFIELD_API_INTEGRATION.md`

Uses authenticated request-specific `credits` + `usd` preflight, explicit cost cap, async polling, webhooks, output download and provenance. Catalog stays account/model-doc driven rather than hard-coded.

### OpenRouter
First-class hosted aggregator, not automatically preferred.

- `ugc-studio/providers/openrouter/client.py`
- `docs/ugc-factory/OPENROUTER_VIDEO_INTEGRATION.md`

Uses the async `/api/v1/videos` lifecycle and live `/api/v1/videos/models` catalog. The adapter snapshots capabilities/`pricing_skus`, validates documented inputs, requires an expected-cost + maximum-cost envelope before live submission, and records completed `usage.cost` as provider-reported actual spend.

### Direct Google / Veo
Direct provider lane implemented with the Gemini Developer API.

- `ugc-studio/providers/google-veo/client.py`
- `ugc-studio/providers/google-veo/README.md`
- `docs/ugc-factory/GOOGLE_VEO_INTEGRATION.md`

Current official paid rates recorded 2026-09-17:

```text
Veo 3.1 Lite:     $0.05/s 720p | $0.08/s 1080p
Veo 3.1 Fast:     $0.10/s 720p | $0.12/s 1080p | $0.30/s 4k
Veo 3.1 Standard: $0.40/s 720p | $0.40/s 1080p | $0.60/s 4k
```

Veo 3.1 audio is always on. Google documents charges only for successful generations. The adapter validates 4/6/8-second constraints, 1080p/4k eight-second requirements, vertical/horizontal aspect ratios, reference-image constraints, and one-video-per-request. It polls long-running operations, downloads completed outputs immediately because Google retention is 2 days, and stores the pricing snapshot/cost basis in provenance.

V1 supports text-to-video, image-to-video, first/last-frame interpolation, and Standard/Fast asset-reference images. Video extension is intentionally deferred to a dedicated provenance contract.

## Cross-provider no-spend comparison

`.archon/scripts/ugc/compare_provider_preflight.py`

This is the shared decision surface before any generation spend. It accepts provider job JSONs and preserves unlike cost evidence rather than forcing all providers into one fake estimate format.

Offline:

```bash
python .archon/scripts/ugc/compare_provider_preflight.py \
  ./fal-job.json \
  ./openrouter-job.json \
  ./google-job.json \
  ./higgsfield-job.json \
  --out ./provider-comparison.json
```

Authenticated read/estimate mode:

```bash
python .archon/scripts/ugc/compare_provider_preflight.py \
  ./fal-job.json ./openrouter-job.json ./google-job.json ./higgsfield-job.json \
  --network \
  --out ./provider-comparison.json
```

`--network` only performs read/estimate calls; it never submits generation.

Schema:
`ugc-studio/schemas/provider-preflight-comparison.schema.json`

Documentation:
`docs/ugc-factory/PROVIDER_PREFLIGHT_COMPARISON.md`

The output keeps:
- provider/model
- preflight cost when known
- `cost_evidence_type`
- evidence precision
- provider-specific details
- post-run actual-cost source
- whether authenticated network preflight can strengthen the evidence

It may show a `cost_only_order`, but that is only a benchmark-priority aid, not a production-provider recommendation.

## Cost evidence must stay typed

Do not treat every provider's number as equally authoritative:

```text
Higgsfield -> provider-authenticated request quote
OpenRouter -> current catalog preview + provider-reported completed usage.cost
Google Veo -> dated official per-second pricing formula
fal        -> dated configured provider pricing formula
self-host  -> future measured compute economics
```

The benchmark ledger should preserve provider, source/date, estimate type, actual-cost source, and QA outcome.

## Existing core factory

### Reference intelligence
`observe_reference.py`, `build_reference_analysis.py`, `enrich_reference_semantics.py`.

Deterministic facts stay separate from semantic creative interpretation. Public references default to `creative_dna_only`; literal performance transfer requires licensed/owned rights.

### Creator identity and rights
`build_identity_pack.py`, `prepare_creator_assets.py`, and the CreatorIdentityPack schema.

The canonical creator record is provider-neutral. Provider-specific identity handles remain secondary bindings.

### Creative generation/ranking
`generate_creative_specs.py` and `rank_creative_specs.py`.

Campaigns expand creator × hook × CTA × location × outfit up to a configured cap. Ranking uses observable structure, cost, optional measured history and shortlist diversity; it is not presented as a virality prediction.

### Product truth
- `ugc-studio/capture/`: Playwright real app/UI capture
- `ugc-studio/assembly/`: Remotion + FFmpeg final assembly

Generative models should not recreate exact app UI by default.

### QA + learning
`qa_video.py`, `enrich_video_qa.py`, `benchmark_metrics.py`, `retry_policy.py`.

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

## First benchmark frontier

The user already has fal, OpenRouter and Gemini credentials. Higgsfield credentials have not been confirmed.

Use one approved/synthetic creator asset and one 4–5 second hook. Candidate low-cost starting points should include:

1. direct Veo 3.1 Lite 720p
2. OpenRouter current cheapest suitable creator-video route after catalog preflight
3. fal Wan 3.0 720p
4. fal Kling Standard if the cheaper outputs fail QA
5. Higgsfield equivalent only when credentials are available

For every attempt:
- preserve pricing source/date or catalog/quote snapshot
- record provider/model and prompt strategy
- run the same QA profile
- count failed spend as zero usable seconds
- calculate cost per usable approved second

Do not change automatic provider preference until comparable evidence exists.

## Remaining high-value work

1. Provider-neutral asset preparation + provider job compilation from one CreativeSpec/creator pack.
2. First small credentialed fal/OpenRouter/Google benchmark with an approved or synthetic creator asset and explicit spend envelope.
3. Creator-rights revocation propagation.
4. Audio-aware lip-sync QA.
5. Ground-truth app/UI correctness QA.
6. Background-music ducking.
7. Maestro mobile capture.
8. Self-host Wan worker/benchmark.
9. Published social/ad performance ingestion.
10. Optional Higgsfield Soul binding importer.

## Merge policy

Keep PR #5 draft until fixture capture + assembly are verified end-to-end and at least one provider-ready benchmark path has been inspected. Live spending is not required to merge architecture. Rights/spend gates must remain intact.
