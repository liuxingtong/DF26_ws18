import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "engine"))

from engine import intro_story  # noqa: E402


class IntroStoryPayloadTests(unittest.TestCase):
    def test_build_intro_payload_contains_core_sections(self):
        payload = intro_story.build_intro_payload("dapuqiao")

        self.assertEqual(payload["meta"]["slug"], "dapuqiao")
        self.assertEqual(payload["meta"]["title"], "Dapuqiao 24h Negotiated District")
        self.assertIn("current", payload["collections"])
        self.assertIn("touristSpine", payload["collections"])
        self.assertIn("reliefNodes", payload["collections"])
        self.assertIn("quietBuffer", payload["collections"])
        self.assertEqual(len(payload["scenarios"]), 4)
        self.assertGreater(payload["stats"]["buildingCount"], 100)

    def test_build_intro_payload_exports_operator_impacts(self):
        payload = intro_story.build_intro_payload("dapuqiao")
        metrics = payload["stats"]["operatorMetrics"]

        self.assertGreaterEqual(metrics["crowdValve"]["reliefNodes"], 1)
        self.assertGreaterEqual(metrics["crowdValve"]["oneWayAlleys"], 1)
        self.assertGreaterEqual(metrics["nightReversion"]["quietBuildings"], 1)
        self.assertGreaterEqual(len(payload["allOperators"]), 8)
        self.assertIn("freeze_tags", [item["key"] for item in payload["allOperators"]])
        self.assertIn("crowd_valve", [item["key"] for item in payload["allOperators"]])

    def test_build_intro_payload_contains_scenario_sequences_with_geometry(self):
        payload = intro_story.build_intro_payload("dapuqiao")
        sequences = payload["scenarioSequences"]

        self.assertIn("negotiated_24h_alley", sequences)
        negotiated = sequences["negotiated_24h_alley"]
        self.assertGreaterEqual(len(negotiated["steps"]), 5)
        self.assertEqual(negotiated["steps"][0]["op"], "freeze_tags")
        self.assertEqual(negotiated["steps"][-1]["op"], "night_reversion")
        self.assertGreater(len(negotiated["steps"][-1]["collection"]["features"]), 100)

    def test_build_intro_payload_uses_english_story_labels(self):
        payload = intro_story.build_intro_payload("dapuqiao")

        self.assertIn("Tourist", payload["scenarios"][0]["caption"])
        self.assertIn("Resident", payload["scenarios"][1]["caption"])

    def test_frame_output_dir_and_video_path_are_deterministic(self):
        frames_dir = intro_story.frame_output_dir("dapuqiao", duration_s=15, fps=24)
        video_path = intro_story.video_output_path("dapuqiao", duration_s=15)

        self.assertEqual(frames_dir.name, "intro_story_frames_15s_24fps")
        self.assertEqual(video_path.name, "intro_story_dark_15s.mp4")

    def test_capture_frame_indices_cover_full_15_seconds_at_24fps(self):
        indices = intro_story.capture_frame_indices(duration_s=15, fps=24)

        self.assertEqual(len(indices), 360)
        self.assertEqual(indices[0], 0)
        self.assertEqual(indices[-1], 359)


if __name__ == "__main__":
    unittest.main()
