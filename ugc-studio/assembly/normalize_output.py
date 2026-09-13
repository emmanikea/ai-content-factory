#!/usr/bin/env python3
"""Normalize final Reel output for social delivery using FFmpeg."""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path


def normalize(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-i", str(source),
        "-vf", "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2,setsar=1",
        "-af", "loudnorm=I=-14:LRA=11:TP=-1.5",
        "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
        "-movflags", "+faststart",
        str(destination),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or "ffmpeg normalization failed")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input")
    parser.add_argument("output")
    args = parser.parse_args()

    source = Path(args.input).resolve()
    destination = Path(args.output).resolve()
    if not source.exists():
        raise SystemExit(f"input not found: {source}")
    normalize(source, destination)
    print(json.dumps({"input": str(source), "output": str(destination), "normalized": True}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
