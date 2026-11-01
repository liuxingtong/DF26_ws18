"""Assemble the final bilingual manuscript, artwork, references, and accepted PDF."""
from pathlib import Path
import re,json,csv,shutil,hashlib,zipfile
from export_proceedings_tables import BLOCK
BASE=Path(__file__).resolve().parents[1]
ROOT=BASE.parents[1]
DEST=ROOT/'research/submissions/CAADRIA2027_20261101'
DESKTOP=Path.home()/'Desktop/CAADRIA2027_最终稿_20261101'
DEST.mkdir(parents=True,exist_ok=True)
en=(BASE/'2026-11-01_Dapuqiao_CAADRIA_English_v19_Revised.md').read_text()
zh=(BASE/'2026-11-01_打浦桥_CAADRIA_中文稿_v18_精简版.md').read_text()

def para(text,start,value):
 pat=r'^'+re.escape(start)+r'[^\n]*'
 text,n=re.subn(pat,lambda m:value,text,flags=re.M);assert n==1,start
 return text

short_en='The interactive platform links scenario settings, objective trade-offs, role-based selection, and 3D building views (Figure 2). Users compare alternatives, switch roles, and inspect preferred solutions and building-level changes. Statistics summarise ten seeds, while 3D exploration uses seed 97, also used for the role comparison. Users can adjust settings and recalculate alternatives, with parameters and results saved for each run. These functions connect overall performance to specific interventions and support informed selection.'
en=para(en,'The interactive platform connects scenario settings',short_en)
# Align the Chinese manuscript with the restored introduction and explanations.
intro='''历史街区更新需要协调住房改善、开发与遗产保护。增建可能影响既有住宅，地面释放也可能改变商业活动和日常通行。因此，更新决策既涉及空间表现，也涉及居民、经营者和公共部门之间收益与代价的分配。田子坊研究将空间变化与权力关系、空间使用及改造权联系起来（Wang & Zhou, 2022）。由此产生一个计算问题：如何通过各主体可改动的建筑及其允许采取的操作，表达控制权的差异？

计算设计为生成和比较更新方案提供了工具。SIMForms连接形态生成、性能评价与可视化（Zhang et al., 2024）。参与式遗产规划通过共同设计和共同决策，让参与者介入方案形成与选择（Leong & Janssen, 2022）。土地利用优化也可以在生成备选方案后，通过利益相关者偏好引导选解（Kaim et al., 2020）。在此基础上，本研究连接两个决策阶段：权限决定可供选择的方案，角色优先级引导对这些方案的选择。研究考察建筑权限如何改变可实现的目标权衡，以及不同角色如何从同一方案集合中选择不同的建筑形态。

以上海打浦桥为例，研究在相同城市数据、评价目标和共同约束下，比较三种治理情景与参数基线。在相近净增建量下比较居住暴露，在相同暴露上限下比较开发容量。权限匹配零模型考察将近似相同的改动机会分配给不同建筑后，结果如何变化。我们还搭建了一个交互式三维平台，将这些比较与逐栋建筑变化联系起来，支持用户检查方案、切换主体视角，并讨论更新选择的空间后果。'''
a=zh.index('## 1. 引言\n\n')+len('## 1. 引言\n\n');b=zh.index('\n\n## 2. 研究区域与数据',a);zh=zh[:a]+intro+zh[b:]
zh=para(zh,'根据建筑用途和属性', '将建筑用途与属性映射为居民、开发主体和公共资产三类利益相关者标签，作为分配建筑操作权限的代理，并结合保护状态确定允许的改动。公共协调（Public Coordination，PC）、开发增长（Development Growth，DG）和居民与遗产优先（Residents and Heritage Priority，RH）在可改对象、操作类型、强度和范围上存在差异（表1）。各情景采用相同评价目标独立搜索，再依据角色偏好从各自的帕累托集合中选择代表方案。')
zh=para(zh,'六类形态操作规定', '权限通过六类形态操作落实，每类操作规定几何变化方式及其强度上限（表2）。例如，地面释放缩减建筑轮廓，并在允许范围内尝试通过增高补偿损失的建筑面积。同一次操作因此可能在释放地面的同时，增加周边更新单元内住宅的暴露。模型记录这两类变化，并将其共同影响纳入评价。')
zh=zh.replace('容积率为建筑总面积与单元面积之比', '容积率为建筑总面积（GFA）与单元面积之比')
zh=zh.replace('建筑总面积以GFA表示。','')
zh=para(zh,'其中，', r'其中，\(R\)为全部住宅建筑，\(R_{exposed}\)为符合直接或间接暴露条件的住宅，上标“base”表示现状。每栋受影响住宅的既有建筑面积仅计一次。按单元统计暴露，将改动建筑周边的住宅纳入计算，因此暴露取决于建筑变化及其所在位置。')
zh=para(zh,'同时报告新增和移除建筑面积',r'逐栋比较方案与现状建筑面积，\(A_{site}\)表示研究区域面积。同时报告新增量和移除量，因为相近的净变化可能来自差异很大的建设与移除规模。')
zh=zh.replace('NSGA-II反复生成和评价候选方案', '非支配排序遗传算法II（NSGA-II）反复生成和评价候选方案')
needle='折中方案则选择三个角色中最差名次最好的方案。';assert needle in zh
zh=zh.replace(needle,'\n\n框架还提供折中方案。先计算每个方案在三个角色下的名次，再选择最差名次最好的方案，使其在最不利角色排序下仍处于相对较好的位置，为共同讨论提供起点。')
zh=para(zh,'平台连接情景选择', '交互平台连接情景设置、目标权衡、角色选解和建筑三维视图（图2）。用户可以比较备选方案、切换角色，查看首选方案及逐栋变化。统计汇总十个种子，三维浏览采用与角色比较相同的种子97。用户可调整设置并重新计算，每次运行均保存参数与结果。这些功能将总体表现与具体改动联系起来，支持有依据的方案选择。')
zh=para(zh,'**图3.**', '**图3.** 治理前沿与BL（灰色）比较。颜色表示居住暴露，黑色轮廓标记未被BL合并前沿支配的方案。各子图采用相同坐标轴和色标。')
zh=para(zh,'**图4.**', '**图4.** 净增建筑面积比档与居住暴露上限的匹配比较。浅色点表示各种子，实线表示中位数，竖线表示种子范围。断开处表示无匹配，n标记少于十个匹配种子的条件。')
authors={'names':['Xingtong Liu','Luwei Li','Boyang Bian','Jinbao Zhong','June-Hao Hou'],'affiliations':{'1':'Tongji University','2':'Zhejiang University','3':'Suzhou University of Science and Technology','4,5':'National Yang Ming Chiao Tung University'},'emails':['liuxingtong@tongji.edu.cn','3220103760@zju.edu.cn','2446364510@qq.com','Jinbao@arch.nycu.edu.tw','jhou@arch.nycu.edu.tw'],'source':'Author information transcribed from the final supplied PDF.'}
author_block='Xingtong Liu¹, Luwei Li², Boyang Bian³, Jinbao Zhong⁴, June-Hao Hou⁵\n\n¹ Tongji University; ² Zhejiang University; ³ Suzhou University of Science and Technology; ⁴⁵ National Yang Ming Chiao Tung University\n\n¹ liuxingtong@tongji.edu.cn; ² 3220103760@zju.edu.cn; ³ 2446364510@qq.com; ⁴ Jinbao@arch.nycu.edu.tw; ⁵ jhou@arch.nycu.edu.tw'
for language,text in [('en',en),('zh',zh)]:
 text=text.replace('\n\n## ', '\n\n'+author_block+'\n\n## ',1)
 text=re.sub(r'\n{3,}','\n\n',text)
 text=re.sub(r'[ \t]+$', '',text,flags=re.M)
 (DEST/f'manuscript_{language}.md').write_text(text)
