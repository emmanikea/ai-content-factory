# Comfy Agent Bootstrap

Use this when a terminal/worker machine is ready to author or run Comfy workflows for this repo.

## 1. Verify the current CLI

```bash
comfy --version
comfy --json discover
```

Do not proceed by guessing if the CLI is missing or the command surface differs from the current docs.

## 2. Install the official Comfy agent skills into this project

The current official CLI ships skills for Claude Code, Cursor and AGENTS.md-aware agents.

Preview first:

```bash
comfy skills install --scope project --dry-run
```

Then install:

```bash
comfy skills install --scope project
```

Inspect what is available:

```bash
comfy skills list
comfy skills status
```

The core installed family currently includes `comfy`, `comfy-debug`, `comfy-relay`, `comfy-director`, `comfy-build` and `comfy-deploy`. The CLI also exposes deeper reference skills on demand; inspect them with `comfy skills show <name>` instead of assuming they are installed globally.

Our repository-specific policy/UGC skill remains:

`.claude/skills/comfy-ugc-factory/SKILL.md`

The official skills explain Comfy mechanics; our skill explains how this factory should use them.

## 3. Route to local Comfy by default

```bash
export COMFY_WHERE=local
export COMFY_LOCAL_URL=http://127.0.0.1:8188
export COMFY_ALLOW_SPEND=0
```

Start Comfy if needed:

```bash
comfy launch
```

## 4. Refresh/discover before model selection

```bash
comfy --json knowledge status
comfy --json knowledge pick
comfy --json templates ls --type image --limit 20
comfy --json templates ls --type video --limit 20
```

For a specific task, ask the knowledge layer using the task words instead of picking a remembered model name:

```bash
comfy --json knowledge pick "product placement with a real product reference"
comfy --json knowledge pick "image to video product b-roll"
comfy --json knowledge pick "talking person driven by exact audio"
```

## 5. Work capability-by-capability

Open:

`ugc-studio/providers/comfy/workflow-registry.json`

Take one `candidate` or `research` capability at a time. Start from its official template source, reproduce it, parameterize it as a project recipe, QA it, then promote it to `validated`.

## 6. Never bypass spend policy

If a Comfy graph uses a paid partner/API node, do not add `--allow-spend` simply because execution requests it. Paid execution must pass the same deliberate spend approval used by direct hosted providers.

Higgsfield is not a fallback. `ENABLE_HIGGSFIELD_RUNTIME=0` remains the repository policy.
