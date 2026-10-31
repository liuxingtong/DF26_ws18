# 居住暴露修复及权限匹配零模型 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. 本次计划由当前会话直接执行，不自动创建子代理。

**Goal:** 在统一的实际形态暴露指标下重算与重跑四组正式实验，并补齐权限匹配零模型及论文图表。

**Architecture:** 共同暴露函数负责按真实几何判定影响；回放工具读取冻结精确决策；零模型通过独立权限掩码改变可操作建筑。所有输出具有指标版本和输入/代码哈希，与旧实验隔离。

**Tech Stack:** Python、GeoPandas、Shapely、NumPy、pymoo NSGA-II、unittest/pytest、Matplotlib、SSH 远端批处理。

**Spec:** `docs/superpowers/specs/2026-10-31-exposure-and-permission-null.md`

## Global Constraints

- 旧结果不覆盖，当前用户对 canvas.html 的改动不纳入本次代码提交。
- 暴露规则采用 spec 的实际增高/实际拆分定义，不能只把 open_ground 加入原算子名单。
- 主实验 4×10=40 次；零模型 3×10×3=90 次；每次固定 2,000 次原始评价、40 个体、50 代。
- 标签、住宅识别及分母不因零模型随机化而变化；每算子每单元栋数一致，总 GFA 误差≤5%。
- 回放缺完整精度决策时显式记录缺失；原 Pareto 子集重排不冒充新搜索。
- 先验证，再正式批处理；远端使用后台任务、日志、进程/完成状态文件，不依赖前台 SSH 持续连接。

## Review Focus

- 同样形态经不同算子实现：暴露必须一致，任务 1 测试覆盖。
- 零强度、纯缩占地、原本多连通轮廓、空 zone：任务 1 测试覆盖。
- 冻结快照与当前代码不一致、决策精度损失：任务 2 用重建核对和缺失清单拦截。
- 小单元无抽样自由度、面积无法匹配：任务 4 输出失败或固定部分，不静默放宽。
- 主实验与零模型指标版本、权限执行环节不一致：任务 4–5 验证清单与输入不变断言拦截。

## 文件职责

- 修改 `05_Shanghai Power to Form Students/engine/optimization/objectives.py`：实际形态暴露判定。
- 修改 `05_Shanghai Power to Form Students/optimization/objectives.yaml`：新版本及定义。
- 新增 `05_Shanghai Power to Form Students/tests/test_actual_geometry_exposure.py`：指标一致性边界测试。
- 新增 `05_Shanghai Power to Form Students/scripts/replay_dapuqiao_exposure.py`：冻结方案精确回放、新旧指标及重排输出。
- 新增 `05_Shanghai Power to Form Students/engine/optimization/permission_null.py`：匹配权限表生成和校验。
- 修改 `05_Shanghai Power to Form Students/engine/optimization/operators.py`：权限掩码统一入口。
- 新增 `05_Shanghai Power to Form Students/tests/test_permission_null.py`：抽样、匹配与执行一致性。
- 新增 `05_Shanghai Power to Form Students/scripts/run_dapuqiao_permission_null.py`：随机权限表×seed 批处理。
- 修改 `05_Shanghai Power to Form Students/scripts/run_dapuqiao_optimization.py`：导出全部候选的完整精度决策。
- 复用现有 `compare_dapuqiao_methods.py`、`analyze_dapuqiao_matching.py`、`analyze_dapuqiao_baseline_dominance.py`，增加版本校验及正式新批次入口。
- 新增 `research/paper_draft_cn/figures/make_permission_null_figure.py`：共同参考点下图 5。

## Task 1 新指标

**接口：** `actual_exposure_ids(baseline, candidate, numerical_resolution) -> (changed_ids, impact_ids)`；ID 为字符串集合。`evaluate_objectives` 使用该结果，不读取 operator 名称决定暴露。

- [ ] 新建测试：同一补偿增高分别标记 open_ground/densify/parameter，暴露相等；同单元住宅必须被计入。
- [ ] 增加边界测试：高度增加恰达 0.1 m、低于阈值、纯缩占地、强度为零但标签为 densify、体量拆分产生≥1 m² 新分量、原 MultiPolygon 未增加分量、空 zone、住宅直接改动、住宅只计一次。
- [ ] 运行测试，确认旧实现因算子名称判定而失败。
- [ ] 实现真实高度/足迹/连通分量比较，版本记为 actual_geometry_v2，更新 YAML 定义。
- [ ] 运行 `../.venv/bin/python -m pytest tests/test_actual_geometry_exposure.py tests/test_optimization_framework.py -q`，全部通过；旧测试如表达了旧规则，逐项记录语义变化。
- [ ] 独立提交指标及测试。

## Task 2 原方案重新评价

**接口：** `replay_dapuqiao_exposure.py --source-runs PATH --output PATH`，输出 replay_detail.csv、replay_missing.csv、provenance.json 及可精确重建候选。

