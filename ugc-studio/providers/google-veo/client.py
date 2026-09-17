#!/usr/bin/env python3
"""Direct Google Gemini API / Veo 3.1 video provider adapter for UGC Studio.

V1 focuses on text-to-video, image-to-video, first/last-frame interpolation, and asset
reference images. Video extension is intentionally excluded until we add a dedicated contract.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import time
from pathlib import Path
from typing import Any
from urllib import error, parse, request

DEFAULT_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
PRICING_CHECKED_AT = "2026-09-17"
PRICING_SOURCE = "https://ai.google.dev/gemini-api/docs/pricing"

MODEL_PRICING = {
    "veo-3.1-generate-preview": {
        "rates": {"720p": 0.40, "1080p": 0.40, "4k": 0.60},
        "reference_images": True,
        "max_reference_images": 3,
    },
    "veo-3.1-fast-generate-preview": {
        "rates": {"720p": 0.10, "1080p": 0.12, "4k": 0.30},
        "reference_images": True,
        "max_reference_images": 3,
    },
    "veo-3.1-lite-generate-preview": {
        "rates": {"720p": 0.05, "1080p": 0.08},
        "reference_images": False,
        "max_reference_images": 0,
    },
}


class GoogleVeoError(RuntimeError):
    pass


def _api_key(explicit: str | None = None) -> str:
    value = explicit or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not value:
        raise GoogleVeoError("GEMINI_API_KEY (or GOOGLE_API_KEY) is required for live Google Veo operations")
    return value.strip()


def _json_request(
    method: str,
    url: str,
    *,
    api_key: str,
    body: dict[str, Any] | None = None,
    timeout: float = 60.0,
) -> dict[str, Any]:
    payload = None if body is None else json.dumps(body).encode("utf-8")
    headers = {"x-goog-api-key": api_key}
    if payload is not None:
        headers["Content-Type"] = "application/json"
    req = request.Request(url, data=payload, headers=headers, method=method)
    try:
        with request.urlopen(req, timeout=timeout) as response:
            raw = response.read()
            if not raw:
                return {"http_status": getattr(response, "status", 200)}
            return json.loads(raw.decode("utf-8"))
    except error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            detail: Any = json.loads(raw)
        except json.JSONDecodeError:
            detail = raw
        raise GoogleVeoError(f"Google Veo HTTP {exc.code}: {detail}") from exc
    except error.URLError as exc:
        raise GoogleVeoError(f"Google Veo network error: {exc.reason}") from exc


def _single_instance(job: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    body = job.get("request")
    if not isinstance(body, dict):
        raise GoogleVeoError("job.request must be a JSON object")
    instances = body.get("instances")
    if not isinstance(instances, list) or len(instances) != 1 or not isinstance(instances[0], dict):
        raise GoogleVeoError("V1 Google Veo jobs require exactly one request.instances item")
    parameters = body.get("parameters") or {}
    if not isinstance(parameters, dict):
        raise GoogleVeoError("request.parameters must be a JSON object")
    return instances[0], parameters


def validate_job(job: dict[str, Any]) -> dict[str, Any]:
    if job.get("provider") != "google-veo":
        raise GoogleVeoError("job.provider must be 'google-veo'")
    model = str(job.get("model") or "")
    info = MODEL_PRICING.get(model)
    if not info:
        raise GoogleVeoError(f"unsupported Google Veo model: {model!r}")
    instance, parameters = _single_instance(job)
    if not str(instance.get("prompt") or "").strip():
        raise GoogleVeoError("request instance prompt is required")
    if instance.get("video") is not None:
        raise GoogleVeoError("video extension is not enabled in the V1 direct Google adapter")

    aspect = str(parameters.get("aspectRatio", "16:9"))
    if aspect not in {"16:9", "9:16"}:
        raise GoogleVeoError("aspectRatio must be '16:9' or '9:16'")
    try:
        duration = int(parameters.get("durationSeconds", 8))
    except (TypeError, ValueError) as exc:
        raise GoogleVeoError("durationSeconds must be 4, 6, or 8") from exc
    if duration not in {4, 6, 8}:
        raise GoogleVeoError("durationSeconds must be 4, 6, or 8")
    resolution = str(parameters.get("resolution", "720p"))
    rates = info["rates"]
    if resolution not in rates:
        raise GoogleVeoError(f"{model} does not support resolution {resolution!r}")
    if resolution in {"1080p", "4k"} and duration != 8:
        raise GoogleVeoError(f"{resolution} requires durationSeconds=8")
    if int(parameters.get("numberOfVideos", 1)) != 1:
        raise GoogleVeoError("Veo 3.1 currently supports one video per request")

    if instance.get("lastFrame") is not None and instance.get("image") is None:
        raise GoogleVeoError("lastFrame requires an initial image")
    references = instance.get("referenceImages") or []
    if not isinstance(references, list):
        raise GoogleVeoError("referenceImages must be an array")
    if references and not info["reference_images"]:
        raise GoogleVeoError(f"{model} does not support referenceImages")
    if len(references) > int(info["max_reference_images"]):
        raise GoogleVeoError(f"referenceImages exceeds {info['max_reference_images']} for {model}")
    if references and duration != 8:
        raise GoogleVeoError("referenceImages require durationSeconds=8")

    person_generation = parameters.get("personGeneration")
    if person_generation is not None and person_generation not in {"allow_all", "allow_adult"}:
        raise GoogleVeoError("personGeneration must be 'allow_all' or 'allow_adult' when supplied")

    return {
        "model": model,
        "duration_seconds": duration,
        "resolution": resolution,
        "aspect_ratio": aspect,
        "has_initial_image": instance.get("image") is not None,
        "has_last_frame": instance.get("lastFrame") is not None,
        "reference_image_count": len(references),
        "audio": "always_on",
    }


def estimate_cost(job: dict[str, Any]) -> dict[str, Any]:
    validated = validate_job(job)
    info = MODEL_PRICING[validated["model"]]
    rate = float(info["rates"][validated["resolution"]])
    usd = round(rate * int(validated["duration_seconds"]), 4)
    return {
        "usd": usd,
        "rate_usd_per_second": rate,
        "duration_seconds": validated["duration_seconds"],
        "resolution": validated["resolution"],
        "model": validated["model"],
        "audio": "always_on",
        "pricing_checked_at": PRICING_CHECKED_AT,
        "pricing_source": PRICING_SOURCE,
        "billing_note": "Google states Veo is charged only when video generation succeeds.",
    }


def submit(job: dict[str, Any], *, api_key: str | None = None, base_url: str = DEFAULT_BASE_URL) -> dict[str, Any]:
    model = str(job["model"])
    result = _json_request(
        "POST",
        f"{base_url.rstrip('/')}/models/{parse.quote(model, safe='')}:predictLongRunning",
        api_key=_api_key(api_key),
        body=job["request"],
    )
    if not result.get("name"):
        raise GoogleVeoError("Google Veo submission response is missing operation name")
    return result


def _operation_url(name: str, base_url: str = DEFAULT_BASE_URL) -> str:
    name = str(name or "").lstrip("/")
    if not name or ".." in name or "://" in name:
        raise GoogleVeoError("invalid Google operation name")
    return f"{base_url.rstrip('/')}/{name}"


def get_operation(name: str, *, api_key: str | None = None, base_url: str = DEFAULT_BASE_URL) -> dict[str, Any]:
    return _json_request("GET", _operation_url(name, base_url), api_key=_api_key(api_key))


def wait_for_terminal(
    initial: dict[str, Any],
    *,
    api_key: str | None = None,
    base_url: str = DEFAULT_BASE_URL,
    interval_seconds: float = 10.0,
    timeout_seconds: float = 3600.0,
    sleep_fn=time.sleep,
) -> dict[str, Any]:
    current = initial
    deadline = time.monotonic() + timeout_seconds
    while not bool(current.get("done")):
        if time.monotonic() >= deadline:
            raise GoogleVeoError(f"operation {current.get('name')} timed out after {timeout_seconds:.0f}s")
        sleep_fn(interval_seconds)
        if time.monotonic() >= deadline:
            raise GoogleVeoError(f"operation {current.get('name')} timed out after {timeout_seconds:.0f}s")
        current = get_operation(str(current.get("name") or ""), api_key=api_key, base_url=base_url)
    return current


def video_uris(operation: dict[str, Any]) -> list[str]:
    response = operation.get("response") or {}
    generate = response.get("generateVideoResponse") if isinstance(response, dict) else {}
    samples = generate.get("generatedSamples") if isinstance(generate, dict) else None
    uris: list[str] = []
    if isinstance(samples, list):
        for sample in samples:
            video = sample.get("video") if isinstance(sample, dict) else None
            uri = video.get("uri") if isinstance(video, dict) else None
            if isinstance(uri, str) and uri.startswith("https://"):
                uris.append(uri)
    return list(dict.fromkeys(uris))


def _safe_download_url(url: str) -> str:
    parsed = parse.urlparse(url)
    host = (parsed.hostname or "").lower()
    if parsed.scheme != "https" or not (host == "storage.googleapis.com" or host.endswith(".googleapis.com")):
        raise GoogleVeoError("Google Veo download URI must stay on a Google APIs/storage host")
    return url


def download_video(url: str, destination: Path, *, api_key: str | None = None) -> None:
    req = request.Request(
        _safe_download_url(url),
        headers={"x-goog-api-key": _api_key(api_key)},
        method="GET",
    )
    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        with request.urlopen(req, timeout=180) as response, destination.open("wb") as handle:
            shutil.copyfileobj(response, handle, length=1024 * 1024)
    except error.HTTPError as exc:
        raise GoogleVeoError(f"Google Veo video download failed: HTTP {exc.code}") from exc
    except error.URLError as exc:
        raise GoogleVeoError(f"Google Veo video download failed: {exc.reason}") from exc


def load_job(path: Path) -> dict[str, Any]:
    job = json.loads(path.read_text(encoding="utf-8"))
    validate_job(job)
    return job


def run_job(
    job: dict[str, Any],
    *,
    estimate_only: bool = False,
    live: bool = False,
    no_poll: bool = False,
    outdir: Path | None = None,
    api_key: str | None = None,
    base_url: str = DEFAULT_BASE_URL,
) -> dict[str, Any]:
    estimate = estimate_cost(job)
    preview = {
        "mode": "live" if live else ("estimate" if estimate_only else "dry-run"),
        "provider": "google-veo",
        "model": job["model"],
        "rights_approved": job.get("rights_approved") is True,
        "approved_for_spend": job.get("approved_for_spend") is True,
        "max_provider_cost_usd": job.get("max_provider_cost_usd"),
        "estimate": estimate,
        "request": job["request"],
    }
    maximum = job.get("max_provider_cost_usd")
    if maximum is not None and float(estimate["usd"]) > float(maximum):
        raise GoogleVeoError(
            f"estimated Google Veo cost ${estimate['usd']:.4f} exceeds approved cap ${float(maximum):.4f}"
        )
    if estimate_only or not live:
        return preview

    if job.get("rights_approved") is not True:
        raise GoogleVeoError("live render blocked: job.rights_approved must be true")
    if job.get("approved_for_spend") is not True:
        raise GoogleVeoError("live render blocked: job.approved_for_spend must be true")
    if maximum is None:
        raise GoogleVeoError("live render requires max_provider_cost_usd")

    key = _api_key(api_key)
    started_at = time.time()
    submitted = submit(job, api_key=key, base_url=base_url)
    if no_poll:
        return {**preview, "operation_name": submitted["name"], "done": bool(submitted.get("done"))}

    terminal = wait_for_terminal(
        submitted,
        api_key=key,
        base_url=base_url,
        interval_seconds=float(job.get("poll_interval_seconds", 10)),
        timeout_seconds=float(job.get("timeout_seconds", 3600)),
    )
    failed = bool(terminal.get("error"))
    uris = [] if failed else video_uris(terminal)
    success = not failed and bool(uris)
    derived_billable_cost = estimate["usd"] if success else 0.0
    result = {
        **preview,
        "operation_name": terminal.get("name") or submitted["name"],
        "done": bool(terminal.get("done")),
        "status": "failed" if failed else ("completed" if success else "completed_without_video"),
        "video_uris": uris,
        "derived_billable_cost_usd": derived_billable_cost,
        "cost_basis": "official per-second rate; Google documents charges only for successful Veo generations",
        "terminal": terminal,
        "elapsed_seconds": round(time.time() - started_at, 3),
    }

    if success and outdir:
        outdir.mkdir(parents=True, exist_ok=True)
        for index, uri in enumerate(uris):
            download_video(uri, outdir / f"asset-{index + 1}.mp4", api_key=key)
        provenance = {
            "provider": "google-veo",
            "model": job["model"],
            "operation_name": result["operation_name"],
            "estimate": estimate,
            "derived_billable_cost_usd": derived_billable_cost,
            "cost_basis": result["cost_basis"],
            "rights_approved": True,
            "approved_for_spend": True,
            "max_provider_cost_usd": maximum,
            "request": job["request"],
            "terminal": terminal,
            "video_uris": uris,
        }
        (outdir / "provenance.json").write_text(json.dumps(provenance, indent=2) + "\n", encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Direct Google Gemini API / Veo 3.1 provider adapter")
    parser.add_argument("--job", required=True)
    parser.add_argument("--estimate", action="store_true")
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--no-poll", action="store_true")
    parser.add_argument("--outdir")
    parser.add_argument("--base-url", default=os.environ.get("GOOGLE_GEMINI_API_BASE", DEFAULT_BASE_URL))
    args = parser.parse_args()
    if args.estimate and args.live:
        raise GoogleVeoError("choose either --estimate or --live")
    job = load_job(Path(args.job))
    result = run_job(
        job,
        estimate_only=args.estimate,
        live=args.live,
        no_poll=args.no_poll,
        outdir=Path(args.outdir) if args.outdir else None,
        base_url=args.base_url,
    )
    print(json.dumps(result, indent=2))
    return 1 if result.get("status") in {"failed", "completed_without_video"} else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except GoogleVeoError as exc:
        print(json.dumps({"error": str(exc)}))
        raise SystemExit(2)
