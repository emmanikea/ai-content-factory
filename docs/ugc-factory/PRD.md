# UGC Studio v1 PRD

## Product thesis

AI Content Factory should evolve from a catalog ad demo into a repeatable short-form creative operating system for apps and startups.

The product is not a generic video generator. It turns a product, a creator, and a reference creative into many measurable Reel/TikTok variants while preserving explicit creator rights, using real product/app footage where accuracy matters, and routing each shot to the cheapest model capable of producing acceptable quality.

## Primary user

An internal growth or creative team that needs to produce and test short-form UGC at high volume across multiple products.

Secondary future user: an AI-native UGC agency serving startups.

## Core jobs

1. Create a campaign from an app, website, product, or startup.
2. Add or select a real consented creator or a synthetic creator.
3. Add a reference Reel or a reusable creative template.
4. Extract the reusable creative DNA rather than blindly copying the source.
5. Generate scripts, hooks, shot plans, and variants cheaply before rendering video.
6. Produce accurate app/product footage separately from generative creator footage.
7. Render only approved or highly ranked variants.
8. Assemble final 9:16 videos with captions, music, overlays, B-roll, CTA, and product footage.
9. Track provenance, consent, model, cost, quality, and later performance for every asset.
10. Feed performance back into future creative ranking.

## V1 scope

### Campaign Studio

Each campaign stores:
- product/app
- target audience
- offer/value proposition
- platform
- desired duration
- reference assets
- creator pool
- creative constraints
- CTA

### Creator Library

A creator profile contains:
- canonical identity references
- face references
- full-body references
- voice references
- approved hairstyles/outfits/settings
- reusable performance clips
- consent status
- permitted products/categories
- permitted channels
- allowed synthetic transformations
- compensation metadata
- rights start/end dates
- revocation status

A creator may be `real_consenting`, `synthetic`, or `founder_owned`.

No generation using a real person's identity is eligible for render unless rights state is valid.

### CreativeSpec

Every concept is normalized into a machine-readable CreativeSpec.

Required fields:
- campaign_id
- concept_id
- reference_id
- hook
- angle
- script
- duration_seconds
- aspect_ratio
- shot list
- creator instructions
- app/product demo instructions
- audio plan
- caption style
- CTA
- provider hints
- cost budget
- rights requirements

Every shot records:
- purpose
- start/end timing
- source type
- generation mode
- creator
- dialogue
- motion/performance reference
- product/app requirement
- model/provider preference
- fallback provider

### Reference Repurposer

Two modes:

#### Creative DNA
For third-party public creative. Extract structure, pacing, framing, hook mechanics, transitions, CTA mechanics, and generic performance beats. Create a new work for the selected product and creator.

#### Licensed Performance Transfer
For owned, licensed, or creator-approved source footage. Preserve timing, body motion, camera movement, or facial performance as permitted by the rights record while changing creator appearance, wardrobe, scene, dialogue, or product.

### App Demo Capture

App footage should be deterministic whenever possible.

Web:
- Playwright scripted interactions
- viewport presets for vertical content
- deterministic screen capture

Mobile:
- Maestro or Appium scripts
- emulator/device recording

Generated video models must not be the default path for reproducing UI screens.

### Media Router

Provider-neutral operations:

```text
generateCreatorStill()
generateCreatorVideo()
transferMotion()
replaceCharacter()
editWardrobeOrScene()
generateVoice()
lipSync()
generateBroll()
captureProductDemo()
renderFinal()
validateAsset()
```

Initial provider classes:
- premium multimodal video: Seedance-class
- motion transfer: Kling/Wan-class
- open-source motion/video: Wan-class workers
- identity stills: PuLID/InfiniteYou-class
- talking/lip sync: LivePortrait/MuseTalk-class
- existing Higgsfield CLI adapter retained as one provider

Exact models remain configuration, not product architecture.

### Assembly

Use deterministic composition for final videos:
- creator clips
- app/product footage
- B-roll
- captions
- music/audio
- CTA
- brand overlays

Target renderer: Remotion + FFmpeg.

### Quality gates

Before final approval, evaluate:
- identity consistency
- hands/limbs
- face deformation
- lip sync
- product fidelity
- UI correctness
- text legibility
- creator rights validity
- aspect ratio
- duration
- caption safe zones
- audio clipping

Bad assets retry through the configured fallback policy rather than silently shipping.

## UI requirements

Primary screen: Campaign Studio.

Three core selectors are visible without navigating away:
1. Reference
2. Creator
3. Product

A variation panel lets the user choose counts for hooks, scripts, creators, outfits, locations, languages, and CTAs and shows the combinatorial space before rendering.

The system generates CreativeSpecs first. The user sees ranked cards with estimated cost and quality before expensive video rendering.

The review gallery exposes:
- score
- hook
- creator
- format
- estimated/rendered cost
- provider
- rights status
- QA state

## V1 non-goals

- training a foundation video model
- competing with Higgsfield as a general creation suite
- autonomous publishing to every social network
- recreating third-party creator identity without permission
- blindly cloning a third-party video shot-for-shot
- rendering every possible combination

## Success criteria

V1 is successful when one operator can:
1. create a campaign
2. select a creator and product
3. attach a reference
4. generate multiple CreativeSpecs
5. approve a subset
6. route/render creator shots
7. insert real product/app footage
8. assemble vertical finals
9. see cost, rights, and QA metadata for every output

The end goal is not maximum generations. It is a repeatable loop:

`observe -> understand -> generate -> approve -> render -> publish -> measure -> learn`
