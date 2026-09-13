#!/usr/bin/env python3
"""Model-aware prompt compiler for UGC creator shots.

The stable input is a provider-neutral ShotSpec-like dict. The compiler keeps prompts
short and execution-focused, especially for image-to-video where the reference image
already anchors identity, wardrobe, setting, and composition.

The rules are derived from public model/provider guidance and our own UGC architecture;
this module does not require Higgsfield at runtime.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

PROMPT_COMPILER_VERSION = "2026-09-12.1"
MAX_WORDS = 150


@dataclass(frozen=True)
class CompiledPrompt:
    text: str
    strategy: str
    version: str = PROMPT_COMPILER_VERSION


def _clean(value: str | None) -> str:
    if not value:
        return ""
    value = re.sub(r"\s+", " ", value).strip()
    return value.rstrip(" .")


def _sentence(value: str | None) -> str:
    value = _clean(value)
    return f"{value}." if value else ""


def _cap_words(text: str, max_words: int = MAX_WORDS) -> str:
    words = text.split()
    if len(words) <= max_words:
        return text.strip()
    trimmed = " ".join(words[:max_words]).rstrip(" ,;:")
    return f"{trimmed}."


def _dialogue(shot: dict[str, Any], generate_audio: bool) -> str:
    dialogue = _clean(shot.get("dialogue"))
    if not dialogue:
        return ""
    if generate_audio:
        return f'The creator says naturally: "{dialogue}".'
    # If audio is being built separately, the visual model needs a performance cue rather
    # than an instruction to synthesize speech/audio.
    return "Natural conversational mouth and facial movement suitable for later lip sync."


def _base_motion(shot: dict[str, Any]) -> str:
    visual = _sentence(shot.get("visual_direction"))
    if visual:
        return visual
    purpose = _clean(shot.get("purpose")) or "creator reaction"
    return f"Natural {purpose} with subtle believable facial and body movement."


def _i2v_prompt(shot: dict[str, Any], *, generate_audio: bool) -> CompiledPrompt:
    # The start/reference image owns the static visual facts. Avoid restating appearance,
    # wardrobe, room, etc. unless the shot's visual_direction explicitly needs a change.
    parts = [
        _base_motion(shot),
        _dialogue(shot, generate_audio),
        "Casual smartphone UGC performance with stable framing and natural micro-movements.",
        "Maintain consistent face, body proportions, clothing, background, and lighting from the reference image.",
        "Clean natural hands and facial detail throughout the motion.",
    ]
    return CompiledPrompt(_cap_words(" ".join(filter(None, parts))), "image_to_video_motion_first")


def _motion_transfer_prompt(shot: dict[str, Any], *, generate_audio: bool) -> CompiledPrompt:
    # The motion reference owns pose/timing/body movement. Keep guidance narrow so the
    # provider does not fight the reference performance.
    parts = [
        "Use the reference video as the performance and timing source.",
        "Preserve the approved creator identity from the reference image while following the source body motion, gesture timing, and facial performance naturally.",
        _sentence(shot.get("visual_direction")),
        _dialogue(shot, generate_audio),
        "Keep the result photorealistic and consistent from frame to frame.",
    ]
    return CompiledPrompt(_cap_words(" ".join(filter(None, parts))), "licensed_motion_transfer")


def _seedance_prompt(shot: dict[str, Any], *, generate_audio: bool) -> CompiledPrompt:
    # Seedance-style multimodal reference generation benefits from explicit but compact
    # creative direction. References still own identity/static details.
    purpose = _clean(shot.get("purpose")) or "UGC creator shot"
    visual = _clean(shot.get("visual_direction"))
    parts = [
        f"Shot objective: {purpose}.",
        f"Performance and camera: {visual}." if visual else "Performance and camera: natural handheld creator delivery with subtle realistic movement.",
        _dialogue(shot, generate_audio),
        "Reference media defines the creator identity and visual continuity; preserve those details consistently.",
        "Photorealistic casual social-video aesthetic, believable skin texture, stable anatomy, natural hands, coherent lighting, no unintended on-screen text.",
    ]
    return CompiledPrompt(_cap_words(" ".join(filter(None, parts))), "multimodal_reference_directed")


def compile_shot_prompt(
    shot: dict[str, Any],
    *,
    model_id: str,
    generate_audio: bool = False,
) -> CompiledPrompt:
    """Compile one provider-neutral shot into a concise model-aware prompt."""
    model = model_id.lower()

    if "motion-control" in model or "motion_control" in model:
        return _motion_transfer_prompt(shot, generate_audio=generate_audio)

    if "seedance" in model and ("reference" in model or "2.5" in model or "2_5" in model):
        return _seedance_prompt(shot, generate_audio=generate_audio)

    if "image-to-video" in model or "image_to_video" in model or "kling" in model or "wan" in model:
        return _i2v_prompt(shot, generate_audio=generate_audio)

    # Conservative default: still use motion-first guidance because creator shots normally
    # arrive with a visual reference in this pipeline.
    return _i2v_prompt(shot, generate_audio=generate_audio)
