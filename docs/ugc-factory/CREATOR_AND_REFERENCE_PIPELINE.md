# Creator and Reference Ingestion Pipeline

Last updated: 2026-09-12

## Purpose

UGC Studio needs two durable reusable inputs before generation becomes reliable:

1. a portable creator identity pack
2. a structured understanding of a reference Reel/video

Neither object should belong to Higgsfield, fal, Kling, Seedance, Wan, or any other provider. Provider-specific IDs are optional bindings on top of portable source assets and rights records.

## Creator pipeline

```text
creator assets + rights record
        ↓
creator import manifest
        ↓
build_identity_pack.py
        ↓
CreatorIdentityPack
        ↓
prepare_creator_assets.py
        ↓
rights-approved render assets
        ↓
Wan / Kling / Seedance / local identity model / optional Higgsfield
```

### Recommended source pack

For a reusable real creator identity, target roughly 8–12 clean images with meaningful variety.

Useful coverage:

- front-facing neutral
- front-facing expression/smile
- three-quarter left/right
- profile
- upper body
- full body
- talking expression
- varied natural lighting

This target is informed in part by the public Higgsfield Soul ID onboarding guidance reviewed in `HIGGSFIELD_SKILLS_RESEARCH.md`, but our identity pack is provider-neutral.

The builder does not claim those photos are semantically good identity references merely because files exist. It records deterministic metadata and leaves `semantic_identity_review_required: true` until visual QA is implemented.

### Rights are part of the pack

For `real_consenting` and `founder_owned` creators, the builder requires:

- `rights_snapshot.consent_state = active`
- a non-empty `agreement_reference`

If a performance clip is marked `approved_for_motion_transfer: true`, the rights snapshot must explicitly include `motion_transfer`.

A provider binding never overrides the rights snapshot.

Product/category scope has explicit semantics:

- both product and category allow-lists empty = unrestricted within the agreement
- either populated list creates a restriction
- a render is allowed when the requested product OR category matches an explicit allowed value

This prevents an empty product list from accidentally erasing a populated category restriction.

### Asset provenance

For local assets the builder records:

- SHA-256
- byte size
- MIME type when detectable
- width/height/duration when `ffprobe` can inspect it

For remote assets the builder records that the source is remote without downloading it. Production object storage can later add immutable checksum/version metadata.

### Build command

```bash
python .archon/scripts/ugc/build_identity_pack.py \
  ugc-studio/examples/creator-import.example.json \
  --out ./creator-pack.json
```

The example uses placeholder remote URLs and a placeholder agreement reference. Real packs must point to actual approved source assets and rights records.

### Derive render rights and assets

The normal render path should not require an operator to hand-author `rights_approved: true`.

Use the pack to evaluate the exact request:

```bash
python .archon/scripts/ugc/prepare_creator_assets.py ./creator-pack.json \
  --product-id bordereta \
  --product-category apps \
  --platform instagram \
  --transform face_generation \
  --transform script_change \
  --require-remote \
  --out ./creator-assets.json
```

For licensed motion transfer:

```bash
python .archon/scripts/ugc/prepare_creator_assets.py ./creator-pack.json \
  --product-id bordereta \
  --product-category apps \
  --platform instagram \
  --transform face_generation \
  --transform motion_transfer \
  --performance-id reaction-surprise \
  --require-remote \
  --out ./creator-motion-assets.json
```

The resolver checks:

- consent state
- validity dates
- product/category scope
- platform scope
- every requested transformation
- whether the selected performance clip is itself marked motion-transfer approved

The resulting manifest contains a derived rights decision and agreement evidence that the direct render job preserves in provenance.

Local assets can still be used, but direct hosted providers need an upload/staging step before `--require-remote` can pass.

### Future provider bindings

The same pack can later bind to:

```text
canonical portable identity references
    ├── Kling/Seedance/Wan image references
    ├── PuLID / InfiniteYou-class identity representation
    ├── future LoRA / local identity worker
    ├── Higgsfield Soul ID
    └── another provider-specific identity handle
```

Provider-specific bindings should be marked non-portable when they cannot leave that provider.

## Reference-video pipeline

Reference understanding is deliberately split into two stages.

```text
reference video
      ↓
DETERMINISTIC OBSERVATION
ffprobe + ffmpeg + optional transcript
      ↓
ReferenceObservation
      ↓
SEMANTIC ENRICHMENT
vision adapter / multimodal agent / human
      ↓
ReferenceSemanticLabels
      ↓
build_reference_analysis.py
      ↓
ReferenceAnalysis
```

### Why two stages

FFmpeg can truthfully tell us:

- duration
- resolution / FPS
- whether audio exists
- scene-change candidates
- segment boundaries
- keyframe images

It cannot truthfully tell us that a segment is:

- a hook
- a creator reaction
- an app demo
- proof
- a CTA

