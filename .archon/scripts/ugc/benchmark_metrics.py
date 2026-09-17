#!/usr/bin/env python3
"""Record and summarize UGC model benchmark outcomes across providers.

The economic unit is a usable approved second, not a raw generation. Records preserve
model, prompt strategy, cost evidence, attempt count, QA status, and failed spend.
"""
from __future__ import annotations

import argparse
import json
import os
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from local_store import LocalStore


def _duration_from_qa(qa: dict[str, Any]) -> float:
    for check in qa.get("deterministic_checks") or []:
        if check.get("name") == "duration_readable" and isinstance(check.get("value"), (int, float)):
            return max(0.0, float(check["value"]))
    return 0.0


def _provider_model(job: dict[str, Any]) -> str | None:
    provider = str(job.get("provider") or "")
    if job.get("model_id"):
        return str(job["model_id"])
    if job.get("model"):
        return str(job["model"])
    if provider == "openrouter":
        model = (job.get("input") or {}).get("model")
        return str(model) if model else None
    if provider == "higgsfield":
        endpoint = job.get("endpoint")
        return str(endpoint) if endpoint else None
    return None


def _estimated_cost(job: dict[str, Any], provider_provenance: dict[str, Any] | None = None) -> float:
    for key in ("estimated_cost_usd", "expected_cost_usd"):
        value = job.get(key)
        if isinstance(value, (int, float)):
            return max(0.0, float(value))

    # Completed provider provenance commonly preserves its preflight estimate even when the
    # provider job shape itself did not need a top-level estimate field.
    if provider_provenance:
        estimate = provider_provenance.get("estimate")
        if isinstance(estimate, dict) and isinstance(estimate.get("usd"), (int, float)):
            return max(0.0, float(estimate["usd"]))

    provenance = job.get("provenance") or {}
    estimate = provenance.get("estimate") if isinstance(provenance, dict) else None
    if isinstance(estimate, dict) and isinstance(estimate.get("usd"), (int, float)):
        return max(0.0, float(estimate["usd"]))

    # Benchmark jobs preserve dated rates + a normalized target duration. Derive only when
    # both are explicitly present; never infer from max_provider_cost_usd because a cap can
    # intentionally be larger than the expected spend.
    if isinstance(provenance, dict):
        duration = provenance.get("target_duration_seconds")
        if isinstance(duration, (int, float)):
            for rate_key in ("rate_usd_per_second", "approx_output_rate_usd_per_second", "preview_rate_usd_per_second"):
                rate = provenance.get(rate_key)
                if isinstance(rate, (int, float)):
                    return max(0.0, float(rate) * float(duration))
    return 0.0


def _cost_evidence_type(job: dict[str, Any]) -> str | None:
    provenance = job.get("provenance") or {}
    if isinstance(provenance, dict) and provenance.get("cost_evidence_type"):
        return str(provenance["cost_evidence_type"])
    provider = str(job.get("provider") or "")
    return {
        "fal": "configured_provider_formula",
        "openrouter": "caller_preview_from_live_catalog",
        "google-veo": "official_rate_formula",
        "google-omni": "official_effective_output_rate_approximation",
        "higgsfield": "provider_authenticated_request_quote",
    }.get(provider)


def actual_cost_from_provider_provenance(provider_provenance: dict[str, Any] | None) -> tuple[float | None, str | None]:
    if not provider_provenance:
        return None, None
    value = provider_provenance.get("actual_cost_usd")
    if isinstance(value, (int, float)):
        return max(0.0, float(value)), "provider_reported_actual"
    value = provider_provenance.get("derived_billable_cost_usd")
    if isinstance(value, (int, float)):
        return max(0.0, float(value)), "provider_billing_formula_after_success"
    terminal = provider_provenance.get("terminal")
    if isinstance(terminal, dict):
        usage = terminal.get("usage")
        if isinstance(usage, dict) and isinstance(usage.get("cost"), (int, float)):
            return max(0.0, float(usage["cost"])), "provider_reported_actual"
    return None, None


