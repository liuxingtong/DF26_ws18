# 打浦桥更新单元草案

本目录由 `scripts/build_dapuqiao_draft_zones.py` 生成。边界通过从打浦桥研究范围中扣除 OSM 道路缓冲带得到；小于5,000平方米的碎片会并入最近的大单元，以保持可审查的单元数量。它属于可复现的研究草案，不是地籍、控规或法定更新单元。

文件：

- `intervention_zones.draft.geojson`：道路围合空间草案。
- `planning_controls.draft.csv`：以现状形态和情景默认值生成的控制草案。
- `heritage_buildings.draft.geojson`：按田子坊官方管理范围建立的保守保护代理。
- `building_zone_assignment.draft.csv`：建筑到草案单元的匹配结果。
- `draft_summary.json`：方法、覆盖率和待办事项。
- `draft_preview.png`：草案单元、道路、建筑和未匹配建筑预览。

正式使用前必须：

1. 在 GIS 中检查并修改边界；
2. 处理未匹配建筑；
3. 将保护代理与上海市优秀历史建筑名录及控规图则逐栋交叉核对；
4. 逐行确认控制指标来源；
5. 审核完成后再复制为 `intervention_zones.geojson` 和 `planning_controls.csv`。

数据派生自 OpenStreetMap，遵循 ODbL 1.0，并应标注 `© OpenStreetMap contributors`。
