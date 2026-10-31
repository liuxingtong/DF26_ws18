"""体量调整幅度实验臂的读取与应用。

幅度不是散落在若干 YAML 里的常数，而是一个可命名的实验臂：
`v1` 复现 2026-10-04 的正式对照，`expanded` 满足 2026-10-14 会议"加大体量调整幅度"的要求。
实验臂只覆盖算子参数与参数基线的倍率，不改变约束、目标、单元、标签或种子。
"""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml


CONFIG_ROOT = Path(__file__).resolve().parents[2] / "optimization"
ARMS_PATH = CONFIG_ROOT / "amplitude_arms.yaml"


def load_arms(path: Path | None = None) -> dict[str, Any]:
    payload = yaml.safe_load((path or ARMS_PATH).read_text(encoding="utf-8")) or {}
    arms = payload.get("arms", {})
    if not arms:
        raise ValueError(f"{path or ARMS_PATH} 未定义任何幅度实验臂")
    return {"meta": payload.get("meta", {}), "arms": arms}


def resolve_arm(name: str | None = None, path: Path | None = None) -> tuple[str, dict[str, Any]]:
    payload = load_arms(path)
    aliases = {
        str(key).lower(): str(value)
        for key, value in (payload["meta"].get("aliases") or {}).items()
    }
    arm_id = name or payload["meta"].get("default") or next(iter(payload["arms"]))
    arm_id = aliases.get(str(arm_id).lower(), arm_id)
    if arm_id not in payload["arms"]:
        known = ", ".join(sorted(payload["arms"]))
        raise KeyError(f"未知幅度实验臂：{arm_id}（可选：{known}）")
    return arm_id, deepcopy(payload["arms"][arm_id])


def apply_operator_arm(
    operator_specs: dict[str, Any], arm: dict[str, Any] | None
) -> dict[str, Any]:
    """把实验臂的算子参数并入 operator_specs，返回新对象，不修改入参。"""
    specs = deepcopy(operator_specs)
    for operator, overrides in ((arm or {}).get("operator_parameters") or {}).items():
        if operator not in specs:
            raise KeyError(f"幅度实验臂引用了未登记的算子：{operator}")
        parameters = specs[operator].setdefault("parameters", {})
        parameters.update(deepcopy(overrides))
    return specs


def apply_baseline_arm(
    baseline_config: dict[str, Any], arm: dict[str, Any] | None
) -> dict[str, Any]:
    """把实验臂的倍率并入参数基线配置，返回新对象，不修改入参。"""
    config = deepcopy(baseline_config)
    parameters = config.setdefault("baseline", {}).setdefault("parameters", {})
    for name, overrides in ((arm or {}).get("parameter_baseline_parameters") or {}).items():
        entry = parameters.setdefault(name, {})
        entry.update(deepcopy(overrides))
    return config


def arm_metadata(arm_id: str, arm: dict[str, Any] | None) -> dict[str, Any]:
    """写入 run_config / experiment_manifest，便于事后核对用了哪一档幅度。"""
    arm = arm or {}
    return {
        "amplitude_arm": arm_id,
        "label": arm.get("label"),
        "source": arm.get("source"),
        "operator_parameters": deepcopy(arm.get("operator_parameters") or {}),
        "parameter_baseline_parameters": deepcopy(
            arm.get("parameter_baseline_parameters") or {}
        ),
    }
