#!/usr/bin/env python3
"""Creator-rights revocation registry and propagation for UGC Studio.

CreatorIdentityPack rights snapshots are historical evidence and are not rewritten. Current
revocation state lives in a separate registry. Propagation disables stored jobs and marks
derived artifacts as blocked from reuse/distribution pending review.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
from datetime import date, datetime, time, timezone
from typing import Any

from local_store import LocalStore

COLLECTION = "revocations"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _as_datetime(value: datetime | date | str | None) -> datetime:
    if value is None:
        return _now()
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, date):
        return datetime.combine(value, time.max, tzinfo=timezone.utc)
    text = str(value).strip().replace("Z", "+00:00")
    parsed = datetime.fromisoformat(text)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def revocation_record_id(creator_id: str) -> str:
    digest = hashlib.sha256(creator_id.encode("utf-8")).hexdigest()[:24]
    return f"creator-revocation-{digest}"


def get_revocation(store: LocalStore, creator_id: str) -> dict[str, Any] | None:
    row = store.get(COLLECTION, revocation_record_id(creator_id))
    if not row or row.get("creator_id") != creator_id:
        return None
    return row


def is_creator_revoked(
    store: LocalStore,
    creator_id: str,
    *,
    at: datetime | date | str | None = None,
) -> bool:
    row = get_revocation(store, creator_id)
    if not row or row.get("status") != "revoked":
        return False
    effective = _as_datetime(row.get("effective_at"))
    return effective <= _as_datetime(at)


def assert_creator_active(
    store: LocalStore,
    creator_id: str,
    *,
    at: datetime | date | str | None = None,
) -> None:
    if not is_creator_revoked(store, creator_id, at=at):
        return
    row = get_revocation(store, creator_id) or {}
    raise ValueError(
        f"creator rights revoked for {creator_id}: effective {row.get('effective_at')}; "
        f"reason={row.get('reason') or 'not specified'}"
    )


def _document_creator_id(document: dict[str, Any]) -> str | None:
    for key in ("creator_id", "source_creator_id"):
        if document.get(key):
            return str(document[key])
    for container_key in ("provenance", "rights_decision", "metadata"):
        nested = document.get(container_key)
        if isinstance(nested, dict) and nested.get("creator_id"):
            return str(nested["creator_id"])
    return None


def _revocation_marker(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "creator_id": record["creator_id"],
        "effective_at": record["effective_at"],
        "recorded_at": record["recorded_at"],
        "reason": record.get("reason"),
        "evidence_reference": record.get("evidence_reference"),
    }


def _propagate_collection(
    store: LocalStore,
    collection: str,
    creator_id: str,
    record: dict[str, Any],
) -> list[str]:
    affected: list[str] = []
    marker = _revocation_marker(record)
    for row in store.list(collection):
        document = store.get(collection, row["id"])
        if not document or _document_creator_id(document) != creator_id:
            continue
        updated = copy.deepcopy(document)
        if collection == "jobs":
            updated["rights_approved"] = False
            updated["approved_for_spend"] = False
            updated["rights_status"] = "revoked"
            updated["revocation"] = marker
        elif collection == "artifacts":
            updated["rights_status"] = "revoked"
            updated["reuse_blocked"] = True
            updated["distribution_review_required"] = True
            updated["revocation"] = marker
        else:
            continue
        if updated == document:
            continue
        store.put(collection, row["id"], updated, expected_version=int(row["store_version"]))
        affected.append(row["id"])
    return affected


def apply_revocation(store: LocalStore, creator_id: str, *, now: datetime | None = None) -> dict[str, Any]:
    record = get_revocation(store, creator_id)
    if not record:
        raise ValueError(f"no revocation record found for creator: {creator_id}")
    current = now or _now()
    effective = _as_datetime(record["effective_at"])
    if effective > current:
        return {
            "creator_id": creator_id,
            "applied": False,
            "reason": "revocation_not_effective_yet",
            "effective_at": record["effective_at"],
            "affected_jobs": [],
            "affected_artifacts": [],
        }
    affected_jobs = _propagate_collection(store, "jobs", creator_id, record)
    affected_artifacts = _propagate_collection(store, "artifacts", creator_id, record)
    return {
        "creator_id": creator_id,
        "applied": True,
        "effective_at": record["effective_at"],
        "affected_jobs": affected_jobs,
        "affected_artifacts": affected_artifacts,
    }


def record_revocation(
    store: LocalStore,
    creator_id: str,
    *,
    reason: str,
    effective_at: datetime | str | None = None,
    evidence_reference: str | None = None,
    propagate: bool = True,
) -> dict[str, Any]:
    if not creator_id.strip():
        raise ValueError("creator_id is required")
    if not reason.strip():
        raise ValueError("revocation reason is required")
    record_id = revocation_record_id(creator_id)
    if store.get(COLLECTION, record_id) is not None:
        raise ValueError(f"creator already has a revocation record: {creator_id}")
    now = _now()
    effective = _as_datetime(effective_at) if effective_at is not None else now
    record = {
        "creator_id": creator_id,
        "status": "revoked",
        "effective_at": effective.astimezone(timezone.utc).isoformat(),
        "recorded_at": now.isoformat(),
        "reason": reason.strip(),
        "evidence_reference": evidence_reference,
    }
    store.put(COLLECTION, record_id, record, expected_version=0)
    applied = {
        "creator_id": creator_id,
        "applied": False,
        "effective_at": record["effective_at"],
        "affected_jobs": [],
        "affected_artifacts": [],
    }
    if propagate:
        applied = apply_revocation(store, creator_id, now=now)
    return {
        "revocation_id": record_id,
        "record": record,
        "propagated": applied["applied"],
        "affected_jobs": applied["affected_jobs"],
        "affected_artifacts": applied["affected_artifacts"],
        "note": (
            "Historical creator packs/specs/performance records remain unchanged for audit. "
            "Artifact flags require external takedown/review workflows to enforce removal outside UGC Studio storage."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Manage creator-rights revocation state")
    parser.add_argument("--root", default=os.environ.get("UGC_STORE_DIR", "ugc-studio/data"))
    sub = parser.add_subparsers(dest="command", required=True)

    revoke = sub.add_parser("revoke")
    revoke.add_argument("creator_id")
    revoke.add_argument("--reason", required=True)
    revoke.add_argument("--effective-at", help="ISO timestamp; defaults to now")
    revoke.add_argument("--evidence-reference")
    revoke.add_argument("--no-propagate", action="store_true")

    apply_cmd = sub.add_parser("apply")
    apply_cmd.add_argument("creator_id", help="Apply an existing revocation that is now effective")

    status = sub.add_parser("status")
    status.add_argument("creator_id")
    status.add_argument("--at", help="ISO timestamp/date to evaluate; defaults to now")

    args = parser.parse_args()
    store = LocalStore(args.root)
    if args.command == "revoke":
        result = record_revocation(
            store,
            args.creator_id,
            reason=args.reason,
            effective_at=args.effective_at,
            evidence_reference=args.evidence_reference,
            propagate=not args.no_propagate,
        )
        print(json.dumps(result, indent=2))
        return 0
    if args.command == "apply":
        print(json.dumps(apply_revocation(store, args.creator_id), indent=2))
        return 0

    row = get_revocation(store, args.creator_id)
    print(json.dumps({
        "creator_id": args.creator_id,
        "revoked": is_creator_revoked(store, args.creator_id, at=args.at),
        "record": row,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
