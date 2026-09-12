#!/usr/bin/env python3
"""Build a portable CreatorIdentityPack from an explicit manifest.

The builder is intentionally provider-neutral. It validates rights state, preserves
asset provenance, hashes local files, and emits onboarding warnings without inventing
face/identity quality judgments that require a vision model.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import mimetypes
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

REMOTE_SCHEMES = {"http", "https", "s3", "r2", "gs"}
IMAGE_VIEWS = {"front", "three_quarter", "profile", "full_body", "upper_body", "expression", "other"}
PERFORMANCE_TYPES = {"talking", "reaction", "gesture", "walking", "product_hold", "turn", "other"}


def _is_remote(uri: str) -> bool:
    return urlparse(uri).scheme.lower() in REMOTE_SCHEMES


def _resolve(uri: str, base: Path) -> Path | None:
    if _is_remote(uri):
        return None
    path = Path(uri).expanduser()
    if not path.is_absolute():
        path = (base / path).resolve()
    return path


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _ffprobe(path: Path) -> dict[str, Any]:
    """Best-effort local media metadata. Missing ffprobe never blocks pack creation."""
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "error", "-print_format", "json",
                "-show_entries", "stream=codec_type,width,height,duration:format=duration",
                str(path),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return {}
    payload = json.loads(result.stdout or "{}")
    streams = payload.get("streams") or []
    meta: dict[str, Any] = {}
    for stream in streams:
        if stream.get("width") and stream.get("height"):
            meta["width"] = int(stream["width"])
            meta["height"] = int(stream["height"])
            break
    duration = (payload.get("format") or {}).get("duration")
    if duration is None:
        duration = next((s.get("duration") for s in streams if s.get("duration")), None)
    if duration is not None:
        try:
            meta["duration_seconds"] = round(float(duration), 3)
        except (TypeError, ValueError):
            pass
    return meta


def _asset_meta(uri: str, base: Path) -> dict[str, Any]:
    path = _resolve(uri, base)
    if path is None:
        return {"source_kind": "remote"}
    if not path.exists() or not path.is_file():
        raise ValueError(f"asset not found: {uri}")
    stat = path.stat()
    meta = {
        "source_kind": "local",
        "sha256": _sha256(path),
        "bytes": stat.st_size,
        "mime_type": mimetypes.guess_type(path.name)[0],
    }
    meta.update(_ffprobe(path))
    return {k: v for k, v in meta.items() if v is not None}


def _validate_rights(manifest: dict[str, Any]) -> None:
    creator_type = manifest.get("creator_type", "real_consenting")
    rights = manifest.get("rights_snapshot") or {}
    consent = rights.get("consent_state")
    if creator_type == "synthetic":
        if consent not in {"not_required", "active"}:
            raise ValueError("synthetic creator rights_snapshot.consent_state must be not_required or active")
    elif consent != "active":
        raise ValueError("real/founder creator pack requires rights_snapshot.consent_state=active")
    if creator_type != "synthetic" and not rights.get("agreement_reference"):
        raise ValueError("real/founder creator pack requires rights_snapshot.agreement_reference")


def _decorate_asset(item: dict[str, Any], base: Path) -> dict[str, Any]:
    out = dict(item)
    out["provenance"] = _asset_meta(str(item["uri"]), base)
    return out


def build_identity_pack(manifest: dict[str, Any], *, base_dir: Path) -> dict[str, Any]:
    _validate_rights(manifest)
    creator_id = str(manifest.get("creator_id") or "").strip()
    if not creator_id:
        raise ValueError("creator_id is required")

    images = list(manifest.get("canonical_images") or [])
    if not images:
        raise ValueError("at least one canonical image is required")
    for item in images:
        if item.get("view") not in IMAGE_VIEWS:
            raise ValueError(f"invalid canonical image view: {item.get('view')!r}")
        if not item.get("id") or not item.get("uri"):
            raise ValueError("canonical images require id and uri")

    performances = list(manifest.get("performance_samples") or [])
    for item in performances:
        if item.get("performance_type") not in PERFORMANCE_TYPES:
            raise ValueError(f"invalid performance_type: {item.get('performance_type')!r}")
        if item.get("approved_for_motion_transfer") is True:
            allowed = set((manifest.get("rights_snapshot") or {}).get("allowed_transformations") or [])
            if "motion_transfer" not in allowed:
                raise ValueError(
                    f"performance {item.get('id')} marked for motion transfer but creator rights do not allow motion_transfer"
                )

    warnings: list[str] = []
    if len(images) < 5:
        warnings.append("fewer than 5 identity images; usable for some direct-reference models but weak for reusable identity onboarding")
    elif not 8 <= len(images) <= 12:
        warnings.append("8-12 varied identity images is the current recommended onboarding target; this pack is outside that range")

    views = {str(x.get("view")) for x in images}
    if "front" not in views:
        warnings.append("no front-facing canonical image")
    if not ({"three_quarter", "profile"} & views):
        warnings.append("no three-quarter/profile identity reference")
    if not ({"upper_body", "full_body"} & views):
        warnings.append("no upper-body/full-body reference")

    decorated_images = [_decorate_asset(item, base_dir) for item in images]
    voice_samples = [_decorate_asset(item, base_dir) for item in (manifest.get("voice_samples") or [])]
    performance_samples = [_decorate_asset(item, base_dir) for item in performances]

    return {
        "creator_id": creator_id,
        "creator_type": manifest.get("creator_type", "real_consenting"),
        "version": str(manifest.get("version") or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "canonical_images": decorated_images,
        "voice_samples": voice_samples,
        "performance_samples": performance_samples,
        "appearance_presets": manifest.get("appearance_presets") or {"outfits": [], "hairstyles": [], "locations": []},
        "provider_bindings": manifest.get("provider_bindings") or [],
        "rights_snapshot": manifest["rights_snapshot"],
        "quality_summary": {
            "identity_image_count": len(images),
            "views_present": sorted(views),
            "voice_sample_count": len(voice_samples),
            "performance_sample_count": len(performance_samples),
            "warnings": warnings,
            "semantic_identity_review_required": True,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a portable creator identity pack")
    parser.add_argument("manifest", help="Creator import manifest JSON")
    parser.add_argument("--out", required=True, help="Output CreatorIdentityPack JSON")
    args = parser.parse_args()

    manifest_path = Path(args.manifest).resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    pack = build_identity_pack(manifest, base_dir=manifest_path.parent)
    Path(args.out).write_text(json.dumps(pack, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(pack["quality_summary"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
