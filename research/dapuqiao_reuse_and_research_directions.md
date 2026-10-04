# 打浦桥：更新后代码复用与研究深化核查

核查日期：2026-09-14。代码版本：13b2693（feat(dapuqiao): add narrative visualization workflows）。本说明替换上一轮对旧版本的判断。依据为用户摘要、审稿截图、新版源码、notebook 保存输出和本地 HTML 文件，以及下列原始文献来源。此次未重新运行全流程；保存输出属于仓库已有执行证据，不等于本机复现或方法有效性验证。

## 1. 明确更正：整合文件存在，且地点已经设为 dapuqiao

主入口：`05_Shanghai Power to Form Students/05_完整流程.ipynb`。

- `05_Shanghai Power to Form Students/config.py:9` 当前为 `SLUG = "dapuqiao"`。
- `06_AI Render Students/config.yaml:5` 当前为 `site: dapuqiao`。
- notebook 第 2 个索引单元的保存输出明确显示打浦桥，时间戳 20260702_101233。
- 阶段 A：多源数据、角色映射、查表反事实；B：五个高度情景；C：形态算子及四类配方；D：3D/OBJ；E：可选跨站点；F：生成 06 HTML 并建立链接。
- 全流程 notebook 通过配置读取地点，并非每个函数都硬编码打浦桥；四个专题情景名称在 notebook 内明确指定。

已存在的结果入口：

1. `05_Shanghai Power to Form Students/out/dapuqiao/Step_05/20260702_101233/index.html`
2. `06_AI Render Students/out/dapuqiao/canvas.html`
3. `06_AI Render Students/out/dapuqiao/report.html`

以前推荐的 `05/engine/build_report.py` 已不在新版目录；当前报告逻辑迁往 06。优先使用上述完整 notebook，而非备份 notebook 或“原始仓库版”。Run All 时宜从 05 目录启动内核，因为准备单元用相对路径定位 engine。阶段 F 调用 06 子进程，不是一个脱离项目依赖的独立文件。

已有保存输出：1370 栋；resident 780、developer 344、state 183、unknown 63；EULUC 覆盖约 88%，Function 约 46%。微经济和协商配方输出记录数均为 2320。后者含细分经营单元，不能不加区分地解释为现实中建筑栋数增长。以上数字未在本轮重算。

## 2. 最贴合摘要的可复用代码

本表位置均相对仓库根目录。

| 优先级 | 文件/函数 | 建议用途 |
|---|---|---|
| 主入口 | `05_Shanghai Power to Form Students/05_完整流程.ipynb` | 保留完整实验编排；改造成论文实验 notebook |
| 核心 | `05_Shanghai Power to Form Students/engine/my_operator.py:144` freeze_tags | 已有按标签保护的接口；以真实调查标签替代启发式标签 |
| 核心 | 同文件 `:153` micro_lease | 细分经营空间并分配用途标签；优先发展“保持建筑外壳的内部/首层适应性再利用” |
| 核心 | 同文件 `:205` frontage_quota | 旅游、居民服务、小店、文化的界面配额；改为真实街段和有效临街长度约束 |
| 进阶 | 同文件 `:246` crowd_valve、`:272` night_reversion | 时段与客流驱动的空间使用机制，有潜力形成后续研究方向 |
| 核心 | `05_Shanghai Power to Form Students/engine/operators.py:287` apply_regime；regimes.yaml | 四个打浦桥配方：tourism_capture、everyday_life_first、heritage_micro_economy、negotiated_24h_alley |
| 基线 | `05_Shanghai Power to Form Students/engine/common.py:349` scenario_heights；power_scenarios.yaml | 只调高度的简单方法，适合与新方法作对照 |
| 量测 | `05_Shanghai Power to Form Students/engine/measure.py:30` diagnose | 现有九个几何指标；作为独立评价层扩展 |
| 解释 | `05_Shanghai Power to Form Students/engine/plots/operator_atlas.py:95` change_summary；`:155` operator_diff；`:191` tag_map | 区分标签、角色、高度和几何变化，补充论文逐步解释图 |
| 解释 | `06_AI Render Students/engine/intro_story.py:131` _scenario_sequences | 已记录逐算子中间几何，可扩展成规则来源与逐建筑变化日志 |
| 展示 | `06_AI Render Students/engine/ws05.py`、build_canvas.py、editorial_data_film.py | 共用 05 算子结果生成可视化；叙事和 AI 表面效果作为沟通层 |

