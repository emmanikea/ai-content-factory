# /// script
# requires-python = ">=3.10"
# dependencies = ["google-genai>=1.0.0", "openai>=1.40.0", "python-dotenv>=1.0.0"]
# ///
"""
score_frame.py - a real vision-based "virality / ad-quality" score for a concept key frame.

The local stand-in for Higgsfield's virality-prediction tool. It asks a vision model to rate a
generated ad frame 0-100 with a short rubric and returns JSON on stdout:
    {"score": 84, "reason": "...", "judge": "gemini-vision"}

Dual-provider so an exhausted quota never silently disables scoring: tries Gemini first, then
OpenAI (gpt-4o-mini). Force one with VISION_PROVIDER=gemini|openai. Falls back to a deterministic
size heuristic only if BOTH are unavailable. Reads keys from the process env or the .env files.
"""
import base64, json, os, sys, time
from pathlib import Path
from dotenv import load_dotenv

REPO = Path(__file__).resolve().parents[2]
for envp in (REPO / ".env", REPO / "video-processor" / ".env", REPO / ".claude" / "scripts" / ".env"):
    if envp.exists():
        load_dotenv(envp, override=False)

PROVIDER = os.environ.get("VISION_PROVIDER", "auto")

RUBRIC = (
    "Rate this image as a short-form video AD key frame for scroll-stopping virality, 0-100. "
    "Weigh: subject clarity, thumb-stopping composition, emotional pull, production polish, and "
    "whether any on-image text is legible (garbled AI text is a heavy penalty). REPUTATION-SAFETY "
    "RULES (brand-safe product catalog): an identifiable human FACE is a hard penalty (subtract 40+); "
    "the ad must not read as featuring a real person. Human HANDS or arms handling the product are "
    "FINE and NOT penalized. Alcohol, cocktails, beer, wine, spirits, or bar/liquor-bottle settings "
    "are a hard penalty (subtract 40+) - this is a coffee and hydration brand, keep it non-alcoholic. "
    "Concept: {concept}. Respond ONLY as JSON: "
    '{{"score": <int 0-100>, "reason": "<one sentence>"}}.')


def _parse(txt: str) -> dict:
    txt = (txt or "").strip().strip("`")
    if txt.startswith("json"):
        txt = txt[4:]
    return json.loads(txt[txt.find("{"): txt.rfind("}") + 1])


def heuristic(img: Path) -> dict:
    size = img.stat().st_size if img.exists() else 50000
    return {"score": int(55 + (size // 4096) % 40), "reason": "heuristic (no vision key/quota)", "judge": "heuristic"}


def judge_gemini(img_bytes: bytes, prompt: str) -> dict | None:
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not key:
        return None
    try:
        from google import genai
        from google.genai import types
        client = genai.Client(api_key=key)
        resp = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[types.Part.from_bytes(data=img_bytes, mime_type="image/jpeg"), prompt])
        obj = _parse(resp.text)
        return {"score": int(max(0, min(100, obj.get("score", 60)))), "reason": obj.get("reason", ""),
                "judge": "gemini-vision"}
    except Exception as e:  # noqa: BLE001
        sys.stderr.write(f"[score] gemini failed: {str(e)[:90]}\n")
        return None


def judge_openai(img_bytes: bytes, prompt: str) -> dict | None:
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        return None
    try:
        from openai import OpenAI
        client = OpenAI(api_key=key)
        content = [{"type": "text", "text": prompt},
                   {"type": "image_url",
                    "image_url": {"url": "data:image/jpeg;base64," + base64.b64encode(img_bytes).decode()}}]
        for attempt in range(3):
            try:
                resp = client.chat.completions.create(
                    model=os.environ.get("VISION_OPENAI_MODEL", "gpt-4o-mini"),
                    messages=[{"role": "user", "content": content}], max_tokens=160, temperature=0)
                obj = _parse(resp.choices[0].message.content)
                return {"score": int(max(0, min(100, obj.get("score", 60)))),
                        "reason": obj.get("reason", ""), "judge": "openai-gpt4o"}
            except Exception as e:  # noqa: BLE001
                sys.stderr.write(f"[score] openai attempt {attempt+1} failed: {str(e)[:90]}\n")
                time.sleep(2 * (attempt + 1))
    except Exception as e:  # noqa: BLE001
        sys.stderr.write(f"[score] openai unavailable: {str(e)[:90]}\n")
    return None


def main() -> int:
    if len(sys.argv) < 2:
        print(json.dumps({"score": 0, "reason": "no path", "judge": "error"})); return 1
    img = Path(sys.argv[1])
    concept = sys.argv[2] if len(sys.argv) > 2 else ""
    if not img.exists() or img.suffix.lower() not in (".jpg", ".jpeg", ".png"):
        print(json.dumps(heuristic(img))); return 0
    data = img.read_bytes()
    prompt = RUBRIC.format(concept=concept or "n/a")
    order = {"auto": ["gemini", "openai"], "gemini": ["gemini"], "openai": ["openai"]}.get(PROVIDER, ["gemini", "openai"])
    for prov in order:
        r = judge_gemini(data, prompt) if prov == "gemini" else judge_openai(data, prompt)
        if r:
            print(json.dumps(r)); return 0
    print(json.dumps(heuristic(img)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
