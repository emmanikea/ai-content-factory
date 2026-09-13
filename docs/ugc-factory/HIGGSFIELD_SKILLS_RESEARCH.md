# Higgsfield Skills Research for UGC Studio

Last reviewed: 2026-09-12

## Why this exists

Higgsfield's public `higgsfield-ai/skills` repository is useful to this project even when Higgsfield is not our default runtime.

The skills encode practical production knowledge around:

- model selection
- prompting
- image/video reference roles
- UGC/ad modes
- creator/avatar handling
- reusable reference ads
- hook and setting composition
- identity training inputs
- cost inspection
- workflow orchestration

We should treat that repo as a public upstream knowledge source, not as a required dependency for our rendering architecture.

## Upstream snapshot

Repository: `https://github.com/higgsfield-ai/skills`

Snapshot reviewed:

- version: `0.12.0`
- main commit: `d071406147a37b835bed09543d85ab3e9bd85c7d`
- commit date: 2026-09-11
- license: MIT

Because this upstream moves quickly, always record the reviewed version/commit when deriving new behavior from it.

## Optional installation for terminal agents

The skills can be installed into supported coding agents and used as live research/benchmark guidance.

Recommended upstream methods:

```bash
npx skills add higgsfield-ai/skills
```

or:

```bash
gh skill install higgsfield-ai/skills
```

This is optional for our UGC Studio runtime. Installing the skills does **not** mean we should route generation through Higgsfield by default.

Use the skills when an agent needs to:

- inspect current Higgsfield model recommendations
- understand the way Higgsfield composes ads/UGC
- benchmark a Higgsfield route against direct inference
- inspect a newly-added Higgsfield model or workflow
- compare current model/media schemas
- research Higgsfield-specific capabilities such as Soul

## Most relevant upstream files

### Generation/model behavior

- `higgsfield-generate/SKILL.md`
- `higgsfield-generate/references/model-catalog.md`
- `higgsfield-generate/references/prompt-engineering.md`
- `higgsfield-generate/references/media-inputs.md`

### UGC/Marketing Studio

- `higgsfield-generate/references/marketing-modes.md`
- `higgsfield-generate/references/marketing-setup-items.md`
- `higgsfield-generate/references/marketing-ad-references.md`
- `higgsfield-generate/references/marketing-avatars.md`
- `higgsfield-generate/references/marketing-products.md`
- `COOKBOOK.md`

### Creator identity

- `higgsfield-soul-id/SKILL.md`
- `higgsfield-soul-id/references/photo-guide.md`

## Prompting lessons we should adopt

Higgsfield's public guidance validates several prompt rules that should be model-agnostic defaults in our own system.

### 1. Use concrete visual direction

A useful generation brief should describe the visual intent in concrete terms rather than abstract marketing adjectives.

Useful dimensions:

- subject/performance
- scene/setting
- framing
- lens or camera feel when relevant
- camera movement
- subject movement
- lighting
- visual style
- dialogue/audio when the model supports it

### 2. Keep prompts compact

Their public prompt guide warns that overly long prompts degrade output and suggests staying roughly below 200 tokens.

Our compiler should therefore optimize for a concise executable shot brief, not dump the entire campaign strategy into the generation prompt.

Campaign strategy belongs in `CreativeSpec`; the individual model should receive only what it needs for that shot.

### 3. For image-to-video, describe motion rather than redescribing the image

When a reference/start image already anchors:

- identity
- wardrobe
- location
- composition

then the prompt should focus on:

- expression
- gesture
- body movement
- camera movement
- timing
- dialogue/audio

This is especially important for recurring UGC creators because unnecessary restatement can invite unwanted visual drift.

### 4. Phrase desired state positively

Prefer:

- `tack-sharp face`
- `clean hands visible naturally`
- `unobstructed face`
- `stable handheld phone framing`

rather than relying on long lists of negative constraints.

### 5. Treat model schemas as contracts

Higgsfield's skills repeatedly instruct agents to inspect the live model schema instead of guessing media roles or parameters.

We should follow the same philosophy with direct providers:

- provider schemas are source of truth
- adapters compile our stable `CreativeSpec` into provider-specific payloads
- provider parameter changes should not leak into the product/domain model

## Model-selection lessons

At the reviewed upstream version, Higgsfield recommends:

- Seedance 2.5 as the serious all-purpose video default
- Kling 3.0 as a cheaper/simple/single-plane option
- Marketing Studio for ads/UGC workflows
- Soul 2.0 for aesthetic UGC/lifestyle/editorial character images

We should **not blindly copy their ranking** because their economics and platform integrations differ from ours.

We should, however, use those recommendations as a strong benchmark hypothesis.

Our router currently differs intentionally:

```text
draft / cheap testing   -> Wan direct
standard creator shot   -> Kling direct
licensed motion         -> Kling Motion direct
premium/reference-heavy -> Seedance direct
Higgsfield              -> optional benchmark/proprietary route
```

The long-term winner is determined by measured cost per usable approved second.

## The most useful Marketing Studio idea: composable creative primitives

Higgsfield exposes reusable concepts for:

- avatar
- product
- hook
- setting
- ad reference
- mode

That is highly relevant to our architecture.

We should model the same concept at a provider-neutral level.

### Our equivalent

```text
Creator
Product
HookTemplate
SettingTemplate
ReferenceAnalysis
Format / UGCMode
CreativeSpec
```

These primitives can be recombined without rewriting a complete prompt every time.

### Hook

Higgsfield treats a hook as reusable opening-angle context which is combined with the user's prompt.

We should adopt this concept as a `HookTemplate` / hook library that can carry:

