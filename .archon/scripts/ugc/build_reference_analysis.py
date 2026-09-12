#!/usr/bin/env python3
"""Compile factual video observations + semantic labels into ReferenceAnalysis.

This separation is intentional: ffmpeg can tell us where cuts occurred, but it cannot
truthfully decide that a shot is a creator reaction, app demo, or CTA. Those semantic
labels must come from a multimodal agent/human/provider step and are validated here.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

SHOT_TYPES = {"creator", "product_demo", "app_demo", "broll", "graphic", "transition"}


def _pacing(segments: list[dict[str, Any]]) -> str:
    durations = [float(x["end"]) - float(x["start"]) for x in segments if float(x["end"]) > float(x["start"])]
    if not durations:
        return "unknown"
    avg = sum(durations) / len(durations)
    if avg < 1.5:
        return f"rapid cuts; average observed segment {avg:.2f}s"
    if avg < 3.0:
        return f"brisk pacing; average observed segment {avg:.2f}s"
    if avg < 5.0:
        return f"moderate pacing; average observed segment {avg:.2f}s"
    return f"slow/held pacing; average observed segment {avg:.2f}s"


def build_reference_analysis(observation: dict[str, Any], semantics: dict[str, Any]) -> dict[str, Any]:
    if semantics.get("reference_id") != observation.get("id"):
        raise ValueError("semantic reference_id does not match observation id")

    segments = {item["id"]: item for item in observation.get("segments") or []}
    labels = semantics.get("beats") or []
    if not segments:
        raise ValueError("observation contains no segments")
    seen: set[str] = set()
    beats = []
    literal_allowed = observation.get("rights_mode") in {"licensed_performance_transfer", "owned_source"}

    for index, label in enumerate(labels, start=1):
        segment_id = label.get("segment_id")
        if segment_id not in segments:
            raise ValueError(f"semantic beat references unknown segment: {segment_id!r}")
        if segment_id in seen:
            raise ValueError(f"duplicate semantic label for segment: {segment_id}")
        if label.get("shot_type") not in SHOT_TYPES:
            raise ValueError(f"invalid shot_type: {label.get('shot_type')!r}")
        seen.add(segment_id)
        segment = segments[segment_id]
        beats.append({
            "id": f"beat-{index:03d}",
            "start": segment["start"],
            "end": segment["end"],
            "role": str(label.get("role") or "").strip(),
            "shot_type": label["shot_type"],
            "framing": label.get("framing"),
            "generic_motion": label.get("generic_motion"),
            "dialogue_function": label.get("dialogue_function"),
            "transition_out": label.get("transition_out"),
            "literal_motion_reference_allowed": literal_allowed,
        })

    missing = sorted(set(segments) - seen)
    if missing:
        raise ValueError(f"semantic enrichment must label every observed segment; missing: {', '.join(missing)}")

    dna = semantics.get("creative_dna") or {}
    required_dna = ["hook_mechanic", "structure", "cta_mechanic"]
    missing_dna = [field for field in required_dna if not dna.get(field)]
    if missing_dna:
        raise ValueError(f"semantic creative_dna missing: {', '.join(missing_dna)}")

    return {
        "id": observation["id"],
        "source_url": observation.get("source_path"),
        "rights_mode": observation["rights_mode"],
        "duration_seconds": observation["duration_seconds"],
        "transcript": observation.get("transcript"),
        "creative_dna": {
            "hook_mechanic": dna["hook_mechanic"],
            "structure": dna["structure"],
            "pacing": _pacing(list(segments.values())),
            "camera_language": dna.get("camera_language") or [],
            "editing_language": dna.get("editing_language") or [],
            "performance_style": dna.get("performance_style") or [],
            "cta_mechanic": dna["cta_mechanic"],
            "what_to_preserve": dna.get("what_to_preserve") or [],
            "what_to_change": dna.get("what_to_change") or [],
        },
        "beats": beats,
    }


def semantic_enrichment_prompt(observation: dict[str, Any]) -> str:
    """Build a compact prompt for a multimodal agent that can see the source/keyframes."""
    rights_mode = observation.get("rights_mode")
    segments = observation.get("segments") or []
    transcript = observation.get("transcript") or "(no transcript available)"
    lines = [
        "Analyze this short-form video as creative structure, not as content to copy verbatim.",
        f"Reference id: {observation.get('id')}",
        f"Rights mode: {rights_mode}",
        f"Duration: {observation.get('duration_seconds')}s; observed segments: {len(segments)}.",
        "For each observed segment, label role and shot_type from: creator, product_demo, app_demo, broll, graphic, transition.",
        "Describe only generic motion/performance and framing. Do not infer literal motion-transfer permission from visual content; rights_mode controls that separately.",
        "Extract hook mechanic, reusable structure, camera/editing language, performance style, CTA mechanic, what to preserve structurally, and what must change in a new creative.",
        "Return JSON matching reference-semantic-labels.schema.json and label every segment exactly once.",
        f"Transcript: {transcript[:4000]}",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("observation")
    parser.add_argument("--semantics", help="Semantic labels JSON")
    parser.add_argument("--out")
    parser.add_argument("--print-prompt", action="store_true")
    args = parser.parse_args()

    observation = json.loads(Path(args.observation).read_text(encoding="utf-8"))
    if args.print_prompt:
        print(semantic_enrichment_prompt(observation))
        return 0
    if not args.semantics or not args.out:
        parser.error("--semantics and --out are required unless --print-prompt is used")
    semantics = json.loads(Path(args.semantics).read_text(encoding="utf-8"))
    analysis = build_reference_analysis(observation, semantics)
    Path(args.out).write_text(json.dumps(analysis, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"reference_id": analysis["id"], "beats": len(analysis["beats"]), "rights_mode": analysis["rights_mode"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
