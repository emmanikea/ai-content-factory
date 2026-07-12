---
name: higgsfield
description: |
  Use when the user wants to generate an image, a video, or a UGC-style video ad with the
  Higgsfield CLI. Triggers: "higgsfield", "make an ad", "make a UGC ad", "generate a product
  video", "product pan", "make a video ad with higgsfield".
---

# Higgsfield CLI

Higgsfield is ONE CLI that drives frontier image + video models from the terminal. It is
**self-documenting** — when you're unsure of a model or a flag, ask the CLI itself:

```bash
higgsfield --help                 # top-level commands (generate, model, voices, upload...)
higgsfield model list             # every model (add --video or --image to filter)
higgsfield model get <model>      # the EXACT params for a model: duration caps, flags, defaults
higgsfield voices list            # TTS voices (for text2speech_v2)
```

Every `generate create` job takes `--wait` (block until done) and prints a `result_url` — download that URL to get the file. Aliases: `higgs`, `hf`. On Windows, if `higgsfield` isn't on PATH, call `%APPDATA%\npm\higgsfield.cmd`.

## Models you'll actually use

| Job | Model | Notes |
|-----|-------|-------|
| Product image / plate | `nano_banana_pro` | ~0.15 cr. `--image-references <img>` to keep/edit a real product (e.g. add branding). |
| Product pan (video, no person) | `kling3_0_turbo` | image→video. `--start-image <img> --duration 10 --resolution 1080p`. |
| **UGC talking-head (video + native voice)** | `gemini_omni` | **10s max**, generates its own audio + lipsync. `--image-references <product.jpg>`. |

## Make a UGC ad (the main recipe)

One command → a ~10s vertical ad of a person holding a product and reviewing it in their own voice:

```bash
higgsfield generate create gemini_omni \
  --prompt "A friendly <man|woman> in a bright modern kitchen holding up this <product> toward the camera, casual selfie UGC review, looking right at the camera and speaking warmly in one continuous take: '<~25-word spoken line>' Deliver the line exactly once at a natural, unhurried pace; do NOT repeat, stutter, or loop any word or phrase, and if it finishes before the clip ends, just hold a natural smile in silence. Keep any product logo facing the camera, crisp and legible. Natural handheld vlog style, real skin texture. No on-screen text, no captions, no phone visible in frame." \
  --image-references <path/to/branded-product.jpg> \
  --duration 10 --aspect_ratio 9:16 --resolution 720p --wait
```

Three rules that keep it clean:
1. **`gemini_omni` caps at 10s** — keep the spoken line to ~2 short sentences (~25 words) or the audio gets cut off mid-word.
2. **Always keep the anti-repeat clause** ("deliver the line exactly once… hold a smile in silence"). Without it the model pads the fixed 10s by repeating a phrase.
3. Pass a **branded product image** as `--image-references` so the product and its logo stay accurate through the video.

## Make a product pan (no person)

```bash
# 1) generate the product image
higgsfield generate create nano_banana_pro --prompt "<product>, premium product photo, soft light, no text" --aspect_ratio 9:16 --wait
# 2) animate it into a 10s push-in
higgsfield generate create kling3_0_turbo --start-image <image-from-step-1> --prompt "slow cinematic push-in, gentle light shift, premium product-ad motion" --aspect_ratio 9:16 --duration 10 --resolution 1080p --wait
```

## Gotchas
- Keep each `--prompt` on ONE line — a newline inside the arg can break the CLI on Windows.
- `higgsfield auth login` once to authenticate; `higgsfield account` shows your credit balance.
- Images are cheap (~0.15 cr), video is ~100x more — generate/iterate on images freely, spend deliberately on video.
