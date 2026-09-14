---
name: higgsfield
description: |
  Historical Higgsfield research only. Runtime use is disabled in this repository. Do not invoke
  Higgsfield CLI/API/MCP for image, video, UGC, fallback, benchmarking, or production unless a future
  explicit repository policy change re-enables it.
---

# Higgsfield — Research Only / Runtime Disabled

Higgsfield runtime is intentionally disabled for this repository because the current product direction is Comfy-first/open-model/direct-provider and cost-sensitive.

## Hard rule

Do **not** call:

- the Higgsfield CLI,
- Higgsfield API,
- Higgsfield MCP,
- Higgsfield paid generation endpoints,
- old `.archon/scripts/factory/*` Higgsfield generation paths,
- or Higgsfield as an automatic fallback.

`ENABLE_HIGGSFIELD_RUNTIME=0` is the repository default. An agent must not change that value to make a task easier.

If a user later explicitly decides to restore Higgsfield runtime, treat that as an architecture/policy change: update the provider policy, active workflows, spend controls and benchmarks deliberately. Do not silently reactivate old commands.

## What may still be used

Historical/public Higgsfield skills and docs may be read as **research material** for:

- UGC creative patterns,
- prompt structure,
- shot/camera vocabulary,
- identity/reference workflow ideas,
- product-ad workflow decomposition,
- comparison against our Comfy/direct-model implementation.

Translate useful ideas into provider-neutral CreativeSpec/Comfy workflows. Do not translate a research finding into a Higgsfield generation call.

## Current execution path

For media workflow work, load:

`.claude/skills/comfy-ugc-factory/SKILL.md`

and read:

`docs/ugc-factory/COMFY_WORKFLOW_STACK.md`

The preferred execution hierarchy is:

```text
deterministic capture/assembly
        -> Comfy local/self-hosted validated workflows
        -> direct hosted provider only when benchmarks justify it
        -> NEVER automatic Higgsfield fallback
```

The historical analysis of Higgsfield skills remains in `docs/ugc-factory/HIGGSFIELD_SKILLS_RESEARCH.md` for reference.
