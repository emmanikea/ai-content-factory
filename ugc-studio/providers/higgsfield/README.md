# Higgsfield Provider Adapter

This adapter makes Higgsfield a first-class hosted provider without making it the default route.

## Why the adapter is model-catalog agnostic

Higgsfield documents a stable shared lifecycle for authentication, estimates, async requests,
polling, cancellation, webhooks, and output retention. Its model catalog and model-specific
schemas can differ by account and can change independently. The adapter therefore accepts a
model endpoint path plus its model-specific JSON input instead of hard-coding the full catalog.

Sources checked 2026-09-17:
- https://docs.higgsfield.ai/docs
- https://docs.higgsfield.ai/docs/llms.txt
- https://docs.higgsfield.ai/docs/concepts/billing-and-retention
- https://docs.higgsfield.ai/docs/concepts/requests
- https://docs.higgsfield.ai/docs/concepts/polling
- https://docs.higgsfield.ai/docs/how-to/webhooks
- https://docs.higgsfield.ai/docs/openapi.json

## Credentials

Set one of these server-side:

```bash
HF_CREDENTIALS=<api_key_id>:<api_key_secret>
# HF_KEY is accepted as a compatibility alias.
```

Never expose credentials in browser code.

## Job contract

```json
{
  "version": "1.0",
  "provider": "higgsfield",
  "endpoint": "veo3.1/image-to-video",
  "input": {
    "prompt": "Subtle natural creator movement, handheld UGC feel.",
    "image_url": "https://example.com/approved-creator.jpg",
    "duration": "4",
    "resolution": "720",
    "aspect_ratio": "9:16",
    "generate_audio": false
  },
  "rights_approved": true,
  "approved_for_spend": false,
  "max_provider_cost_usd": 1.0
}
```

The example endpoint is present in the supplementary OpenAPI snapshot checked on 2026-09-17.
For production, use the model-specific documentation exposed for the account as the schema source.

## Commands

Dry-run, no credentials and no network call:

```bash
python ugc-studio/providers/higgsfield/client.py --job job.json
```

Authenticated cost estimate only, no generation:

```bash
python ugc-studio/providers/higgsfield/client.py --job job.json --estimate
```

Live generation:

```bash
python ugc-studio/providers/higgsfield/client.py \
  --job job.json \
  --live \
  --outdir ./higgsfield-output
```

Live mode always:
1. obtains the authenticated Higgsfield estimate;
2. enforces `max_provider_cost_usd` when supplied;
3. requires `rights_approved=true`;
4. requires `approved_for_spend=true`;
5. submits exactly once;
6. polls with Higgsfield's recommended backoff;
7. downloads completed media when an output directory is supplied;
8. stores provider provenance including the authenticated estimate.

Use `--no-poll` for queue/worker architectures. Store the returned `request_id` immediately.

## Webhooks

A job may include:

```json
{
  "webhook_url": "https://your-domain.example/api/webhooks/higgsfield"
}
```

Higgsfield requires a public HTTPS endpoint. Production webhook handlers must be idempotent
because duplicate terminal deliveries are possible. Deduplicate by request ID + terminal status.

## Routing policy

Higgsfield is available as a provider, but automatic routing should not prefer it merely because
the platform is integrated. First collect equivalent benchmark attempts and compare:

- authenticated provider cost;
- pass rate;
- usable seconds;
- identity consistency;
- anatomy/visual QA;
- audio/lip-sync when relevant;
- cost per usable approved second.

The factory keeps direct fal/OpenRouter/Google/self-host lanes independent.
