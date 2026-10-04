import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "engine"))

from engine import build_canvas  # noqa: E402


class DapuqiaoCanvasModelTests(unittest.TestCase):
    def test_dapuqiao_canvas_uses_only_current_base_without_counterfactuals(self):
        regimes, include_counterfactuals = build_canvas._canvas_base_scope(
            "dapuqiao",
            ["current", "tourism_capture", "everyday_life_first"],
        )

        self.assertEqual(regimes, ("current",))
        self.assertFalse(include_counterfactuals)

    def test_experiment_selector_ignores_archived_scenario_and_keeps_current(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            old = root / "20260101_old"
            current = root / "20260102_current"
            for path, scenario in (
                (old, "tourism_capture"),
                (current, "public_coordination"),
            ):
                path.mkdir()
                (path / "search_summary.csv").write_text(
                    "backend\n", encoding="utf-8"
                )
                (path / "experiment_manifest.json").write_text(
                    json.dumps({"scenario": scenario}), encoding="utf-8"
                )

            selected = build_canvas._latest_compatible_experiment(
                root,
                {"public_coordination", "development_growth", "resident_heritage_priority"},
            )

        self.assertEqual(selected.name, "20260102_current")

    def test_single_run_provenance_defaults_to_preview(self):
        provenance = build_canvas._run_provenance({"seed": 11})

        self.assertEqual(provenance, {
            "seed": 11,
            "display_status": "preview_single_seed",
        })

    def test_latest_scenario_runs_can_come_from_a_newer_suite(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            optimization = root / "optimization"
            suites = root / "scenario_suites"
            old_run = optimization / "public_coordination__20260101_010101"
            suite_run = suites / "20260102_010101" / "public_coordination" / "seed_11"
            for path in (old_run, suite_run):
                path.mkdir(parents=True)
                (path / "selected_solutions.json").write_text("{}", encoding="utf-8")
                (path / "run_config.json").write_text(
                    json.dumps({"scenario_id": "public_coordination", "seed": 11}),
                    encoding="utf-8",
                )

            selected = build_canvas._latest_scenario_runs(
                optimization, suites, {"public_coordination"}
            )

        self.assertEqual(selected["public_coordination"].name, "seed_11")

    def test_dynamic_research_controls_use_event_listeners_not_inline_handlers(self):
        script = build_canvas.viewer_js({})

        self.assertIn("[data-scenario]", script)
        self.assertIn(
            'scenarioButtons.querySelectorAll("[data-scenario]").forEach(b=>b.onclick=',
            script,
        )
        self.assertIn(
            'roleViewButtons.querySelectorAll("[data-role-view]").forEach(b=>b.onclick=',
            script,
        )
        self.assertNotIn('onclick="selectScenario', script)
        self.assertNotIn('onclick="selectRole', script)

    def test_viewer_defaults_to_satellite_without_removed_display_modes(self):
        script = build_canvas.viewer_js({})

        self.assertIn('basemap=(GEOM.sat&&GEOM.satExtent)?"satellite":"osm"', script)
        self.assertIn('const MODES=["massing","depth","normal","segmentation"]', script)
        self.assertNotIn("baselineOverlay", script)
        self.assertNotIn('mode==="canny"', script)

    def test_solution_card_names_positive_increment_and_shows_net_gfa(self):
        script = build_canvas.viewer_js({})

        self.assertIn("Added floor area", script)
        self.assertIn("Net GFA change", script)


if __name__ == "__main__":
    unittest.main()
