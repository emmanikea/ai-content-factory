# Studio UX Reference

## Purpose

The Studio should feel like a creative production environment, not a provider console.

Higgsfield Cinema Studio 4.0 is a useful reference for interaction hierarchy because it places references, scene direction, cinematography controls and generation settings above model/provider details. AI Influencer is a useful reference for treating persistent characters as reusable cast members rather than repeated prompts.

This is a reference for product principles, not a directive to copy Higgsfield branding or exact UI.

## Core principles

1. **Creative intent first**
   - scene prompt is the primary interaction
   - references and cast are visible near the prompt
   - camera, lighting, color and performance use plain creative language

2. **Infrastructure second**
   - provider and model are hidden under Advanced by default
   - Auto routing should be the normal path
   - cost/provider diagnostics live with the job result, not the creative controls

3. **Persistent Elements**
   - people, image references, performances, locations, wardrobe and outputs should be reusable
   - database table boundaries should not dictate the user-facing information architecture
   - Library is the operator-facing collection of reusable Elements

4. **Cast, not rows**
   - Characters should be visual cards
   - identity references should be visual
   - real-person consent remains explicit and enforced
   - synthetic characters should be easy to create without technical settings

5. **Progressive disclosure**
   - basic generation should require prompt + optional cast/references
   - common creative settings remain one click away
   - provider-specific controls belong in Advanced

6. **Project context**
   - every generation may belong to a project
   - future Project Brief should define tone, references, constraints and reusable direction for agents and teammates

## Current navigation

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

Future surfaces should only be added when their workflow is real. Likely candidates:

- UGC / Product Ad templates
- Talking Head
- Review
- Project Brief
- Canvas / visual workflow builder
- Analytics

Do not add empty navigation items simply to make the product look larger.

## Generate hierarchy

```text
References / Elements

Scene prompt

Setup | Camera | Color | Lighting | Performance

Advanced
  Quality tier
  Provider
  Model
  External reference

1080p | 9:16 | duration | audio | Generate
```

The creative controls currently compile into the generation prompt. As providers expose reliable normalized controls, individual controls can move into structured generation fields without changing the UI hierarchy.

## Character hierarchy

```text
Cast grid
  select character
  create character

Selected character
  hero identity
  type
  consent state when applicable
  identity references
  upload reference
```

For a real person:

- character consent must be verified before generation
- reference authorization must be verified
- arbitrary external references must not bypass the stored provenance path

## Library hierarchy

Library is the user-facing abstraction over reusable assets.

Filters:

- All
- Images
- Video
- Audio
- Performances
- Locations
- Wardrobe

Later it can include generated outputs, products and voices once those are represented by durable asset records.

## What not to expose by default

Avoid placing these in the primary creation surface:

- provider API names
- ComfyUI node IDs
- workflow JSON
- GPU worker settings
- bucket/storage keys
- database UUIDs
- provider-specific retry state

Those remain available to operators through Advanced, Jobs or diagnostics.

## Design character

- monochrome / neutral
- restrained typography
- generous spacing
- visual media over metadata
- compact controls
- no decorative gradients beyond subtle depth/background treatment
- no unnecessary badges or colorful status systems
- responsive enough to operate from a laptop or tablet

## Next UX work

1. Project Brief and project detail view.
2. Generated-output Library backed by the `assets` table.
3. Review surface connecting the original factory approval gate to Studio.
4. Character profile fields for persona, voice, wardrobe and recurring locations.
5. Template entry points for UGC, talking-head and product-ad workflows.
6. Canvas only after multiple real workflows justify a node surface.
