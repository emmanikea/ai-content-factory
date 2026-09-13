#!/usr/bin/env python3
"""Rights checks for synthetic creator rendering.

The planner calls this before any provider submission. The module does not decide legal
sufficiency; it enforces the explicit permissions recorded for the creator.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Iterable


@dataclass(frozen=True)
class RightsDecision:
    allowed: bool
    reasons: tuple[str, ...]


def _contains_or_unrestricted(values: Iterable[str] | None, requested: str) -> bool:
    values = tuple(values or ())
    return not values or "*" in values or requested in values


def _product_scope_allows(rights: dict, product_id: str, product_category: str) -> bool:
    """Allow when both scopes are empty, or either explicit scope matches.

    Important: an empty product list must not erase a populated category restriction.
    Likewise, an empty category list must not erase a populated product allow-list.
    """
    products = tuple(rights.get("allowed_products") or ())
    categories = tuple(rights.get("allowed_product_categories") or ())
    if not products and not categories:
        return True
    if "*" in products or product_id in products:
        return True
    if "*" in categories or product_category in categories:
        return True
    return False


def evaluate_creator_rights(
    creator: dict,
    *,
    product_id: str,
    product_category: str,
    platform: str,
    transformations: Iterable[str],
    on_date: date | None = None,
) -> RightsDecision:
    """Return an allow/block decision from stored creator permissions.

    Synthetic creators may use `not_required`; real/founder identities must be active.
    Product/category scope is unrestricted only when both corresponding lists are empty.
    Empty platform lists remain unrestricted within the agreement.
    """
    today = on_date or date.today()
    creator_type = creator.get("creator_type")
    rights = creator.get("rights") or {}
    state = rights.get("consent_state")
    reasons: list[str] = []

    if creator_type == "synthetic":
        if state not in {"not_required", "active"}:
            reasons.append(f"synthetic creator has invalid consent state: {state!r}")
    elif state != "active":
        reasons.append(f"creator consent is not active: {state!r}")

    valid_from = rights.get("valid_from")
    valid_until = rights.get("valid_until")
    if valid_from and today < date.fromisoformat(valid_from):
        reasons.append(f"rights do not start until {valid_from}")
    if valid_until and today > date.fromisoformat(valid_until):
        reasons.append(f"rights expired on {valid_until}")

    if not _product_scope_allows(rights, product_id, product_category):
        reasons.append(f"product/category not permitted: {product_id}/{product_category}")

    if not _contains_or_unrestricted(rights.get("allowed_platforms"), platform):
        reasons.append(f"platform not permitted: {platform}")

    allowed_transformations = set(rights.get("allowed_transformations") or [])
    for transformation in transformations:
        if transformation not in allowed_transformations:
            reasons.append(f"transformation not permitted: {transformation}")

    return RightsDecision(allowed=not reasons, reasons=tuple(reasons))


def enforce_reference_mode(reference: dict, requested_operation: str) -> RightsDecision:
    """Prevent performance cloning from references that are analysis-only."""
    mode = reference.get("rights_mode", "creative_dna_only")
    transfer_ops = {"motion_transfer", "character_replace", "literal_timing_transfer"}
    if requested_operation in transfer_ops and mode == "creative_dna_only":
        return RightsDecision(
            False,
            ("reference is creative_dna_only; literal performance transfer is blocked",),
        )
    return RightsDecision(True, ())
