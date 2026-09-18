# 人工研究数据模板

这些模板不包含正式规划数据，也不应直接改名后作为研究输入。

1. 在 GIS 中依据道路围合、功能和历史风貌边界绘制更新单元，将结果保存为 `intervention_zones.geojson`。
2. 为每个 `zone_id` 填写 `planning_controls.csv`。
3. `constraint_status` 应明确填写 `official`、`research_assumption` 或 `unknown`。
4. 每条控制记录都应填写 `source`；研究假设需在论文方法部分单独说明。
