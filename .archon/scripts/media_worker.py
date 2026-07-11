#!/usr/bin/env python3
"""
media_worker.py - the swappable "media worker" behind the Archon ad-factory workflow.

This is the ONE swap point. The Archon DAG (brief -> shotlist -> fan-out -> curate ->
assemble) never changes. To go from the free/no-auth demo backend to Higgsfield, you
change a single flag: --backend pollinations  ->  --backend higgsfield.

  * pollinations : free, no API key. Real image gen via image.pollinations.ai, then a
                   real "cinematic motion" MP4 via an ffmpeg Ken-Burns move. Proves the
                   whole pipeline end-to-end today with zero secrets, so ANYONE can run it.
  * higgsfield   : the REAL production worker, via the official `higgsfield` CLI
                   (authenticated once with `higgsfield auth login`). Image-first: generates
                   a clean Higgsfield image (nano_banana_pro by default; Soul for character
                   consistency) + scores it. Video is generated separately for winners only
                   (animate_winner.py), because images are ~0.12 credits and video ~7.5-12.5.
                   Set --animate-model <model> to also make video in this step.

Usage (reads one concept from a shotlist.json produced by the shotlist node):
    media_worker.py --shotlist <path> --index <i> --outdir <dir> --backend pollinations

Or standalone (no shotlist file):
    media_worker.py --prompt "..." --motion "..." --caption "..." --aspect 9:16 \
        --outdir <dir> --backend pollinations

Writes into <outdir>: frame.jpg (key frame), asset.mp4 (motion clip), meta.json (provenance).
Prints a one-line summary to stdout (captured as the Archon node output).
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ASPECTS = {
    "16:9": (1280, 720),
    "9:16": (720, 1280),
    "1:1": (1024, 1024),
    "4:5": (864, 1080),
}


def log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


# --------------------------------------------------------------------------- #
# Backend: pollinations (free, no auth) - the demo worker
# --------------------------------------------------------------------------- #
def gen_image_pollinations(prompt: str, w: int, h: int, seed: int, dest: Path) -> None:
    """
    Fetch a real generated key-frame from pollinations.ai (no API key).

    The free endpoint rate-limits (HTTP 429) when the parallel fan-out hits it at once,
    so this backs off generously and 429-aware. This is exactly the kind of flaky async
    behavior a real production worker must absorb.
    """
    q = urllib.parse.quote(prompt, safe="")
    url = (
        f"https://image.pollinations.ai/prompt/{q}"
        f"?width={w}&height={h}&seed={seed}&nologo=true&model=flux"
    )
    last_err = None
    max_attempts = 7
    for attempt in range(1, max_attempts + 1):
        try:
            log(f"  [pollinations] GET (attempt {attempt}/{max_attempts}) {w}x{h} seed={seed}")
            req = urllib.request.Request(url, headers={"User-Agent": "archon-ad-factory/1.0"})
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = resp.read()
            if len(data) < 2000:
                raise RuntimeError(f"suspiciously small image ({len(data)} bytes)")
            dest.write_bytes(data)
            log(f"  [pollinations] wrote {dest.name} ({len(data)} bytes)")
            return
        except urllib.error.HTTPError as e:
            last_err = e
            # 429 = rate limited by the shared free endpoint: wait much longer.
            wait = (8 * attempt) if e.code == 429 else (3 * attempt)
            jitter = (int.from_bytes(os.urandom(1), "big") % 2000) / 1000.0  # 0-2s
            log(f"  [pollinations] attempt {attempt} HTTP {e.code}; backing off {wait + jitter:.1f}s")
            time.sleep(wait + jitter)
        except Exception as e:  # noqa: BLE001 - retry any transient failure
            last_err = e
            log(f"  [pollinations] attempt {attempt} failed: {e}")
            time.sleep(3 * attempt)
    raise RuntimeError(f"pollinations image generation failed after retries: {last_err}")


# --------------------------------------------------------------------------- #
# Backend: higgsfield (REAL, via the official CLI)
# --------------------------------------------------------------------------- #
# The `higgsfield` CLI (npm: @higgsfield/cli) is authenticated once with
# `higgsfield auth login`. Images (Soul V2) cost ~0.12 credits; image-to-video
# (Kling / Veo / Seedance) costs ~7.5-12.5 credits. So we generate + score + re-roll
# IMAGES freely and only spend on VIDEO for the winners (see animate_winner.py).
# nano_banana_pro gives clean, text-free product plates (Soul V2 bakes in garbled UGC
# captions). Both route through Higgsfield/its credits; override with HF_IMAGE_MODEL.
# Use text2image_soul_v2 / soul_cinematic when you want Soul character consistency.
HF_IMAGE_MODEL = os.environ.get("HF_IMAGE_MODEL", "nano_banana_pro")
HF_VIDEO_MODEL = os.environ.get("HF_VIDEO_MODEL", "kling3_0_turbo")
_VID_ASPECTS = {"16:9", "9:16", "1:1"}


def _hf_bin() -> str:
    import shutil
    return shutil.which("higgsfield") or shutil.which("hf") or "higgsfield"


def hf_run_job(args: list) -> dict:
    """Run a higgsfield CLI generate command with --json and return the first job dict."""
    # CRITICAL (Windows): the `higgsfield.CMD` shim is run via cmd.exe, which truncates an
    # argument at any embedded newline - silently dropping later flags like --wait/--json.
    # So flatten newlines out of every arg (prompts especially) before invoking the CLI.
    args = [str(a).replace("\r", " ").replace("\n", " ") for a in args]
    cmd = [_hf_bin()] + args + ["--json"]
    log(f"  [higgsfield] {' '.join(args[:4])} ...")
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
    if proc.returncode != 0:
        raise RuntimeError(f"higgsfield CLI failed: {(proc.stderr or proc.stdout)[:400]}")
    out = proc.stdout
    start = out.find("[")
    blob = out[start:out.rfind("]") + 1] if start >= 0 else out[out.find("{"):out.rfind("}") + 1]
    data = json.loads(blob)
    jobs = data if isinstance(data, list) else [data]
    if not jobs or jobs[0].get("status") != "completed" or not jobs[0].get("result_url"):
        raise RuntimeError(f"higgsfield job not completed: {jobs[0].get('status') if jobs else 'no job'}")
    return jobs[0]


def _download(url: str, dest: Path) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": "archon-ad-factory/1.0"})
    with urllib.request.urlopen(req, timeout=240) as r:
        dest.write_bytes(r.read())


def gen_image_higgsfield(prompt: str, aspect: str, dest: Path) -> None:
    """Higgsfield Soul V2 text-to-image via the CLI (~0.12 credits). Normalizes to JPG."""
    # Soul's ad templates like to bake in UGC-style captions, and AI-rendered text comes
    # out garbled. Force a clean plate; the ad copy is composited in post.
    clean = (prompt + " Clean editorial product photography, absolutely NO on-image text, "
             "no captions, no words, no letters, no UI overlays, no price tags, no logos, no watermark.")
    job = hf_run_job(["generate", "create", HF_IMAGE_MODEL,
                      "--prompt", clean, "--aspect_ratio", aspect,
                      "--wait", "--wait-timeout", "5m"])
    tmp = dest.with_name("_hf_src.png")
    _download(job["result_url"], tmp)
    # Normalize whatever Higgsfield returns (png/webp) to the jpg the pipeline expects.
    r = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(tmp), str(dest)],
                       capture_output=True, text=True)
    if r.returncode != 0 or not dest.exists():
        tmp.replace(dest)  # fall back to the raw file under the jpg name
    elif tmp.exists():
        tmp.unlink()
    log(f"  [higgsfield] Soul image -> {dest.name}")


def gen_video_higgsfield(frame: Path, motion: str, aspect: str, dest: Path,
                         model: str | None = None) -> None:
    """Higgsfield image-to-video via the CLI (~7.5-12.5 credits). Downloads the MP4."""
    model = model or HF_VIDEO_MODEL
    va = aspect if aspect in _VID_ASPECTS else "9:16"
    job = hf_run_job(["generate", "create", model,
                      "--prompt", motion or "subtle cinematic camera motion",
                      "--start-image", str(frame), "--aspect_ratio", va,
                      "--wait", "--wait-timeout", "12m"])
    _download(job["result_url"], dest)
    log(f"  [higgsfield] {model} video -> {dest.name}")


# --------------------------------------------------------------------------- #
# Motion: turn the key-frame into a real cinematic-motion MP4 with ffmpeg
# (the demo stand-in for Higgsfield DoP camera motion)
# --------------------------------------------------------------------------- #
def kenburns_mp4(frame: Path, dest: Path, w: int, h: int, seconds: int, index: int) -> None:
    fps = 30
    total = seconds * fps
    # Vary the move per variant so the fan-out visibly differs: push-in, pull-out, pan.
    moves = [
        "z='min(zoom+0.0018,1.20)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'",   # push in
        "z='if(lte(zoom,1.0),1.20,max(1.001,zoom-0.0018))':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'",  # pull out
        "z='min(zoom+0.0012,1.15)':x='(iw-iw/zoom)*(on/%d)':y='ih/2-(ih/zoom/2)'" % total,  # pan L->R
    ]
    move = moves[index % len(moves)]
    vf = (
        f"scale={w*2}:{h*2}:force_original_aspect_ratio=increase,"
        f"crop={w*2}:{h*2},"
        f"zoompan={move}:d={total}:s={w}x{h}:fps={fps},"
        f"format=yuv420p"
    )
    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-loop", "1", "-i", str(frame),
        "-vf", vf, "-t", str(seconds),
        "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p",
        str(dest),
    ]
    log(f"  [ffmpeg] rendering {seconds}s motion clip -> {dest.name}")
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0 or not dest.exists():
        raise RuntimeError(f"ffmpeg failed: {proc.stderr.strip()[:500]}")


def score_frame(frame: Path, concept: str) -> tuple:
    """Score the rendered frame 0-100 via the vision scorer (uv-run PEP723 script).
    Returns (score:int|None, reason:str, judge:str). Never raises."""
    script = Path(__file__).with_name("score_frame.py")
    try:
        proc = subprocess.run(
            ["uv", "run", "--quiet", str(script), str(frame), concept],
            capture_output=True, text=True, timeout=120,
        )
        line = [l for l in proc.stdout.splitlines() if l.strip().startswith("{")]
        if line:
            obj = json.loads(line[-1])
            return int(obj.get("score", 0)), obj.get("reason", ""), obj.get("judge", "unknown")
    except Exception as e:  # noqa: BLE001
        log(f"  [score] fell back to heuristic: {e}")
    # stdlib heuristic fallback (no uv / no key)
    size = frame.stat().st_size if frame.exists() else 50000
    return int(55 + (size // 4096) % 40), "heuristic", "heuristic"


def main() -> int:
    ap = argparse.ArgumentParser(description="Swappable media worker for the ad-factory workflow.")
    ap.add_argument("--shotlist", help="Path to shotlist.json")
    ap.add_argument("--index", type=int, default=0, help="Which concept (0-based) to render")
    ap.add_argument("--prompt", help="Image prompt (standalone mode, overrides shotlist)")
    ap.add_argument("--motion", default="", help="Motion/camera prompt (metadata + higgsfield)")
    ap.add_argument("--caption", default="", help="Ad caption (metadata)")
    ap.add_argument("--aspect", default="9:16", choices=list(ASPECTS.keys()))
    ap.add_argument("--seconds", type=int, default=4)
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--backend", default="pollinations", choices=["pollinations", "higgsfield"])
    ap.add_argument("--hint", default="", help="Extra guidance appended to the prompt (used on a re-roll)")
    ap.add_argument("--seed-bump", type=int, default=0, help="Vary the seed on a re-roll so the regen differs")
    ap.add_argument("--no-score", action="store_true", help="Skip the vision quality score")
    ap.add_argument("--animate-model", default="",
                    help="higgsfield backend only: if set (e.g. kling3_0_turbo), also generate video from the frame")
    args = ap.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    # Resolve the concept: shotlist file (workflow mode) or direct args (standalone).
    concept = {}
    if args.shotlist and not args.prompt:
        data = json.loads(Path(args.shotlist).read_text(encoding="utf-8"))
        concepts = data.get("concepts", data if isinstance(data, list) else [])
        if args.index >= len(concepts):
            raise SystemExit(f"index {args.index} out of range ({len(concepts)} concepts)")
        concept = concepts[args.index]
    prompt = args.prompt or concept.get("image_prompt") or concept.get("prompt", "")
    motion = args.motion or concept.get("motion_prompt", "")
    caption = args.caption or concept.get("caption", "")
    aspect = concept.get("aspect_ratio", args.aspect) if concept else args.aspect
    title = concept.get("title", f"Variant {args.index + 1}")
    if not prompt:
        raise SystemExit("no image prompt (need --prompt or a shotlist concept)")
    if args.hint:
        # No embedded newline: on Windows the higgsfield CLI is a .CMD shim run via
        # cmd.exe, which truncates command-line args at a literal newline, silently
        # dropping --wait/--json and breaking the JSON response parsing downstream.
        prompt = f"{prompt} Fix on this pass: {args.hint}"

    w, h = ASPECTS.get(aspect, ASPECTS["9:16"])
    seed = 1000 + args.index * 137 + args.seed_bump * 971  # deterministic, distinct per variant + reroll

    frame = outdir / "frame.jpg"
    asset = outdir / "asset.mp4"

    t0 = time.time()
    log(f"[variant {args.index + 1}] backend={args.backend} aspect={aspect} :: {title}")
    score, score_reason, score_judge = None, "", "skipped"
    if args.backend == "pollinations":
        # De-sync the parallel fan-out so the free endpoint doesn't 429 all at once.
        stagger = args.index * 6
        if stagger:
            log(f"  [stagger] variant {args.index + 1} waiting {stagger}s to de-sync parallel calls")
            time.sleep(stagger)
        gen_image_pollinations(prompt, w, h, seed, frame)
        kenburns_mp4(frame, asset, w, h, args.seconds, args.index)
        if not args.no_score:
            score, score_reason, score_judge = score_frame(frame, title)
    else:  # higgsfield (REAL, via CLI): image-first, with a validate + regenerate gate.
        # The factory "checks its own work": generate the concept image, vision-score it, and if
        # it is weak (garbled, off-brand, product unclear) regenerate with a cleanup hint, keeping
        # the best take. This is the cheap-image half of the two-stage validation harness.
        min_score = int(os.environ.get("IMAGE_MIN_SCORE", "62"))
        max_tries = int(os.environ.get("IMAGE_MAX_TRIES", "2"))
        img_hints = ["", " Cleaner composition, the product perfectly clear and centered, absolutely no text.",
                     " Simpler background, product sharp and unmistakable, no text, no clutter."]
        best = None  # (score, reason, judge)
        for attempt in range(max_tries):
            p = prompt + (img_hints[min(attempt, len(img_hints) - 1)] if attempt else "")
            tmp = frame.with_name(f"_img_try{attempt}.jpg")
            gen_image_higgsfield(p, aspect, tmp)
            sc, rs, jd = (None, "", "skipped") if args.no_score else score_frame(tmp, title)
            log(f"  [image-gate] attempt {attempt + 1}/{max_tries} score={sc}")
            if best is None or (sc or 0) > (best[0] or 0):
                if frame.exists():
                    frame.unlink()
                tmp.replace(frame)
                best = (sc, rs, jd)
            elif tmp.exists():
                tmp.unlink()
            if sc is None or sc >= min_score:
                break
        score, score_reason, score_judge = best
        if args.animate_model:
            gen_video_higgsfield(frame, motion, aspect, asset, args.animate_model)

    elapsed = round(time.time() - t0, 1)

    meta = {
        "index": args.index,
        "title": title,
        "backend": args.backend,
        "aspect_ratio": aspect,
        "dimensions": f"{w}x{h}",
        "seed": seed,
        "reroll_pass": args.seed_bump,
        "hint": args.hint,
        "image_prompt": prompt,
        "motion_prompt": motion,
        "caption": caption,
        "frame": str(frame),
        "asset": str(asset),
        "seconds": args.seconds,
        "elapsed_s": elapsed,
        "score": score,
        "score_reason": score_reason,
        "score_judge": score_judge,
    }
    (outdir / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")

    # stdout = the Archon node output (kept to one clean line)
    print(
        f"OK variant {args.index + 1} [{title}] backend={args.backend} "
        f"{w}x{h} {args.seconds}s score={score} ({score_judge}) in {elapsed}s -> {asset}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
