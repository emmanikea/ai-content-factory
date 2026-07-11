#!/usr/bin/env python3
"""
claim.py - the shared work queue for the factory's worker pool.

Parallel worker loop-nodes call this each iteration to atomically claim the NEXT unit of work,
so no two workers ever grab the same one. Claiming is a filesystem-atomic `mkdir` (only one
worker wins the race). Prints a single JSON line describing the claimed work + the exact output
paths the worker should use, or the literal `NONE` when the queue is empty (worker then stops).

Modes:
  claim.py product   -> next catalog product with no concepts yet (for content-factory-explore)
  claim.py render    -> next human-approved concept with no video yet (for content-factory-render)

Env: SITE_DIR (default: the Camber catalog-site).
"""
import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
DEFAULT_SITE = REPO / "catalog-site"
SITE = Path(os.environ.get("SITE_DIR", str(DEFAULT_SITE)))


def try_claim(claim_dir: Path, key: str) -> bool:
    """Atomically claim `key`. Returns True if we won the claim, False if already taken."""
    claim_dir.mkdir(parents=True, exist_ok=True)
    try:
        (claim_dir / key).mkdir()  # atomic: raises if it already exists
        return True
    except FileExistsError:
        return False


def claim_product() -> int:
    catalog = json.loads((SITE / "catalog.json").read_text(encoding="utf-8"))
    claims = SITE / "review" / ".claims-product"
    for p in catalog["products"]:
        pid = p["id"]
        if (SITE / "review" / pid / "concepts.json").exists():
            continue  # already built in a prior run (idempotent)
        if not try_claim(claims, pid):
            continue  # another worker owns it
        base = SITE / "review" / pid
        print(json.dumps({
            "product_id": pid, "name": p["name"], "category": p.get("category", ""),
            "description": p.get("description", ""), "image_prompt": p.get("image_prompt", ""),
            "outdir_a": str(base / f"{pid}-a"), "outdir_b": str(base / f"{pid}-b"),
            "concepts_json": str(base / "concepts.json"),
        }))
        return 0
    print("NONE")
    return 0


def claim_render() -> int:
    approved = set(json.loads((SITE / "approvals.json").read_text(encoding="utf-8")).get("approved", []))
    qp = SITE / "review" / "queue.json"
    queue = json.loads(qp.read_text(encoding="utf-8")) if qp.exists() else {"products": []}
    claims = SITE / "review" / ".claims-render"
    for p in queue.get("products", []):
        for c in p.get("concepts", []):
            cid = c["concept_id"]
            cdir = SITE / "review" / c["product_id"] / cid
            if cid not in approved or (cdir / "asset.mp4").exists():
                continue
            if not try_claim(claims, cid):
                continue
            print(json.dumps({
                "product_id": c["product_id"], "concept_id": cid, "angle": c.get("angle", ""),
                "frame": str(cdir / "frame.jpg"), "aspect_ratio": c.get("aspect_ratio", "9:16"),
            }))
            return 0
    print("NONE")
    return 0


def reset(kind: str) -> int:
    """Clear stale claim locks at the start of a run (a crashed prior run may leave locks)."""
    import shutil
    d = SITE / "review" / (".claims-product" if kind == "product" else ".claims-render")
    if d.exists():
        shutil.rmtree(d, ignore_errors=True)
    d.mkdir(parents=True, exist_ok=True)
    print(f"reset {d}")
    return 0


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else "product"
    if mode == "reset-product":
        return reset("product")
    if mode == "reset-render":
        return reset("render")
    return claim_product() if mode == "product" else claim_render()


if __name__ == "__main__":
    sys.exit(main())
