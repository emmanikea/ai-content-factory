#!/usr/bin/env python3
"""
merge_queue.py - the finalize step of the fan-out explore workflow.

Each per-product Archon AGENT node writes a small fragment at review/<pid>/concepts.json
(its concept ids + angle/caption/aspect) and the concept images/scores under
review/<pid>/<cid>/ (frame.jpg + meta.json, produced by the Higgsfield CLI via media_worker).

This finalize node stitches every product's fragment into the single review/queue.json the
storefront reads - joining each concept with its vision score (meta.json) and any already
-rendered video (asset.mp4 on disk). Merge-safe: products explored in prior runs are kept.

Env: SITE_DIR (default Camber catalog-site).
"""
import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
DEFAULT_SITE = REPO / "catalog-site"
SITE = Path(os.environ.get("SITE_DIR", str(DEFAULT_SITE)))


def main() -> int:
    review = SITE / "review"
    catalog = json.loads((SITE / "catalog.json").read_text(encoding="utf-8"))
    order = {p["id"]: i for i, p in enumerate(catalog["products"])}
    names = {p["id"]: p["name"] for p in catalog["products"]}

    # 1. Read every per-product fragment produced by the agent nodes this run.
    run_products = {}
    for frag in review.glob("*/concepts.json"):
        try:
            f = json.loads(frag.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        pid = f.get("product_id") or frag.parent.name
        cs = []
        for c in f.get("concepts", []):
            cid = c["concept_id"]
            cdir = review / pid / cid
            score = None
            meta = cdir / "meta.json"
            if meta.exists():
                try:
                    score = json.loads(meta.read_text(encoding="utf-8")).get("score")
                except Exception:  # noqa: BLE001
                    pass
            if not (cdir / "frame.jpg").exists():
                continue  # generation failed for this concept - drop it
            video = f"review/{pid}/{cid}/asset.mp4" if (cdir / "asset.mp4").exists() else None
            cs.append({
                "product_id": pid, "product_name": f.get("product_name", names.get(pid, pid)),
                "concept_id": cid, "angle": c.get("angle", ""), "caption": c.get("caption", ""),
                "aspect_ratio": c.get("aspect_ratio", "9:16"),
                "image": f"review/{pid}/{cid}/frame.jpg", "score": score,
                "approved": False, "video": video,
            })
        if cs:
            cs.sort(key=lambda x: -(x.get("score") or 0))
            run_products[pid] = {"product_id": pid, "product_name": names.get(pid, pid), "concepts": cs}

    # 2. Merge into the existing queue (keep products explored in prior runs).
    merged = {}
    qp = review / "queue.json"
    if qp.exists():
        try:
            for p in json.loads(qp.read_text(encoding="utf-8")).get("products", []):
                merged[p["product_id"]] = p
        except Exception:  # noqa: BLE001
            pass
    merged.update(run_products)
    products = [merged[pid] for pid in sorted(merged, key=lambda x: order.get(x, 999))]

    queue = {"products": products,
             "counts": {"products": len(products),
                        "concepts": sum(len(p["concepts"]) for p in products)}}
    qp.write_text(json.dumps(queue, indent=2), encoding="utf-8")
    print(f"merge_queue: {queue['counts']} (this run wrote {len(run_products)} products)")
    for p in products:
        top = max((c.get("score") or 0) for c in p["concepts"]) if p["concepts"] else 0
        print(f"  {p['product_id']} {p['product_name']}: {len(p['concepts'])} concepts, top {top}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
