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
 fal | OpenRouter | Google Veo | Google Omni | Higgsfield | self-host
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
Wan I2V, Kling I2V, Kling Motion and Seedance reference-to-video are implemented. Live jobs require rights approval, spend approval, `FAL_KEY`, and an explicit live command.

### Higgsfield
First-class hosted provider, not automatically preferred. The adapter uses authenticated request-specific `credits` + `usd` estimates, async polling, cancellation, webhooks, output download and provenance. Model availability stays account/model-doc driven.

Files:
- `ugc-studio/providers/higgsfield/client.py`
- `docs/ugc-factory/HIGGSFIELD_API_INTEGRATION.md`

### OpenRouter
First-class video aggregator, not automatically preferred. Uses `/api/v1/videos`, live `/api/v1/videos/models` discovery and completed `usage.cost` as provider-reported actual spend.

Files:
- `ugc-studio/providers/openrouter/client.py`
- `docs/ugc-factory/OPENROUTER_VIDEO_INTEGRATION.md`

### Direct Google / Veo
Current official rates captured 2026-09-17:

```text
Veo 3.1 Lite:     $0.05/s 720p | $0.08/s 1080p
Veo 3.1 Fast:     $0.10/s 720p | $0.12/s 1080p | $0.30/s 4k
Veo 3.1 Standard: $0.40/s 720p | $0.40/s 1080p | $0.60/s 4k
```

Google documents charges only for successful Veo generations.

Files:
- `ugc-studio/providers/google-veo/client.py`
- `docs/ugc-factory/GOOGLE_VEO_INTEGRATION.md`

### Direct Google / Gemini Omni Flash
Google currently recommends `gemini-omni-1.1-flash` as the default new video-generation model for stronger coherence, multi-input reasoning, character consistency and conversational editing. UGC Studio keeps it separate from cheaper Veo Lite.

```text
Veo 3.1 Lite 720p -> ~$0.05/s
Gemini Omni 720p  -> ~$0.10/s effective video output + separately billed input tokens
```

Files:
- `ugc-studio/providers/google-omni/client.py`
- `docs/ugc-factory/GOOGLE_OMNI_INTEGRATION.md`

## Comparable first-benchmark compiler

`.archon/scripts/ugc/build_provider_benchmark_jobs.py`

Takes one rights-approved `creator_generated` CreativeSpec shot and compiles as many genuinely comparable jobs as the available asset forms permit:

```text
fal Wan 3.0 I2V
OpenRouter Seedance 2.0 Fast
Google Veo 3.1 Lite
Google Gemini Omni Flash
```

Contract:

```text
same approved creator identity image
same CreativeSpec intent/dialogue
720p
9:16
native audio
common 4 / 6 / 8 second target
approved_for_spend = false
```

Hosted HTTPS image -> fal/OpenRouter. Local/base64 image -> Google. The compiler never silently fetches or uploads creator media. Motion-transfer is intentionally excluded because provider semantics are not equivalent enough yet.

Runbook: `docs/ugc-factory/FIRST_PROVIDER_BENCHMARK.md`.

## Cross-provider preflight comparison

`.archon/scripts/ugc/compare_provider_preflight.py`

Preserves unlike evidence instead of pretending all cost numbers are equally precise:

```text
Higgsfield  -> provider-authenticated request quote
OpenRouter  -> current catalog preview + completed usage.cost
Google Veo  -> dated official per-second formula
Google Omni -> approximate effective 720p output rate; input tokens separate
fal         -> dated configured provider formula
self-host   -> future measured compute economics
```

`cost_only_order` is a benchmark-priority aid, not a provider recommendation.

## Benchmark ledger

`.archon/scripts/ugc/benchmark_metrics.py`

The recorder is now provider-neutral. It normalizes model identity/cost evidence across fal, OpenRouter and Google, can read provider `provenance.json`, and preserves request IDs and cost-source semantics.

Examples:

