#!/usr/bin/env python3
from __future__ import annotations

import unittest

from benchmark_metrics import build_benchmark_event, summarize_events


class BenchmarkMetricsTests(unittest.TestCase):
    def job(self, model: str = "model-a") -> dict:
        return {
            "campaign_id": "c1",
            "concept_id": "x1",
            "shot_id": "s1",
            "provider": "fal",
            "model_id": model,
            "estimated_cost_usd": 0.5,
            "provenance": {
                "quality_tier": "standard",
                "prompt_strategy": "image_to_video_motion_first",
                "prompt_compiler_version": "v1",
                "rights_evidence": "agreement:test"
            }
        }

    def qa(self, status: str, score: float | None = 90, duration: float = 5.0) -> dict:
        return {
            "status": status,
            "score": score,
            "deterministic_checks": [
                {"name": "duration_readable", "status": "pass", "value": duration, "message": None}
            ],
            "failures": [] if status != "fail" else [{"code": "identity_drift"}]
        }

    def test_pass_records_usable_seconds_and_actual_cost(self) -> None:
        event = build_benchmark_event(self.job(), self.qa("pass"), actual_cost_usd=0.42, attempt_number=2)
        self.assertTrue(event["usable"])
        self.assertEqual(event["usable_seconds"], 5.0)
        self.assertEqual(event["cost_used_usd"], 0.42)
        self.assertEqual(event["cost_source"], "actual")
        self.assertEqual(event["attempt_number"], 2)

    def test_fail_spends_money_but_adds_no_usable_seconds(self) -> None:
        event = build_benchmark_event(self.job(), self.qa("fail"))
        self.assertFalse(event["usable"])
        self.assertEqual(event["usable_seconds"], 0.0)
        self.assertEqual(event["cost_used_usd"], 0.5)

    def test_summary_calculates_cost_per_usable_second(self) -> None:
        events = [
            build_benchmark_event(self.job(), self.qa("pass"), actual_cost_usd=0.5),
            build_benchmark_event(self.job(), self.qa("fail"), actual_cost_usd=0.5),
        ]
        result = summarize_events(events)
        row = result["models"][0]
        self.assertEqual(row["attempts"], 2)
        self.assertEqual(row["passes"], 1)
        self.assertEqual(row["pass_rate"], 0.5)
        self.assertEqual(row["total_cost_usd"], 1.0)
        self.assertEqual(row["usable_seconds"], 5.0)
        self.assertEqual(row["cost_per_usable_second_usd"], 0.2)

    def test_needs_review_is_not_counted_as_usable(self) -> None:
        event = build_benchmark_event(self.job(), self.qa("needs_review", score=None))
        result = summarize_events([event])
        row = result["models"][0]
        self.assertEqual(row["passes"], 0)
        self.assertEqual(row["needs_review"], 1)
        self.assertIsNone(row["cost_per_usable_second_usd"])


if __name__ == "__main__":
    unittest.main()
