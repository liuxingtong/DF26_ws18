"""Restore explanatory paragraphs approved during review of the ProceeDings PDF."""
from pathlib import Path
import re,json,shutil,hashlib
from export_proceedings_tables import BLOCK
BASE=Path(__file__).resolve().parents[1]
OLD=BASE/'2026-11-01_Dapuqiao_CAADRIA_English_v18_Concise.md'
NEW=BASE/'2026-11-01_Dapuqiao_CAADRIA_English_v19_Revised.md'
PACK=BASE/'submission_caadria2027/revised_v19'
DESKTOP=Path.home()/'Desktop/CAADRIA2027_精简正文_v18/英文正文_v19'
old=OLD.read_text();s=old
intro='''Historic neighbourhood renewal requires coordination among housing improvement, development, and heritage conservation. Adding floor area may affect existing housing, while releasing ground space can change commercial activities and everyday access. Renewal decisions therefore concern both spatial performance and the distribution of benefits and costs among residents, businesses, and public agencies. Research in Tianzifang links spatial transformation to power relations and rights to use and modify space (Wang & Zhou, 2022). This perspective raises a computational question: how can these differences in control be represented through the buildings that each stakeholder may change and the interventions they may undertake?

Computational design provides tools for generating and comparing renewal alternatives. SIMForms connects form generation, performance evaluation, and visualisation (Zhang et al., 2024). Participatory heritage planning involves participants in developing and selecting alternatives through co-design and co-decision (Leong & Janssen, 2022). In land-use optimisation, stakeholder preferences can also guide selection after alternatives have been generated (Kaim et al., 2020). Building on these approaches, this study connects two stages of decision-making: permissions shape the alternatives available before selection, and stakeholder priorities guide the choice among those alternatives. We examine how building permissions change achievable trade-offs and how different roles select distinct building forms from the same solution set.

Using Dapuqiao, Shanghai, we compare three governance scenarios with a parametric baseline under shared urban data, evaluation objectives, and common constraints. Matched comparisons examine residential exposure at similar net additions and development capacity under equal exposure ceilings. A permission-matched null model examines how allocating comparable intervention opportunities to different buildings changes performance. We further develop an interactive 3D platform that connects these comparisons to individual building changes, enabling users to inspect alternatives, switch stakeholder perspectives, and discuss the spatial consequences of renewal choices.'''
a=s.index('## 1. Introduction\n\n')+len('## 1. Introduction\n\n');b=s.index('\n\n## 2. Study Area and Data',a)
s=s[:a]+intro+s[b:]
def replace_paragraph(start,replacement):
 global s
 matches=list(re.finditer(r'^'+re.escape(start)+r'[^\n]*(?:\n(?!\n)[^\n]+)*',s,re.M))
 assert len(matches)==1,(start,len(matches))
 m=matches[0];s=s[:m.start()]+replacement+s[m.end():]
