# Gemini Omni Flash integration

Checked against Google AI for Developers on 2026-09-17.

Google now recommends **Gemini Omni Flash (`gemini-omni-1.1-flash`) as the default video-generation model** for new workflows, citing stronger coherence, multi-input reasoning, character consistency, factual accuracy, and conversational editing. Veo 3.1 remains useful for specific controls and remains a separate provider lane in UGC Studio.

## Why it matters for UGC Studio

Omni accepts text, images, video, and reference media in the same interaction. It supports image-to-video, reference-to-video, iterative editing, extension, 9:16 output, native audio, and explicit media-role prompting. This maps well to CreatorIdentityPack + CreativeSpec workflows where identity, product, and performance references may need to be combined.

We do **not** replace Veo Lite with Omni. We benchmark both:

```text
Veo 3.1 Lite 720p -> cheaper Google baseline (~$0.05/s)
Gemini Omni 720p  -> stronger/default Google video candidate (~$0.10/s effective video output)
```

The Omni price is an effective 720p video-output rate from Google's token schedule. Input tokens are billed separately, and actual output duration/token usage can vary, so it is not treated as a provider-guaranteed per-request quote.

## Adapter

`ugc-studio/providers/google-omni/client.py`

Dry run:

```bash
python ugc-studio/providers/google-omni/client.py --job job.json
```

Cost preview:

```bash
python ugc-studio/providers/google-omni/client.py --job job.json --estimate
```

Live:

```bash
python ugc-studio/providers/google-omni/client.py --job job.json --live --outdir ./google-omni-output
```

Live still requires:
- `rights_approved=true`
- `approved_for_spend=true`
- `max_provider_cost_usd`
- `GEMINI_API_KEY`
- `--live`

## Media safety / staging

The adapter does not fetch arbitrary image/video URLs. Inline base64 media is supported, as are Gemini Files API URIs. Hosted creator references should therefore be staged into Gemini Files (or encoded locally) before Omni generation. This avoids turning the provider adapter into an SSRF-capable general URL fetcher.

## V1 benchmark constraint

The adapter deliberately limits benchmark generation to **720p**. Google documents approximately $0.10/s of 720p output for Gemini Omni Flash. Higher resolutions are supported by the model, but UGC Studio should not assign them the same cost assumption until their measured/token economics are recorded.

Expected duration is a planning field between 3 and 10 seconds. Omni can produce 3–10 second video, but the current docs do not expose the same exact duration control contract as Veo's 4/6/8-second parameter. For that reason the preflight estimate is explicitly an approximation, not an exact quote.

## Prompting implication

Google notes that Omni tends to create multiple shots unless instructed otherwise. Creator-shot prompts should include language such as:

```text
single continuous shot
single unbroken scene
no scene cuts
```

For identity/reference work, its media-role tags (`<FIRST_FRAME>`, `<IMAGE_REF_N>`, `<VIDEO_REF_N>`) may be useful later in the prompt compiler.

## Sources

- https://ai.google.dev/gemini-api/docs/video
- https://ai.google.dev/gemini-api/docs/omni
- https://ai.google.dev/gemini-api/docs/pricing
- https://ai.google.dev/gemini-api/docs/models/gemini-omni-flash
- https://ai.google.dev/gemini-api/docs/deprecations
