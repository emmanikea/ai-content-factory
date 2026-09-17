#!/usr/bin/env python3
"""Cost-aware retry/escalation policy for UGC render jobs."""
from __future__ import annotations

from dataclasses import dataclass


TIERS = ("draft", "standard", "premium")


@dataclass(frozen=True)
class RetryDecision:
    action: str
    quality_tier: str
    reason: str


def next_tier(current: str) -> str:
    try:
        index = TIERS.index(current)
    except ValueError as exc:
        raise ValueError(f"unknown quality tier: {current!r}") from exc
    return TIERS[min(index + 1, len(TIERS) - 1)]


def decide_retry(
    *,
    quality_tier: str,
    attempt: int,
    failure_type: str,
    estimated_next_cost_usd: float,
    spent_usd: float,
    budget_usd: float | None,
) -> RetryDecision:
    """Choose retry, escalation, or stop after a failed asset QA result.

    Stochastic failures get one same-tier retry. Structural/model-quality failures escalate.
    Rights, source, and deterministic-content failures never get routed around the guard.
    """
    hard_stop = {"rights", "missing_source", "ui_incorrect", "unlicensed_reference"}
    stochastic = {"transient", "provider_error", "minor_deformation", "audio_glitch"}
    structural = {"identity_drift", "major_deformation", "prompt_miss", "motion_miss", "lip_sync"}

    if failure_type in hard_stop:
        return RetryDecision("stop", quality_tier, f"non-retryable failure: {failure_type}")

    if budget_usd is not None and spent_usd + estimated_next_cost_usd > budget_usd:
        return RetryDecision("stop", quality_tier, "next attempt would exceed render budget")

    if failure_type in stochastic and attempt <= 1:
        return RetryDecision("retry_same_tier", quality_tier, f"one same-tier retry for {failure_type}")

    if failure_type in structural or attempt > 1:
        promoted = next_tier(quality_tier)
        if promoted == quality_tier:
            return RetryDecision("stop", quality_tier, "premium route already exhausted")
        return RetryDecision("escalate", promoted, f"promote after {failure_type}")

    return RetryDecision("retry_same_tier", quality_tier, f"retry unclassified failure: {failure_type}")
