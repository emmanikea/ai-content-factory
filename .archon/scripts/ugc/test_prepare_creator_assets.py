#!/usr/bin/env python3
from __future__ import annotations

import unittest
from datetime import date

from prepare_creator_assets import prepare_assets


class PrepareCreatorAssetsTests(unittest.TestCase):
    def pack(self) -> dict:
        return {
            "creator_id": "creator-a",
            "creator_type": "real_consenting",
            "version": "v1",
            "canonical_images": [
                {"id": "front", "uri": "https://assets.example/front.jpg", "view": "front", "provenance": {"source_kind": "remote"}},
                {"id": "body", "uri": "https://assets.example/body.jpg", "view": "full_body", "provenance": {"source_kind": "remote"}}
            ],
            "performance_samples": [
                {"id": "reaction", "uri": "https://assets.example/reaction.mp4", "performance_type": "reaction", "approved_for_motion_transfer": True, "provenance": {"source_kind": "remote"}}
            ],
            "rights_snapshot": {
                "consent_state": "active",
                "valid_from": "2026-01-01",
                "valid_until": "2027-01-01",
                "agreement_reference": "agreement:test",
                "allowed_products": [],
                "allowed_product_categories": ["apps"],
                "allowed_platforms": ["instagram"],
                "allowed_transformations": ["face_generation", "motion_transfer", "script_change"]
            }
        }

    def test_derives_rights_approved_from_pack(self) -> None:
        assets = prepare_assets(
            self.pack(),
            product_id="bordereta",
            product_category="apps",
            platform="instagram",
            transformations=["face_generation", "script_change"],
            on_date=date(2026, 9, 12),
            require_remote=True,
        )
        self.assertTrue(assets["rights_approved"])
        self.assertEqual(assets["rights_evidence"], "agreement:test")
        self.assertEqual(assets["creator_image_url"], "https://assets.example/front.jpg")
        self.assertFalse(assets["needs_hosted_upload"])

    def test_category_restriction_blocks_unrelated_product(self) -> None:
        with self.assertRaisesRegex(ValueError, "product/category not permitted"):
            prepare_assets(
                self.pack(),
                product_id="drink-1",
                product_category="beverage",
                platform="instagram",
                transformations=["face_generation"],
                on_date=date(2026, 9, 12),
            )

    def test_motion_sample_requires_requested_motion_transformation(self) -> None:
        with self.assertRaisesRegex(ValueError, "requires motion_transfer"):
            prepare_assets(
                self.pack(),
                product_id="bordereta",
                product_category="apps",
                platform="instagram",
                transformations=["face_generation"],
                performance_id="reaction",
                on_date=date(2026, 9, 12),
            )

    def test_approved_motion_sample_yields_motion_url(self) -> None:
        assets = prepare_assets(
            self.pack(),
            product_id="bordereta",
            product_category="apps",
            platform="instagram",
            transformations=["face_generation", "motion_transfer"],
            performance_id="reaction",
            on_date=date(2026, 9, 12),
            require_remote=True,
        )
        self.assertEqual(assets["motion_video_url"], "https://assets.example/reaction.mp4")
        self.assertEqual(assets["motion_performance_id"], "reaction")

    def test_expired_rights_are_blocked(self) -> None:
        with self.assertRaisesRegex(ValueError, "expired"):
            prepare_assets(
                self.pack(),
                product_id="bordereta",
                product_category="apps",
                platform="instagram",
                transformations=["face_generation"],
                on_date=date(2028, 1, 1),
            )


if __name__ == "__main__":
    unittest.main()
