#!/usr/bin/env python3
"""Strict JSON Schema validation for UGC Studio domain documents."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
SCHEMA_DIR = REPO_ROOT / "ugc-studio" / "schemas"

SCHEMAS = {
    "campaign_brief": "campaign-brief.schema.json",
    "creator": "creator.schema.json",
    "creator_identity_pack": "creator-identity-pack.schema.json",
    "creative_spec": "creative-spec.schema.json",
    "reference_observation": "reference-observation.schema.json",
    "reference_semantic_labels": "reference-semantic-labels.schema.json",
    "reference_analysis": "reference-analysis.schema.json",
    "qa_result": "qa-result.schema.json",
}

COLLECTION_SCHEMA = {
    "campaigns": "campaign_brief",
    "creators": "creator_identity_pack",
    "references": "reference_analysis",
    "specs": "creative_spec",
    "qa": "qa_result",
}


def load_schema(kind: str) -> dict[str, Any]:
    filename = SCHEMAS.get(kind)
    if not filename:
        raise ValueError(f"unknown schema kind {kind!r}; allowed: {', '.join(sorted(SCHEMAS))}")
    return json.loads((SCHEMA_DIR / filename).read_text(encoding="utf-8"))


def validate_document(kind: str, document: dict[str, Any]) -> None:
    try:
        from jsonschema import Draft202012Validator, FormatChecker
    except ImportError as exc:
        raise RuntimeError("jsonschema is required for strict UGC document validation") from exc

    schema = load_schema(kind)
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = sorted(validator.iter_errors(document), key=lambda e: list(e.absolute_path))
    if not errors:
        return
    lines = []
    for error in errors[:20]:
        path = ".".join(str(x) for x in error.absolute_path) or "$"
        lines.append(f"{path}: {error.message}")
    suffix = f"\n... and {len(errors) - 20} more" if len(errors) > 20 else ""
    raise ValueError("schema validation failed:\n" + "\n".join(lines) + suffix)


def validate_collection_document(collection: str, document: dict[str, Any]) -> bool:
    kind = COLLECTION_SCHEMA.get(collection)
    if kind is None:
        return False
    validate_document(kind, document)
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate UGC Studio JSON against a domain schema")
    parser.add_argument("kind", choices=sorted(SCHEMAS))
    parser.add_argument("json_file")
    args = parser.parse_args()
    document = json.loads(Path(args.json_file).read_text(encoding="utf-8"))
    validate_document(args.kind, document)
    print(json.dumps({"valid": True, "schema": args.kind, "file": args.json_file}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
