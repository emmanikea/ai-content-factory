#!/usr/bin/env python3
"""OpenRouter async video provider adapter for UGC Studio.

The adapter owns the shared OpenRouter video lifecycle only. Model capabilities/pricing are
read from the live `/videos/models` catalog rather than hard-coded. Live generation is
explicitly rights- and spend-gated and records final `usage.cost` when OpenRouter returns it.
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

DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"
TERMINAL_STATUSES = {"completed", "failed", "cancelled", "expired"}
ACTIVE_STATUSES = {"pending", "in_progress"}


class OpenRouterError(RuntimeError):
    pass


def _api_key(explicit: str | None = None) -> str:
    value = explicit or os.environ.get("OPENROUTER_API_KEY")
    if not value:
        raise OpenRouterError("OPENROUTER_API_KEY is required for authenticated OpenRouter operations")
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
    headers = {"Authorization": f"Bearer {api_key}"}
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
        raise OpenRouterError(f"OpenRouter HTTP {exc.code}: {detail}") from exc
    except error.URLError as exc:
        raise OpenRouterError(f"OpenRouter network error: {exc.reason}") from exc


def _safe_openrouter_url(value: str, *, base_url: str = DEFAULT_BASE_URL) -> str:
    absolute = parse.urljoin("https://openrouter.ai", value)
    parsed = parse.urlparse(absolute)
    if parsed.scheme != "https" or parsed.hostname != "openrouter.ai":
        raise OpenRouterError("OpenRouter job URLs must remain on https://openrouter.ai")
    return absolute


def list_video_models(*, api_key: str | None = None, base_url: str = DEFAULT_BASE_URL) -> list[dict[str, Any]]:
    result = _json_request("GET", f"{base_url.rstrip('/')}/videos/models", api_key=_api_key(api_key))
    rows = result.get("data") if isinstance(result, dict) else None
    if rows is None and isinstance(result, dict):
        rows = result.get("models")
    if rows is None and isinstance(result, list):
        rows = result
    if not isinstance(rows, list):
        raise OpenRouterError("video model catalog did not contain a model list")
    return [row for row in rows if isinstance(row, dict)]


def find_video_model(model_id: str, *, api_key: str | None = None, base_url: str = DEFAULT_BASE_URL) -> dict[str, Any]:
    for row in list_video_models(api_key=api_key, base_url=base_url):
        identifiers = {
            str(row.get("id") or ""),
            str(row.get("slug") or ""),
            str(row.get("canonical_slug") or ""),
            str(row.get("model") or ""),
        }
        if model_id in identifiers:
            return row
    raise OpenRouterError(f"model {model_id!r} is not present in the current OpenRouter video catalog")


def _validate_parameter(name: str, value: Any, spec: Any) -> None:
    if not isinstance(spec, dict):
        return
    values = spec.get("values")
    if isinstance(values, list) and values and value not in values:
        raise OpenRouterError(f"{name}={value!r} is not supported; current values: {values}")
    if isinstance(value, (int, float)):
        minimum = spec.get("min")
        maximum = spec.get("max")
        if isinstance(minimum, (int, float)) and value < minimum:
            raise OpenRouterError(f"{name}={value!r} is below current minimum {minimum}")
        if isinstance(maximum, (int, float)) and value > maximum:
            raise OpenRouterError(f"{name}={value!r} exceeds current maximum {maximum}")


def validate_request_against_catalog(video_input: dict[str, Any], model_row: dict[str, Any]) -> None:
    """Best-effort validation using the live capability descriptor.

    OpenRouter's model catalog is the source of truth. The function intentionally validates only
    shapes the catalog describes, rather than guessing undocumented provider constraints.
    """
    supported = model_row.get("supported_parameters") or {}
    if not isinstance(supported, dict):
        return
    for name in ("duration", "resolution", "aspect_ratio", "n", "seed"):
        if name in video_input and name in supported:
            _validate_parameter(name, video_input[name], supported[name])

    for name in ("frame_images", "input_references"):
        if name not in video_input or name not in supported:
            continue
        value = video_input[name]
        if not isinstance(value, list):
            raise OpenRouterError(f"{name} must be an array")
        _validate_parameter(name, len(value), supported[name])


def preflight(job: dict[str, Any], *, api_key: str | None = None, base_url: str = DEFAULT_BASE_URL) -> dict[str, Any]:
    video_input = dict(job["input"])
    model_id = str(video_input.get("model") or "")
    if not model_id:
        raise OpenRouterError("job.input.model is required")
    row = find_video_model(model_id, api_key=api_key, base_url=base_url)
    validate_request_against_catalog(video_input, row)
    expected = job.get("expected_cost_usd")
    maximum = job.get("max_provider_cost_usd")
    if expected is not None and maximum is not None and float(expected) > float(maximum):
        raise OpenRouterError(
            f"expected cost ${float(expected):.4f} exceeds approved provider cap ${float(maximum):.4f}"
        )
    return {
        "model": model_id,
        "catalog_snapshot": row,
        "pricing_skus": row.get("pricing_skus"),
        "expected_cost_usd": expected,
        "max_provider_cost_usd": maximum,
        "note": (
            "OpenRouter does not document an authoritative per-request estimate endpoint for video. "
            "Use current pricing_skus for preview and final usage.cost for actual spend."
        ),
    }


def submit(video_input: dict[str, Any], *, api_key: str | None = None, base_url: str = DEFAULT_BASE_URL) -> dict[str, Any]:
    result = _json_request(
        "POST",
        f"{base_url.rstrip('/')}/videos",
        api_key=_api_key(api_key),
        body=video_input,
    )
    if not result.get("id"):
        raise OpenRouterError("video submission response is missing id")
    if not result.get("polling_url"):
        raise OpenRouterError("video submission response is missing polling_url")
    return result


def get_status(job_id: str, *, api_key: str | None = None, base_url: str = DEFAULT_BASE_URL) -> dict[str, Any]:
    return _json_request(
        "GET",
        f"{base_url.rstrip('/')}/videos/{parse.quote(str(job_id), safe='')}",
        api_key=_api_key(api_key),
    )


def get_status_url(polling_url: str, *, api_key: str | None = None) -> dict[str, Any]:
    return _json_request("GET", _safe_openrouter_url(polling_url), api_key=_api_key(api_key))


def wait_for_terminal(
    initial: dict[str, Any],
    *,
    api_key: str | None = None,
    base_url: str = DEFAULT_BASE_URL,
    interval_seconds: float = 30.0,
    timeout_seconds: float = 3600.0,
    sleep_fn=time.sleep,
) -> dict[str, Any]:
    current = initial
    deadline = time.monotonic() + timeout_seconds
    while True:
        status = str(current.get("status") or "").lower()
        if status in TERMINAL_STATUSES:
            return current
        if status not in ACTIVE_STATUSES:
            raise OpenRouterError(f"unexpected OpenRouter video status: {status!r}")
        if time.monotonic() >= deadline:
            raise OpenRouterError(f"video job {current.get('id')} timed out after {timeout_seconds:.0f}s")
        sleep_fn(interval_seconds)
        if time.monotonic() >= deadline:
            raise OpenRouterError(f"video job {current.get('id')} timed out after {timeout_seconds:.0f}s")
        if current.get("polling_url"):
            current = get_status_url(str(current["polling_url"]), api_key=api_key)
        else:
            current = get_status(str(current["id"]), api_key=api_key, base_url=base_url)


def _download_url(job: dict[str, Any], index: int, *, base_url: str = DEFAULT_BASE_URL) -> str:
    urls = job.get("unsigned_urls") or []
    if isinstance(urls, list) and len(urls) > index and isinstance(urls[index], str):
        return _safe_openrouter_url(urls[index])
    return f"{base_url.rstrip('/')}/videos/{parse.quote(str(job['id']), safe='')}/content?index={index}"


def download_video(
    job: dict[str, Any],
    destination: Path,
    *,
    index: int = 0,
    api_key: str | None = None,
    base_url: str = DEFAULT_BASE_URL,
) -> None:
    url = _download_url(job, index, base_url=base_url)
    req = request.Request(url, headers={"Authorization": f"Bearer {_api_key(api_key)}"}, method="GET")
    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        with request.urlopen(req, timeout=180) as response, destination.open("wb") as handle:
            shutil.copyfileobj(response, handle, length=1024 * 1024)
    except error.HTTPError as exc:
        raise OpenRouterError(f"OpenRouter video download failed: HTTP {exc.code}") from exc
    except error.URLError as exc:
        raise OpenRouterError(f"OpenRouter video download failed: {exc.reason}") from exc


def load_job(path: Path) -> dict[str, Any]:
    job = json.loads(path.read_text(encoding="utf-8"))
    if job.get("provider") != "openrouter":
        raise OpenRouterError("job.provider must be 'openrouter'")
    if not isinstance(job.get("input"), dict):
        raise OpenRouterError("job.input must be a JSON object")
    if not job["input"].get("model"):
        raise OpenRouterError("job.input.model is required")
    return job


def run_job(
    job: dict[str, Any],
    *,
    preflight_only: bool = False,
    live: bool = False,
    no_poll: bool = False,
    outdir: Path | None = None,
    api_key: str | None = None,
    base_url: str = DEFAULT_BASE_URL,
) -> dict[str, Any]:
    preview = {
        "mode": "live" if live else ("preflight" if preflight_only else "dry-run"),
        "provider": "openrouter",
        "model": job["input"].get("model"),
        "rights_approved": job.get("rights_approved") is True,
        "approved_for_spend": job.get("approved_for_spend") is True,
        "expected_cost_usd": job.get("expected_cost_usd"),
        "max_provider_cost_usd": job.get("max_provider_cost_usd"),
        "input": job["input"],
    }
    if not preflight_only and not live:
        return preview

    key = _api_key(api_key)
    pf = preflight(job, api_key=key, base_url=base_url)
    preview["preflight"] = pf
    if preflight_only and not live:
        return preview

    if job.get("rights_approved") is not True:
        raise OpenRouterError("live render blocked: job.rights_approved must be true")
    if job.get("approved_for_spend") is not True:
        raise OpenRouterError("live render blocked: job.approved_for_spend must be true")
    if job.get("expected_cost_usd") is None or job.get("max_provider_cost_usd") is None:
        raise OpenRouterError(
            "live render requires expected_cost_usd and max_provider_cost_usd because OpenRouter video "
            "does not expose an authoritative per-request preflight estimate endpoint"
        )

    video_input = dict(job["input"])
    callback = job.get("callback_url")
    if callback:
        if not str(callback).startswith("https://"):
            raise OpenRouterError("callback_url must be a public HTTPS URL")
        video_input["callback_url"] = callback

    started_at = time.time()
    submitted = submit(video_input, api_key=key, base_url=base_url)
    if no_poll:
        return {
            **preview,
            "id": submitted["id"],
            "status": submitted.get("status"),
            "polling_url": submitted.get("polling_url"),
        }

    terminal = wait_for_terminal(
        submitted,
        api_key=key,
        base_url=base_url,
        interval_seconds=float(job.get("poll_interval_seconds", 30)),
        timeout_seconds=float(job.get("timeout_seconds", 3600)),
    )
    usage = terminal.get("usage") if isinstance(terminal.get("usage"), dict) else {}
    actual = usage.get("cost")
    maximum = job.get("max_provider_cost_usd")
    cost_cap_exceeded = (
        actual is not None and maximum is not None and float(actual) > float(maximum)
    )
    result = {
        **preview,
        "id": terminal.get("id") or submitted["id"],
        "status": terminal.get("status"),
        "terminal": terminal,
        "actual_cost_usd": actual,
        "is_byok": usage.get("is_byok"),
        "cost_cap_exceeded_after_run": cost_cap_exceeded,
        "elapsed_seconds": round(time.time() - started_at, 3),
    }

    if str(terminal.get("status") or "").lower() == "completed" and outdir:
        outdir.mkdir(parents=True, exist_ok=True)
        urls = terminal.get("unsigned_urls") or []
        output_count = max(1, len(urls) if isinstance(urls, list) else 1)
        for index in range(output_count):
            download_video(terminal, outdir / f"asset-{index + 1}.mp4", index=index, api_key=key, base_url=base_url)
        provenance = {
            "provider": "openrouter",
            "model": video_input["model"],
            "job_id": result["id"],
            "catalog_snapshot": pf["catalog_snapshot"],
            "pricing_skus": pf.get("pricing_skus"),
            "expected_cost_usd": job.get("expected_cost_usd"),
            "max_provider_cost_usd": maximum,
            "actual_cost_usd": actual,
            "is_byok": usage.get("is_byok"),
            "cost_cap_exceeded_after_run": cost_cap_exceeded,
            "rights_approved": True,
            "approved_for_spend": True,
            "input": video_input,
            "terminal": terminal,
        }
        (outdir / "provenance.json").write_text(json.dumps(provenance, indent=2) + "\n", encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="OpenRouter async video provider adapter")
    parser.add_argument("--job")
    parser.add_argument("--preflight", action="store_true", help="Fetch current model capabilities/pricing without generating")
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--no-poll", action="store_true")
    parser.add_argument("--outdir")
    parser.add_argument("--catalog", action="store_true", help="Print the current video model catalog")
    parser.add_argument("--model", help="With --catalog, return one model row")
    parser.add_argument("--base-url", default=os.environ.get("OPENROUTER_API_BASE", DEFAULT_BASE_URL))
    args = parser.parse_args()

    if args.catalog:
        if args.job or args.live or args.preflight:
            raise OpenRouterError("--catalog is a standalone operation")
        if args.model:
            print(json.dumps(find_video_model(args.model, base_url=args.base_url), indent=2))
        else:
            print(json.dumps(list_video_models(base_url=args.base_url), indent=2))
        return 0

    if not args.job:
        raise OpenRouterError("--job is required unless --catalog is used")
    if args.preflight and args.live:
        raise OpenRouterError("choose either --preflight or --live")
    job = load_job(Path(args.job))
    result = run_job(
        job,
        preflight_only=args.preflight,
        live=args.live,
        no_poll=args.no_poll,
        outdir=Path(args.outdir) if args.outdir else None,
        base_url=args.base_url,
    )
    print(json.dumps(result, indent=2))
    return 1 if str(result.get("status") or "").lower() in {"failed", "cancelled", "expired"} else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except OpenRouterError as exc:
        print(json.dumps({"error": str(exc)}))
        raise SystemExit(2)
