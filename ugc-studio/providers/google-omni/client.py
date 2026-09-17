#!/usr/bin/env python3
"""Google Gemini Omni Flash video adapter for UGC Studio.

This lane is intentionally separate from Veo. Google currently recommends Gemini Omni Flash
as the default video-generation/editing model for coherence, multi-input reasoning, character
consistency and conversational editing. V1 keeps benchmark generation at 720p so its cost
preview has a documented basis (~$0.10/output-second); input-token charges remain separate.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import re
import time
from pathlib import Path
from typing import Any
from urllib import error, parse, request

DEFAULT_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
MODEL_ID = "gemini-omni-1.1-flash"
PRICING_CHECKED_AT = "2026-09-17"
PRICING_SOURCE = "https://ai.google.dev/gemini-api/docs/pricing"
VIDEO_OUTPUT_RATE_720P_USD_PER_SECOND = 0.10
ALLOWED_TASKS = {"text_to_video", "image_to_video", "reference_to_video", "edit", "extend"}


class GoogleOmniError(RuntimeError):
    pass


def _api_key(explicit: str | None = None) -> str:
    value = explicit or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not value:
        raise GoogleOmniError("GEMINI_API_KEY (or GOOGLE_API_KEY) is required for live Gemini Omni operations")
    return value.strip()


def _json_request(method: str, url: str, *, api_key: str, body: dict[str, Any] | None = None, timeout: float = 300.0) -> dict[str, Any]:
    payload = None if body is None else json.dumps(body).encode("utf-8")
    headers = {"x-goog-api-key": api_key}
    if payload is not None:
        headers["Content-Type"] = "application/json"
    req = request.Request(url, data=payload, headers=headers, method=method)
    try:
        with request.urlopen(req, timeout=timeout) as response:
            raw = response.read()
            return json.loads(raw.decode("utf-8")) if raw else {"http_status": getattr(response, "status", 200)}
    except error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            detail: Any = json.loads(raw)
        except json.JSONDecodeError:
            detail = raw
        raise GoogleOmniError(f"Gemini Omni HTTP {exc.code}: {detail}") from exc
    except error.URLError as exc:
        raise GoogleOmniError(f"Gemini Omni network error: {exc.reason}") from exc


def _validate_google_file_uri(uri: str) -> None:
    parsed = parse.urlparse(uri)
    host = (parsed.hostname or "").lower()
    if parsed.scheme != "https" or host != "generativelanguage.googleapis.com" or "/files/" not in parsed.path:
        raise GoogleOmniError("image/video uri must be a Gemini Files API URI; arbitrary remote URLs are not fetched by this adapter")


def validate_job(job: dict[str, Any]) -> dict[str, Any]:
    if job.get("provider") != "google-omni":
        raise GoogleOmniError("job.provider must be 'google-omni'")
    if job.get("model") != MODEL_ID:
        raise GoogleOmniError(f"V1 supports model {MODEL_ID!r}")
    req = job.get("request")
    if not isinstance(req, dict):
        raise GoogleOmniError("job.request must be a JSON object")
    if req.get("model") != MODEL_ID:
        raise GoogleOmniError("job.request.model must match job.model")
    inputs = req.get("input")
    if not isinstance(inputs, (str, list)) or (isinstance(inputs, list) and not inputs):
        raise GoogleOmniError("request.input must be non-empty text or a non-empty content array")
    if isinstance(inputs, list):
        for item in inputs:
            if not isinstance(item, dict) or not item.get("type"):
                raise GoogleOmniError("every request.input item must be an object with type")
            if item.get("type") in {"image", "video"}:
                if item.get("uri"):
                    _validate_google_file_uri(str(item["uri"]))
                elif item.get("data"):
                    if not item.get("mime_type"):
                        raise GoogleOmniError("inline image/video data requires mime_type")
                else:
                    raise GoogleOmniError("image/video input requires Google Files uri or inline base64 data")
    fmt = req.get("response_format") or {"type": "video", "resolution": "720p", "aspect_ratio": "9:16"}
    if not isinstance(fmt, dict) or fmt.get("type", "video") != "video":
        raise GoogleOmniError("request.response_format.type must be 'video'")
    resolution = str(fmt.get("resolution", "720p"))
    if resolution != "720p":
        raise GoogleOmniError("V1 benchmark adapter is limited to 720p so cost evidence stays comparable")
    aspect = str(fmt.get("aspect_ratio", "16:9"))
    if aspect not in {"9:16", "16:9"}:
        raise GoogleOmniError("response_format.aspect_ratio must be '9:16' or '16:9'")
    cfg = req.get("generation_config") or {}
    if not isinstance(cfg, dict):
        raise GoogleOmniError("generation_config must be an object")
    video_cfg = cfg.get("video_config") or {}
    task = video_cfg.get("task") if isinstance(video_cfg, dict) else None
    if task is not None and task not in ALLOWED_TASKS:
        raise GoogleOmniError(f"unsupported video_config.task: {task!r}")
    expected_duration = float(job.get("expected_duration_seconds") or 0)
    if expected_duration < 3 or expected_duration > 10:
        raise GoogleOmniError("expected_duration_seconds must be between 3 and 10 for Gemini Omni Flash")
    return {
        "model": MODEL_ID,
        "resolution": resolution,
        "aspect_ratio": aspect,
        "task": task,
        "expected_duration_seconds": expected_duration,
    }


def estimate_cost(job: dict[str, Any]) -> dict[str, Any]:
    validated = validate_job(job)
    usd = round(validated["expected_duration_seconds"] * VIDEO_OUTPUT_RATE_720P_USD_PER_SECOND, 4)
    return {
        "usd": usd,
        "rate_usd_per_second": VIDEO_OUTPUT_RATE_720P_USD_PER_SECOND,
        "expected_duration_seconds": validated["expected_duration_seconds"],
        "resolution": "720p",
        "pricing_checked_at": PRICING_CHECKED_AT,
        "pricing_source": PRICING_SOURCE,
        "cost_evidence_type": "official_effective_output_rate_approximation",
        "billing_note": "Approximate video-output cost only. Gemini Omni also charges input tokens; actual output duration/token use can differ from the caller expectation.",
    }


def submit(job: dict[str, Any], *, api_key: str | None = None, base_url: str = DEFAULT_BASE_URL) -> dict[str, Any]:
    return _json_request("POST", f"{base_url.rstrip('/')}/interactions", api_key=_api_key(api_key), body=job["request"])


def _video_contents(interaction: dict[str, Any]) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    for step in interaction.get("steps") or []:
        if not isinstance(step, dict):
            continue
        for content in step.get("content") or []:
            if isinstance(content, dict) and content.get("type") == "video":
                found.append(content)
    # Some API/SDK-shaped responses expose output_video directly.
    direct = interaction.get("output_video")
    if isinstance(direct, dict):
        found.append(direct)
    return found


def _file_id_from_uri(uri: str) -> str:
    _validate_google_file_uri(uri)
    match = re.search(r"/files/([^/:?]+)", uri)
    if not match:
        raise GoogleOmniError("could not extract Gemini file id from output URI")
    return match.group(1)


def wait_for_file(file_id: str, *, api_key: str | None = None, base_url: str = DEFAULT_BASE_URL, interval_seconds: float = 5.0, timeout_seconds: float = 600.0, sleep_fn=time.sleep) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_seconds
    while True:
        info = _json_request("GET", f"{base_url.rstrip('/')}/files/{parse.quote(file_id, safe='')}", api_key=_api_key(api_key))
        state = str(info.get("state") or "").upper()
        if state == "ACTIVE":
            return info
        if state == "FAILED":
            raise GoogleOmniError(f"generated Gemini file {file_id} entered FAILED state")
        if time.monotonic() >= deadline:
            raise GoogleOmniError(f"generated Gemini file {file_id} timed out after {timeout_seconds:.0f}s")
        sleep_fn(interval_seconds)


def download_file(file_id: str, destination: Path, *, api_key: str | None = None, base_url: str = DEFAULT_BASE_URL) -> None:
    url = f"{base_url.rstrip('/')}/files/{parse.quote(file_id, safe='')}:download?alt=media"
    req = request.Request(url, headers={"x-goog-api-key": _api_key(api_key)}, method="GET")
    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        with request.urlopen(req, timeout=180) as response, destination.open("wb") as handle:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                handle.write(chunk)
    except error.HTTPError as exc:
        raise GoogleOmniError(f"Gemini Omni video download failed: HTTP {exc.code}") from exc
    except error.URLError as exc:
        raise GoogleOmniError(f"Gemini Omni video download failed: {exc.reason}") from exc


def run_job(job: dict[str, Any], *, estimate_only: bool = False, live: bool = False, outdir: Path | None = None, api_key: str | None = None, base_url: str = DEFAULT_BASE_URL) -> dict[str, Any]:
    estimate = estimate_cost(job)
    preview = {
        "mode": "live" if live else ("estimate" if estimate_only else "dry-run"),
        "provider": "google-omni",
        "model": job["model"],
        "rights_approved": job.get("rights_approved") is True,
        "approved_for_spend": job.get("approved_for_spend") is True,
        "max_provider_cost_usd": job.get("max_provider_cost_usd"),
        "estimate": estimate,
        "request": job["request"],
    }
    maximum = job.get("max_provider_cost_usd")
    if maximum is not None and float(estimate["usd"]) > float(maximum):
        raise GoogleOmniError(f"estimated Gemini Omni output cost ${estimate['usd']:.4f} exceeds approved cap ${float(maximum):.4f}")
    if estimate_only or not live:
        return preview
    if job.get("rights_approved") is not True:
        raise GoogleOmniError("live render blocked: job.rights_approved must be true")
    if job.get("approved_for_spend") is not True:
        raise GoogleOmniError("live render blocked: job.approved_for_spend must be true")
    if maximum is None:
        raise GoogleOmniError("live render requires max_provider_cost_usd")

    key = _api_key(api_key)
    started = time.time()
    interaction = submit(job, api_key=key, base_url=base_url)
    status = str(interaction.get("status") or "completed").lower()
    if status in {"failed", "cancelled"}:
        raise GoogleOmniError(f"Gemini Omni interaction ended with status {status!r}: {interaction}")
    videos = _video_contents(interaction)
    if not videos:
        raise GoogleOmniError("Gemini Omni response did not contain video output")

    written: list[str] = []
    if outdir:
        outdir.mkdir(parents=True, exist_ok=True)
        for index, video in enumerate(videos):
            target = outdir / f"asset-{index + 1}.mp4"
            if video.get("data"):
                target.write_bytes(base64.b64decode(str(video["data"]), validate=True))
            elif video.get("uri"):
                file_id = _file_id_from_uri(str(video["uri"]))
                wait_for_file(file_id, api_key=key, base_url=base_url)
                download_file(file_id, target, api_key=key, base_url=base_url)
            else:
                raise GoogleOmniError("video output contains neither data nor uri")
            written.append(str(target))

    result = {
        **preview,
        "interaction_id": interaction.get("id"),
        "status": status,
        "estimated_video_output_cost_usd": estimate["usd"],
        "actual_cost_usd": None,
        "actual_cost_note": "The documented REST response does not provide provider-reported billing cost; reconcile later from usage/billing if exposed.",
        "elapsed_seconds": round(time.time() - started, 3),
        "written_assets": written,
    }
    if outdir:
        provenance = {
            "provider": "google-omni",
            "model": MODEL_ID,
            "interaction_id": interaction.get("id"),
            "estimate": estimate,
            "actual_cost_usd": None,
            "rights_approved": True,
            "approved_for_spend": True,
            "max_provider_cost_usd": maximum,
            "request": job["request"],
            "response_metadata": {"status": status, "object": interaction.get("object")},
        }
        (outdir / "provenance.json").write_text(json.dumps(provenance, indent=2) + "\n", encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Gemini Omni Flash UGC video jobs")
    parser.add_argument("--job", required=True)
    parser.add_argument("--estimate", action="store_true")
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--outdir")
    args = parser.parse_args()
    job = json.loads(Path(args.job).read_text(encoding="utf-8"))
    result = run_job(job, estimate_only=args.estimate, live=args.live, outdir=Path(args.outdir) if args.outdir else None)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