Those are semantic judgments. Keeping the stages separate prevents deterministic tooling from inventing creative meaning.

### Stage 1: factual observation

```bash
python .archon/scripts/ugc/observe_reference.py ./reel.mp4 \
  --id reference-001 \
  --rights-mode creative_dna_only \
  --scene-threshold 0.35 \
  --keyframes-dir ./reference-001-keyframes \
  --out ./reference-001-observation.json
```

The observer uses `ffprobe` and `ffmpeg` and hashes the input video.

#### Transcription

If a transcript already exists:

```bash
python .archon/scripts/ugc/observe_reference.py ./reel.mp4 \
  --id reference-001 \
  --rights-mode creative_dna_only \
  --transcript-json ./transcript.json \
  --out ./reference-001-observation.json
```

If the local OpenAI Whisper CLI is installed:

```bash
python .archon/scripts/ugc/observe_reference.py ./reel.mp4 \
  --id reference-001 \
  --rights-mode creative_dna_only \
  --whisper \
  --out ./reference-001-observation.json
```

Whisper is optional. The observer itself does not require a paid transcription API.

### Stage 2A: automatic semantic enrichment

An optional Gemini adapter consumes the strict observation and available keyframes:

```bash
uv run .archon/scripts/ugc/enrich_reference_semantics.py \
  ./reference-001-observation.json \
  --out ./reference-001-semantics.json \
  --provenance-out ./reference-001-semantics-provenance.json
```

It reads `GEMINI_API_KEY` or `GOOGLE_API_KEY`. The model is configurable through `REFERENCE_GEMINI_MODEL` or `--model`.

Dry-run the exact prompt/keyframe packet without making a model call:

```bash
uv run .archon/scripts/ugc/enrich_reference_semantics.py \
  ./reference-001-observation.json \
  --out /tmp/not-used.json \
  --dry-run
```

The adapter:

- sends semantic instructions plus observed keyframes/transcript
- requires JSON output
- validates the result through the same final ReferenceAnalysis compiler
- fails when credentials are absent
- does not fall back to a heuristic semantic guess

A keyframe is treated as visual evidence from a segment, not proof of its full motion or proof of rights.

### Stage 2B: provider-neutral/manual semantic enrichment

Generate the exact enrichment instruction:

```bash
python .archon/scripts/ugc/build_reference_analysis.py \
  ./reference-001-observation.json \
  --print-prompt
```

A different multimodal agent or human reviewer can use the source video/keyframes plus that instruction to produce JSON matching:

`ugc-studio/schemas/reference-semantic-labels.schema.json`

The semantic layer labels each observed segment exactly once and describes:

- role
- shot type
- framing
- generic motion
- dialogue function
- transition
- hook mechanic
- reusable structure
- camera/editing language
- performance style
- CTA mechanic
- what to preserve structurally
- what must change in the new creative

Example labels:

`ugc-studio/examples/reference-semantics.example.json`

### Compile final ReferenceAnalysis

```bash
python .archon/scripts/ugc/build_reference_analysis.py \
  ./reference-001-observation.json \
  --semantics ./reference-001-semantics.json \
  --out ./reference-001-analysis.json
```

The compiler also calculates observed pacing from segment lengths instead of asking the semantic model to invent a numeric pacing profile.

## Rights behavior for references

### `creative_dna_only`

Use for public/third-party inspiration unless stronger rights are documented.

Allowed reuse:

- hook mechanic
- abstract shot sequence
- pacing concept
- framing style
- generic reaction type
- editing language
- problem/solution structure
- CTA structure

Literal motion/performance transfer remains false for every beat regardless of what the semantic analyzer says.

### `licensed_performance_transfer`

Use when the source performance is licensed for that transformation. Final beats can be marked eligible for literal motion reference use.

### `owned_source`

Use for footage the project owns and has rights to transform. It receives the same literal-motion eligibility at the reference level, subject to creator-specific rights checks.

The creator rights record and reference rights mode both matter. One cannot override the other.

## What this pipeline still does not do

Current implementation does not yet:

- visually score identity-reference quality against the creator across the whole pack
- perform OCR as a default reference-analysis step
- infer copyright/license status from a URL or visual content
- automatically upload local creator assets to hosted inference storage
- propagate a later rights revocation through every derived artifact/job

Those are separate explicit follow-up layers rather than hidden assumptions in ingestion.

## Resulting production flow

With both reusable objects available, a campaign can become:

```text
CreatorIdentityPack
        +
ReferenceAnalysis
        +
Product/App
        +
Hook / Setting / CTA variation
        ↓
CreativeSpec variants
        ↓
rank cheaply
        ↓
prepare rights-approved creator assets
        ↓
render selected creator shots
        ↓
insert deterministic app/product capture
        ↓
assemble + QA + measure
```

This is the core path toward "give the system this creator, this successful Reel structure, and this app, then produce several new testable creatives" without binding the factory to one generation platform.
