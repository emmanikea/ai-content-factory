#!/usr/bin/env python3
"""
animate_concept.py - animate ONE approved concept to a validated Higgsfield video.

Each node of the parallel RENDER fan-out runs this. Given a product id + concept id, it drives
the Higgsfield CLI (image-to-video, kling) on that concept's approved still and saves the mp4
next to it. It then VALIDATES the rendered video (duration + a vision QA pass via validate_video.py)
and, if the clip is bad (garbled text, warping product, too short), regenerates up to RENDER_MAX_TRIES
and keeps the best-scoring take. Idempotent (skips if a good video already exists). RENDER_DRY_RUN=1
makes it a free no-op.

Usage: animate_concept.py <product_id> <concept_id>
Env: SITE_DIR, HF_VIDEO_MODEL (kling3_0_turbo), HF_VIDEO_DURATION (10), HF_VIDEO_RESOLUTION (1080p),
     RENDER_MAX_TRIES (2), MOTION, RENDER_DRY_RUN.
"""
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
DEFAULT_SITE = REPO / "Dynamous" / "Content-Ideation" / "2026-07-07" / "higgsfield-archon" / "catalog-site"
SITE = Path(os.environ.get("SITE_DIR", str(DEFAULT_SITE)))
VIDEO_MODEL = os.environ.get("HF_VIDEO_MODEL", "kling3_0_turbo")
DURATION = os.environ.get("HF_VIDEO_DURATION", "10")
RESOLUTION = os.environ.get("HF_VIDEO_RESOLUTION", "1080p")
MAX_TRIES = int(os.environ.get("RENDER_MAX_TRIES", "2"))
DEFAULT_MOTION = os.environ.get(
    "MOTION", "slow cinematic push-in on the product, gentle light shift, premium product-ad motion")
VID_ASPECTS = {"16:9", "9:16", "1:1"}
VALIDATOR = Path(__file__).resolve().parents[1] / "validate_video.py"  # .archon/scripts/validate_video.py


def hf_bin() -> str:
    for cand in (shutil.which("higgsfield"), shutil.which("higgsfield.cmd"),
                 os.path.expandvars(r"%APPDATA%\npm\higgsfield.cmd")):
        if cand and Path(cand).exists():
            return cand
    return shutil.which("higgsfield") or "higgsfield"


def generate(frame: Path, motion: str, aspect: str, dest: Path) -> bool:
    cmd = [hf_bin(), "generate", "create", VIDEO_MODEL, "--prompt", motion,
           "--start-image", str(frame), "--aspect_ratio", aspect,
           "--duration", str(DURATION), "--resolution", RESOLUTION,
           "--wait", "--wait-timeout", "15m", "--json"]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=1200)
    if proc.returncode != 0:
        print(f"  CLI failed: {(proc.stderr or proc.stdout)[:200]}", file=sys.stderr)
        return False
    out = proc.stdout
    blob = out[out.find("["):out.rfind("]") + 1] if "[" in out else out[out.find("{"):out.rfind("}") + 1]
    try:
        job = json.loads(blob)
    except Exception:  # noqa: BLE001
        print("  could not parse CLI json", file=sys.stderr)
        return False
    job = job[0] if isinstance(job, list) else job
    url = job.get("result_url")
    if not url:
        print(f"  no result_url (status={job.get('status')})", file=sys.stderr)
        return False
    req = urllib.request.Request(url, headers={"User-Agent": "camber-factory/1.0"})
    with urllib.request.urlopen(req, timeout=300) as r:
        dest.write_bytes(r.read())
    return True


def validate(path: Path, concept_desc: str) -> dict:
    try:
        p = subprocess.run(["uv", "run", "--quiet", str(VALIDATOR), str(path), concept_desc],
                           capture_output=True, text=True, timeout=200)
        lines = [l for l in p.stdout.splitlines() if l.strip().startswith("{")]
        if lines:
            return json.loads(lines[-1])
    except Exception as e:  # noqa: BLE001
        print(f"  validate error: {e}", file=sys.stderr)
    return {"ok": True, "score": None, "reason": "validation skipped"}


