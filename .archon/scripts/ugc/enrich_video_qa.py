# /// script
# requires-python = ">=3.10"
# dependencies = ["google-genai>=1.0.0", "python-dotenv>=1.0.0"]
# ///
"""Optional multimodal visual QA enrichment for UGC Studio.

This stage supplements qa_video.py. It never erases deterministic failures and only marks
checks it actually evaluated. Lip-sync remains unresolved in this frame-based adapter.
"""
from __future__ import annotations

import argparse
import json
import mimetypes
import os
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None

REPO = Path(__file__).resolve().parents[3]
if load_dotenv:
    for envp in (REPO / ".env", REPO / "video-processor" / ".env", REPO / ".claude" / "scripts" / ".env"):
        if envp.exists():
            load_dotenv(envp, override=False)

DEFAULT_MODEL = os.environ.get("UGC_QA_GEMINI_MODEL", "gemini-2.5-flash")

PROFILE_CHECKS = {
    "creator_shot": ["identity_consistency", "face_anatomy", "hands_limbs", "visual_artifacts"],
    "app_capture": ["text_legibility", "unexpected_visual_artifacts"],
    "broll": ["visual_artifacts", "subject_consistency", "unexpected_text"],
    "final_reel": ["identity_consistency", "caption_legibility", "timeline_visual_coherence", "visual_artifacts"],
}


def _strip_fence(text: str) -> str:
    text = (text or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)
    return text.strip()


def parse_semantic_qa(text: str) -> dict[str, Any]:
    cleaned = _strip_fence(text)
    try:
        obj = json.loads(cleaned)
    except json.JSONDecodeError:
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start < 0 or end <= start:
            raise ValueError("QA model did not return a JSON object")
        obj = json.loads(cleaned[start:end + 1])
    if not isinstance(obj, dict):
        raise ValueError("QA model response must be a JSON object")
    if not isinstance(obj.get("checks"), dict):
        raise ValueError("QA model response requires a checks object")
    return obj


