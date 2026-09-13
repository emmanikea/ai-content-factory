# Change Proposal: UGC Studio v1

## Why

The current AI Content Factory proves the core economics of cheap exploration, human approval, and selective rendering. The next step is to generalize that into a short-form UGC production system for apps and startups.

The system should support recurring creators, reference-driven creative ideation, deterministic product/app footage, provider-neutral rendering, rights-aware identity use, and batch variation without making expensive video generation the planning primitive.

## What changes

- Add a Campaign Studio user experience.
- Add a persistent Creator model with rights metadata.
- Add a normalized CreativeSpec contract for concepts and shots.
- Add reference analysis with Creative DNA and Licensed Performance Transfer modes.
- Add deterministic app/product capture as a first-class source type.
- Generalize the existing media worker into provider-neutral capabilities.
- Add a render planner that chooses provider/model per shot based on quality, rights, and budget.
- Add deterministic final composition and QA.
- Preserve the existing approval gate and cost-aware exploration model.

## User-visible outcome

A user can choose a product, creator, and reference, request several creative variants, review ranked CreativeSpecs before spending on video, render selected variants, and receive finished 9:16 UGC videos with provenance, rights, QA, and cost metadata.

## Constraints

- Do not require proprietary Higgsfield infrastructure.
- Keep Higgsfield as an optional adapter.
- No foundation-model training in V1.
- Real-person synthetic generation requires explicit valid rights metadata.
- Public third-party references default to structure extraction, not identity or performance cloning.
- Real app UI should be captured, not hallucinated, whenever deterministic capture is possible.
- Main remains stable; work ships through a feature branch and PR.
