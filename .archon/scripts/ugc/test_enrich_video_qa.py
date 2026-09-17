#!/usr/bin/env python3
from __future__ import annotations

import unittest

from enrich_video_qa import merge_semantic_result, parse_semantic_qa, semantic_prompt


class SemanticQATests(unittest.TestCase):
    def base(self) -> dict:
        return {
            "artifact_id": "a1",
            "profile": "creator_shot",
            "status": "needs_review",
            "checked_at": "2026-09-12T00:00:00+00:00",
            "score": None,
            "deterministic_checks": [{"name": "duration_readable", "status": "pass", "value": 5.0, "message": None}],
            "semantic_checks": [
                {"name": "identity_consistency", "status": "needs_review", "value": None, "message": "semantic QA has not run"},
                {"name": "face_anatomy", "status": "needs_review", "value": None, "message": "semantic QA has not run"},
                {"name": "hands_limbs", "status": "needs_review", "value": None, "message": "semantic QA has not run"},
                {"name": "motion_naturalness", "status": "needs_review", "value": None, "message": "semantic QA has not run"},
                {"name": "lip_sync", "status": "needs_review", "value": None, "message": "semantic QA has not run"},
            ],
            "failures": [],
            "retry_hint": "manual_review",
            "provenance": {"qa_stage": "deterministic"}
        }

    def test_parse_fenced_json(self) -> None:
        parsed = parse_semantic_qa('```json\n{"score":90,"checks":{},"failures":[]}\n```')
        self.assertEqual(parsed["score"], 90)

    def test_visual_pass_still_leaves_unassessed_checks_needing_review(self) -> None:
        semantic = {
            "score": 92,
            "checks": {
                "identity_consistency": {"status": "pass", "message": "stable"},
                "face_anatomy": {"status": "pass", "message": "natural"},
                "hands_limbs": {"status": "pass", "message": "natural"},
            },
            "failures": []
        }
        result = merge_semantic_result(self.base(), semantic, provider="test", model="vision")
        self.assertEqual(result["status"], "needs_review")
        lip = next(x for x in result["semantic_checks"] if x["name"] == "lip_sync")
        self.assertEqual(lip["status"], "needs_review")

    def test_retryable_visual_failure_requests_retry(self) -> None:
        semantic = {
            "score": 42,
            "checks": {
                "identity_consistency": {"status": "fail", "message": "face drifts"},
                "face_anatomy": {"status": "pass", "message": "ok"},
                "hands_limbs": {"status": "pass", "message": "ok"},
            },
            "failures": [{"code": "identity_drift", "severity": "retryable", "message": "face drifts"}]
        }
        result = merge_semantic_result(self.base(), semantic, provider="test", model="vision")
        self.assertEqual(result["status"], "fail")
        self.assertEqual(result["retry_hint"], "retry_same")

    def test_deterministic_structural_failure_cannot_be_overridden(self) -> None:
        base = self.base()
        base["status"] = "fail"
        base["failures"] = [{"code": "wrong_aspect", "severity": "structural", "message": "wrong aspect"}]
        semantic = {
            "score": 99,
            "checks": {
                "identity_consistency": {"status": "pass", "message": "stable"},
                "face_anatomy": {"status": "pass", "message": "natural"},
                "hands_limbs": {"status": "pass", "message": "natural"},
            },
            "failures": []
        }
        result = merge_semantic_result(base, semantic, provider="test", model="vision")
        self.assertEqual(result["status"], "fail")
        self.assertEqual(result["retry_hint"], "stop")

    def test_missing_identity_refs_prompt_forces_conservative_result(self) -> None:
        prompt = semantic_prompt("creator_shot", "hook", False)
        self.assertIn("Do not claim identity_consistency passed", prompt)
        self.assertIn("Do not infer rights", prompt)


if __name__ == "__main__":
    unittest.main()
