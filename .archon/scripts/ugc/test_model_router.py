#!/usr/bin/env python3
from __future__ import annotations

import unittest

from model_router import estimate_model_cost, load_registry, plan_spec, route_shot


class ModelRouterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.registry = load_registry()
        cls.models = {
            model["id"]: model
            for provider in cls.registry["providers"]
            for model in provider.get("models", [])
        }

    def creator_shot(self) -> dict:
        return {
            "id": "creator-1",
            "start": 0,
            "end": 5,
            "source_type": "creator_generated",
            "purpose": "hook",
        }

    def test_draft_creator_routes_to_wan(self) -> None:
        route = route_shot(self.creator_shot(), quality_tier="draft", registry=self.registry)
        self.assertEqual(route["model"], "alibaba/wan-3.0/image-to-video")
        self.assertEqual(route["estimated_cost_usd"], 0.5)

    def test_standard_creator_routes_to_kling_standard(self) -> None:
        route = route_shot(self.creator_shot(), quality_tier="standard", registry=self.registry)
        self.assertEqual(route["model"], "fal-ai/kling-video/v3/standard/image-to-video")
        self.assertEqual(route["estimated_cost_usd"], 0.42)

    def test_premium_creator_routes_to_seedance(self) -> None:
        route = route_shot(self.creator_shot(), quality_tier="premium", registry=self.registry)
        self.assertEqual(route["model"], "bytedance/seedance-2.5/reference-to-video")
        self.assertAlmostEqual(route["estimated_cost_usd"], 2.3112, places=4)

    def test_motion_transfer_routes_to_kling_motion(self) -> None:
        shot = {
            "id": "motion-1",
            "start": 0,
            "end": 5,
            "source_type": "creator_motion_transfer",
            "purpose": "licensed reaction performance",
        }
        route = route_shot(shot, quality_tier="standard", registry=self.registry)
        self.assertEqual(route["model"], "fal-ai/kling-video/v3/standard/motion-control")
        self.assertEqual(route["estimated_cost_usd"], 0.63)

    def test_seedance_token_formula_matches_five_second_720p_example(self) -> None:
        model = self.models["bytedance/seedance-2.5/reference-to-video"]
        cost = estimate_model_cost(
            model,
            duration_seconds=5,
            resolution="720p",
            aspect_ratio="9:16",
        )
        self.assertAlmostEqual(cost, 2.3112, places=4)

    def test_deterministic_app_capture_costs_zero(self) -> None:
        shot = {
            "id": "app-1",
            "start": 1,
            "end": 6,
            "source_type": "app_capture",
            "purpose": "real product demo",
        }
        route = route_shot(shot, quality_tier="standard", registry=self.registry)
        self.assertEqual(route["provider"], "local-playwright")
        self.assertEqual(route["estimated_cost_usd"], 0.0)

    def test_bordereta_style_plan_only_bills_creator_seconds(self) -> None:
        spec = {
            "concept_id": "demo",
            "quality_tier": "standard",
            "aspect_ratio": "9:16",
            "max_render_cost_usd": 2,
            "shots": [
                {"id": "s1", "start": 0, "end": 2.4, "source_type": "creator_generated", "purpose": "hook"},
                {"id": "s2", "start": 2.4, "end": 8.8, "source_type": "app_capture", "purpose": "demo"},
                {"id": "s3", "start": 8.8, "end": 11.4, "source_type": "creator_generated", "purpose": "reaction"},
                {"id": "s4", "start": 11.4, "end": 15.4, "source_type": "app_capture", "purpose": "demo"},
                {"id": "s5", "start": 15.4, "end": 17.5, "source_type": "graphic", "purpose": "cta"}
            ],
        }
        result = plan_spec(spec)
        self.assertFalse(result["blocked"])
        self.assertAlmostEqual(result["estimated_total_usd"], 0.42, places=4)
        self.assertTrue(all(item["provider"] != "higgsfield" for item in result["items"]))


if __name__ == "__main__":
    unittest.main()
