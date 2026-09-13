#!/usr/bin/env python3
"""Deterministic first-stage QA for UGC Studio video artifacts.

This gate checks facts it can actually measure: media readability, duration, dimensions,
aspect, audio presence when required, and excessive black frames. It deliberately returns
`needs_review` when semantic checks such as identity consistency or anatomy have not run.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROFILES = {"creator_shot", "app_capture", "broll", "final_reel"}
BLACK_DURATION_RE = re.compile(r"black_duration:([0-9]+(?:\.[0-9]+)?)")
SEMANTIC_CHECKS = {
    "creator_shot": ["identity_consistency", "face_anatomy", "hands_limbs", "motion_naturalness", "lip_sync"],
    "app_capture": ["ui_correctness", "text_legibility", "unexpected_visual_artifacts"],
    "broll": ["visual_artifacts", "subject_consistency", "unexpected_text"],
    "final_reel": ["identity_consistency", "caption_legibility", "timeline_coherence", "visual_artifacts", "lip_sync"],
}


def _rate(value: str | None) -> float | None:
    if not value or value == "0/0":
        return None
    if "/" in value:
        left, right = value.split("/", 1)
        try:
            return float(left) / float(right) if float(right) else None
        except ValueError:
            return None
    try:
        return float(value)
    except ValueError:
        return None


def probe(path: Path) -> dict[str, Any]:
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "error", "-print_format", "json",
                "-show_entries", "stream=codec_type,width,height,avg_frame_rate:format=duration",
                str(path),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:
        raise RuntimeError("ffprobe is required for deterministic video QA") from exc
    except subprocess.CalledProcessError as exc:
        raise ValueError(f"ffprobe could not read video: {exc.stderr.strip()}") from exc
    payload = json.loads(result.stdout or "{}")
    streams = payload.get("streams") or []
    video = next((x for x in streams if x.get("codec_type") == "video"), {})
    return {
        "duration_seconds": float((payload.get("format") or {}).get("duration") or 0),
        "width": int(video["width"]) if video.get("width") else 0,
        "height": int(video["height"]) if video.get("height") else 0,
        "fps": _rate(video.get("avg_frame_rate")),
        "has_audio": any(x.get("codec_type") == "audio" for x in streams),
    }


def black_duration(path: Path) -> float | None:
    try:
        result = subprocess.run(
            [
                "ffmpeg", "-hide_banner", "-i", str(path),
                "-vf", "blackdetect=d=0.15:pix_th=0.10", "-an", "-f", "null", "-",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        return None
    durations = [float(x) for x in BLACK_DURATION_RE.findall(result.stderr)]
    return round(sum(durations), 3)


def evaluate_metadata(
    meta: dict[str, Any],
    *,
    artifact_id: str,
    profile: str,
    expected_duration: float | None = None,
    duration_tolerance: float = 0.75,
    require_audio: bool = False,
    black_seconds: float | None = None,
    min_width: int = 480,
    min_height: int = 854,
) -> dict[str, Any]:
    if profile not in PROFILES:
        raise ValueError(f"unknown QA profile: {profile}")
    checks: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []

    duration = float(meta.get("duration_seconds") or 0)
    width = int(meta.get("width") or 0)
    height = int(meta.get("height") or 0)
    has_audio = bool(meta.get("has_audio"))

    duration_ok = duration > 0
    checks.append({"name": "duration_readable", "status": "pass" if duration_ok else "fail", "value": round(duration, 3), "message": None if duration_ok else "video has no readable positive duration"})
    if not duration_ok:
        failures.append({"code": "invalid_duration", "severity": "structural", "message": "video has no readable positive duration"})

    if expected_duration is not None and duration_ok:
        delta = abs(duration - expected_duration)
        ok = delta <= duration_tolerance
        checks.append({"name": "expected_duration", "status": "pass" if ok else "fail", "value": round(delta, 3), "message": f"expected {expected_duration:.2f}s ± {duration_tolerance:.2f}s"})
        if not ok:
            failures.append({"code": "duration_mismatch", "severity": "structural", "message": f"duration {duration:.2f}s does not match expected {expected_duration:.2f}s"})

    resolution_ok = width >= min_width and height >= min_height
    checks.append({"name": "minimum_resolution", "status": "pass" if resolution_ok else "fail", "value": {"width": width, "height": height}, "message": f"minimum {min_width}x{min_height}"})
    if not resolution_ok:
        failures.append({"code": "resolution_too_low", "severity": "structural", "message": f"video is {width}x{height}"})

    vertical_required = profile in {"creator_shot", "app_capture", "final_reel"}
    if vertical_required:
        vertical = height > width
        checks.append({"name": "vertical_aspect", "status": "pass" if vertical else "fail", "value": f"{width}x{height}", "message": "vertical output required"})
        if not vertical:
            failures.append({"code": "wrong_aspect", "severity": "structural", "message": "expected vertical output"})

    if require_audio:
        checks.append({"name": "audio_stream", "status": "pass" if has_audio else "fail", "value": has_audio, "message": "audio stream required"})
        if not has_audio:
            failures.append({"code": "missing_audio", "severity": "structural", "message": "required audio stream is missing"})
    else:
        checks.append({"name": "audio_stream", "status": "pass" if has_audio else "not_run", "value": has_audio, "message": "audio not required by this QA invocation"})

    if black_seconds is None:
        checks.append({"name": "black_frames", "status": "not_run", "value": None, "message": "ffmpeg blackdetect unavailable/not supplied"})
    elif duration > 0:
        ratio = black_seconds / duration
        ok = black_seconds <= 0.5 and ratio <= 0.08
        checks.append({"name": "black_frames", "status": "pass" if ok else "fail", "value": {"seconds": round(black_seconds, 3), "ratio": round(ratio, 4)}, "message": "fails when >0.5s or >8% of clip"})
        if not ok:
            failures.append({"code": "excessive_black_frames", "severity": "structural", "message": f"detected {black_seconds:.2f}s black frames"})

    semantic = [{"name": name, "status": "needs_review", "value": None, "message": "semantic QA has not run"} for name in SEMANTIC_CHECKS[profile]]
    hard_fail = any(item["severity"] in {"structural", "rights", "source"} for item in failures)
    status = "fail" if hard_fail else "needs_review"
    retry_hint = "stop" if hard_fail else "manual_review"

    return {
        "artifact_id": artifact_id,
        "profile": profile,
        "status": status,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "score": None,
        "deterministic_checks": checks,
        "semantic_checks": semantic,
        "failures": failures,
        "retry_hint": retry_hint,
        "provenance": {"qa_stage": "deterministic", "fps": meta.get("fps")},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run deterministic first-stage QA on a UGC video")
    parser.add_argument("video")
    parser.add_argument("--artifact-id", required=True)
    parser.add_argument("--profile", required=True, choices=sorted(PROFILES))
    parser.add_argument("--expected-duration", type=float)
    parser.add_argument("--duration-tolerance", type=float, default=0.75)
    parser.add_argument("--require-audio", action="store_true")
    parser.add_argument("--min-width", type=int, default=480)
    parser.add_argument("--min-height", type=int, default=854)
    parser.add_argument("--out")
    args = parser.parse_args()

    video = Path(args.video).resolve()
    if not video.exists():
        raise SystemExit(f"video not found: {video}")
    meta = probe(video)
    result = evaluate_metadata(
        meta,
        artifact_id=args.artifact_id,
        profile=args.profile,
        expected_duration=args.expected_duration,
        duration_tolerance=args.duration_tolerance,
        require_audio=args.require_audio,
        black_seconds=black_duration(video),
        min_width=args.min_width,
        min_height=args.min_height,
    )
    text = json.dumps(result, indent=2)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
    print(text)
    return 1 if result["status"] == "fail" else 0


if __name__ == "__main__":
    raise SystemExit(main())