def extract_frames(video: Path, duration: float, outdir: Path, count: int = 6) -> list[Path]:
    if duration <= 0:
        return []
    positions = [min(duration - 0.05, max(0.0, duration * ((i + 0.5) / count))) for i in range(count)]
    frames: list[Path] = []
    for i, position in enumerate(positions):
        target = outdir / f"frame-{i:02d}.jpg"
        result = subprocess.run(
            ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-ss", f"{position:.3f}", "-i", str(video), "-frames:v", "1", "-q:v", "3", str(target)],
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode == 0 and target.exists():
            frames.append(target)
    return frames


def local_identity_refs(pack: dict[str, Any] | None, maximum: int = 4) -> list[Path]:
    if not pack:
        return []
    preferred = ("front", "three_quarter", "upper_body", "expression", "full_body", "profile", "other")
    result: list[Path] = []
    for view in preferred:
        for item in pack.get("canonical_images") or []:
            if item.get("view") != view:
                continue
            path = Path(str(item.get("uri") or "")).expanduser()
            if path.exists() and path.is_file() and path not in result:
                result.append(path)
                if len(result) >= maximum:
                    return result
    return result


def semantic_prompt(profile: str, concept: str = "", has_identity_refs: bool = False) -> str:
    checks = PROFILE_CHECKS[profile]
    identity_note = (
        "Canonical creator reference images are supplied before the generated-video frames. Compare identity only when those references are present."
        if has_identity_refs else
        "No local canonical creator references are supplied. Do not claim identity_consistency passed; return needs_review for that check if requested."
    )
    return (
        "You are a strict visual QA reviewer for a short-form UGC production pipeline. "
        "Judge only visible evidence in the supplied still frames. Do not infer rights, audio quality, or lip sync. "
        f"Profile: {profile}. Intended concept: {concept or 'not provided'}. {identity_note} "
        f"Evaluate only these checks: {', '.join(checks)}. "
        "For each check return status pass, fail, or needs_review and one short message. "
        "Fail identity consistency for material face/identity drift when canonical references are available. "
        "Fail anatomy for clearly deformed face, hands, fingers, limbs, duplicates, or melting. "
        "Fail visual/text checks for obvious generated gibberish, broken captions, blank frames, overlays, or visible generation artifacts. "
        "Use severity retryable for a generation defect that could improve on rerender; structural only for timeline/layout/source defects. "
        "Return JSON only: {\"score\":0-100,\"checks\":{\"check_name\":{\"status\":\"pass|fail|needs_review\",\"message\":\"...\"}},\"failures\":[{\"code\":\"...\",\"severity\":\"retryable|structural\",\"message\":\"...\"}]}"
    )


def merge_semantic_result(base: dict[str, Any], semantic: dict[str, Any], *, provider: str, model: str) -> dict[str, Any]:
    result = json.loads(json.dumps(base))
    allowed_names = {item["name"] for item in result.get("semantic_checks") or []}
    incoming = semantic.get("checks") or {}
    merged_checks = []
    for check in result.get("semantic_checks") or []:
        update = incoming.get(check["name"])
        if update and update.get("status") in {"pass", "fail", "needs_review"}:
            merged_checks.append({
                "name": check["name"],
                "status": update["status"],
                "value": None,
                "message": str(update.get("message") or ""),
            })
        else:
            merged_checks.append(check)
    result["semantic_checks"] = merged_checks

    failures = list(result.get("failures") or [])
    for failure in semantic.get("failures") or []:
        severity = failure.get("severity")
        if severity not in {"warning", "retryable", "structural"}:
            severity = "retryable"
        failures.append({
            "code": str(failure.get("code") or "semantic_qa_failure"),
            "severity": severity,
            "message": str(failure.get("message") or "semantic QA failure"),
        })
    result["failures"] = failures
    raw_score = semantic.get("score")
    if isinstance(raw_score, (int, float)):
        result["score"] = max(0, min(100, float(raw_score)))

    semantic_fail = any(check["status"] == "fail" for check in merged_checks)
    unresolved = any(check["status"] in {"needs_review", "not_run"} for check in merged_checks)
    deterministic_hard_fail = any(x.get("severity") in {"structural", "rights", "source"} for x in failures)
    if deterministic_hard_fail or semantic_fail:
        result["status"] = "fail"
        if any(x.get("severity") == "retryable" for x in failures) and not deterministic_hard_fail:
            result["retry_hint"] = "retry_same"
        else:
            result["retry_hint"] = "stop"
    elif unresolved:
        result["status"] = "needs_review"
        result["retry_hint"] = "manual_review"
    else:
        result["status"] = "pass"
        result["retry_hint"] = None

    provenance = dict(result.get("provenance") or {})
    provenance["semantic_qa"] = {"provider": provider, "model": model, "evaluated_checks": sorted(set(incoming) & allowed_names)}
    result["provenance"] = provenance
    return result


def enrich_with_gemini(
    base_qa: dict[str, Any],
    *,
    video: Path,
    identity_pack: dict[str, Any] | None,
    concept: str,
    model: str,
) -> dict[str, Any]:
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not key:
        raise RuntimeError("GEMINI_API_KEY or GOOGLE_API_KEY is required for semantic video QA")
    from google import genai
    from google.genai import types

    duration_check = next((x for x in base_qa.get("deterministic_checks") or [] if x.get("name") == "duration_readable"), None)
    duration = float((duration_check or {}).get("value") or 0)
    refs = local_identity_refs(identity_pack)
    with tempfile.TemporaryDirectory(prefix="ugc-qa-") as temp:
        frames = extract_frames(video, duration, Path(temp))
        if not frames:
            raise RuntimeError("no frames could be extracted for semantic QA")
        contents: list[Any] = [semantic_prompt(base_qa["profile"], concept, bool(refs))]
        for path in refs:
            mime = mimetypes.guess_type(path.name)[0] or "image/jpeg"
            contents.extend(["Canonical identity reference:", types.Part.from_bytes(data=path.read_bytes(), mime_type=mime)])
        for path in frames:
            contents.extend(["Generated video frame:", types.Part.from_bytes(data=path.read_bytes(), mime_type="image/jpeg")])

        client = genai.Client(api_key=key)
        response = client.models.generate_content(
            model=model,
            contents=contents,
            config={"temperature": 0, "response_mime_type": "application/json"},
        )
    semantic = parse_semantic_qa(response.text or "")
    return merge_semantic_result(base_qa, semantic, provider="google-genai", model=model)


def main() -> int:
    parser = argparse.ArgumentParser(description="Enrich deterministic QA with visual semantic checks")
    parser.add_argument("qa_json")
    parser.add_argument("--video", required=True)
    parser.add_argument("--identity-pack")
    parser.add_argument("--concept", default="")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--out", required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    base = json.loads(Path(args.qa_json).read_text(encoding="utf-8"))
    video = Path(args.video).resolve()
    pack = json.loads(Path(args.identity_pack).read_text(encoding="utf-8")) if args.identity_pack else None
    if args.dry_run:
        print(json.dumps({
            "profile": base.get("profile"),
            "model": args.model,
            "local_identity_references": [str(x) for x in local_identity_refs(pack)],
            "prompt": semantic_prompt(base["profile"], args.concept, bool(local_identity_refs(pack))),
        }, indent=2))
        return 0
    result = enrich_with_gemini(base, video=video, identity_pack=pack, concept=args.concept, model=args.model)
    Path(args.out).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"artifact_id": result["artifact_id"], "status": result["status"], "score": result.get("score"), "retry_hint": result.get("retry_hint")}, indent=2))
    return 1 if result["status"] == "fail" else 0


if __name__ == "__main__":
    raise SystemExit(main())
