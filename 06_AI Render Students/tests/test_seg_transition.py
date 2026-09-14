import sys
import unittest
from pathlib import Path

from shapely.geometry import box

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "engine"))

from engine import seg_transition  # noqa: E402


class SegTransitionTimelineTests(unittest.TestCase):
    def test_build_transition_plan_spans_all_regime_pairs_without_wraparound(self):
        plan = seg_transition.build_transition_plan(
            ["tourism_capture", "everyday_life_first", "heritage_micro_economy", "negotiated_24h_alley"],
            total_frames=10,
        )

        self.assertEqual(len(plan), 10)
        self.assertEqual(plan[0]["from_regime"], "tourism_capture")
        self.assertEqual(plan[0]["to_regime"], "everyday_life_first")
        self.assertEqual(plan[-1]["from_regime"], "heritage_micro_economy")
        self.assertEqual(plan[-1]["to_regime"], "negotiated_24h_alley")
        self.assertAlmostEqual(plan[0]["alpha"], 0.0)
        self.assertAlmostEqual(plan[-1]["alpha"], 1.0)

    def test_build_transition_plan_handles_single_frame_tail_cleanly(self):
        plan = seg_transition.build_transition_plan(
            ["a", "b", "c", "d"],
            total_frames=7,
        )

        self.assertEqual([item["pair_index"] for item in plan], [0, 0, 0, 1, 1, 2, 2])
        self.assertEqual(plan[2]["to_regime"], "b")
        self.assertEqual(plan[4]["to_regime"], "c")
        self.assertAlmostEqual(plan[-1]["alpha"], 1.0)


class SegTransitionPathTests(unittest.TestCase):
    def test_frame_output_dir_includes_slug_duration_and_fps(self):
        out_dir = seg_transition.frame_output_dir(
            root=Path("F:/tmp/out"),
            slug="dapuqiao",
            duration_s=10,
            fps=24,
        )

        self.assertEqual(out_dir, Path("F:/tmp/out/dapuqiao/seg_transition_10s_24fps"))


def rec(x0, y0, x1, y1, h, sh):
    return {
        "geom": box(x0, y0, x1, y1),
        "h": float(h),
        "sh": sh,
        "area": float((x1 - x0) * (y1 - y0)),
        "frozen": False,
    }


class NumericSceneInterpolationTests(unittest.TestCase):
    def test_pair_records_uses_geometry_union(self):
        pair = seg_transition.pair_records_by_geometry(
            [rec(0, 0, 1, 1, 10, "state"), rec(2, 0, 3, 1, 8, "resident")],
            [rec(0, 0, 1, 1, 20, "developer"), rec(4, 0, 5, 1, 6, "resident")],
        )

        self.assertEqual(len(pair), 3)
        self.assertEqual(sum(1 for item in pair if item["from_rec"] and item["to_rec"]), 1)
        self.assertEqual(sum(1 for item in pair if item["from_rec"] and not item["to_rec"]), 1)
        self.assertEqual(sum(1 for item in pair if item["to_rec"] and not item["from_rec"]), 1)

    def test_interpolate_scene_records_blends_height_and_color_roles(self):
        scene = seg_transition.interpolate_scene_records(
            [rec(0, 0, 1, 1, 10, "state")],
            [rec(0, 0, 1, 1, 30, "developer")],
            0.25,
        )

        self.assertEqual(len(scene), 1)
        self.assertAlmostEqual(scene[0]["h"], 15.0)
        self.assertEqual(scene[0]["sh"], "mix:state:developer")
        self.assertEqual(scene[0]["sh_from"], "state")
        self.assertEqual(scene[0]["sh_to"], "developer")
        self.assertAlmostEqual(scene[0]["mix"], 0.25)

    def test_interpolate_scene_records_grows_new_geometry_from_zero_height(self):
        scene = seg_transition.interpolate_scene_records(
            [],
            [rec(0, 0, 1, 1, 12, "resident")],
            0.5,
        )

        self.assertEqual(len(scene), 1)
        self.assertAlmostEqual(scene[0]["h"], 6.0)
        self.assertEqual(scene[0]["sh"], "resident")


if __name__ == "__main__":
    unittest.main()
