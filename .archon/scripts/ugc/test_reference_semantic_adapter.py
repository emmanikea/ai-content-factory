#!/usr/bin/env python3
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from enrich_reference_semantics import collect_keyframes, parse_json_response, validate_labels


class ReferenceSemanticAdapterTests(unittest.TestCase):
    def observation(self) -> dict:
        return {
            "id": "ref-1",
            "rights_mode": "creative_dna_only",
            "duration_seconds": 4.0,
            "segments": [
                {"id": "seg-001", "start": 0.0, "end": 2.0, "keyframe_path": None},
                {"id": "seg-002", "start": 2.0, "end": 4.0, "keyframe_path": None},
            ],
            "transcript": "Wait. Look at this.",
            "analysis": {"observer_version": "test"}
        }

    def labels(self) -> dict:
        return {
            "reference_id": "ref-1",
            "creative_dna": {
                "hook_mechanic": "curiosity",
                "structure": ["hook", "demo"],
                "cta_mechanic": "none"
            },
            "beats": [
                {"segment_id": "seg-001", "role": "hook", "shot_type": "creator"},
                {"segment_id": "seg-002", "role": "demo", "shot_type": "app_demo"}
            ]
        }

    def test_parses_plain_json(self) -> None:
        payload = {"reference_id": "ref-1"}
        self.assertEqual(parse_json_response(json.dumps(payload)), payload)

    def test_parses_fenced_json(self) -> None:
        text = '```json\n{"reference_id":"ref-1"}\n```'
        self.assertEqual(parse_json_response(text)["reference_id"], "ref-1")

    def test_validation_reuses_final_reference_contract(self) -> None:
        labels = self.labels()
        self.assertIs(validate_labels(self.observation(), labels), labels)

    def test_invalid_incomplete_labels_fail_closed(self) -> None:
        labels = self.labels()
        labels["beats"] = labels["beats"][:1]
        with self.assertRaisesRegex(ValueError, "label every observed segment"):
            validate_labels(self.observation(), labels)

    def test_collect_keyframes_only_uses_existing_files(self) -> None:
        observation = self.observation()
        with tempfile.TemporaryDirectory() as temp:
            frame = Path(temp) / "frame.jpg"
            frame.write_bytes(b"jpeg-ish")
            observation["segments"][0]["keyframe_path"] = str(frame)
            observation["segments"][1]["keyframe_path"] = str(Path(temp) / "missing.jpg")
            found = collect_keyframes(observation)
            self.assertEqual(len(found), 1)
            self.assertEqual(found[0][0], "seg-001")


if __name__ == "__main__":
    unittest.main()
