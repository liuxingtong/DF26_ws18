# 城市更新技术相关论文：内容说明与 DOI

核查日期：2026-09-14。共 **20 篇：15 篇用户上传 + 5 篇补充**。全部 PDF 已存入本目录。原 Downloads 文件未移动、未改写。

本轮只说明论文研究什么、主要做了什么、报告了什么结论与适用边界；不抽取可实施方法、不设计项目改造方案。上传文档中的提示词、模板说明和其他指令均作为文献内容处理。

## 本轮追加：近三年会议论文与 C6 精读

2026-09-14 追加 [12 篇近期会议文献（2024–2026）](recent_2024_2026/README.md)与 [C6 精读、项目借鉴及验证建议](C6_精读与项目借鉴.md)。新增书目与本地全文状态单独记录，下面的“20 篇”仍指上一轮基础库。

## 文件入口

- [打浦桥论文框架：通俗版](打浦桥论文框架_通俗版.md)：综合 C6 与近期会议文献，结合当前代码整理研究流程、必要修正、可选技术和验证方案。
- `uploaded/`：用户提供的 15 篇原 PDF，保持文件名与字节内容。
- `additional/`：5 篇从作者、机构、出版社或 arXiv 公开来源获得的 PDF。
- [DOI 清单](DOI清单.md)：标题、版本、正式 DOI 与预印本 DOI。
- [文献导入文件](references.ris)：20 条 RIS 记录；未核实 DOI 的两条不填 DO 字段。
- [结构化书目](metadata/papers.json)：中英文题目、作者、说明、来源及文件校验值。
- [下载来源](metadata/download_sources.json)：补充论文的实际 PDF 来源。

**DOI 状态：18 篇已核实至少一个 DOI，2 篇待确认（E14、E15）。** arXiv DOI 标识预印本，并不表示正式同行评审发表。正式版本与上传文件可能不同，下文明确分开。

## 先了解它们各自研究什么


