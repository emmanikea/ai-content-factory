#!/usr/bin/env python3
"""Build a normalized no-spend execution quote for a CreativeSpec.

The quote is deliberately provider-neutral and never enables Higgsfield. It turns the
existing dry model plan into a stable contract that can later accept authoritative provider
or measured GPU estimates without changing the product-facing spend gate.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from model_router import load_metrics, plan_spec


def quote_from_plan(spec: dict[str, Any], plan: dict[str, Any]) -> dict[str, Any]:
    line_items = []
    expected_total = 0.0
    for item in plan.get("items") or []:
        provider = str(item.get("provider") or "")
        if provider == "higgsfield":
            raise ValueError("Higgsfield runtime is disabled; execution quotes cannot include it")
        expected = float(item.get("expected_usable_cost_usd") or item.get("estimated_cost_usd") or 0.0)
        expected_total += expected
        line_items.append(
            {
                "shot_id": str(item["shot_id"]),
                "source_type": str(item["source_type"]),
                "duration_seconds": float(item.get("duration_seconds") or 0.0),
                "provider": provider,
                "model": str(item.get("model") or ""),
                "estimated_cost_usd": round(float(item.get("estimated_cost_usd") or 0.0), 6),
                "expected_usable_cost_usd": round(expected, 6),
                "quote_source": "registry_estimate",
            }
        )

    estimated_total = round(float(plan.get("estimated_total_usd") or 0.0), 6)
    budget_cap = spec.get("max_render_cost_usd")
    return {
        "schema_version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "concept_id": plan.get("concept_id") or spec.get("concept_id"),
        "currency": "USD",
        "quote_source": "registry_estimate",
        "authoritative": False,
        "line_items": line_items,
        "estimated_total_usd": estimated_total,
        "expected_usable_total_usd": round(expected_total, 6),
        "budget_cap_usd": float(budget_cap) if budget_cap is not None else None,
        "spend_required": estimated_total > 0,
        "spend_approved": False,
        "blocked": bool(plan.get("blocked", False)),
        "block_reason": plan.get("block_reason"),
        "policy": {
            "higgsfield_runtime_allowed": False,
            "paid_execution_requires_explicit_approval": True,
        },
    }


def build_preflight_quote(
    spec: dict[str, Any],
    *,
    allow_selfhost: bool = False,
    metrics: dict[tuple[str, str], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    plan = plan_spec(
        spec,
        allow_higgsfield=False,
        allow_selfhost=allow_selfhost,
        metrics=metrics,
    )
    return quote_from_plan(spec, plan)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a no-spend execution quote for a CreativeSpec")
    parser.add_argument("spec", help="CreativeSpec JSON")
    parser.add_argument("--allow-selfhost", action="store_true", help="Permit configured self-host candidates")
    parser.add_argument("--metrics", help="Optional benchmark summary JSON")
    parser.add_argument("--out")
    args = parser.parse_args()

    spec = json.loads(Path(args.spec).read_text(encoding="utf-8"))
    quote = build_preflight_quote(
        spec,
        allow_selfhost=args.allow_selfhost,
        metrics=load_metrics(args.metrics) if args.metrics else None,
    )
    text = json.dumps(quote, indent=2)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
    print(text)
    return 1 if quote["blocked"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