优先组合为完整 notebook + my_operator + regimes + measure + operator_diff/_scenario_sequences。无需为了论文核心贡献先引入 VAE 或扩展影像生成。

## 3. 新增能力应认可，但仍要区分模型语义与实证数据

### 3.1 标签有了，来源仍是教学启发式

`my_operator.py:85` 的 _copy_with_tags 根据用途角色、面积和记录序号自动补标签：

- resident 全部变 residential_core；每隔五条记录添加 resident_gate。
- state 自动加 emergency_access。
- developer 加 tourism_frontage/commercial；每隔七条加 culture。
- resident/developer 中面积小于 180 m² 的对象加 heritage。

所以“按标签保护”已实现，但不能说“已经识别并保护了真实遗产和消防通道”。记录顺序变化还可能改变文化/入口标签。`common.to_recs` 仍只保留 geom/h/sh/area/frozen，缺少原始 bid、用途、真实标签和证据来源。

### 3.2 新算子存在，但参数含义尚未全部实现

AST 静态检查确认：frontage_quota 的 primary_routes、crowd_valve 的 route、night_reversion 的 start_hour 在各函数体中未使用。

- 游客主线取建筑质心范围中间的水平/竖直轴线，不是读取真实道路或游客轨迹。
- crowd_threshold 只控制 `< 0.5` 时提前退出；没有输入实际客流并与阈值比较。0.75 不代表已估计拥挤程度。
- night_reversion 没有当前时间输入，start_hour 不参与判断；目前不是 22 点自动生效的时序模型。
- 夜间算子改变建筑 footprint 和高度；收摊、开放时间、通行权更适合改变空间使用状态，不应直接等同永久建筑变化。
- frontage_quota 根据候选记录数量分配标签，不是依据临街长度；冻结对象被跳过，配额未重新求解，因此最低/最高比例不是已保证满足的硬约束。

此外，_copy_with_tags 每次调用都会补标签。frontage_quota 移除旅游标签后，下一步可能给仍为 developer 的对象重新添加；微租赁改变 sh 后，下一步又会据新 sh 推导住宅核心或应急标签。应拆开“不可变原始身份”“拟议用途”“使用状态”，避免转换功能意外改变保护身份。

micro_lease/frontage_quota 使用固定 seed，具有复现设计意图；这与无随机分配的规则系统不同，且还依赖稳定输入顺序。论文应报告 seed 并测试顺序及种子敏感性。

### 3.3 指标与图形需要统一计算来源

- measure.py 仍只有 FAR、覆盖率、数量、高度均值/最大值/CV、粒度、瘦长比、集中度。功能混合、真实街道界面连续性、公共空间连通和居民连续性仍需实现。
- `editorial_data_film.py:52` 的瘦长度优先取 rec['area']；拆分/缩放后该缓存面积未随几何同步。其“均高/平均面积平方根”也不同于 measure.py 的逐栋瘦长比中位数，应明确口径。
- `editorial_data_film.py:71` 中，协商情景的 reliefNodes/oneWayAlleys/quietBuildings 来自对现状另跑的 _operator_metrics；而协商几何来自完整配方。两个计算分支不同，不能默认解释为同一最终方案的指标。
- `_scenario_sequences` 已有逐步几何，但每步 GeoJSON ID 来自重新枚举，缺少稳定父子 ID、参数来源、规则版本与约束检查。旧判断“完全没有中间记录”需要修正为“已有中间快照，审计链仍不完整”。
- 完整 notebook 阶段 D 的 negotiated 3D 使用阶段 B 的高度情景，导出 OBJ 是现状；并非阶段 C 全部算子的最终几何。论文图版应分别标明高度模型与完整形态模型。

上述均为源码检查结果，不是实测失败率。仓库已有 operator_atlas 的变化显示测试，但不能替代标签真实性、配额可行性或时序机制验证。

## 4. 结合文献，最有价值的研究深化

### 方向 A：有证据的“多方诉求—空间权利—指标—算子”映射（本轮论文优先）

把居民、租户、房东、小商户、文旅运营、政府和保护专业方的诉求分开，记录他们可影响的空间、时段及受影响范围。同一建筑允许关联多方。区分各方对目标的偏好权重与聚合时的决策影响权重，不能由用途标签自动赋予社会权力。

为每条规则记录：谁提出、原始证据、目标指标、可调参数、作用对象、保护限制、预测方向、执行后变化、未满足的诉求。重点是让参与者能质疑和修改转换机制。

