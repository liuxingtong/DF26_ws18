# 打浦桥三维平台：本地重新计算

从仓库根目录运行：

```bash
.venv/bin/python '06_AI Render Students/run.py' serve-canvas dapuqiao
```

打开 `http://127.0.0.1:8765/`。在“Optimization settings and priorities”中，三个情景的建议值会显示在各滑条下方。选好情景并修改数值后，点击“Recompute with these settings”。服务会按当前情景、五项设置和种子 11 运行一次 NSGA-II（400 次有效独立评价），保存逐栋方案，并重新生成画布。单次计算可能需要数分钟；页面完成后自动刷新。

新运行保存在 `05_Shanghai Power to Form Students/out/dapuqiao/optimization/<scenario>__interactive_<time>/`，其中 `interactive_settings.json` 记录本次设置。它是单种子交互实验；论文中冻结的四方法、五种子正式对比仍使用原来的数据快照。若要用新设置重做论文对比，需要把同一设置应用于完整实验矩阵，再重新统计。

直接打开 `canvas.html` 文件可以浏览已有方案；重新计算按钮需要上述本地服务。