# Preserve original relative image paths so both Markdown files display without external dependencies.
paths=re.findall(r'!\[[^\]]*\]\(([^)]+)\)',en)
for path in paths:
 source=BASE/path;target=DEST/path;target.parent.mkdir(parents=True,exist_ok=True)
 shutil.copy2(source,target)
 for suffix in ['.pdf','.svg']:
  alt=source.with_suffix(suffix)
  if alt.exists():shutil.copy2(alt,target.with_suffix(suffix))
# Clear import order for the five figures and six tables.
art=DEST/'figures_for_import';art.mkdir(exist_ok=True)
for n,path in enumerate(paths,1):
 for suffix in ['.png','.pdf','.svg']:
  source=(BASE/path).with_suffix(suffix)
  if source.exists():shutil.copy2(source,art/f'Figure_{n:02d}{suffix}')
for n in range(1,7):
 for ext in ['png','pdf','csv']:
  source=BASE/'submission_caadria2027/revised_v19/tables'/f'Table_{n:02d}.{ext}'
  target=DEST/'tables'/source.name;target.parent.mkdir(exist_ok=True);shutil.copy2(source,target)
refdir=DEST/'references';refdir.mkdir(exist_ok=True)
for name in ['references.bib','reference_records.json','reference_audit.md','citation_keys.json']:
 shutil.copy2(BASE/'submission_caadria2027'/name,refdir/name)
