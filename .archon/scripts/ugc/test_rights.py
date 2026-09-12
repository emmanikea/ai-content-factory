#!/usr/bin/env python3
from __future__ import annotations

import unittest
from datetime import date

from rights import enforce_reference_mode, evaluate_creator_rights


class RightsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.creator = {
            "creator_type": "real_consenting",
            "rights": {
                "consent_state": "active",
                "valid_from": "2026-01-01",
                "valid_until": "2027-01-01",
                "allowed_products": ["bordereta"],
                "allowed_product_categories": ["apps"],
                "allowed_platforms": ["instagram", "tiktok"],
                "allowed_transformations": [
                    "face_generation",
                    "voice_clone",
                    "wardrobe_change",
                    "script_change"
                ]
            }
        }

    def test_valid_creator_rights_allow_render(self) -> None:
        decision = evaluate_creator_rights(
            self.creator,
            product_id="bordereta",
            product_category="apps",
            platform="instagram",
            transformations=["wardrobe_change", "script_change"],
            on_date=date(2026, 9, 12),
        )
        self.assertTrue(decision.allowed)
        self.assertEqual(decision.reasons, ())

    def test_unapproved_transformation_blocks(self) -> None:
        decision = evaluate_creator_rights(
            self.creator,
            product_id="bordereta",
            product_category="apps",
            platform="instagram",
            transformations=["motion_transfer"],
            on_date=date(2026, 9, 12),
        )
        self.assertFalse(decision.allowed)
        self.assertIn("transformation not permitted: motion_transfer", decision.reasons)

    def test_creative_dna_reference_blocks_literal_transfer(self) -> None:
        decision = enforce_reference_mode(
            {"rights_mode": "creative_dna_only"},
            "motion_transfer",
        )
        self.assertFalse(decision.allowed)

    def test_licensed_reference_allows_transfer(self) -> None:
        decision = enforce_reference_mode(
            {"rights_mode": "licensed_performance_transfer"},
            "motion_transfer",
        )
        self.assertTrue(decision.allowed)


if __name__ == "__main__":
    unittest.main()
