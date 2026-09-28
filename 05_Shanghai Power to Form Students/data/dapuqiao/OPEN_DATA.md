# 打浦桥开放研究数据

本目录中的开放图层用于让不同机器能够复现打浦桥空间分析，同时避免公开上传授权不明确的百度、高德、天地图或商业数据包。

## 可直接使用的图层

- `study_boundary.geojson`：OpenStreetMap 中的打浦桥街道行政边界。
- `street_network.geojson`：研究边界内的 OSM 道路与步行路径。
- `public_services.geojson`：教育、医疗、社区服务、菜场及公共交通候选点。
- `public_space_candidates.geojson`：公共空间背景候选及逐项核查状态；不参与优化目标计算。
- `public_space_verification.json`：高德、OSM 与政府资料交叉核查形成的逐项冻结决定。
- `alley_entrances.geojson`：田子坊入口研究点；当前仅 1 处研究级核实、1 处候选冻结，不是穷尽清单。
- `alley_entrance_verification.json`：入口证据、适用范围和冻结决定。
- `online_gap_freeze.json`：网上补证后仍无法可靠补齐的数据缺口登记。
- `SOURCE_ARCHIVE.json`：跨 2026-09-18、09-27、09-28 三轮更新的总来源档案与文件 SHA-256。
- `open_data_sources.yaml`：来源、许可证、生成时间、限制和质量摘要。
- `open_data_quality.json`：机器可读的数据质量检查结果。

## 重新生成

在仓库根目录运行：

```bash
python "05_Shanghai Power to Form Students/scripts/build_dapuqiao_open_data.py"
```

脚本会查询 OpenStreetMap/Nominatim/Overpass，因此重新生成时需要网络。OpenStreetMap 会持续更新，未来运行的要素数量可能变化。

来源档案可用 `python scripts/audit_dapuqiao_source_archive.py` 核对；它同时检查总档案、遗产审核清单和正式输入清单的哈希。

## 许可证与引用

数据来源为 OpenStreetMap contributors，许可证为 ODbL 1.0：

- https://www.openstreetmap.org/copyright
- https://opendatacommons.org/licenses/odbl/1-0/

在论文、网页或地图中使用这些数据时，应注明 `© OpenStreetMap contributors`。

## 研究限制

这些文件不是正式地籍、控规、历史保护或公共空间权属资料。特别是：

- 当前 OSM 快照只得到 2 个公共空间候选，不能用于断言研究区只有 2 处公共空间；
- 丽园公园已由高德 POI、黄浦区统计年鉴和上海市公园管理资料交叉确认其公共公园身份；现保存 OSM 研究多边形及 2021 年官方公布的 `05:00–21:00` 历史时段，但它们不能替代当前实测/法定边界和 2026 年开放时段；
- 白玉兰广场仍只有 OSM `place=square` 标签，高德附近检索未获得对应同名公共空间，继续冻结并排除；
- 两个要素均不进入目标函数；第三目标仅表示与街道网络相连的释放地面潜力，不等于公共空间面积、可达性或权属效益；
- `public_services.geojson` 可能存在漏标、过时或分类不一致；
- OSM 边界面积约为 1.5739 km²，比现有 `site.yaml` 记录的旧边界面积小约 0.86%，跨版本比较时应固定所用边界；
- 田子坊 1 号门由官方文字与 OSM 点位交叉核实，2 号门仍是 OSM 候选；入口图层非穷尽、坐标未经测绘，且不提供开放时段或通行能力；
- 4 条未决遗产记录虽已复核官方地址，但可靠建筑级范围仍缺失；法规也没有可直接套用的统一遗产退界距离，二者继续冻结；
- 正式保护建筑、规划控制和更新单元已冻结为论文实验规范输入，但不构成法定规划、地籍或法律保护边界。

`templates/` 中的文件只定义人工研究数据的字段结构，不包含虚构记录。
