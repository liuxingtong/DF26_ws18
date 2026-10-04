# 07 · AI 渲染:从体块到影像(Power → Image）

把 05 算出的「权力 → 形态」体块,变成 **AI 渲染影像 + 过渡动画**。不用 ComfyUI、不用 ControlNet 节点图——
走现在最简单清楚的路:**1 张体块参考图 + 文字提示词 → 图**(Replicate 上的 nano-banana / Flux-Kontext 这类模型)。

> 07 **依赖 05**:数据、引擎、权力体制都从隔壁 `05_Shanghai Power to Form Students/` 读,不重复一份。

---

## 诚实分层(07 的方法论核心)

一张渲染图被显式拆成两层——这正是整个工作坊「形态由权力计算、外观由论述补充」的缩影:

| 层 | 是什么 | 谁定 | 性质 |
|---|---|---|---|
| **结构** | 05 的体块参考图(footprint/高度/天际线) | pipeline 计算 | **诚实、可追溯** |
| **表面** | 文字提示词的材质/氛围 | 学生改 `config.yaml` | **论点 / illustrative,非数据** |

提示词本身也分两层:**[计算层]**(从 05 真实算出的栋数/最高高/形态指纹)+ **[论述层]**(你主张这种权力长什么样)。
护栏:提示词明令模型**严格保住参考图体块**,不许加减楼——把 AI 的自由限制在"外观",守住诚实性。

## 学习路线(3 本 notebook,简体主 + 繁体变体)

| # | notebook | 学什么 |
|---|---|---|
| 01 | `01_提示词生成器` | 从权力体制自动出提示词,看 [计算层]/[论述层] 拆分;改 `config.yaml` = 改论述 |
| 02 | `02_体块到影像` | 体块参考图(固定机位)+ 提示词 → Replicate 渲染(无 token 自动 dry-run) |
| 03 | `03_过渡动画` | 三种过渡:算子强度连续扫(最诚实·离线)/ 渲染图溶解 / AI 图生视频补间 |

## 互动画布 canvas.html(★ 找角度 · 导出 ControlNet 条件图)

```bash
python run.py canvas            # 出 3 站的 out/<slug>/canvas.html
python run.py canvas caoyang    # 单站
```
自含单档、浏览器打开即用(Three.js 内联)。体块可叠加仓库内的 **OSM 道路快照**或真实卫星影像:
- 打浦桥页面采用一条连续流程：选择三种治理情景 → 选择三类角色视角 → 阅读当前情景独立计算的 Pareto 取舍 → 查看三维与导出。正式搜索包含合规增建、临街地面释放、大体量拆分和敏感对象退台四个强形态动作，以及公共空间重构和居民院落通行改善两个低强度动作；三个情景分别读取自己的算子权限和优化结果，三类角色再按离散优先级对同一解集排序，形成 3×3 阅读组合。
- **拖拽 orbit 找角度** → 「保存当前角度」存进列表,点一下回到那个角度。
- 切换**情景或角色视角**时，形态、指标、Pareto 图和选中方案同步变化；图中每个点均可打开对应三维方案。
- **5 种导出模式**(作 AI 参考图 / ControlNet 条件图):

  | 模式 | 画面 | 用途 |
  |---|---|---|
  | 体块 massing | 素模 + 真实卫星地面 | nano-banana「1 参考图 + 文字」 |
  | 深度 depth | 灰阶(近白远黑)黑底 | ControlNet **depth** |
  | 法线 normal | 表面法线彩色 白底 | ControlNet **normal** |
  | 分色 seg | 按权利方著色 白底 | ControlNet **segmentation** |
  | 边缘 canny | 白色硬边 黑底 | ControlNet **canny / lineart** |

- **导出**:当前视图 / 当前角度全部 5 模式 / 所有保存角度 × 全部模式。PNG 命名 `<slug>_<体制>_<模式>.png`。
- 条件图(depth/normal/seg/canny)**不含卫星底、干净可直接喂 ControlNet**;massing 含真实卫星地面。

## 跑法

