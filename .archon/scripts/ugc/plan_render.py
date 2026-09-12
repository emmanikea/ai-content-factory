#!/usr/bin/env python3
"""Dry-run render planner for CreativeSpec JSON.

This does not submit media jobs. It converts a CreativeSpec into an explainable per-shot
plan and cost estimate so humans can approve spend before generation.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


DETERMINISTIC = {
    "app_capture": ("local", "playwright", 0.0, "real app capture"),
    "product_capture": ("local", "capture", 0.0, "owned product capture"),
    "owned_media": ("local", "asset", 0.0, "reuse owned media"),
    "graphic": ("local", "remotion", 0.0, "deterministic composition"),
}

# Placeholder routing table. Costs are illustrative configuration values, not billing facts.
ROUTES = {
    "creator_generated": [
        ("higgsfield", "configured_ugc_model", 1.50, 0.88),
        ("reference-video-api", "premium_reference_video", 2.50, 0.94),
    ],
    "creator_motion_transfer": [
        ("motion-api", "motion_transfer_standard", 1.25, 0.86),
        ("reference-video-api", "motion_transfer_premium", 2.25, 0.93),
    ],
    "creator_lipsync": [
        ("local", "lipsync_worker", 0.20, 0.82),
        ("higgsfield", "configured_ugc_model", 1.50, 0.90),
    ],
    "broll_generated": [
        ("higgsfield", "configured_video_model", 1.00, 0.86),
        ("reference-video-api", "premium_video", 2.00, 0.92),
    ],
}


def choose_route(source_type: str, quality_tier: str) -> tuple[str, str, float, str]:
    if source_type in DETERMINISTIC:
        return DETERMINISTIC[source_type]

    options = ROUTES.get(source_type)
    if not options:
        raise ValueError(f"no route configured for source_type={source_type!r}")

    # Draft prefers lowest cost. Premium prefers quality. Standard balances both.
    if quality_tier == "draft":
        provider, model, cost, quality = min(options, key=lambda x: x[2])
    elif quality_tier == "premium":
        provider, model, cost, quality = max(options, key=lambda x: x[3])
    else:
        provider, model, cost, quality = max(options, key=lambda x: x[3] - (x[2] * 0.08))
    return provider, model, cost, f"{quality_tier} route; quality={quality:.2f}"


def plan(spec: dict) -> dict:
    quality_tier = spec.get("quality_tier", "standard")
    items = []
    total = 0.0

    for shot in spec.get("shots", []):
        provider, model, cost, reason = choose_route(shot["source_type"], quality_tier)
        duration = max(0.0, float(shot["end"]) - float(shot["start"]))
        # Current placeholder cost is per planned shot. Provider adapters will replace this
        # with real provider quotes once connected.
        estimate = round(cost, 2)
        total += estimate
        items.append({
            "shot_id": shot["id"],
            "source_type": shot["source_type"],
            "duration_seconds": round(duration, 2),
            "provider": provider,
            "model": model,
            "estimated_cost_usd": estimate,
            "reason": reason,
            "status": "planned",
        })

    max_cost = spec.get("max_render_cost_usd")
    blocked = max_cost is not None and total > float(max_cost)
    return {
        "concept_id": spec.get("concept_id"),
        "quality_tier": quality_tier,
        "items": items,
        "estimated_total_usd": round(total, 2),
        "blocked": blocked,
        "block_reason": (
            f"estimated cost ${total:.2f} exceeds cap ${float(max_cost):.2f}"
            if blocked else None
        ),
        "dry_run": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("spec", help="Path to CreativeSpec JSON")
    parser.add_argument("--out", help="Optional output path")
    args = parser.parse_args()

    spec = json.loads(Path(args.spec).read_text(encoding="utf-8"))
    result = plan(spec)
    text = json.dumps(result, indent=2)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
    print(text)
    return 1 if result["blocked"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
