# UGC Studio v1 Design

## Architecture principles

1. Planning is cheap; rendering is expensive.
2. Creative intent is stored independently from any model provider.
3. Every media artifact is attributable to its inputs, model, prompt/config, rights state, cost, and QA result.
4. Deterministic product footage beats generative reconstruction for UI/product truth.
5. The system routes individual shots, not entire campaigns, to providers.
6. Human approval remains between exploration and expensive rendering.

## Domain model

### Campaign
Owns audience, product, references, creators, platform, creative constraints, and goals.

### Creator
Owns identity references, voice references, style presets, performance references, and rights policy.

### ReferenceAsset
A Reel, raw clip, ad, image, script, or template supplied for analysis.

Rights mode:
- `creative_dna_only`
- `licensed_performance_transfer`
- `owned_source`

### CreativeSpec
Provider-neutral representation of one proposed short-form creative.

### ShotSpec
One timed unit in a CreativeSpec. Source type is one of:
- `creator_generated`
- `creator_motion_transfer`
- `creator_lipsync`
- `app_capture`
- `product_capture`
- `broll_generated`
- `owned_media`
- `graphic`

### RenderJob
An executable provider-specific job derived from a ShotSpec.

### Artifact
A generated/captured media output plus provenance.

### QAResult
Automated and human validation metadata.

## Pipeline

```text
Campaign
  -> Reference analysis
  -> Creative DNA / licensed performance plan
  -> CreativeSpec generation
  -> Cheap ranking + cost estimate
  -> Human approval
  -> Shot planner
       -> creator render jobs
       -> app/product capture jobs
       -> b-roll jobs
  -> per-shot QA/retry
  -> deterministic assembly
  -> final QA
  -> approved final
  -> performance ingest (future)
```

## Provider boundary

The existing `media_worker.py` remains the migration seam. Introduce a capability-oriented interface above vendor implementations.

```python
class MediaProvider:
    def capabilities(self): ...
    def estimate(self, job): ...
    def submit(self, job): ...
    def poll(self, job_id): ...
    def fetch(self, job_id): ...
```

Capabilities are described separately from provider names:

```text
identity_still
text_to_video
image_to_video
reference_to_video
motion_transfer
character_replace
video_edit
voice_clone
speech
lip_sync
broll
```

The router scores eligible providers by:
- required capability
- quality tier
- creator/rights restrictions
- estimated cost
- latency
- previous QA pass rate
- campaign budget

## Rights enforcement

Rights are not a note field. They are a hard render precondition.

A real-person Creator must have:
- consent state `active`
- valid term for render date
- requested product/category permitted
- requested platform permitted
- requested transformation permitted

If any check fails, the job is blocked before provider submission.

Public third-party reference assets default to `creative_dna_only`. This mode may extract structure and generic performance descriptions but cannot request identity reproduction or literal performance transfer.

## CreativeSpec contract

Store JSON and validate before render.

Example:

```json
{
  "version": "1.0",
  "campaign_id": "bordereta-launch-01",
  "concept_id": "concept-014",
  "format": "ugc_reaction_demo",
  "duration_seconds": 18,
  "hook": "I didn't know there was a faster way to pick a bridge.",
  "angle": "surprise + utility proof",
  "creator_id": "creator-003",
  "shots": [
    {
      "id": "s1",
      "start": 0,
      "end": 2.2,
      "source_type": "creator_generated",
      "purpose": "hook reaction",
      "dialogue": "Wait, why did nobody tell me this existed?"
    },
    {
      "id": "s2",
      "start": 2.2,
      "end": 8.5,
      "source_type": "app_capture",
      "purpose": "show bridge comparison",
      "capture_script": "open app; show bridge cards; tap fastest route"
    },
    {
      "id": "s3",
      "start": 8.5,
      "end": 11,
      "source_type": "creator_generated",
      "purpose": "confirmation reaction"
    }
  ]
}
```

## Capture subsystem

### Web
Playwright scripts produce reproducible viewport recordings and optional cursor/touch indicators.

### Mobile
Maestro is preferred for concise deterministic flows; Appium remains a fallback for cases requiring deeper automation.

Capture scripts are versioned alongside CreativeSpecs so a product demo can be re-rendered after UI changes.

## Assembly subsystem

Use Remotion for timeline composition and FFmpeg for normalization/transcoding.

Composition responsibilities:
- clip timing
- crop/scale
- transitions
- captions
- safe zones
- overlays
- CTA cards
- audio mixing
- background music
- loudness normalization
- final 1080x1920 export

Generative providers should not be responsible for the final edit when deterministic composition can do it better.

## QA

### Shot QA
- face/identity consistency
- deformation
- hand/limb artifacts
- product fidelity
- lip sync
- UI correctness
- text correctness
- expected duration
- resolution/aspect ratio

### Final QA
- no blank frames
- no unintended black bars
- caption safe zones
- consistent loudness
- CTA visibility
- rights pass for every included artifact
- provenance complete

## Storage layout

Initial filesystem-compatible layout:

```text
ugc-studio/
  data/
    campaigns/
    creators/
    references/
    specs/
    jobs/
    artifacts/
  captures/
  renders/
```

This can later map cleanly to Postgres + R2/S3 without changing the domain contract.

## Migration strategy

1. Keep existing catalog demo working.
2. Add UGC Studio as an independent surface.
3. Reuse the existing media worker through an adapter.
4. Convert existing UGC generation into the first provider implementation.
5. Add second provider only after the contract is exercised.
6. Move storage from filesystem JSON to database/object storage after the workflow stabilizes.
