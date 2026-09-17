#!/usr/bin/env python3
"""Fail CI if active runtime files reintroduce retired Higgsfield execution commands.

Historical research/docs may mention Higgsfield. This check is about executable paths and active
Archon workflows, not deleting history.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SELF = Path(__file__).resolve()

# These strings represent executable/runtime coupling rather than harmless historical discussion.
FORBIDDEN = (
    "higgsfield generate",
    "higgsfield auth",
    "@higgsfield/cli",
    "--backend higgsfield",
    "mcp.higgsfield.ai",
)

SCAN_ROOTS = (
    ROOT / ".archon" / "workflows",
    ROOT / ".archon" / "scripts",
    ROOT / "ugc-studio" / "providers",
    ROOT / "ugc-studio" / "capture",
    ROOT / "ugc-studio" / "assembly",
)

# Research/provenance files are allowed to record external sources and policies.
ALLOW = {
    ROOT / "ugc-studio" / "providers" / "research-sources.json",
    ROOT / "ugc-studio" / "providers" / "model-registry.json",
}

TEXT_SUFFIXES = {".py", ".yaml", ".yml", ".json", ".js", ".mjs", ".ts", ".tsx", ".sh", ".md"}


def main() -> int:
    violations: list[str] = []
    for base in SCAN_ROOTS:
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if (
                not path.is_file()
                or path.suffix.lower() not in TEXT_SUFFIXES
                or path in ALLOW
                or path.resolve() == SELF
            ):
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="ignore").lower()
            except OSError:
                continue
            for token in FORBIDDEN:
                if token in text:
                    violations.append(f"{path.relative_to(ROOT)}: contains forbidden runtime token {token!r}")

    if violations:
        print("Provider policy violations:")
        for item in violations:
            print(f"- {item}")
        print("Higgsfield research may remain in docs, but executable generation paths are disabled.")
        return 1

    print("Provider policy OK: no retired Higgsfield runtime commands in active execution paths.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