[Wang & Zhou, 2022，田子坊权力—空间研究](https://www.dlyj.ac.cn/EN/abstract/article/1000-0585/51181)基于田野、访谈和观察讨论多主体关系、空间使用与日常实践，比抽象地把“居民权重”乘在高度上更贴近此项目。其启示是将主体与空间的关系显式建模；论文并不为当前 180 m²、22 点等数值提供依据。

[Commercial Gentrification and Entrepreneurial Governance in Shanghai, 2011](https://www.tandfonline.com/doi/full/10.1080/08111146.2011.598226)的出版商摘要讨论商业更新和社会排斥，可帮助论证为何商业增量需要同时衡量居民代价。[Community-Initiated Adaptive Reuse, 2014](https://ascelibrary.org/doi/10.1061/%28ASCE%29UP.1943-5444.0000174)的出版商检索摘要明确以田子坊社区发起的适应性再利用为案例，可指导把微租赁细分从拆建筑转向保壳更新。后两篇全文本轮未成功打开，暂不推断其具体实验细节。

### 方向 B：有限空间中的日夜使用权协商（有潜力，但需要扩充摘要范围）

将既有 crowd_valve/night_reversion 发展为时间状态模型：保持建筑几何，改变摊位占用、商铺营业、院落开放和通道通行状态。输入时间 t、客流 q、街巷网络和参与者偏好；约束居民入口、通行宽度及保护对象；输出各时段可达性和占用分配。

比较全天固定商业、全天固定居民优先、分时协商三个策略。优先用实地计数和营业记录校准，再检验高峰拥堵、夜间干扰与经营时长之间的权衡。若本轮不增加时间数据，就将此列为后续方向，不能以动画播放证明动态协商。

### 方向 C：解释是否改善参与，而不只是提高视觉吸引力

复用 operator_diff、tag_map 和 _scenario_sequences，比较普通参数控制与带规则来源/分步解释的界面。保持几何算子和可行域一致，测量参与者理解变化原因的准确率、表达异议的能力、任务时间及方案选择理由。

[Leong & Janssen, 2022](https://papers.cumincad.org/cgi-bin/works/paper/caadria2022_388)已经提出遗产保护中的 co-design/co-decision；[Talmor Blaistain & Fisher-Gewirtzman, 2025](https://journals.sagepub.com/doi/10.1177/23998083241261767)已结合规则生成与设计师参与。因此增量应落在有证据的多方映射、可追溯冲突和参与效果，而不能仅用“交互生成工具”作创新点。

[Koenig et al., 2020](https://publications.ait.ac.at/en/publications/integrating-urban-analysis-generative-design-and-evolutionary-opt/)支持借鉴街道—地块—建筑统一表示；[Cai et al., 2025](https://ual.sg/publication/2025-scs-bidirectional/2025-scs-bidirectional.pdf)支持检验指标组是否有效描述形态。这些已有方法说明，新增图形或指标数量本身并不充分证明本文贡献。

## 5. 回应三位审稿人的最小实验组合

| 审稿重点 | 可实施的下一步 | 应报告的证据 |
|---|---|---|
| R1 创新定位 | 比较参与式遗产、交互生成、指标—形态映射方法，明确本文增量 | 文献比较表，避免未经支持的“首次” |
| R1 有效性 | 现状、只调高度、同算子直接参数模型、诉求映射模型四组对比 | 同边界、同资源预算、同初始数据；量化差异与约束违反 |
| R2 stakeholder 必要性 | 多方及同类内部访谈；允许同楼多方、同人多目标 | 原始诉求、空间影响、分歧与最终转换依据 |
| R2 超越普通参数工具 | 同能力界面作用户对照；解释层消融 | 理解正确率、表达能力、任务耗时、定性意见 |
| R3 映射机制 | 发布逐条映射表和两三个建筑/街段的完整追踪 | 来源→目标→规则→实际变化→反馈 |

先完成四项基础核查：真实标签与街巷替换；统一 ID/功能/权利/状态；统一几何和展示指标；修复不生效参数与配额检查。再扫描偏好、阈值、种子及输入顺序；遇到不可行配额应报告失败原因，而不是默默跳过。

建议论文优先题目方向：**面向历史街区微更新的可解释多方诉求—空间规则转换与验证。** 以方向 A 为主、方向 C 作验证；有足够时间和客流数据时再将方向 B 提升为主贡献。AI 渲染与叙事影片保留为展示产物，不能用来证明客流改善、保护真实性或协商有效。
