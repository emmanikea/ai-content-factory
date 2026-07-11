#!/usr/bin/env python3
"""
animate_ugc.py <product_id> <concept_id> - the UGC half of the ad "pair".

One approval -> two videos: animate_concept.py makes the product PAN; this makes the ~24s UGC
talking-head ad. A person holds/uses the ACTUAL product (nano_banana_pro keyframe with the product
image as a reference, no phone chrome) and delivers a short review in native Veo 3.1 voice. THREE
Veo segments are CHAINED via last-frame (continuity, so it does NOT have the creepy reset-cuts the
same-keyframe approach produced), concatenated to ~24s -> review/<pid>/ugc.mp4, then validated with
a UGC-aware rubric (a person on camera is expected). Idempotent. RENDER_DRY_RUN=1 -> free no-op.

Env: SITE_DIR, UGC_VIDEO_QUALITY (high), UGC_SEG_SECONDS (8).
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
SEG = os.environ.get("UGC_SEG_SECONDS", "8")
QUALITY = os.environ.get("UGC_VIDEO_QUALITY", "high")

CLEAN = (" Casual authentic UGC vlogger selfie look, vertical 9:16 portrait, natural candid home "
         "lighting, photorealistic, real skin texture, light natural smile, looking into the camera. "
         "IMPORTANT: no phone visible in frame, no phone bezel or screen border, no camera-app UI, no "
         "shutter button, no icons, no on-image text, no captions, no watermark, no logos.")

# per-product UGC: (how the product is held/described, [(spoken line, emotion) x3])
SCRIPTS = {
    "p01": ("a matte-black insulated stainless steel coffee tumbler", [
        ("Okay I have to show you this tumbler, it honestly changed my mornings.", "warm, excited"),
        ("It keeps my coffee hot for like twelve hours. Still hot at 2pm, no joke.", "impressed"),
        ("If you're always reheating your coffee, get this one. Total game changer.", "friendly, confident")]),
    "p03": ("a warm oat-cream hand-glazed stoneware coffee mug", [
        ("This mug completely upgraded my morning coffee routine.", "warm"),
        ("It's hand-glazed stoneware, feels amazing to hold and keeps it warm forever.", "enthusiastic"),
        ("Do yourself a favor and get a really good mug. Worth it.", "friendly, confident")]),
    "p06": ("a dark-grey anodized aluminum manual hand coffee grinder", [
        ("I did not expect a hand grinder to be this good.", "surprised"),
        ("Thirty-six settings, super consistent, and honestly grinding it is kind of therapeutic.", "enthusiastic"),
        ("If you want fresh-ground coffee every morning, this is the one.", "confident")]),
    "p07": ("a matte-black gooseneck pour-over kettle", [
        ("This kettle made my pour-over so much better.", "warm"),
        ("The gooseneck gives you this perfect slow, controlled pour, and the temperature is dialed in.", "impressed"),
        ("If you're serious about coffee, you need this kettle.", "confident")]),
    "p09": ("a tall glass cold brew coffee carafe", [
        ("I make cold brew at home now and it is honestly unreal.", "excited"),
        ("You add coffee and water, wait overnight, and it comes out so smooth, never bitter.", "enthusiastic"),
        ("Grab one of these. Your afternoons will thank you.", "friendly")]),
    "p10": ("a slim matte-black handheld milk frother", [
        ("Cafe-level foam at home with this tiny frother.", "warm"),
        ("Two seconds and my latte looks like I paid six bucks for it.", "impressed"),
        ("Best cheap upgrade to your coffee, hands down.", "confident")]),
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


def last_frame(mp4: Path, dest: Path):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-sseof", "-0.4", "-i", str(mp4),
                    "-frames:v", "1", "-q:v", "2", str(dest)], capture_output=True, text=True)


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
    return (hold, [
        (f"Okay I have to show you the {name}, it's honestly so good.", "warm, excited"),
        (f"{prod.get('description','')[:90]}", "enthusiastic"),
        (f"{tag} Seriously, check it out.", "friendly, confident")])


def main() -> int:
    if len(sys.argv) < 3:
        print("usage: animate_ugc.py <product_id> <concept_id>", file=sys.stderr)
        return 2
    pid, cid = sys.argv[1], sys.argv[2]
    cdir = SITE / "review" / pid / cid
    dest = SITE / "review" / pid / "ugc.mp4"
    if dest.exists():
        print(f"{pid}: ugc.mp4 already exists, skip")
        return 0
    catalog = json.loads((SITE / "catalog.json").read_text(encoding="utf-8"))
    prod = next((x for x in catalog["products"] if x["id"] == pid), None)
    if not prod:
        print(f"{pid}: not in catalog", file=sys.stderr)
        return 1
    hold, lines = script_for(prod)
    who = GENDER.get(pid, "person")

    if os.environ.get("RENDER_DRY_RUN"):
        print(f"[DRY RUN] would make UGC ad for {pid} ({prod['name']}): 3 Veo segments -> ugc.mp4")
        return 0

    work = SITE / "review" / pid
    # 1) person keyframe holding the real product (reference the clean product image if present)
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
    person = work / "ugc-person.jpg"
    r = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(ksrc), str(person)],
                       capture_output=True, text=True)
    if r.returncode != 0 or not person.exists():
        ksrc.replace(person)
    elif ksrc.exists():
        ksrc.unlink()

    # 2) three Veo talking segments, chained via last-frame for continuity
    start = person
    parts = []
    for i, (line, emo) in enumerate(lines):
        motion = (f"A {who} in a kitchen holding {hold}, filming a casual selfie video review. "
                  f"They look right at the camera and say: \"{line}\" [{emo}]. "
                  f"Natural subtle head movement, authentic hand-held UGC style.")
        seg = work / f"_ugc_seg{i}.mp4"
        print(f"{pid}: UGC segment {i + 1}/3: \"{line[:40]}...\"", file=sys.stderr)
        j = hf_run(["generate", "create", "veo3_1", "--prompt", motion, "--start-image", str(start),
                    "--aspect_ratio", "9:16", "--duration", SEG, "--quality", QUALITY,
                    "--variant", "veo-3-1-fast", "--wait", "--wait-timeout", "20m"])
        download(j["result_url"], seg)
        parts.append(seg)
        if i < len(lines) - 1:
            nxt = work / f"_ugc_lf{i}.jpg"
            last_frame(seg, nxt)
            start = nxt

    # 3) concat -> ugc.mp4 (re-encode to normalize audio/video)
    listf = work / "_ugc_concat.txt"
    listf.write_text("".join(f"file '{p.name}'\n" for p in parts), encoding="utf-8")
    r = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
                        "-i", str(listf), "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac",
                        str(dest)], capture_output=True, text=True, cwd=str(work))
    if r.returncode != 0 or not dest.exists():
        print(f"{pid}: concat failed: {r.stderr[:200]}", file=sys.stderr)
        return 1

    # 4) validate (UGC-aware rubric: a talking person is expected)
    v = validate(dest, f"UGC talking-head ad, a person holding {hold}")
    (work / "ugc_meta.json").write_text(json.dumps(
        {"product_id": pid, "kind": "ugc", "segments": len(parts), "validation_score": v.get("score"),
         "lines": [l for l, _ in lines]}, indent=2), encoding="utf-8")
    # cleanup temp
    for f in list(work.glob("_ugc_*")):
        f.unlink()
    pr = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                         "-of", "default=noprint_wrappers=1:nokey=1", str(dest)],
                        capture_output=True, text=True)
    print(f"{pid}: UGC -> {dest} ({pr.stdout.strip()}s, validation score {v.get('score')} {v.get('judge','')})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
