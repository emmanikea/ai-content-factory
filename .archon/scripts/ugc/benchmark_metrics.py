#!/usr/bin/env python3
"""Record and summarize UGC model benchmark outcomes.

The economic unit is a usable approved second, not a raw generation. Records preserve
model, prompt strategy, attempt count, QA status, and the cost assumption used at the time.
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


def build_benchmark_event(
    job: dict[str, Any],
    qa: dict[str, Any],
    *,
    actual_cost_usd: float | None = None,
    attempt_number: int = 1,
) -> dict[str, Any]:
    estimated = float(job.get("estimated_cost_usd") or 0.0)
    cost = estimated if actual_cost_usd is None else float(actual_cost_usd)
    duration = _duration_from_qa(qa)
    status = qa.get("status")
    usable = status == "pass"
    provenance = job.get("provenance") or {}
    return {
        "event_id": str(uuid.uuid4()),
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "campaign_id": job.get("campaign_id"),
        "concept_id": job.get("concept_id"),
        "shot_id": job.get("shot_id"),
        "provider": job.get("provider"),
        "model_id": job.get("model_id"),
        "quality_tier": provenance.get("quality_tier"),
        "prompt_strategy": provenance.get("prompt_strategy"),
        "prompt_compiler_version": provenance.get("prompt_compiler_version"),
        "attempt_number": int(attempt_number),
        "estimated_cost_usd": round(estimated, 6),
        "actual_cost_usd": round(float(actual_cost_usd), 6) if actual_cost_usd is not None else None,
        "cost_used_usd": round(cost, 6),
        "cost_source": "actual" if actual_cost_usd is not None else "estimate",
        "qa_status": status,
        "qa_score": qa.get("score"),
        "usable": usable,
        "artifact_duration_seconds": round(duration, 3),
        "usable_seconds": round(duration, 3) if usable else 0.0,
        "failures": [x.get("code") for x in (qa.get("failures") or [])],
        "rights_evidence": provenance.get("rights_evidence"),
    }


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
            "actual_cost_samples": sum(1 for x in items if x.get("cost_source") == "actual"),
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
    record.add_argument("--qa", required=True)
    record.add_argument("--actual-cost", type=float)
    record.add_argument("--attempt", type=int, default=1)
    record.add_argument("--id")

    summary = sub.add_parser("summarize")
    summary.add_argument("--out")

    args = parser.parse_args()
    store = LocalStore(args.root)
    if args.command == "record":
        job = json.loads(Path(args.job).read_text(encoding="utf-8"))
        qa = json.loads(Path(args.qa).read_text(encoding="utf-8"))
        event = build_benchmark_event(job, qa, actual_cost_usd=args.actual_cost, attempt_number=args.attempt)
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