(refdir/'references.txt').write_text(en.split('## References\n\n',1)[1])
(DEST/'authors.json').write_text(json.dumps(authors,ensure_ascii=False,indent=2)+'\n')
# Keep accepted final PDF byte-for-byte, with its supplied name.
final_pdf=Path.home()/'Desktop/caadria20271101.pdf';shutil.copy2(final_pdf,DEST/final_pdf.name)
for lang,text in [('en',en),('zh',zh)]:
 caps=re.findall(r'^\*\*(?:Figure|Table) \d+\.\*\* .+$' if lang=='en' else r'^\*\*(?:图|表)\d+\.\*\* .+$',text,re.M)
 assert len(caps)==11
 (DEST/f'captions_{lang}.txt').write_text('\n\n'.join(x.replace('**','') for x in caps)+'\n')
shutil.copy2(BASE/'submission_caadria2027/equations_latex.txt',DEST/'equations_latex.txt')
# Create a current title/abstract/keywords/body-only import file as an extra convenience.
text=en.split('## References',1)[0]
text=re.sub(r'^!\[[^\]]*\]\([^\n]+\)\n?|^\*\*(?:Figure|Table) \d+\.\*\*[^\n]*\n?|^\|.*\n?', '',text,flags=re.M)
text=re.sub(r'\\\[.*?\\\]', '',text,flags=re.S)
text=re.sub(r'^Here, [^\n]*$', 'Unit-based exposure includes housing around an intervention, so exposure depends on both the modified building and its location.',text,flags=re.M)
text=text.replace('Proposed and existing GFA are compared for each building, and \\(A_{site}\\) denotes the study area.','Proposed and existing GFA are compared for each building.')
text=text.replace('Each residential building is counted once:','Each residential building is counted once.')
text=text.replace('by study area \\(A_{site}\\):','by the study area.')
text=text.replace('by the buffer area inside the site:','by the buffer area inside the site.')
text=re.sub(r'^#{1,6}\s+','',text,flags=re.M).replace('**','')
# Authors are provided independently for submission metadata.
text=text.replace(author_block+'\n\n','')
text=re.sub(r'\n{3,}','\n\n',text).strip()+'\n'
(DEST/'ProceeDings_import_en.txt').write_text(text)
readme='''# CAADRIA 2027 最终稿归档（2026-11-01）

论文题名：Stakeholder-Driven Urban Morphology Simulation: An Interactive Computational Tool for Participatory Historic District Renewal

## 文件

- manuscript_en.md：最新版英文全文，恢复引言及方法解释，采用最后确认的精简平台段落。
- manuscript_zh.md：对应中文全文，同步相同结构、图表、方法解释及数据。
- caadria20271101.pdf：用户确认的最终10页排版PDF，原文件原样保存。
- figures/：两份Markdown引用的图片，可直接显示；统计图附PDF与SVG。
- figures_for_import/：按Figure 1–5命名的插图，Figure 3–5为扁长版。
- tables/：Table 1–6的600 dpi PNG、矢量PDF和CSV；Table 6为压缩行高版。
- references/：BibTeX、结构化引用记录、引用核查记录和参考文献文本。
- captions_en.txt、captions_zh.txt：完整图表说明。
- equations_latex.txt：三条指标公式源。
- authors.json：根据最终PDF记录的作者、单位和邮箱。
- ProceeDings_import_en.txt：含标题、摘要、关键词和正文的导入文本，不含图表内容、图表注、公式及参考文献列表。
- manifest_sha256.json：包内文件SHA-256与验证结果。

## 版本说明

中英文Markdown基于英文v19及后续确认修改同步，保留完整图注与规范数学符号，便于编辑。PDF保留用户确认的排版，不重新排版或改写。PDF与编辑源在图注长度、缩写展开及浮动位置上可能存在排版编辑差别，实验数据一致。共五张图、六张表和十一条参考文献。

数据版本为actual_geometry_v2，包含40次主搜索、90次权限匹配零模型及相应匹配和BL合并前沿结果。图表本次未重新计算实验结果。
'''
(DEST/'README.md').write_text(readme)
# Validate manuscript parity and local links.
eng=(DEST/'manuscript_en.md').read_text();chn=(DEST/'manuscript_zh.md').read_text()
assert len(BLOCK.findall(eng))==len(BLOCK.findall(chn))==6
numbers=lambda t:re.findall(r'\d+(?:[,.]\d+)*',t)
for a,b in zip(BLOCK.findall(eng),BLOCK.findall(chn)):assert numbers(a)==numbers(b)
assert eng.split('## References\n\n')[1]==chn.split('## 参考文献\n\n')[1]
assert re.findall(r'\\\[.*?\\\]',eng,re.S)==re.findall(r'\\\[.*?\\\]',chn,re.S)
assert len(re.findall(r'^!\[',eng,re.M))==len(re.findall(r'^!\[',chn,re.M))==5
for path in re.findall(r'!\[[^\]]*\]\(([^)]+)\)',eng+chn):assert (DEST/path).is_file()
assert hashlib.sha256(final_pdf.read_bytes()).hexdigest()==hashlib.sha256((DEST/final_pdf.name).read_bytes()).hexdigest()
assert not re.search(r'^\||^!\[|^\s*(?:Figure|Table) \d+\.|\\\[|\\\]|\\\(|\\\)|\\frac|\\sum',text,re.M)
assert '\nAbstract\n' in text and '\nKeywords:' in text
assert not any(ord(c)<32 and c not in '\n\t' for c in eng+chn+text)
# Embedded PDF page count is supplied by the independent PDF reader verification.
files=[]
for p in sorted(DEST.rglob('*')):
 if p.is_file() and p.name!='manifest_sha256.json':files.append({'path':p.relative_to(DEST).as_posix(),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
manifest={'version':'final_20261101','metric_version':'actual_geometry_v2','figures':5,'tables':6,'references':11,'pdf_pages':10,'validation':{'bilingual_table_numbers':'identical','equations':'identical','references':'identical','image_links':'resolved','pdf':'original bytes preserved','import_text':'title abstract keywords body; no artwork captions or formulas'},'files':files}
(DEST/'manifest_sha256.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
shutil.copytree(DEST,DESKTOP,dirs_exist_ok=True)
for p in DEST.rglob('*'):
 if p.is_file():assert p.read_bytes()==(DESKTOP/p.relative_to(DEST)).read_bytes()
zipname=DESKTOP.with_suffix('.zip')
with zipfile.ZipFile(zipname,'w',zipfile.ZIP_DEFLATED) as z:
 for p in sorted(DESKTOP.rglob('*')):
  if p.is_file():z.write(p,Path(DESKTOP.name)/p.relative_to(DESKTOP))
print(json.dumps({'folder':str(DEST),'desktop':str(DESKTOP),'zip':str(zipname),'files':len(files)+1,'size_mb':round(sum(p.stat().st_size for p in DEST.rglob('*') if p.is_file())/1024**2,2),'pdf_sha256':hashlib.sha256(final_pdf.read_bytes()).hexdigest()},ensure_ascii=False,indent=2))
