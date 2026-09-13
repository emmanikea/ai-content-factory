#!/usr/bin/env python3
from __future__ import annotations

import unittest

from qa_video import evaluate_metadata


class QAVideoTests(unittest.TestCase):
    def meta(self) -> dict:
        return {
            "duration_seconds": 10.0,
            "width": 1080,
            "height": 1920,
            "fps": 30.0,
            "has_audio": True,
        }

    def test_structurally_good_creator_shot_needs_semantic_review(self) -> None:
        result = evaluate_metadata(
            self.meta(),
            artifact_id="a1",
            profile="creator_shot",
            expected_duration=10.0,
            black_seconds=0.0,
        )
        self.assertEqual(result["status"], "needs_review")
        self.assertEqual(result["failures"], [])
        self.assertTrue(all(x["status"] == "needs_review" for x in result["semantic_checks"]))

    def test_wrong_aspect_hard_fails_vertical_profile(self) -> None:
        meta = self.meta()
        meta.update({"width": 1920, "height": 1080})
        result = evaluate_metadata(meta, artifact_id="a1", profile="final_reel", black_seconds=0.0)
        self.assertEqual(result["status"], "fail")
        self.assertIn("wrong_aspect", [x["code"] for x in result["failures"]])
        self.assertEqual(result["retry_hint"], "stop")

    def test_duration_mismatch_fails(self) -> None:
        result = evaluate_metadata(
            self.meta(),
            artifact_id="a1",
            profile="creator_shot",
            expected_duration=7.0,
            duration_tolerance=0.5,
            black_seconds=0.0,
        )
        self.assertIn("duration_mismatch", [x["code"] for x in result["failures"]])

    def test_missing_required_audio_fails(self) -> None:
        meta = self.meta()
        meta["has_audio"] = False
        result = evaluate_metadata(meta, artifact_id="a1", profile="final_reel", require_audio=True, black_seconds=0.0)
        self.assertIn("missing_audio", [x["code"] for x in result["failures"]])

    def test_excessive_black_frames_fail(self) -> None:
        result = evaluate_metadata(self.meta(), artifact_id="a1", profile="final_reel", black_seconds=1.2)
        self.assertIn("excessive_black_frames", [x["code"] for x in result["failures"]])

    def test_broll_does_not_require_vertical_aspect(self) -> None:
        meta = self.meta()
        meta.update({"width": 1920, "height": 1080})
        result = evaluate_metadata(meta, artifact_id="broll-1", profile="broll", black_seconds=0.0)
        names = [x["name"] for x in result["deterministic_checks"]]
        self.assertNotIn("vertical_aspect", names)
        self.assertEqual(result["status"], "needs_review")


if __name__ == "__main__":
    unittest.main()
