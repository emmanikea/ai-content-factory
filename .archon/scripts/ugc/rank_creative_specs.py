#!/usr/bin/env python3
"""Rank CreativeSpec candidates before expensive rendering.

This is a production-priority score, not a virality claim. It combines observable
structure, direct-model cost, optional historical performance priors, and shortlist
diversity so the system does not spend on many near-identical variants.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

from model_router import plan_spec

MIN_HISTORY_SAMPLES = 3


def _tag(spec: dict[str, Any], prefix: str) -> str | None:
    for tag in spec.get("tags") or []:
        if tag.startswith(prefix + ":"):
            return tag.split(":", 1)[1]
    return None


def _bounded(value: float) -> float:
    return max(0.0, min(1.0, value))


def structural_score(spec: dict[str, Any]) -> tuple[float, dict[str, float]]:
    shots = list(spec.get("shots") or [])
    duration = float(spec.get("duration_seconds") or 0)
    if not shots or duration <= 0:
        return 0.0, {"hook": 0.0, "proof_speed": 0.0, "cta": 0.0, "deterministic_truth": 0.0}

    creator = [x for x in shots if x.get("source_type") in {"creator_generated", "creator_motion_transfer", "creator_lipsync"}]
    proof = [x for x in shots if x.get("source_type") in {"app_capture", "product_capture", "owned_media"}]

    if creator:
        first = creator[0]
        hook_duration = max(0.0, float(first["end"]) - float(first["start"]))
        hook = 1.0 if hook_duration <= 2.5 else _bounded(1.0 - ((hook_duration - 2.5) / 5.0))
    else:
        hook = 0.35

    if proof:
        proof_fraction = float(proof[0]["start"]) / duration
        proof_speed = 1.0 if proof_fraction <= 0.35 else _bounded(1.0 - ((proof_fraction - 0.35) / 0.5))
    else:
        proof_speed = 0.35

    cta_text = str(spec.get("cta") or "").strip().lower()
    cta = 0.0
    if cta_text:
        creator_dialogue = " ".join(str(x.get("dialogue") or "") for x in creator).lower()
        if cta_text in creator_dialogue:
            cta = 1.0
        elif any("cta" in str(x.get("purpose") or "").lower() for x in shots):
            cta = 0.8
        else:
            cta = 0.55

    generated_ui = any(
        x.get("source_type") in {"creator_generated", "broll_generated"}
        and "app" in str(x.get("purpose") or "").lower()
        for x in shots
    )
    deterministic_truth = 0.0 if generated_ui else (1.0 if proof else 0.65)

    parts = {
        "hook": round(hook, 4),
        "proof_speed": round(proof_speed, 4),
        "cta": round(cta, 4),
        "deterministic_truth": round(deterministic_truth, 4),
    }
    score = (hook * 0.30) + (proof_speed * 0.30) + (cta * 0.20) + (deterministic_truth * 0.20)
    return round(score, 4), parts


def cost_score(plan: dict[str, Any]) -> float:
    expected = sum(float(x.get("expected_usable_cost_usd", x.get("estimated_cost_usd", 0.0)) or 0.0) for x in plan.get("items") or [])
    if plan.get("blocked"):
        return 0.0
    # Smoothly rewards low-cost candidates without making cost dominate every decision.
    return round(1.0 / (1.0 + max(0.0, expected)), 4)


def history_score(spec: dict[str, Any], history: dict[str, Any] | None) -> tuple[float | None, dict[str, Any]]:
    if not history:
        return None, {"used": False, "dimensions": []}

    dimensions = [
        ("hooks", str(spec.get("hook") or "")),
        ("creators", str(spec.get("creator_id") or "")),
        ("ctas", str(spec.get("cta") or "")),
        ("formats", str(spec.get("format") or "")),
        ("locations", str(_tag(spec, "location") or "")),
        ("outfits", str(_tag(spec, "outfit") or "")),
    ]
    used = []
    weighted = []
    weights = {
        "hooks": 0.30,
        "creators": 0.25,
        "ctas": 0.15,
        "formats": 0.15,
        "locations": 0.075,
        "outfits": 0.075,
    }
    for dimension, value in dimensions:
        if not value:
            continue
        row = (history.get(dimension) or {}).get(value)
        if not row or int(row.get("samples") or 0) < MIN_HISTORY_SAMPLES:
            continue
        score = float(row.get("score", 0.5))
        weight = weights[dimension]
        weighted.append((score, weight))
        used.append({"dimension": dimension, "value": value, "score": score, "samples": int(row.get("samples") or 0)})
    if not weighted:
        return None, {"used": False, "dimensions": []}
    total_weight = sum(weight for _, weight in weighted)
    score = sum(score * weight for score, weight in weighted) / total_weight
    return round(_bounded(score), 4), {"used": True, "dimensions": used}


def candidate_features(spec: dict[str, Any]) -> set[str]:
    return {
        f"creator={spec.get('creator_id')}",
        f"hook={spec.get('hook')}",
        f"cta={spec.get('cta')}",
        f"format={spec.get('format')}",
        f"location={_tag(spec, 'location')}",
        f"outfit={_tag(spec, 'outfit')}",
    }


def similarity(a: dict[str, Any], b: dict[str, Any]) -> float:
    left = candidate_features(a)
    right = candidate_features(b)
    union = left | right
    return len(left & right) / len(union) if union else 0.0


def score_spec(
    spec: dict[str, Any],
    *,
    history: dict[str, Any] | None = None,
    model_metrics: dict[tuple[str, str], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    structure, structure_parts = structural_score(spec)
    plan = plan_spec(spec, metrics=model_metrics)
    cost = cost_score(plan)
    historical, history_details = history_score(spec, history)

    if historical is None:
        # Without enough historical campaign performance, do not invent it.
        score = (structure * 0.65) + (cost * 0.35)
        history_weight = 0.0
    else:
        score = (structure * 0.45) + (cost * 0.20) + (historical * 0.35)
        history_weight = 0.35

    estimated_cost = sum(float(x.get("estimated_cost_usd") or 0) for x in plan.get("items") or [])
    expected_usable = sum(float(x.get("expected_usable_cost_usd", x.get("estimated_cost_usd", 0)) or 0) for x in plan.get("items") or [])
    return {
        "concept_id": spec["concept_id"],
        "production_score": round(score * 100, 2),
        "breakdown": {
            "structure": round(structure * 100, 2),
            "structure_parts": structure_parts,
            "cost_efficiency": round(cost * 100, 2),
            "historical_performance": round(historical * 100, 2) if historical is not None else None,
            "historical_weight": history_weight,
            "history": history_details,
        },
        "estimated_render_cost_usd": round(estimated_cost, 4),
        "expected_usable_cost_usd": round(expected_usable, 4),
        "plan_blocked": bool(plan.get("blocked")),
        "spec": spec,
    }


def diversified_shortlist(scored: list[dict[str, Any]], count: int, diversity_weight: float = 0.20) -> list[dict[str, Any]]:
    if count <= 0:
        return []
    pool = list(scored)
    selected: list[dict[str, Any]] = []
    while pool and len(selected) < count:
        if not selected:
            chosen = max(pool, key=lambda x: x["production_score"])
        else:
            def objective(row: dict[str, Any]) -> float:
                max_similarity = max(similarity(row["spec"], existing["spec"]) for existing in selected)
                diversity = 1.0 - max_similarity
                return (row["production_score"] / 100.0) * (1.0 - diversity_weight) + diversity * diversity_weight
            chosen = max(pool, key=objective)
        selected.append(chosen)
        pool.remove(chosen)
    return selected


def rank_specs(
    specs: list[dict[str, Any]],
    *,
    history: dict[str, Any] | None = None,
    model_metrics: dict[tuple[str, str], dict[str, Any]] | None = None,
    shortlist: int = 8,
) -> dict[str, Any]:
    scored = [score_spec(spec, history=history, model_metrics=model_metrics) for spec in specs]
    scored.sort(key=lambda x: (-x["production_score"], x["expected_usable_cost_usd"], x["concept_id"]))
    selected = diversified_shortlist(scored, min(shortlist, len(scored)))
    selected_ids = {x["concept_id"] for x in selected}
    for rank, row in enumerate(scored, start=1):
        row["rank"] = rank
        row["shortlisted"] = row["concept_id"] in selected_ids
        row.pop("spec", None)
    return {
        "candidate_count": len(scored),
        "shortlist_count": len(selected_ids),
        "shortlist": [x["concept_id"] for x in selected],
        "candidates": scored,
        "disclaimer": "Production ranking prioritizes structure, cost and available measured history. It is not a virality prediction.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Rank CreativeSpec candidates before rendering")
    parser.add_argument("specs", help="JSON array of CreativeSpecs")
    parser.add_argument("--history", help="Optional CreativePerformanceSummary JSON")
    parser.add_argument("--model-metrics", help="Optional model benchmark summary JSON used by the router")
    parser.add_argument("--shortlist", type=int, default=8)
    parser.add_argument("--out")
    args = parser.parse_args()

    specs = json.loads(Path(args.specs).read_text(encoding="utf-8"))
    history = json.loads(Path(args.history).read_text(encoding="utf-8")) if args.history else None
    model_metrics = None
    if args.model_metrics:
        from model_router import load_metrics
        model_metrics = load_metrics(args.model_metrics)
    result = rank_specs(specs, history=history, model_metrics=model_metrics, shortlist=args.shortlist)
    text = json.dumps(result, indent=2)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
