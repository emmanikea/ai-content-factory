#!/usr/bin/env python3
from __future__ import annotations

import tempfile
import unittest
from datetime import date, datetime, timezone

from creator_revocation import apply_revocation, get_revocation, is_creator_revoked, record_revocation
from local_store import LocalStore
from prepare_creator_assets import prepare_assets


def pack() -> dict:
    return {
        "creator_id": "creator-a",
        "creator_type": "real_consenting",
        "version": "v1",
        "canonical_images": [
            {"id": "front", "uri": "https://assets.example/front.jpg", "view": "front", "provenance": {"source_kind": "remote"}}
        ],
        "performance_samples": [],
        "rights_snapshot": {
            "consent_state": "active",
            "valid_from": "2026-01-01",
            "valid_until": "2027-01-01",
            "agreement_reference": "agreement:test",
            "allowed_products": [],
            "allowed_product_categories": ["apps"],
            "allowed_platforms": ["instagram"],
            "allowed_transformations": ["face_generation", "script_change"],
        },
    }


class CreatorRevocationTests(unittest.TestCase):
    def test_revocation_is_separate_from_historical_creator_pack(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            store = LocalStore(temp)
            original = pack()
            store.put("creators", "creator-a-v1", original)
            result = record_revocation(store, "creator-a", reason="creator withdrew consent")
            self.assertTrue(is_creator_revoked(store, "creator-a"))
            self.assertEqual(get_revocation(store, "creator-a")["reason"], "creator withdrew consent")
            self.assertEqual(store.get("creators", "creator-a-v1"), original)
            self.assertIn("revocation_id", result)

    def test_propagation_disables_matching_jobs_and_blocks_artifact_reuse(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            store = LocalStore(temp)
            store.put("jobs", "job-a", {
                "provider": "fal",
                "rights_approved": True,
                "approved_for_spend": True,
                "provenance": {"creator_id": "creator-a"},
            })
            store.put("jobs", "job-b", {
                "provider": "fal",
                "rights_approved": True,
                "approved_for_spend": True,
                "provenance": {"creator_id": "creator-b"},
            })
            store.put("artifacts", "artifact-a", {
                "artifact_id": "artifact-a",
                "creator_id": "creator-a",
                "uri": "r2://bucket/a.mp4",
            })
            result = record_revocation(store, "creator-a", reason="creator withdrew consent")
            job_a = store.get("jobs", "job-a")
            job_b = store.get("jobs", "job-b")
            artifact = store.get("artifacts", "artifact-a")
            self.assertFalse(job_a["rights_approved"])
            self.assertFalse(job_a["approved_for_spend"])
            self.assertEqual(job_a["rights_status"], "revoked")
            self.assertTrue(job_b["rights_approved"])
            self.assertTrue(job_b["approved_for_spend"])
            self.assertTrue(artifact["reuse_blocked"])
            self.assertTrue(artifact["distribution_review_required"])
            self.assertEqual(result["affected_jobs"], ["job-a"])
            self.assertEqual(result["affected_artifacts"], ["artifact-a"])

    def test_historical_on_date_cannot_bypass_current_revocation(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            store = LocalStore(temp)
            record_revocation(store, "creator-a", reason="creator withdrew consent")
            with self.assertRaisesRegex(ValueError, "creator rights revoked"):
                prepare_assets(
                    pack(),
                    product_id="bordereta",
                    product_category="apps",
                    platform="instagram",
                    transformations=["face_generation"],
                    on_date=date(2026, 1, 15),
                    revocation_store=store,
                )

    def test_future_revocation_can_be_applied_once_effective(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            store = LocalStore(temp)
            store.put("jobs", "job-a", {
                "rights_approved": True,
                "approved_for_spend": True,
                "provenance": {"creator_id": "creator-a"},
            })
            result = record_revocation(
                store,
                "creator-a",
                reason="scheduled end of consent",
                effective_at="2027-01-01T00:00:00+00:00",
            )
            self.assertFalse(result["propagated"])
            self.assertFalse(is_creator_revoked(store, "creator-a", at="2026-09-17T00:00:00+00:00"))
            self.assertTrue(is_creator_revoked(store, "creator-a", at="2027-01-02T00:00:00+00:00"))
            applied = apply_revocation(
                store,
                "creator-a",
                now=datetime(2027, 1, 2, tzinfo=timezone.utc),
            )
            self.assertTrue(applied["applied"])
            self.assertFalse(store.get("jobs", "job-a")["rights_approved"])

    def test_duplicate_revocation_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            store = LocalStore(temp)
            record_revocation(store, "creator-a", reason="first")
            with self.assertRaisesRegex(ValueError, "already has a revocation"):
                record_revocation(store, "creator-a", reason="second")


if __name__ == "__main__":
    unittest.main()
