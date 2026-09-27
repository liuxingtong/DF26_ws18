# 打浦桥正式研究输入

本目录中的以下三个文件是论文实验的规范输入（canonical research inputs）：

- `intervention_zones.geojson`
- `planning_controls.csv`
- `heritage_buildings.geojson`

这里的“正式”表示已冻结、可复现并由默认优化流程读取，不表示法定控规、地籍边界或法律意义上的保护范围。

## 适用口径

### 更新单元

`intervention_zones.geojson` 包含 38 个由 OSM 道路缓冲切分得到的道路围合研究单元。几何有效且 ID 唯一，但未经过地籍测绘或逐边人工 GIS 修订。32 栋无法稳定匹配到单元的建筑继续作为不可编辑背景，不强行分配到最近单元。

### 规划控制

`planning_controls.csv` 与 38 个更新单元一一对应。限高、FAR 和覆盖率采用现状形态下限与论文共同默认值形成的冻结实验基线，全部保留 `constraint_status=research_assumption`，不得表述为法定建设权或法定控规指标。

### 遗产建筑

`heritage_buildings.geojson` 不再使用旧的 73 栋田子坊范围代理。它由黄浦区第二批文物保护点的 12 条建筑级预标注生成，共对应 21 个本地建筑轮廓。恒昌里、康益里、海会寺旧址和安顺里四条范围未确认记录仍保留在 `review_app/public/data/review_cases.json`，但不进入优化约束。

## 复现与审核

运行：

```bash
python scripts/promote_dapuqiao_formal_inputs.py
```

质量检查、数量、限制条件和 SHA-256 校验值保存在 `formal_input_quality.json`。任何来源、边界或控制参数更新都应重新运行脚本，并形成新的冻结版本。
