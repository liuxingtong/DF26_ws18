# 打浦桥数据审核器

本地地图审核器只展示无法由官方名录、高德地理编码和现有建筑轮廓自动确定的记录。高德 Key 不会写入浏览器、源代码或生成结果。

## 更新审核数据

```bash
export AMAP_WEB_SERVICE_KEY="你的 Web 服务 API Key"
python scripts/build_review_data.py
unset AMAP_WEB_SERVICE_KEY
```

脚本完成以下工作：

1. 读取黄浦区第二批文物保护点名单中的 16 个打浦桥记录；
2. 通过高德 Web 服务 API 地理编码地址；
3. 将 GCJ-02 坐标转换为 WGS84，仅用于与本地建筑轮廓匹配；
4. 计算附近候选建筑、匹配距离、主体代理与现有遗产代理状态；
5. 输出不包含密钥的静态审核数据。

## 启动

```bash
pnpm install
pnpm dev
```

审核结果保存在浏览器本地存储中，也可通过“保存审核”导出为 `dapuqiao_review_annotations.json`。原始数据不会被直接覆盖。

## 冻结口径（2026-09-27）

- 官方记录共 16 条，全部保留在资料库中；
- 12 条已完成建筑级预标注，`include_in_optimization=true`；
- 恒昌里、康益里、海会寺旧址、安顺里共 4 条因历史范围或现状建筑对应关系不明确，设置为 `spatial_status=unresolved`、`include_in_optimization=false`；
- 未确认记录仍保留坐标、候选建筑、联网证据与排除原因，不用“最近建筑”代替历史建筑范围；
- 高德 API Key 只在生成时从环境变量读取，不进入代码、静态数据或冻结清单。

冻结版本、文件校验值及复现说明见 `DATA_FREEZE.md`。

## 同步正式实验结果

实验结果页使用冻结提交 `04d8073` 的正式高预算对照实验。重新生成实验页数据与图表：

```bash
python scripts/sync_experiment_results.py
pnpm build
```

同步脚本会先检查 5 种方法、5 个随机种子、25 个方法—种子组合、统一的 400 次有效评价预算、25 条公平性记录和 3 张正式图表，再写入 `public/data/experiment_results.json`。启动应用后点击顶部“实验结果”，或直接打开 `#results`，即可查看总体指标、逐种子结果、正式图表与来源信息。
