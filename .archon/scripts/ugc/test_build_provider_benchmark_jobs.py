#!/usr/bin/env python3
from __future__ import annotations

import base64
import tempfile
import unittest
from pathlib import Path

from build_provider_benchmark_jobs import build_benchmark


def spec(duration: float = 3.2, source_type: str = "creator_generated") -> dict:
    return {
        "campaign_id": "campaign-1",
        "concept_id": "concept-1",
        "creator_id": "creator-1",
        "rights_mode": "owned_source",
        "shots": [
            {
                "id": "shot-1",
                "start": 0,
                "end": duration,
                "source_type": source_type,
                "purpose": "hook",
                "visual_direction": "Creator looks into camera and reacts naturally",
                "dialogue": "I use this before I cross the border.",
            }
        ],
    }


def full_assets() -> dict:
    return {
        "rights_approved": True,
        "rights_evidence": "agreement:test",
        "rights_decision": {"checked_on": "2026-09-17"},
        "creator_image_id": "front-1",
        "creator_image_url": "https://cdn.example.com/creator.jpg",
        "creator_image_base64": base64.b64encode(b"fake-image-bytes").decode("ascii"),
        "creator_image_mime_type": "image/jpeg",
    }


class ProviderBenchmarkJobTests(unittest.TestCase):
    def test_builds_all_four_spend_disabled_jobs_when_both_asset_forms_exist(self):
        bundle = build_benchmark(spec(), "shot-1", full_assets())
        self.assertEqual(bundle["target_duration_seconds"], 4)
        self.assertEqual(
            set(name for name, item in bundle["providers"].items() if item["available"]),
            {"fal-wan", "openrouter-seedance-fast", "google-veo-lite", "google-omni"},
        )
        for item in bundle["providers"].values():
            if item["available"]:
                self.assertTrue(item["job"]["rights_approved"])
                self.assertFalse(item["job"]["approved_for_spend"])

    def test_duration_rounds_to_common_veo_compatible_targets(self):
        self.assertEqual(build_benchmark(spec(3.9), "shot-1", full_assets())["target_duration_seconds"], 4)
        self.assertEqual(build_benchmark(spec(4.1), "shot-1", full_assets())["target_duration_seconds"], 6)
        self.assertEqual(build_benchmark(spec(6.1), "shot-1", full_assets())["target_duration_seconds"], 8)
        with self.assertRaises(ValueError):
            build_benchmark(spec(8.01), "shot-1", full_assets())

    def test_openrouter_uses_first_frame_and_native_audio(self):
        job = build_benchmark(spec(), "shot-1", full_assets())["providers"]["openrouter-seedance-fast"]["job"]
        frame = job["input"]["frame_images"][0]
        self.assertEqual(frame["frame_type"], "first_frame")
        self.assertEqual(frame["image_url"]["url"], "https://cdn.example.com/creator.jpg")
        self.assertTrue(job["input"]["generate_audio"])
        self.assertEqual(job["input"]["model"], "bytedance/seedance-2.0-fast")

    def test_google_jobs_use_same_inline_creator_bytes(self):
        providers = build_benchmark(spec(), "shot-1", full_assets())["providers"]
        veo = providers["google-veo-lite"]["job"]
        omni = providers["google-omni"]["job"]
        encoded = full_assets()["creator_image_base64"]
        self.assertEqual(veo["request"]["instances"][0]["image"]["inlineData"]["data"], encoded)
        self.assertEqual(omni["request"]["input"][0]["data"], encoded)
        self.assertIn("No scene cuts", omni["request"]["input"][1]["text"])

    def test_expected_4_second_costs_are_preserved_by_evidence_type(self):
        bundle = build_benchmark(spec(3.5), "shot-1", full_assets())
        providers = bundle["providers"]
        self.assertEqual(providers["fal-wan"]["job"]["estimated_cost_usd"], 0.4)
        self.assertEqual(providers["openrouter-seedance-fast"]["job"]["expected_cost_usd"], 0.1614)
        self.assertEqual(providers["google-veo-lite"]["job"]["max_provider_cost_usd"], 0.2)
        self.assertEqual(providers["google-omni"]["job"]["expected_duration_seconds"], 4)
        comparison = bundle["offline_comparison"]
        by_provider = {item["provider"]: item for item in comparison["items"]}
        self.assertEqual(by_provider["google-veo"]["cost_evidence_type"], "official_rate_formula")
        self.assertEqual(by_provider["google-omni"]["cost_evidence_type"], "official_effective_output_rate_approximation")

    def test_remote_only_does_not_make_google_fetch_arbitrary_url(self):
        assets = full_assets()
        assets.pop("creator_image_base64")
        assets.pop("creator_image_mime_type")
        bundle = build_benchmark(spec(), "shot-1", assets)
        self.assertTrue(bundle["providers"]["fal-wan"]["available"])
        self.assertTrue(bundle["providers"]["openrouter-seedance-fast"]["available"])
        self.assertFalse(bundle["providers"]["google-veo-lite"]["available"])
        self.assertFalse(bundle["providers"]["google-omni"]["available"])

    def test_local_only_does_not_pretend_hosted_providers_can_access_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "creator.jpg").write_bytes(b"fake-image-bytes")
            assets = {
                "rights_approved": True,
                "creator_image_id": "front-1",
                "creator_image_uri": "creator.jpg",
            }
            bundle = build_benchmark(spec(), "shot-1", assets, assets_base_dir=root)
            self.assertFalse(bundle["providers"]["fal-wan"]["available"])
            self.assertFalse(bundle["providers"]["openrouter-seedance-fast"]["available"])
            self.assertTrue(bundle["providers"]["google-veo-lite"]["available"])
            self.assertTrue(bundle["providers"]["google-omni"]["available"])

    def test_motion_transfer_is_rejected_as_not_comparable(self):
        with self.assertRaises(ValueError) as ctx:
            build_benchmark(spec(4, "creator_motion_transfer"), "shot-1", full_assets())
        self.assertIn("motion-transfer", str(ctx.exception))

    def test_rights_must_be_approved(self):
        assets = full_assets()
        assets["rights_approved"] = False
        with self.assertRaises(ValueError):
            build_benchmark(spec(), "shot-1", assets)


if __name__ == "__main__":
    unittest.main()
