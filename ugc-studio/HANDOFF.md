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
Direct paths exist for Wan I2V, Kling I2V, Kling Motion and Seedance reference-to-video. Live jobs require rights approval, spend approval, runtime `FAL_KEY`, and an explicit live command.

### Higgsfield
First-class hosted provider, not automatically preferred.

- `ugc-studio/providers/higgsfield/client.py`
- `docs/ugc-factory/HIGGSFIELD_API_INTEGRATION.md`

Uses authenticated request-specific `credits` + `usd` preflight, cost caps, async polling, webhooks, output download and provenance. Catalog stays account/model-doc driven rather than hard-coded.

### OpenRouter
First-class hosted aggregator, not automatically preferred.

- `ugc-studio/providers/openrouter/client.py`
- `docs/ugc-factory/OPENROUTER_VIDEO_INTEGRATION.md`

Uses `/api/v1/videos`, live `/api/v1/videos/models` discovery, current pricing/capability snapshots and completed `usage.cost` for actual spend. There is no Higgsfield-style authoritative per-request video quote, so live jobs require an expected-cost + maximum-cost envelope.

### Direct Google / Veo
- `ugc-studio/providers/google-veo/client.py`
- `docs/ugc-factory/GOOGLE_VEO_INTEGRATION.md`

Current official paid rates recorded 2026-09-17:

```text
Veo 3.1 Lite:     $0.05/s 720p | $0.08/s 1080p
Veo 3.1 Fast:     $0.10/s 720p | $0.12/s 1080p | $0.30/s 4k
Veo 3.1 Standard: $0.40/s 720p | $0.40/s 1080p | $0.60/s 4k
```

Google documents charges only for successful Veo generations. V1 supports text-to-video, image-to-video, first/last-frame interpolation and supported reference images.

### Direct Google / Gemini Omni Flash
Google currently recommends `gemini-omni-1.1-flash` as the default video-generation model for new workflows because of coherence, multi-input reasoning, character consistency, factual accuracy and conversational editing. It remains a separate lane from cheaper Veo Lite.

- `ugc-studio/providers/google-omni/client.py`
- `docs/ugc-factory/GOOGLE_OMNI_INTEGRATION.md`

Current benchmark economics:

```text
Veo 3.1 Lite 720p -> ~$0.05/s
Gemini Omni 720p  -> ~$0.10/s effective video output + separately billed input tokens
```

Omni accepts text/image/video references, 9:16 output and native audio. V1 deliberately benchmarks only 720p. The adapter never fetches arbitrary remote media; it accepts inline bytes or Gemini Files media.

## Comparable first-benchmark compiler

`.archon/scripts/ugc/build_provider_benchmark_jobs.py`

This closes the gap between provider adapters and an actual apples-to-apples test. It takes one **rights-approved `creator_generated` CreativeSpec shot** and one creator asset manifest and compiles comparable, spend-disabled jobs for:

```text
fal Wan 3.0 I2V
OpenRouter Seedance 2.0 Fast
Google Veo 3.1 Lite
Google Gemini Omni Flash
```

The first benchmark contract is intentionally:

```text
same creator identity image
same CreativeSpec intent/dialogue
720p
9:16
native audio
common 4 / 6 / 8 second target
approved_for_spend = false
```

Motion-transfer is rejected from this first compiler because provider motion/reference semantics are not equivalent enough to call the results comparable.

Asset behavior is fail-closed:

- approved hosted HTTPS image -> fal/OpenRouter jobs
- approved local/base64 image -> direct Google jobs
- arbitrary creator URLs are not downloaded
- local creator media is not silently uploaded

If both hosted and local/base64 representations exist, all four jobs are emitted. The bundle also contains an offline typed cost comparison.

Run:

```bash
python .archon/scripts/ugc/build_provider_benchmark_jobs.py \
  ./creative-spec.json \
  --shot shot-1 \
  --assets ./creator-assets.json \
  --outdir ./ugc-benchmark/shot-1
```

Outputs include `benchmark-manifest.json`, `provider-comparison.json`, and one JSON job per available provider.

Full runbook: `docs/ugc-factory/FIRST_PROVIDER_BENCHMARK.md`.

## Cross-provider no-spend comparison

`.archon/scripts/ugc/compare_provider_preflight.py`

Cost evidence remains typed:

```text
Higgsfield  -> provider-authenticated request quote
OpenRouter  -> current catalog preview + completed usage.cost
Google Veo  -> dated official per-second formula
Google Omni -> approximate effective 720p output rate; input tokens separate
fal         -> dated configured provider formula
self-host   -> future measured compute economics
```

`cost_only_order` is a benchmark-priority aid, not a provider recommendation.

## Existing core factory

### Reference intelligence
`observe_reference.py`, `build_reference_analysis.py`, `enrich_reference_semantics.py`.

Factual observation stays separate from semantic interpretation. Public references default to `creative_dna_only`; literal performance transfer requires licensed/owned rights.

### Creator identity and rights
`build_identity_pack.py`, `prepare_creator_assets.py`, and the CreatorIdentityPack schema.

The canonical creator record is provider-neutral. Provider-specific identity handles remain secondary bindings.

### Creative generation/ranking
`generate_creative_specs.py` and `rank_creative_specs.py`.

Campaigns expand creator × hook × CTA × location × outfit. Ranking uses observable structure, cost, optional measured history and shortlist diversity; it is not presented as a virality prediction.

### Product truth
- `ugc-studio/capture/`: Playwright real app/UI capture
- `ugc-studio/assembly/`: Remotion + FFmpeg final assembly

Generative models should not recreate exact app UI by default.

### QA + learning
`qa_video.py`, `enrich_video_qa.py`, `benchmark_metrics.py`, `retry_policy.py`.

Failed paid generations count as spend with zero usable seconds. Measured provider quality replaces static priors only after enough samples.

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

Real secrets stay in a local `.env` or Vercel/server environment variables, never GitHub.

## No paid generation has been triggered from this branch

Every provider path remains dry-run/spend-gated by default.

## First benchmark frontier

For a 4-second 720p creator shot, current planning figures are approximately:

```text
OpenRouter Seedance 2.0 Fast  $0.1614   caller preview/current list price
Google Veo 3.1 Lite           $0.20     official formula
fal Wan 3.0                    $0.40     configured provider formula
Gemini Omni output             $0.40     approximate output only; input tokens extra
```

Do not pick a production provider from this ordering alone. Run the same QA profile and record pass rate, identity consistency, failures and usable seconds.

The user already has fal, OpenRouter and Gemini credentials. Higgsfield credentials have not been confirmed. No live benchmark should be run until there is an approved/synthetic creator asset and an explicit spend envelope.

## Remaining high-value work

1. First small credentialed fal/OpenRouter/Google benchmark with an approved or synthetic creator asset and explicit spend approval.
2. Automatically persist QA + provider actual-cost data into the benchmark ledger from completed runs.
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
