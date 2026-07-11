#!/usr/bin/env python3
"""
gen_catalog.py - generate one clean Higgsfield product image per catalog item.

Reads catalog.json, calls the `higgsfield` CLI (nano_banana_pro, ~0.12 cr each), downloads
each result into images/<id>.jpg. Idempotent (skips images that already exist), newline-safe
for the Windows CLI shim, light concurrency to respect rate limits. NO video.

Usage: python gen_catalog.py [--force] [--workers 3]
"""
import argparse
import json
import shutil
import subprocess
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

HERE = Path(__file__).resolve().parent
IMAGES = HERE / "images"
MODEL = "nano_banana_pro"
ASPECT = "1:1"
NO_TEXT = ("absolutely NO on-image text, no captions, no words, no letters, no logos, "
           "no watermark, no price tags")


def hf_bin() -> str:
    return shutil.which("higgsfield") or shutil.which("hf") or "higgsfield"


def gen_one(prod: dict, style_note: str, force: bool) -> tuple:
    pid = prod["id"]
    dest = IMAGES / f"{pid}.jpg"
    if dest.exists() and not force:
        return pid, "skip", str(dest)
    prompt = f'{prod["image_prompt"]}. {style_note} {NO_TEXT}'.replace("\r", " ").replace("\n", " ")
    for attempt in (1, 2):
        try:
            cmd = [hf_bin(), "generate", "create", MODEL, "--prompt", prompt,
                   "--aspect_ratio", ASPECT, "--wait", "--wait-timeout", "5m", "--json"]
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            if proc.returncode != 0:
                raise RuntimeError((proc.stderr or proc.stdout)[:200])
            out = proc.stdout
            blob = out[out.find("["):out.rfind("]") + 1] if "[" in out else out[out.find("{"):out.rfind("}") + 1]
            job = json.loads(blob)
            job = job[0] if isinstance(job, list) else job
            url = job.get("result_url")
            if job.get("status") != "completed" or not url:
                raise RuntimeError(f"status={job.get('status')}")
            tmp = IMAGES / f"_{pid}_src"
            req = urllib.request.Request(url, headers={"User-Agent": "camber-catalog/1.0"})
            with urllib.request.urlopen(req, timeout=180) as r:
                tmp.write_bytes(r.read())
            r2 = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(tmp),
                                 "-vf", "scale=1000:1000:force_original_aspect_ratio=increase,crop=1000:1000",
                                 str(dest)], capture_output=True, text=True)
            if r2.returncode != 0 or not dest.exists():
                tmp.replace(dest)
            elif tmp.exists():
                tmp.unlink()
            return pid, "ok", str(dest)
        except Exception as e:  # noqa: BLE001
            last = str(e)[:160]
            if attempt == 2:
                return pid, f"FAIL: {last}", ""
    return pid, "FAIL", ""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--workers", type=int, default=3)
    args = ap.parse_args()

    data = json.loads((HERE / "catalog.json").read_text(encoding="utf-8"))
    products = data["products"]
    style = data.get("style_note", "")
    IMAGES.mkdir(exist_ok=True)

    print(f"Generating {len(products)} product images (model={MODEL}, {args.workers} workers)...", flush=True)
    done = fail = 0
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futs = {pool.submit(gen_one, p, style, args.force): p["id"] for p in products}
        for fut in as_completed(futs):
            pid, status, _ = fut.result()
            print(f"  {pid}: {status}", flush=True)
            if status.startswith("FAIL"):
                fail += 1
            else:
                done += 1
    print(f"Done. {done} ok/skip, {fail} failed.", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
