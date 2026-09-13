#!/usr/bin/env python3
from __future__ import annotations

import unittest
from datetime import date

from build_fal_job import build_job
from generate_creative_specs import generate_specs
from model_router import plan_spec
from prepare_creator_assets import prepare_assets


class DryPipelineIntegrationTests(unittest.TestCase):
    def campaign(self) -> dict:
        return {
            "campaign_id": "integration-campaign",
            "product": {"id": "bordereta", "name": "BorderETA", "category": "apps", "kind": "app"},
            "audience": "cross-border travelers",
            "platform": "instagram",
            "target_duration_seconds": 12.0,
            "creator_ids": ["creator-a"],
            "hook_options": ["Wait, why did nobody tell me this existed?"],
            "cta_options": ["Check BorderETA before your next crossing."],
            "locations": ["parked car"],
            "outfits": ["casual neutral top"],
            "app_capture_script": "open app; compare bridges; show selected route",
            "quality_tier": "standard",
            "render_resolution": "720p",
            "generate_native_audio": False,
            "max_render_cost_usd": 6,
            "use_literal_motion": False,
            "max_specs": 4,
        }

    def reference(self) -> dict:
        return {
            "id": "public-ref-1",
            "rights_mode": "creative_dna_only",
            "duration_seconds": 8.0,
            "creative_dna": {"hook_mechanic": "surprise then proof"},
            "beats": [
                {"id": "b1", "start": 0.0, "end": 2.0, "role": "hook", "shot_type": "creator", "framing": "close-up", "generic_motion": "small surprise reaction"},
                {"id": "b2", "start": 2.0, "end": 6.0, "role": "proof", "shot_type": "app_demo", "framing": "screen", "generic_motion": "tap and scroll"},
                {"id": "b3", "start": 6.0, "end": 8.0, "role": "CTA", "shot_type": "creator", "framing": "close-up", "generic_motion": "small nod"},
            ],
        }

    def creator_pack(self) -> dict:
        return {
            "creator_id": "creator-a",
            "creator_type": "real_consenting",
            "version": "v1",
            "canonical_images": [
                {"id": "front", "uri": "https://assets.example/front.jpg", "view": "front", "provenance": {"source_kind": "remote"}}
            ],
            "voice_samples": [],
            "performance_samples": [],
            "appearance_presets": {"outfits": [], "hairstyles": [], "locations": []},
            "provider_bindings": [],
            "rights_snapshot": {
                "consent_state": "active",
                "valid_from": "2026-01-01",
                "valid_until": "2027-01-01",
                "agreement_reference": "agreement:integration-test",
                "allowed_products": [],
                "allowed_product_categories": ["apps"],
                "allowed_platforms": ["instagram"],
                "allowed_transformations": ["face_generation", "script_change"],
            },
            "quality_summary": {
                "identity_image_count": 1,
                "views_present": ["front"],
                "voice_sample_count": 0,
                "performance_sample_count": 0,
                "warnings": ["fixture"],
                "semantic_identity_review_required": True,
            },
        }

    def test_campaign_to_provider_job_preserves_safety_and_deterministic_ui(self) -> None:
        specs = generate_specs(self.campaign(), self.reference())
        self.assertEqual(len(specs), 1)
        spec = specs[0]

        plan = plan_spec(spec)
        self.assertFalse(plan["blocked"])
        creator_items = [x for x in plan["items"] if x["source_type"] == "creator_generated"]
        app_items = [x for x in plan["items"] if x["source_type"] == "app_capture"]
        self.assertTrue(creator_items)
        self.assertEqual(app_items[0]["provider"], "local-playwright")
        self.assertEqual(app_items[0]["estimated_cost_usd"], 0.0)

        assets = prepare_assets(
            self.creator_pack(),
            product_id="bordereta",
            product_category="apps",
            platform="instagram",
            transformations=["face_generation", "script_change"],
            on_date=date(2026, 9, 12),
            require_remote=True,
        )
        self.assertTrue(assets["rights_approved"])

        first_creator_shot = next(x for x in spec["shots"] if x["source_type"] == "creator_generated")
        job = build_job(spec, first_creator_shot["id"], assets)
        self.assertTrue(job["rights_approved"])
        self.assertFalse(job["approved_for_spend"])
        self.assertEqual(job["provider"], "fal")
        self.assertEqual(job["provenance"]["rights_evidence"], "agreement:integration-test")
        self.assertEqual(job["provenance"]["creator_id"], "creator-a")
        self.assertEqual(job["provenance"]["quality_tier"], "standard")
        self.assertIn("prompt_strategy", job["provenance"])

    def test_public_reference_cannot_generate_motion_transfer_in_integration_path(self) -> None:
        campaign = self.campaign()
        campaign["use_literal_motion"] = True
        with self.assertRaisesRegex(ValueError, "does not allow performance transfer"):
            generate_specs(campaign, self.reference())


if __name__ == "__main__":
    unittest.main()