```bash
# 装依赖(07 + 05 都要)
pip install -r engine/requirements.txt
pip install -r "../05_Shanghai Power to Form Students/engine/requirements.txt"

# 离线就能跑的部分(提示词 + 体块参考图 + 算子动画,不需 token):
jupyter lab          # 打开 01/02/03 逐格跑;02 真渲染前会自动 dry-run

# 真渲染 / 真补间(需联网 + token):
export REPLICATE_API_TOKEN=你的token    # 见下方「token」一节
```

单独跑引擎(命令行自测):
```bash
python3 engine/prompt_gen.py lujiazui     # 出各权力的提示词(两层拆分)
python3 engine/massing.py    lujiazui     # 出各权力的体块参考图 → out/<slug>/
python3 engine/render.py     lujiazui     # dry-run:打印将发给 Replicate 的 payload
python3 engine/animate.py    lujiazui slim # 算子强度扫描动画(gif)
```

## REPLICATE_API_TOKEN(凭证,别进 git）

- token 是**凭证**:绝不写进代码 / notebook / git。只在自己 shell 里设环境变量:
  ```bash
  export REPLICATE_API_TOKEN=r8_xxx...
  ```
- 代码一律从 `os.environ` 读;没设时所有渲染自动 **dry-run**(只打印 payload,不联网、不花钱)。
- 费用:每张图约 $0.01–0.05。课堂可每人自带 token,或共用一个(注意额度/滥用)。

## 文件结构

```
07_AI Render Students/
├─ config.yaml   ★ 唯一要改的设定:站点 / 模型 / 机位 + 提示词论述层(站点·模型·体制·look 全在这)
├─ run.py        ★ 唯一要跑的入口:python run.py [canvas|report|bridge|notebooks|<slug>]
├─ README.md
├─ out/<slug>/                    产出:massing_*.jpg · render_*.png · *.gif · canvas.html · report.html
├─ web/                           three.min.js / OrbitControls.js(canvas.html 内联用)
└─ engine/  (代码,不用进)
   ├─ settings.py    读取器:把 config.yaml 读成 settings.SLUG/MODEL/CAM/...
   ├─ build_canvas.py 出互动画布 canvas.html
   ├─ build_report.py 出聚合报告 report.html + 05→06 桥接页
   ├─ ws05.py        桥:把 05 的数据/引擎/算子接进来
   ├─ prompt_gen.py  ★ 提示词生成器(计算层 + 论述层;论述层读 config.yaml)
   ├─ massing.py     固定机位体块参考图(= AI 的结构底)
   ├─ render.py      Replicate 调用(token 从 env;dry-run 可离线)
   ├─ animate.py     过渡动画(算子扫描 / 溶解 / 图生视频接口)
   ├─ _build_notebooks.py  生成 01/02/03 学生 notebook(python run.py notebooks)
   └─ requirements.txt
```

## 模型选择

- **`google/nano-banana`**(默认)— Gemini Flash Image,"保结构改外观"目前最稳。
- **`black-forest-labs/flux-kontext`** — 图+文编辑、保构图,备选。
- 换模型:改 `config.yaml` 的 `model`;若新模型入参不同,在 `engine/render.py` 的 `MODEL_ADAPTERS` 加一条适配。
- 图生视频(03-C):`kwaivgi/kling-*` / `wan-video/wan-2.2-i2v` / runway / luma 等(首帧→末帧补间)。

## 诚实边界

- 渲染图是 **illustrative**:体块忠实(参考图约束 + negative 护栏),但外观是 AI 按论述层**想象**的——不是这座城真实的样子。
- 模型偶尔仍会偷改天际线;出图要**肉眼核对体块**有没有被篡改。
- 动画里 **(A) 算子强度扫描最诚实**(每帧是真算子输出);**(B) 溶解 / (C) AI 补间**是观感润色,中间态是混合/想象,标 illustrative。
- 固定机位贯穿:相机不动,画面里动的只有形态 = 纯权力信号。
- 07 不含本地神经网生成;AI 渲染在 Replicate 云端,属"把已算好的形态做外观可视化",**不反推、不臆造权力归属**。
