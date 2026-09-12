#!/usr/bin/env python3
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from build_identity_pack import build_identity_pack


class IdentityPackTests(unittest.TestCase):
    def manifest(self) -> dict:
        return {
            "creator_id": "creator-a",
            "creator_type": "real_consenting",
            "version": "test-v1",
            "canonical_images": [
                {"id": "front", "uri": "front.jpg", "view": "front"},
                {"id": "threeq", "uri": "threeq.jpg", "view": "three_quarter"},
                {"id": "body", "uri": "body.jpg", "view": "full_body"},
            ],
            "voice_samples": [],
            "performance_samples": [],
            "appearance_presets": {"outfits": [], "hairstyles": [], "locations": []},
            "provider_bindings": [],
            "rights_snapshot": {
                "consent_state": "active",
                "agreement_reference": "agreement:test",
                "allowed_transformations": ["face_generation", "script_change"]
            }
        }

    def make_assets(self, root: Path) -> None:
        for name in ("front.jpg", "threeq.jpg", "body.jpg"):
            (root / name).write_bytes((name * 5).encode("utf-8"))

    def test_builds_portable_pack_and_hashes_local_assets(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.make_assets(root)
            pack = build_identity_pack(self.manifest(), base_dir=root)
            self.assertEqual(pack["creator_id"], "creator-a")
            self.assertEqual(pack["canonical_images"][0]["provenance"]["source_kind"], "local")
            self.assertEqual(len(pack["canonical_images"][0]["provenance"]["sha256"]), 64)
            self.assertTrue(pack["quality_summary"]["semantic_identity_review_required"])
            self.assertTrue(any("fewer than 5" in x for x in pack["quality_summary"]["warnings"]))

    def test_real_creator_requires_active_consent(self) -> None:
        manifest = self.manifest()
        manifest["rights_snapshot"]["consent_state"] = "revoked"
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.make_assets(root)
            with self.assertRaisesRegex(ValueError, "consent_state=active"):
                build_identity_pack(manifest, base_dir=root)

    def test_real_creator_requires_agreement_reference(self) -> None:
        manifest = self.manifest()
        manifest["rights_snapshot"].pop("agreement_reference")
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.make_assets(root)
            with self.assertRaisesRegex(ValueError, "agreement_reference"):
                build_identity_pack(manifest, base_dir=root)

    def test_motion_transfer_sample_requires_motion_transfer_right(self) -> None:
        manifest = self.manifest()
        manifest["performance_samples"] = [
            {
                "id": "reaction-1",
                "uri": "https://assets.example/reaction.mp4",
                "performance_type": "reaction",
                "approved_for_motion_transfer": True
            }
        ]
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.make_assets(root)
            with self.assertRaisesRegex(ValueError, "motion_transfer"):
                build_identity_pack(manifest, base_dir=root)

    def test_remote_assets_are_not_downloaded(self) -> None:
        manifest = self.manifest()
        manifest["canonical_images"] = [
            {"id": "front", "uri": "https://assets.example/front.jpg", "view": "front"},
            {"id": "threeq", "uri": "https://assets.example/threeq.jpg", "view": "three_quarter"},
            {"id": "body", "uri": "https://assets.example/body.jpg", "view": "full_body"},
            {"id": "expr1", "uri": "https://assets.example/expr1.jpg", "view": "expression"},
            {"id": "expr2", "uri": "https://assets.example/expr2.jpg", "view": "expression"},
            {"id": "profile", "uri": "https://assets.example/profile.jpg", "view": "profile"},
            {"id": "upper", "uri": "https://assets.example/upper.jpg", "view": "upper_body"},
            {"id": "other", "uri": "https://assets.example/other.jpg", "view": "other"}
        ]
        pack = build_identity_pack(manifest, base_dir=Path("."))
        self.assertEqual(pack["canonical_images"][0]["provenance"], {"source_kind": "remote"})
        self.assertFalse(any("8-12" in x for x in pack["quality_summary"]["warnings"]))


if __name__ == "__main__":
    unittest.main()
