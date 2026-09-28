# 打浦桥单轮多目标优化框架

本目录保存优化配置。运行逻辑位于 `engine/optimization/`，入口为：

```bash
python scripts/run_dapuqiao_optimization.py audit
python scripts/run_dapuqiao_optimization.py run --backend nsga2 --seed 42 --population 80 --generations 100
```

`audit` 可立即运行。默认流程读取 `data/dapuqiao/` 下已冻结的规范研究输入；它们可用于论文实验，但不能解释为法定规划、地籍或法律保护范围。仅在调试缺失输入的草稿管线时显式使用 `--research-demo`。`--backend random` 保留为搜索对照基线。

遗产硬约束来自 `review_app/public/data/` 下的冻结审核快照。快照更新后，用下面的命令校验 SHA-256 清单并重新物化优化图层：

```bash
python scripts/materialize_dapuqiao_heritage_freeze.py
```

该命令只导出明确标记为 `include_in_optimization=true` 的记录；范围未决的官方记录继续留在证据库中，不以最近建筑替代。

## 论文主对照：传统参数基线 vs. 四治理情景

```bash
python scripts/preflight_dapuqiao_formal_experiment.py

python scripts/compare_dapuqiao_methods.py \
  --seeds 11,23,37,53,71 \
  --population 20 \
  --generations 20 \
  --jobs 5
```

预检会先生成独立的 `preflight_manifest.json`，核对 1 处已确认公共公园背景（丽园公园）、1 处未核实并排除候选（白玉兰广场）、两者均不进入目标函数，以及 4 条未决历史记录与 32 栋未匹配分区建筑的独立计数。它还冻结本次输入与代码 SHA-256、Git 状态和运行时版本。默认正式矩阵是 25 次运行、10,000 个有效独立评价；只有 `ready=true` 才应启动正式命令。

该命令为每个方法/种子保留恰好 `population × generations` 个独立、非空候选评价，并输出逐运行候选表、Pareto 表、约束记录、追溯文件、三张对照图、逐种子指标、均值/标准差、双向支配覆盖率、预算公平性审计，以及按随机种子配对的 Wilcoxon 检验和秩双列效应量。五种子的检验效力有限，必须同时报告原始种子值、效应方向、coverage 与收敛轨迹。

`--jobs` 只按随机种子分配独立进程；每个种子内部仍顺序运行参数基线和四个治理情景。汇总表最终按种子和方法固定排序，因此并行完成顺序不会改变统计或文件结构。

传统基线只使用两个逐更新单元的常规几何参数：高度倍率 `1.00–1.30` 与足迹保留率 `0.75–1.00`。它不读取 `stakeholder_proxy`、由主体派生的 `editable` 或四情景 `operator_policy`；保护代理仍作为共同硬约束。五组实验共同使用同一建筑/更新单元、36 m 限高、FAR 3.0、覆盖率 0.60、住宅 GFA 保留率 0.80、三目标定义、有效评价预算和随机种子；三个目标共同使用 5 m 街道缓冲。四情景的主体对象、允许算子、强度与最大改动范围属于被检验的治理逻辑，不属于共同法规控制。

第三目标严格定义为 `street-connected released-ground potential`：只计算建筑足迹缩减后与 5 m 道路缓冲相交的释放地面比例。丽园公园、白玉兰广场及非穷尽的田子坊入口点仅作为背景证据保存，均不进入目标或约束；该目标不是公共空间面积、入口可达性、权属或通行能力指标。

输入限制分开记录：4 条范围未决的历史记录保留在证据库中但不进入遗产硬约束；另有 32 栋建筑因未匹配更新单元而冻结为不可编辑背景，两者不是同一类缺失。

快速管线检查可使用较小预算并加 `--skip-geometries`；正式论文运行不要省略几何输出：

```bash
python scripts/compare_dapuqiao_methods.py \
  --seeds 11 --population 4 --generations 2 --skip-geometries
```

算子校准：

```bash
python scripts/calibrate_dapuqiao_operators.py
```

算法附录：同一有效独立评价预算下比较 NSGA-II 与随机搜索：

```bash
python scripts/compare_dapuqiao_search.py --seeds 11,23,37 --population 20 --generations 10
```

工作流是单向的：

```text
固定情景 → 生成候选 → 约束检查 → 三目标评价 → 帕累托筛选 → 角色后评价 → 导出
```

角色评价不会修改本轮优化目标或触发下一轮。

## 固定测量与三层前沿

四个情景共同读取 `objectives.yaml`：道路连接一律使用 5 m 缓冲；开发容量按每栋建筑的正 GFA 增量求和，净 GFA 变化只作为描述指标。单栋变化低于 1 m² GFA、1 m²足迹且 0.1 m 高度时视为数值噪声。

每次运行同时输出：

- `pareto_full.csv`：形态去重后的完整精确非支配前沿；
- `pareto_solutions.csv`：按已确认 ε（居住扰动 0.001、容量 0.0005 FAR、释放地面 0.00005）去除不可辨识差异后的前沿；
- `representative_solutions.csv`：保留三目标极值、接近理想点与最大间距解的正文展示子集；
- `pareto_distribution.csv`：按前沿层记录三目标的样本数、唯一值数、零值占比、分位数、均值和标准差；
- `epsilon_sensitivity.csv`：0.5×、1×、2× ε 下的解集与质量指标；
- `role_sensitivity.csv`：角色权重及居住扰动阈值的单因素敏感性；
- `convergence.csv`：有效独立评价预算上的 hypervolume、spacing 与前沿规模。

候选先经过算子级预防性截断、容量缩放或足迹子集操作；随后统一约束检查仍发现的 blocking 违规，均按 `reject_candidate` 淘汰。每条违规在导出中同时保留规则代码、严重度和处置动作。

角色评分使用 `objectives.yaml` 中跨情景固定的归一化边界，不再对每个情景自己的最小值和最大值重新缩放。

按当前冻结数据，三项 ε 分别约对应 2,169 m² 现状住宅 GFA、787 m² 正 GFA 增量和 79 m² 临街释放地面。换数据后必须从新基数重新换算并在 manifest 中披露，不能直接沿用这些平方米数。

四情景五种子运行：

```bash
python scripts/run_dapuqiao_scenario_suite.py \
  --population 20 --generations 15 --seeds 11,23,37,53,71
```
