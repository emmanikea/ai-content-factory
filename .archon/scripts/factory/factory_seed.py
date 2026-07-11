#!/usr/bin/env python3
"""
factory_seed.py - drive the EXPLORE phase across the whole catalog directly (the same work units
the content-factory-explore workflow runs, without the Archon orchestration layer, so it is fast,
reliable and credit-controlled for pre-generating the demo site).

For each product it builds TWO text-free ad concepts (a clean studio hero + a lifestyle angle),
calls media_worker.py (Higgsfield image + the built-in validate/regenerate gate), writes the
per-product concepts.json fragment, then runs merge_queue.py to stitch the storefront queue.

Env: SITE_DIR, HF_IMAGE_MODEL (default nano_banana_pro), IMAGE_MIN_SCORE, IMAGE_MAX_TRIES.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve()
FACTORY = HERE.parent
SCRIPTS = FACTORY.parent
REPO = FACTORY.parents[2]
DEFAULT_SITE = REPO / "catalog-site"
SITE = Path(os.environ.get("SITE_DIR", str(DEFAULT_SITE)))
IMAGE_MODEL = os.environ.get("HF_IMAGE_MODEL", "nano_banana_pro")

LIFE = {
    "Drinkware": "held in soft morning light on a minimalist kitchen counter with gentle condensation or steam, cozy premium lifestyle",
    "Brew": "on a warm wooden cafe counter with soft window light and subtle blurred coffee elements behind, premium lifestyle",
    "Accessories": "on a clean modern kitchen surface in soft natural daylight, premium lifestyle, tasteful negative space",
}


def concepts_for(p: dict) -> list[dict]:
    style = ("Minimalist premium product photography, centered single product on a soft neutral warm-grey "
             "seamless studio background, gentle diffused daylight, subtle soft shadow, shallow depth of field.")
    ip = p["image_prompt"]
    setting = LIFE.get(p.get("category", ""), LIFE["Accessories"])
    return [
        {"cid": f"{p['id']}-a", "angle": "Studio hero",
         "caption": p.get("tagline", ""),
         "prompt": f"{style} {ip}. A single centered premium studio product hero shot, crisp, clean and evenly lit."},
        {"cid": f"{p['id']}-b", "angle": "In its element",
         "caption": p.get("description", "")[:60],
         "prompt": f"{ip}, {setting}, cinematic warm directional lighting, shallow depth of field, premium lifestyle product ad."},
    ]


def run_media(prompt: str, caption: str, outdir: Path) -> bool:
    env = dict(os.environ, HF_IMAGE_MODEL=IMAGE_MODEL)
    cmd = [sys.executable, str(SCRIPTS / "media_worker.py"),
           "--prompt", prompt, "--caption", caption, "--aspect", "9:16",
           "--outdir", str(outdir), "--backend", "higgsfield"]
    r = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=1500)
    ok = (outdir / "frame.jpg").exists()
    tail = (r.stdout or r.stderr).strip().splitlines()[-1:] or [""]
    print(f"    -> {'OK' if ok else 'FAIL'} {tail[0][:100]}", flush=True)
    return ok


def main() -> int:
    only = set(sys.argv[1:])  # optional: specific product ids
    catalog = json.loads((SITE / "catalog.json").read_text(encoding="utf-8"))
    review = SITE / "review"
    for p in catalog["products"]:
        pid = p["id"]
        if only and pid not in only:
            continue
        cj = review / pid / "concepts.json"
        if cj.exists():
            print(f"[{pid}] concepts.json exists, skip", flush=True)
            continue
        print(f"[{pid}] {p['name']} ({p.get('category')})", flush=True)
        cons = concepts_for(p)
        made = []
        for c in cons:
            outdir = review / pid / c["cid"]
            outdir.mkdir(parents=True, exist_ok=True)
            print(f"  concept {c['cid']} :: {c['angle']}", flush=True)
            if run_media(c["prompt"], c["caption"], outdir):
                made.append({"concept_id": c["cid"], "angle": c["angle"],
                             "caption": c["caption"], "aspect_ratio": "9:16"})
        if made:
            cj.write_text(json.dumps({"product_id": pid, "product_name": p["name"], "concepts": made},
                                     indent=2), encoding="utf-8")
    print("=== merge_queue ===", flush=True)
    subprocess.run([sys.executable, str(FACTORY / "merge_queue.py")], check=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
