#!/usr/bin/env python3
"""Generate provider-neutral CreativeSpec variants from campaign + ReferenceAnalysis.

This is deterministic variation planning, not an LLM copywriter. Hooks, CTAs and optional
role lines come from the campaign brief; reusable timing/roles come from ReferenceAnalysis.
The resulting specs can be ranked before any video spend.
"""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
from pathlib import Path
from typing import Any

SHOT_SOURCE_MAP = {
    "creator": "creator_generated",
    "app_demo": "app_capture",
    "product_demo": "product_capture",
    "broll": "broll_generated",
    "graphic": "graphic",
    "transition": "graphic",
}


def _choice_for_role(role_lines: dict[str, Any], role: str, variant_index: int) -> str | None:
    value = role_lines.get(role)
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, list) and value:
        return str(value[variant_index % len(value)])
    return None


def _variant_id(parts: tuple[str, ...]) -> str:
    digest = hashlib.sha1("|".join(parts).encode("utf-8")).hexdigest()[:10]
    return f"concept-{digest}"


def _source_type(shot_type: str, *, literal_motion: bool) -> str:
    if shot_type == "creator" and literal_motion:
        return "creator_motion_transfer"
    return SHOT_SOURCE_MAP[shot_type]


def _required_capabilities(source_type: str) -> list[str]:
    return {
        "creator_generated": ["image_to_video"],
        "creator_motion_transfer": ["motion_transfer"],
        "app_capture": ["app_capture"],
        "product_capture": [],
        "broll_generated": ["broll"],
        "graphic": [],
    }.get(source_type, [])


def generate_specs(campaign: dict[str, Any], reference: dict[str, Any]) -> list[dict[str, Any]]:
    beats = list(reference.get("beats") or [])
    if not beats:
        raise ValueError("ReferenceAnalysis contains no beats")
    literal_motion = bool(campaign.get("use_literal_motion", False))
    if literal_motion and reference.get("rights_mode") not in {"licensed_performance_transfer", "owned_source"}:
        raise ValueError("literal motion requested but reference rights_mode does not allow performance transfer")

    creators = list(campaign.get("creator_ids") or [])
    hooks = list(campaign.get("hook_options") or [])
    ctas = list(campaign.get("cta_options") or [])
    locations = list(campaign.get("locations") or ["canonical"])
    outfits = list(campaign.get("outfits") or ["canonical"])
    if not creators or not hooks or not ctas:
        raise ValueError("campaign requires creator_ids, hook_options, and cta_options")

    max_specs = int(campaign.get("max_specs", 24))
    reference_duration = float(reference.get("duration_seconds") or beats[-1]["end"])
    target_duration = float(campaign.get("target_duration_seconds") or reference_duration)
    scale = target_duration / reference_duration if reference_duration > 0 else 1.0
    role_lines = campaign.get("role_lines") or {}
    product = campaign.get("product") or {}
    specs = []

    combinations = itertools.product(creators, hooks, ctas, locations, outfits)
    for variant_index, (creator_id, hook, cta, location, outfit) in enumerate(combinations):
        if len(specs) >= max_specs:
            break
        concept_id = _variant_id((campaign["campaign_id"], reference["id"], creator_id, hook, cta, location, outfit))
        shots = []
        spoken_lines: list[str] = []
        creator_seen = 0
        for index, beat in enumerate(beats, start=1):
            shot_type = beat["shot_type"]
            if shot_type not in SHOT_SOURCE_MAP:
                raise ValueError(f"unsupported reference shot_type: {shot_type!r}")
            source_type = _source_type(shot_type, literal_motion=literal_motion)
            role = str(beat.get("role") or f"beat {index}")
            role_lower = role.lower()
            dialogue = None
            if shot_type == "creator":
                creator_seen += 1
                if "hook" in role_lower or creator_seen == 1:
                    dialogue = hook
                elif "cta" in role_lower or index == len(beats):
                    dialogue = cta
                else:
                    dialogue = _choice_for_role(role_lines, role, variant_index)
                if dialogue:
                    spoken_lines.append(dialogue)

            visual_bits = []
            if beat.get("framing"):
                visual_bits.append(str(beat["framing"]))
            if beat.get("generic_motion"):
                visual_bits.append(str(beat["generic_motion"]))
            if shot_type == "creator":
                visual_bits.append(f"Setting: {location}.")
                visual_bits.append(f"Wardrobe: {outfit}.")
                visual_bits.append("Natural phone-shot UGC performance; keep the creator recognizable and performance understated.")
            elif shot_type == "app_demo":
                visual_bits.append("Use the real app UI capture; do not reconstruct interface elements with a generative model.")

            capture_script = None
            if shot_type == "app_demo":
                capture_script = campaign.get("app_capture_script")
            elif shot_type == "product_demo":
                capture_script = campaign.get("product_capture_script")

            start = round(float(beat["start"]) * scale, 3)
            end = round(float(beat["end"]) * scale, 3)
            shots.append({
                "id": f"s{index}",
                "start": start,
                "end": end,
                "source_type": source_type,
                "purpose": role,
                "dialogue": dialogue,
                "visual_direction": " ".join(visual_bits) if visual_bits else None,
                "capture_script": capture_script,
                "motion_reference_id": reference["id"] if source_type == "creator_motion_transfer" else None,
                "asset_reference_ids": [],
                "provider_preference": None,
                "provider_fallback": None,
                "required_capabilities": _required_capabilities(source_type),
            })

        dna = reference.get("creative_dna") or {}
        specs.append({
            "version": "1.0",
            "campaign_id": campaign["campaign_id"],
            "concept_id": concept_id,
            "reference_id": reference["id"],
            "format": "custom",
            "duration_seconds": round(target_duration, 3),
            "aspect_ratio": "9:16",
            "hook": hook,
            "angle": campaign.get("angle") or str(dna.get("hook_mechanic") or "reference-informed UGC"),
            "script": " ".join(spoken_lines),
            "creator_id": creator_id,
            "rights_mode": reference["rights_mode"],
            "language": campaign.get("language", "en"),
            "cta": cta,
            "caption_style": "clean social subtitles",
            "quality_tier": campaign.get("quality_tier", "standard"),
            "max_render_cost_usd": campaign.get("max_render_cost_usd"),
            "tags": [
                f"product:{product.get('id', 'unknown')}",
                f"platform:{campaign.get('platform', 'unknown')}",
                f"location:{location}",
                f"outfit:{outfit}",
                "reference-informed",
            ],
            "shots": shots,
        })
    return specs


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate CreativeSpec variants without rendering media")
    parser.add_argument("campaign")
    parser.add_argument("reference_analysis")
    parser.add_argument("--out", required=True, help="Output JSON array of CreativeSpecs")
    parser.add_argument("--split-dir", help="Optional directory to write one JSON file per concept")
    args = parser.parse_args()

    campaign = json.loads(Path(args.campaign).read_text(encoding="utf-8"))
    reference = json.loads(Path(args.reference_analysis).read_text(encoding="utf-8"))
    specs = generate_specs(campaign, reference)
    Path(args.out).write_text(json.dumps(specs, indent=2) + "\n", encoding="utf-8")
    if args.split_dir:
        split_dir = Path(args.split_dir)
        split_dir.mkdir(parents=True, exist_ok=True)
        for spec in specs:
            (split_dir / f"{spec['concept_id']}.json").write_text(json.dumps(spec, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"campaign_id": campaign["campaign_id"], "spec_count": len(specs), "output": args.out}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
