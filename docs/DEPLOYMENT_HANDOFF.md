# Deployment handoff

This document captures the minimum manual setup required to turn the V2 Studio into a deployed, persistent generation environment.

## Current status

- Neon project created: `ai-content-factory`
- Neon project ID: `green-wildflower-39475505`
- Region: AWS us-east-2
- PostgreSQL: 17
- Compute: 0.25 CU with immediate suspend
- V2 schema has been successfully dry-run on a temporary Neon migration branch.
- The dry run found and fixed two portability issues before production:
  - reserved table name `references` was replaced with `character_references`
  - `updated_at` is now maintained by application writes rather than a PL/pgSQL trigger
- R2/S3-compatible storage support is implemented in the Studio.
- Vercel account/team is connected, but an `ai-content-factory` Vercel project has not been created yet.

## Manual Vercel setup

Import GitHub repository:

`emmanikea/ai-content-factory`

Use:

- Framework: Next.js
- Root directory: `apps/studio`
- Production branch: keep `main` for eventual production; use `feat/content-factory-v2` for the current preview/integration deployment until the PR stack is approved.

Do not put secrets in Git or in this document.

## Required deployment variables

### Database

`DATABASE_URL`

Use the connection string from the Neon `ai-content-factory` project. The application remains portable to any Postgres-compatible host through this single variable.

Also set:

```text
DATABASE_POOL_SIZE=5
STUDIO_ALLOW_EPHEMERAL_STORE=false
```

### Cloudflare R2

Create or choose one R2 bucket and an R2 API token with object read/write access for that bucket.

Set:

```text
OBJECT_STORAGE_BUCKET=<bucket name>
OBJECT_STORAGE_ENDPOINT=https://<cloudflare-account-id>.r2.cloudflarestorage.com
OBJECT_STORAGE_REGION=auto
OBJECT_STORAGE_ACCESS_KEY_ID=<R2 access key id>
OBJECT_STORAGE_SECRET_ACCESS_KEY=<R2 secret access key>
OBJECT_STORAGE_FORCE_PATH_STYLE=false
OBJECT_STORAGE_PREFIX=ai-content-factory
```

`OBJECT_STORAGE_PUBLIC_BASE_URL` is optional. Leave it unset initially so private objects are exposed to providers through short-lived signed URLs.

### OpenRouter

```text
OPENROUTER_API_KEY=<secret>
OPENROUTER_VIDEO_MODEL=<chosen default model>
OPENROUTER_SITE_URL=<deployed Studio URL>
OPENROUTER_APP_NAME=AI Content Factory Studio
```

Keep the initial provider path OpenRouter-first. Do not provision RunPod/ComfyUI solely to launch V1.

### Studio access

Set unique credentials:

```text
STUDIO_BASIC_AUTH_USER=<internal username>
STUDIO_BASIC_AUTH_PASSWORD=<strong secret>
STUDIO_ALLOW_INSECURE_DEV=false
```

For legacy Archon workers, configure matching credentials through:

```text
CONTENT_STUDIO_URL=<deployed Studio URL>
CONTENT_STUDIO_BASIC_AUTH_USER=<same or dedicated internal username>
CONTENT_STUDIO_BASIC_AUTH_PASSWORD=<matching secret>
```

### Spend control

Start with a conservative per-generation ceiling, then revise from benchmark data:

```text
STUDIO_MAX_ESTIMATED_COST_USD=5
```

## First end-to-end verification

After environment variables are configured:

1. Open the Studio.
2. Create a project.
3. Create a synthetic character.
4. Upload one or more character reference images.
5. Verify the files persist in R2 and references persist in Neon.
6. Submit one OpenRouter generation.
7. Confirm the factory job exists before provider submission.
8. Poll until completion.
9. Confirm the resulting media plays through the Studio content route.
10. Confirm estimated cost, provider, model, status, prompt and reference IDs remain recorded in Neon.
11. Retry the same operation with an idempotency key and verify it does not create a second paid generation.

## Next milestone after smoke test

Run the same approved Camber/product-pan input through:

- existing Higgsfield path
- V2 OpenRouter path

Record generation success, usable clip rate, retries, latency, visual quality, raw cost and cost per usable clip.

Only after real usage data should RunPod + ComfyUI + self-hosted H3 be provisioned.