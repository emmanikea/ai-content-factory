#!/usr/bin/env python3
"""Compile a CreativeSpec shot into a provider-ready fal job.

This compiler never submits work. It creates the JSON consumed by
ugc-studio/providers/fal/render.mjs. A higher-level rights check must explicitly mark the
assets manifest `rights_approved: true`; live rendering separately requires spend approval.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

from model_router import route_shot
from prompt_compiler import compile_shot_prompt
from rights import enforce_reference_mode


def _duration(shot: dict[str, Any]) -> float:
    return max(0.0, float(shot["end"]) - float(shot["start"]))


def _whole_duration(seconds: float, low: int, high: int) -> int:
    return max(low, min(high, int(math.ceil(seconds))))


def compile_input(
    model_id: str,
    *,
    shot: dict[str, Any],
    assets: dict[str, Any],
    resolution: str,
    aspect_ratio: str,
    generate_audio: bool,
    prompt_text: str,
) -> dict[str, Any]:
    duration = _duration(shot)
    creator_image = assets.get("creator_image_url")

    if model_id == "alibaba/wan-3.0/image-to-video":
        if not creator_image:
            raise ValueError("Wan I2V requires assets.creator_image_url")
        return {
            "prompt": prompt_text,
            "resolution": resolution,
            "aspect_ratio": aspect_ratio,
            "duration": _whole_duration(duration, 1, 30),
            "audio": generate_audio,
            "enable_prompt_expansion": True,
            "enable_safety_checker": True,
            "start_image_url": creator_image,
            **({"end_image_url": assets["end_image_url"]} if assets.get("end_image_url") else {}),
        }

    if model_id in {
        "fal-ai/kling-video/v3/standard/image-to-video",
        "fal-ai/kling-video/v3/pro/image-to-video",
    }:
        if not creator_image:
            raise ValueError("Kling I2V requires assets.creator_image_url")
        return {
            "prompt": prompt_text,
            "start_image_url": creator_image,
            "duration": str(_whole_duration(duration, 3, 15)),
            "generate_audio": generate_audio,
            **({"end_image_url": assets["end_image_url"]} if assets.get("end_image_url") else {}),
        }

    if model_id == "fal-ai/kling-video/v3/standard/motion-control":
        if not creator_image or not assets.get("motion_video_url"):
            raise ValueError("Kling Motion requires creator_image_url and motion_video_url")
        return {
            "prompt": prompt_text,
            "image_url": creator_image,
            "video_url": assets["motion_video_url"],
            "keep_original_sound": bool(assets.get("keep_original_sound", False)),
            "character_orientation": assets.get("character_orientation", "video"),
        }

    if model_id == "bytedance/seedance-2.5/reference-to-video":
        image_urls = list(assets.get("image_urls") or ([] if not creator_image else [creator_image]))
        video_urls = list(assets.get("video_urls") or ([] if not assets.get("motion_video_url") else [assets["motion_video_url"]]))
        audio_urls = list(assets.get("audio_urls") or [])
        if not image_urls and not video_urls:
            raise ValueError("Seedance reference-to-video requires at least one image or video reference")
        return {
            "prompt": prompt_text,
            "task": "reference",
            "image_urls": image_urls,
            "video_urls": video_urls,
            "audio_urls": audio_urls,
            "resolution": resolution,
            "duration": str(_whole_duration(duration, 4, 30)),
            "aspect_ratio": aspect_ratio,
            "generate_audio": generate_audio,
            "bitrate_mode": assets.get("bitrate_mode", "standard"),
            **({"end_user_id": assets["end_user_id"]} if assets.get("end_user_id") else {}),
        }

    raise ValueError(f"No fal input compiler implemented for model {model_id!r}")


def build_job(spec: dict[str, Any], shot_id: str, assets: dict[str, Any]) -> dict[str, Any]:
    shot = next((item for item in spec.get("shots", []) if item.get("id") == shot_id), None)
    if not shot:
        raise ValueError(f"shot {shot_id!r} not found")

    if assets.get("rights_approved") is not True:
        raise ValueError("direct creator render blocked: assets.rights_approved must be true")

    if shot.get("source_type") == "creator_motion_transfer":
        decision = enforce_reference_mode(
            {"rights_mode": spec.get("rights_mode", "creative_dna_only")},
            "motion_transfer",
        )
        if not decision.allowed:
            raise ValueError("; ".join(decision.reasons))

    quality_tier = spec.get("quality_tier", "standard")
    resolution = spec.get("render_resolution", "720p")
    aspect_ratio = spec.get("aspect_ratio", "9:16")
    generate_audio = bool(spec.get("generate_native_audio", False))
    route = route_shot(
        shot,
        quality_tier=quality_tier,
        resolution=resolution,
        aspect_ratio=aspect_ratio,
        generate_audio=generate_audio,
    )
    if route["provider"] != "fal":
        raise ValueError(f"shot routes to {route['provider']!r}, not fal")

    model_id = route["model"]
    compiled_prompt = compile_shot_prompt(
        shot,
        model_id=model_id,
        generate_audio=generate_audio,
    )
    input_payload = compile_input(
        model_id,
        shot=shot,
        assets=assets,
        resolution=resolution,
        aspect_ratio=aspect_ratio,
        generate_audio=generate_audio,
        prompt_text=compiled_prompt.text,
    )
    return {
        "version": "1.0",
        "campaign_id": spec.get("campaign_id"),
        "concept_id": spec.get("concept_id"),
        "shot_id": shot_id,
        "provider": "fal",
        "model_id": model_id,
        "estimated_cost_usd": route["estimated_cost_usd"],
        "rights_approved": True,
        "approved_for_spend": False,
        "input": input_payload,
        "provenance": {
            "router_reason": route["reason"],
            "rights_mode": spec.get("rights_mode"),
            "creator_id": spec.get("creator_id"),
            "source_type": shot.get("source_type"),
            "rights_evidence": assets.get("rights_evidence"),
            "prompt_compiler_version": compiled_prompt.version,
            "prompt_strategy": compiled_prompt.strategy,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("spec")
    parser.add_argument("--shot", required=True)
    parser.add_argument("--assets", required=True, help="JSON file with creator/reference URLs and rights approval")
    parser.add_argument("--out")
    args = parser.parse_args()

    spec = json.loads(Path(args.spec).read_text(encoding="utf-8"))
    assets = json.loads(Path(args.assets).read_text(encoding="utf-8"))
    job = build_job(spec, args.shot, assets)
    text = json.dumps(job, indent=2)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
