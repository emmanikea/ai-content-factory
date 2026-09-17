#!/usr/bin/env python3
"""Build comparable no-spend provider jobs for one creator-generated CreativeSpec shot.

V1 deliberately benchmarks only creator image-to-video. Motion/performance-transfer semantics
are not equivalent enough across providers to call them apples-to-apples yet.

The compiler never submits media and never flips spend approval. Hosted providers that need
an HTTPS source are marked unavailable when the approved asset is local-only. Google jobs are
marked unavailable when the approved asset is remote-only; this module never fetches arbitrary
creator URLs just to make a benchmark possible.
"""
from __future__ import annotations

import argparse
import base64
import json
import mimetypes
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from compare_provider_preflight import compare_jobs
from prompt_compiler import compile_shot_prompt

BENCHMARK_VERSION = "1.0"
PROFILE = "native_av_i2v"
RESOLUTION = "720p"
ASPECT_RATIO = "9:16"

FAL_MODEL = "alibaba/wan-3.0/image-to-video"
FAL_RATE_720P = 0.10
FAL_PRICE_CHECKED_AT = "2026-09-12"
FAL_PRICE_SOURCE = "https://fal.ai/models/alibaba/wan-3.0/image-to-video"

OPENROUTER_MODEL = "bytedance/seedance-2.0-fast"
OPENROUTER_PREVIEW_RATE = 0.04035
OPENROUTER_PRICE_CHECKED_AT = "2026-09-17"
OPENROUTER_PRICE_SOURCE = "https://openrouter.ai/bytedance/seedance-2.0-fast"

GOOGLE_VEO_MODEL = "veo-3.1-lite-generate-preview"
GOOGLE_VEO_RATE_720P = 0.05
GOOGLE_VEO_PRICE_CHECKED_AT = "2026-09-17"
GOOGLE_VEO_PRICE_SOURCE = "https://ai.google.dev/gemini-api/docs/pricing"

GOOGLE_OMNI_MODEL = "gemini-omni-1.1-flash"
GOOGLE_OMNI_OUTPUT_RATE_720P = 0.10
GOOGLE_OMNI_PRICE_CHECKED_AT = "2026-09-17"
GOOGLE_OMNI_PRICE_SOURCE = "https://ai.google.dev/gemini-api/docs/pricing"


def _is_https(value: str | None) -> bool:
    if not value:
        return False
    parsed = urlparse(str(value))
    return parsed.scheme.lower() == "https" and bool(parsed.netloc)


def _target_duration(seconds: float) -> int:
    if seconds <= 0:
        raise ValueError("shot duration must be positive")
    for candidate in (4, 6, 8):
        if seconds <= candidate:
            return candidate
    raise ValueError("first cross-provider benchmark supports creator shots up to 8 seconds")


def _shot(spec: dict[str, Any], shot_id: str) -> dict[str, Any]:
    shot = next((x for x in spec.get("shots") or [] if x.get("id") == shot_id), None)
    if not shot:
        raise ValueError(f"shot {shot_id!r} not found")
    if shot.get("source_type") != "creator_generated":
        raise ValueError(
            "first comparable benchmark only supports source_type='creator_generated'; "
            "motion-transfer/reference-video semantics differ across providers"
        )
    return shot


def _decode_b64(value: str) -> bytes:
    try:
        return base64.b64decode(value, validate=True)
    except Exception as exc:  # binascii.Error differs by Python version
        raise ValueError("assets.creator_image_base64 is not valid base64") from exc


def _local_image(
    assets: dict[str, Any],
    *,
    assets_base_dir: Path,
) -> tuple[str | None, str | None, str | None]:
    """Return (base64, mime_type, source_description) without remote fetching."""
    explicit = assets.get("creator_image_base64")
    if explicit:
        _decode_b64(str(explicit))
        mime = str(assets.get("creator_image_mime_type") or "image/jpeg")
        if not mime.startswith("image/"):
            raise ValueError("creator_image_mime_type must be an image MIME type")
        return str(explicit), mime, "assets.creator_image_base64"

    candidates = [assets.get("creator_image_local_path"), assets.get("creator_image_uri")]
    for raw in candidates:
        if not raw or _is_https(str(raw)):
            continue
        path = Path(str(raw)).expanduser()
        if not path.is_absolute():
            path = (assets_base_dir / path).resolve()
        if not path.is_file():
            continue
        data = path.read_bytes()
        mime = str(assets.get("creator_image_mime_type") or mimetypes.guess_type(path.name)[0] or "image/jpeg")
        if not mime.startswith("image/"):
            raise ValueError(f"local creator asset is not recognized as an image: {path}")
        return base64.b64encode(data).decode("ascii"), mime, str(path)
    return None, None, None


