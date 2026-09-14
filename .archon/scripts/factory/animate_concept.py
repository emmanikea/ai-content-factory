#!/usr/bin/env python3
"""Retired legacy concept renderer.

This entry point previously called a vendor-specific video runtime directly. It now fails closed so
old commands cannot bypass the Comfy-first UGC Studio architecture and spend gates.
"""
from __future__ import annotations

import sys


def main() -> int:
    print(
        "animate_concept.py is retired and performs no generation. Use a validated Comfy product-I2V "
        "recipe or an explicitly approved direct UGC Studio route.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
