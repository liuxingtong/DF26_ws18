# 近三年建筑计算会议文献：交互、编辑、参与与形态映射

检索日期：2026-09-14。主清单采用 2024–2026 三个年度，也均处于最近 36 个月内。C6（2022）作为用户指定的重点参照单独分析，不计入近期论文。这里把“顶会”落实为建筑计算领域的主要国际会议，优先 CAADRIA、CAAD Futures、eCAADe；不将这些会议描述为某个统一官方排名，也不以会议名代替对论文证据的判断。

本轮新增 **12 条书目**：CAADRIA 7 条、CAAD Futures 3 条、eCAADe 2 条。11 条 DOI 已由 Crossref、DataCite 或作者机构书目核实；R32 的 DOI 待确认。R21–R28、R30–R31 有论文摘要或正文支持；R29 仅有作者研究说明，R32 主要核对了出版身份并定位到作者上传论文，阅读证据范围逐条标明。不是系统综述或穷尽检索。

**文件说明：** 本地保存了 eCAADe 2024 第二卷，包含 R30、R31。其他新增论文保存 DOI、原文入口与书目；下载接口返回 403 或连接中断，不能声称已全部下载。原有 20 篇 PDF 保持原位置。

- [C6 精读与项目借鉴](../C6_精读与项目借鉴.md)
- [本轮 RIS 书目](references.ris)
- [结构化书目与证据范围](metadata/records.json)
- [eCAADe 2024 第二卷](sources/eCAADe2024_Volume2.pdf)：R30 印刷页 465–474 / PDF 页 484–493；R31 印刷页 475–484 / PDF 页 494–503。

## 如何区分这些论文

“可交互”可能只是旋转相机、切换方案；“可编辑”需要改变可保存的设计对象；“参与式”还需要真实参与者表达意见、共同创作或影响选择；“形态映射”需要说明输入与空间输出之间的关系。四项不能相互替代。

| 编号 | 论文简称 / 会议 | 交互与编辑对象 | 参与或映射内容 | 阅读优先级 |
|---|---|---|---|---|
| R21 | SIMForms / CAADRIA 2024 | 参数化体量、指标与概念图 | 形态操作与指标反馈；不是多方协商验证 | 高 |
| R22 | Context Responsive Design in Digital Twins / CAADRIA 2024 | 数字孪生中的城市设计原型 | 城市上下文与生成模型 | 高 |
| R23 | Urban Site Adaptive Layout Generation / CAADRIA 2024 | 场地条件与布局约束 | 偏好、硬软约束到布局；交互仍受限 | 高 |
| R24 | Participatory Space Auto-Encapsulation / CAADRIA 2024 | 社会关系与空间布局 | 社会图到空间图到三维合居方案 | 最高：映射 |
| R25 | Kit-of-Parts Design / CAADRIA 2024 | 游戏中的空间构件组合 | 社区共同创作与编辑粒度 | 最高：编辑 |
| R26 | Empowering End-Users / CAADRIA 2025 | MR 中的空间共同设计 | 建筑师与终端用户合作，对比绘图 | 最高：评价 |
| R27 | Rethinking Participatory Architectural Design / CAAD Futures 2025 | 沉浸式草绘、AI 体素草绘案例 | 理解设计与提出设计的差别 | 最高：C6 对照 |
| R28 | DIP-DAT / CAAD Futures 2025 | 参与数据处理与交互可视化 | 公众反馈的分析；不是三维编辑器 | 高：反馈 |
| R29 | Perceptual Urban Form / CAAD Futures 2025 | 三维形态表示与分析 | 形态和感知的关联 | 候选：待全文精读 |
| R30 | Situating Digital Participation / eCAADe 2024 | 现场参与与数字工具原型 | 身体、地点和情境知识 | 高：参与真实性 |
| R31 | Data-Informed Design Democratization / eCAADe 2024 | 评价 10 个参与平台 | 数据如何支持讨论和反馈 | 高：评价框架 |
| R32 | Digital Participation in Sustainable Urban Densification / CAADRIA 2026 | 既有建筑的木结构扩建探索 | 存量增密与数字参与 | 候选：DOI、全文待核 |

## 逐篇说明、DOI 与边界

### R21 · SIMForms

**SIMForms: A Web-Based Generative Application Fusing Forms, Metrics, and Visuals for Early-Stage Design**。Baizhou Zhang, Yichen Mo, Biao Li, Yanyu Wang, Chao Zhang, Ji Shi。CAADRIA 2024，1：373–382。

