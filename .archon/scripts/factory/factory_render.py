#!/usr/bin/env python3
"""
factory_render.py - drive the RENDER phase over the approved winners (the same work the
content-factory-render workflow runs). For each approved concept it calls animate_concept.py,
which generates the Higgsfield video AND validates it (regenerating a bad take). Then merge_queue.

Usage: factory_render.py
Env: SITE_DIR, HF_VIDEO_RESOLUTION (720p to save credits), HF_VIDEO_DURATION (10), RENDER_MAX_TRIES.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

FACTORY = Path(__file__).resolve().parent
REPO = FACTORY.parents[2]
DEFAULT_SITE = REPO / "catalog-site"
SITE = Path(os.environ.get("SITE_DIR", str(DEFAULT_SITE)))


def main() -> int:
    approved = set(json.loads((SITE / "approvals.json").read_text(encoding="utf-8")).get("approved", []))
    queue = json.loads((SITE / "review" / "queue.json").read_text(encoding="utf-8"))
    # cid -> pid
    pid_of = {c["concept_id"]: p["product_id"] for p in queue.get("products", []) for c in p.get("concepts", [])}
    todo = [cid for cid in sorted(approved) if cid in pid_of]
    print(f"rendering {len(todo)} approved concepts: {todo}", flush=True)
    for i, cid in enumerate(todo, 1):
        pid = pid_of[cid]
        print(f"\n[{i}/{len(todo)}] {pid} {cid}", flush=True)
        r = subprocess.run([sys.executable, str(FACTORY / "animate_concept.py"), pid, cid],
                           capture_output=True, text=True, timeout=2400)
        sys.stdout.write(r.stdout)
        sys.stderr.write(r.stderr)
        sys.stdout.flush()
    print("\n=== merge_queue ===", flush=True)
    subprocess.run([sys.executable, str(FACTORY / "merge_queue.py")], check=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
