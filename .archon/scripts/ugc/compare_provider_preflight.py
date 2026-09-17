#!/usr/bin/env python3
"""Compare provider preflights without spending money.

The output preserves cost evidence type instead of flattening provider-specific pricing
mechanisms into one fake precision level. Network preflight is opt-in and never submits a
render job.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]


def _load_module(name: str, relative_path: str):
    path = REPO_ROOT / relative_path
    spec = importlib.util.spec_from_file_location(name, path)
    if not spec or not spec.loader:
        raise RuntimeError(f"cannot load provider module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _modules() -> dict[str, Any]:
    return {
        "google-veo": _load_module("ugc_google_veo", "ugc-studio/providers/google-veo/client.py"),
        "google-omni": _load_module("ugc_google_omni", "ugc-studio/providers/google-omni/client.py"),
        "openrouter": _load_module("ugc_openrouter_video", "ugc-studio/providers/openrouter/client.py"),
        "higgsfield": _load_module("ugc_higgsfield_video", "ugc-studio/providers/higgsfield/client.py"),
    }


def _base_item(job: dict[str, Any], *, source: str | None = None) -> dict[str, Any]:
    provider = str(job.get("provider") or "unknown")
    if provider == "fal":
        model = job.get("model_id")
    elif provider == "openrouter":
        model = (job.get("input") or {}).get("model")
    elif provider in {"google-veo", "google-omni"}:
        model = job.get("model")
    elif provider == "higgsfield":
        model = job.get("endpoint")
    else:
        model = job.get("model") or job.get("model_id")
    return {
        "provider": provider,
        "model": model,
        "source_job": source,
        "preflight_cost_usd": None,
        "cost_evidence_type": "unknown",
        "cost_precision": "unknown",
        "requires_network_for_stronger_evidence": False,
        "actual_cost_source_after_run": None,
        "details": {},
    }


def preflight_job(
    job: dict[str, Any],
    *,
    network: bool = False,
    source: str | None = None,
    modules: dict[str, Any] | None = None,
) -> dict[str, Any]:
    item = _base_item(job, source=source)
    provider = item["provider"]
    modules = modules or (_modules() if provider in {"google-veo", "google-omni", "openrouter", "higgsfield"} else {})

    if provider == "fal":
        value = job.get("estimated_cost_usd")
        item.update({
            "preflight_cost_usd": float(value) if value is not None else None,
            "cost_evidence_type": "configured_provider_formula",
            "cost_precision": "dated_formula",
            "actual_cost_source_after_run": "provider reconciliation when implemented",
            "details": {"pricing_basis": "fal job compiler/model registry"},
        })
        return item

    if provider == "google-veo":
        quote = modules["google-veo"].estimate_cost(job)
        item.update({
            "preflight_cost_usd": float(quote["usd"]),
            "cost_evidence_type": "official_rate_formula",
            "cost_precision": "dated_formula",
            "actual_cost_source_after_run": "derived successful-generation billable cost",
            "details": quote,
        })
        return item

    if provider == "google-omni":
        quote = modules["google-omni"].estimate_cost(job)
        item.update({
            "preflight_cost_usd": float(quote["usd"]),
            "cost_evidence_type": "official_effective_output_rate_approximation",
            "cost_precision": "approximate_output_only",
            "actual_cost_source_after_run": "usage/billing reconciliation when exposed; input-token spend separate",
            "details": quote,
        })
        return item

    if provider == "openrouter":
        expected = job.get("expected_cost_usd")
        item.update({
            "preflight_cost_usd": float(expected) if expected is not None else None,
            "cost_evidence_type": "caller_preview_from_live_catalog" if expected is not None else "live_catalog_required",
            "cost_precision": "preview_not_provider_guaranteed" if expected is not None else "unknown",
            "requires_network_for_stronger_evidence": True,
            "actual_cost_source_after_run": "provider-reported usage.cost",
            "details": {"expected_cost_usd": expected, "max_provider_cost_usd": job.get("max_provider_cost_usd")},
        })
        if network:
            pf = modules["openrouter"].preflight(job)
            item["details"]["live_catalog"] = pf.get("catalog_snapshot")
            item["details"]["pricing_skus"] = pf.get("pricing_skus")
            item["requires_network_for_stronger_evidence"] = False
        return item

    if provider == "higgsfield":
        item.update({
            "cost_evidence_type": "authenticated_quote_required",
            "cost_precision": "unknown_without_quote",
            "requires_network_for_stronger_evidence": True,
            "actual_cost_source_after_run": "authenticated preflight quote; post-run billing reconciliation when exposed",
        })
        if network:
            quote = modules["higgsfield"].estimate(job["endpoint"], job["input"])
            item.update({
                "preflight_cost_usd": float(quote["usd"]),
                "cost_evidence_type": "provider_authenticated_request_quote",
                "cost_precision": "provider_quote",
                "requires_network_for_stronger_evidence": False,
                "details": {"credits": quote.get("credits"), "usd": quote.get("usd")},
            })
        return item

    raise ValueError(f"unsupported provider for comparison: {provider!r}")


def compare_jobs(
    jobs: list[tuple[str | None, dict[str, Any]]],
    *,
    network: bool = False,
    modules: dict[str, Any] | None = None,
) -> dict[str, Any]:
    items = [
        preflight_job(job, network=network, source=source, modules=modules)
        for source, job in jobs
    ]
    cost_known = [item for item in items if item["preflight_cost_usd"] is not None]
    cost_known.sort(key=lambda item: (float(item["preflight_cost_usd"]), str(item["provider"]), str(item["model"])))
    unknown = [item for item in items if item["preflight_cost_usd"] is None]
    return {
        "version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "network_preflight": network,
        "items": items,
        "cost_only_order": [
            {
                "provider": item["provider"],
                "model": item["model"],
                "preflight_cost_usd": item["preflight_cost_usd"],
                "cost_evidence_type": item["cost_evidence_type"],
            }
            for item in cost_known
        ],
        "unknown_cost": [
            {"provider": item["provider"], "model": item["model"], "reason": item["cost_evidence_type"]}
            for item in unknown
        ],
        "warning": (
            "cost_only_order is not a provider recommendation. Evidence precision differs by provider, "
            "and measured QA/pass rate must be combined before automatic routing."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare UGC provider job preflights without generating media")
    parser.add_argument("jobs", nargs="+", help="Provider job JSON files")
    parser.add_argument("--network", action="store_true", help="Allow authenticated read/estimate calls; never submits generation")
    parser.add_argument("--out")
    args = parser.parse_args()

    loaded: list[tuple[str | None, dict[str, Any]]] = []
    for value in args.jobs:
        path = Path(value)
        loaded.append((str(path), json.loads(path.read_text(encoding="utf-8"))))
    result = compare_jobs(loaded, network=args.network)
    text = json.dumps(result, indent=2)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
