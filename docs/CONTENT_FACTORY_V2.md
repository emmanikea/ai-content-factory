# AI Content Factory V2

## Purpose

V2 does not replace the original Content Factory. It turns the original product-ad factory into one workflow inside a broader, provider-agnostic media production system.

The original architecture remains valuable:

- cheap exploration before expensive rendering
- worker pools with atomic claiming
- fresh context per unit of work
- human approval before high-cost generation
- validation and retry gates
- idempotent reruns

V2 adds the infrastructure required for AI influencers, consented real-person digital twins, model routing, reusable references, durable jobs, cost accounting and self-hosted generation.

## Target architecture

```text
Studio / Archon / future agents
             |
             v
      Factory API + state
             |
      Generation Router
       /      |       \
OpenRouter  ComfyUI  legacy Higgsfield
             |
        GPU workers
             |
     H3 / LTX / future
```

The generation provider is an implementation detail. Workflows should depend on the factory contract, not directly on OpenRouter, ComfyUI, Higgsfield, RunPod or a model vendor.

## What exists on `feat/content-factory-v2`

### Factory entities

- `characters`: real people, synthetic influencers, brand mascots
- `references`: image, video, audio, performance, location, wardrobe
- `projects`: units of production work
- `generation_jobs`: durable provider-neutral jobs
- `assets`: generated media + provenance
- `quality_reviews`: automated/human QA scores
- `approval_events`: human review decisions
- `cost_events`: estimated and reconciled spend

The canonical Postgres schema is `apps/studio/db/schema.sql`.

### Persistence

`ContentFactoryStore` is the application boundary.

- local development with no `DATABASE_URL`: in-memory store
- `DATABASE_URL`: portable Postgres adapter
- production without `DATABASE_URL`: refused by default rather than silently becoming ephemeral

The application does not depend on Supabase-specific APIs. Supabase, Neon or ordinary Postgres can host the schema.

### Generation lifecycle

`POST /api/generate` now follows a spend-safe order:

1. validate the request, project and character
2. enforce verified consent when a real-person character is selected
3. resolve the provider and query live provider metadata when available
4. enforce the optional estimated-spend cap
5. create the durable factory job first
6. submit to OpenRouter or ComfyUI
7. attach the provider job ID/result to the factory job
8. record provider-submission failures against the factory job

Agents can provide an `idempotencyKey`. Duplicate calls return the existing factory job rather than spending again. The database enforces uniqueness for non-null idempotency keys.

`GET /api/generations/:id` refreshes non-terminal provider jobs and updates factory state. Terminal jobs no longer repeatedly poll the provider.

Generated content is served through `/api/generations/:id/content`; provider credentials or authenticated provider URLs are not exposed to the browser.

### Cost accounting

OpenRouter estimates come from the current `/videos/models` pricing metadata rather than a hard-coded model price table. If a model does not advertise a directly comparable per-video-second SKU, the system records that an estimate is unavailable instead of inventing one.

`STUDIO_MAX_ESTIMATED_COST_USD` can reject a generation before provider submission when a live estimate exceeds the configured per-job cap.

Self-hosted ComfyUI cost should ultimately be reconciled from GPU telemetry rather than guessed from hosted API pricing.

### ComfyUI execution boundary

A deployed Studio does not accept arbitrary client-supplied ComfyUI graphs by default.

- `COMFYUI_WORKFLOW_JSON`: server-owned, tested API-format workflow
- `COMFYUI_BINDINGS_JSON`: server-owned mapping from portable inputs to graph inputs
- `COMFYUI_ALLOW_CLIENT_WORKFLOW_OVERRIDES=false`: default safe setting

The override flag is an explicit local-development escape hatch only. This matters because installed ComfyUI custom nodes can perform much more than image/video generation.

### Internal access control

The Studio is an internal spend-bearing application. Production requires `STUDIO_BASIC_AUTH_USER` and `STUDIO_BASIC_AUTH_PASSWORD` unless the authentication layer is intentionally replaced with a stronger session/SSO mechanism.

Legacy workers use matching `CONTENT_STUDIO_BASIC_AUTH_USER` / `CONTENT_STUDIO_BASIC_AUTH_PASSWORD` values when calling the Studio.

Basic Auth is an interim internal control, not the long-term multi-user permission model.

### Legacy bridge

