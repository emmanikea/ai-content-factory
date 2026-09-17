#!/usr/bin/env python3
from __future__ import annotations

import types
import unittest

from compare_provider_preflight import compare_jobs, preflight_job


class ProviderPreflightComparisonTests(unittest.TestCase):
    def google_module(self):
        return types.SimpleNamespace(
            estimate_cost=lambda job: {
                "usd": 0.20,
                "rate_usd_per_second": 0.05,
                "duration_seconds": 4,
                "pricing_checked_at": "2026-09-17",
                "pricing_source": "google-pricing",
            }
        )

    def openrouter_module(self):
        return types.SimpleNamespace(
            preflight=lambda job: {
                "catalog_snapshot": {"id": job["input"]["model"], "supported_parameters": {}},
                "pricing_skus": [{"price": "0.05"}],
            }
        )

    def higgsfield_module(self):
        return types.SimpleNamespace(
            estimate=lambda endpoint, arguments: {"credits": "3", "usd": "0.27"}
        )

    def modules(self):
        return {
            "google-veo": self.google_module(),
            "openrouter": self.openrouter_module(),
            "higgsfield": self.higgsfield_module(),
        }

    def test_fal_preserves_configured_formula_evidence(self):
        item = preflight_job(
            {"provider": "fal", "model_id": "wan", "estimated_cost_usd": 0.40},
            modules=self.modules(),
        )
        self.assertEqual(item["preflight_cost_usd"], 0.40)
        self.assertEqual(item["cost_evidence_type"], "configured_provider_formula")

    def test_google_preserves_official_formula_evidence(self):
        item = preflight_job(
            {"provider": "google-veo", "model": "veo-lite", "request": {}},
            modules=self.modules(),
        )
        self.assertEqual(item["preflight_cost_usd"], 0.20)
        self.assertEqual(item["cost_evidence_type"], "official_rate_formula")

    def test_openrouter_offline_uses_caller_preview_without_claiming_quote(self):
        job = {
            "provider": "openrouter",
            "input": {"model": "bytedance/seedance-2.0"},
            "expected_cost_usd": 0.25,
            "max_provider_cost_usd": 0.40,
        }
        item = preflight_job(job, network=False, modules=self.modules())
        self.assertEqual(item["preflight_cost_usd"], 0.25)
        self.assertEqual(item["cost_precision"], "preview_not_provider_guaranteed")
        self.assertTrue(item["requires_network_for_stronger_evidence"])

    def test_openrouter_network_adds_catalog_but_keeps_cost_semantics(self):
        job = {
            "provider": "openrouter",
            "input": {"model": "bytedance/seedance-2.0"},
            "expected_cost_usd": 0.25,
        }
        item = preflight_job(job, network=True, modules=self.modules())
        self.assertIn("live_catalog", item["details"])
        self.assertEqual(item["cost_evidence_type"], "caller_preview_from_live_catalog")
        self.assertFalse(item["requires_network_for_stronger_evidence"])

    def test_higgsfield_offline_cost_is_unknown(self):
        item = preflight_job(
            {"provider": "higgsfield", "endpoint": "model/endpoint", "input": {}},
            network=False,
            modules=self.modules(),
        )
        self.assertIsNone(item["preflight_cost_usd"])
        self.assertEqual(item["cost_evidence_type"], "authenticated_quote_required")

    def test_higgsfield_network_uses_provider_quote(self):
        item = preflight_job(
            {"provider": "higgsfield", "endpoint": "model/endpoint", "input": {}},
            network=True,
            modules=self.modules(),
        )
        self.assertEqual(item["preflight_cost_usd"], 0.27)
        self.assertEqual(item["cost_precision"], "provider_quote")

    def test_comparison_orders_known_cost_but_warns_not_recommendation(self):
        jobs = [
            ("fal.json", {"provider": "fal", "model_id": "wan", "estimated_cost_usd": 0.40}),
            ("google.json", {"provider": "google-veo", "model": "veo-lite", "request": {}}),
            ("openrouter.json", {"provider": "openrouter", "input": {"model": "seedance"}, "expected_cost_usd": 0.25}),
            ("higgsfield.json", {"provider": "higgsfield", "endpoint": "x", "input": {}}),
        ]
        result = compare_jobs(jobs, network=False, modules=self.modules())
        self.assertEqual(
            [item["provider"] for item in result["cost_only_order"]],
            ["google-veo", "openrouter", "fal"],
        )
        self.assertEqual(result["unknown_cost"][0]["provider"], "higgsfield")
        self.assertIn("not a provider recommendation", result["warning"])


if __name__ == "__main__":
    unittest.main()
