#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import os
import unittest
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[3]
CLIENT_PATH = REPO_ROOT / "ugc-studio" / "providers" / "openrouter" / "client.py"
spec = importlib.util.spec_from_file_location("openrouter_video_provider", CLIENT_PATH)
orv = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(orv)


class OpenRouterVideoProviderTests(unittest.TestCase):
    def job(self) -> dict:
        return {
            "version": "1.0",
            "provider": "openrouter",
            "input": {
                "model": "bytedance/seedance-2.0",
                "prompt": "Natural creator reaction with subtle handheld movement.",
                "duration": 4,
                "resolution": "720p",
                "aspect_ratio": "9:16",
                "generate_audio": False,
            },
            "rights_approved": True,
            "approved_for_spend": False,
            "expected_cost_usd": 0.30,
            "max_provider_cost_usd": 0.50,
        }

    def catalog_row(self) -> dict:
        return {
            "id": "bytedance/seedance-2.0",
            "supported_parameters": {
                "duration": {"type": "enum", "values": [4, 5, 6, 8, 10]},
                "resolution": {"type": "enum", "values": ["480p", "720p"]},
                "aspect_ratio": {"type": "enum", "values": ["9:16", "16:9"]},
            },
            "pricing_skus": [{"name": "example", "price": "0.06726"}],
        }

    def test_dry_run_never_requires_key_or_network(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            with patch.object(orv, "preflight") as preflight:
                result = orv.run_job(self.job())
        self.assertEqual(result["mode"], "dry-run")
        preflight.assert_not_called()

    def test_preflight_reads_live_catalog_without_submit(self) -> None:
        with patch.object(orv, "find_video_model", return_value=self.catalog_row()), \
             patch.object(orv, "submit") as submit:
            result = orv.run_job(self.job(), preflight_only=True, api_key="key")
        self.assertEqual(result["preflight"]["model"], "bytedance/seedance-2.0")
        self.assertTrue(result["preflight"]["pricing_skus"])
        submit.assert_not_called()

    def test_catalog_validation_rejects_unsupported_resolution(self) -> None:
        body = dict(self.job()["input"])
        body["resolution"] = "1080p"
        with self.assertRaisesRegex(orv.OpenRouterError, "resolution"):
            orv.validate_request_against_catalog(body, self.catalog_row())

    def test_live_requires_spend_approval(self) -> None:
        with patch.object(orv, "preflight", return_value={"catalog_snapshot": self.catalog_row(), "pricing_skus": []}):
            with self.assertRaisesRegex(orv.OpenRouterError, "approved_for_spend"):
                orv.run_job(self.job(), live=True, api_key="key")

    def test_live_requires_budget_envelope(self) -> None:
        job = self.job()
        job["approved_for_spend"] = True
        job["expected_cost_usd"] = None
        with patch.object(orv, "preflight", return_value={"catalog_snapshot": self.catalog_row(), "pricing_skus": []}):
            with self.assertRaisesRegex(orv.OpenRouterError, "expected_cost_usd"):
                orv.run_job(job, live=True, api_key="key")

    def test_preflight_blocks_expected_cost_over_cap(self) -> None:
        job = self.job()
        job["expected_cost_usd"] = 0.75
        with patch.object(orv, "find_video_model", return_value=self.catalog_row()):
            with self.assertRaisesRegex(orv.OpenRouterError, "exceeds approved provider cap"):
                orv.preflight(job, api_key="key")

    def test_live_captures_actual_usage_cost(self) -> None:
        job = self.job()
        job["approved_for_spend"] = True
        initial = {"id": "job-1", "status": "pending", "polling_url": "https://openrouter.ai/api/v1/videos/job-1"}
        terminal = {
            "id": "job-1",
            "status": "completed",
            "unsigned_urls": ["https://openrouter.ai/api/v1/videos/job-1/content?index=0"],
            "usage": {"cost": 0.42, "is_byok": False},
        }
        pf = {"catalog_snapshot": self.catalog_row(), "pricing_skus": self.catalog_row()["pricing_skus"]}
        with patch.object(orv, "preflight", return_value=pf), \
             patch.object(orv, "submit", return_value=initial), \
             patch.object(orv, "wait_for_terminal", return_value=terminal):
            result = orv.run_job(job, live=True, api_key="key")
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["actual_cost_usd"], 0.42)
        self.assertFalse(result["cost_cap_exceeded_after_run"])

    def test_actual_cost_over_cap_is_recorded_not_hidden(self) -> None:
        job = self.job()
        job["approved_for_spend"] = True
        initial = {"id": "job-1", "status": "pending", "polling_url": "https://openrouter.ai/api/v1/videos/job-1"}
        terminal = {"id": "job-1", "status": "completed", "usage": {"cost": 0.72}}
        pf = {"catalog_snapshot": self.catalog_row(), "pricing_skus": []}
        with patch.object(orv, "preflight", return_value=pf), \
             patch.object(orv, "submit", return_value=initial), \
             patch.object(orv, "wait_for_terminal", return_value=terminal):
            result = orv.run_job(job, live=True, api_key="key")
        self.assertTrue(result["cost_cap_exceeded_after_run"])

    def test_external_polling_url_is_rejected(self) -> None:
        with self.assertRaises(orv.OpenRouterError):
            orv._safe_openrouter_url("https://evil.example/video/job-1")


if __name__ == "__main__":
    unittest.main()
