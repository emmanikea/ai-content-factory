#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, mimetypes, os, random, shutil, time
from pathlib import Path
from urllib import error, parse, request

DEFAULT_BASE_URL = "https://api.higgsfield.ai"
TERMINAL_STATUSES = {"completed", "failed", "nsfw", "canceled"}

class HiggsfieldError(RuntimeError):
    pass

def _credentials(explicit=None):
    value = explicit or os.environ.get("HF_CREDENTIALS") or os.environ.get("HF_KEY")
    if not value:
        raise HiggsfieldError("Higgsfield credentials missing. Set HF_CREDENTIALS (preferred) or HF_KEY to '<api_key_id>:<api_key_secret>'.")
    if ":" not in value:
        raise HiggsfieldError("Higgsfield credentials must be '<api_key_id>:<api_key_secret>'.")
    return value.strip()

def _endpoint(value):
    endpoint = str(value or "").strip().strip("/")
    if not endpoint:
        raise HiggsfieldError("job.endpoint is required")
    if "://" in endpoint or endpoint.startswith("requests/") or ".." in endpoint:
        raise HiggsfieldError("job.endpoint must be a model endpoint path, not a URL/request path")
    return endpoint

def _json_request(method, url, *, credentials, body=None, timeout=60):
    payload = None if body is None else json.dumps(body).encode("utf-8")
    headers = {"Authorization": f"Key {credentials}"}
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
            detail = json.loads(raw)
        except json.JSONDecodeError:
            detail = raw
        raise HiggsfieldError(f"Higgsfield HTTP {exc.code}: {detail}") from exc
    except error.URLError as exc:
        raise HiggsfieldError(f"Higgsfield network error: {exc.reason}") from exc

def estimate(endpoint, arguments, *, credentials=None, base_url=DEFAULT_BASE_URL):
    endpoint = _endpoint(endpoint)
    result = _json_request("POST", f"{base_url.rstrip('/')}/estimate/{endpoint}", credentials=_credentials(credentials), body=arguments)
    if "usd" not in result or "credits" not in result:
        raise HiggsfieldError("estimate response is missing usd/credits")
    return result

def submit(endpoint, arguments, *, credentials=None, base_url=DEFAULT_BASE_URL, webhook=None):
    endpoint = _endpoint(endpoint)
    url = f"{base_url.rstrip('/')}/{endpoint}"
    if webhook:
        if not webhook.startswith("https://"):
            raise HiggsfieldError("hf_webhook must be a public HTTPS URL")
        url += "?" + parse.urlencode({"hf_webhook": webhook})
    result = _json_request("POST", url, credentials=_credentials(credentials), body=arguments)
    if not result.get("request_id"):
        raise HiggsfieldError("submission response is missing request_id")
    return result

def get_status_url(status_url, *, credentials=None):
    if not status_url.startswith("https://api.higgsfield.ai/"):
        raise HiggsfieldError("status_url must point to api.higgsfield.ai")
    return _json_request("GET", status_url, credentials=_credentials(credentials))

def get_status(request_id, *, credentials=None, base_url=DEFAULT_BASE_URL):
    return _json_request("GET", f"{base_url.rstrip('/')}/requests/{parse.quote(str(request_id), safe='')}/status", credentials=_credentials(credentials))

def cancel(request_id, *, credentials=None, base_url=DEFAULT_BASE_URL):
    return _json_request("POST", f"{base_url.rstrip('/')}/requests/{parse.quote(str(request_id), safe='')}/cancel", credentials=_credentials(credentials))

def wait_for_terminal(*, initial, credentials=None, base_url=DEFAULT_BASE_URL, timeout_seconds=900, sleep_fn=time.sleep, jitter_fn=random.uniform):
    current = initial
    deadline = time.monotonic() + timeout_seconds
    delay = 2.0
    while str(current.get("status", "")).lower() not in TERMINAL_STATUSES:
        if time.monotonic() >= deadline:
            raise HiggsfieldError(f"polling timed out after {timeout_seconds:.0f}s")
        sleep_fn(delay + float(jitter_fn(0.0, 0.5)))
        if current.get("status_url"):
            current = get_status_url(str(current["status_url"]), credentials=credentials)
        elif current.get("request_id"):
            current = get_status(str(current["request_id"]), credentials=credentials, base_url=base_url)
        else:
            raise HiggsfieldError("request is missing request_id/status_url")
        delay = min(delay * 1.5, 10.0)
    return current

def media_urls(result):
    urls = []
    def collect(value):
        if isinstance(value, dict):
            url = value.get("url")
            if isinstance(url, str) and url.startswith(("https://", "http://")):
                urls.append(url)
            for key, child in value.items():
                if key != "url":
                    collect(child)
        elif isinstance(value, list):
            for child in value:
                collect(child)
    collect(result)
    return list(dict.fromkeys(urls))

