#!/usr/bin/env python3
"""Validate and sync a frozen Dapuqiao experiment into the review app."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from datetime import datetime
from pathlib import Path

import pandas as pd


APP_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = APP_ROOT.parent
DEFAULT_SOURCE = (
    PROJECT_ROOT
    / "out"
    / "dapuqiao"
    / "method_comparison"
    / "formal_high_budget_04d8073"
)
DEFAULT_OUTPUT = APP_ROOT / "public" / "data"

TABLES = (
    "aggregate_summary.csv",
    "run_summary.csv",
    "paired_statistical_tests.csv",
    "baseline_scenario_coverage.csv",
    "pareto_distribution.csv",
    "fairness_audit.csv",
)
FIGURES = (
    "pareto_fronts.png",
    "quality_metrics.png",
    "dominance_coverage.png",
)
EXPECTED_METHODS = (
    "conventional_parameter_baseline",
    "tourism_capture",
    "everyday_life_first",
    "heritage_micro_economy",
    "negotiated_24h_alley",
)
METHOD_LABELS = {
    "conventional_parameter_baseline": "传统参数基线",
    "tourism_capture": "旅游流量资本主导",
    "everyday_life_first": "日常生活优先",
    "heritage_micro_economy": "遗产微经济",
    "negotiated_24h_alley": "24 小时协商弄堂",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def records(path: Path) -> list[dict]:
    frame = pd.read_csv(path)
    return json.loads(frame.to_json(orient="records", force_ascii=False))


def validate(source: Path, manifest: dict, tables: dict[str, list[dict]]) -> dict:
    methods = tuple(manifest.get("methods", []))
    seeds = tuple(manifest.get("seeds", []))
    run_summary = tables["run_summary.csv"]
    fairness = tables["fairness_audit.csv"]
    pairs = {(row["seed"], row["method_id"]) for row in run_summary}
    expected_pairs = {(seed, method) for seed in seeds for method in methods}
    checks = {
        "five_expected_methods": methods == EXPECTED_METHODS,
        "five_unique_seeds": len(seeds) == 5 and len(set(seeds)) == 5,
        "all_25_method_seed_pairs": len(run_summary) == 25 and pairs == expected_pairs,
        "equal_400_evaluation_budget": {
            row["effective_evaluation_budget"] for row in run_summary
        } == {400},
        "fairness_audit_complete": len(fairness) == 25
        and all(
            row["effective_budget_match"] and row["candidate_count_match"]
            for row in fairness
        ),
        "frozen_commit_recorded": str(
            manifest.get("reproducibility", {}).get("git", {}).get("commit", "")
        ).startswith("04d8073"),
        "all_required_figures_exist": all((source / name).is_file() for name in FIGURES),
    }
    if not all(checks.values()):
        failed = [name for name, passed in checks.items() if not passed]
        raise RuntimeError(f"Experiment validation failed: {', '.join(failed)}")
    return checks


def main() -> int:
    args = parse_args()
    source = args.source.resolve()
    output = args.output.resolve()
    if not source.is_dir():
        raise FileNotFoundError(source)
    output.mkdir(parents=True, exist_ok=True)

    manifest_path = source / "experiment_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    table_rows = {name: records(source / name) for name in TABLES}
    checks = validate(source, manifest, table_rows)

    aggregate = table_rows["aggregate_summary.csv"]
    primary_tests = [
        row
        for row in table_rows["paired_statistical_tests.csv"]
        if row["metric"] == "hypervolume"
    ]
    try:
        source_label = str(source.relative_to(PROJECT_ROOT))
    except ValueError:
        source_label = str(source)
    payload = {
        "schema_version": 1,
        "synced_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "source": {
            "label": "Dapuqiao formal high-budget comparison",
            "relative_directory": source_label,
            "git_commit": manifest["reproducibility"]["git"]["commit"],
            "manifest_sha256": sha256(manifest_path),
            "input_mode": manifest.get("input_mode"),
        },
        "model_status": {
            "frozen_experiment_status": "archived_pre_revision",
            "current_model": "three_scenario_ordinal",
            "current_scenarios": [
                {"id": "public_coordination", "label": "公共协调"},
                {"id": "development_growth", "label": "开发增长"},
                {"id": "resident_heritage_priority", "label": "居民生活与遗产优先"},
            ],
            "role_selection": "epsilon_tiered_lexicographic",
            "role_selection_label": "离散优先级 + epsilon 同档判定",
            "note": (
                "本页保留的 04d8073 高预算结果仅用于复现修订前的五方法实验；"
                "当前模型已改为三情景和离散角色优先级，不将历史数字重新解释为新模型结果。"
            ),
        },
        "plan": {
            "methods": list(manifest["methods"]),
            "method_labels": METHOD_LABELS,
            "seeds": manifest["seeds"],
            "population": manifest["population"],
            "requested_generations": manifest["requested_generations"],
            "effective_evaluation_budget": manifest[
                "effective_independent_evaluation_budget"
            ],
            "parallel_execution": manifest["parallel_execution"],
        },
        "validation": {
            "checks": checks,
            "completed_runs": len(table_rows["run_summary.csv"]),
            "fairness_passes": sum(
                row["effective_budget_match"] and row["candidate_count_match"]
                for row in table_rows["fairness_audit.csv"]
            ),
        },
        "summary": {
            "aggregate": aggregate,
            "primary_hypervolume_tests": primary_tests,
            "interpretation": [
                "传统参数基线在共同三目标空间中的平均超体积最高。",
                "四种治理情景通过主体权限、情景许可与改动范围约束缩小可行解域。",
                "五个配对种子的超体积差异方向一致，但样本量仅为五，Holm 校正后未达到统计显著。",
                "日常生活优先与遗产微经济情景的最低居住扰动为结构性零值，来自住宅冻结规则，不能解释为优化器自动发现。",
            ],
        },
        "tables": {
            name.removesuffix(".csv"): rows for name, rows in table_rows.items()
        },
        "figures": [
            {
                "id": Path(name).stem,
                "label": {
                    "pareto_fronts.png": "五种方法的 Pareto 前沿",
                    "quality_metrics.png": "搜索质量与可行性",
                    "dominance_coverage.png": "基线与治理情景支配覆盖",
                }[name],
                "file": f"experiment_{name}",
                "source_sha256": sha256(source / name),
            }
            for name in FIGURES
        ],
        "caveats": [
            "本页 04d8073 数据属于修订前历史实验；三情景新模型需要重新正式运行后才能替换。",
            "全部输入是冻结的论文研究模型输入，不是法定控规或地籍数据。",
            "五个随机种子的配对检验统计功效有限，应同时报告原始值、效应方向和校正后的 p 值。",
            "街道连接的释放地面潜力不是已建成公共空间面积，也不表示产权或实际开放性。",
            "四种治理情景的参数是透明研究假设，不代表真实利益相关者已经达成共识。",
        ],
    }

    target = output / "experiment_results.json"
    target.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    for name in FIGURES:
        shutil.copy2(source / name, output / f"experiment_{name}")

    print(
        json.dumps(
            {
                "output": str(target),
                "completed_runs": payload["validation"]["completed_runs"],
                "fairness_passes": payload["validation"]["fairness_passes"],
                "figures": len(payload["figures"]),
                "git_commit": payload["source"]["git_commit"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