def _hosted_image_url(assets: dict[str, Any]) -> str | None:
    for key in ("creator_image_url", "creator_image_uri"):
        value = assets.get(key)
        if _is_https(str(value) if value else None):
            return str(value)
    return None


def _common_provenance(
    spec: dict[str, Any],
    shot: dict[str, Any],
    assets: dict[str, Any],
    *,
    target_duration: int,
    prompt_version: str,
    prompt_strategy: str,
) -> dict[str, Any]:
    return {
        "benchmark_version": BENCHMARK_VERSION,
        "benchmark_profile": PROFILE,
        "campaign_id": spec.get("campaign_id"),
        "concept_id": spec.get("concept_id"),
        "shot_id": shot.get("id"),
        "creator_id": spec.get("creator_id"),
        "source_type": shot.get("source_type"),
        "target_duration_seconds": target_duration,
        "resolution": RESOLUTION,
        "aspect_ratio": ASPECT_RATIO,
        "generate_native_audio": True,
        "rights_mode": spec.get("rights_mode"),
        "rights_evidence": assets.get("rights_evidence"),
        "rights_decision": assets.get("rights_decision"),
        "creator_image_id": assets.get("creator_image_id"),
        "prompt_compiler_version": prompt_version,
        "prompt_strategy": prompt_strategy,
    }


def _fal_job(
    spec: dict[str, Any],
    shot: dict[str, Any],
    assets: dict[str, Any],
    *,
    target_duration: int,
    image_url: str,
    prompt: str,
    prompt_version: str,
    prompt_strategy: str,
) -> dict[str, Any]:
    estimated = round(target_duration * FAL_RATE_720P, 4)
    return {
        "version": "1.0",
        "campaign_id": spec.get("campaign_id"),
        "concept_id": spec.get("concept_id"),
        "shot_id": shot["id"],
        "provider": "fal",
        "model_id": FAL_MODEL,
        "estimated_cost_usd": estimated,
        "max_provider_cost_usd": estimated,
        "rights_approved": True,
        "approved_for_spend": False,
        "input": {
            "prompt": prompt,
            "resolution": RESOLUTION,
            "aspect_ratio": ASPECT_RATIO,
            "duration": target_duration,
            "audio": True,
            "enable_prompt_expansion": True,
            "enable_safety_checker": True,
            "start_image_url": image_url,
        },
        "provenance": {
            **_common_provenance(spec, shot, assets, target_duration=target_duration, prompt_version=prompt_version, prompt_strategy=prompt_strategy),
            "pricing_checked_at": FAL_PRICE_CHECKED_AT,
            "pricing_source": FAL_PRICE_SOURCE,
            "cost_evidence_type": "configured_provider_formula",
        },
    }


def _openrouter_job(
    spec: dict[str, Any],
    shot: dict[str, Any],
    assets: dict[str, Any],
    *,
    target_duration: int,
    image_url: str,
    prompt: str,
    prompt_version: str,
    prompt_strategy: str,
) -> dict[str, Any]:
    expected = round(target_duration * OPENROUTER_PREVIEW_RATE, 4)
    return {
        "version": "1.0",
        "campaign_id": spec.get("campaign_id"),
        "concept_id": spec.get("concept_id"),
        "shot_id": shot["id"],
        "provider": "openrouter",
        "expected_cost_usd": expected,
        "max_provider_cost_usd": round(expected * 1.25, 4),
        "rights_approved": True,
        "approved_for_spend": False,
        "input": {
            "model": OPENROUTER_MODEL,
            "prompt": prompt,
            "duration": target_duration,
            "resolution": RESOLUTION,
            "aspect_ratio": ASPECT_RATIO,
            "generate_audio": True,
            "frame_images": [
                {
                    "type": "image_url",
                    "image_url": {"url": image_url},
                    "frame_type": "first_frame",
                }
            ],
        },
        "provenance": {
            **_common_provenance(spec, shot, assets, target_duration=target_duration, prompt_version=prompt_version, prompt_strategy=prompt_strategy),
            "pricing_checked_at": OPENROUTER_PRICE_CHECKED_AT,
            "pricing_source": OPENROUTER_PRICE_SOURCE,
            "preview_rate_usd_per_second": OPENROUTER_PREVIEW_RATE,
            "cost_evidence_type": "caller_preview_from_current_list_price",
            "actual_cost_source": "OpenRouter completed usage.cost",
        },
    }


