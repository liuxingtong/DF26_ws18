import sys
import unittest
from pathlib import Path

from shapely.geometry import box

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "engine"))

from engine.plots import operator_atlas  # noqa: E402


def rec(x0, y0, x1, y1, h=10.0, sh="developer", tags=None, frozen=False):
    return {
        "geom": box(x0, y0, x1, y1),
        "h": h,
        "sh": sh,
        "tags": sorted(tags or []),
        "frozen": frozen,
    }


class OperatorAtlasDiffTests(unittest.TestCase):
    def test_change_summary_detects_tag_only_changes(self):
        before = [
            rec(0, 0, 10, 10, tags=["tourism_frontage"]),
            rec(20, 0, 30, 10, tags=["micro_shop"]),
        ]
        after = [
            rec(0, 0, 10, 10, tags=["shared_frontage"]),
            rec(20, 0, 30, 10, tags=["micro_shop"]),
        ]

        summary = operator_atlas.change_summary(before, after)

        self.assertEqual(summary["changed_count"], 1)
        self.assertEqual(summary["tag_count"], 1)
        self.assertEqual(summary["stakeholder_count"], 0)
        self.assertEqual(summary["height_count"], 0)
        self.assertEqual(summary["geometry_count"], 0)

    def test_change_summary_detects_geometry_and_height_changes(self):
        before = [
            rec(0, 0, 10, 10, h=10.0, tags=["tourism_frontage"]),
            rec(20, 0, 30, 10, h=12.0, tags=["tourism_frontage"]),
        ]
        after = [
            rec(0, 0, 8, 8, h=18.0, tags=["tourism_frontage", "relief_node"]),
            rec(20, 0, 30, 10, h=12.0, tags=["tourism_frontage"]),
        ]

        summary = operator_atlas.change_summary(before, after)

        self.assertEqual(summary["changed_count"], 1)
        self.assertEqual(summary["geometry_count"], 1)
        self.assertEqual(summary["height_count"], 1)
        self.assertEqual(summary["tag_count"], 1)

    def test_tag_category_prioritizes_visual_signal_tags(self):
        self.assertEqual(
            operator_atlas.tag_category(rec(0, 0, 1, 1, tags=["tourism_frontage", "micro_shop"])),
            "tourism_frontage",
        )
        self.assertEqual(
            operator_atlas.tag_category(rec(0, 0, 1, 1, tags=["shared_frontage", "micro_shop"])),
            "shared_frontage",
        )
        self.assertEqual(
            operator_atlas.tag_category(rec(0, 0, 1, 1, tags=["relief_node", "tourism_frontage"])),
            "relief_node",
        )


if __name__ == "__main__":
    unittest.main()
