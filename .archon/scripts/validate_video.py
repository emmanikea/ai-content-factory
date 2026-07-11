# /// script
# requires-python = ">=3.10"
# dependencies = ["google-genai>=1.0.0", "openai>=1.40.0", "python-dotenv>=1.0.0"]
# ///
"""
validate_video.py - the render-side quality gate. Given a rendered ad video, it (1) checks the
duration is real (not a truncated stub) and (2) asks a vision model to look at frames sampled
across the clip and judge whether it is a clean, usable product ad - no garbled AI text, no
melting/warping artifacts, the product intact, brand-safe (no faces/alcohol).

Vision is dual-provider so a single exhausted quota never silently disables QA: it tries Gemini
first, then falls back to OpenAI (gpt-4o-mini). Force one with VISION_PROVIDER=gemini|openai.
Only if BOTH are unavailable does it drop to a permissive duration-only heuristic.

Prints ONE json line:
    {"ok": true, "score": 86, "duration": 10.0, "reason": "...", "judge": "gemini-vision"}
"""
import base64, json, os, subprocess, sys, tempfile, time
from pathlib import Path
from dotenv import load_dotenv

REPO = Path(__file__).resolve().parents[2]
for envp in (REPO / ".env", REPO / "video-processor" / ".env", REPO / ".claude" / "scripts" / ".env"):
    if envp.exists():
        load_dotenv(envp, override=False)

MIN_DURATION = float(os.environ.get("VALIDATE_MIN_DURATION", "8.0"))
MIN_SCORE = int(os.environ.get("VALIDATE_MIN_SCORE", "60"))
PROVIDER = os.environ.get("VISION_PROVIDER", "auto")

RUBRIC = (
    "You are the QA gate for an automated product-ad factory. These frames are sampled across ONE "
    "short vertical video ad. Judge whether the FINISHED VIDEO is usable, 0-100. HARD FAILURES "
    "(score < 50): garbled/warped AI text or captions anywhere; the product melting, morphing, "
    "duplicating, or changing shape between frames; grotesque distortion; an identifiable human face; "
    "alcohol/cocktails/bar setting. GOOD (score 75+): the product stays consistent and recognizable "
    "across all frames, clean premium motion, brand-safe, no text artifacts. Human hands are fine. "
    "Intended concept: {concept}. Respond ONLY as JSON: "
    '{{"score": <int 0-100>, "reason": "<one sentence>"}}.')


def ffprobe_duration(path: Path) -> float:
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
            capture_output=True, text=True, timeout=60).stdout.strip()
        return float(out)
    except Exception:  # noqa: BLE001
        return 0.0


def extract_frames(path: Path, dur: float, tmp: Path) -> list[bytes]:
    ts = [0.3, dur * 0.35, dur * 0.6, max(0.0, dur - 0.3)]
    out = []
    for i, t in enumerate(ts):
        f = tmp / f"vf_{i}.jpg"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{t:.2f}", "-i", str(path),
                        "-frames:v", "1", "-q:v", "3", str(f)], capture_output=True, text=True)
        if f.exists():
            out.append(f.read_bytes())
    return out


def _parse(txt: str) -> dict:
    txt = (txt or "").strip().strip("`")
    if txt.startswith("json"):
        txt = txt[4:]
    return json.loads(txt[txt.find("{"): txt.rfind("}") + 1])


def judge_gemini(frames: list[bytes], prompt: str) -> dict | None:
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not key:
        return None
    try:
        from google import genai
        from google.genai import types
        parts = [types.Part.from_bytes(data=b, mime_type="image/jpeg") for b in frames]
        client = genai.Client(api_key=key)  # keep in scope (inline gets GC'd -> "client closed")
        resp = client.models.generate_content(model="gemini-2.5-flash", contents=[*parts, prompt])
        obj = _parse(resp.text)
        return {"score": int(max(0, min(100, obj.get("score", 60)))), "reason": obj.get("reason", ""),
                "judge": "gemini-vision"}
    except Exception as e:  # noqa: BLE001
        sys.stderr.write(f"[validate] gemini failed: {str(e)[:90]}\n")
        return None


def judge_openai(frames: list[bytes], prompt: str) -> dict | None:
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        return None
    try:
        from openai import OpenAI
        client = OpenAI(api_key=key)
        content = [{"type": "text", "text": prompt}]
        for b in frames:
            content.append({"type": "image_url",
                            "image_url": {"url": "data:image/jpeg;base64," + base64.b64encode(b).decode()}})
        for attempt in range(3):
            try:
                resp = client.chat.completions.create(
                    model=os.environ.get("VISION_OPENAI_MODEL", "gpt-4o-mini"),
                    messages=[{"role": "user", "content": content}], max_tokens=200, temperature=0)
                obj = _parse(resp.choices[0].message.content)
                return {"score": int(max(0, min(100, obj.get("score", 60)))),
                        "reason": obj.get("reason", ""), "judge": "openai-gpt4o"}
            except Exception as e:  # noqa: BLE001
                sys.stderr.write(f"[validate] openai attempt {attempt+1} failed: {str(e)[:90]}\n")
                time.sleep(2 * (attempt + 1))
    except Exception as e:  # noqa: BLE001
        sys.stderr.write(f"[validate] openai unavailable: {str(e)[:90]}\n")
    return None


def judge(frames: list[bytes], prompt: str) -> dict | None:
    order = {"auto": ["gemini", "openai"], "gemini": ["gemini"], "openai": ["openai"]}.get(PROVIDER, ["gemini", "openai"])
    for prov in order:
        r = judge_gemini(frames, prompt) if prov == "gemini" else judge_openai(frames, prompt)
        if r:
            return r
    return None


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

    with tempfile.TemporaryDirectory() as td:
        frames = extract_frames(vid, dur, Path(td))
        if not frames:
            print(json.dumps({"ok": True, "score": 70, "duration": round(dur, 2),
                              "reason": "no frames; duration-only", "judge": "heuristic"})); return 0
        r = judge(frames, RUBRIC.format(concept=concept or "a clean product ad"))
        if r is None:
            print(json.dumps({"ok": True, "score": 70, "duration": round(dur, 2),
                              "reason": "no vision provider available; duration-only", "judge": "heuristic"}))
            return 0
        print(json.dumps({"ok": r["score"] >= MIN_SCORE, "score": r["score"], "duration": round(dur, 2),
                          "reason": r["reason"], "judge": r["judge"]}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
