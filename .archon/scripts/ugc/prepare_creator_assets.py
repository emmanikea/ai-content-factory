#!/usr/bin/env python3
"""Prepare a direct-render asset manifest from a CreatorIdentityPack.

This removes the normal need to hand-author `rights_approved: true`. Approval is derived
from the pack's rights snapshot for the requested product/platform/transformations. Current
creator revocation state is checked separately from the immutable pack snapshot when a
revocation store is supplied.
"""
from __future__ import annotations

import argparse
import json
import os
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from rights import evaluate_creator_rights

PREFERRED_VIEWS = ("front", "three_quarter", "upper_body", "expression", "full_body", "profile", "other")


def _remote(uri: str) -> bool:
    return urlparse(uri).scheme.lower() in {"http", "https"}


def _creator_for_rights(pack: dict[str, Any]) -> dict[str, Any]:
    return {
        "creator_type": pack.get("creator_type"),
        "rights": pack.get("rights_snapshot") or {},
    }


def select_identity_image(pack: dict[str, Any], preferred_view: str | None = None) -> dict[str, Any]:
    images = list(pack.get("canonical_images") or [])
    if not images:
        raise ValueError("creator pack has no canonical images")
    order = ((preferred_view,) if preferred_view else ()) + PREFERRED_VIEWS
    for view in order:
        if not view:
            continue
        candidate = next((item for item in images if item.get("view") == view), None)
        if candidate:
            return candidate
    return images[0]


def select_performance(pack: dict[str, Any], performance_id: str) -> dict[str, Any]:
    item = next((x for x in (pack.get("performance_samples") or []) if x.get("id") == performance_id), None)
    if not item:
        raise ValueError(f"performance sample not found: {performance_id}")
    if item.get("approved_for_motion_transfer") is not True:
        raise ValueError(f"performance sample is not approved for motion transfer: {performance_id}")
    return item


def prepare_assets(
    pack: dict[str, Any],
    *,
    product_id: str,
    product_category: str,
    platform: str,
    transformations: list[str],
    preferred_view: str | None = None,
    performance_id: str | None = None,
    on_date: date | None = None,
    require_remote: bool = False,
    revocation_store: Any | None = None,
) -> dict[str, Any]:
    creator_id = str(pack.get("creator_id") or "")
    if revocation_store is not None:
        from creator_revocation import assert_creator_active

        # Revocation is current-state authorization. The historical `on_date` below may be
        # useful for agreement-validity evaluation, but it must never let a new render bypass
        # a revocation that is active now.
        assert_creator_active(revocation_store, creator_id)

    decision = evaluate_creator_rights(
        _creator_for_rights(pack),
        product_id=product_id,
        product_category=product_category,
        platform=platform,
        transformations=transformations,
        on_date=on_date,
    )
    if not decision.allowed:
        raise ValueError("creator rights blocked render: " + "; ".join(decision.reasons))

    image = select_identity_image(pack, preferred_view)
    image_uri = str(image["uri"])
    if require_remote and not _remote(image_uri):
        raise ValueError("selected creator image is local; upload/stage it before direct hosted rendering")

    rights = pack.get("rights_snapshot") or {}
    checked_on = (on_date or date.today()).isoformat()
    output: dict[str, Any] = {
        "rights_approved": True,
        "rights_evidence": rights.get("agreement_reference") or f"creator-pack:{pack.get('creator_id')}:{pack.get('version')}",
        "rights_decision": {
            "checked_on": checked_on,
            "creator_id": pack.get("creator_id"),
            "creator_pack_version": pack.get("version"),
            "product_id": product_id,
            "product_category": product_category,
            "platform": platform,
            "transformations": transformations,
            "revocation_registry_checked": revocation_store is not None,
        },
        "creator_image_uri": image_uri,
        "creator_image_id": image.get("id"),
        "creator_image_view": image.get("view"),
        "needs_hosted_upload": not _remote(image_uri),
    }
    if _remote(image_uri):
        output["creator_image_url"] = image_uri

    if performance_id:
        performance = select_performance(pack, performance_id)
        motion_uri = str(performance["uri"])
        if "motion_transfer" not in transformations:
            raise ValueError("performance_id requires motion_transfer in requested transformations")
        if require_remote and not _remote(motion_uri):
            raise ValueError("selected motion video is local; upload/stage it before direct hosted rendering")
        output.update({
            "motion_video_uri": motion_uri,
            "motion_performance_id": performance_id,
            "motion_needs_hosted_upload": not _remote(motion_uri),
        })
        if _remote(motion_uri):
            output["motion_video_url"] = motion_uri

    return output


def main() -> int:
    parser = argparse.ArgumentParser(description="Derive direct-render assets and rights approval from a CreatorIdentityPack")
    parser.add_argument("pack")
    parser.add_argument("--product-id", required=True)
    parser.add_argument("--product-category", required=True)
    parser.add_argument("--platform", required=True)
    parser.add_argument("--transform", action="append", dest="transformations", default=[])
    parser.add_argument("--preferred-view")
    parser.add_argument("--performance-id")
    parser.add_argument("--on-date", help="YYYY-MM-DD; defaults to today")
    parser.add_argument("--require-remote", action="store_true")
    parser.add_argument("--store-root", default=os.environ.get("UGC_STORE_DIR", "ugc-studio/data"), help="Local store used for current creator-revocation checks")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    from local_store import LocalStore

    pack = json.loads(Path(args.pack).read_text(encoding="utf-8"))
    checked_date = date.fromisoformat(args.on_date) if args.on_date else None
    store = LocalStore(args.store_root)
    assets = prepare_assets(
        pack,
        product_id=args.product_id,
        product_category=args.product_category,
        platform=args.platform,
        transformations=args.transformations,
        preferred_view=args.preferred_view,
        performance_id=args.performance_id,
        on_date=checked_date,
        require_remote=args.require_remote,
        revocation_store=store,
    )
    Path(args.out).write_text(json.dumps(assets, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "rights_approved": True,
        "creator_image_id": assets["creator_image_id"],
        "needs_hosted_upload": assets["needs_hosted_upload"],
        "motion_performance_id": assets.get("motion_performance_id"),
        "revocation_registry_checked": True,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