replace_paragraph('Building uses and attributes assign', 'Building uses and attributes are mapped to three stakeholder categories: residents, developers, and public assets. These labels serve as proxies for assigning building-operation permissions and are combined with conservation status to determine permitted interventions. Public Coordination (PC), Development Growth (DG), and Residents and Heritage Priority (RH) differ in eligible buildings, operation types, intensity, and intervention extent (Table 1). Each scenario is searched independently using the same evaluation objectives. Stakeholder preferences are then applied to select representative alternatives from its resulting Pareto set.')
replace_paragraph('Six morphological operators define', 'Permissions are implemented through six morphological operators, each defining a geometric transformation and its intensity limits (Table 2). Ground release, for example, reduces a building’s footprint and attempts to compensate for lost floor area by increasing height within the available limits. The same intervention can therefore release ground space while increasing exposure for housing in the surrounding renewal unit. The model records both changes so that their combined effects enter the evaluation.')
replace_paragraph('Here, \\(R\\) contains', 'Here, \\(R\\) denotes all residential buildings, \\(R_{exposed}\\) denotes those meeting the direct or indirect exposure conditions, and the superscript “base” refers to existing conditions. Each affected building contributes its existing residential GFA once. This unit-based definition includes housing around an intervention, so exposure depends on both the modified building and its location.')
replace_paragraph('Gross additions and removals are also reported', 'Proposed and existing GFA are compared for each building, and \\(A_{site}\\) denotes the study area. Gross additions and removals are also reported because similar net changes can result from substantially different amounts of construction and removal.')
needle='A compromise solution minimises the worst rank across the three roles.'
assert s.count(needle)==1
s=s.replace(needle, '\n\nThe framework also identifies a compromise solution. Each alternative receives a rank under all three roles, and the alternative with the best worst rank is selected. This provides a starting point for discussion by favouring an alternative whose least favourable position across the three role rankings is comparatively strong.')
replace_paragraph('The platform links scenario selection', 'The interactive platform connects scenario settings, objective comparisons, role-based selection, and building form (Figure 2). Users first choose a scenario and inspect its alternatives in an objective scatter plot. They can then switch stakeholder roles to view the corresponding preferred solution and inspect its 3D form and building-level changes. The statistical panel summarises ten seeds, while 3D exploration uses seed 97, which also provides the role-comparison examples. A settings panel supports adjustment and recalculation, with parameters and results saved for each run. This sequence allows users to trace differences in overall performance to specific building interventions and explain the reasons for their selections.')
replace_paragraph('**Figure 3.**', '**Figure 3.** Governance fronts compared with BL (grey). Colour indicates residential exposure, and black outlines mark solutions not dominated by the merged BL front. All panels share the same axes and colour scale.')
replace_paragraph('**Figure 4.**', '**Figure 4.** Comparisons at matched net floor-area change bands and residential exposure ceilings. Faint points show individual seeds, solid lines indicate medians, and vertical lines show seed ranges. Gaps indicate unmatched conditions; n marks conditions with fewer than ten matching seeds.')
# Define abbreviations at their first occurrence in the methods.
s=s.replace('FAR is GFA divided by unit area;', 'FAR is gross floor area (GFA) divided by unit area;')
s=s.replace(' Gross floor area (GFA) measures building floor area.', '')
s=s.replace('NSGA-II generates and evaluates candidates,', 'The Non-dominated Sorting Genetic Algorithm II (NSGA-II) generates and evaluates candidates,')
s=re.sub(r'\n{3,}','\n\n',s)
s=re.sub(r'[ \t]+$', '',s,flags=re.M)
NEW.write_text(s)
PACK.mkdir(parents=True,exist_ok=True)
shutil.copy2(NEW,PACK/NEW.name)
oldpack=BASE/'submission_caadria2027/concise_v18'
for directory in ['figures','figures_for_import','tables','compact_figure_audit']:
 shutil.copytree(oldpack/directory,PACK/directory,dirs_exist_ok=True)
for name in ['references.bib','reference_audit.md','equations_latex.txt','metadata.json','title_abstract_keywords.txt']:
 shutil.copy2(oldpack/name,PACK/name)
cap_matches=list(re.finditer(r'^\*\*(Figure|Table) (\d+)\.\*\* (.+)$',s,re.M))
(PACK/'captions_v19.txt').write_text('\n\n'.join(m[0].replace('**','') for m in cap_matches)+'\n')
placements=[]
for m in cap_matches:
 typ,n,cap=m[1],int(m[2]),m[3]
 placements.append({'type':typ.lower(),'number':n,'file':f'figures_for_import/Figure_{n:02d}.png' if typ=='Figure' else f'tables/Table_{n:02d}.png','caption':cap})
(PACK/'figures_tables_placement.json').write_text(json.dumps(placements,ensure_ascii=False,indent=2)+'\n')
# User-requested import: title, abstract, keywords and body; no equations or figure/table content/captions.
text=s.split('## References',1)[0]
text=re.sub(r'^!\[[^\]]*\]\([^\n]+\)\n?', '',text,flags=re.M)
text=re.sub(r'^\*\*(?:Figure|Table) \d+\.\*\*[^\n]*\n?', '',text,flags=re.M)
text=re.sub(r'^\|.*\n?', '',text,flags=re.M)
text,n=re.subn(r'\\\[.*?\\\]', '',text,flags=re.S);assert n==3
# These explanations accompany the displayed equations in the full manuscript.
# Retain their substantive meaning, but remove formula-dependent symbol definitions from import text.
text=re.sub(r'^Here, [^\n]*$', 'Unit-based exposure includes housing around an intervention, so exposure depends on both the modified building and its location.',text,flags=re.M)
text=text.replace('Proposed and existing GFA are compared for each building, and \\(A_{site}\\) denotes the study area.', 'Proposed and existing GFA are compared for each building.')
text=text.replace('Each residential building is counted once:', 'Each residential building is counted once.')
text=text.replace('**Net floor-area change** divides proposed minus existing GFA by study area \\(A_{site}\\):', '**Net floor-area change** divides proposed minus existing GFA by the study area.')
text=text.replace('**Street-adjacent ground release** divides released footprint area within the 5 m street buffer by the buffer area inside the site:', '**Street-adjacent ground release** divides released footprint area within the 5 m street buffer by the buffer area inside the site.')
text=re.sub(r'^#{1,6}\s+','',text,flags=re.M).replace('**','')
text=re.sub(r'\n{3,}','\n\n',text).strip()+'\n'
(PACK/'Dapuqiao_ProceeDings_import_v19.txt').write_text(text)
full=s
for m in list(BLOCK.finditer(full))[::-1]:
 rows=[line.strip().strip('|').split('|') for line in m[0].strip().splitlines()]
 body='\n'.join('\t'.join(c.strip() for c in row) for i,row in enumerate(rows) if i!=1)+'\n'
 full=full[:m.start()]+body+full[m.end():]
