#!/usr/bin/env python3
from __future__ import annotations

import unittest

from generate_creative_specs import generate_specs


class CreativeSpecGenerationTests(unittest.TestCase):
    def campaign(self) -> dict:
        return {
            "campaign_id": "bordereta-growth-01",
            "product": {"id": "bordereta", "name": "BorderETA", "category": "apps", "kind": "app"},
            "audience": "frequent cross-border travelers",
            "platform": "instagram",
            "target_duration_seconds": 18.0,
            "creator_ids": ["creator-a", "creator-b"],
            "hook_options": ["Wait, why did nobody tell me this existed?", "Stop guessing which bridge is faster."],
            "cta_options": ["Check BorderETA before your next crossing."],
            "locations": ["car"],
            "outfits": ["casual neutral top"],
            "role_lines": {"payoff": ["That is literally what I needed."]},
            "app_capture_script": "open app; compare bridges; select best option",
            "quality_tier": "standard",
            "render_resolution": "720p",
            "generate_native_audio": False,
            "max_render_cost_usd": 6,
            "max_specs": 10
        }

    def reference(self, rights_mode: str = "creative_dna_only") -> dict:
        return {
            "id": "ref-1",
            "rights_mode": rights_mode,
            "duration_seconds": 9.0,
            "creative_dna": {"hook_mechanic": "surprise / curiosity"},
            "beats": [
                {"id": "b1", "start": 0.0, "end": 1.5, "role": "hook reaction", "shot_type": "creator", "framing": "close-up", "generic_motion": "small surprise reaction"},
                {"id": "b2", "start": 1.5, "end": 5.0, "role": "demo", "shot_type": "app_demo", "framing": "screen", "generic_motion": "tap and scroll"},
                {"id": "b3", "start": 5.0, "end": 7.0, "role": "payoff", "shot_type": "creator", "framing": "medium close-up", "generic_motion": "small nod"},
                {"id": "b4", "start": 7.0, "end": 9.0, "role": "end card", "shot_type": "graphic", "framing": None, "generic_motion": None},
            ]
        }

    def test_generates_combinatorial_variants_without_rendering(self) -> None:
        specs = generate_specs(self.campaign(), self.reference())
        self.assertEqual(len(specs), 4)
        self.assertEqual({x["creator_id"] for x in specs}, {"creator-a", "creator-b"})
        self.assertEqual({x["hook"] for x in specs}, set(self.campaign()["hook_options"]))

    def test_scales_reference_timing_to_campaign_duration(self) -> None:
        spec = generate_specs(self.campaign(), self.reference())[0]
        self.assertEqual(spec["duration_seconds"], 18.0)
        self.assertEqual(spec["shots"][0]["end"], 3.0)
        self.assertEqual(spec["shots"][-1]["end"], 18.0)

    def test_maps_app_demo_to_deterministic_capture(self) -> None:
        spec = generate_specs(self.campaign(), self.reference())[0]
        app = spec["shots"][1]
        self.assertEqual(app["source_type"], "app_capture")
        self.assertEqual(app["capture_script"], self.campaign()["app_capture_script"])
        self.assertIn("real app UI", app["visual_direction"])

    def test_hook_and_cta_land_on_first_and_last_creator_beats(self) -> None:
        campaign = self.campaign()
        spec = generate_specs(campaign, self.reference())[0]
        creator_shots = [x for x in spec["shots"] if x["source_type"] == "creator_generated"]
        self.assertEqual(creator_shots[0]["dialogue"], campaign["hook_options"][0])
        self.assertEqual(creator_shots[-1]["dialogue"], campaign["cta_options"][0])
        self.assertIn(campaign["cta_options"][0], spec["script"])

    def test_render_controls_are_carried_into_spec(self) -> None:
        spec = generate_specs(self.campaign(), self.reference())[0]
        self.assertEqual(spec["render_resolution"], "720p")
        self.assertFalse(spec["generate_native_audio"])
        self.assertEqual(spec["quality_tier"], "standard")

    def test_creative_dna_reference_blocks_literal_motion_generation(self) -> None:
        campaign = self.campaign()
        campaign["use_literal_motion"] = True
        with self.assertRaisesRegex(ValueError, "does not allow"):
            generate_specs(campaign, self.reference("creative_dna_only"))

    def test_licensed_reference_can_generate_motion_transfer_shots(self) -> None:
        campaign = self.campaign()
        campaign["use_literal_motion"] = True
        spec = generate_specs(campaign, self.reference("licensed_performance_transfer"))[0]
        creator_shots = [x for x in spec["shots"] if x["source_type"] == "creator_motion_transfer"]
        self.assertEqual(len(creator_shots), 2)
        self.assertTrue(all(x["motion_reference_id"] == "ref-1" for x in creator_shots))

    def test_max_specs_caps_combinatorial_explosion(self) -> None:
        campaign = self.campaign()
        campaign["max_specs"] = 2
        specs = generate_specs(campaign, self.reference())
        self.assertEqual(len(specs), 2)


if __name__ == "__main__":
    unittest.main()
