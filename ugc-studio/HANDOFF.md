# UGC Studio Handoff

Last updated: 2026-09-17  
Branch: `feat/ugc-studio-v1`  
PR: #5

## Product direction

Build a provider-independent UGC/Reels factory. We own creative intelligence, creator identity/rights, deterministic app capture, assembly, QA, and learning. Generation providers compete underneath that layer.

```text
Reference video -> ReferenceAnalysis
Creator assets  -> CreatorIdentityPack
Campaign brief  -> CreativeSpec variants
                        ↓
                 concept ranking
                        ↓
                 provider candidates
           ┌────────┬───────┬────────┬────────────┐
           fal   OpenRouter  Google  Higgsfield  self-host
                        ↓
                  explicit spend gate
                        ↓
                      render
                        ↓
                  deterministic + visual QA
                        ↓
                    final assembly
                        ↓
                    benchmark ledger
                        ↓
              cost per usable approved second
```

## Important provider policy change

Higgsfield is no longer modeled as a website/CLI-only fallback. Its current API has a standard server-side lifecycle: credentials, authenticated request estimates, async submission, request IDs, polling, cancellation, webhooks, and downloadable outputs.

It is therefore a **first-class hosted provider**.

It is **not automatically preferred**. Its own documentation says model availability/schema should be discovered from the account Console/model-specific docs, and the shared OpenAPI file is supplementary. The router should only promote Higgsfield after equivalent benchmark evidence.

See:
- `docs/ugc-factory/HIGGSFIELD_API_INTEGRATION.md`
- `ugc-studio/providers/higgsfield/README.md`
- `ugc-studio/providers/higgsfield/client.py`

## Higgsfield adapter

Credentials:

```text
HF_CREDENTIALS=<api_key_id>:<api_key_secret>
```

`HF_KEY` is accepted as an alias.

Dry-run:
```bash
python ugc-studio/providers/higgsfield/client.py --job job.json
```

Authenticated estimate only:
```bash
python ugc-studio/providers/higgsfield/client.py --job job.json --estimate
```

Live:
```bash
python ugc-studio/providers/higgsfield/client.py --job job.json --live --outdir ./higgsfield-output
```

Live generation requires:
- `rights_approved=true`
- `approved_for_spend=true`
- credentials
- `--live`

Before submission the adapter calls Higgsfield's authenticated estimate endpoint, preserves `credits` + `usd`, and enforces `max_provider_cost_usd` when present. Completed media is downloaded because provider retention is not permanent.

Webhook jobs may include `webhook_url`. Production handlers must deduplicate terminal events by request ID + terminal status.

## Existing factory pieces

### Reference intelligence
- `.archon/scripts/ugc/observe_reference.py`
- `.archon/scripts/ugc/build_reference_analysis.py`
- `.archon/scripts/ugc/enrich_reference_semantics.py`

Deterministic video facts stay separate from semantic interpretation. Public references default to `creative_dna_only`; literal performance transfer requires licensed/owned rights.

### Creator identity and rights
- `.archon/scripts/ugc/build_identity_pack.py`
- `.archon/scripts/ugc/prepare_creator_assets.py`
- `ugc-studio/schemas/creator-identity-pack.schema.json`

Canonical identity stays provider-neutral. Provider IDs such as a future Higgsfield Soul/custom reference binding are secondary/non-portable bindings.

### CreativeSpec generation and ranking
- `.archon/scripts/ugc/generate_creative_specs.py`
- `.archon/scripts/ugc/rank_creative_specs.py`

Campaigns expand creator × hook × CTA × location × outfit up to a cap. Ranking uses observable structure, direct-model cost, optional measured history, and shortlist diversity. It is not a virality prediction.

### fal path
- `.archon/scripts/ugc/build_fal_job.py`
- `ugc-studio/providers/fal/`

Current direct routes include Wan I2V, Kling I2V, Kling Motion, and Seedance reference-to-video. fal remains an independent provider, not a Higgsfield dependency.

### App capture + assembly
- `ugc-studio/capture/` -> Playwright real UI capture
- `ugc-studio/assembly/` -> Remotion + FFmpeg final assembly

Real app UI should be captured, not hallucinated by a video model.

### QA + learning
- `.archon/scripts/ugc/qa_video.py`
- `.archon/scripts/ugc/enrich_video_qa.py`
- `.archon/scripts/ugc/benchmark_metrics.py`
- `.archon/scripts/ugc/retry_policy.py`

Primary economic metric: **cost per usable approved second**. Failed paid generations count as spend with zero usable seconds. Measured routing only overrides priors after enough comparable attempts.

## Credential convention

Root `.env.example` documents local/server variable names:

```text
OPENROUTER_API_KEY
GEMINI_API_KEY
FAL_KEY
HF_CREDENTIALS
NVIDIA_API_KEY
OPENAI_API_KEY
```

Real secrets must never be committed. Vercel environment variables are the deployed equivalent of a local `.env`.

## No paid generation has been triggered from this branch

Provider integrations remain dry-run/spend-gated by default.

## Next benchmark

Use one approved/synthetic creator reference and one 4–5 second hook.

1. Produce equivalent fal and Higgsfield jobs.
2. Fetch both preflight estimates where available.
3. Inspect prompts/inputs.
4. Explicitly approve a small spend cap.
5. Render equivalent versions.
6. Run deterministic + visual QA.
7. Record every attempt, failure, and cost.
8. Compare cost per usable approved second.
9. Only then promote/demote providers in automatic routing.

OpenRouter and direct Google/Veo adapters are the next provider-infrastructure slices because those credentials are already available.

## Remaining high-value work

1. OpenRouter video provider adapter.
2. Direct Google/Veo provider adapter.
3. Cross-provider estimate normalization and automatic candidate comparison.
4. Creator-rights revocation propagation.
5. Audio-aware lip-sync QA.
6. Ground-truth app/UI correctness QA.
7. Background-music ducking.
8. Maestro mobile capture.
9. Self-host Wan worker/benchmark.
10. Published social/ad performance ingestion.

## Merge policy

Keep PR #5 draft until fixture capture + assembly are verified end-to-end and at least one provider-ready benchmark path has been inspected. Live spending is not required to merge architecture. Rights and spend gates must remain intact.
