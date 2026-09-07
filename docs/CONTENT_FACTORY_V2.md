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

V2 adds the infrastructure required for AI influencers, real-person digital twins, model routing, reusable references, durable jobs, cost accounting, object storage and self-hosted generation.

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

## Current implementation

### Factory entities

- `characters`: real people, synthetic influencers, brand mascots
- `references`: image, video, audio, performance, location, wardrobe
- `projects`: units of production work, including a lightweight project brief in metadata
- `generation_jobs`: durable provider-neutral jobs
- `assets`: generated media + provenance schema
- `quality_reviews`: automated/human QA score schema
- `approval_events`: human review decision schema
- `cost_events`: estimated and reconciled spend schema

The canonical Postgres schema is `apps/studio/db/schema.sql`.

### Persistence

`ContentFactoryStore` is the application boundary.

- development may use the in-memory store
- production requires `DATABASE_URL` unless ephemeral storage is explicitly enabled
- `DATABASE_URL` uses the portable Postgres adapter

The application does not depend on Supabase-specific APIs. Supabase, Neon or ordinary Postgres can host the schema.

### Generation

`POST /api/generate` now:

1. validates request shape, provider and tier
2. validates project and character state
3. enforces verified consent for real-person digital twins
4. enforces registered/authorized references for real-person generations
5. resolves stored reference IDs into short-lived provider URLs
6. checks idempotency before paid submission
7. selects the provider
8. validates current OpenRouter video model capabilities when relevant
9. estimates generation cost and applies the configured spend cap
10. creates the durable factory job before provider submission
11. submits the provider job
12. persists provider state and exposes server-side playback

`GET /api/generations/:id` refreshes provider state and updates the factory job.

### Provider hardening

- OpenRouter media retrieval remains server-side so credentials never reach the browser.
- OpenRouter model capability/pricing metadata is queried from the live video catalog instead of using a permanent hard-coded pricing table.
- ComfyUI uses a server-owned workflow by default. Client-supplied arbitrary graphs are disabled unless intentionally enabled for development.

### Object storage

The Studio has an S3-compatible storage layer suitable for Cloudflare R2, AWS S3, MinIO or equivalent storage.

- browser uploads use short-lived signed PUT URLs
- the database stores stable object keys/reference IDs
- generation resolves stored references to short-lived signed GET URLs only when needed
- temporary signed URLs are not the canonical identity of an asset

### Studio UX

The current Studio intentionally presents creative concepts before infrastructure concepts.

Navigation:

```text
Create
  Generate

Talent & assets
  Characters
  Library

Production
  Projects
  Jobs
```

Generate prioritizes:

- visual references
- scene prompt
- setup
- camera
- color
- lighting
- performance
- resolution / aspect ratio / duration / audio

Provider, model and external-reference controls live under Advanced.

Characters is a visual cast manager rather than a database form. Library presents reusable references as Elements. Projects supports a lightweight Project Brief. See `docs/STUDIO_UX_REFERENCE.md`.

### Legacy bridge

`.archon/scripts/factory/generation_gateway.py` lets existing Python/Archon workers submit and poll through the Studio API.

This is the migration seam. New workflow code should use the gateway rather than learning OpenRouter/ComfyUI directly.

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

## Remaining implementation slices

### Slice A — make persistence operational

- run `db/schema.sql` against a development Postgres instance
- smoke-test create/list character, project, reference and generation APIs against the real DB
- add migration/version tooling before schema changes become frequent

### Slice B — generated asset persistence

Source/reference object storage is implemented. Next:

- ingest completed provider outputs into object storage
- create durable `assets` rows
- stop relying on provider retention for completed media
- add generated outputs to Library

### Slice C — real H3 ComfyUI workflow

Do not fabricate workflow JSON from memory.

- import a current API-format H3 workflow from the installed ComfyUI/model environment
- validate checkpoint/custom-node names
- version the known-good graph under `workflows/comfy/`
- define documented input/output bindings
- run smoke tests from the Studio

Then repeat for LTX or another cheap high-throughput model if its economics justify it.

### Slice D — migrate one legacy render path

Migrate the product-pan path first because it is simpler than UGC/digital-human generation.

- expose the approved still through object storage
- call `generation_gateway.py` with that reference
- persist output asset + cost + validation
- compare against the current Higgsfield product-pan output

Do not migrate `animate_ugc.py` until the product-pan bridge is proven.

### Slice E — review and approvals

Connect the original factory approval gate to Studio:

- Review surface
- asset-level approve / reject / needs changes
- QA scores and retry state
- human decision history

### Slice F — worker infrastructure

Only after a real local ComfyUI workflow is proven:

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
- regression tests pass
- Python gateway syntax validation passes
- Postgres schema applies cleanly to a real development DB
- OpenRouter submit/poll/content smoke test passes
- ComfyUI submit/poll/content smoke test passes with at least one real workflow
- factory job persistence survives process restart
- source references upload and resolve through object storage
- one legacy Camber render path works end-to-end through the V2 gateway
- old Higgsfield path remains available for rollback/comparison

At that point V2 is an extension of the factory rather than parallel scaffolding.
