import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CLIENT_PATH = ROOT / "ugc-studio" / "providers" / "google-omni" / "client.py"
spec = importlib.util.spec_from_file_location("ugc_google_omni_test", CLIENT_PATH)
mod = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(mod)


def base_job():
    return {
        "provider": "google-omni",
        "model": "gemini-omni-1.1-flash",
        "expected_duration_seconds": 5,
        "rights_approved": True,
        "approved_for_spend": False,
        "max_provider_cost_usd": 1.0,
        "request": {
            "model": "gemini-omni-1.1-flash",
            "input": [
                {"type": "image", "data": "YWJj", "mime_type": "image/jpeg"},
                {"type": "text", "text": "Single continuous creator shot, natural movement."},
            ],
            "response_format": {"type": "video", "delivery": "uri", "aspect_ratio": "9:16", "resolution": "720p"},
            "generation_config": {"video_config": {"task": "image_to_video"}},
        },
    }


class GoogleOmniTests(unittest.TestCase):
    def test_estimate_uses_documented_effective_720p_rate(self):
        quote = mod.estimate_cost(base_job())
        self.assertEqual(quote["usd"], 0.5)
        self.assertEqual(quote["cost_evidence_type"], "official_effective_output_rate_approximation")

    def test_dry_run_needs_no_key(self):
        result = mod.run_job(base_job())
        self.assertEqual(result["mode"], "dry-run")
        self.assertFalse(result["approved_for_spend"])

    def test_non_720p_rejected_in_v1_benchmark_adapter(self):
        job = base_job()
        job["request"]["response_format"]["resolution"] = "1080p"
        with self.assertRaises(mod.GoogleOmniError):
            mod.validate_job(job)

    def test_arbitrary_remote_uri_is_not_fetched(self):
        job = base_job()
        job["request"]["input"][0] = {"type": "image", "uri": "https://example.com/creator.jpg"}
        with self.assertRaises(mod.GoogleOmniError):
            mod.validate_job(job)

    def test_google_files_uri_allowed(self):
        job = base_job()
        job["request"]["input"][0] = {
            "type": "image",
            "uri": "https://generativelanguage.googleapis.com/v1beta/files/abc123",
        }
        validated = mod.validate_job(job)
        self.assertEqual(validated["task"], "image_to_video")

    def test_live_requires_explicit_spend_approval_before_network(self):
        job = base_job()
        with self.assertRaises(mod.GoogleOmniError) as ctx:
            mod.run_job(job, live=True, api_key="not-used")
        self.assertIn("approved_for_spend", str(ctx.exception))

    def test_cost_cap_blocks_before_network(self):
        job = base_job()
        job["max_provider_cost_usd"] = 0.49
        with self.assertRaises(mod.GoogleOmniError) as ctx:
            mod.run_job(job, live=True, api_key="not-used")
        self.assertIn("exceeds approved cap", str(ctx.exception))

    def test_video_content_parser_supports_rest_steps(self):
        payload = {
            "steps": [
                {"type": "model_output", "content": [{"type": "video", "mime_type": "video/mp4", "data": "YWJj"}]}
            ]
        }
        found = mod._video_contents(payload)
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["data"], "YWJj")


if __name__ == "__main__":
    unittest.main()