```bash
python .archon/scripts/ugc/benchmark_metrics.py record \
  --job ./provider.job.json \
  --qa ./qa.json \
  --provider-provenance ./provider-output/provenance.json
```

A paid generation failure with no artifact can also be recorded:

```bash
python .archon/scripts/ugc/benchmark_metrics.py record \
  --job ./provider.job.json \
  --generation-failure provider_failed \
  --actual-cost 0.42
```

Failed spend always contributes zero usable seconds.

Documentation: `docs/ugc-factory/BENCHMARK_LEDGER_RECORDING.md`.

## Creator revocation

Current authorization is now separate from immutable CreatorIdentityPack history.

`.archon/scripts/ugc/creator_revocation.py`

An effective revocation:
- creates a current-state revocation record,
- makes CLI asset preparation fail closed,
- sets matching stored jobs `rights_approved=false`,
- sets matching stored jobs `approved_for_spend=false`,
- marks stored artifacts `reuse_blocked=true`, and
- marks them `distribution_review_required=true`.

A historical `on_date` cannot bypass a revocation that is active now. Future-effective revocations can be recorded and later applied.

Documentation: `docs/ugc-factory/CREATOR_REVOCATION.md`.

## Existing core factory

### Reference intelligence
`observe_reference.py`, `build_reference_analysis.py`, `enrich_reference_semantics.py`.

Factual observation stays separate from semantic interpretation. Public references default to `creative_dna_only`; literal performance transfer requires licensed/owned rights.

### Creator identity and rights
`build_identity_pack.py`, `prepare_creator_assets.py`, CreatorIdentityPack schema, and the revocation registry.

Canonical identity remains provider-neutral. Provider-specific identity handles are secondary bindings.

### Creative generation/ranking
`generate_creative_specs.py` and `rank_creative_specs.py`.

Campaigns expand creator × hook × CTA × location × outfit. Ranking uses observable structure, cost, optional measured history and shortlist diversity; it is not presented as a virality prediction.

### Product truth
- `ugc-studio/capture/`: Playwright real app/UI capture
- `ugc-studio/assembly/`: Remotion + FFmpeg final assembly

Exact app UI should be captured, not regenerated by a video model.

### QA + learning
`qa_video.py`, `enrich_video_qa.py`, `benchmark_metrics.py`, `retry_policy.py`.

Primary metric: **cost per usable approved second**. Measured provider history only replaces static priors after enough comparable samples.

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

Real secrets belong in a local `.env` or Vercel/server environment variables, never GitHub.

## Current external gate

No paid generation has been triggered from this branch.

The user already has fal, OpenRouter and Gemini credentials. The architecture can now compile and compare provider jobs without spending. The first live benchmark still requires:

1. an approved or synthetic creator image that can be represented in the needed hosted/local forms,
2. selection of one 4–5 second `creator_generated` shot,
3. explicit small spend approval for the chosen provider jobs.

Current 4-second planning figures:

```text
OpenRouter Seedance 2.0 Fast  ~$0.1614  current caller preview
Google Veo 3.1 Lite            $0.20    official formula
fal Wan 3.0                     $0.40    configured provider formula
Gemini Omni output             ~$0.40    output estimate only; input tokens extra
```

Do not select production routing from this price order alone. Use the same QA profile and benchmark pass rate/usable seconds.

## Remaining high-value work

1. First small credentialed fal/OpenRouter/Google benchmark with explicit spend approval.
2. Automatically persist QA result linkage onto artifact records after each run.
3. Audio-aware lip-sync QA.
4. Ground-truth app/UI correctness QA.
5. Background-music ducking.
6. Maestro mobile capture.
7. Self-host Wan worker/benchmark.
8. Published social/ad performance ingestion.
9. Optional Higgsfield Soul binding importer.
10. Full schema enforcement on every remaining untyped ingestion boundary.

## Merge policy

Keep PR #5 draft until fixture capture + assembly are verified end-to-end and at least one provider-ready benchmark path has been inspected. Live spending is not required to merge architecture. Rights/spend gates must remain intact.
