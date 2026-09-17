# Cross-Provider Preflight Comparison

Last updated: 2026-09-17

## Purpose

UGC Studio now has multiple provider lanes. Their cost evidence is not equally precise, so this tool compares them without pretending they are.

```text
fal        -> dated configured provider formula
Higgsfield -> authenticated request-specific quote
OpenRouter -> current catalog preview + post-run usage.cost
Google Veo -> dated official $/second formula
```

The comparison is a **no-spend decision surface**. It never submits video generation.

## Command

Offline comparison:

```bash
python .archon/scripts/ugc/compare_provider_preflight.py \
  ./fal-job.json \
  ./openrouter-job.json \
  ./google-job.json \
  ./higgsfield-job.json \
  --out ./provider-comparison.json
```

Offline mode performs no authenticated network calls. Costs that require authenticated provider evidence remain unknown.

Authenticated read/estimate mode:

```bash
python .archon/scripts/ugc/compare_provider_preflight.py \
  ./fal-job.json \
  ./openrouter-job.json \
  ./google-job.json \
  ./higgsfield-job.json \
  --network \
  --out ./provider-comparison.json
```

`--network` may:
- request a Higgsfield authenticated estimate;
- fetch OpenRouter's current video model/catalog metadata.

It still **never submits generation**.

## Output

Each provider row preserves:
- provider/model
- preflight cost when known
- evidence type
- evidence precision
- whether a network call can strengthen the evidence
- expected post-run actual-cost source
- provider-specific detail/provenance

The schema is:

`ugc-studio/schemas/provider-preflight-comparison.schema.json`

The output includes a `cost_only_order`, but that is deliberately not called a ranking or provider recommendation.

Example interpretation:

```text
$0.20  Google Veo Lite  -> official dated formula
$0.25  OpenRouter       -> caller preview based on current catalog
$0.40  fal Wan          -> configured provider formula
?      Higgsfield       -> needs authenticated request quote
```

Those numbers are useful for deciding what to benchmark first. They are not sufficient to decide the production winner.

## Why evidence types matter

A provider quote and a price derived from a catalog are different claims.

### Higgsfield
The API exposes an authenticated estimate for the exact request. This is the strongest pre-generation evidence among the current hosted lanes.

### OpenRouter
The video model catalog exposes current pricing SKUs/capabilities. The completed job exposes `usage.cost`, which is strong post-run evidence. The current public video API does not document a Higgsfield-style exact pre-request quote.

### Google Veo
Google publishes a per-second price schedule. A request estimate is deterministic from model/resolution/duration, but the schedule is still a dated external price that should be preserved with its source/date.

### fal
Current job compilation uses our dated provider pricing metadata. Keep source/date with every benchmark and reconcile actual billing when the provider exposes it.

## What chooses the production route

Not preflight price alone.

After real benchmark attempts, combine:
- actual/derived paid cost
- pass rate
- identity consistency
- anatomy/artifact QA
- motion/reference adherence
- lip-sync/audio QA where relevant
- usable approved seconds

Primary production metric remains:

**cost per usable approved second**

A provider that costs $0.20 per raw attempt but only passes 20% of the time can be more expensive than a $0.40 provider that passes consistently.

## Spend boundary

This comparison tool is safe to run before spend authorization. Generation remains provider-specific and separately requires rights/spend approval.
