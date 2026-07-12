#!/usr/bin/env python3
"""
curate_approvals.py - stand in for the human approval step so the demo site can be pre-built.

Reads the post-explore review/queue.json, picks the best-scoring concept for each product, then
approves the top N products by that winner score (default 12) with a little category spread, and
writes approvals.json. That is the set the render phase will animate.

Usage: curate_approvals.py [N]
Env: SITE_DIR, APPROVE_N.
"""
import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
DEFAULT_SITE = (REPO / "catalog-site") if (REPO / "catalog-site").exists() else (REPO / "Dynamous" / "Content-Ideation" / "2026-07-07" / "higgsfield-archon" / "catalog-site")
SITE = Path(os.environ.get("SITE_DIR", str(DEFAULT_SITE)))


def main() -> int:
    n = int(sys.argv[1]) if len(sys.argv) > 1 else int(os.environ.get("APPROVE_N", "12"))
    catalog = json.loads((SITE / "catalog.json").read_text(encoding="utf-8"))
    cat_of = {p["id"]: p.get("category", "") for p in catalog["products"]}
    queue = json.loads((SITE / "review" / "queue.json").read_text(encoding="utf-8"))

    # winner per product = highest-scored concept
    winners = []
    for p in queue.get("products", []):
        cs = [c for c in p.get("concepts", []) if (c.get("image"))]
        if not cs:
            continue
        best = max(cs, key=lambda c: (c.get("score") or 0))
        winners.append({"pid": p["product_id"], "cid": best["concept_id"],
                        "score": best.get("score") or 0, "cat": cat_of.get(p["product_id"], "")})

    winners.sort(key=lambda w: -w["score"])
    # take top N but guarantee at least 2 per category if available
    picked, per_cat = [], {}
    for w in winners:
        picked.append(w)
        per_cat[w["cat"]] = per_cat.get(w["cat"], 0) + 1
        if len(picked) >= n:
            break
    # ensure spread: if a category is missing, swap in its best
    cats = set(cat_of.values())
    for cat in cats:
        if per_cat.get(cat, 0) == 0:
            extra = next((w for w in winners if w["cat"] == cat and w not in picked), None)
            if extra and picked:
                picked[-1] = extra

    approved = sorted({w["cid"] for w in picked})
    (SITE / "approvals.json").write_text(json.dumps({"approved": approved}, indent=2), encoding="utf-8")
    print(f"approved {len(approved)} winners:")
    for w in picked:
        print(f"  {w['pid']} {w['cid']} score={w['score']} [{w['cat']}]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
