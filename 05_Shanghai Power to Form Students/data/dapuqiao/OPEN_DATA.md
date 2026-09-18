# 打浦桥开放研究数据

本目录中的开放图层用于让不同机器能够复现打浦桥空间分析，同时避免公开上传授权不明确的百度、高德、天地图或商业数据包。

## 可直接使用的图层

- `study_boundary.geojson`：OpenStreetMap 中的打浦桥街道行政边界。
- `street_network.geojson`：研究边界内的 OSM 道路与步行路径。
- `public_services.geojson`：教育、医疗、社区服务、菜场及公共交通候选点。
- `public_space_candidates.geojson`：公园、花园、游乐场、广场等公共空间候选要素。
- `open_data_sources.yaml`：来源、许可证、生成时间、限制和质量摘要。
- `open_data_quality.json`：机器可读的数据质量检查结果。

## 重新生成

在仓库根目录运行：

```bash
python "05_Shanghai Power to Form Students/scripts/build_dapuqiao_open_data.py"
```

脚本会查询 OpenStreetMap/Nominatim/Overpass，因此重新生成时需要网络。OpenStreetMap 会持续更新，未来运行的要素数量可能变化。

## 许可证与引用

数据来源为 OpenStreetMap contributors，许可证为 ODbL 1.0：

- https://www.openstreetmap.org/copyright
- https://opendatacommons.org/licenses/odbl/1-0/

在论文、网页或地图中使用这些数据时，应注明 `© OpenStreetMap contributors`。

## 研究限制

这些文件不是正式地籍、控规、历史保护或公共空间权属资料。特别是：

- `public_space_candidates.geojson` 只表示 OSM 标签候选，不能证明空间为公有或实际可进入；
- 当前 OSM 快照只得到 2 个公共空间候选，不能用于断言研究区只有 2 处公共空间；
- `public_services.geojson` 可能存在漏标、过时或分类不一致；
- OSM 边界面积约为 1.5739 km²，比现有 `site.yaml` 记录的旧边界面积小约 0.86%，跨版本比较时应固定所用边界；
- 尚无经过核实的弄堂入口图层；
- 正式保护建筑、规划控制和更新单元仍需另行制作或取得授权数据。

`templates/` 中的文件只定义人工研究数据的字段结构，不包含虚构记录。
