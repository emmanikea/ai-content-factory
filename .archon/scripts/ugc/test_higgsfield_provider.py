#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, os, unittest
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[3]
CLIENT_PATH = REPO_ROOT / "ugc-studio" / "providers" / "higgsfield" / "client.py"
spec = importlib.util.spec_from_file_location("higgsfield_provider", CLIENT_PATH)
hf = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(hf)

class HiggsfieldProviderTests(unittest.TestCase):
    def job(self):
        return {
            "version": "1.0",
            "provider": "higgsfield",
            "endpoint": "veo3.1/image-to-video",
            "input": {
                "prompt": "small natural smile",
                "image_url": "https://example.com/a.jpg"
            },
            "rights_approved": True,
            "approved_for_spend": False,
            "max_provider_cost_usd": 1.25,
        }

    def test_dry_run_never_requires_credentials(self):
        with patch.dict(os.environ, {}, clear=True):
            result = hf.run_job(self.job())
        self.assertEqual(result["mode"], "dry-run")
        self.assertNotIn("estimate", result)

    def test_live_requires_explicit_spend_approval_after_estimate(self):
        with patch.object(hf, "estimate", return_value={"credits": "2", "usd": "0.50"}):
            with self.assertRaisesRegex(hf.HiggsfieldError, "approved_for_spend"):
                hf.run_job(self.job(), live=True, credentials="id:secret")

    def test_estimate_only_does_not_submit(self):
        with patch.object(hf, "estimate", return_value={"credits": "2", "usd": "0.50"}) as est:
            with patch.object(hf, "submit") as submit:
                result = hf.run_job(self.job(), estimate_only=True, credentials="id:secret")
        self.assertEqual(result["estimate"]["usd"], "0.50")
        est.assert_called_once()
        submit.assert_not_called()

    def test_live_blocks_estimate_above_cost_cap(self):
        job = self.job()
        job["approved_for_spend"] = True
        with patch.object(hf, "estimate", return_value={"credits": "9", "usd": "2.00"}):
            with patch.object(hf, "submit") as submit:
                with self.assertRaisesRegex(hf.HiggsfieldError, "exceeds job cap"):
                    hf.run_job(job, live=True, credentials="id:secret")
        submit.assert_not_called()

    def test_live_submit_uses_estimate_and_preserves_request(self):
        job = self.job()
        job["approved_for_spend"] = True
        initial = {
            "status": "queued",
            "request_id": "abc",
            "status_url": "https://api.higgsfield.ai/requests/abc/status",
            "cancel_url": "https://api.higgsfield.ai/requests/abc/cancel",
        }
        terminal = {
            "status": "completed",
            "request_id": "abc",
            "video": {"url": "https://cdn.example.com/v.mp4"},
        }
        with patch.object(hf, "estimate", return_value={"credits": "2", "usd": "0.50"}), \
             patch.object(hf, "submit", return_value=initial), \
             patch.object(hf, "wait_for_terminal", return_value=terminal):
            result = hf.run_job(job, live=True, credentials="id:secret")
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["request_id"], "abc")
        self.assertEqual(result["media_urls"], ["https://cdn.example.com/v.mp4"])

    def test_endpoint_rejects_full_urls(self):
        with self.assertRaises(hf.HiggsfieldError):
            hf._endpoint("https://api.higgsfield.ai/veo3.1/image-to-video")

    def test_media_urls_deduplicates_nested_artifacts(self):
        result = {
            "video": {"url": "https://cdn.example.com/a.mp4"},
            "payload": {
                "video": {"url": "https://cdn.example.com/a.mp4"},
                "images": [{"url": "https://cdn.example.com/b.jpg"}],
            },
        }
        self.assertEqual(
            hf.media_urls(result),
            ["https://cdn.example.com/a.mp4", "https://cdn.example.com/b.jpg"],
        )

if __name__ == "__main__":
    unittest.main()