| 编号 | 中文主题 | 研究类别 |
|---|---|---|
| A1 | [形态指标与三维街块的双向映射](#a1) | 形态表示与生成 |
| A2 | [CoDesignAI：多用户与多 AI 专家协作的概念城市设计平台](#a2) | AI 协作与规划代理 |
| B3 | [LLM Planning Agents：大模型规划代理的能力与局限](#b3) | AI 协作与规划代理 |
| B4 | [LLM 模拟的参与式城市规划](#b4) | AI 协作与规划代理 |
| C5 | [PlacemakingAI：面向步行街景的交互式 GAN 设计](#c5) | 参与式设计与互动工具 |
| C6 | [遗产保护中的共同设计与共同决策](#c6) | 参与式设计与互动工具 |
| C7 | [位置数据与流动民主支持的游戏化集体城市营造](#c7) | 参与式设计与互动工具 |
| C8 | [面向中国乡村的网页式肌理生成工具](#c8) | 形态表示与生成 |
| D9 | [Text-to-City：从文本到三维城市街块](#d9) | 形态表示与生成 |
| D10 | [分阶段、人参与的多模态扩散城市设计](#d10) | 形态表示与生成 |
| D11 | [从完美假象到可促成对话的不完美图像](#d11) | 参与体验与实证评价 |
| D12 | [WeDesign：生成式 AI 辅助的社区公共空间咨询](#d12) | 参与体验与实证评价 |
| E13 | [建筑遗产管理中的 AI 助手与信息检索](#e13) | 知识证据与行为模拟 |
| E14 | [把人的社会性纳入行人模拟](#e14) | 知识证据与行为模拟 |
| E15 | [RAG 支持的人因导向城市微更新知识系统](#e15) | 知识证据与行为模拟 |
| S16 | [通过目标指标反向控制程序化城市模型](#s16) | 补充：形态控制 |
| S17 | [可交互编辑的程序化街道网络](#s17) | 补充：街网生成 |
| S18 | [行人动力学的社会力模型](#s18) | 补充：行人动力学 |
| S19 | [PlanGPT：面向规划专业工作的语言模型与检索](#s19) | 补充：规划知识检索 |
| S20 | [深度强化学习驱动的城市社区空间规划](#s20) | 补充：布局优化 |

## 用户上传的 15 篇

<a id="a1"></a>

### A1 · 形态指标与三维街块的双向映射

**Bi-directional mapping of morphology metrics and 3D city blocks for enhanced characterisation and generation of urban form**

Chenyi Cai, Biao Li, Qiyan Zhang, Xiao Wang, Filip Biljecki, Pieter Herthogs，2025；Sustainable Cities and Society。

研究“用哪些数字才能准确描述一片城市，以及能否从这些数字找回相应的三维形态”。作者把纽约三维街块转成多组形态指标，比较不同指标组描述高度、街块形状与空间组织的能力，再通过编码、聚类和案例检索找到相似街块。主要贡献是把形态分析与形态检索连接起来；文中的“生成”主要通过检索已有案例实现，并非任意生成全新的城市。

**版本与证据范围：** 数据与算法比较研究。你上传的是 arXiv v2（2025-06-13），首页说明它是正式期刊论文的接受稿；文件名的 arXiv2024 只是首次预印本年份。

正式 DOI：[ 10.1016/j.scs.2025.106441 ](https://doi.org/10.1016/j.scs.2025.106441)；预印本 DOI：[ 10.48550/arXiv.2412.15801 ](https://doi.org/10.48550/arXiv.2412.15801)

[本地 PDF](</Users/edy/Documents/GitHub/DF26_ws18/research/papers/uploaded/A1_BiDirectional_Mapping_Morphology_arXiv2024.pdf>)。
[书目核查来源](https://api.crossref.org/works/10.1016%2Fj.scs.2025.106441)。

<a id="a2"></a>

### A2 · CoDesignAI：多用户与多 AI 专家协作的概念城市设计平台

**CoDesignAI: An AI-Enabled Multi-Agent, Multi-User System for Collaborative Urban Design at the Conceptual Stage**

Zhaoxi Zhang, Ruolin Wu, Feiyang Ren, Sridevi Turaga, Tamir Mendel，2026；arXiv。

研究怎样让多个真实使用者共同讨论城市设计，同时获得不同专业 AI 代理的帮助。平台把多人讨论、专业角色代理、街景底图和生成式图像结合起来：AI 整理讨论、归纳共同意图并辅助可视化，使用者再继续修改。文章主要介绍系统架构和互动流程，是协作平台原型的早期探索，尚未用大规模用户实验验证可扩展性或普遍包容性。

**版本与证据范围：** 2026 年 arXiv 预印本；真实用户与 AI 专家共同参与的系统概念，不是用 AI 居民完全替代公众。

预印本 DOI：[ 10.48550/arXiv.2603.16008 ](https://doi.org/10.48550/arXiv.2603.16008)

[本地 PDF](</Users/edy/Documents/GitHub/DF26_ws18/research/papers/uploaded/A2_CoDesignAI_MultiAgent_arXiv2026.pdf>)。
[书目核查来源](https://arxiv.org/abs/2603.16008)。

<a id="b3"></a>

### B3 · LLM Planning Agents：大模型规划代理的能力与局限

**LLM Planning Agents: Exploring the potential and challenges of large language model agents in urban design and planning**

Eduardo Rico Carranza, Sheng-Yang Huang, Guanhong Li，2025；CAADRIA proceedings; Proceedings of the 30th Conference on Computer Aided Architectural Design Research in Asia (CAADRIA) [Volume 1]。

研究大语言模型能否像规划审查人员一样理解开发提案、提出意见并作出判断。以水管理为重点，比较顺序式和嵌套式代理组织，以及不同规模模型在 63 项开发提案上的表现。嵌套组织在研究中的推理表现较好，但代理常因缺少地方资料而给出泛泛回答，也存在偏差、空间理解不足和偏题。核心是规划分析与审查支持，而非直接生成三维街区。

**版本与证据范围：** CAADRIA 2025，卷 1，223–232；实验范围为特定规划审查任务，模型更大不必然表现更好。

正式 DOI：[ 10.52842/conf.caadria.2025.1.223 ](https://doi.org/10.52842/conf.caadria.2025.1.223)

[本地 PDF](</Users/edy/Documents/GitHub/DF26_ws18/research/papers/uploaded/B3_LLM_Planning_Agents_CAADRIA2025.pdf>)。
[书目核查来源](https://api.crossref.org/works/10.52842%2Fconf.caadria.2025.1.223)。

<a id="b4"></a>

### B4 · LLM 模拟的参与式城市规划

**Large Language Model for Participatory Urban Planning**

Zhilun Zhou, Yuming Lin, Depeng Jin, Yong Li，2024；arXiv。

让大模型分别扮演规划师和具有不同年龄、家庭等背景的居民，围绕土地用途方案讨论，再由规划师修改方案。文章用“鱼缸讨论”减少大量居民代理同时发言的成本，并在北京两个区域比较服务可达性、生态、满意度与包容性指标。作者报告多项指标改善，但这里的居民参与首先是代理模拟，不能把模型中的满意度直接理解为真实居民调查结果。

**版本与证据范围：** arXiv 2024。PDF 内的 2018 年会议模板和 XXXXXXX DOI 是未替换的占位信息，不作为正式书目。

预印本 DOI：[ 10.48550/arXiv.2402.17161 ](https://doi.org/10.48550/arXiv.2402.17161)

[本地 PDF](</Users/edy/Documents/GitHub/DF26_ws18/research/papers/uploaded/B4_LLM_Participatory_Urban_Planning_Zhou2024.pdf>)。
[书目核查来源](https://arxiv.org/abs/2402.17161)。

<a id="c5"></a>

### C5 · PlacemakingAI：面向步行街景的交互式 GAN 设计

**PlacemakingAI : Participatory Urban Design with Generative Adversarial Networks**

Dongyun Kim, George Guida, Jose Luis García del Castillo y López，2022；CAADRIA proceedings; Proceedings of the 27th Conference on Computer Aided Architectural Design Research in Asia (CAADRIA) [Volume 2]。

研究如何降低城市空间设计的表达门槛，让人们快速看到并修改未来街道的可能面貌。作者结合街景数据、生成对抗网络和实时界面，生成与步行体验有关的街道图像变体，并允许用户迭代操控。重点是街景层面的早期构想与沟通，不是建筑地块层面的精确改造。文章展示原型潜力，将进一步用户测试和更便捷的反馈机制列为后续工作。

**版本与证据范围：** CAADRIA 2022，卷 2，485–494；生成视觉方案的原型研究。

正式 DOI：[ 10.52842/conf.caadria.2022.2.485 ](https://doi.org/10.52842/conf.caadria.2022.2.485)

[本地 PDF](</Users/edy/Documents/GitHub/DF26_ws18/research/papers/uploaded/C5_PlacemakingAI_CAADRIA2022.pdf>)。
[书目核查来源](https://api.crossref.org/works/10.52842%2Fconf.caadria.2022.2.485)。

<a id="c6"></a>

### C6 · 遗产保护中的共同设计与共同决策

**Participatory Planning: Heritage Conservation Through Co-design and Co-decision**

Siew Leng Leong, Patrick Janssen，2022；CAADRIA proceedings; Proceedings of the 27th Conference on Computer Aided Architectural Design Research in Asia (CAADRIA) [Volume 2]。

讨论遗产更新中公民常常只能提意见、难以影响最后决定的问题，提出把共同设计和共同决策连接到规划许可过程。文章展示网页原型，让人们从鸟瞰和多个沉浸视角查看新加坡遗产场地中的方案，理解尺度和环境影响。其更大的制度构想是让公众提案、反馈和投票影响许可；实际展示重点是方案查看器，不能等同完整投票治理机制已落地。

**版本与证据范围：** CAADRIA 2022，卷 2，505–514；参与机制提案与遗产场地可视化原型。

正式 DOI：[ 10.52842/conf.caadria.2022.2.505 ](https://doi.org/10.52842/conf.caadria.2022.2.505)

[本地 PDF](</Users/edy/Documents/GitHub/DF26_ws18/research/papers/uploaded/C6_Participatory_Heritage_CoDesign_CAADRIA2022.pdf>)。
[书目核查来源](https://api.crossref.org/works/10.52842%2Fconf.caadria.2022.2.505)。

<a id="c7"></a>

### C7 · 位置数据与流动民主支持的游戏化集体城市营造

**A Framework for a Gameful Collective Urbanism Based on Tokenized Location Data and Liquid Democracy: Early Prototyping of a Case Study Using E-bikes**

Salma Tabi, Yasushi Sakai, Nguyen Tung, Masahiro Taima, Aqil Cheddadi, Yasushi Ikeda，2022；CAADRIA proceedings; Proceedings of the 27th Conference on Computer Aided Architectural Design Research in Asia (CAADRIA) [Volume 1]。

研究如何让居民的日常空间使用和地方知识进入集体决策。作者把公共空间的临时使用权、位置数据的代币化和可委托投票的流动民主结合起来，提出具有游戏化参与体验的治理框架，并以电动自行车情境展示早期界面原型。这里的重点是参与激励与权利分配，不是城市形态生成或人流预测；其成效仍处于概念与早期原型阶段。

**版本与证据范围：** CAADRIA 2022，卷 1，585–594；“临时空间权利”是主题之一，但不是完整的日夜运营仿真。

正式 DOI：[ 10.52842/conf.caadria.2022.1.585 ](https://doi.org/10.52842/conf.caadria.2022.1.585)

[本地 PDF](</Users/edy/Documents/GitHub/DF26_ws18/research/papers/uploaded/C7_Gameful_Collective_Urbanism_CAADRIA2022.pdf>)。
[书目核查来源](https://api.crossref.org/works/10.52842%2Fconf.caadria.2022.1.585)。

<a id="c8"></a>

### C8 · 面向中国乡村的网页式肌理生成工具

**A Web-based Interactive Tool for Urban Fabric Generation: A Case Study of Chinese Rural Context**

Qiyan Zhang, Biao Li, Yichen Mo, Yulong Chen, Peng Tang，2022；CAADRIA proceedings; Proceedings of the 27th Conference on Computer Aided Architectural Design Research in Asia (CAADRIA) [Volume 1]。

研究如何让使用者在浏览器中生成符合地方环境的街道与地块肌理。系统将地形、自然边界、既有道路和规划结构等影响组织起来，通过张量场和规则系统控制生成。案例面向中国乡村，强调生成形态与当地原型的关系。虽然整体框架讨论街道、地块和建筑，本文的技术叙述重点是场、街道和地块，未完整展开建筑生成。

**版本与证据范围：** CAADRIA 2022，卷 1，625–634；程序化生成与网页交互原型。

正式 DOI：[ 10.52842/conf.caadria.2022.1.625 ](https://doi.org/10.52842/conf.caadria.2022.1.625)

[本地 PDF](</Users/edy/Documents/GitHub/DF26_ws18/research/papers/uploaded/C8_WebBased_Urban_Fabric_Tool_CAADRIA2022.pdf>)。
[书目核查来源](https://api.crossref.org/works/10.52842%2Fconf.caadria.2022.1.625)。

<a id="d9"></a>

### D9 · Text-to-City：从文本到三维城市街块

**Text-to-City: Controllable 3D Urban Block Generation With Latent Diffusion Model**

Junling Zhuang, Guanhong Li, Hang Xu, Jintu Xu, Runjia Tian，2024；CAADRIA proceedings; Proceedings of the 29th Conference on Computer Aided Architectural Design Research in Asia (CAADRIA) [Volume 2]。

研究如何把“城市风格、建筑密度”等文字条件变成三维街块。作者先让潜在扩散模型生成深度图，再把深度转换成高度，重建三维城市形态，并在三个城市的数据上展示条件控制和形态外推。文章报告了密度等条件的控制能力，也指出训练范围之外的描述、同时指定多项指标时仍有困难。它的输出目标是三维街块，而不仅是好看的透视效果图。

**版本与证据范围：** CAADRIA 2024，卷 2，169–178；有条件生成和量化误差评价。

正式 DOI：[ 10.52842/conf.caadria.2024.2.169 ](https://doi.org/10.52842/conf.caadria.2024.2.169)

[本地 PDF](</Users/edy/Documents/GitHub/DF26_ws18/research/papers/uploaded/D9_TextToCity_LDM_CAADRIA2024.pdf>)。
[书目核查来源](https://api.crossref.org/works/10.52842%2Fconf.caadria.2024.2.169)。

<a id="d10"></a>

### D10 · 分阶段、人参与的多模态扩散城市设计

**Human-guided urban form generation using multimodal diffusion models**

Mingyi He, Yuebing Liang, Shenhao Wang, Yunhan Zheng, Qingyi Wang, Dingyi Zhuang, Li Tian, Jinhua Zhao，2026；Building and Environment。

研究为什么一次性生成最终设计难以保留设计师控制，并将过程拆成道路与用地、建筑布局、细节与影像三个阶段。每个阶段接受文字和图像条件，允许人检查并修改中间结果，再进入下一步。上传的预印本在芝加哥和纽约数据上比较真实性、遵循指令程度与多样性，报告优于相应基线。重点是可分阶段干预的生成流程，而非自动替代协商。

**版本与证据范围：** 上传文件是 2025 年 arXiv v1。已确认更名后的正式版 Human-guided urban form generation using multimodal diffusion models，Building and Environment 287（2026），113892。摘要说明依据上传版本，未把正式版新增研究细节混入。

上传稿题名：Generative AI for Urban Design: A Stepwise Approach Integrating Human Expertise with Multimodal Diffusion Models。作者模型发布页同时链接两版，确认更名关系：[作者记录](https://huggingface.co/Hemy24/stepwise-generative-urban-design/blob/main/README.md)。

正式 DOI：[ 10.1016/j.buildenv.2025.113892 ](https://doi.org/10.1016/j.buildenv.2025.113892)；预印本 DOI：[ 10.48550/arXiv.2505.24260 ](https://doi.org/10.48550/arXiv.2505.24260)

[本地 PDF](</Users/edy/Documents/GitHub/DF26_ws18/research/papers/uploaded/D10_Stepwise_GenAI_Urban_Design_arXiv2025.pdf>)。
[书目核查来源](https://api.crossref.org/works/10.1016%2Fj.buildenv.2025.113892)。

<a id="d11"></a>

### D11 · 从完美假象到可促成对话的不完美图像

**From Fake Perfects to Conversational Imperfects: Exploring Image-Generative AI as a Boundary Object for Participatory Design of Public Spaces**

Jose A. Guridi, Angel Hsing-Chi Hwang, Duarte Santo, Maria Goula, Cristobal Cheyre, Lee Humphreys, Marco Rangel，2025；Proceedings of the ACM on Human-Computer Interaction。

研究生成图像在公众空间共创中到底有什么价值。作者参与洛杉矶一个公园更新项目，通过工作坊和 AI 图像辅助访谈观察交流过程。发现图像价值未必取决于是否逼真或完全符合提示词：某些不完美图像反而会引出更具体的空间讨论、隐藏需求和分歧。效果也强烈依赖主持人如何协调公众、设计师与 AI。它是一项真实参与过程的定性研究。

**版本与证据范围：** 上传为 arXiv 2024 v1；正式发表于 Proceedings of the ACM on Human-Computer Interaction（2025），DOI 10.1145/3710912。PDF 内 XXXXXXX 是模板占位符。

正式 DOI：[ 10.1145/3710912 ](https://doi.org/10.1145/3710912)；预印本 DOI：[ 10.48550/arXiv.2411.00949 ](https://doi.org/10.48550/arXiv.2411.00949)

[本地 PDF](</Users/edy/Documents/GitHub/DF26_ws18/research/papers/uploaded/D11_Conversational_Imperfects_BoundaryObject_arXiv.pdf>)。
[书目核查来源](https://api.crossref.org/works/10.1145%2F3710912)。

<a id="d12"></a>

### D12 · WeDesign：生成式 AI 辅助的社区公共空间咨询

**WeDesign: Generative AI-Facilitated Community Consultations for Urban Public Space Design**

Rashid Mushkani, Hugo Berard, Shin Koseki，2025；arXiv。

研究文本生成图像能否让社区咨询更容易表达、交流和迭代。作者在蒙特利尔举办半天工作坊，包含五个混合焦点小组，并访谈六位规划专业人士。实时图像鼓励创意与对话，但对行动不便者需求、地方建筑细节和双语提示的表现不足，一些图像精致却脱离场地。文章的重点是实际使用经验、表达门槛与包容性，而不是新的图像生成算法。

**版本与证据范围：** arXiv 2025；上传为 v3（2025-09-15）。五个小组不等于五位参与者。

预印本 DOI：[ 10.48550/arXiv.2508.19256 ](https://doi.org/10.48550/arXiv.2508.19256)

[本地 PDF](</Users/edy/Documents/GitHub/DF26_ws18/research/papers/uploaded/D12_WeDesign_arXiv2025.pdf>)。
[书目核查来源](https://arxiv.org/abs/2508.19256)。

<a id="e13"></a>

### E13 · 建筑遗产管理中的 AI 助手与信息检索

**New Frontiers in Built Heritage Management: AI assistant for advanced data integration and building information retrieval**

Cassia De Lian Cui, Edoardo Currà, Antonio Fioravanti, Wei Yan，2025；CAADRIA proceedings; Proceedings of the 30th Conference on Computer Aided Architectural Design Research in Asia (CAADRIA) [Volume 3]。

研究如何把历史文献等非结构化资料与遗产建筑信息模型 HBIM 连接起来，让非程序员也能查询复杂建筑知识。作者以意大利蒂沃利的赫拉克勒斯圣所和原 Segrè 造纸厂为案例，将 AI 助手用于资料访问、解释与跨专业交流，并作定性评估。重点是遗产知识管理与信息问答；实验证据来自案例的一小部分，数据准备和解释准确性仍是限制。

**版本与证据范围：** CAADRIA 2025，卷 3，121–130；不是直接生成遗产街区更新方案的系统。

正式 DOI：[ 10.52842/conf.caadria.2025.3.121 ](https://doi.org/10.52842/conf.caadria.2025.3.121)

[本地 PDF](</Users/edy/Documents/GitHub/DF26_ws18/research/papers/uploaded/E13_Built_Heritage_AI_CAADRIA2025.pdf>)。
[书目核查来源](https://api.crossref.org/works/10.52842%2Fconf.caadria.2025.3.121)。

<a id="e14"></a>

### E14 · 把人的社会性纳入行人模拟

**A Case for Socially Driven Pedestrian Simulations in Urban Environments**

Puja Bhagat, Jonathan Wong, Milad Showkatbakhsh，2026；CAADRIA 2026, Volume 3, 645–654。

研究行人为什么不总沿最短路径行走，以及人的社会行为会怎样改变空间流动。作者介绍 Grasshopper 插件 Kova PedSim，将社会性行为纳入行人模拟，并比较它与传统模拟在不同城市空间实验中的路径与涌现行为。文章强调，考虑交往倾向后，路径会更加多样，能揭示潜在聚集和未充分使用的区域。这是仿真工具研究，不能直接当作特定街区的已校准预测。

**版本与证据范围：** CAADRIA 2026，卷 3，645–654。通过上传论文和作者团队出版页核对；未找到可验证 DOI，保留为空。

DOI：**未核实，留空；不根据会议卷页推造编号。**

[本地 PDF](</Users/edy/Documents/GitHub/DF26_ws18/research/papers/uploaded/E14_Social_Pedestrian_Sim_CAADRIA2026.pdf>)。
[书目核查来源](https://www.emtech.aaschool.ac.uk/publications/)。

<a id="e15"></a>

### E15 · RAG 支持的人因导向城市微更新知识系统

**Knowledge System Construction for Human-Factors-Oriented Urban Regeneration Empowered by Retrieval-Augmented Generation: A case study of age-friendly micro-space renewal in residential communities**

Hanzhe Guo, Zhe Guo, Jinhao Xie, Xing Chen，2026；CAADRIA 2026, Volume 1, 305–314。

研究如何将分散的环境心理学、行为研究和设计指南组织成能被设计工作使用的知识。系统把文献证据整理成可检索记录，再生成有来源的设计指导，并连接更新图像和空间变化评价。作者展示上海、合肥的三个适老微更新案例，并由十位建筑专业学生和教师组成焦点组评估。文章报告初步效率和互动收益，同时承认人因证据可能冲突、依赖场景，建议不能代替设计判断。

**版本与证据范围：** CAADRIA 2026，卷 1，305–314。书目信息来自上传论文；未找到可验证 DOI，保留为空。

DOI：**未核实，留空；不根据会议卷页推造编号。**

[本地 PDF](</Users/edy/Documents/GitHub/DF26_ws18/research/papers/uploaded/E15_HumanFactors_Urban_Knowledge_CAADRIA2026.pdf>)。
上传 PDF 首页；公开标题检索及 DOI 注册服务未核实到 DOI。


## 另外补充的 5 篇

补充文献覆盖目标控制、街网生成、行人模拟、规划检索和布局优化，包含基础研究与近年 AI 研究。以下只是内容介绍。

<a id="s16"></a>

### S16 · 通过目标指标反向控制程序化城市模型

**Inverse design of urban procedural models**

Carlos A. Vanegas, Ignacio Garcia-Dorado, Daniel G. Aliaga, Bedrich Benes, Paul Waddell，2012；ACM Transactions on Graphics。

研究如何让使用者指定希望达到的结果，而不必自己调整大量底层生成参数。用户可提出日照、室内采光、到公园的距离等目标，系统反向寻找能实现目标的模型参数和城市布局。论文展示局部和整体目标下的交互编辑与多个备选结果。它连接的是高层量化目标与程序化几何模型，不涉及大语言模型或真实居民协商。

**版本与证据范围：** ACM Transactions on Graphics 31(6)，2012；作者公开稿。论文书目为 11 页，下载文件含额外页，PDF 共 12 页。

正式 DOI：[ 10.1145/2366145.2366187 ](https://doi.org/10.1145/2366145.2366187)

[本地 PDF](</Users/edy/Documents/GitHub/DF26_ws18/research/papers/additional/S16_Inverse_Design_Urban_Procedural_2012.pdf>)。
[书目核查来源](https://api.crossref.org/works/10.1145%2F2366145.2366187)。

<a id="s17"></a>

### S17 · 可交互编辑的程序化街道网络

**Interactive procedural street modeling**

Guoning Chen, Gregory Esch, Peter Wonka, Pascal Müller, Eugene Zhang，2008；ACM Transactions on Graphics。

研究怎样高效创建和修改大尺度街道网络，同时保留用户对整体方向和局部形状的控制。使用者通过笔刷、旋转、平滑和约束等操作调整方向场，系统生成相应街网，并可进一步编辑图结构、展示三维城市。它是街网程序化建模的基础论文，重点在几何控制和交互效率，并非行人交通性能的直接验证。

**版本与证据范围：** ACM Transactions on Graphics 27(3)，2008；这里记录期刊版 DOI，SIGGRAPH 收录版本可能使用不同 DOI。

正式 DOI：[ 10.1145/1360612.1360702 ](https://doi.org/10.1145/1360612.1360702)

[本地 PDF](</Users/edy/Documents/GitHub/DF26_ws18/research/papers/additional/S17_Interactive_Procedural_Street_Modeling_2008.pdf>)。
[书目核查来源](https://api.crossref.org/works/10.1145%2F1360612.1360702)。

<a id="s18"></a>

### S18 · 行人动力学的社会力模型

**Social force model for pedestrian dynamics**

Dirk Helbing, Péter Molnár，1995；Physical Review E。

研究如何用个体运动规则解释人群整体行为。模型把行人的目标速度、对他人及边界的避让、吸引作用等组织成运动动力学，展示相互作用如何产生自组织现象。它是微观行人模拟的经典基础，有助于理解“客流仿真”具体研究的对象。这里的社会力主要是行为动机的数学表示，并不等于详细模拟居民、游客的文化身份和权利关系。

**版本与证据范围：** Physical Review E 51，4282–4286，正式发表年份为 1995；不要与后来上传 arXiv 的 1998 年混淆。

正式 DOI：[ 10.1103/physreve.51.4282 ](https://doi.org/10.1103/physreve.51.4282)

[本地 PDF](</Users/edy/Documents/GitHub/DF26_ws18/research/papers/additional/S18_Social_Force_Pedestrian_Dynamics_1995.pdf>)。
[书目核查来源](https://api.crossref.org/works/10.1103%2FPhysRevE.51.4282)。

<a id="s19"></a>

### S19 · PlanGPT：面向规划专业工作的语言模型与检索

**PlanGPT: Enhancing Urban Planning with Tailored Language Model and Efficient Retrieval**

He Zhu, Wenjia Zhang, Nuoxian Huang, Boyang Li, Luyao Niu, Zipei Fan, Tianle Lun, Yicheng Tao, Junyou Su, Zhaoya Gong, Chenyu Fang, Xing Liu，2024；arXiv。

研究通用大模型在规划文本生成、资料检索和文档评价上回答不够专业的问题。作者结合规划领域资料、专门模型训练和检索工具，构建面向城市与国土空间规划工作的系统，并报告专业任务上的改善。文章聚焦知识与文本工作的准确性和效率，不是从文本直接生成三维城市。它与面向单个更新场景的人因知识系统具有不同范围。

**版本与证据范围：** arXiv 2024 预印本；此处是 PlanGPT 原论文，不是后来另行发表的 PlanGPT-VL。

预印本 DOI：[ 10.48550/arXiv.2402.19273 ](https://doi.org/10.48550/arXiv.2402.19273)

[本地 PDF](</Users/edy/Documents/GitHub/DF26_ws18/research/papers/additional/S19_PlanGPT_arXiv2024.pdf>)。
[书目核查来源](https://arxiv.org/abs/2402.19273)。

<a id="s20"></a>

### S20 · 深度强化学习驱动的城市社区空间规划

**Spatial planning of urban communities via deep reinforcement learning**

Yu Zheng, Yuming Lin, Liang Zhao, Tinghai Wu, Depeng Jin, Yong Li，2023；Nature Computational Science。

研究在不规则社区中如何自动安排土地用途与道路。作者把空间表示为图，将规划拆成连续决策，并用图神经网络和强化学习探索布局。在合成与真实社区实验中，模型在论文设定的客观指标上优于所比较的人工方案，也展示人机协作减少规划时间的可能。结论限定于相应任务和指标，不能解释成 AI 在所有城市价值判断上都优于规划师。

**版本与证据范围：** Nature Computational Science 3，748–762，2023；作者机构提供正式论文 PDF。

正式 DOI：[ 10.1038/s43588-023-00503-5 ](https://doi.org/10.1038/s43588-023-00503-5)

[本地 PDF](</Users/edy/Documents/GitHub/DF26_ws18/research/papers/additional/S20_Spatial_Planning_Deep_RL_2023.pdf>)。
[书目核查来源](https://api.crossref.org/works/10.1038%2Fs43588-023-00503-5)。

## 容易混淆的版本与结论

- A1 文件名为 arXiv2024，实际上传的是 2025 年接受稿；正式 DOI 为 10.1016/j.scs.2025.106441。
- D10 正式发表时更名，正式卷期为 2026 年，DOI 字符串中的 2025 不应直接当作卷期年份。
- D11 已正式发表于 2025 年，上传文件仍保留 2024 年预印本格式。
- B4、D11 中的 XXXXXXX DOI 与版权模板年份不进入书目。
- C6 的共同决策机制是提出的治理方案，原型演示主要是方案查看器；C7 是概念框架与早期原型。
- A2 的多用户协作、B4 的模拟居民讨论、D11/D12 的真实工作坊是三种不同证据，不能混称为“公众参与已验证”。
- E14/E15 已有会议论文 PDF，但 DOI 尚未核实。保留作者、题目、会议、卷页，后续可据此补全。

全文说明主要依据本地 PDF 的摘要及相关正文、结论/讨论；正式版本核对依据 Crossref、arXiv、作者发布页及出版商记录。没有将未阅读的正式版细节替换进上传稿内容概述。