def _request_id(provider_provenance: dict[str, Any] | None) -> str | None:
    if not provider_provenance:
        return None
    for key in ("request_id", "job_id", "id", "operation_name", "interaction_id"):
        value = provider_provenance.get(key)
        if value:
            return str(value)
    terminal = provider_provenance.get("terminal")
    if isinstance(terminal, dict):
        for key in ("id", "name"):
            if terminal.get(key):
                return str(terminal[key])
    return None


def _base_event(
    job: dict[str, Any],
    *,
    actual_cost_usd: float | None,
    actual_cost_source: str | None,
    attempt_number: int,
    provider_provenance: dict[str, Any] | None,
) -> dict[str, Any]:
    estimated = _estimated_cost(job, provider_provenance)
    cost = estimated if actual_cost_usd is None else float(actual_cost_usd)
    provenance = job.get("provenance") or {}
    return {
        "event_id": str(uuid.uuid4()),
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "campaign_id": job.get("campaign_id"),
        "concept_id": job.get("concept_id"),
        "shot_id": job.get("shot_id"),
        "provider": job.get("provider"),
        "model_id": _provider_model(job),
        "provider_request_id": _request_id(provider_provenance),
        "quality_tier": provenance.get("quality_tier"),
        "prompt_strategy": provenance.get("prompt_strategy"),
        "prompt_compiler_version": provenance.get("prompt_compiler_version"),
        "attempt_number": int(attempt_number),
        "estimated_cost_usd": round(estimated, 6),
        "actual_cost_usd": round(float(actual_cost_usd), 6) if actual_cost_usd is not None else None,
        "cost_used_usd": round(cost, 6),
        "cost_source": actual_cost_source or ("actual" if actual_cost_usd is not None else "estimate"),
        "cost_evidence_type": _cost_evidence_type(job),
        "rights_evidence": provenance.get("rights_evidence"),
    }


def build_benchmark_event(
    job: dict[str, Any],
    qa: dict[str, Any],
    *,
    actual_cost_usd: float | None = None,
    attempt_number: int = 1,
    provider_provenance: dict[str, Any] | None = None,
) -> dict[str, Any]:
    explicit_actual = actual_cost_usd is not None
    derived_actual, derived_source = actual_cost_from_provider_provenance(provider_provenance)
    if actual_cost_usd is None:
        actual_cost_usd = derived_actual
    actual_source = "explicit_actual_override" if explicit_actual else derived_source

    duration = _duration_from_qa(qa)
    status = qa.get("status")
    usable = status == "pass"
    event = _base_event(
        job,
        actual_cost_usd=actual_cost_usd,
        actual_cost_source=actual_source,
        attempt_number=attempt_number,
        provider_provenance=provider_provenance,
    )
    event.update({
        "qa_status": status,
        "qa_score": qa.get("score"),
        "usable": usable,
        "artifact_duration_seconds": round(duration, 3),
        "usable_seconds": round(duration, 3) if usable else 0.0,
        "failures": [x.get("code") for x in (qa.get("failures") or [])],
    })
    return event


