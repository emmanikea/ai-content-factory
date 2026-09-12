#!/usr/bin/env python3
from __future__ import annotations

import unittest

from build_fal_job import build_job
from retry_policy import decide_retry


class RenderGuardTests(unittest.TestCase):
    def spec(self, *, rights_mode: str = "creative_dna_only", source_type: str = "creator_generated") -> dict:
        return {
            "version": "1.0",
            "campaign_id": "campaign",
            "concept_id": "concept",
            "aspect_ratio": "9:16",
            "creator_id": "creator-a",
            "rights_mode": rights_mode,
            "quality_tier": "standard",
            "shots": [
                {
                    "id": "s1",
                    "start": 0,
                    "end": 5,
                    "source_type": source_type,
                    "purpose": "creator hook",
                    "visual_direction": "Natural surprised reaction"
                }
            ]
        }

    def test_job_compiler_requires_rights_approval(self) -> None:
        with self.assertRaisesRegex(ValueError, "rights_approved"):
            build_job(
                self.spec(),
                "s1",
                {"creator_image_url": "https://example.com/creator.jpg"},
            )

    def test_standard_creator_compiles_kling_job_after_rights_approval(self) -> None:
        job = build_job(
            self.spec(),
            "s1",
            {
                "rights_approved": True,
                "rights_evidence": "agreement:demo",
                "creator_image_url": "https://example.com/creator.jpg"
            },
        )
        self.assertEqual(job["model_id"], "fal-ai/kling-video/v3/standard/image-to-video")
        self.assertTrue(job["rights_approved"])
        self.assertFalse(job["approved_for_spend"])
        self.assertEqual(job["input"]["duration"], "5")

    def test_creative_dna_cannot_compile_literal_motion_transfer(self) -> None:
        with self.assertRaisesRegex(ValueError, "creative_dna_only"):
            build_job(
                self.spec(source_type="creator_motion_transfer"),
                "s1",
                {
                    "rights_approved": True,
                    "creator_image_url": "https://example.com/creator.jpg",
                    "motion_video_url": "https://example.com/motion.mp4"
                },
            )

    def test_licensed_motion_transfer_compiles(self) -> None:
        job = build_job(
            self.spec(rights_mode="licensed_performance_transfer", source_type="creator_motion_transfer"),
            "s1",
            {
                "rights_approved": True,
                "creator_image_url": "https://example.com/creator.jpg",
                "motion_video_url": "https://example.com/motion.mp4"
            },
        )
        self.assertEqual(job["model_id"], "fal-ai/kling-video/v3/standard/motion-control")

    def test_retry_policy_retries_one_stochastic_failure(self) -> None:
        decision = decide_retry(
            quality_tier="standard",
            attempt=1,
            failure_type="minor_deformation",
            estimated_next_cost_usd=0.42,
            spent_usd=0.42,
            budget_usd=2.0,
        )
        self.assertEqual(decision.action, "retry_same_tier")

    def test_retry_policy_escalates_identity_drift(self) -> None:
        decision = decide_retry(
            quality_tier="standard",
            attempt=1,
            failure_type="identity_drift",
            estimated_next_cost_usd=1.0,
            spent_usd=0.42,
            budget_usd=3.0,
        )
        self.assertEqual(decision.action, "escalate")
        self.assertEqual(decision.quality_tier, "premium")

    def test_retry_policy_never_retries_rights_failure(self) -> None:
        decision = decide_retry(
            quality_tier="standard",
            attempt=1,
            failure_type="rights",
            estimated_next_cost_usd=0.42,
            spent_usd=0,
            budget_usd=3.0,
        )
        self.assertEqual(decision.action, "stop")


if __name__ == "__main__":
    unittest.main()
