import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "engine"))

from engine import editorial_data_film  # noqa: E402


class EditorialDataFilmPayloadTests(unittest.TestCase):
    def test_build_payload_contains_story_beats_and_metric_signatures(self):
        payload = editorial_data_film.build_payload("dapuqiao")

        self.assertEqual(payload["meta"]["slug"], "dapuqiao")
        self.assertEqual(payload["meta"]["durationMs"], 10000)
        self.assertEqual(len(payload["beats"]), 4)
        self.assertEqual(len(payload["scenarios"]), 4)
        self.assertIn("tourism_capture", payload["scenarioMetrics"])
        self.assertIn("negotiated_24h_alley", payload["scenarioMetrics"])
        self.assertIn("baseline", payload["collections"])
        self.assertIn("touristSpine", payload["collections"])

    def test_build_payload_exposes_editorial_metrics_used_in_film(self):
        payload = editorial_data_film.build_payload("dapuqiao")
        tourism = payload["scenarioMetrics"]["tourism_capture"]
        negotiated = payload["scenarioMetrics"]["negotiated_24h_alley"]

        self.assertGreater(tourism["buildingCount"], 0)
        self.assertGreater(tourism["avgHeight"], 0)
        self.assertGreaterEqual(tourism["slenderness"], 0)
        self.assertGreaterEqual(negotiated["reliefNodes"], 1)
        self.assertGreaterEqual(negotiated["oneWayAlleys"], 1)
        self.assertGreaterEqual(negotiated["quietBuildings"], 1)

    def test_build_payload_contains_editorial_overlay_groups(self):
        payload = editorial_data_film.build_payload("dapuqiao")

        self.assertIn("baselineNumbers", payload["overlayGroups"])
        self.assertIn("pressureBand", payload["overlayGroups"])
        self.assertIn("heritageParticles", payload["overlayGroups"])
        self.assertIn("dayNightBand", payload["overlayGroups"])

    def test_build_writes_editorial_film_html(self):
        path = editorial_data_film.build("dapuqiao")

        self.assertTrue(path.exists())
        self.assertEqual(path.name, "editorial_data_film.html")
        text = path.read_text(encoding="utf-8")
        self.assertIn("One district, four redistributions of urban life.", text)
        self.assertIn("window.__codexRenderAt", text)

    def test_frame_output_dir_and_video_path_are_deterministic(self):
        frames_dir = editorial_data_film.frame_output_dir("dapuqiao", duration_s=10, fps=24)
        video_path = editorial_data_film.video_output_path("dapuqiao", duration_s=10)

        self.assertEqual(frames_dir.name, "editorial_data_film_frames_10s_24fps")
        self.assertEqual(video_path.name, "editorial_data_film_10s.mp4")


if __name__ == "__main__":
    unittest.main()
