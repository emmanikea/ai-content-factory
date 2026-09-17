#!/usr/bin/env python3
from __future__ import annotations

import unittest

from prompt_compiler import MAX_WORDS, compile_shot_prompt


class PromptCompilerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.shot = {
            "purpose": "hook reaction",
            "visual_direction": "Creator widens her eyes, gives a small surprised smile, then glances toward the phone. Camera makes a subtle handheld push in",
            "dialogue": "Wait, why did nobody tell me this existed?",
        }

    def test_i2v_prompt_is_motion_first(self) -> None:
        result = compile_shot_prompt(
            self.shot,
            model_id="fal-ai/kling-video/v3/standard/image-to-video",
            generate_audio=False,
        )
        self.assertEqual(result.strategy, "image_to_video_motion_first")
        self.assertIn("widens her eyes", result.text)
        self.assertIn("later lip sync", result.text)
        self.assertLessEqual(len(result.text.split()), MAX_WORDS)

    def test_native_audio_includes_dialogue(self) -> None:
        result = compile_shot_prompt(
            self.shot,
            model_id="alibaba/wan-3.0/image-to-video",
            generate_audio=True,
        )
        self.assertIn('"Wait, why did nobody tell me this existed?"', result.text)
        self.assertNotIn("later lip sync", result.text)

    def test_motion_transfer_treats_reference_as_performance_source(self) -> None:
        result = compile_shot_prompt(
            self.shot,
            model_id="fal-ai/kling-video/v3/standard/motion-control",
            generate_audio=False,
        )
        self.assertEqual(result.strategy, "licensed_motion_transfer")
        self.assertIn("performance and timing source", result.text)
        self.assertIn("source body motion", result.text)

    def test_seedance_gets_structured_multimodal_direction(self) -> None:
        result = compile_shot_prompt(
            self.shot,
            model_id="bytedance/seedance-2.5/reference-to-video",
            generate_audio=True,
        )
        self.assertEqual(result.strategy, "multimodal_reference_directed")
        self.assertIn("Shot objective:", result.text)
        self.assertIn("Performance and camera:", result.text)
        self.assertIn("Reference media defines", result.text)

    def test_prompt_is_capped(self) -> None:
        shot = dict(self.shot)
        shot["visual_direction"] = " ".join(["natural motion"] * 200)
        result = compile_shot_prompt(
            shot,
            model_id="fal-ai/kling-video/v3/standard/image-to-video",
        )
        self.assertLessEqual(len(result.text.split()), MAX_WORDS)


if __name__ == "__main__":
    unittest.main()
