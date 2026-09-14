import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "engine"))

from engine import white_film_hybrid  # noqa: E402


class WhiteFilmHybridPayloadTests(unittest.TestCase):
    def test_build_payload_contains_real_scenarios_beats_and_plan_collections(self):
        payload = white_film_hybrid.build_payload("dapuqiao")

        self.assertEqual(payload["meta"]["slug"], "dapuqiao")
        self.assertEqual(payload["meta"]["durationMs"], 10000)
        self.assertEqual([beat["key"] for beat in payload["beats"]], ["site_intro", "data_shift", "operator_logic"])
        self.assertEqual(len(payload["scenarios"]), 4)
        self.assertIn("baseline", payload["collections"])
        self.assertIn("scenarioBuildings", payload["collections"])
        self.assertIn("touristSpine", payload["collections"])

    def test_build_payload_uses_real_project_metrics_for_cards_and_overlays(self):
        payload = white_film_hybrid.build_payload("dapuqiao")
        metrics = payload["scenarioMetrics"]
        overlays = payload["overlayGroups"]

        self.assertIn("tourism_capture", metrics)
        self.assertIn("negotiated_24h_alley", metrics)
        self.assertGreater(metrics["tourism_capture"]["buildingCount"], 0)
        self.assertGreater(metrics["tourism_capture"]["avgHeight"], 0)
        self.assertGreater(metrics["tourism_capture"]["maxHeight"], 0)
        self.assertGreaterEqual(metrics["tourism_capture"]["slenderness"], 0)
        self.assertGreaterEqual(metrics["negotiated_24h_alley"]["reliefNodes"], 1)
        self.assertGreaterEqual(metrics["negotiated_24h_alley"]["oneWayAlleys"], 1)
        self.assertGreaterEqual(metrics["negotiated_24h_alley"]["quietBuildings"], 1)
        self.assertIn("metricCards", overlays)
        self.assertIn("scenarioBars", overlays)
        self.assertIn("heritageDots", overlays)
        self.assertIn("protocolBand", overlays)

    def test_output_path_points_to_out_slug_directory(self):
        path = white_film_hybrid.output_path("dapuqiao")
        self.assertIn("out", str(path))
        self.assertEqual(path.parent.name, "dapuqiao")

    def test_html_output_path_and_build_are_deterministic(self):
        out_path = white_film_hybrid.output_path("dapuqiao")
        built = white_film_hybrid.build("dapuqiao")

        self.assertEqual(out_path.name, "white_film_hybrid.html")
        self.assertEqual(built, out_path)
        self.assertTrue(built.exists())
        text = built.read_text(encoding="utf-8")
        self.assertIn("White Film Hybrid", text)
        self.assertIn("window.__codexRenderAt", text)

    def test_build_writes_white_plan_page_without_progress_bar(self):
        path = white_film_hybrid.build("dapuqiao")
        text = path.read_text(encoding="utf-8")

        self.assertIn("One district, four redistributions of urban life.", text)
        self.assertIn("Scenario Metrics", text)
        self.assertIn("Operator Logic", text)
        self.assertIn("maplibre-gl.js", text)
        self.assertIn("floating", text)
        self.assertIn("Operator Diff", text)
        self.assertIn("Policy Heatmap", text)
        self.assertNotIn("timelineFill", text)
        self.assertNotIn("progressBar", text)
        self.assertNotIn("fill-extrusion", text)
        self.assertNotIn("left-panel", text)
        self.assertNotIn("right-panel", text)


if __name__ == "__main__":
    unittest.main()
