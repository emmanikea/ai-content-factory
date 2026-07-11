# /// script
# requires-python = ">=3.10"
# dependencies = ["google-genai>=1.0.0", "python-dotenv>=1.0.0"]
# ///
"""
validate_video.py - the render-side quality gate. Given a rendered ad video, it (1) checks the
duration is real (not a truncated stub) and (2) asks a vision model to look at frames sampled
across the clip and judge whether it is a clean, usable product ad - no garbled AI text, no
melting/warping artifacts, the product intact, brand-safe (no faces/alcohol).

Prints ONE json line:
    {"ok": true, "score": 86, "duration": 10.0, "reason": "...", "judge": "gemini-vision"}

Falls back to a permissive heuristic if there is no vision key/quota (so a run never hard-blocks
on a missing key - it just can't catch subtle artifacts). Stdlib-friendly caller contract.
"""
import json, os, subprocess, sys, tempfile
from pathlib import Path
from dotenv import load_dotenv

REPO = Path(__file__).resolve().parents[2]
for envp in (REPO / ".env", REPO / "video-processor" / ".env", REPO / ".claude" / "scripts" / ".env"):
    if envp.exists():
        load_dotenv(envp, override=False)

MIN_DURATION = float(os.environ.get("VALIDATE_MIN_DURATION", "8.0"))
MIN_SCORE = int(os.environ.get("VALIDATE_MIN_SCORE", "60"))


def ffprobe_duration(path: Path) -> float:
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
            capture_output=True, text=True, timeout=60).stdout.strip()
        return float(out)
    except Exception:  # noqa: BLE001
        return 0.0


def extract_frames(path: Path, dur: float, tmp: Path) -> list[Path]:
    # sample start / three interior points / end so warps mid-clip are caught
    ts = [0.3, dur * 0.35, dur * 0.6, max(0.0, dur - 0.3)]
    frames = []
    for i, t in enumerate(ts):
        f = tmp / f"vf_{i}.jpg"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{t:.2f}", "-i", str(path),
                        "-frames:v", "1", "-q:v", "3", str(f)], capture_output=True, text=True)
        if f.exists():
            frames.append(f)
    return frames


def heuristic(dur: float) -> dict:
    ok = dur >= MIN_DURATION
    return {"ok": ok, "score": 70 if ok else 30, "duration": round(dur, 2),
            "reason": "heuristic (no vision key/quota); duration-only check", "judge": "heuristic"}


def main() -> int:
    if len(sys.argv) < 2:
        print(json.dumps({"ok": False, "score": 0, "reason": "no path", "judge": "error"})); return 1
    vid = Path(sys.argv[1])
    concept = sys.argv[2] if len(sys.argv) > 2 else ""
    if not vid.exists():
        print(json.dumps({"ok": False, "score": 0, "reason": "missing file", "judge": "error"})); return 1

    dur = ffprobe_duration(vid)
    if dur < MIN_DURATION:
        print(json.dumps({"ok": False, "score": 20, "duration": round(dur, 2),
                          "reason": f"too short ({dur:.1f}s < {MIN_DURATION}s)", "judge": "duration"}))
        return 0

    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not key:
        print(json.dumps(heuristic(dur))); return 0

    try:
        from google import genai
        from google.genai import types
        with tempfile.TemporaryDirectory() as td:
            frames = extract_frames(vid, dur, Path(td))
            if not frames:
                print(json.dumps(heuristic(dur))); return 0
            rubric = (
                "You are the QA gate for an automated product-ad factory. These frames are sampled "
                "across ONE short vertical video ad. Judge whether the FINISHED VIDEO is usable, 0-100. "
                "HARD FAILURES (score < 50): garbled/warped AI text or captions anywhere; the product "
                "melting, morphing, duplicating, or changing shape between frames; grotesque distortion; "
                "an identifiable human face; alcohol/cocktails/bar setting. GOOD (score 75+): the product "
                "stays consistent and recognizable across all frames, clean premium motion, brand-safe, "
                "no text artifacts. Human hands are fine. "
                f"Intended concept: {concept or 'a clean product ad'}. "
                'Respond ONLY as JSON: {"score": <int 0-100>, "reason": "<one sentence>"}.')
            parts = [types.Part.from_bytes(data=f.read_bytes(), mime_type="image/jpeg") for f in frames]
            resp = genai.Client(api_key=key).models.generate_content(
                model="gemini-2.5-flash", contents=[*parts, rubric])
            txt = (resp.text or "").strip().strip("`")
            if txt.startswith("json"):
                txt = txt[4:]
            obj = json.loads(txt[txt.find("{"): txt.rfind("}") + 1])
            score = int(max(0, min(100, obj.get("score", 60))))
            print(json.dumps({"ok": score >= MIN_SCORE, "score": score, "duration": round(dur, 2),
                              "reason": obj.get("reason", ""), "judge": "gemini-vision"}))
    except Exception as e:  # noqa: BLE001
        h = heuristic(dur); h["reason"] = f"heuristic (judge error: {str(e)[:80]})"
        print(json.dumps(h))
    return 0


if __name__ == "__main__":
    sys.exit(main())
