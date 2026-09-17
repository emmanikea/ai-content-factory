# Benchmark Ledger Recording

The benchmark ledger is provider-neutral. Do not manually rewrite OpenRouter/Google/fal/Higgsfield results into a fal-shaped record.

## Successful generation + QA

After a provider run writes `provenance.json` and QA writes a `QAResult`:

```bash
python .archon/scripts/ugc/benchmark_metrics.py record \
  --job ./ugc-benchmark/shot-1/openrouter-seedance-fast.job.json \
  --qa ./ugc-benchmark/shot-1/openrouter-output/qa.json \
  --provider-provenance ./ugc-benchmark/shot-1/openrouter-output/provenance.json \
  --attempt 1
```

The recorder normalizes provider/model identity and uses the strongest cost evidence available:

```text
OpenRouter actual_cost_usd / terminal usage.cost -> provider-reported actual
Google Veo derived_billable_cost_usd             -> post-success official billing formula
fal provider actual when available               -> actual; otherwise dated estimate
Gemini Omni                                       -> output-cost estimate until usage/billing reconciliation exists
```

An explicit `--actual-cost` is still available as a manual override when a provider invoice/dashboard gives a stronger number than the saved provenance.

## Generation failed before QA

A paid failure must not disappear because no video existed to inspect:

```bash
python .archon/scripts/ugc/benchmark_metrics.py record \
  --job ./ugc-benchmark/shot-1/provider.job.json \
  --generation-failure provider_failed \
  --provider-provenance ./provider-output/provenance.json \
  --attempt 1
```

If the provider did not produce provenance but the charged amount is known:

```bash
python .archon/scripts/ugc/benchmark_metrics.py record \
  --job ./provider.job.json \
  --generation-failure provider_failed \
  --actual-cost 0.42
```

The record gets:

```text
qa_status = fail
usable = false
usable_seconds = 0
cost_used_usd = actual cost when known, otherwise the preserved estimate
```

## Summarize

```bash
python .archon/scripts/ugc/benchmark_metrics.py summarize \
  --out ./ugc-benchmark/model-summary.json
```

Summary rows include:

- attempts
- passes / failures / needs-review
- generation failures before QA
- pass rate
- total spend
- usable seconds
- cost per usable approved second
- average QA score
- number of attempts with actual-cost evidence

The router should only consume these measurements after the configured minimum sample threshold and when the QA criteria are comparable across the tested providers.
