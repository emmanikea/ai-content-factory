#!/usr/bin/env python3
"""Provider-neutral bridge from legacy Archon workers to the V2 Generation Studio.

This intentionally does not know OpenRouter or ComfyUI APIs. It only knows the Studio API,
so existing Python/Archon workflows can migrate one call site at a time without becoming
coupled to another media vendor.

Examples:
  python .archon/scripts/factory/generation_gateway.py submit \
    --prompt "cinematic coffee grinder product pan" --tier standard --duration 8

  python .archon/scripts/factory/generation_gateway.py wait --factory-job-id <uuid>

Set CONTENT_STUDIO_URL (default http://localhost:3000).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request

BASE = os.environ.get("CONTENT_STUDIO_URL", "http://localhost:3000").rstrip("/")


def request_json(path: str, method: str = "GET", payload: dict | None = None) -> dict:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(
        f"{BASE}{path}",
        data=data,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=900) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Studio HTTP {exc.code}: {body[:1200]}") from exc


def submit(args: argparse.Namespace) -> dict:
    payload: dict = {
        "prompt": args.prompt,
        "tier": args.tier,
        "duration": args.duration,
        "aspectRatio": args.aspect,
        "generateAudio": args.audio,
    }
    if args.provider:
        payload["provider"] = args.provider
    if args.model:
        payload["model"] = args.model
    if args.project_id:
        payload["projectId"] = args.project_id
    if args.character_id:
        payload["characterId"] = args.character_id
    if args.reference_url:
        payload["inputReferences"] = [{"url": url} for url in args.reference_url]
    return request_json("/api/generate", "POST", payload)


def wait_for_job(factory_job_id: str, interval: float, timeout: float) -> dict:
    deadline = time.time() + timeout
    last: dict = {}
    while time.time() < deadline:
        last = request_json(f"/api/generations/{factory_job_id}")
        status = last.get("status")
        if status in {"completed", "failed", "cancelled", "expired"}:
            return last
        time.sleep(interval)
    raise TimeoutError(f"generation {factory_job_id} did not finish within {timeout}s; last={last}")


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    p_submit = sub.add_parser("submit")
    p_submit.add_argument("--prompt", required=True)
    p_submit.add_argument("--tier", choices=["draft", "standard", "quality", "max"], default="standard")
    p_submit.add_argument("--provider", choices=["openrouter", "comfyui"])
    p_submit.add_argument("--model")
    p_submit.add_argument("--duration", type=int, default=8)
    p_submit.add_argument("--aspect", default="9:16")
    p_submit.add_argument("--audio", action=argparse.BooleanOptionalAction, default=True)
    p_submit.add_argument("--project-id")
    p_submit.add_argument("--character-id")
    p_submit.add_argument("--reference-url", action="append", default=[])
    p_submit.add_argument("--wait", action="store_true")
    p_submit.add_argument("--poll-interval", type=float, default=5.0)
    p_submit.add_argument("--timeout", type=float, default=1200.0)

    p_wait = sub.add_parser("wait")
    p_wait.add_argument("--factory-job-id", required=True)
    p_wait.add_argument("--poll-interval", type=float, default=5.0)
    p_wait.add_argument("--timeout", type=float, default=1200.0)

    args = parser.parse_args()

    try:
        if args.command == "submit":
            result = submit(args)
            if args.wait:
                factory_id = result.get("factoryJobId")
                if not factory_id:
                    raise RuntimeError(f"Studio response did not include factoryJobId: {result}")
                result = wait_for_job(factory_id, args.poll_interval, args.timeout)
        else:
            result = wait_for_job(args.factory_job_id, args.poll_interval, args.timeout)
        print(json.dumps(result, separators=(",", ":")))
        return 0
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
