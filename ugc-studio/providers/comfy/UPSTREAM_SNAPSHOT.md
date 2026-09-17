# Reviewed Comfy Upstream Snapshot

Checked: 2026-09-14

These pins record what was actually reviewed while designing the Comfy-first UGC stack. They are provenance, not permanent dependency locks. Agents should still inspect the current live CLI/templates before building a new workflow.

| Source | Reviewed revision | Role |
|---|---|---|
| `Comfy-Org/comfy-cli` | `7a79900c3551a188cbbc90515bd4a1958aa5c997` | official CLI + bundled agent skills |
| `Comfy-Org/workflow_templates` | `f7e38002b6fc9edb21d774e48b49e4cf5c0584a2` | official templates/blueprints/manifest |
| `Comfy-Org/comfy-mcp` | `d067bf7dc44b497d88f20c9cd227c64f2ac3e2af` | optional MCP agent control surface |
| `digitalinnovator/comfyui-production-workflows` | `7b24418de051cc2da1857c1a68a256e030bc2a57` | community production patterns/benchmark references |

## Verified official skill family

At the reviewed `comfy-cli` revision, the CLI's skill command describes bundled skills including:

- `comfy`
- `comfy-debug`
- `comfy-relay`
- `comfy-director`
- `comfy-build`
- `comfy-deploy`

The CLI supports project installation with:

```bash
comfy skills install --scope project --dry-run
comfy skills install --scope project
```

It installs into Claude Code, Cursor and AGENTS.md-aware surfaces unless targets are narrowed explicitly.

## Verified official workflow references

At the reviewed official templates revision:

- `templates/image_qwen_image_edit_2511.json` exists,
- `blueprints/image_edit_qwen_2511.json` exists,
- the manifest includes template id `video_ltx2_5_i2v`.

These are starting references only. The agent must fetch the current template, inspect its actual slots/node schemas and reproduce it on the target environment before capturing a project recipe.

## Verified community workflow families

The reviewed community repo advertises 12 production-oriented workflows, including:

- AI UGC video + voice cloning (InfiniTalk + VibeVoice),
- AI UGC video + prebuilt audio,
- Wan 2.2 Animate image-guided trend/motion transfer,
- Qwen product placement,
- realism enhancement,
- InfiniTalk talking avatar.

Use these to discover patterns and dependency combinations. Do not treat them as authoritative current Comfy node schemas.
