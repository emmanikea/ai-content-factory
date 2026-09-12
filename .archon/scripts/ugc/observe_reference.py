#!/usr/bin/env python3
"""Observe a reference video without inventing semantic meaning.

Outputs factual metadata, scene-cut candidates, segment boundaries, optional keyframes,
and optional transcript data. A separate semantic step converts these observations into
ReferenceAnalysis roles such as creator/app-demo/hook/CTA.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

OBSERVER_VERSION = "2026-09-12.1"
RIGHTS_MODES = {"creative_dna_only", "licensed_performance_transfer", "owned_source"}
PTS_RE = re.compile(r"pts_time:([0-9]+(?:\.[0-9]+)?)")


def _run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, check=True, capture_output=True, text=True)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _rate(value: str | None) -> float | None:
    if not value or value in {"0/0", "N/A"}:
        return None
    if "/" in value:
        a, b = value.split("/", 1)
        try:
            return float(a) / float(b) if float(b) else None
        except ValueError:
            return None
    try:
        return float(value)
    except ValueError:
        return None


def probe_video(path: Path) -> dict[str, Any]:
    try:
        result = _run([
            "ffprobe", "-v", "error", "-print_format", "json",
            "-show_entries", "stream=codec_type,width,height,avg_frame_rate,r_frame_rate:format=duration",
            str(path),
        ])
    except FileNotFoundError as exc:
        raise RuntimeError("ffprobe is required for reference observation") from exc
    payload = json.loads(result.stdout or "{}")
    streams = payload.get("streams") or []
    video = next((s for s in streams if s.get("codec_type") == "video"), {})
    duration = float((payload.get("format") or {}).get("duration") or 0)
    if duration <= 0:
        raise ValueError("could not determine a positive video duration")
    return {
        "duration_seconds": round(duration, 3),
        "width": int(video["width"]) if video.get("width") else None,
        "height": int(video["height"]) if video.get("height") else None,
        "fps": _rate(video.get("avg_frame_rate") or video.get("r_frame_rate")),
        "has_audio": any(s.get("codec_type") == "audio" for s in streams),
    }


def detect_scene_cuts(path: Path, threshold: float) -> list[float]:
    if not 0 <= threshold <= 1:
        raise ValueError("scene threshold must be between 0 and 1")
    try:
        result = subprocess.run(
            [
                "ffmpeg", "-hide_banner", "-i", str(path),
                "-vf", f"select='gt(scene,{threshold})',showinfo",
                "-an", "-f", "null", "-",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:
        raise RuntimeError("ffmpeg is required for scene-cut detection") from exc
    cuts = sorted({round(float(match), 3) for match in PTS_RE.findall(result.stderr) if float(match) > 0})
    return cuts


def build_segments(duration: float, cuts: list[float], *, min_segment: float = 0.15) -> list[dict[str, Any]]:
    points = [0.0] + [x for x in cuts if min_segment <= x <= duration - min_segment] + [duration]
    deduped: list[float] = []
    for value in points:
        if not deduped or value - deduped[-1] >= min_segment:
            deduped.append(value)
    if deduped[-1] != duration:
        deduped.append(duration)
    segments = []
    for index, (start, end) in enumerate(zip(deduped, deduped[1:]), start=1):
        if end <= start:
            continue
        segments.append({"id": f"seg-{index:03d}", "start": round(start, 3), "end": round(end, 3), "keyframe_path": None})
    return segments


def extract_keyframes(path: Path, segments: list[dict[str, Any]], outdir: Path) -> None:
    outdir.mkdir(parents=True, exist_ok=True)
    for segment in segments:
        midpoint = (float(segment["start"]) + float(segment["end"])) / 2
        target = outdir / f"{segment['id']}.jpg"
        result = subprocess.run(
            [
                "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                "-ss", f"{midpoint:.3f}", "-i", str(path),
                "-frames:v", "1", "-q:v", "2", str(target),
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode == 0 and target.exists():
            segment["keyframe_path"] = str(target)


def load_transcript(path: Path | None) -> tuple[str | None, list[dict[str, Any]], str | None]:
    if path is None:
        return None, [], None
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        segments = payload
        text = " ".join(str(x.get("text", "")).strip() for x in segments).strip()
    else:
        segments = payload.get("segments") or []
        text = str(payload.get("text") or "").strip() or " ".join(str(x.get("text", "")).strip() for x in segments).strip()
    clean = []
    for item in segments:
        if item.get("start") is None or item.get("end") is None:
            continue
        clean.append({"start": round(float(item["start"]), 3), "end": round(float(item["end"]), 3), "text": str(item.get("text") or "").strip()})
    return text or None, clean, f"json:{path.name}"


def transcribe_whisper_cli(video: Path) -> tuple[str | None, list[dict[str, Any]], str | None]:
    whisper = shutil.which("whisper")
    if not whisper:
        raise RuntimeError("--whisper requested but `whisper` executable is not on PATH")
    with tempfile.TemporaryDirectory(prefix="ugc-whisper-") as temp:
        result = subprocess.run(
            [whisper, str(video), "--output_format", "json", "--output_dir", temp, "--verbose", "False"],
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f"whisper transcription failed: {result.stderr.strip()}")
        candidates = list(Path(temp).glob("*.json"))
        if not candidates:
            raise RuntimeError("whisper completed without a JSON transcript")
        text, segments, _ = load_transcript(candidates[0])
        return text, segments, "whisper-cli"


def observe_reference(
    path: Path,
    *,
    reference_id: str,
    rights_mode: str,
    scene_threshold: float = 0.35,
    transcript_json: Path | None = None,
    use_whisper: bool = False,
    keyframes_dir: Path | None = None,
) -> dict[str, Any]:
    if rights_mode not in RIGHTS_MODES:
        raise ValueError(f"invalid rights_mode: {rights_mode}")
    if not path.exists() or not path.is_file():
        raise ValueError(f"reference video not found: {path}")
    meta = probe_video(path)
    cuts = detect_scene_cuts(path, scene_threshold)
    segments = build_segments(meta["duration_seconds"], cuts)
    if keyframes_dir is not None:
        extract_keyframes(path, segments, keyframes_dir)

    if transcript_json is not None and use_whisper:
        raise ValueError("use either --transcript-json or --whisper, not both")
    if transcript_json is not None:
        transcript, transcript_segments, transcription_source = load_transcript(transcript_json)
    elif use_whisper:
        transcript, transcript_segments, transcription_source = transcribe_whisper_cli(path)
    else:
        transcript, transcript_segments, transcription_source = None, [], None

    return {
        "id": reference_id,
        "source_path": str(path.resolve()),
        "source_sha256": _sha256(path),
        "rights_mode": rights_mode,
        "duration_seconds": meta["duration_seconds"],
        "video": {
            "width": meta["width"],
            "height": meta["height"],
            "fps": round(meta["fps"], 3) if meta["fps"] else None,
            "has_audio": meta["has_audio"],
        },
        "cuts": cuts,
        "segments": segments,
        "transcript": transcript,
        "transcript_segments": transcript_segments,
        "analysis": {
            "observer_version": OBSERVER_VERSION,
            "scene_threshold": scene_threshold,
            "semantic_enrichment_required": True,
            "transcription_source": transcription_source,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Create factual observations from a reference video")
    parser.add_argument("video")
    parser.add_argument("--id", required=True, dest="reference_id")
    parser.add_argument("--rights-mode", required=True, choices=sorted(RIGHTS_MODES))
    parser.add_argument("--scene-threshold", type=float, default=0.35)
    parser.add_argument("--transcript-json")
    parser.add_argument("--whisper", action="store_true", help="Use the local OpenAI Whisper CLI if installed")
    parser.add_argument("--keyframes-dir")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    observation = observe_reference(
        Path(args.video).resolve(),
        reference_id=args.reference_id,
        rights_mode=args.rights_mode,
        scene_threshold=args.scene_threshold,
        transcript_json=Path(args.transcript_json).resolve() if args.transcript_json else None,
        use_whisper=args.whisper,
        keyframes_dir=Path(args.keyframes_dir).resolve() if args.keyframes_dir else None,
    )
    Path(args.out).write_text(json.dumps(observation, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"segments": len(observation["segments"]), "cuts": len(observation["cuts"]), "transcript": bool(observation["transcript"])}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
