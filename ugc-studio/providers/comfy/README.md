# Comfy Provider / Workflow Layer

ComfyUI is the preferred reusable media-workflow layer for UGC Studio.

## Default posture

- `COMFY_WHERE=local`
- open/local models first
- no paid partner-node spending by default
- project-owned workflows must be derived from working upstream templates or live node schemas
- every project workflow remains experimental until promoted to `validated` in `workflow-registry.json`
- Higgsfield is not a fallback

## Repository layout

```text
ugc-studio/providers/comfy/
  README.md
  workflow-registry.json   # capability -> source candidates + validation status
  recipes/                 # project-owned reusable Comfy recipes (added after validation)
  fixtures/                # representative non-secret inputs for repeatable smoke tests
  benchmarks/              # workflow-specific benchmark summaries (future)
```

Do not commit model weights, generated media, secrets, or machine-specific Comfy installations here.

## Bootstrap on a machine with Comfy

Use the current official Comfy CLI. Confirm the command surface rather than assuming an old version:

```bash
comfy --help
comfy --json discover
comfy --json knowledge pick
comfy --json templates ls --type image --limit 20
comfy --json templates ls --type video --limit 20
```

For local execution:

```bash
export COMFY_WHERE=local
comfy launch
```

If ComfyUI is already running somewhere other than the default local address:

```bash
export COMFY_LOCAL_URL=http://127.0.0.1:8189
```

## Build a project recipe

1. Pick one capability from `workflow-registry.json`.
2. Fetch/reproduce the current official template or other upstream reference.
3. Inspect its actual slots and node schemas.
4. Run it with representative inputs.
5. Use `comfy workflow capture` to create a parameterized recipe under `recipes/`.
6. Record dependencies and provenance next to the recipe.
7. Run UGC Studio QA.
8. Update registry status to `validated` only after the promotion checklist in `docs/ugc-factory/COMFY_WORKFLOW_STACK.md` passes.

## Spend gate

Comfy local execution can still consume paid infrastructure if the machine/GPU itself is metered. Record that cost when known.

Comfy partner/API nodes are a separate paid-provider path. They must not be silently enabled. Any automated use of a paid node requires the same explicit spend approval used by the direct-model path.

An agent must not add `--allow-spend` merely because a workflow fails without it.

## Runtime integration contract

The rest of UGC Studio should care about capabilities, not node graphs. A validated Comfy recipe must expose enough stable parameters to satisfy a capability contract such as:

```json
{
  "capability": "product_i2v",
  "inputs": {
    "start_image": "...",
    "prompt": "...",
    "seed": 42,
    "duration_seconds": 5,
    "aspect_ratio": "9:16"
  }
}
```

The Comfy adapter translates this contract into recipe parameters/slots. Model- or node-specific details stay inside the validated workflow layer.

## Source of truth

Read in this order:

1. live Comfy node/model schemas,
2. official `Comfy-Org/workflow_templates`,
3. official Comfy CLI skills,
4. project-owned validated recipes,
5. community workflows as research patterns only.

See `.claude/skills/comfy-ugc-factory/SKILL.md` for the agent authoring procedure.
