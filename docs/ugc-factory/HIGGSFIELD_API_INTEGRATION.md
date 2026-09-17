# Higgsfield API Integration Decision

Last verified: 2026-09-17

## Decision

Higgsfield is now treated as a **first-class hosted provider**, not as a platform-only fallback.

This does **not** make Higgsfield the default renderer. Provider choice remains evidence-driven.

```text
CreativeSpec
    ↓
rights + asset resolution
    ↓
provider candidates
    ├── fal
    ├── OpenRouter
    ├── Google
    ├── Higgsfield
    └── self-host
    ↓
provider-specific authenticated estimate where available
    ↓
explicit spend gate
    ↓
render
    ↓
QA + benchmark ledger
    ↓
cost per usable approved second
```

## What changed

Earlier architecture treated Higgsfield runtime mostly as proprietary-only / benchmark / fallback.
The current API supports a normal production lifecycle:

- server-side API credentials
- one authenticated asynchronous API
- per-request cost estimation before generation
- request IDs
- status URLs and polling
- cancellation
- webhooks
- output download
- official Python and TypeScript SDKs

That is enough to integrate it like any other hosted generation provider.

## Authoritative pricing behavior

Do not hard-code a permanent USD-per-credit conversion.

Higgsfield exposes:

```text
POST /estimate/{model_endpoint}
```

using the same input parameters as generation. The authenticated response contains `credits`
and `usd`. Higgsfield says that authenticated estimate is authoritative for the account.

Therefore:
- estimate before every Higgsfield live submission;
- preserve the estimate in job provenance;
- compare the estimate against a job/campaign cost cap;
- record actual observed billing later if the provider exposes post-run billable usage;
- never overwrite historical estimates with newer prices.

## Request lifecycle

Terminal states:
- `completed`
- `failed`
- `nsfw`
- `canceled`

Non-terminal states:
- `queued`
- `in_progress`

Polling starts at roughly two seconds and backs off toward ten seconds. Production should prefer
webhooks with polling as recovery.

Failed/NSFW requests are documented as uncharged/refunded. Successfully canceled queued requests
are refunded.

## Retention

Higgsfield guarantees generated output availability for at least seven days, not permanent storage.
Completed media must be copied to our own durable object storage for long-term use.

## Model discovery

Higgsfield explicitly says:
1. discover models in the Console;
2. use model-specific documentation for endpoint and schema;
3. treat the shared OpenAPI file as supplementary rather than the authoritative catalog;
4. do not infer account access from documentation alone.

For that reason the provider adapter does not embed a permanent catalog. A job carries:
- `endpoint`
- provider-specific `input`

The model registry records Higgsfield as an available provider, while account/model discovery and
benchmark results determine whether it becomes an eligible automatic route.

## Identity

Higgsfield's supplementary API reference includes Soul endpoints and persistent character-reference
parameters such as `custom_reference_id`.

That fits the existing portable identity design:

```text
CreatorIdentityPack
    ├── canonical source images
    ├── voice/performance references
    ├── rights snapshot
    └── provider_bindings
         └── higgsfield
              └── Soul/custom reference identifier
```

The Higgsfield identifier is a non-portable provider binding, never the canonical identity record.

## Safety/spend boundary

`ugc-studio/providers/higgsfield/client.py` is dry-run by default.

An actual generation requires:
- server-side Higgsfield credentials;
- `rights_approved=true`;
- `approved_for_spend=true`;
- `--live`.

The adapter also retrieves the authenticated estimate before it submits the request.

## Next benchmark

When Higgsfield credentials and an approved creator asset are available:

1. use the same approved 4–5 second creator hook;
2. compile/direct the closest equivalent job on fal and Higgsfield;
3. estimate both before spend;
4. run equivalent settings where possible;
5. QA both;
6. record every attempt, including failures;
7. compare cost per usable approved second.

Do not promote Higgsfield, fal, OpenRouter, or Google based on list price alone.

## Sources

- https://docs.higgsfield.ai/docs
- https://docs.higgsfield.ai/docs/llms.txt
- https://docs.higgsfield.ai/docs/concepts/billing-and-retention
- https://docs.higgsfield.ai/docs/concepts/requests
- https://docs.higgsfield.ai/docs/concepts/polling
- https://docs.higgsfield.ai/docs/how-to/webhooks
- https://docs.higgsfield.ai/docs/how-to/sdk
- https://docs.higgsfield.ai/docs/openapi.json
