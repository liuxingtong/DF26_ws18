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

## 论文主对照：传统参数基线 vs. 三治理情景

```bash
python scripts/preflight_dapuqiao_formal_experiment.py

python scripts/compare_dapuqiao_methods.py \
  --seeds 11,23,37,53,71 \
  --population 20 \
  --generations 20 \
  --jobs 5
```

预检会先生成独立的 `preflight_manifest.json`，核对 1 处已确认公共公园背景（丽园公园）、1 处未核实并排除候选（白玉兰广场）、两者均不进入目标函数，以及 4 条未决历史记录与 32 栋未匹配分区建筑的独立计数。它还冻结本次输入与代码 SHA-256、Git 状态和运行时版本。默认正式矩阵是 20 次运行、8,000 个有效独立评价；只有 `ready=true` 才应启动正式命令。

该命令为每个方法/种子保留恰好 `population × generations` 个独立、非空候选评价，并输出逐运行候选表、Pareto 表、约束记录、追溯文件、三张对照图、逐种子指标、均值/标准差、双向支配覆盖率、预算公平性审计，以及按随机种子配对的 Wilcoxon 检验和秩双列效应量。五种子的检验效力有限，必须同时报告原始种子值、效应方向、coverage 与收敛轨迹。

`--jobs` 只按随机种子分配独立进程；每个种子内部仍顺序运行参数基线和三个治理情景。汇总表最终按种子和方法固定排序，因此并行完成顺序不会改变统计或文件结构。

传统基线只使用两个逐更新单元的常规几何参数：高度倍率 `1.00–1.30` 与足迹保留率 `0.75–1.00`。它不读取 `stakeholder_proxy`、由主体派生的 `editable` 或三情景 `operator_policy`；保护代理仍作为共同硬约束。四组实验共同使用同一建筑/更新单元、共同规划控制、三目标定义、有效评价预算和随机种子；三个目标共同使用 5 m 街道缓冲。三情景的主体对象、允许算子、强度与最大改动范围属于被检验的治理逻辑，不属于共同法规控制。

当前三个情景为 `public_coordination`、`development_growth` 和 `resident_heritage_priority`。配置同时披露各项研究参数的 `uncertainty_ranges`；单次运行使用范围内参考值，正式稳健性结论必须来自后续范围采样，不能把参考值解释为法规阈值。冻结提交 `04d8073` 的旧四情景移入 `archived_scenarios`，旧 ID 仅保留用于读取和审计当时的情景形态设定，不再进入当前套件和三维平台。若要精确复现旧角色权重与旧导出结构，必须使用冻结提交 `04d8073`；当前代码不会把新离散优先级伪装成旧模型复现。

当前正式形态语法由四个强形态动作和两个低强度改善动作组成：`densify` 合规增建，`open_ground` 释放临街地面，`split_to_towers` 拆分大体量，`heritage_step_down` 把高度移离敏感对象；`public_space_reconfiguration` 从公共主体非遗产资产的最近道路一侧形成浅退界，`courtyard_access_improvement` 从居民住宅临街方向切出受面积保留上限约束的窄通行缺口，后二者均不增高，只解释为候选干预而非施工设计。遗产本体与未知主体的冻结是前置硬规则。

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

## 固定测量、三层前沿与离散角色优先级

三个情景共同读取 `objectives.yaml`：道路连接一律使用 5 m 缓冲；居住影响采用离散暴露判定——直接修改的住宅，以及与增高、拆分或退台建筑位于同一道路围合更新单元的住宅均计入，不设置距离权重。内部兼容字段 `development_capacity` 对外统一称为“正向增建量”，按逐建筑正 GFA 增量求和；净 GFA 变化同时报告，不能用正向增建量代替街区总量变化。单栋变化低于 1 m² GFA、1 m²足迹且 0.1 m 高度时视为数值噪声。

每次运行同时输出：

- `pareto_full.csv`：形态去重后的完整精确非支配前沿；
- `pareto_solutions.csv`：按已确认 ε（居住影响暴露 0.001、正向增建量 0.0005 FAR、释放地面 0.00005）去除不可辨识差异后的前沿；
- `representative_solutions.csv`：保留三目标极值、接近理想点与最大间距解的正文展示子集；
- `pareto_distribution.csv`：按前沿层记录三目标的样本数、唯一值数、零值占比、分位数、均值和标准差；
- `epsilon_sensitivity.csv`：0.5×、1×、2× ε 下的解集与质量指标；
- `role_rankings.csv`：按离散优先级和 epsilon 同档规则得到的角色逐级排名；
- `role_priority_sensitivity.csv`：相邻优先级交换后，角色首选方案是否改变；
- `convergence.csv`：有效独立评价预算上的 hypervolume、spacing 与前沿规模。

候选先经过算子级预防性截断、容量缩放、足迹子集操作或单元内高度重分配；随后统一约束检查仍发现的 blocking 违规，均按 `reject_candidate` 淘汰。每条违规在导出中同时保留规则代码、严重度和处置动作。

角色后评价不再计算加权总分。居民按“居住影响暴露 → 临街释放 → 正向增建量”、开发主体按“正向增建量 → 临街释放 → 居住影响暴露”、公共规划按“临街释放 → 居住影响暴露 → 正向增建量”逐级排序；差异小于 `objectives.yaml` epsilon 的方案在该目标上视为同档。跨角色折中解最小化三方中的最差名次，并以总名次作为次级判据。

正向增建量的固定归一化上限在 2026-09-28 根据新增算子后三情景预览由 0.01 校准为 0.03，高于已观测最大值 0.02377。该上限只服务于 hypervolume、spacing、近似去重和折中距离；原始目标、约束和精确支配仍保留原值。超过 0.03 的结果必须触发复核。

按当前冻结数据，三项 ε 分别约对应 2,169 m² 现状住宅 GFA、787 m² 正 GFA 增量和 79 m² 临街释放地面。换数据后必须从新基数重新换算并在 manifest 中披露，不能直接沿用这些平方米数。

三情景五种子运行：

```bash
python scripts/run_dapuqiao_scenario_suite.py \
  --population 20 --generations 15 --seeds 11,23,37,53,71
```
