#!/usr/bin/env python3
"""Retired legacy catalog seed path.

The original script generated catalog concepts through a vendor-specific media worker. That path
is disabled to prevent bypassing the current UGC Studio provider/spend policy.
"""
from __future__ import annotations

import sys


def main() -> int:
    print(
        "factory_seed.py is retired and performs no generation. Use the current UGC Studio planning "
        "pipeline and validated Comfy workflows documented in docs/ugc-factory/COMFY_WORKFLOW_STACK.md.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
