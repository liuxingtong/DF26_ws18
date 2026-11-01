# CAADRIA 2027 导入文件

官方要求来源：https://www.caadria2027.org/#/full-papers （核对日期 2026-11-01）。

2027 使用 ProceeDings 在线编辑系统，参考文献由系统自动排版。英文 v16 是完整阅读稿，手工参考文献仅供校对，不代表已在在线系统完成排版。

1. 核对 metadata.json 中的题名、摘要与五个关键词，更新相应投稿字段。
2. 通过 Import Text 导入 body_import.txt；跳过 Title、Authors、Abstract、Keywords、References。图表也已从这个纯正文文件分离。
3. 在 Manage References 导入 references.bib，按正文的作者—年份引用建立对应关系；没有年份的数据源保留 n.d.，不补造年份。
4. 用 Insert 添加七张图和十一张表，顺序与图注见完整英文稿和 figures_tables_placement.json；表格提供独立 CSV。
5. 导出系统预览 PDF 检查图表、引用与分页。官方接受 6、8、10 页；本地 Markdown 不能证明最终页数合规。
6. 作者资料在系统填写真实信息；官方在提交后自动执行所需匿名处理，不手工填匿名占位作者。

参考文献已按作者顺序整理，统一作者—年份写法、DOI 链接、会议录名称、卷页和机构作者。参考文献中的地图数据源已在数据说明或图注中引用。政府文件采用公布日 2023-02-10，施行日 2023-03-12 保留在记录备注中。Leong 与 Janssen 的会议论文补齐 DOI。汪明峰论文主页面末页有373–289的元数据错误，已由原始PDF核实为373–389。

尚未登录或提交 ProceeDings；最终页数与系统 Warnings 须以在线生成的 PDF 为准。

## 纯文本版本

- Dapuqiao_ProceeDings_body.txt：供 Import Text 使用的正文。使用UTF-8编码，段落之间留空行，去掉Markdown、题名、摘要、关键词、参考文献和图表内容；问题题号用Q1–Q5，避免与章节混淆。
- Dapuqiao_complete_text.txt：完整阅读/复制版，含题名、摘要、关键词、正文、制表符分隔的表格、图注及参考文献，不用于整篇一次性导入。
- title_abstract_keywords.txt：单独填写题名、摘要和关键词。
- figures_tables_text.txt：单独插入图表时复制题注和表格内容。
- equations_latex.txt：三条公式的LaTeX源；纯文本正文中保留对应的线性表达，排版时用公式源替换。

正式引用仍通过 references.bib 在 Manage References 导入并关联。