- hook type
- opening line
- visual beat
- emotional mechanism
- duration target
- product transition rule
- prior performance metrics

### Setting

A setting should be a reusable scene/environment prescription:

- bedroom
- car
- kitchen
- office
- street
- airport
- bridge crossing context
- etc.

The setting should not become tangled with the creator's core identity.

### Reference-driven vs composed-from-blocks

One especially useful Higgsfield constraint is conceptual rather than vendor-specific:

- reference-driven generation is one path
- hook + setting composition is another path

Higgsfield does not combine its ad-reference path with hook/setting IDs.

For our system this suggests we should explicitly choose a generation strategy:

1. **Reference-driven**
   - derive shot rhythm/performance from an approved reference
   - useful for owned/licensed performance transfer or strongly reference-led creative

2. **Block-composed**
   - Creator + Hook + Setting + Product + Script + CTA
   - useful for scalable variations

We can still borrow high-level Creative DNA from a public reference before constructing a new block-composed creative.

## UGC format taxonomy worth adopting

Higgsfield's current Marketing Studio modes provide a useful starting taxonomy:

- UGC / organic presenter
- tutorial / how-to
- unboxing
- product showcase
- product review
- polished commercial / TV-style spot
- experimental/wild-card
- UGC try-on
- polished try-on

For apps/startups, our equivalent should expand with:

- reaction -> app demo
- problem -> app solution
- POV / situation
- testimonial
- founder POV
- comparison
- listicle
- screen-record-first demo
- storytime
- comment/reply style
- green-screen commentary

The taxonomy belongs in our product layer; individual video providers simply execute shots.

## Reusable ad-reference workflow

Higgsfield processes a source video into a reusable ad-reference object, optionally associated with an avatar and product.

This strongly validates our `ReferenceAnalysis` direction.

Our richer reference object should preserve:

- source asset + source rights mode
- transcript
- scenes/cuts
- hook mechanics
- pacing
- shot types
- generic performance beats
- camera behavior
- audio/dialogue structure
- app/product-demo regions
- CTA pattern
- reusable Creative DNA

For licensed/owned references it may also preserve:

- exact timing
- pose/motion track
- camera track
- performance-transfer eligibility

## Creator identity lessons from Soul ID

Higgsfield's public Soul guide recommends 5–20 photos, with roughly 8–12 as a practical sweet spot.

Useful collection guidance:

- clear face / visible eyes
- one person per image
- varied front and three-quarter views
- varied lighting
- varied expressions
- varied distances, including upper/full body
- sharp, unfiltered images
- roughly 1024x1024 or better when possible

That is now our recommended minimum onboarding pack for a real consenting creator as well, even though our pack remains portable and is not tied to Soul.

Our `CreatorIdentityPack` should be capable of binding the same creator to multiple backends:

```text
portable canonical references
  -> direct model references
  -> future local identity embedding / LoRA
  -> optional Higgsfield Soul ID
  -> other provider-specific identity handles
```

Provider-specific bindings must be marked non-portable.

## Media-role lessons

The upstream repo documents explicit differences between model inputs such as:

- start image
- end image
- general image references
- video references
- audio references

This validates our adapter/compiler boundary.

For example, Seedance-style multimodal generation can benefit from separate image/video/audio roles, while Kling image-to-video is more naturally anchored by start/end frames.

Do not collapse all references into one undifferentiated `media[]` list at the domain level.

## Batch-generation lesson

The Higgsfield cookbook explicitly demonstrates producing multiple UGC/ad modes in parallel from one product.

Our system should go further:

```text
Product
x Creator
x Hook
x Script
x Format
x Setting
x CTA
= conceptual search space
```

But only a ranked subset should render.

This matches the existing UGC Studio principle:

`generate specs cheaply -> rank -> approve -> render a small frontier`

## Virality Predictor lesson

Higgsfield exposes a finished-video analysis step for hook/attention/retention/virality.

Regardless of whether we use their predictor, the architectural lesson is valuable:

A final render should not be treated as the end of the creative pipeline.

Our future post-render evaluation should measure:

- first-second hook clarity
- attention continuity
- dead time
- product/app visibility
- creator vs product balance
- speech/caption comprehensibility
- CTA timing
- predicted hold / retention
- eventually actual platform performance

## How to use Higgsfield in this repo

### Good uses

- research their latest model recommendations
- learn prompt/media conventions
- benchmark the same shot against Higgsfield
- inspect proprietary Soul/Cinema behavior
- interrogate current Higgsfield cost before an optional benchmark
- discover new creative workflow patterns we can reproduce provider-neutrally

### Bad uses

- routing every generation through Higgsfield simply because the skill exists
- embedding Higgsfield-only IDs into `CreativeSpec`
- treating Higgsfield credit pricing as equivalent to direct provider pricing
- copying a platform recommendation without measuring quality-per-dollar ourselves
- making Soul ID the only representation of a creator

## Upstream refresh procedure

Before a major benchmark or every few weeks during active development:

1. Check `higgsfield-ai/skills/VERSION`.
2. Record latest main commit SHA/date.
3. Diff relevant files:
   - generate skill
   - model catalog
   - prompt engineering
   - media inputs
   - marketing modes/setup/ad references
   - Soul ID/photo guide
4. Update this document only when the change affects our architecture or prompt/routing behavior.
5. Update `ugc-studio/providers/research-sources.json`.
6. Re-verify direct-provider pricing independently.

Do not silently overwrite historical benchmark results when upstream recommendations or prices change.

## License note

The upstream skills repo is MIT-licensed as reviewed on 2026-09-12. Even so, our implementation should prefer derived model-agnostic rules over vendoring large copies of their skill files. This keeps our architecture clearer and reduces synchronization burden.
