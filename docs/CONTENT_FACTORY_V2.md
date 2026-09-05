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

V2 adds the infrastructure required for AI influencers, real-person digital twins, model routing, reusable references, durable jobs, cost accounting and self-hosted generation.

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

- no `DATABASE_URL`: in-memory development store
- `DATABASE_URL`: portable Postgres adapter

The application does not depend on Supabase-specific APIs. Supabase, Neon or ordinary Postgres can host the schema.

### Generation

`POST /api/generate` now:

1. normalizes the generation request
2. routes to OpenRouter or ComfyUI
3. estimates provider cost when a reference rate is known
4. creates a factory-level generation record
5. returns both provider and factory job IDs

`GET /api/generations/:id` refreshes the provider job and updates factory state.

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

## Next implementation slices

### Slice A — make persistence operational

- run `db/schema.sql` against a development Postgres instance
- test create/list character, project and generation APIs
- add migration/version tooling before schema changes become frequent

### Slice B — asset storage

Add one object-storage abstraction for:

- source references
- generated images
- generated video
- thumbnails
- audio
- QA frame samples

The DB stores stable keys and provenance; provider-signed URLs should not become canonical asset identities.

### Slice C — real H3 ComfyUI workflow

Do not fabricate workflow JSON from memory.

- import a current API-format H3 workflow from the installed ComfyUI/model environment
- validate checkpoint/custom-node names
- version the known-good graph under `workflows/comfy/`
- define documented input/output placeholders
- run smoke tests from the Studio

Then repeat for LTX or another cheap high-throughput model.

### Slice D — migrate one legacy render path

Migrate the product-pan path first because it is simpler than UGC/digital-human generation.

- expose the approved still through object storage
- call `generation_gateway.py` with that reference
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

For real people, references must carry consent/provenance metadata.

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
- OpenRouter submit/poll smoke test passes
- ComfyUI submit/poll smoke test passes with at least one real workflow
- factory job persistence survives process restart
- one legacy Camber render path works end-to-end through the V2 gateway
- old Higgsfield path remains available for rollback/comparison

At that point V2 is an extension of the factory rather than parallel scaffolding.
