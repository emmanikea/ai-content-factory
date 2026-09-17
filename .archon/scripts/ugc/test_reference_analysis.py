#!/usr/bin/env python3
from __future__ import annotations

import unittest

from build_reference_analysis import build_reference_analysis, semantic_enrichment_prompt
from observe_reference import build_segments


class ReferenceAnalysisTests(unittest.TestCase):
    def observation(self, rights_mode: str = "creative_dna_only") -> dict:
        return {
            "id": "ref-1",
            "source_path": "/tmp/ref.mp4",
            "source_sha256": "abc",
            "rights_mode": rights_mode,
            "duration_seconds": 9.0,
            "video": {"width": 1080, "height": 1920, "fps": 30.0, "has_audio": True},
            "cuts": [1.0, 3.0, 7.0],
            "segments": [
                {"id": "seg-001", "start": 0.0, "end": 1.0, "keyframe_path": None},
                {"id": "seg-002", "start": 1.0, "end": 3.0, "keyframe_path": None},
                {"id": "seg-003", "start": 3.0, "end": 7.0, "keyframe_path": None},
                {"id": "seg-004", "start": 7.0, "end": 9.0, "keyframe_path": None},
            ],
            "transcript": "Wait, look at this. Here is how it works. Try it.",
            "transcript_segments": [],
            "analysis": {
                "observer_version": "test",
                "scene_threshold": 0.35,
                "semantic_enrichment_required": True,
                "transcription_source": None
            }
        }

    def semantics(self) -> dict:
        return {
            "reference_id": "ref-1",
            "creative_dna": {
                "hook_mechanic": "surprise / curiosity",
                "structure": ["reaction", "demo", "proof", "CTA"],
                "camera_language": ["phone close-up"],
                "editing_language": ["hard cuts"],
                "performance_style": ["conversational"],
                "cta_mechanic": "low-pressure recommendation",
                "what_to_preserve": ["fast hook", "demo before payoff"],
                "what_to_change": ["creator", "product", "script"]
            },
            "beats": [
                {"segment_id": "seg-001", "role": "hook", "shot_type": "creator", "framing": "close-up"},
                {"segment_id": "seg-002", "role": "setup", "shot_type": "creator", "framing": "medium close-up"},
                {"segment_id": "seg-003", "role": "demo", "shot_type": "app_demo", "framing": "screen"},
                {"segment_id": "seg-004", "role": "cta", "shot_type": "creator", "framing": "close-up"}
            ]
        }

    def test_build_segments_uses_cut_boundaries(self) -> None:
        segments = build_segments(10.0, [2.0, 5.0, 8.0])
        self.assertEqual([(x["start"], x["end"]) for x in segments], [(0.0, 2.0), (2.0, 5.0), (5.0, 8.0), (8.0, 10.0)])

    def test_creative_dna_reference_never_enables_literal_motion(self) -> None:
        result = build_reference_analysis(self.observation(), self.semantics())
        self.assertTrue(all(not x["literal_motion_reference_allowed"] for x in result["beats"]))
        self.assertIn("brisk pacing", result["creative_dna"]["pacing"])

    def test_licensed_reference_enables_literal_motion(self) -> None:
        result = build_reference_analysis(self.observation("licensed_performance_transfer"), self.semantics())
        self.assertTrue(all(x["literal_motion_reference_allowed"] for x in result["beats"]))

    def test_missing_segment_label_is_rejected(self) -> None:
        semantics = self.semantics()
        semantics["beats"] = semantics["beats"][:-1]
        with self.assertRaisesRegex(ValueError, "label every observed segment"):
            build_reference_analysis(self.observation(), semantics)

    def test_semantic_reference_id_must_match(self) -> None:
        semantics = self.semantics()
        semantics["reference_id"] = "wrong"
        with self.assertRaisesRegex(ValueError, "does not match"):
            build_reference_analysis(self.observation(), semantics)

    def test_semantic_prompt_keeps_rights_separate_from_visuals(self) -> None:
        prompt = semantic_enrichment_prompt(self.observation())
        self.assertIn("label every segment exactly once", prompt)
        self.assertIn("Do not infer literal motion-transfer permission", prompt)
        self.assertIn("creative_dna_only", prompt)


if __name__ == "__main__":
    unittest.main()