def _google_veo_job(
    spec: dict[str, Any],
    shot: dict[str, Any],
    assets: dict[str, Any],
    *,
    target_duration: int,
    image_b64: str,
    image_mime: str,
    prompt: str,
    prompt_version: str,
    prompt_strategy: str,
) -> dict[str, Any]:
    estimated = round(target_duration * GOOGLE_VEO_RATE_720P, 4)
    return {
        "version": "1.0",
        "campaign_id": spec.get("campaign_id"),
        "concept_id": spec.get("concept_id"),
        "shot_id": shot["id"],
        "provider": "google-veo",
        "model": GOOGLE_VEO_MODEL,
        "rights_approved": True,
        "approved_for_spend": False,
        "max_provider_cost_usd": estimated,
        "request": {
            "instances": [
                {
                    "prompt": prompt,
                    "image": {"inlineData": {"mimeType": image_mime, "data": image_b64}},
                }
            ],
            "parameters": {
                "aspectRatio": ASPECT_RATIO,
                "durationSeconds": target_duration,
                "resolution": RESOLUTION,
                "numberOfVideos": 1,
            },
        },
        "provenance": {
            **_common_provenance(spec, shot, assets, target_duration=target_duration, prompt_version=prompt_version, prompt_strategy=prompt_strategy),
            "pricing_checked_at": GOOGLE_VEO_PRICE_CHECKED_AT,
            "pricing_source": GOOGLE_VEO_PRICE_SOURCE,
            "rate_usd_per_second": GOOGLE_VEO_RATE_720P,
            "cost_evidence_type": "official_rate_formula",
        },
    }


def _google_omni_job(
    spec: dict[str, Any],
    shot: dict[str, Any],
    assets: dict[str, Any],
    *,
    target_duration: int,
    image_b64: str,
    image_mime: str,
    prompt: str,
    prompt_version: str,
    prompt_strategy: str,
) -> dict[str, Any]:
    expected = round(target_duration * GOOGLE_OMNI_OUTPUT_RATE_720P, 4)
    omni_prompt = f"{prompt} Single continuous shot. Single unbroken scene. No scene cuts."
    return {
        "version": "1.0",
        "campaign_id": spec.get("campaign_id"),
        "concept_id": spec.get("concept_id"),
        "shot_id": shot["id"],
        "provider": "google-omni",
        "model": GOOGLE_OMNI_MODEL,
        "expected_duration_seconds": target_duration,
        "rights_approved": True,
        "approved_for_spend": False,
        "max_provider_cost_usd": round(expected * 1.25 + 0.02, 4),
        "request": {
            "model": GOOGLE_OMNI_MODEL,
            "input": [
                {"type": "image", "data": image_b64, "mime_type": image_mime},
                {"type": "text", "text": omni_prompt},
            ],
            "response_format": {
                "type": "video",
                "delivery": "uri",
                "aspect_ratio": ASPECT_RATIO,
                "resolution": RESOLUTION,
            },
            "generation_config": {"video_config": {"task": "image_to_video"}},
            "background": False,
            "store": False,
            "stream": False,
        },
        "provenance": {
            **_common_provenance(spec, shot, assets, target_duration=target_duration, prompt_version=prompt_version, prompt_strategy=prompt_strategy),
            "pricing_checked_at": GOOGLE_OMNI_PRICE_CHECKED_AT,
            "pricing_source": GOOGLE_OMNI_PRICE_SOURCE,
            "approx_output_rate_usd_per_second": GOOGLE_OMNI_OUTPUT_RATE_720P,
            "cost_evidence_type": "official_effective_output_rate_approximation",
            "cost_note": "Input tokens are billed separately and actual output duration/token use can differ.",
        },
    }


