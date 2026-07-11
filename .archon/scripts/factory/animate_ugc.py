#!/usr/bin/env python3
"""
animate_ugc.py <product_id> <concept_id> - the UGC half of the ad "pair".

One approval -> two videos: animate_concept.py makes the product PAN; this makes the UGC
talking-head ad. A person holds/uses the ACTUAL product (nano_banana_pro keyframe with the product
image as a reference, no phone chrome) and delivers a short spoken review.

The ad is ONE single continuous ~10s generation (Google gemini_omni: image-to-video WITH native
speech + lipsync). This deliberately replaced the old 3-segment Veo chain: stitching three separate
Veo clips produced visible seams AND a voice/accent that changed at every join (each Veo generation
invents its own voice). A single take = one voice, zero cuts, by construction. gemini_omni caps at
10s, which is why the ad is ~10s. Validated with a UGC-aware rubric. Idempotent. RENDER_DRY_RUN=1 -> no-op.

Env: SITE_DIR, UGC_MODEL (gemini_omni), UGC_SECONDS (10), UGC_RESOLUTION (720p).
"""
import json
import os
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
DEFAULT_SITE = REPO / "Dynamous" / "Content-Ideation" / "2026-07-07" / "higgsfield-archon" / "catalog-site"
SITE = Path(os.environ.get("SITE_DIR", str(DEFAULT_SITE)))
VALIDATOR = Path(__file__).resolve().parents[1] / "validate_video.py"
MODEL = os.environ.get("UGC_MODEL", "gemini_omni")
SECONDS = os.environ.get("UGC_SECONDS", "10")          # gemini_omni hard cap is 10
RESOLUTION = os.environ.get("UGC_RESOLUTION", "720p")

CLEAN = (" Casual authentic UGC vlogger selfie look, vertical 9:16 portrait, natural candid home "
         "lighting, photorealistic, real skin texture, light natural smile, looking into the camera. "
         "IMPORTANT: no phone visible in frame, no phone bezel or screen border, no camera-app UI, no "
         "shutter button, no icons, no on-image text, no captions, no watermark, no logos.")

# per-product UGC: (how the product is held/described, the ONE spoken line - kept to ~24 words so it
# lands naturally inside a single 10s take without getting cut off).
SCRIPTS = {
    "p01": ("a matte-black insulated stainless steel coffee tumbler",
            "Okay, I have to show you this tumbler. It keeps my coffee hot for like twelve hours, "
            "still hot at 2pm. If you reheat your coffee a lot, get this one."),
    "p03": ("a warm oat-cream hand-glazed stoneware coffee mug",
            "This mug completely upgraded my morning coffee. It's hand-glazed stoneware, feels amazing "
            "to hold, and keeps it warm forever. Total game changer."),
    "p06": ("a dark-grey anodized aluminum manual hand coffee grinder",
            "I did not expect a hand grinder to be this good. Thirty-six settings, super consistent, "
            "and honestly kind of therapeutic. Highly recommend."),
    "p07": ("a matte-black gooseneck pour-over kettle",
            "This kettle made my pour-over so much better. The gooseneck gives you a perfect slow, "
            "controlled pour. If you're serious about coffee, get it."),
    "p09": ("a tall glass cold brew coffee carafe",
            "I make cold brew at home now and it is unreal. Add coffee and water, wait overnight, and "
            "it comes out so smooth, never bitter. Grab one."),
    "p10": ("a slim matte-black handheld milk frother",
            "Cafe-level foam at home with this tiny frother. Two seconds and my latte looks like I paid "
            "six bucks for it. Best cheap coffee upgrade, hands down."),
}

# Which reviewer to show per product. Default reviewer reads female; set a pid to "man" to force a
# male reviewer + voice. Keeps the UGC cast varied instead of all-female.
GENDER = {"p06": "man", "p07": "man"}


def hf_bin() -> str:
    for c in (shutil.which("higgsfield"), shutil.which("higgsfield.cmd"),
              os.path.expandvars(r"%APPDATA%\npm\higgsfield.cmd")):
        if c and Path(c).exists():
            return c
    return "higgsfield"


HF = hf_bin()


def hf_run(args: list) -> dict:
    args = [str(a).replace("\r", " ").replace("\n", " ") for a in args]
    proc = subprocess.run([HF] + args + ["--json"], capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=1800)
    if proc.returncode != 0:
        raise RuntimeError(f"CLI failed: {(proc.stderr or proc.stdout)[:300]}")
    out = proc.stdout
    s = out.find("[")
    blob = out[s:out.rfind("]") + 1] if s >= 0 else out[out.find("{"):out.rfind("}") + 1]
    jobs = json.loads(blob)
    j = jobs[0] if isinstance(jobs, list) else jobs
    if j.get("status") != "completed" or not j.get("result_url"):
        raise RuntimeError(f"job status {j.get('status')}")
    return j


def download(url: str, dest: Path):
    req = urllib.request.Request(url, headers={"User-Agent": "camber-ugc/1.0"})
    with urllib.request.urlopen(req, timeout=300) as r:
        dest.write_bytes(r.read())


