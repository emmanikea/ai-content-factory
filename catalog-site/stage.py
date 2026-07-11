#!/usr/bin/env python3
"""
stage.py - flip the storefront between two pre-generated states so a demo looks live without
waiting on any real generation.

The whole visible state lives in two small files: review/queue.json (whether each concept has a
`video`) and approvals.json (which concepts are approved). The video FILES stay on disk in both
states; we just show or hide them. So the switch is instant.

States (saved under _states/):
  empty : plain storefront, no ad concepts at all. -> what you show BEFORE kicking off the factory.
  ready : every product has its scored ad CONCEPTS on the review board, nothing approved, no videos.
          -> what you show after "explore" runs, and when you approve winners.
  done  : the approved winners are approved + their videos are loaded and playing (admin/review view).
          -> the payoff, after "render" runs.

Usage (run inside catalog-site/):
  python stage.py build     # snapshot current (post-render) queue+approvals into all three states
  python stage.py empty     # show the plain store (no concepts)
  python stage.py ready     # show State A  (concepts only, 0 approved)
  python stage.py done      # show State B  (winners approved + videos playing)
  python stage.py status    # what's live right now
"""
import json
import shutil
import sys
from pathlib import Path

SITE = Path(__file__).resolve().parent
QUEUE = SITE / "review" / "queue.json"
APPROVALS = SITE / "approvals.json"
STATES = SITE / "_states"


def load(p, default):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return default


def write(p, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2), encoding="utf-8")


def build():
    """Derive both states from the current, fully-rendered queue + approvals."""
    q = load(QUEUE, {"products": []})
    appr = load(APPROVALS, {"approved": []})
    approved = list(appr.get("approved", []))

    # DONE = current queue (videos present on approved+rendered concepts) + the approval set.
    write(STATES / "done" / "queue.json", q)
    write(STATES / "done" / "approvals.json", {"approved": sorted(approved)})

    # READY = same concepts, but every video hidden and nothing approved yet.
    q_ready = json.loads(json.dumps(q))
    for p in q_ready.get("products", []):
        for c in p.get("concepts", []):
            c["video"] = None
            c["approved"] = False
    write(STATES / "ready" / "queue.json", q_ready)
    write(STATES / "ready" / "approvals.json", {"approved": []})

    # EMPTY = plain store, no concepts at all.
    write(STATES / "empty" / "queue.json", {"products": []})
    write(STATES / "empty" / "approvals.json", {"approved": []})

    nvid = sum(1 for p in q.get("products", []) for c in p.get("concepts", []) if c.get("video"))
    print(f"built states: {len(q.get('products', []))} products, {len(approved)} approved, {nvid} videos")
    print(f"  -> {STATES/'ready'}  and  {STATES/'done'}")


def apply(state):
    src = STATES / state
    if not (src / "queue.json").exists():
        sys.exit(f"state '{state}' not built yet. Run: python stage.py build")
    shutil.copyfile(src / "queue.json", QUEUE)
    shutil.copyfile(src / "approvals.json", APPROVALS)
    appr = load(APPROVALS, {"approved": []})
    print(f"LIVE: {state}  ({len(appr.get('approved', []))} approved)  - refresh the storefront")


def status():
    q = load(QUEUE, {"products": []})
    appr = load(APPROVALS, {"approved": []})
    concepts = sum(len(p.get("concepts", [])) for p in q.get("products", []))
    vids = sum(1 for p in q.get("products", []) for c in p.get("concepts", []) if c.get("video"))
    print(f"live now: {len(q.get('products', []))} products, {concepts} concepts, "
          f"{len(appr.get('approved', []))} approved, {vids} videos shown")


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd == "build":
        build()
    elif cmd in ("empty", "ready", "done"):
        apply(cmd)
    else:
        status()


if __name__ == "__main__":
    main()
