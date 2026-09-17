# Higgsfield API Research — Patterns to Reuse Without the Runtime

Last reviewed: 2026-09-17

## Decision

The Higgsfield developer API does **not** change the repository's runtime policy.

Higgsfield remains disabled as an execution provider. We do not need Higgsfield credentials, credits, CLI, MCP, SDK, or API calls for normal UGC Studio operation.

The API documentation is still useful as product/architecture research. It exposes several operational patterns worth reproducing in our own Comfy/direct-model stack.

## What the current API actually is

Higgsfield documents one authenticated asynchronous API for image/video generation. A model request returns a request identifier plus status/cancel links; clients then poll or receive a webhook when work completes.

Source: https://docs.higgsfield.ai/docs

This means Higgsfield is a managed orchestration/provider layer, not evidence that its underlying model orchestration is available to us without Higgsfield billing.

## Billing implication

Successful generation requests consume Higgsfield account credits. Cost depends on the selected model and parameters.

Higgsfield also exposes an estimate endpoint that accepts the same model parameters and returns an estimated credit and USD cost before generation.

Source: https://docs.higgsfield.ai/docs/concepts/billing-and-retention

That estimate endpoint is the most useful architectural idea for us. We should have the same UX/contract in UGC Studio even when our route is Comfy/local or a direct hosted API.

## Rate-limit implication

Higgsfield documents concurrency as the primary generation limit. Limits depend on account/subscription/model. Their guidance is to use a worker pool or semaphore, track every accepted request until terminal state, and use backoff + jitter rather than tight-loop retries.

Source: https://docs.higgsfield.ai/docs/concepts/rate-limits

UGC Studio already has worker/queue concepts. We should preserve this provider-neutral pattern for Comfy and direct APIs rather than creating provider-specific polling loops.

## Model documentation/source priority

Higgsfield's own documentation says model-specific API documentation is authoritative for endpoint, request schema, parameters, examples, and production-vs-preview status. Their shared OpenAPI file is supplementary and is not a complete authoritative model catalog.

Source: https://docs.higgsfield.ai/docs/llms.txt

This reinforces the evidence-first approach already used for Comfy:

1. inspect the live/current model or node schema,
2. start from a working official template/example,
3. capture the exact parameters/dependencies,
4. do not infer availability from a generic catalog alone.

## Patterns adopted into UGC Studio

### 1. Preflight quote before spend

Every render plan should be representable as a normalized quote before execution:

```text
CreativeSpec
  -> route candidates
  -> normalized execution quote
       provider/workflow
       model/recipe
       duration
       estimated raw cost
       expected usable cost
       quote source
       whether estimate is authoritative
       budget block state
  -> explicit spend approval when paid
  -> execute
```

Implementation:

- `.archon/scripts/ugc/preflight_quote.py`
- `ugc-studio/schemas/execution-quote.schema.json`

Current quotes use our registry/benchmark data and are explicitly non-authoritative unless a provider or measured GPU estimator later supplies an authoritative quote.

### 2. Provider-neutral async job lifecycle

Execution adapters should normalize provider-specific IDs/states into our own lifecycle rather than leaking each provider's polling semantics throughout the application.

Target states:

```text
planned -> approved -> queued -> running -> succeeded
                                  |-> failed
                                  |-> canceled
```

Each accepted job should preserve:

- internal job id,
- provider/workflow execution id,
- provider/model/workflow version,
- submitted timestamp,
- terminal timestamp,
- cancelability,
- output references,
- error/failure category,
- actual cost when available.

For local Comfy, the Comfy `prompt_id` is the external execution identifier. For direct hosted providers, use their request/job identifier. Do not build separate product semantics around each vendor's status names.

### 3. Bounded concurrency

The factory should use explicit per-executor concurrency controls:

```text
Comfy local GPU -> bounded by measured GPU/VRAM throughput
Fal/API route   -> bounded by provider limits/config
Deterministic   -> bounded separately by CPU/browser capacity
```

Do not make retry loops the concurrency controller.

### 4. Backoff and jitter

Polling/retry behavior belongs in provider adapters. Tight-loop polling is prohibited. Retry policy should distinguish:

- transient transport/provider error,
- concurrency/rate-limit rejection,
- deterministic input/schema failure,
- model/content failure,
- QA failure after successful generation.

Only the first two categories should generally use transport-level backoff.

### 5. Own the output

Higgsfield documents generated files as retained for a limited period and tells developers to copy completed outputs to their own storage.

UGC Studio should follow the same principle for every provider: once an artifact is accepted, copy it into project-owned storage (R2/object storage/local canonical store) and save provenance. Provider URLs are transport, not the asset system of record.

## What we are deliberately *not* adopting

- Higgsfield authentication or API credentials.
- Higgsfield billing/credit accounting as a runtime dependency.
- Higgsfield model aliases as our canonical model identities.
- Higgsfield's provider-specific endpoint shapes in our domain contracts.
- Any assumption that a model shown inside Higgsfield should be accessed through Higgsfield.

## Research use of Higgsfield model pages

Agents may use Higgsfield model-specific docs to learn:

- supported media inputs,
- durations/resolutions/aspect ratios,
- prompt/parameter vocabulary,
- model-specific capability boundaries,
- useful production UX patterns.

Before implementing a route, verify the corresponding direct/open/Comfy source independently. Higgsfield documentation is research evidence, not authorization to invoke Higgsfield.

## Runtime invariant

```text
Higgsfield docs: allowed as research
Higgsfield skills: allowed as research
Higgsfield API/SDK/CLI/MCP execution: disabled
Comfy/local/open workflows: preferred
Direct hosted API: explicit route + spend gate
```
