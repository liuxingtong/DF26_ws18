"""E1 消融臂定义的单元测试（不加载规范输入，不跑优化）。"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

WS05 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WS05 / "scripts"))

from run_dapuqiao_e1_ablation import (  # noqa: E402
    ARMS,
    CANONICAL_TARGETS,
    COMMON_INTENSITY,
    REFERENCE_ARM,
    UNION_OPERATORS,
    transform_scenario,
)
from summarize_dapuqiao_e1_ablation import effect, parse_arm  # noqa: E402


SCENARIO = {
    "id": "test_scenario",
    "defaults": {"height_limit_m": 30.0},
    "implementation": {"maximum_changed_zone_ratio": 0.30},
    "operator_policy": {
        "allowed_operators": ["densify", "open_ground"],
        "stakeholder_targets": {"densify": ["developer"], "open_ground": ["developer"]},
        "maximum_intensity": {"densify": 0.45, "open_ground": 0.75},
    },
}


def test_reference_arm_is_identity():
    arm = ARMS[REFERENCE_ARM]
    result = transform_scenario(SCENARIO, arm)
    assert result["scenario"] == SCENARIO
    assert result["diff"]["before"] == result["diff"]["after"]


def test_transform_does_not_mutate_input():
    transform_scenario(SCENARIO, ARMS["attr-off__ops-union__int-common"])
    assert SCENARIO["operator_policy"]["allowed_operators"] == ["densify", "open_ground"]
    assert SCENARIO["operator_policy"]["stakeholder_targets"] == {
        "densify": ["developer"], "open_ground": ["developer"],
    }


def test_attribution_off_clears_targets_only():
    policy = transform_scenario(SCENARIO, ARMS["attr-off__ops-own__int-own"])["scenario"][
        "operator_policy"
    ]
    assert policy["stakeholder_targets"] == {}
    assert policy["allowed_operators"] == ["densify", "open_ground"]
    assert policy["maximum_intensity"] == {"densify": 0.45, "open_ground": 0.75}


def test_operator_union_adds_canonical_targets_and_limits():
    policy = transform_scenario(SCENARIO, ARMS["attr-on__ops-union__int-own"])["scenario"][
        "operator_policy"
    ]
    assert set(policy["allowed_operators"]) == set(UNION_OPERATORS)
    for operator in UNION_OPERATORS:
        assert policy["stakeholder_targets"][operator] == CANONICAL_TARGETS[operator]
    # 情景原有的上限不被并集改写。
    assert policy["maximum_intensity"]["densify"] == 0.45
    assert policy["maximum_intensity"]["split_to_towers"] == COMMON_INTENSITY["split_to_towers"]


def test_common_intensity_covers_every_allowed_operator():
    policy = transform_scenario(SCENARIO, ARMS["attr-on__ops-union__int-common"])["scenario"][
        "operator_policy"
    ]
    assert policy["maximum_intensity"] == {
        operator: COMMON_INTENSITY[operator] for operator in UNION_OPERATORS
    }


def test_implementation_and_defaults_held_constant():
    result = transform_scenario(SCENARIO, ARMS["attr-off__ops-union__int-common"])["scenario"]
    assert result["implementation"] == SCENARIO["implementation"]
    assert result["defaults"] == SCENARIO["defaults"]


def test_all_arms_are_complete_factorial():
    assert len(ARMS) == 8
    for arm_id, arm in ARMS.items():
        assert parse_arm(arm_id) == {
            "attribution": 1 if arm["attribution"] == "on" else -1,
            "operator_set": 1 if arm["operator_set"] == "union" else -1,
            "intensity": 1 if arm["intensity"] == "common" else -1,
        }


def test_effect_recovers_known_main_effect():
    codes, values = [], []
    for arm_id in ARMS:
        code = parse_arm(arm_id)
        codes.append(code)
        values.append(3.0 * code["attribution"] + 0.5 * code["operator_set"])
    # 编码为 ±1 时，高水位与低水位相差 2 倍系数。
    assert effect(values, codes, ("attribution",)) == pytest.approx(6.0)
    assert effect(values, codes, ("operator_set",)) == pytest.approx(1.0)
    assert effect(values, codes, ("intensity",)) == pytest.approx(0.0)
    assert effect(values, codes, ("attribution", "operator_set")) == pytest.approx(0.0)
