#!/usr/bin/env python3
from __future__ import annotations

import unittest

from model_router import MIN_MEASURED_SAMPLES, route_shot


class MeasuredRouterTests(unittest.TestCase):
    def registry(self) -> dict:
        return {
            "providers": [
                {
                    "id": "fal",
                    "kind": "direct_hosted",
                    "enabled_by_default": True,
                    "models": [
                        {
                            "id": "cheap-low-pass",
                            "capabilities": ["creator_video"],
                            "quality_score": 0.93,
                            "recommended_for": ["standard"],
                            "cost_model": {"type": "per_second", "rate": 0.08},
                        },
                        {
                            "id": "slightly-costlier-high-pass",
                            "capabilities": ["creator_video"],
                            "quality_score": 0.87,
                            "recommended_for": ["standard"],
                            "cost_model": {"type": "per_second", "rate": 0.10},
                        },
                    ],
                }
            ]
        }

    def shot(self) -> dict:
        return {"id": "s1", "source_type": "creator_generated", "start": 0, "end": 5}

    def test_mature_metrics_can_override_static_prior(self) -> None:
        metrics = {
            ("fal", "cheap-low-pass"): {"attempts": 10, "pass_rate": 0.2, "cost_per_usable_second": 0.40},
            ("fal", "slightly-costlier-high-pass"): {"attempts": 10, "pass_rate": 0.9, "cost_per_usable_second": 0.12},
        }
        result = route_shot(
            self.shot(),
            quality_tier="standard",
            registry=self.registry(),
            metrics=metrics,
        )
        self.assertEqual(result["model"], "slightly-costlier-high-pass")
        self.assertEqual(result["measured_samples"], 10)
        self.assertIn("measured pass=90%", result["reason"])

    def test_insufficient_metrics_do_not_replace_static_prior(self) -> None:
        metrics = {
            ("fal", "cheap-low-pass"): {"attempts": MIN_MEASURED_SAMPLES - 1, "pass_rate": 0.1, "cost_per_usable_second": 0.8},
            ("fal", "slightly-costlier-high-pass"): {"attempts": MIN_MEASURED_SAMPLES - 1, "pass_rate": 1.0, "cost_per_usable_second": 0.1},
        }
        result = route_shot(
            self.shot(),
            quality_tier="standard",
            registry=self.registry(),
            metrics=metrics,
        )
        self.assertEqual(result["model"], "cheap-low-pass")
        self.assertIn("static quality prior", result["reason"])

    def test_no_metrics_preserves_prior_behavior(self) -> None:
        result = route_shot(
            self.shot(),
            quality_tier="standard",
            registry=self.registry(),
            metrics={},
        )
        self.assertEqual(result["model"], "cheap-low-pass")
        self.assertIsNone(result["measured_pass_rate"])


if __name__ == "__main__":
    unittest.main()