def build_benchmark(
    spec: dict[str, Any],
    shot_id: str,
    assets: dict[str, Any],
    *,
    assets_base_dir: Path | None = None,
) -> dict[str, Any]:
    if assets.get("rights_approved") is not True:
        raise ValueError("benchmark blocked: assets.rights_approved must be true")

    shot = _shot(spec, shot_id)
    duration = float(shot["end"]) - float(shot["start"])
    target_duration = _target_duration(duration)
    base_dir = (assets_base_dir or Path.cwd()).resolve()
    image_url = _hosted_image_url(assets)
    image_b64, image_mime, local_source = _local_image(assets, assets_base_dir=base_dir)

    base_prompt = compile_shot_prompt(shot, model_id=FAL_MODEL, generate_audio=True)
    providers: dict[str, dict[str, Any]] = {}

    if image_url:
        providers["fal-wan"] = {
            "available": True,
            "job": _fal_job(
                spec, shot, assets, target_duration=target_duration, image_url=image_url,
                prompt=base_prompt.text, prompt_version=base_prompt.version, prompt_strategy=base_prompt.strategy,
            ),
        }
        providers["openrouter-seedance-fast"] = {
            "available": True,
            "job": _openrouter_job(
                spec, shot, assets, target_duration=target_duration, image_url=image_url,
                prompt=base_prompt.text, prompt_version=base_prompt.version, prompt_strategy=base_prompt.strategy,
            ),
        }
    else:
        reason = "requires an approved hosted HTTPS creator_image_url; local assets are not silently uploaded"
        providers["fal-wan"] = {"available": False, "reason": reason}
        providers["openrouter-seedance-fast"] = {"available": False, "reason": reason}

    if image_b64 and image_mime:
        providers["google-veo-lite"] = {
            "available": True,
            "job": _google_veo_job(
                spec, shot, assets, target_duration=target_duration, image_b64=image_b64, image_mime=image_mime,
                prompt=base_prompt.text, prompt_version=base_prompt.version, prompt_strategy=base_prompt.strategy,
            ),
        }
        providers["google-omni"] = {
            "available": True,
            "job": _google_omni_job(
                spec, shot, assets, target_duration=target_duration, image_b64=image_b64, image_mime=image_mime,
                prompt=base_prompt.text, prompt_version=base_prompt.version, prompt_strategy=base_prompt.strategy,
            ),
        }
    else:
        reason = "requires approved local/base64 creator bytes; arbitrary remote creator URLs are not fetched"
        providers["google-veo-lite"] = {"available": False, "reason": reason}
        providers["google-omni"] = {"available": False, "reason": reason}

    comparison_jobs = [
        (name, item["job"])
        for name, item in providers.items()
        if item.get("available") is True
    ]
    offline_comparison = compare_jobs(comparison_jobs, network=False) if comparison_jobs else None

    return {
        "version": BENCHMARK_VERSION,
        "profile": PROFILE,
        "campaign_id": spec.get("campaign_id"),
        "concept_id": spec.get("concept_id"),
        "shot_id": shot_id,
        "original_duration_seconds": round(duration, 3),
        "target_duration_seconds": target_duration,
        "resolution": RESOLUTION,
        "aspect_ratio": ASPECT_RATIO,
        "generate_native_audio": True,
        "rights_approved": True,
        "approved_for_spend": False,
        "creator_asset": {
            "creator_image_id": assets.get("creator_image_id"),
            "hosted_https_available": bool(image_url),
            "local_or_base64_available": bool(image_b64),
            "local_source": local_source,
        },
        "providers": providers,
        "offline_comparison": offline_comparison,
        "warning": (
            "All generated jobs are spend-disabled. Cost order is not a provider recommendation; "
            "run equivalent QA and compare cost per usable approved second before routing automatically."
        ),
    }


def write_bundle(bundle: dict[str, Any], outdir: Path) -> None:
    outdir.mkdir(parents=True, exist_ok=True)
    for name, item in bundle["providers"].items():
        if item.get("available") is True:
            (outdir / f"{name}.job.json").write_text(json.dumps(item["job"], indent=2) + "\n", encoding="utf-8")
    (outdir / "benchmark-manifest.json").write_text(json.dumps(bundle, indent=2) + "\n", encoding="utf-8")
    if bundle.get("offline_comparison") is not None:
        (outdir / "provider-comparison.json").write_text(
            json.dumps(bundle["offline_comparison"], indent=2) + "\n",
            encoding="utf-8",
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Build comparable no-spend creator I2V provider jobs")
    parser.add_argument("spec")
    parser.add_argument("--shot", required=True)
    parser.add_argument("--assets", required=True)
    parser.add_argument("--outdir", required=True)
    args = parser.parse_args()

    spec_path = Path(args.spec)
    assets_path = Path(args.assets)
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    assets = json.loads(assets_path.read_text(encoding="utf-8"))
    bundle = build_benchmark(spec, args.shot, assets, assets_base_dir=assets_path.parent)
    write_bundle(bundle, Path(args.outdir))
    print(json.dumps({
        "benchmark_manifest": str(Path(args.outdir) / "benchmark-manifest.json"),
        "available": [name for name, item in bundle["providers"].items() if item.get("available") is True],
        "unavailable": {name: item.get("reason") for name, item in bundle["providers"].items() if item.get("available") is not True},
        "approved_for_spend": False,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
