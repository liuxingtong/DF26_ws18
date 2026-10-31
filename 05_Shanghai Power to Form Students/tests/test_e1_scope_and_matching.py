"""E1 scope 档位与 E6 匹配筛选的单元测试（不加载规范输入，不跑优化）。"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

WS05 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WS05 / "scripts"))

from run_dapuqiao_e1_scope import SCOPE_LEVELS, apply_scope  # noqa: E402
from analyze_dapuqiao_matching import match_capacity, match_disruption  # noqa: E402


SCENARIO = {
    "id": "test",
    "implementation": {
        "maximum_changed_zone_ratio": 0.30,
        "maximum_changed_building_ratio": 0.18,
        "note": "keep-me",
    },
    "operator_policy": {"allowed_operators": ["densify"]},
}


def test_scope_levels_are_ordered_and_owned():
    assert SCOPE_LEVELS["tight"][0] < SCOPE_LEVELS["mid"][0] < SCOPE_LEVELS["loose"][0]
    assert SCOPE_LEVELS["tight"][1] < SCOPE_LEVELS["mid"][1] < SCOPE_LEVELS["loose"][1]


def test_apply_scope_only_touches_the_two_ratios():
    result = apply_scope(SCENARIO, "loose")["scenario"]
    assert result["implementation"]["maximum_changed_zone_ratio"] == 0.45
    assert result["implementation"]["maximum_changed_building_ratio"] == 0.30
    assert result["implementation"]["note"] == "keep-me"
    assert result["operator_policy"] == SCENARIO["operator_policy"]


def test_apply_scope_does_not_mutate_input_and_records_diff():
    diff = apply_scope(SCENARIO, "tight")["diff"]
    assert SCENARIO["implementation"]["maximum_changed_zone_ratio"] == 0.30
    assert diff["before"]["maximum_changed_zone_ratio"] == 0.30
    assert diff["after"]["maximum_changed_zone_ratio"] == 0.22


def test_match_capacity_is_inclusive_and_bounded():
    rows = [
        {"capacity": 0.0015, "disruption": 0.1},
        {"capacity": 0.0020, "disruption": 0.2},
        {"capacity": 0.0025, "disruption": 0.3},
        {"capacity": 0.0026, "disruption": 0.4},
    ]
    matched = match_capacity(rows, 0.002, 0.0005)
    assert [row["capacity"] for row in matched] == [0.0015, 0.0020, 0.0025]


def test_match_disruption_ceiling_is_inclusive():
    rows = [{"disruption": 0.0}, {"disruption": 0.05}, {"disruption": 0.06}]
    assert [row["disruption"] for row in match_disruption(rows, 0.05, 0.0)] == [0.0, 0.05]
