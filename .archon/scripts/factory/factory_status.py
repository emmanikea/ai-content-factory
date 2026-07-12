#!/usr/bin/env python3
"""
factory_status.py - free, read-only health + cost preview for the content factory.

Reports catalog/queue/approvals state, checks data integrity (every referenced image/video
exists on disk, every approved concept is renderable), and previews credit cost of the next
explore/render without spending anything.

Usage: python factory_status.py            # full report
       python factory_status.py --json      # machine-readable
Env: SITE_DIR, IMAGE_COST (0.15), VIDEO_COST (7.5).
"""
import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
DEFAULT_SITE = (REPO / "catalog-site") if (REPO / "catalog-site").exists() else (REPO / "Dynamous" / "Content-Ideation" / "2026-07-07" / "higgsfield-archon" / "catalog-site")
SITE = Path(os.environ.get("SITE_DIR", str(DEFAULT_SITE)))
IMAGE_COST = float(os.environ.get("IMAGE_COST", "0.15"))
VIDEO_COST = float(os.environ.get("VIDEO_COST", "7.5"))


def load(p, default):
    try:
        return json.loads((SITE / p).read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return default


def main() -> int:
    as_json = "--json" in sys.argv
    catalog = load("catalog.json", {"products": []})
    queue = load("review/queue.json", {"products": []})
    approvals = load("approvals.json", {"approved": []})
    approved = set(approvals.get("approved", []))

    n_products = len(catalog.get("products", []))
    concepts = [c for p in queue.get("products", []) for c in p.get("concepts", [])]
    n_concepts = len(concepts)
    rendered = [c for c in concepts if c.get("video")]
    approved_concepts = [c for c in concepts if c["concept_id"] in approved]
    approved_no_video = [c for c in approved_concepts if not c.get("video")]

    # Integrity checks
    issues = []
    for c in concepts:
        img = c.get("image")
        if not img or not (SITE / img).exists():
            issues.append(f"missing concept image: {c['concept_id']} ({img})")
        if c.get("video") and not (SITE / c["video"]).exists():
            issues.append(f"queue says video but file missing: {c['concept_id']}")
    for pid in {c["product_id"] for c in concepts}:
        if not (SITE / "images" / f"{pid}.jpg").exists():
            issues.append(f"missing catalog image: {pid}.jpg")
    # approvals referencing unknown concepts
    known = {c["concept_id"] for c in concepts}
    for cid in approved:
        if cid not in known:
            issues.append(f"approval references unknown concept: {cid}")
    # approved concept must have a frame to render
    for c in approved_no_video:
        frame = SITE / "review" / c["product_id"] / c["concept_id"] / "frame.jpg"
        if not frame.exists():
            issues.append(f"approved concept has no frame to render: {c['concept_id']}")

    remaining_products = n_products - len({c["product_id"] for c in concepts})
    explore_next_cost = remaining_products * 2 * IMAGE_COST  # 2 concepts/product
    render_next_cost = len(approved_no_video) * VIDEO_COST

    report = {
        "catalog_products": n_products,
        "explored_products": len({c["product_id"] for c in concepts}),
        "concepts": n_concepts,
        "approved": len(approved_concepts),
        "rendered_videos": len(rendered),
        "approved_awaiting_render": len(approved_no_video),
        "integrity_issues": issues,
        "cost_preview": {
            "explore_remaining_products": remaining_products,
            "explore_remaining_credits": round(explore_next_cost, 2),
            "render_approved_credits": round(render_next_cost, 2),
        },
    }
    if as_json:
        print(json.dumps(report, indent=2))
        return 0

    print("=== CONTENT FACTORY STATUS ===")
    print(f"  catalog products      : {n_products}")
    print(f"  explored (have concepts): {report['explored_products']}")
    print(f"  ad concepts           : {n_concepts}")
    print(f"  approved              : {len(approved_concepts)}")
    print(f"  rendered videos       : {len(rendered)}")
    print(f"  approved awaiting render: {len(approved_no_video)}")
    print("--- integrity ---")
    if issues:
        for i in issues:
            print(f"  ISSUE: {i}")
    else:
        print("  OK - all referenced images/videos exist, approvals valid, approved concepts renderable.")
    print("--- cost preview (no spend) ---")
    print(f"  explore remaining {remaining_products} products : ~{explore_next_cost:.2f} credits")
    print(f"  render {len(approved_no_video)} approved concept(s)   : ~{render_next_cost:.2f} credits")
    return 1 if issues else 0


if __name__ == "__main__":
    sys.exit(main())