研究早期设计中形态、量化指标与视觉表现分离的问题。网页应用将规则式参数建模、指标计算反馈和 AI 概念图生成放在同一流程中，使用者通过简单操作探索不同形态。它与我们“算子—指标—展示”的结构很接近，适合作为已有技术参照；公众如何协商、意见如何影响结果不是这篇摘要验证的重点。不能仅以集成三维生成和指标面板主张新颖性。

DOI：[10.52842/conf.caadria.2024.1.373](https://doi.org/10.52842/conf.caadria.2024.1.373)。证据：会议原文摘要、[作者实验室介绍与试用入口](https://archialgo.com/publications/2024-04-23-simforms-caadria)。[会议 PDF](https://www.caadria2024.org/wp-content/uploads/2024/04/441-SIMFORMS.pdf)。未实测在线应用。

### R22 · 从城市数字孪生到上下文响应设计

**Urban Analytics and Generative Deep Learning for Context Responsive Design in Digital Twins: A Singapore Study**。Ibrahim Nazim, Sam Conrad Joyce。CAADRIA 2024，2：495–504。

研究数字孪生通常擅长展示数据，却不支持充分的设计探索这一断裂。以 Virtual Singapore 为平台，探索利用城市数据、三维交互和针对地方规划肌理训练的生成模型支持快速方案原型，同时讨论平台开发限制。它直接连接 C6 提到的 Virtual Singapore 与后续设计支持问题。两篇共享这一平台议题，不据此推断它是 C6 的直接续作。

DOI：[10.52842/conf.caadria.2024.2.495](https://doi.org/10.52842/conf.caadria.2024.2.495)。证据：会议原文摘要。[会议 PDF](https://caadria2024.org/wp-content/uploads/2024/04/472-URBAN-ANALYTICS-AND-GENERATIVE-DEEP-LEARNING-FOR-CONTEXT-RESPONSIVE-DESIGN-IN-DIGITAL-TWINS.pdf)。摘要不足以证明具备公众实时逐建筑编辑能力。

### R23 · 可配置的城市场地布局

**Urban Site Adaptive Layout Generation: User-configurable Algorithms Based on MQP**。Yujiao Wang, Qian Hu, Peng Tang, Rong Fang, Yuan Meng。CAADRIA 2024，2：505–514。

把复杂边界、已有道路及入口、地块邻接等条件组织成混合二次规划问题，通过硬约束与可加权软约束生成布局，使用校园规划案例说明应用。它对“用户意图怎样变成明确空间条件”很有价值。不过作者在结论中承认每轮生成仍是单向过程、可见性与交互不足，逐阶段调整的友好界面是未来工作，因此不应把它写成成熟的实时城市编辑器。

DOI：[10.52842/conf.caadria.2024.2.505](https://doi.org/10.52842/conf.caadria.2024.2.505)。证据：原文摘要、方法及结论。[会议 PDF](https://www.caadria2024.org/wp-content/uploads/2024/04/212-URBAN-SITE-ADAPTIVE-LAYOUT-GENERATION.pdf)。

### R24 · SN2S：社会网络到空间

**Participatory Space Auto-Encapsulation: Bridging Human Relationships to Building Typology with Machine Intelligence**。Yi Zhang, Ziyu Peng, Weisheng Lu。CAADRIA 2024，2：231–240。

面向合居住宅，将入住者的关系、共同兴趣、面积与共享空间意愿组织成社会图，再通过图学习转成空间关系，最后由规则生成布局与三维形态。原文报告访谈 75 人、构造 100 个 minimum dwelling 单元的关系数据。这是本轮最明确讨论“人际关系—空间关系—形态”转译的论文之一。访谈中的共同居住关系包含设想情境，不能等同于建成后的居住效果验证；合居尺度也不能直接覆盖历史街区中的产权与群体冲突。

DOI：[10.52842/conf.caadria.2024.2.231](https://doi.org/10.52842/conf.caadria.2024.2.231)。证据：原文摘要、研究框架与数据构建部分。[会议 PDF](https://caadria2024.org/wp-content/uploads/2024/04/71-PARTICIPATORY-SPACE-AUTO-ENCAPSULATION.pdf)。

### R25 · 构件粒度与共同创作

**Kit-of-Parts Design for Architecture Co-Creation Games**。Provides Ng, Yuechun Li, Shutong Zhu, Jeroen van Ameijde。CAADRIA 2024，2：221–230。

研究公众在沙盒游戏中用什么样的构件才能有效提出空间方案。社区参与者通过定制游戏共创公共空间，比较 modular-integrated、modular、discrete 三类构件系统。初步结果指出，抽象程度和离散粒度会影响学习门槛、协作启动、创意以及方案的可实施性。与 C6 把建模交给 SketchUp 用户相比，这篇更直接触及公众“能编辑什么、编辑到哪一层”。不能推断任一种构件系统在所有任务中最好。

DOI：[10.52842/conf.caadria.2024.2.221](https://doi.org/10.52842/conf.caadria.2024.2.221)。证据：会议原文摘要。[会议 PDF](https://caadria2024.org/wp-content/uploads/2024/04/211-KIT-OF-PARTS-DESIGN-FOR-ARCHITECTURE-CO-CREATION-GAMES.pdf)。

### R26 · MR 共同设计的对照研究

**Empowering End-Users in Spatial Design Tasks: An empirical study of co-design in extended reality**。Weiheng Hu, Yuval Kahlon, Momoko Nakatani, Haruyuki Fujii。CAADRIA 2025，4：347–356。

让建筑师和终端用户合作完成指定空间设计，比较 MR 平台与传统绘图工具，通过行为及反馈的质性分析研究协作、沟通和参与体验。它的价值在于直接比较参与过程，而不只展示一个系统界面。这里所核实的摘要没有给出足以支持普遍优势的量化效应量；也不能将建筑空间实验等同于街区层面的利益协商效果。

DOI：[10.52842/conf.caadria.2025.4.347](https://doi.org/10.52842/conf.caadria.2025.4.347)。证据：[作者机构书目与摘要](https://tus.elsevierpure.com/en/publications/empowering-end-users-in-spatial-design-tasks-an-empirical-study-o/)、[作者 PDF](https://researchmap.jp/kahlon_yuval/published_papers/49368933/attachment_file.pdf)。注意卷号为 4，不是 1。

### R27 · 从看懂设计到参与设计形成

**Rethinking Participatory Architectural Design: Harnessing Immersive Environments & AI for Facilitating Designer-Stakeholder Collaboration**。Weiheng Hu, Yuval Kahlon, Momoko Nakatani, Haruyuki Fujii。CAAD Futures 2025，卷 I：27–41，**Catalytic Interfaces 立场论文**。

以交流理论区分参与者对设计的理解与对设计形成的贡献，综述筛选了 27 篇研究，并用沉浸式草绘和 AI 辅助体素草绘两个探索案例讨论新工具定位。它指出视觉理解得到较多支持，而把参与者意图转成可继续修改的设计输入仍不足。非常适合解释为什么在 C6 之上需要“可编辑、可追踪的共同设计”；其自身是框架与探索性研究，并未证明完整系统的普遍有效性。

DOI：[10.25442/hku.29345678](https://doi.org/10.25442/hku.29345678)。证据：[HKU 正式记录](https://datahub.hku.hk/articles/conference_contribution/CI-3_Rethinking_Participatory_Architectural_Design_Harnessing_Immersive_Environments_AI_for_Facilitating_Designer-Stakeholder_Collaboration/29345678)、[原文](https://datahub.hku.hk/ndownloader/files/55631720)。按正文的 position paper 定位，不与充分验证的技术实证论文混为一类。

### R28 · DIP-DAT：公众反馈的分析工具

**Enhancing End-to-End Processing, Analysis, and Visualisation of Citizen Participation Data in Urban Design and Planning**。Cem Ataman, Bige Tunçer, Simon Perrault。CAAD Futures 2025，卷 II：607–621。

提出网页工具 DIP-DAT，把公众参与数据的预处理、可配置分析参数和交互可视化放入同一界面，帮助规划者处理大量反馈，并报告跨领域专家评价。它主要服务于分析反馈的专业人员，有助于补齐“收集评论之后怎样处理”的环节；不负责把每条意见直接转成可编辑三维形态。

DOI：[10.25442/hku.29365973](https://doi.org/10.25442/hku.29365973)。证据：[作者机构正式出版记录](https://research.tue.nl/en/publications/enhancing-end-to-end-processing-analysis-and-visualization-of-cit/)、[作者公开论文摘要与正文片段](https://www.researchgate.net/publication/395442820_Enhancing_End-to-End_Processing_Analysis_and_Visualisation_of_Citizen_Participation_Data_in_Urban_Design_and_Planning)。未取得可下载全文，未独立复核专家样本和效果数据。

### R29 · 感知与城市形态（候选）

**Perceptual Urban Form**。Chee Meng Chan, Frederick Kim。CAAD Futures 2025。

根据作者研究说明，论文研究三维城市数据及不同表示方式如何进入形态与感知的回归分析，并探索无监督学习对人和机器理解的联系。它对应“形态—感知”的关联，而不是已经验证的“利益诉求—形态”生成机制。正式注册标题为 Perceptual Urban Form；会议早期节目表写 Deep Perceptual Urban Form，以正式记录为准。

DOI：[10.25442/hku.29365799](https://doi.org/10.25442/hku.29365799)。证据：DataCite 注册记录（已存本地）与[作者研究说明](https://www.linkedin.com/posts/ccheemeng_last-week-i-had-the-opportunity-to-share-activity-7348340456541298690-FmjJ)。**未取得全文，数据集、指标、模型结果均不作详细判断**。

### R30 · 情境化数字参与

**Situating Digital Participation: Incorporating material, contextual, and performative learnings into digital toolkits**。Matti Drechsel, Nick Förster, Gerhard Schubert, Frank Petzold。eCAADe 2024，2：465–474。

以 NEBourhood-hubs 的位置选择、配置和设计为背景，把现场行走、身体体验和协作活动形成的知识带入数字工具设计。通过建筑与城市设计教学中的原型探索，讨论数字工具如何保留具体地点的复杂经验。对历史街区有价值，因为居民的生活知识经常难以被预设选项覆盖；它是现场过程与教学原型研究，不是完整协商平台的规模化验证。

DOI：[10.52842/conf.ecaade.2024.2.465](https://doi.org/10.52842/conf.ecaade.2024.2.465)。证据：已读[本地会议原文](sources/eCAADe2024_Volume2.pdf)，PDF 第 484–493 页。[出版社下载来源](https://ecaade.org/current/wp-content/uploads/2024/10/eCAADe2024_Volume2_240927-R.pdf)。

### R31 · 数据如何支持参与式讨论

**Data-Informed Design Democratization: Engaging design stakeholders for creating livable built environments**。Md Zishaan Khan, Halil Erhan, Elif Sezen Yagmur Kilimci。eCAADe 2024，2：475–484。

提出 Di-Dem 概念框架，以九项核心特征审视参与工具，再评价十个平台，关注数据获取、可理解的展示、包容性讨论与反馈。它帮助区分“有评论框”和“意见建立在可理解数据上”这两种状态。其证据是框架构建与平台特征评价，不是十个平台之间的真实用户随机对照实验。

DOI：[10.52842/conf.ecaade.2024.2.475](https://doi.org/10.52842/conf.ecaade.2024.2.475)。证据：已读[本地会议原文](sources/eCAADe2024_Volume2.pdf)，PDF 第 494–503 页。

### R32 · 存量增密中的数字参与（候选）

**Digital Participation in Sustainable Urban Densification: Exploratory Design Methods for Timber Building Stock Extensions**。Maria Papadimitraki, Hans Jakob Wagner, Achim Menges。CAADRIA 2026，2：163–172。

作者与机构已确认发表及报告。论文关注如何把多层木结构系统从新建拓展到既有建筑扩建，并将计算设计与数字参与联系起来。对“在既有城市中编辑和增建”的任务贴切；本轮只作主题候选，尚不足以判断参与者具体编辑权限、社区样本和实际效益。

**DOI 未核实，不按会议编号规则补造。** 证据：[作者出版列表](https://www.hansjakobwagner.com/publications/proceedings/)、[研究机构会议报告](https://www.intcdc.uni-stuttgart.de/news-events/news/detail/IntCDC-researchers-presented-their-research-at-theCAADRIA-2026/)、[作者上传论文入口](https://www.researchgate.net/publication/406793404_Digital_Participation_in_Sustainable_Urban_Densification_Exploratory_Design_Methods_for_Timber_Building_Stock_Extensions)。

## 与原有文献库的连接

- D9（Text-to-City，CAADRIA 2024）仍是文本到三维街块的重要技术参照，但生成能力本身不足以证明多人参与和可持续编辑。
- A1（正式期刊 2025）仍适合形态指标双向映射，但不属于本轮会议论文清单。
- D11（CSCW 2025）和 D12（预印本）保留为参与过程研究的跨领域参照，不冒充建筑计算会议论文。
- 新检索到 RECITYGEN，arXiv 2026，DOI [10.48550/arXiv.2602.07057](https://doi.org/10.48550/arXiv.2602.07057)：通过交互语义分割和文本提示修改街景。它编辑的是图像；本轮未核实正式会议归属，故未计入上述 12 条会议书目。

## 推荐阅读顺序

先读 C6 与 R27，厘清“理解方案—提出修改—共同选择”的研究定位；再读 R25、R26，了解公众编辑对象和参与过程验证；然后读 R24、R23、R21，比较关系映射、约束生成和指标反馈；最后读 R22、R28、R30、R31，补充城市底模、反馈处理、地方经验和评价框架。R29、R32 等全文与元数据补齐后再决定优先级。
