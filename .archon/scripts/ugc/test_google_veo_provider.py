#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import os
import unittest
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[3]
CLIENT_PATH = REPO_ROOT / "ugc-studio" / "providers" / "google-veo" / "client.py"
spec = importlib.util.spec_from_file_location("google_veo_provider", CLIENT_PATH)
gv = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(gv)


class GoogleVeoProviderTests(unittest.TestCase):
    def job(self, model: str = "veo-3.1-lite-generate-preview") -> dict:
        return {
            "version": "1.0",
            "provider": "google-veo",
            "model": model,
            "request": {
                "instances": [{"prompt": "Natural handheld UGC reaction."}],
                "parameters": {
                    "aspectRatio": "9:16",
                    "durationSeconds": "4",
                    "resolution": "720p",
                    "numberOfVideos": 1,
                },
            },
            "rights_approved": True,
            "approved_for_spend": False,
            "max_provider_cost_usd": 0.30,
        }

    def test_dry_run_estimates_without_key_or_network(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            with patch.object(gv, "submit") as submit:
                result = gv.run_job(self.job())
        self.assertEqual(result["mode"], "dry-run")
        self.assertEqual(result["estimate"]["usd"], 0.20)
        submit.assert_not_called()

    def test_lite_720_pricing(self) -> None:
        estimate = gv.estimate_cost(self.job())
        self.assertEqual(estimate["rate_usd_per_second"], 0.05)
        self.assertEqual(estimate["usd"], 0.20)

    def test_fast_1080_requires_eight_seconds(self) -> None:
        job = self.job("veo-3.1-fast-generate-preview")
        job["request"]["parameters"]["resolution"] = "1080p"
        with self.assertRaisesRegex(gv.GoogleVeoError, "requires durationSeconds=8"):
            gv.estimate_cost(job)

    def test_lite_rejects_reference_images(self) -> None:
        job = self.job()
        job["request"]["instances"][0]["referenceImages"] = [
            {"image": {"inlineData": {"mimeType": "image/png", "data": "abc"}}, "referenceType": "asset"}
        ]
        job["request"]["parameters"]["durationSeconds"] = "8"
        with self.assertRaisesRegex(gv.GoogleVeoError, "does not support referenceImages"):
            gv.estimate_cost(job)

    def test_standard_reference_images_require_eight_seconds(self) -> None:
        job = self.job("veo-3.1-generate-preview")
        job["request"]["instances"][0]["referenceImages"] = [
            {"image": {"inlineData": {"mimeType": "image/png", "data": "abc"}}, "referenceType": "asset"}
        ]
        with self.assertRaisesRegex(gv.GoogleVeoError, "require durationSeconds=8"):
            gv.estimate_cost(job)

    def test_live_requires_spend_approval(self) -> None:
        with self.assertRaisesRegex(gv.GoogleVeoError, "approved_for_spend"):
            gv.run_job(self.job(), live=True, api_key="key")

    def test_estimate_over_cap_blocks_before_submit(self) -> None:
        job = self.job("veo-3.1-generate-preview")
        job["max_provider_cost_usd"] = 0.50
        with patch.object(gv, "submit") as submit:
            with self.assertRaisesRegex(gv.GoogleVeoError, "exceeds approved cap"):
                gv.run_job(job, live=True, api_key="key")
        submit.assert_not_called()

    def test_successful_live_run_derives_billable_cost(self) -> None:
        job = self.job()
        job["approved_for_spend"] = True
        initial = {"name": "operations/op-1", "done": False}
        terminal = {
            "name": "operations/op-1",
            "done": True,
            "response": {
                "generateVideoResponse": {
                    "generatedSamples": [
                        {"video": {"uri": "https://generativelanguage.googleapis.com/v1beta/files/video-1"}}
                    ]
                }
            },
        }
        with patch.object(gv, "submit", return_value=initial), \
             patch.object(gv, "wait_for_terminal", return_value=terminal):
            result = gv.run_job(job, live=True, api_key="key")
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["derived_billable_cost_usd"], 0.20)
        self.assertEqual(len(result["video_uris"]), 1)

    def test_failed_generation_records_zero_billable_cost(self) -> None:
        job = self.job()
        job["approved_for_spend"] = True
        initial = {"name": "operations/op-1", "done": False}
        terminal = {"name": "operations/op-1", "done": True, "error": {"code": 400, "message": "failed"}}
        with patch.object(gv, "submit", return_value=initial), \
             patch.object(gv, "wait_for_terminal", return_value=terminal):
            result = gv.run_job(job, live=True, api_key="key")
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["derived_billable_cost_usd"], 0.0)

    def test_external_download_host_is_rejected(self) -> None:
        with self.assertRaises(gv.GoogleVeoError):
            gv._safe_download_url("https://evil.example/video.mp4")


if __name__ == "__main__":
    unittest.main()