`.archon/scripts/factory/generation_gateway.py` lets existing Python/Archon workers submit and poll through the Studio API.

The gateway supports deterministic idempotency keys. A migrated product-pan worker should use a stable key derived from its production unit, for example:

```text
product-pan:<product_id>:<concept_id>
```

This is the migration seam. New workflow code should use the gateway rather than learning OpenRouter/ComfyUI directly.

## Consent rule

For a registered `real_person` character:

- consent cannot be treated as `not_required`
- generation is blocked unless `consent_status = verified`
- a reference cannot become consent-verified unless the character itself is verified

Synthetic characters and brand mascots do not use the real-person consent gate.

Raw external reference URLs remain a development convenience. The production digital-twin path should prefer stored reference IDs with durable provenance once object storage is implemented.

## Migration rule

Do not delete the working Higgsfield pipeline while V2 is unproven.

For each migrated workflow:

1. preserve the existing implementation
2. add a V2 path beside it
3. run the same inputs through both
4. measure usable output rate, retries, latency and cost
5. switch the default only when V2 wins or meets a deliberate strategic requirement

## Benchmark harness

The existing Camber catalog and sample outputs should become the regression suite.

Track at minimum:

| Metric | Why it matters |
| --- | --- |
| generation success rate | provider reliability |
| usable clip rate | true production yield |
| average retries | hidden cost/latency |
| identity consistency | digital-twin/influencer quality |
| prompt adherence | creative control |
| motion quality | realism |
| artifact score | hands/faces/products/warping |
| lip-sync score | talking content |
| latency | operator throughput |
| raw generation cost | provider economics |
| cost per usable clip | actual economic KPI |

## Next implementation slices

### Slice A — make persistence operational

- run `db/schema.sql` against a development Postgres instance
- test create/list character, project and generation APIs
- test idempotent submit under concurrent/retried calls
- add migration/version tooling before schema changes become frequent

### Slice B — asset storage

Add one object-storage abstraction for:

- source references
- generated images
- generated video
- thumbnails
- audio
- QA frame samples

The DB stores stable keys and provenance; provider URLs should not become canonical asset identities. Once storage exists, completed provider output should be copied into object storage and playback should prefer the stable asset.

### Slice C — real H3 ComfyUI workflow

Do not fabricate workflow JSON from memory.

- import a current API-format H3 workflow from the installed ComfyUI/model environment
- validate checkpoint/custom-node names
- version the known-good graph under `workflows/comfy/`
- define documented server-owned input bindings
- run smoke tests from the Studio

Then repeat for LTX or another cheap high-throughput model.

### Slice D — migrate one legacy render path

Migrate the product-pan path first because it is simpler than UGC/digital-human generation.

- expose the approved still through object storage
- call `generation_gateway.py` with that reference and a deterministic idempotency key
- persist output asset + cost + validation
- compare against the current Higgsfield product-pan output

Do not migrate `animate_ugc.py` until the product-pan bridge is proven.

### Slice E — character/reference UI

Replace raw project/character IDs in the Generate screen with selectors and add:

- Characters
- References
- Projects
- Jobs
- Library
- Review

For real people, use stored references with consent/provenance metadata rather than arbitrary public URLs.

### Slice F — worker infrastructure

Only after local ComfyUI workflows are proven:

- package the ComfyUI environment
- deploy one rented GPU worker
- measure cold start + inference time
- add queue-driven autoscaling
- add OpenRouter overflow/fallback

### Slice G — automated QA and routing

Use quality and cost history to make routing data-driven:

- cheapest model meeting a quality threshold
- fallback after provider failure
- retry policy by error type
- optional multi-model fan-out for high-value jobs
- model comparison based on cost per usable clip

## Merge gates

Do not merge V2 to `main` simply because the architecture is broader.

Minimum merge gates:

- Studio typechecks/builds
- Postgres schema applies cleanly
- production configuration refuses unauthenticated/ephemeral defaults
- idempotent generation submission is verified
- OpenRouter submit/poll/content smoke test passes
- ComfyUI submit/poll/content smoke test passes with at least one real server-owned workflow
- factory job persistence survives process restart
- verified-consent rule is exercised for a real-person test character
- one legacy Camber render path works end-to-end through the V2 gateway
- old Higgsfield path remains available for rollback/comparison

At that point V2 is an extension of the factory rather than parallel scaffolding.
