# /// script
# requires-python = ">=3.10"
# dependencies = ["google-genai>=1.0.0", "python-dotenv>=1.0.0"]
# ///
"""Automatically enrich a ReferenceObservation with semantic labels using vision.

This is an optional adapter, not a required runtime dependency. It consumes only the
facts/keyframes already produced by observe_reference.py and must return the strict
ReferenceSemanticLabels shape. If no vision credential is available it fails closed;
it never invents semantic labels from filenames or scene cuts.
"""
from __future__ import annotations

import argparse
import json
import mimetypes
import os
import re
import sys
from pathlib import Path
from typing import Any

from build_reference_analysis import build_reference_analysis, semantic_enrichment_prompt

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - uv/PEP723 normally supplies it
    load_dotenv = None

REPO = Path(__file__).resolve().parents[3]
if load_dotenv:
    for envp in (REPO / ".env", REPO / "video-processor" / ".env", REPO / ".claude" / "scripts" / ".env"):
        if envp.exists():
            load_dotenv(envp, override=False)

DEFAULT_GEMINI_MODEL = os.environ.get("REFERENCE_GEMINI_MODEL", "gemini-2.5-flash")


def _strip_fence(text: str) -> str:
    text = (text or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)
    return text.strip()


def parse_json_response(text: str) -> dict[str, Any]:
    cleaned = _strip_fence(text)
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start < 0 or end <= start:
            raise ValueError("vision model did not return a JSON object")
        parsed = json.loads(cleaned[start:end + 1])
    if not isinstance(parsed, dict):
        raise ValueError("vision model response must be a JSON object")
    return parsed


def collect_keyframes(observation: dict[str, Any]) -> list[tuple[str, Path]]:
    result: list[tuple[str, Path]] = []
    for segment in observation.get("segments") or []:
        raw = segment.get("keyframe_path")
        if not raw:
            continue
        path = Path(raw).expanduser()
        if path.exists() and path.is_file():
            result.append((segment["id"], path))
    return result


def validate_labels(observation: dict[str, Any], labels: dict[str, Any]) -> dict[str, Any]:
    """Use the final compiler as the semantic contract validator."""
    build_reference_analysis(observation, labels)
    return labels


def build_gemini_contents(observation: dict[str, Any]) -> list[Any]:
    from google.genai import types

    prompt = semantic_enrichment_prompt(observation)
    contents: list[Any] = [
        prompt,
        "Use the following segment keyframes as visual evidence. A keyframe is a sample from a segment, not proof of rights or the entire segment's motion."
    ]
    for segment_id, path in collect_keyframes(observation):
        mime = mimetypes.guess_type(path.name)[0] or "image/jpeg"
        contents.append(f"Keyframe for {segment_id}:")
        contents.append(types.Part.from_bytes(data=path.read_bytes(), mime_type=mime))
    if len(contents) == 2:
        contents.append("No keyframes were available. Use transcript/segment timing only and keep visual claims conservative.")
    return contents


def enrich_with_gemini(observation: dict[str, Any], *, model: str = DEFAULT_GEMINI_MODEL) -> tuple[dict[str, Any], dict[str, Any]]:
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not key:
        raise RuntimeError("GEMINI_API_KEY or GOOGLE_API_KEY is required for automatic semantic enrichment")
    from google import genai

    client = genai.Client(api_key=key)
    response = client.models.generate_content(
        model=model,
        contents=build_gemini_contents(observation),
        config={
            "temperature": 0,
            "response_mime_type": "application/json",
        },
    )
    labels = parse_json_response(response.text or "")
    labels.setdefault("reference_id", observation.get("id"))
    validate_labels(observation, labels)
    provenance = {
        "provider": "google-genai",
        "model": model,
        "keyframe_count": len(collect_keyframes(observation)),
        "observation_id": observation.get("id"),
        "observer_version": (observation.get("analysis") or {}).get("observer_version"),
        "rights_mode": observation.get("rights_mode"),
    }
    return labels, provenance


def main() -> int:
    parser = argparse.ArgumentParser(description="Create semantic labels from ReferenceObservation")
    parser.add_argument("observation")
    parser.add_argument("--out", required=True, help="ReferenceSemanticLabels JSON")
    parser.add_argument("--provenance-out", help="Optional semantic-analysis provenance JSON")
    parser.add_argument("--model", default=DEFAULT_GEMINI_MODEL)
    parser.add_argument("--dry-run", action="store_true", help="Print prompt/keyframe plan without calling a model")
    args = parser.parse_args()

    observation = json.loads(Path(args.observation).read_text(encoding="utf-8"))
    if args.dry_run:
        print(json.dumps({
            "model": args.model,
            "reference_id": observation.get("id"),
            "rights_mode": observation.get("rights_mode"),
            "keyframes": [str(path) for _, path in collect_keyframes(observation)],
            "prompt": semantic_enrichment_prompt(observation),
        }, indent=2))
        return 0

    labels, provenance = enrich_with_gemini(observation, model=args.model)
    Path(args.out).write_text(json.dumps(labels, indent=2) + "\n", encoding="utf-8")
    if args.provenance_out:
        Path(args.provenance_out).write_text(json.dumps(provenance, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"reference_id": labels.get("reference_id"), "beats": len(labels.get("beats") or []), **provenance}, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001
        sys.stderr.write(f"reference semantic enrichment failed: {exc}\n")
        raise SystemExit(1)