full=re.sub(r'^!\[([^\]]*)\]\(([^)]+)\)',r'[Image: \2]',full,flags=re.M)
full=re.sub(r'^#{1,6}\s+','',full,flags=re.M).replace('**','')
(PACK/'Dapuqiao_complete_text_v19.txt').write_text(full)
count=lambda t:len(re.findall(r"\b[\w]+(?:[’-][\w]+)*\b",t))
report={'source':OLD.name,'revision':NEW.name,'word_count_before':count(old),'word_count_after':count(s),'figures':5,'tables':6,'data_recalculated':False,'changes':['Restored introduction and method explanations','Clarified compromise selection and platform workflow','Restored figure 3 and 4 captions','Defined FAR, GFA and NSGA-II','Retained compact figure layouts']}
(PACK/'revision_summary.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
(PACK/'README.md').write_text('''# 英文正文 v19

根据2026-11-01对caadria2027test.pdf的审阅恢复说明。保留六张表、五张扁长版图片及全部实验数字。

- 2026-11-01_Dapuqiao_CAADRIA_English_v19_Revised.md：完整英文正文，含公式与图表。
- Dapuqiao_ProceeDings_import_v19.txt：当前推荐导入文本，含标题、摘要、关键词和正文；不含图表内容、图注、表注、公式或参考文献列表。
- Dapuqiao_complete_text_v19.txt：完整阅读文本，保留图注、表格和公式源。
- captions_v19.txt：单独录入的完整图表说明，地图来源及图3、4读图说明均已保留。
- figures_for_import：按正文图号命名的五张图，图3–5为扁长版。
- tables：六张表的PNG、PDF与CSV。
- equations_latex.txt：单独录入的三条公式。
- references.bib：沿用已核验文献，参考文献通过系统单独管理。

在线排版时：图2及其图注置于3.5末、4.Results之前；表6及表注置于4.2内、5.Discussion之前。图5在PDF中的逐栋变化偏小，可适度放大显示。原PDF未被修改，新稿的实际页数需重新生成预览核对。
''')
# Validate before copying into the review folder.
assert BLOCK.findall(old)==BLOCK.findall(s)
assert old.split('## References')[1]==s.split('## References')[1]
assert old.split('## 4. Results')[1].split('## References')[0].replace(re.search(r'^\*\*Figure 3\.\*\*.*$',old,re.M)[0],'').replace(re.search(r'^\*\*Figure 4\.\*\*.*$',old,re.M)[0],'')==s.split('## 4. Results')[1].split('## References')[0].replace(re.search(r'^\*\*Figure 3\.\*\*.*$',s,re.M)[0],'').replace(re.search(r'^\*\*Figure 4\.\*\*.*$',s,re.M)[0],'')
assert re.findall(r'\\\[.*?\\\]',old,re.S)==re.findall(r'\\\[.*?\\\]',s,re.S)
assert len(cap_matches)==11
for typ,total in [('Figure',5),('Table',6)]:assert set(map(int,re.findall(r'\b'+typ+r' (\d+)',s)))==set(range(1,total+1))
assert s.index('**Figure 2.**')<s.index('## 4. Results')
assert s.index('**Table 6.**')<s.index('## 5. Discussion')
assert text.startswith('Stakeholder-Driven Urban Morphology Simulation:')
assert '\nAbstract\n' in text and '\nKeywords:' in text
assert not re.search(r'^\||^!\[|^#{1,6}\s|^\s*(?:Figure|Table) \d+\.|\\\[|\\\]|\\\(|\\\)|\\frac|\\sum|\\cap|f[123]\s*=',text,re.M)
assert not any(ord(c)<32 and c not in '\n\t' for c in s+text)
shutil.copytree(PACK,DESKTOP,dirs_exist_ok=True)
for p in PACK.rglob('*'):
 if p.is_file():assert hashlib.sha256(p.read_bytes()).digest()==hashlib.sha256((DESKTOP/p.relative_to(PACK)).read_bytes()).digest()
print(json.dumps(report,indent=2));print(DESKTOP)
