#!/usr/bin/env python3
"""
animate_concept.py - animate ONE approved concept to Higgsfield video.

This is what each node of the parallel RENDER fan-out runs. Given a product id + concept id,
it drives the Higgsfield CLI (image-to-video, kling by default, ~7.5 cr) on that concept's
already-generated still and saves the mp4 next to it. Idempotent (skips if a video exists),
and RENDER_DRY_RUN=1 makes it a free no-op so you can validate the fan-out without spending.

Usage: animate_concept.py <product_id> <concept_id>
Env: SITE_DIR, HF_VIDEO_MODEL (kling3_0_turbo), MOTION, RENDER_DRY_RUN.
"""
import json
import os
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
DEFAULT_SITE = REPO / "catalog-site"
SITE = Path(os.environ.get("SITE_DIR", str(DEFAULT_SITE)))
VIDEO_MODEL = os.environ.get("HF_VIDEO_MODEL", "kling3_0_turbo")
DEFAULT_MOTION = os.environ.get("MOTION", "slow cinematic push-in, gentle light shift and rising steam, premium ad motion")
VID_ASPECTS = {"16:9", "9:16", "1:1"}


def hf_bin() -> str:
    return shutil.which("higgsfield") or shutil.which("hf") or "higgsfield"


def main() -> int:
    if len(sys.argv) < 3:
        print("usage: animate_concept.py <product_id> <concept_id>", file=sys.stderr); return 2
    pid, cid = sys.argv[1], sys.argv[2]
    cdir = SITE / "review" / pid / cid
    frame = cdir / "frame.jpg"
    dest = cdir / "asset.mp4"
    if dest.exists():
        print(f"{cid}: already has a video, skip"); return 0
    if not frame.exists():
        print(f"{cid}: no frame to animate", file=sys.stderr); return 1

    aspect = "9:16"
    meta = cdir / "meta.json"
    if meta.exists():
        try:
            aspect = json.loads(meta.read_text(encoding="utf-8")).get("aspect_ratio", "9:16")
        except Exception:  # noqa: BLE001
            pass
    va = aspect if aspect in VID_ASPECTS else "9:16"

    if os.environ.get("RENDER_DRY_RUN"):
        print(f"[DRY RUN] would animate {cid} ({va}) with {VIDEO_MODEL} (~7.5 cr)"); return 0

    motion = DEFAULT_MOTION.replace("\r", " ").replace("\n", " ")
    cmd = [hf_bin(), "generate", "create", VIDEO_MODEL, "--prompt", motion,
           "--start-image", str(frame), "--aspect_ratio", va,
           "--wait", "--wait-timeout", "12m", "--json"]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
    if proc.returncode != 0:
        print(f"{cid}: Higgsfield CLI failed: {(proc.stderr or proc.stdout)[:200]}", file=sys.stderr); return 1
    out = proc.stdout
    blob = out[out.find("["):out.rfind("]") + 1] if "[" in out else out[out.find("{"):out.rfind("}") + 1]
    job = json.loads(blob)
    job = job[0] if isinstance(job, list) else job
    url = job.get("result_url")
    if not url:
        print(f"{cid}: no result_url (status={job.get('status')})", file=sys.stderr); return 1
    req = urllib.request.Request(url, headers={"User-Agent": "camber-factory/1.0"})
    with urllib.request.urlopen(req, timeout=240) as r:
        dest.write_bytes(r.read())
    print(f"{cid}: video -> {dest} ({dest.stat().st_size} B)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
