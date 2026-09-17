#!/usr/bin/env python3
from __future__ import annotations

import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

from preflight_quote import build_preflight_quote, quote_from_plan


REPO_ROOT = Path(__file__).resolve().parents[3]
SCHEMA = json.loads((REPO_ROOT / "ugc-studio" / "schemas" / "execution-quote.schema.json").read_text(encoding="utf-8"))


class PreflightQuoteTests(unittest.TestCase):
    def validate(self, quote: dict) -> None:
        Draft202012Validator(SCHEMA, format_checker=FormatChecker()).validate(quote)

    def test_paid_route_requires_approval_but_never_preapproves(self) -> None:
        spec = {
            "concept_id": "quote-demo",
            "quality_tier": "standard",
            "aspect_ratio": "9:16",
            "shots": [
                {"id": "creator-1", "start": 0, "end": 5, "source_type": "creator_generated", "purpose": "hook"}
            ],
        }
        quote = build_preflight_quote(spec)
        self.validate(quote)
        self.assertTrue(quote["spend_required"])
        self.assertFalse(quote["spend_approved"])
        self.assertFalse(quote["authoritative"])
        self.assertEqual(quote["quote_source"], "registry_estimate")
        self.assertTrue(all(x["provider"] != "higgsfield" for x in quote["line_items"]))

    def test_deterministic_plan_needs_no_spend(self) -> None:
        spec = {
            "concept_id": "capture-only",
            "quality_tier": "standard",
            "shots": [
                {"id": "app-1", "start": 0, "end": 5, "source_type": "app_capture", "purpose": "demo"}
            ],
        }
        quote = build_preflight_quote(spec)
        self.validate(quote)
        self.assertFalse(quote["spend_required"])
        self.assertEqual(quote["estimated_total_usd"], 0.0)

    def test_budget_block_is_preserved(self) -> None:
        spec = {
            "concept_id": "budget-block",
            "quality_tier": "standard",
            "max_render_cost_usd": 0.10,
            "shots": [
                {"id": "creator-1", "start": 0, "end": 5, "source_type": "creator_generated", "purpose": "hook"}
            ],
        }
        quote = build_preflight_quote(spec)
        self.validate(quote)
        self.assertTrue(quote["blocked"])
        self.assertIn("exceeds cap", quote["block_reason"])

    def test_higgsfield_plan_is_rejected_even_if_injected(self) -> None:
        spec = {"concept_id": "bad-plan"}
        plan = {
            "concept_id": "bad-plan",
            "estimated_total_usd": 1.0,
            "blocked": False,
            "items": [
                {
                    "shot_id": "s1",
                    "source_type": "creator_generated",
                    "duration_seconds": 5,
                    "provider": "higgsfield",
                    "model": "anything",
                    "estimated_cost_usd": 1.0,
                    "expected_usable_cost_usd": 1.0,
                }
            ],
        }
        with self.assertRaises(ValueError):
            quote_from_plan(spec, plan)


if __name__ == "__main__":
    unittest.main()