def download_media(url, destination):
    destination.parent.mkdir(parents=True, exist_ok=True)
    req = request.Request(url, headers={"User-Agent": "ugc-studio-higgsfield/1.0"})
    with request.urlopen(req, timeout=120) as response, destination.open("wb") as handle:
        shutil.copyfileobj(response, handle)

def _suffix(url, index):
    suffix = Path(parse.urlparse(url).path).suffix
    if suffix and len(suffix) <= 8:
        return suffix
    return mimetypes.guess_extension("video/mp4" if index == 0 else "application/octet-stream") or ".bin"

def load_job(path):
    job = json.loads(path.read_text(encoding="utf-8"))
    if job.get("provider") != "higgsfield":
        raise HiggsfieldError("job.provider must be 'higgsfield'")
    _endpoint(job.get("endpoint"))
    if not isinstance(job.get("input"), dict):
        raise HiggsfieldError("job.input must be a JSON object")
    return job

def run_job(job, *, estimate_only=False, live=False, no_poll=False, outdir=None, credentials=None, base_url=DEFAULT_BASE_URL):
    endpoint = _endpoint(job["endpoint"])
    preview = {
        "mode": "live" if live else ("estimate" if estimate_only else "dry-run"),
        "provider": "higgsfield",
        "endpoint": endpoint,
        "rights_approved": job.get("rights_approved") is True,
        "approved_for_spend": job.get("approved_for_spend") is True,
        "max_provider_cost_usd": job.get("max_provider_cost_usd"),
        "input": job["input"],
    }
    if not estimate_only and not live:
        return preview
    quoted = estimate(endpoint, job["input"], credentials=credentials, base_url=base_url)
    preview["estimate"] = quoted
    max_cost = job.get("max_provider_cost_usd")
    if max_cost is not None and float(quoted["usd"]) > float(max_cost):
        raise HiggsfieldError(f"provider estimate ${float(quoted['usd']):.4f} exceeds job cap ${float(max_cost):.4f}")
    if estimate_only and not live:
        return preview
    if job.get("rights_approved") is not True:
        raise HiggsfieldError("live render blocked: job.rights_approved must be true")
    if job.get("approved_for_spend") is not True:
        raise HiggsfieldError("live render blocked: job.approved_for_spend must be true")
    started_at = time.time()
    submitted = submit(endpoint, job["input"], credentials=credentials, base_url=base_url, webhook=job.get("webhook_url"))
    if no_poll:
        return {**preview, "request_id": submitted["request_id"], "status": submitted.get("status"), "status_url": submitted.get("status_url"), "cancel_url": submitted.get("cancel_url")}
    terminal = wait_for_terminal(initial=submitted, credentials=credentials, base_url=base_url, timeout_seconds=float(job.get("timeout_seconds", 900)))
    result = {**preview, "request_id": terminal.get("request_id") or submitted["request_id"], "status": terminal.get("status"), "terminal": terminal, "elapsed_seconds": round(time.time() - started_at, 3)}
    if str(terminal.get("status")).lower() != "completed":
        return result
    urls = media_urls(terminal)
    result["media_urls"] = urls
    if outdir:
        outdir.mkdir(parents=True, exist_ok=True)
        provenance = {"provider": "higgsfield", "endpoint": endpoint, "request_id": result["request_id"], "authenticated_estimate": quoted, "rights_approved": True, "approved_for_spend": True, "input": job["input"], "terminal": terminal, "media_urls": urls}
        (outdir / "provenance.json").write_text(json.dumps(provenance, indent=2) + "\n", encoding="utf-8")
        for i, url in enumerate(urls):
            download_media(url, outdir / f"asset-{i+1}{_suffix(url, i)}")
    return result

def main():
    parser = argparse.ArgumentParser(description="Higgsfield provider adapter with estimate/spend gates")
    parser.add_argument("--job", required=True)
    parser.add_argument("--estimate", action="store_true")
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--no-poll", action="store_true")
    parser.add_argument("--outdir")
    parser.add_argument("--base-url", default=os.environ.get("HIGGSFIELD_API_BASE", DEFAULT_BASE_URL))
    args = parser.parse_args()
    if args.estimate and args.live:
        raise HiggsfieldError("choose either --estimate or --live")
    job = load_job(Path(args.job))
    result = run_job(job, estimate_only=args.estimate, live=args.live, no_poll=args.no_poll, outdir=Path(args.outdir) if args.outdir else None, base_url=args.base_url)
    print(json.dumps(result, indent=2))
    return 1 if str(result.get("status", "")).lower() in {"failed", "nsfw", "canceled"} else 0

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except HiggsfieldError as exc:
        print(json.dumps({"error": str(exc)}))
        raise SystemExit(2)