def build_generation_failure_event(
    job: dict[str, Any],
    *,
    failure_code: str,
    actual_cost_usd: float | None = None,
    attempt_number: int = 1,
    provider_provenance: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not failure_code.strip():
        raise ValueError("failure_code is required")
    explicit_actual = actual_cost_usd is not None
    derived_actual, derived_source = actual_cost_from_provider_provenance(provider_provenance)
    if actual_cost_usd is None:
        actual_cost_usd = derived_actual
    source = "explicit_actual_override" if explicit_actual else derived_source
    event = _base_event(
        job,
        actual_cost_usd=actual_cost_usd,
        actual_cost_source=source,
        attempt_number=attempt_number,
        provider_provenance=provider_provenance,
    )
    event.update({
        "qa_status": "fail",
        "qa_score": None,
        "usable": False,
        "artifact_duration_seconds": 0.0,
        "usable_seconds": 0.0,
        "failures": [failure_code.strip()],
        "generation_failed_before_qa": True,
    })
    return event


def summarize_events(events: list[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[tuple[str, str, str | None], list[dict[str, Any]]] = defaultdict(list)
    for event in events:
        key = (str(event.get("provider")), str(event.get("model_id")), event.get("prompt_strategy"))
        grouped[key].append(event)

    rows = []
    for (provider, model, prompt_strategy), items in sorted(grouped.items()):
        attempts = len(items)
        passes = sum(1 for x in items if x.get("qa_status") == "pass")
        failures = sum(1 for x in items if x.get("qa_status") == "fail")
        needs_review = sum(1 for x in items if x.get("qa_status") == "needs_review")
        total_cost = sum(float(x.get("cost_used_usd") or 0) for x in items)
        usable_seconds = sum(float(x.get("usable_seconds") or 0) for x in items)
        scored = [float(x["qa_score"]) for x in items if isinstance(x.get("qa_score"), (int, float))]
        rows.append({
            "provider": provider,
            "model_id": model,
            "prompt_strategy": prompt_strategy,
            "attempts": attempts,
            "passes": passes,
            "failures": failures,
            "needs_review": needs_review,
            "pass_rate": round(passes / attempts, 4) if attempts else 0.0,
            "total_cost_usd": round(total_cost, 4),
            "usable_seconds": round(usable_seconds, 3),
            "cost_per_usable_second_usd": round(total_cost / usable_seconds, 4) if usable_seconds > 0 else None,
            "average_qa_score": round(sum(scored) / len(scored), 2) if scored else None,
            "actual_cost_samples": sum(1 for x in items if x.get("actual_cost_usd") is not None),
            "generation_failures_before_qa": sum(1 for x in items if x.get("generation_failed_before_qa") is True),
        })
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "event_count": len(events),
        "models": rows,
        "policy": "Do not use measured pass-rate/cost-per-usable-second for routing until sample size is sufficient and QA criteria are comparable.",
    }


def events_from_store(store: LocalStore) -> list[dict[str, Any]]:
    events = []
    for row in store.list("performance"):
        document = store.get("performance", row["id"])
        if document:
            events.append(document)
    return events


def main() -> int:
    parser = argparse.ArgumentParser(description="Record/summarize UGC model benchmark outcomes")
    parser.add_argument("--root", default=os.environ.get("UGC_STORE_DIR", "ugc-studio/data"))
    sub = parser.add_subparsers(dest="command", required=True)

    record = sub.add_parser("record")
    record.add_argument("--job", required=True)
    record.add_argument("--qa")
    record.add_argument("--generation-failure", help="Failure code when generation produced no artifact/QA result")
    record.add_argument("--provider-provenance", help="Provider provenance.json; used to derive actual cost/request id")
    record.add_argument("--actual-cost", type=float, help="Explicit override; normally derive from provider provenance")
    record.add_argument("--attempt", type=int, default=1)
    record.add_argument("--id")

    summary = sub.add_parser("summarize")
    summary.add_argument("--out")

    args = parser.parse_args()
    store = LocalStore(args.root)
    if args.command == "record":
        if bool(args.qa) == bool(args.generation_failure):
            raise SystemExit("record requires exactly one of --qa or --generation-failure")
        job = json.loads(Path(args.job).read_text(encoding="utf-8"))
        provider_provenance = (
            json.loads(Path(args.provider_provenance).read_text(encoding="utf-8"))
            if args.provider_provenance else None
        )
        if args.qa:
            qa = json.loads(Path(args.qa).read_text(encoding="utf-8"))
            event = build_benchmark_event(
                job,
                qa,
                actual_cost_usd=args.actual_cost,
                attempt_number=args.attempt,
                provider_provenance=provider_provenance,
            )
        else:
            event = build_generation_failure_event(
                job,
                failure_code=args.generation_failure,
                actual_cost_usd=args.actual_cost,
                attempt_number=args.attempt,
                provider_provenance=provider_provenance,
            )
        record_id = args.id or f"bench-{event['event_id']}"
        store.put("performance", record_id, event)
        print(json.dumps(event, indent=2))
        return 0

    result = summarize_events(events_from_store(store))
    text = json.dumps(result, indent=2)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
