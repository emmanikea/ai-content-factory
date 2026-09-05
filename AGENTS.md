# Agent Operating Contract

This repository is an AI content-generation factory. Treat generation providers as replaceable infrastructure.

## Non-negotiables

1. Never hard-code a model/provider into UI code. Route through `apps/studio/lib/generation/router.ts` or the existing swappable media-worker boundary.
2. Do not remove the existing Higgsfield implementation until the OpenRouter/ComfyUI replacement has equivalent tests and output validation.
3. Never commit secrets, API keys, signed URLs, generated private media, or identity/voice datasets.
4. Every real generation attempt must be attributable to a provider, model, request settings, status, and cost when available.
5. Expensive fan-out must be opt-in. Avoid hidden multi-model calls.
6. Reference media involving real people must preserve consent/provenance metadata in the eventual persistence layer.
7. Prefer small PRs with tests. Do not push directly to `main`.

## Architecture

Read `docs/OPEN_GENERATION_STACK.md` before changing generation infrastructure.

Primary layers:

- Existing Archon workflows: orchestration / approval / QA.
- `apps/studio`: internal operator frontend.
- `lib/generation`: provider-neutral request and job contract.
- OpenRouter: hosted/premium video route.
- ComfyUI: self-hosted/bulk route.
- `workflows/comfy`: versioned model workflows; never embed giant graphs in TypeScript.

## Definition of done for generation changes

- Typecheck passes.
- Provider errors are surfaced with actionable messages.
- No secret is sent to the browser.
- No real generation is triggered by tests.
- Dry-run/mock path remains possible.
- Cost-impacting behavior is documented.
- Existing factory workflows are not silently broken.

## Recommended agent workflow

1. Read `docs/OPEN_GENERATION_STACK.md` and relevant code.
2. Make the smallest coherent change on a feature branch.
3. Run lint/typecheck/tests.
4. Review the diff for accidental spend, secret exposure, and provider coupling.
5. Open a PR with implementation notes and remaining setup steps.