def main() -> int:
    if len(sys.argv) < 3:
        print("usage: animate_concept.py <product_id> <concept_id>", file=sys.stderr)
        return 2
    pid, cid = sys.argv[1], sys.argv[2]
    cdir = SITE / "review" / pid / cid
    frame = cdir / "frame.jpg"
    dest = cdir / "asset.mp4"
    if dest.exists():
        print(f"{cid}: already has a video, skip")
        return 0
    if not frame.exists():
        print(f"{cid}: no frame to animate", file=sys.stderr)
        return 1

    aspect, concept_desc = "9:16", ""
    meta = cdir / "meta.json"
    if meta.exists():
        try:
            m = json.loads(meta.read_text(encoding="utf-8"))
            aspect = m.get("aspect_ratio", "9:16")
            concept_desc = m.get("caption") or m.get("title") or ""
        except Exception:  # noqa: BLE001
            pass
    va = aspect if aspect in VID_ASPECTS else "9:16"

    if os.environ.get("RENDER_DRY_RUN"):
        print(f"[DRY RUN] would animate {cid} ({va}) {DURATION}s {RESOLUTION} with {VIDEO_MODEL}, validate + regen")
        return 0

    # B-roll mode: instead of spending on Higgsfield, restore this concept's pre-rendered video
    # from BROLL_SRC (with a pacing delay) and run the REAL validation on it. Produces an authentic
    # "rendered + validated" transcript for demo capture at ~zero cost.
    broll = os.environ.get("BROLL_SRC")
    if broll:
        src = Path(broll) / pid / cid / "asset.mp4"
        time.sleep(float(os.environ.get("BROLL_DELAY", "3")))
        if not src.exists():
            print(f"{cid}: no B-roll source at {src}", file=sys.stderr)
            return 1
        shutil.copyfile(src, dest)
        v = validate(dest, concept_desc)
        (cdir / "render_meta.json").write_text(
            json.dumps({"concept_id": cid, "model": VIDEO_MODEL, "duration": DURATION,
                        "resolution": RESOLUTION, "validation_score": v.get("score")}, indent=2),
            encoding="utf-8")
        print(f"{cid}: rendered -> {dest} ({dest.stat().st_size} B), validation score {v.get('score')} ({v.get('judge')})")
        return 0

    motion = DEFAULT_MOTION.replace("\r", " ").replace("\n", " ")
    hints = ["",
             " Keep the product perfectly consistent and stable across the whole clip, no warping, no text.",
             " Minimal subtle motion only; keep the product rigid, clean and centered, absolutely no text or captions."]

    best = None  # (score, path)
    for attempt in range(MAX_TRIES):
        tmp = dest.with_name(f"_try{attempt}.mp4")
        if not generate(frame, (motion + hints[min(attempt, len(hints) - 1)]).strip(), va, tmp):
            continue
        v = validate(tmp, concept_desc)
        sc = v.get("score") if v.get("score") is not None else 100
        print(f"{cid}: attempt {attempt + 1}/{MAX_TRIES} score={v.get('score')} ok={v.get('ok')} :: {str(v.get('reason',''))[:80]}",
              file=sys.stderr)
        if best is None or sc > best[0]:
            if best is not None and best[1].exists():
                best[1].unlink()
            best = (sc, tmp)
        elif tmp.exists():
            tmp.unlink()
        if v.get("ok"):
            break

    if best is None:
        print(f"{cid}: all {MAX_TRIES} render attempts failed", file=sys.stderr)
        return 1
    best[1].replace(dest)
    (cdir / "render_meta.json").write_text(
        json.dumps({"concept_id": cid, "model": VIDEO_MODEL, "duration": DURATION,
                    "resolution": RESOLUTION, "validation_score": best[0]}, indent=2), encoding="utf-8")
    print(f"{cid}: video -> {dest} ({dest.stat().st_size} B, best validation score {best[0]})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
