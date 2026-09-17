#!/usr/bin/env python3
"""Retired legacy UGC renderer.

This entry point previously called a vendor-specific image/video runtime directly. It now fails
closed so old commands cannot bypass UGC Studio provider, rights, QA and spend policy.
"""
from __future__ import annotations

import sys


def main() -> int:
    print(
        "animate_ugc.py is retired and performs no generation. Build/use a validated Comfy creator "
        "workflow (including exact-audio/lip-sync where required) or an explicitly approved direct route.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
