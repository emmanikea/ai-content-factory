#!/usr/bin/env python3
"""Direct-model router for UGC Studio.

Reads ugc-studio/providers/model-registry.json and chooses a route by capability,
quality tier, and estimated usable cost. Higgsfield is excluded unless explicitly enabled.

This module only plans. It never submits a paid job.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_REGISTRY = REPO_ROOT / "ugc-studio" / "providers" / "model-registry.json"

RESOLUTION_DIMS = {
    ("480p", "9:16"): (480, 864),
    ("480p", "16:9"): (864, 480),
    ("480p", "1:1"): (480, 480),
    ("720p", "9:16"): (720, 1280),
    ("720p", "16:9"): (1280, 720),
    ("720p", "1:1"): (720, 720),
    ("1080p", "9:16"): (1080, 1920),
    ("1080p", "16:9"): (1920, 1080),
    ("1080p", "1:1"): (1080, 1080),
}


@dataclass(frozen=True)
class Candidate:
    provider: str
    model: str
    quality: float
    cost: float
    capability: str
    source: str | None
    kind: str
    recommended_for: tuple[str, ...]


def load_registry(path: Path = DEFAULT_REGISTRY) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def estimate_model_cost(
    model: dict[str, Any],
    *,
    duration_seconds: float,
    resolution: str = "720p",
    aspect_ratio: str = "9:16",
    generate_audio: bool = False,
    voice_control: bool = False,
    reference_video_seconds: float = 0.0,
) -> float:
    cost = model.get("cost_model") or {}
    cost_type = cost.get("type")

    if cost_type == "fixed":
        return round(float(cost.get("usd", 0.0)), 4)

    if cost_type == "per_second":
        return round(duration_seconds * float(cost["rate"]), 4)

    if cost_type == "per_second_by_resolution":
        rates = cost.get("rates") or {}
        rate = float(rates[resolution])
        return round(duration_seconds * rate, 4)

    if cost_type == "per_second_audio_toggle":
        if voice_control:
            rate = float(cost["voice_control"])
        elif generate_audio:
            rate = float(cost["audio_on"])
        else:
            rate = float(cost["audio_off"])
        return round(duration_seconds * rate, 4)

    if cost_type == "token_formula":
        width, height = RESOLUTION_DIMS[(resolution, aspect_ratio)]
        fps = float(cost.get("fps", 24))
        total_seconds = duration_seconds + max(0.0, reference_video_seconds)
        tokens = (width * height * total_seconds * fps) / 1024
        usd = (tokens / 1000) * float(cost["usd_per_1000_tokens"])
        if reference_video_seconds > 0:
            usd *= float(cost.get("video_reference_multiplier", 1.0))
        return round(usd, 4)

    if cost_type == "compute_metered":
        raise ValueError("self-host compute rate has not been benchmarked yet")

    raise ValueError(f"unsupported cost model: {cost_type!r}")


def _models(registry: dict[str, Any], *, allow_higgsfield: bool, allow_selfhost: bool):
    for provider in registry.get("providers", []):
        provider_id = provider["id"]
        kind = provider.get("kind", "unknown")
        if provider_id == "higgsfield" and not allow_higgsfield:
            continue
        if kind == "self_hosted" and not allow_selfhost:
            continue
        if not provider.get("enabled_by_default", False) and provider_id not in {"higgsfield", "selfhost-wan"}:
            continue
        for model in provider.get("models", []):
            yield provider_id, kind, model


def candidates_for(
    capability: str,
    *,
    duration_seconds: float,
    resolution: str,
    aspect_ratio: str,
    quality_tier: str,
    generate_audio: bool,
    reference_video_seconds: float,
    allow_higgsfield: bool = False,
    allow_selfhost: bool = False,
    registry: dict[str, Any] | None = None,
) -> list[Candidate]:
    registry = registry or load_registry()
    out: list[Candidate] = []

    for provider_id, kind, model in _models(
        registry,
        allow_higgsfield=allow_higgsfield,
        allow_selfhost=allow_selfhost,
    ):
        if capability not in set(model.get("capabilities") or []):
            continue
        try:
            cost = estimate_model_cost(
                model,
                duration_seconds=duration_seconds,
                resolution=resolution,
                aspect_ratio=aspect_ratio,
                generate_audio=generate_audio,
                reference_video_seconds=reference_video_seconds,
            )
        except ValueError:
            continue
        out.append(
            Candidate(
                provider=provider_id,
                model=model["id"],
                quality=float(model.get("quality_score", 0.5)),
                cost=cost,
                capability=capability,
                source=model.get("source"),
                kind=kind,
                recommended_for=tuple(model.get("recommended_for") or ()),
            )
        )

    # Respect explicitly curated tiers when at least one eligible model declares itself
    # suitable for the requested tier. This prevents a standard job from silently drifting
    # into a premium model just because its static quality score is a few points higher.
    tier_matches = [c for c in out if quality_tier in c.recommended_for]
    if tier_matches:
        out = tier_matches

    if quality_tier == "draft":
        out.sort(key=lambda c: (c.cost, -c.quality))
    elif quality_tier == "premium":
        out.sort(key=lambda c: (-c.quality, c.cost))
    else:
        out.sort(key=lambda c: -(c.quality - min(c.cost, 10.0) * 0.06))
    return out


def infer_capability(source_type: str, quality_tier: str) -> str | None:
    if source_type == "creator_motion_transfer":
        return "motion_transfer"
    if source_type == "creator_generated":
        return "creator_video" if quality_tier != "draft" else "image_to_video"
    if source_type == "broll_generated":
        return "image_to_video"
    if source_type == "creator_lipsync":
        return None
    return None


def route_shot(
    shot: dict[str, Any],
    *,
    quality_tier: str,
    resolution: str = "720p",
    aspect_ratio: str = "9:16",
    generate_audio: bool = False,
    allow_higgsfield: bool = False,
    allow_selfhost: bool = False,
    registry: dict[str, Any] | None = None,
) -> dict[str, Any]:
    source_type = shot["source_type"]
    duration = max(0.0, float(shot["end"]) - float(shot["start"]))

    deterministic = {
        "app_capture": ("local-playwright", "playwright-capture", 0.0, "real app capture"),
        "product_capture": ("local", "owned-product-capture", 0.0, "owned product capture"),
        "owned_media": ("local", "owned-asset", 0.0, "reuse owned media"),
        "graphic": ("local-remotion", "remotion-ffmpeg", 0.0, "deterministic composition"),
        "creator_lipsync": ("local", "lipsync-worker", 0.0, "local/open lip-sync lane"),
    }
    if source_type in deterministic:
        provider, model, cost, reason = deterministic[source_type]
        return {
            "provider": provider,
            "model": model,
            "estimated_cost_usd": cost,
            "reason": reason,
            "alternatives": [],
        }

    capability = infer_capability(source_type, quality_tier)
    if not capability:
        raise ValueError(f"cannot infer capability for {source_type!r}")

    reference_seconds = duration if source_type == "creator_motion_transfer" else 0.0
    choices = candidates_for(
        capability,
        duration_seconds=duration,
        resolution=resolution,
        aspect_ratio=aspect_ratio,
        quality_tier=quality_tier,
        generate_audio=generate_audio,
        reference_video_seconds=reference_seconds,
        allow_higgsfield=allow_higgsfield,
        allow_selfhost=allow_selfhost,
        registry=registry,
    )
    if not choices:
        raise ValueError(f"no enabled model supports {capability!r}")

    chosen = choices[0]
    return {
        "provider": chosen.provider,
        "model": chosen.model,
        "estimated_cost_usd": chosen.cost,
        "reason": f"{quality_tier} direct route for {capability}; quality={chosen.quality:.2f}",
        "source": chosen.source,
        "alternatives": [
            {
                "provider": c.provider,
                "model": c.model,
                "estimated_cost_usd": c.cost,
                "quality": c.quality,
            }
            for c in choices[1:4]
        ],
    }


def plan_spec(spec: dict[str, Any], *, allow_higgsfield: bool = False, allow_selfhost: bool = False) -> dict[str, Any]:
    quality_tier = spec.get("quality_tier", "standard")
    aspect_ratio = spec.get("aspect_ratio", "9:16")
    resolution = spec.get("render_resolution", "720p")
    generate_audio = bool(spec.get("generate_native_audio", False))
    items = []
    total = 0.0

    for shot in spec.get("shots", []):
        route = route_shot(
            shot,
            quality_tier=quality_tier,
            resolution=resolution,
            aspect_ratio=aspect_ratio,
            generate_audio=generate_audio,
            allow_higgsfield=allow_higgsfield,
            allow_selfhost=allow_selfhost,
        )
        duration = round(float(shot["end"]) - float(shot["start"]), 3)
        total += float(route["estimated_cost_usd"])
        items.append({
            "shot_id": shot["id"],
            "source_type": shot["source_type"],
            "duration_seconds": duration,
            **route,
        })

    max_cost = spec.get("max_render_cost_usd")
    blocked = max_cost is not None and total > float(max_cost)
    return {
        "concept_id": spec.get("concept_id"),
        "quality_tier": quality_tier,
        "resolution": resolution,
        "aspect_ratio": aspect_ratio,
        "allow_higgsfield_fallback": allow_higgsfield,
        "allow_selfhost": allow_selfhost,
        "items": items,
        "estimated_total_usd": round(total, 4),
        "blocked": blocked,
        "block_reason": f"estimated cost ${total:.2f} exceeds cap ${float(max_cost):.2f}" if blocked else None,
        "dry_run": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Plan direct-model UGC rendering without spending money.")
    parser.add_argument("spec", help="CreativeSpec JSON")
    parser.add_argument("--allow-higgsfield", action="store_true", help="Permit Higgsfield fallback candidates")
    parser.add_argument("--allow-selfhost", action="store_true", help="Permit configured self-host candidates")
    parser.add_argument("--out")
    args = parser.parse_args()

    spec = json.loads(Path(args.spec).read_text(encoding="utf-8"))
    result = plan_spec(
        spec,
        allow_higgsfield=args.allow_higgsfield,
        allow_selfhost=args.allow_selfhost,
    )
    text = json.dumps(result, indent=2)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
    print(text)
    return 1 if result["blocked"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