def validate(path: Path, desc: str) -> dict:
    try:
        p = subprocess.run(["uv", "run", "--quiet", str(VALIDATOR), str(path), desc],
                           capture_output=True, text=True, timeout=200)
        lines = [l for l in p.stdout.splitlines() if l.strip().startswith("{")]
        if lines:
            return json.loads(lines[-1])
    except Exception as e:  # noqa: BLE001
        print(f"  validate error: {e}", file=sys.stderr)
    return {"ok": True, "score": None}


def script_for(prod: dict):
    pid = prod["id"]
    if pid in SCRIPTS:
        return SCRIPTS[pid]
    # generic fallback from catalog fields
    hold = prod.get("image_prompt", prod["name"])
    name = prod["name"]
    tag = prod.get("tagline", "")
    return (hold, f"Okay, I have to show you the {name}. {prod.get('description','')[:80]} "
                  f"{tag} Seriously, check it out.")


def main() -> int:
    if len(sys.argv) < 3:
        print("usage: animate_ugc.py <product_id> <concept_id>", file=sys.stderr)
        return 2
    pid = sys.argv[1]
    dest = SITE / "review" / pid / "ugc.mp4"
    if dest.exists():
        print(f"{pid}: ugc.mp4 already exists, skip")
        return 0
    catalog = json.loads((SITE / "catalog.json").read_text(encoding="utf-8"))
    prod = next((x for x in catalog["products"] if x["id"] == pid), None)
    if not prod:
        print(f"{pid}: not in catalog", file=sys.stderr)
        return 1
    hold, line = script_for(prod)
    who = GENDER.get(pid, "person")

    if os.environ.get("RENDER_DRY_RUN"):
        print(f"[DRY RUN] would make UGC ad for {pid} ({prod['name']}): single {SECONDS}s {MODEL} take")
        return 0

    work = SITE / "review" / pid
    work.mkdir(parents=True, exist_ok=True)

    # 1) person keyframe holding the real product (anchors gemini_omni on the accurate product + a
    #    clean, phone-free selfie framing). Reuse an already-good keyframe if present (keeps a chosen
    #    reviewer stable across regens); otherwise generate one, referencing the product plate.
    person = work / "ugc-person.jpg"
    if person.exists() and not os.environ.get("UGC_FORCE_KEYFRAME"):
        print(f"{pid}: reusing existing keyframe {person.name}", file=sys.stderr)
    else:
        ref = SITE / "images" / f"{pid}.jpg"
        kf_prompt = (f"A friendly {who} in a bright modern kitchen holding up {hold} toward the camera, "
                     f"candid vlog-style vertical selfie portrait, waist-up, warm natural light." + CLEAN)
        kargs = ["generate", "create", "nano_banana_pro", "--prompt", kf_prompt,
                 "--aspect_ratio", "9:16", "--wait", "--wait-timeout", "5m"]
        if ref.exists():
            kargs += ["--image-references", str(ref)]
        print(f"{pid}: UGC keyframe...", file=sys.stderr)
        kj = hf_run(kargs)
        ksrc = work / "_ugc_kf.src"
        download(kj["result_url"], ksrc)
        r = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(ksrc), str(person)],
                           capture_output=True, text=True)
        if r.returncode != 0 or not person.exists():
            ksrc.replace(person)
        elif ksrc.exists():
            ksrc.unlink()

    # 2) ONE continuous take: gemini_omni image-to-video WITH native speech (one voice, no seams).
    prompt = (f"A {who} in a kitchen holding {hold}, casual selfie UGC review, looking right at the "
              f"camera and speaking warmly in one continuous take: '{line}' Natural handheld style, "
              f"subtle movement, real skin texture. No on-screen text, no captions, no phone in frame.")
    print(f"{pid}: UGC single take ({SECONDS}s {MODEL})...", file=sys.stderr)
    j = hf_run(["generate", "create", MODEL, "--prompt", prompt, "--image-references", str(person),
                "--duration", SECONDS, "--aspect_ratio", "9:16", "--resolution", RESOLUTION,
                "--wait", "--wait-timeout", "20m"])
    download(j["result_url"], dest)
    if not dest.exists():
        print(f"{pid}: download failed", file=sys.stderr)
        return 1

    # 3) validate (UGC-aware rubric: a talking person is expected)
    v = validate(dest, f"UGC talking-head ad, a {who} holding {hold}")
    (work / "ugc_meta.json").write_text(json.dumps(
        {"product_id": pid, "kind": "ugc_singletake", "model": MODEL, "gender": who,
         "validation_score": v.get("score"), "line": line}, indent=2), encoding="utf-8")
    for f in list(work.glob("_ugc_*")):
        f.unlink()
    pr = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                         "-of", "default=noprint_wrappers=1:nokey=1", str(dest)],
                        capture_output=True, text=True)
    print(f"{pid}: UGC -> {dest} ({pr.stdout.strip()}s, validation score {v.get('score')} {v.get('judge','')})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
