#!/usr/bin/env python3
"""Stage local Reel media into Remotion's public directory.

Remote HTTP(S) assets are left untouched. Local clip files are copied under
`public/assets/` and the output props JSON is rewritten to use Remotion static paths.
"""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from urllib.parse import urlparse


def is_remote(value: str) -> bool:
    return urlparse(value).scheme in {"http", "https", "data", "blob"}


def prepare(props_path: Path, assembly_dir: Path, out_path: Path) -> dict:
    props = json.loads(props_path.read_text(encoding="utf-8"))
    public_assets = assembly_dir / "public" / "assets"
    public_assets.mkdir(parents=True, exist_ok=True)

    for index, clip in enumerate(props.get("clips", []), start=1):
        src = clip.get("src")
        if not src or is_remote(src):
            continue

        source = Path(src)
        if not source.is_absolute():
            source = (props_path.parent / source).resolve()
        if not source.exists():
            raise FileNotFoundError(f"clip source does not exist: {source}")

        safe_id = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in str(clip.get("id") or index))
        ext = source.suffix or ".mp4"
        destination = public_assets / f"{safe_id}{ext}"
        shutil.copy2(source, destination)
        clip["src"] = f"assets/{destination.name}"

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(props, indent=2) + "\n", encoding="utf-8")
    return props


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("props", help="Timeline props JSON")
    parser.add_argument("--assembly-dir", default=str(Path(__file__).resolve().parent))
    parser.add_argument("--out", default="prepared.props.json")
    args = parser.parse_args()

    props_path = Path(args.props).resolve()
    assembly_dir = Path(args.assembly_dir).resolve()
    out_path = Path(args.out)
    if not out_path.is_absolute():
        out_path = assembly_dir / out_path

    result = prepare(props_path, assembly_dir, out_path)
    print(json.dumps({"prepared_props": str(out_path), "clip_count": len(result.get("clips", []))}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
