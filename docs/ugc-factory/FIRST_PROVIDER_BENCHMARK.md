# First Cross-Provider UGC Benchmark

Last updated: 2026-09-17

This runbook creates an apples-to-apples **creator image-to-video** benchmark across the provider lanes currently available to UGC Studio. It is intentionally narrow: one approved creator image, one CreativeSpec creator shot, 720p vertical output, native audio, and a common duration target.

No step in the compilation/preflight phase authorizes spend.

## Why the first benchmark is narrow

We are comparing generation quality and economics, not provider logos. Motion-control/reference-video behavior differs too much across Wan/Kling/Seedance/Higgsfield/Google to treat those jobs as equivalent. V1 therefore benchmarks only:

```text
same approved creator identity image
same CreativeSpec shot
same dialogue / creative intent
same 9:16 orientation
same 720p target
same native-audio profile
same 4 / 6 / 8 second duration bucket
```

Provider-specific prompt wording may differ only to accommodate documented model behavior, such as Gemini Omni's `single continuous shot / no scene cuts` instruction.

## Current benchmark set

```text
fal              -> Wan 3.0 I2V
OpenRouter       -> Seedance 2.0 Fast
Google direct    -> Veo 3.1 Lite
Google direct    -> Gemini Omni Flash
Higgsfield       -> add later when API credentials + exact account model endpoint are available
```

The initial price evidence is not equally authoritative:

```text
fal Wan         -> dated configured provider formula
OpenRouter      -> dated caller preview; strengthen with live catalog; final usage.cost is actual
Veo Lite        -> dated official $/second formula
Gemini Omni     -> approximate effective 720p video-output rate; input tokens extra
```

## 1. Prepare creator rights/assets

Start from an approved CreatorIdentityPack and derive request-specific assets using `prepare_creator_assets.py`.

Hosted providers (fal/OpenRouter) need an approved HTTPS creator-image URL. Direct Google jobs are built from local/base64 image bytes and never fetch an arbitrary remote creator URL.

For all four providers to be emitted from one benchmark bundle, the assets manifest can contain both forms:

```json
{
  "rights_approved": true,
  "rights_evidence": "agreement:creator-123",
  "creator_image_id": "front-1",
  "creator_image_url": "https://approved-storage.example/creator.jpg",
  "creator_image_local_path": "./creator.jpg"
}
```

A local `creator_image_uri` from `prepare_creator_assets.py` also works for Google when that file is accessible relative to the assets JSON.

Do not put private creator assets into Git.

## 2. Build comparable jobs

```bash
python .archon/scripts/ugc/build_provider_benchmark_jobs.py \
  ./creative-spec.json \
  --shot shot-1 \
  --assets ./creator-assets.json \
  --outdir ./ugc-benchmark/shot-1
```

The command writes:

```text
benchmark-manifest.json
provider-comparison.json
fal-wan.job.json                     (if hosted URL available)
openrouter-seedance-fast.job.json    (if hosted URL available)
google-veo-lite.job.json             (if local/base64 bytes available)
google-omni.job.json                 (if local/base64 bytes available)
```

Every generated job has:

```text
rights_approved = true
approved_for_spend = false
```

The compiler cannot submit a render.

## 3. Inspect offline economics

`provider-comparison.json` is generated automatically. You can also rerun:

```bash
python .archon/scripts/ugc/compare_provider_preflight.py \
  ./ugc-benchmark/shot-1/*.job.json \
  --out ./ugc-benchmark/shot-1/provider-comparison.json
```

The cost-only order is **not** a provider recommendation. A cheap failed generation has zero usable seconds and can be more expensive than a higher-list-price model that passes first try.

## 4. Strengthen read-only preflight where supported

With local environment credentials loaded:

```bash
python .archon/scripts/ugc/compare_provider_preflight.py \
  ./ugc-benchmark/shot-1/*.job.json \
  --network \
  --out ./ugc-benchmark/shot-1/provider-comparison.network.json
```

`--network` performs only authenticated read/estimate calls. It never submits generation.

This can strengthen OpenRouter catalog evidence and Higgsfield quotes when those providers are present.

## 5. Human spend approval boundary

Do not bulk-enable the bundle.

Select one provider job at a time, inspect its prompt/input and current cost evidence, then deliberately change only that selected job's:

```json
"approved_for_spend": true
```

Keep or tighten `max_provider_cost_usd` where the adapter supports it.

The provider runner still requires its own explicit live flag, so changing the JSON alone does not submit anything.

## 6. Run one provider at a time

Examples:

### fal

```bash
node --env-file=.env ugc-studio/providers/fal/render.mjs \
  --job ./ugc-benchmark/shot-1/fal-wan.job.json \
  --outdir ./ugc-benchmark/shot-1/fal-output \
  --live
```

### OpenRouter

```bash
python ugc-studio/providers/openrouter/client.py \
  --job ./ugc-benchmark/shot-1/openrouter-seedance-fast.job.json \
  --outdir ./ugc-benchmark/shot-1/openrouter-output \
  --live
```

### Google Veo

```bash
python ugc-studio/providers/google-veo/client.py \
  --job ./ugc-benchmark/shot-1/google-veo-lite.job.json \
  --outdir ./ugc-benchmark/shot-1/google-veo-output \
  --live
```

### Gemini Omni

```bash
python ugc-studio/providers/google-omni/client.py \
  --job ./ugc-benchmark/shot-1/google-omni.job.json \
  --outdir ./ugc-benchmark/shot-1/google-omni-output \
  --live
```

## 7. Apply exactly the same QA profile

For every attempt, run deterministic QA and visual creator QA using the same thresholds/reference identity.

Record at minimum:

- generation success/failure
- provider/model
- attempt number
- estimated/preflight cost and evidence type
- provider-reported/derived actual cost when available
- identity consistency
- anatomy/hands/face defects
- dialogue/audio usefulness
- structural QA
- human usable/not-usable decision
- usable seconds
- failure codes

Do not silently discard failed paid attempts. Failed spend counts toward the provider's economics with **zero usable seconds**.

## 8. Decide from cost per usable approved second

After several equivalent attempts, compare:

```text
raw cost
pass rate
cost per successful render
usable seconds
cost per usable approved second
identity consistency
first-pass approval rate
```

Only after enough comparable samples should benchmark history influence automatic routing. The existing router intentionally waits for a minimum sample threshold before measured data overrides static priors.

## Current expected 4-second price previews

These are dated planning figures, not final provider recommendations:

```text
OpenRouter Seedance 2.0 Fast  ~ $0.1614  (current caller preview)
Google Veo 3.1 Lite           ~ $0.20    (official formula)
fal Wan 3.0 720p              ~ $0.40    (configured provider formula)
Gemini Omni 720p output       ~ $0.40    (approx output only; input tokens extra)
```

This ordering can change as provider prices and model quality change. The benchmark exists specifically so routing does not rely on list price alone.
