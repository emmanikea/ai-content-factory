#!/usr/bin/env python3
"""Retired legacy media-worker entry point.

The original implementation included direct vendor-specific generation and could bypass the
current UGC Studio provider/spend policy. It is intentionally disabled.

Current media workflow work belongs in:
  - .archon/scripts/ugc/
  - ugc-studio/providers/comfy/
  - docs/ugc-factory/COMFY_WORKFLOW_STACK.md

Historical implementation remains available in git history. Re-enabling it requires an explicit
repository policy change; changing an environment variable is not enough.
"""
from __future__ import annotations

import sys


def main() -> int:
    print(
        "media_worker.py is a retired legacy generation entry point and performs no generation. "
        "Use UGC Studio plus a validated Comfy recipe (or an explicitly approved direct route).",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
