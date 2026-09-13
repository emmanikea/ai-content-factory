#!/usr/bin/env python3
"""Small atomic filesystem store for UGC Studio domain objects.

V1 intentionally keeps persistence simple and inspectable. Each record is wrapped in a
store envelope so strict domain JSON schemas remain unchanged. This boundary can later
map to Postgres/R2 without changing callers.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

COLLECTIONS = {
    "campaigns",
    "creators",
    "references",
    "specs",
    "jobs",
    "artifacts",
    "qa",
    "performance",
}
ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


class StoreConflict(RuntimeError):
    pass


class LocalStore:
    def __init__(self, root: Path | str):
        self.root = Path(root).expanduser().resolve()

    def _collection(self, collection: str) -> Path:
        if collection not in COLLECTIONS:
            raise ValueError(f"unknown collection {collection!r}; allowed: {', '.join(sorted(COLLECTIONS))}")
        return self.root / collection

    def _path(self, collection: str, record_id: str) -> Path:
        if not ID_RE.fullmatch(record_id):
            raise ValueError("record id must be 1-128 characters using letters, numbers, dot, underscore or dash")
        return self._collection(collection) / f"{record_id}.json"

    def get_envelope(self, collection: str, record_id: str) -> dict[str, Any] | None:
        path = self._path(collection, record_id)
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def get(self, collection: str, record_id: str) -> dict[str, Any] | None:
        envelope = self.get_envelope(collection, record_id)
        return None if envelope is None else envelope["document"]

    def put(
        self,
        collection: str,
        record_id: str,
        document: dict[str, Any],
        *,
        expected_version: int | None = None,
    ) -> dict[str, Any]:
        path = self._path(collection, record_id)
        current = self.get_envelope(collection, record_id)
        current_version = int(current["store_version"]) if current else 0
        if expected_version is not None and expected_version != current_version:
            raise StoreConflict(
                f"version conflict for {collection}/{record_id}: expected {expected_version}, current {current_version}"
            )
        now = datetime.now(timezone.utc).isoformat()
        envelope = {
            "collection": collection,
            "id": record_id,
            "store_version": current_version + 1,
            "created_at": current.get("created_at") if current else now,
            "updated_at": now,
            "document": document,
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, temp_name = tempfile.mkstemp(prefix=f".{record_id}.", suffix=".tmp", dir=str(path.parent))
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(envelope, handle, indent=2)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_name, path)
        finally:
            if os.path.exists(temp_name):
                os.unlink(temp_name)
        return envelope

    def delete(self, collection: str, record_id: str, *, expected_version: int | None = None) -> bool:
        path = self._path(collection, record_id)
        current = self.get_envelope(collection, record_id)
        if current is None:
            return False
        if expected_version is not None and int(current["store_version"]) != expected_version:
            raise StoreConflict(
                f"version conflict for {collection}/{record_id}: expected {expected_version}, current {current['store_version']}"
            )
        path.unlink()
        return True

    def list(self, collection: str) -> list[dict[str, Any]]:
        directory = self._collection(collection)
        if not directory.exists():
            return []
        rows = []
        for path in sorted(directory.glob("*.json")):
            envelope = json.loads(path.read_text(encoding="utf-8"))
            rows.append({
                "id": envelope["id"],
                "store_version": envelope["store_version"],
                "created_at": envelope["created_at"],
                "updated_at": envelope["updated_at"],
            })
        return rows


def main() -> int:
    parser = argparse.ArgumentParser(description="UGC Studio local domain store")
    parser.add_argument("--root", default=os.environ.get("UGC_STORE_DIR", "ugc-studio/data"))
    sub = parser.add_subparsers(dest="command", required=True)

    put = sub.add_parser("put")
    put.add_argument("collection", choices=sorted(COLLECTIONS))
    put.add_argument("id")
    put.add_argument("json_file")
    put.add_argument("--expected-version", type=int)

    get = sub.add_parser("get")
    get.add_argument("collection", choices=sorted(COLLECTIONS))
    get.add_argument("id")
    get.add_argument("--envelope", action="store_true")

    ls = sub.add_parser("list")
    ls.add_argument("collection", choices=sorted(COLLECTIONS))

    delete = sub.add_parser("delete")
    delete.add_argument("collection", choices=sorted(COLLECTIONS))
    delete.add_argument("id")
    delete.add_argument("--expected-version", type=int)

    args = parser.parse_args()
    store = LocalStore(args.root)

    if args.command == "put":
        document = json.loads(Path(args.json_file).read_text(encoding="utf-8"))
        print(json.dumps(store.put(args.collection, args.id, document, expected_version=args.expected_version), indent=2))
    elif args.command == "get":
        result = store.get_envelope(args.collection, args.id) if args.envelope else store.get(args.collection, args.id)
        if result is None:
            return 1
        print(json.dumps(result, indent=2))
    elif args.command == "list":
        print(json.dumps(store.list(args.collection), indent=2))
    elif args.command == "delete":
        deleted = store.delete(args.collection, args.id, expected_version=args.expected_version)
        print(json.dumps({"deleted": deleted}))
        return 0 if deleted else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
