#!/usr/bin/env python3
"""Compatibility CLI for UGC render planning.

The routing implementation lives in model_router.py. Direct model providers are the
default; Higgsfield is excluded unless explicitly allowed.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from model_router import plan_spec


def plan(spec: dict, *, allow_higgsfield: bool = False, allow_selfhost: bool = False) -> dict:
    return plan_spec(
        spec,
        allow_higgsfield=allow_higgsfield,
        allow_selfhost=allow_selfhost,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Plan UGC renders without spending money.")
    parser.add_argument("spec", help="Path to CreativeSpec JSON")
    parser.add_argument("--out", help="Optional output path")
    parser.add_argument("--allow-higgsfield", action="store_true")
    parser.add_argument("--allow-selfhost", action="store_true")
    args = parser.parse_args()

    spec = json.loads(Path(args.spec).read_text(encoding="utf-8"))
    result = plan(
        spec,
        allow_higgsfield=args.allow_higgsfield,
        allow_selfhost=args.allow_selfhost,
    )
    text = json.dumps(result, indent=2)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
    print(text)
    return 1 if result["blocked"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
