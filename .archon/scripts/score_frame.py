# /// script
# requires-python = ">=3.10"
# dependencies = ["google-genai>=1.0.0", "python-dotenv>=1.0.0"]
# ///
"""
score_frame.py - a real vision-based "virality / ad-quality" score for a key frame.

This is the local stand-in for Higgsfield's virality-prediction tool. It asks a vision
model to rate a generated ad frame 0-100 with a short rubric, and returns JSON on stdout:
    {"score": 84, "reason": "...", "judge": "gemini-vision"}

Falls back to a deterministic heuristic if no key / quota. Reads GEMINI_API_KEY from the
process env or from video-processor/.env. Stdlib-friendly caller contract: prints ONE json line.
"""
import json, os, sys
from pathlib import Path
from dotenv import load_dotenv

REPO = Path(__file__).resolve().parents[2]
for envp in (REPO / ".env", REPO / "video-processor" / ".env", REPO / ".claude" / "scripts" / ".env"):
    if envp.exists():
        load_dotenv(envp, override=False)

def heuristic(img: Path) -> dict:
    size = img.stat().st_size if img.exists() else 50000
    return {"score": int(55 + (size // 4096) % 40), "reason": "heuristic (no vision key/quota)", "judge": "heuristic"}

def main() -> int:
    if len(sys.argv) < 2:
        print(json.dumps({"score": 0, "reason": "no path", "judge": "error"})); return 1
    img = Path(sys.argv[1])
    concept = sys.argv[2] if len(sys.argv) > 2 else ""
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not key or not img.exists() or img.suffix.lower() not in (".jpg", ".jpeg", ".png"):
        print(json.dumps(heuristic(img))); return 0
    try:
        from google import genai
        from google.genai import types
        client = genai.Client(api_key=key)
        rubric = ("Rate this image as a short-form video AD key frame for scroll-stopping virality, 0-100. "
                  "Weigh: subject clarity, thumb-stopping composition, emotional pull, production polish, "
                  "and whether any on-image text is legible (garbled AI text is a heavy penalty). "
                  "REPUTATION-SAFETY RULES (this is a brand-safe product catalog): "
                  "an identifiable human FACE is a hard penalty (subtract 40+); the ad must not read as "
                  "featuring a real person. Human HANDS or arms handling the product are FINE and NOT penalized. "
                  "Alcohol, cocktails, beer, wine, spirits, or bar/liquor-bottle settings are a hard penalty "
                  "(subtract 40+) - this is a coffee and hydration brand, keep it non-alcoholic. "
                  f"Concept: {concept or 'n/a'}. Respond ONLY as JSON: "
                  '{"score": <int 0-100>, "reason": "<one sentence>"}.')
        resp = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[types.Part.from_bytes(data=img.read_bytes(), mime_type="image/jpeg"), rubric],
        )
        txt = (resp.text or "").strip().strip("`")
        if txt.startswith("json"):
            txt = txt[4:]
        obj = json.loads(txt[txt.find("{"): txt.rfind("}") + 1])
        score = int(max(0, min(100, obj.get("score", 60))))
        print(json.dumps({"score": score, "reason": obj.get("reason", ""), "judge": "gemini-vision"}))
    except Exception as e:
        h = heuristic(img); h["reason"] = f"heuristic (judge error: {str(e)[:80]})"
        print(json.dumps(h))
    return 0

if __name__ == "__main__":
    sys.exit(main())
