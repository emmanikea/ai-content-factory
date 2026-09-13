#!/usr/bin/env python3
from __future__ import annotations

import unittest

from generate_creative_specs import generate_specs
from schema_validation import validate_document


class SchemaValidationTests(unittest.TestCase):
    def campaign(self) -> dict:
        return {
            "campaign_id": "c1",
            "product": {"id": "p1", "name": "App", "category": "apps", "kind": "app"},
            "audience": "users",
            "platform": "instagram",
            "creator_ids": ["creator-a"],
            "hook_options": ["Hook"],
            "cta_options": ["CTA"],
            "quality_tier": "standard",
            "render_resolution": "720p",
            "generate_native_audio": False,
            "max_specs": 1,
        }

    def reference(self) -> dict:
        return {
            "id": "r1",
            "rights_mode": "creative_dna_only",
            "duration_seconds": 8,
            "creative_dna": {"hook_mechanic": "curiosity"},
            "beats": [
                {"id": "b1", "start": 0, "end": 2, "role": "hook", "shot_type": "creator", "framing": None, "generic_motion": None},
                {"id": "b2", "start": 2, "end": 6, "role": "demo", "shot_type": "app_demo", "framing": None, "generic_motion": None},
                {"id": "b3", "start": 6, "end": 8, "role": "CTA", "shot_type": "creator", "framing": None, "generic_motion": None},
            ],
        }

    def test_campaign_brief_validates(self) -> None:
        validate_document("campaign_brief", self.campaign())

    def test_generated_creative_spec_validates(self) -> None:
        spec = generate_specs(self.campaign(), self.reference())[0]
        validate_document("creative_spec", spec)

    def test_unknown_field_is_rejected(self) -> None:
        campaign = self.campaign()
        campaign["made_up_field"] = True
        with self.assertRaisesRegex(ValueError, "made_up_field"):
            validate_document("campaign_brief", campaign)

    def test_bad_rights_mode_is_rejected(self) -> None:
        spec = generate_specs(self.campaign(), self.reference())[0]
        spec["rights_mode"] = "anything_goes"
        with self.assertRaisesRegex(ValueError, "anything_goes"):
            validate_document("creative_spec", spec)


if __name__ == "__main__":
    unittest.main()
