# BL 支配分析口径修正

本目录 baseline_dominance.csv 的分母为全部可行候选，属于历史诊断输出，不能用作 brief 要求的 Pareto 解未支配比例。对应 43.97%、26.81%、62.37% 已从当前正文撤下。

正式修正结果另存 ../baseline_dominance_pareto/，由 scripts/analyze_dapuqiao_baseline_dominance.py 从每组每种子 pareto_solutions.csv 计算。每种子分母保持为导出的 Pareto 解数；BL 合并前沿重新按标准支配关系筛选，容差 1e-12，所有注释输出均为独立副本。
