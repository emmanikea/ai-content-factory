#!/usr/bin/env python3
"""Retired legacy catalog render path.

The original script invoked legacy vendor-specific renderers directly. It is intentionally disabled
so manual execution cannot bypass UGC Studio rights/spend/provider policy.
"""
from __future__ import annotations

import sys


def main() -> int:
    print(
        "factory_render.py is retired and performs no generation. Use UGC Studio plus a validated "
        "Comfy recipe or an explicitly approved direct hosted route.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