- [ ] 测试精确 provenance 回放可恢复相同建筑 ID、高度、占地和旧目标；仅有四位小数 signature 时进入缺失清单。
- [ ] 先用归档 PC seed97 三份首选测试，几何核对通过后才计算新暴露。
- [ ] 在每个 seed 的完整存档中回放具有完整决策的方案，保留原 ID，分别输出 old/new/delta、增高和拆分证据。
- [ ] 核对冻结输入哈希和旧目标复现误差；将失败项列出，不混入汇总。
- [ ] 保存指标变化对照，不修改旧 CSV。

## Task 3 旧候选重新筛选

**接口：** 在 task2 的可精确回放候选集上运行现有 Pareto、角色选择、E6 与 BL 支配函数；输出标注 `replayed_archive_subset`。

- [ ] 测试指标变化后原支配关系和角色首选可以变化，原 solution_id 保持不变。
- [ ] 对每个 seed 重筛选、重排；合并新 BL 存档前沿后重算支配比例。
- [ ] 输出新旧 Pareto ID、角色首选 ID、匹配候选数、E6 和未支配比例变化。
- [ ] 明确记录每组可回放候选覆盖率，禁止称为“修复后搜索前沿”。

## Task 4 匹配权限表与单次运行入口

**接口：** `generate_permission_table(study, operator_specs, seed, max_attempts=10000) -> (operator_to_ids, diagnostics)`；`validate_permission_table(...)` 检查各单元栋数、算子总 GFA 误差及冻结对象。随机表通过 scenario 的独立 permission_overrides 字段传递。

- [ ] 测试每算子每单元栋数精确一致、面积误差≤5%、冻结对象不入池、原 stakeholder/residential_proxy/住宅分母不变、同种子可复现、无自由度能报告。
- [ ] 实现按单元无放回抽样和有限面积验收，保存原表/随机表 ID、随机种子、GFA 误差及实际变化数量。
- [ ] 在 `_eligible_for_operator` 统一应用独立权限掩码，使可用性、影响栋数估计和实际执行共用入口；禁止用替换标签实现零模型。
- [ ] 测试未经授权建筑在三个环节都被排除，授权建筑仍受共同几何约束和情景强度限制。
- [ ] 实现批处理 CLI，`--dry-run` 只生成并校验所有表、不启动搜索。
- [ ] 运行 `../.venv/bin/python -m pytest tests/test_permission_null.py tests/test_actual_geometry_exposure.py tests/test_optimization_framework.py -q`；失败时不启动实验。

## Task 5 新搜索与零模型正式批次

**接口：** 现有 E0 runner 加新配置快照和完整精度候选决策导出；新 null runner 使用同一版本 evaluator、质量指标与预算。

- [ ] 增加完整精度决策 JSONL 导出，并测试随机抽取候选可从导出重建相同三目标与几何。
- [ ] 冻结配置：复制原正式 E0 幅度、强度和共同约束，只改变暴露及必要记录功能；记录指标版本、commit、代码哈希和种子。
- [ ] 本地先各跑 1 seed 的小预算 smoke，核对 f2/f3、可行性、完整决策导出和角色选择。
- [ ] 远端单次 smoke 后测量实际耗时和内存，据此设并行数，后台启动 E0 40 次运行；保存 PID、逐 run 日志、成功/失败清单和完成标记。
- [ ] E0 同版本稳定后启动零模型 90 次运行；表生成失败必须显式计入失败清单。
- [ ] 核对主实验 40/40、零模型 90/90、每次原始预算2,000、各自完整决策和约束记录；计算逐代曲线，不把预算完成当作收敛证明。

## Task 6 图表与论文平台同步

- [ ] 统一归一化与参考点，零模型与真实情景不得分别缩放 HV。
- [ ] 在正式修正 E0 上重算匹配净增建、暴露上限比较、BL 合并前沿支配和角色首选表。
- [ ] 生成图 5：真实值叠加随机表分布，统计层级和共同 3 seed 配对关系写入图注。
- [ ] 重选接近中位数 HV 的 seed，从完整决策生成图 6，并核对逐栋变化。
- [ ] 论文、平台和输出报告只从新批次目录读取；旧图和旧暴露数值保留归档，不与新图混用。
- [ ] 检查所有论文数字都有 CSV 来源、匹配样本数和版本；图输出300dpi PNG及PDF/SVG并逐张检查。

## 当前状态

- [x] 正式 40 份冻结代码已核实存在漏计；已复现1,504个原Pareto暴露值。
- [x] PC seed97原角色方案可精确重建；原指标归档图6已生成。
- [x] 本轮完成设计与执行计划，未修改目标函数或启动新实验。
- [ ] 审阅 actual_geometry_v2 的增高/拆分阈值和新旧结果边界后，按任务顺序实施。
