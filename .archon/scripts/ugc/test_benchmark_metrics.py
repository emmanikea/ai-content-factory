#!/usr/bin/env python3
from __future__ import annotations

import unittest

from benchmark_metrics import (
    actual_cost_from_provider_provenance,
    build_benchmark_event,
    build_generation_failure_event,
    summarize_events,
)


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
                "rights_evidence": "agreement:test",
                "cost_evidence_type": "configured_provider_formula",
            },
        }

    def qa(self, status: str, score: float | None = 90, duration: float = 5.0) -> dict:
        return {
            "status": status,
            "score": score,
            "deterministic_checks": [
                {"name": "duration_readable", "status": "pass", "value": duration, "message": None}
            ],
            "failures": [] if status != "fail" else [{"code": "identity_drift"}],
        }

    def test_pass_records_usable_seconds_and_actual_cost(self) -> None:
        event = build_benchmark_event(self.job(), self.qa("pass"), actual_cost_usd=0.42, attempt_number=2)
        self.assertTrue(event["usable"])
        self.assertEqual(event["usable_seconds"], 5.0)
        self.assertEqual(event["cost_used_usd"], 0.42)
        self.assertEqual(event["cost_source"], "explicit_actual_override")
        self.assertEqual(event["attempt_number"], 2)

    def test_fail_spends_money_but_adds_no_usable_seconds(self) -> None:
        event = build_benchmark_event(self.job(), self.qa("fail"))
        self.assertFalse(event["usable"])
        self.assertEqual(event["usable_seconds"], 0.0)
        self.assertEqual(event["cost_used_usd"], 0.5)

    def test_openrouter_model_and_provider_reported_actual_are_normalized(self) -> None:
        job = {
            "campaign_id": "c1",
            "concept_id": "x1",
            "shot_id": "s1",
            "provider": "openrouter",
            "expected_cost_usd": 0.20,
            "input": {"model": "bytedance/seedance-2.0-fast"},
            "provenance": {"prompt_strategy": "image_to_video_motion_first"},
        }
        provider_provenance = {"job_id": "or-123", "actual_cost_usd": 0.17}
        event = build_benchmark_event(job, self.qa("pass", duration=4), provider_provenance=provider_provenance)
        self.assertEqual(event["model_id"], "bytedance/seedance-2.0-fast")
        self.assertEqual(event["estimated_cost_usd"], 0.20)
        self.assertEqual(event["actual_cost_usd"], 0.17)
        self.assertEqual(event["cost_used_usd"], 0.17)
        self.assertEqual(event["cost_source"], "provider_reported_actual")
        self.assertEqual(event["provider_request_id"], "or-123")

    def test_google_veo_derived_successful_cost_is_kept_distinct(self) -> None:
        job = {
            "provider": "google-veo",
            "model": "veo-3.1-lite-generate-preview",
            "estimated_cost_usd": 0.20,
            "provenance": {"cost_evidence_type": "official_rate_formula"},
        }
        event = build_benchmark_event(
            job,
            self.qa("pass", duration=4),
            provider_provenance={"operation_name": "operations/123", "derived_billable_cost_usd": 0.20},
        )
        self.assertEqual(event["model_id"], "veo-3.1-lite-generate-preview")
        self.assertEqual(event["cost_source"], "provider_billing_formula_after_success")
        self.assertEqual(event["provider_request_id"], "operations/123")

    def test_google_omni_benchmark_rate_derives_estimate_without_using_cost_cap(self) -> None:
        job = {
            "provider": "google-omni",
            "model": "gemini-omni-1.1-flash",
            "max_provider_cost_usd": 0.52,
            "provenance": {
                "target_duration_seconds": 4,
                "approx_output_rate_usd_per_second": 0.10,
                "cost_evidence_type": "official_effective_output_rate_approximation",
            },
        }
        event = build_benchmark_event(job, self.qa("needs_review", duration=4))
        self.assertEqual(event["estimated_cost_usd"], 0.4)
        self.assertEqual(event["cost_used_usd"], 0.4)
        self.assertNotEqual(event["estimated_cost_usd"], job["max_provider_cost_usd"])

    def test_provider_provenance_estimate_is_used_when_job_has_no_estimate(self) -> None:
        job = {"provider": "google-veo", "model": "veo-3.1-lite-generate-preview", "provenance": {}}
        event = build_benchmark_event(
            job,
            self.qa("pass", duration=4),
            provider_provenance={"estimate": {"usd": 0.2}},
        )
        self.assertEqual(event["estimated_cost_usd"], 0.2)

    def test_terminal_usage_cost_is_detected(self) -> None:
        actual, source = actual_cost_from_provider_provenance({"terminal": {"usage": {"cost": 0.1234}}})
        self.assertEqual(actual, 0.1234)
        self.assertEqual(source, "provider_reported_actual")

    def test_generation_failure_without_qa_counts_spend_and_zero_usable_seconds(self) -> None:
        event = build_generation_failure_event(
            self.job(),
            failure_code="provider_failed",
            actual_cost_usd=0.5,
            attempt_number=3,
        )
        self.assertEqual(event["qa_status"], "fail")
        self.assertFalse(event["usable"])
        self.assertEqual(event["usable_seconds"], 0.0)
        self.assertEqual(event["cost_used_usd"], 0.5)
        self.assertTrue(event["generation_failed_before_qa"])
        self.assertEqual(event["failures"], ["provider_failed"])

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

    def test_summary_counts_generation_failures_before_qa(self) -> None:
        events = [
            build_generation_failure_event(self.job(), failure_code="timeout", actual_cost_usd=0.5),
            build_benchmark_event(self.job(), self.qa("pass"), actual_cost_usd=0.5),
        ]
        row = summarize_events(events)["models"][0]
        self.assertEqual(row["generation_failures_before_qa"], 1)
        self.assertEqual(row["failures"], 1)

    def test_needs_review_is_not_counted_as_usable(self) -> None:
        event = build_benchmark_event(self.job(), self.qa("needs_review", score=None))
        result = summarize_events([event])
        row = result["models"][0]
        self.assertEqual(row["passes"], 0)
        self.assertEqual(row["needs_review"], 1)
        self.assertIsNone(row["cost_per_usable_second_usd"])


if __name__ == "__main__":
    unittest.main()
