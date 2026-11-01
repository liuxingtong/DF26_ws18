"""Prepare a concise six-table, five-figure manuscript and standalone import pack."""
from pathlib import Path
import re, json, shutil, csv, hashlib
from export_proceedings_tables import tables

BASE=Path(__file__).resolve().parents[1]
OLD=BASE/'2026-11-01_Dapuqiao_CAADRIA_English_v17_Compact_Tables.md'
NEW=BASE/'2026-11-01_Dapuqiao_CAADRIA_English_v18_Concise.md'
PACK=BASE/'submission_caadria2027/concise_v18'
DESKTOP=Path.home()/'Desktop/CAADRIA2027_精简正文_v18'
s=OLD.read_text(); ts=tables(s)
refs=s.split('## References\n\n',1)[1]
title=s.splitlines()[0].lstrip('# ')
images={1:'figures/fig1_study_area_stakeholders.png',2:'figures/exposure_v2/interactive_platform.png',3:'figures/exposure_v2/fig3_merged_pareto_fronts.png',4:'figures/exposure_v2/fig4_e6_matched_tradeoffs.png',5:'figures/exposure_v2/fig6_role_picks_exposure_v2.png'}

def table(n,caption):
 return f'**Table {n}.** {caption}\n\n'+ts[n-1]['block'].strip()

def figure(n,alt,caption):
 return f'![{alt}]({images[n]})\n\n**Figure {n}.** {caption}'

abstract='''Historic neighbourhood renewal requires coordination among housing, development, and heritage conservation. This study links stakeholder categories to building-operation permissions in a model of 1,370 buildings in Dapuqiao, Shanghai. NSGA-II searches a parametric baseline and three governance scenarios using common constraints and objectives for residential exposure, net floor-area change, and street-adjacent ground release. Stakeholder priorities then select representative alternatives. Across ten paired seeds, median minimum exposure at the 0.2% net floor-area change band is 16.41% for the baseline, 2.21% for public coordination, and 1.65% for development growth. The baseline provides greater capacity at higher exposure ceilings, while some governance solutions remain undominated by its merged front. Randomised permissions change performance in different directions across scenarios. An interactive 3D platform connects these trade-offs to individual building changes. Three participants with architecture or planning backgrounds rated its support for understanding permissions and role-based selection more highly than its explanation of objective trade-offs.'''
keywords='Urban Renewal, Heritage Conservation, Multiobjective Optimisation, Stakeholders, Participatory Planning'
parts=[f'# {title}',f'## Abstract\n\n{abstract}',f'**Keywords:** {keywords}', '''## 1. Introduction

Historic neighbourhood renewal combines housing improvement, development, and conservation. These aims distribute benefits and costs differently among residents, businesses, and public agencies. Research in Tianzifang links spatial transformation to power relations and rights to use and modify space (Wang & Zhou, 2022). A computational renewal model therefore needs to represent who may change which buildings, as well as the performance of the resulting forms.

Generative tools such as SIMForms connect form generation, evaluation, and visualisation (Zhang et al., 2024). Participatory heritage planning uses co-design and co-decision to develop and select alternatives (Leong & Janssen, 2022), while land-use optimisation can apply stakeholder preferences after generating solutions (Kaim et al., 2020). This study connects permissions before generation with preferences after generation. It asks: how do building permissions change achievable trade-offs, and how do stakeholder priorities select different forms from the same alternatives?

We compare three governance scenarios with a parametric baseline, using shared urban data, constraints, and objectives. Matched comparisons examine residential exposure at similar additions and capacity under equal exposure ceilings. A permission-matched null model tests the allocation of intervention opportunities. A 3D platform makes the resulting building changes available for inspection and discussion.''', '''## 2. Study Area and Data

The study covers Tianzifang and surrounding neighbourhoods in Dapuqiao, Shanghai, where Shikumen housing, former factories, and commercial uses coexist. Huangpu District's management measures call for distinctive-building conservation, factory reuse, community facilities, safety improvements, and coordination of residential and commercial uses (Huangpu District People's Government, 2023).

The model integrates footprints, heights, uses, streets, and conservation records for 1,370 buildings. Building and street data come from OpenStreetMap contributors (n.d.). Streets define 38 renewal units. A building is assigned to a unit when an interior representative point falls within its boundary; building and unit IDs link geometry to controls. The 32 unassigned buildings and 21 footprints matched to official conservation records remain unchanged. Areas and distances use projected coordinates. All experiments use the same inputs.''',figure(1,'Study area and stakeholder labels.', 'Study area, imagery, and stakeholder labels. Black outlines mark protected buildings; purple outlines mark unassigned buildings. Sources: OpenFreeMap (n.d.), Esri (n.d.), and EOX IT Services GmbH (n.d.).'),'''## 3. Methods

### 3.1 Permissions and Form Generation

Building uses and attributes assign three stakeholder labels: residents, developers, and public assets. These labels act as proxies for operation permissions. Public Coordination (PC), Development Growth (DG), and Residents and Heritage Priority (RH) differ in eligible buildings, operators, intensity, and intervention extent (Table 1). Each scenario generates alternatives independently; stakeholder preferences are applied after the search.''',table(1,'Governance scenarios. Protected and unknown-label buildings remain unchanged in all three.'),'''Six morphological operators define geometric transformations and intensity limits (Table 2). Ground release, for example, reduces the footprint and attempts height compensation within the remaining capacity.''',table(2,'Morphological operators and controls.'),r'''Candidates must satisfy geometry validity, study boundaries, building conservation, height, unit floor area ratio (FAR), coverage, residential retention, and overlap checks. FAR is GFA divided by unit area; coverage is footprint area divided by unit area. Permissions and intervention extent depend on the scenario. The program reduces operation intensity to available capacity, rejects remaining violations, and records each modified building's ID, unit, operator, intensity, and before-and-after attributes.

### 3.2 Evaluation Objectives

Three objectives measure residential exposure (minimise), net floor-area change (maximise), and street-adjacent ground release (maximise). Gross floor area (GFA) measures building floor area.

**Residential exposure** is the share of existing residential GFA affected directly or indirectly. Direct exposure occurs when a residential building changes height by at least 0.1 m or footprint by at least 1 m². Indirect exposure includes housing in any unit where a building gains at least 0.1 m in height or increases its number of connected volumes of at least 1 m². Height compensation during ground release follows this rule. Each residential building is counted once:

\[
f_1 = \frac{\sum_{i \in R_{exposed}} GFA_i^{base}}{\sum_{i \in R} GFA_i^{base}}
\]

Here, \(R\) contains all residential buildings and \(R_{exposed}\) those meeting the exposure conditions. Unit-wide exposure includes housing surrounding an intervention.

**Net floor-area change** divides proposed minus existing GFA by study area \(A_{site}\):

\[
f_2 = \frac{\sum_i (GFA_i^{proposal}-GFA_i^{base})}{A_{site}}
\]

Gross additions and removals are also reported to distinguish alternatives with similar net values.

**Street-adjacent ground release** divides released footprint area within the 5 m street buffer by the buffer area inside the site:

\[
f_3 = \frac{Area[(Footprint_{base}-Footprint_{proposal}) \cap StreetBuffer_{5m}]}{Area(StreetBuffer_{5m} \cap Site)}
\]

### 3.3 Search and Role-Based Selection

NSGA-II generates and evaluates candidates, retaining alternatives with different objective trade-offs (Deb et al., 2002). A candidate dominates another when it is at least as good on every objective and better on at least one; the Pareto set contains undominated candidates. Epsilon tolerances group solutions with small objective differences after the search.

Roles rank this set in priority order. Residents prioritise lower exposure, greater net floor-area change, then greater ground release. Development prioritises greater net floor-area change, greater ground release, then lower exposure. Public planning prioritises greater ground release, lower exposure, then greater net floor-area change. Comparison moves to the next objective when values differ by less than its epsilon tolerance. A compromise solution minimises the worst rank across the three roles.

### 3.4 Experimental Design

The Parametric Baseline (BL) adjusts height by multipliers of 1.00–1.30 and retains 0.75–1.00 of each footprint. PC, DG, and RH use the permissions and operators above. Common model limits are 36 m height, unit FAR 3.0, coverage 0.60, and residential GFA retention 0.80. Height, FAR, and coverage limits take the larger of the specified and existing values.

Each method is searched with a population of 40, 50 planned generations, ten paired seeds, and a fixed budget of 2,000 raw evaluations per run. Effective evaluations count distinct forms with actual changes. Feasibility is the proportion of recorded candidates satisfying all constraints, including the existing model in the candidate count. Hypervolume measures the objective space dominated by a front, using shared normalisation and reference points (Zitzler & Thiele, 1999). Statistics report seed medians and ranges. Table 3 summarises the analyses: E0, E1, and E6 provide the reported comparisons; E2–E3 document labels and constraints, and E4–E5 specify follow-up analyses.''',table(3,'Experimental comparisons and questions. E4–E5 are follow-up analyses.'),'''The permission-matched null model uses ten random permission tables for each governance scenario and paired seeds 11, 23, and 37: 90 searches at the main experiment's budget. Randomisation preserves each operator's eligible-building count per unit and matches eligible existing GFA within 5%. Residential labels, conservation, intensity, and intervention extent remain fixed. Null-model hypervolume uses shared bounds across all 130 runs. Paired differences are randomised minus original permissions, summarised first by the median of three seeds per table, then by the median of ten tables.

Matched net floor-area bands use ±0.05 percentage points. For each seed, we record minimum exposure in each band and maximum net floor-area change under each exposure ceiling, then summarise seed medians and matching counts. Unmatched conditions remain missing. For dominance analysis, all ten BL fronts are merged and filtered into one reference front.

### 3.5 Interactive Platform

The platform links scenario selection, objective scatter plots, role rankings, and 3D building views (Figure 2). Statistics summarise ten seeds; 3D exploration uses seed 97, also used for the role comparison. Users select a scenario, inspect trade-offs, switch roles, and open a solution's form and building-level change records. Adjustable scenario settings support recalculation and comparison, with settings and results saved for each run.''',figure(2,'Interactive 3D platform.','Platform interface linking scenarios, stakeholder roles, objective trade-offs, and building form.'),'''## 4. Results

### 4.1 Alternative Performance

The four methods completed 40 searches of 2,000 raw evaluations each (Table 4).''',table(4,'Ten-seed results. Effective evaluations, Pareto counts, and maximum net floor-area change show ranges; other columns show medians.'),'''The merged BL reference contains 398 non-dominated points. Median proportions of governance solutions undominated by BL are 42.37% for PC (range 27.78–46.67%), 33.33% for DG (15.38–55.56%), and 57.14% for RH (36.36–90.00%) (Figure 3).''',figure(3,'Governance fronts against the merged baseline.','Governance fronts against BL (grey). Colour indicates exposure; black outlines mark solutions undominated by BL. Axes and colour scales are shared.'),'''At the 0.2% addition band, median minimum exposure is 16.41% for BL, 2.21% for PC, and 1.65% for DG, with matches in all ten seeds; RH has no match. Under a 20% exposure ceiling, median maximum net floor-area change is 6.776%, 0.657%, 1.232%, and 0.000%, respectively (Figure 4).''',figure(4,'Matched benefit and exposure comparisons.','Matched addition bands and exposure ceilings. Faint points show seeds, solid lines medians, and vertical lines ranges. Gaps indicate no matches; n marks fewer than ten matching seeds.'),'''The permission-matched null model yields median paired hypervolume differences of −0.01378 for PC, +0.01030 for DG, and +0.00016 for RH. At the 0.2% addition band, paired exposure differences are +0.96 percentage points for PC and −10.59 for DG; RH has no match. Original DG exposure in the three paired seeds is 12.32%, 12.24%, and 1.65%.

Within PC seed 97, resident and development roles select net additions of 1,585 and 9,892 m², with exposure of 0.00% and 6.36%. Public planning selects a net reduction of 70,089 m² and ground release of 0.322% (Figure 5; Table 5).''',figure(5,'Three role-preferred building alternatives.','PC seed 97 role-preferred alternatives, shown at identical projection and extent. Modified buildings are coloured by operator; charts show net GFA change by stakeholder category.'),table(5,'Role-preferred solutions, PC seed 97.'),'''### 4.2 Platform Evaluation

Three participants with architecture or planning backgrounds compared PC and DG near a specified net floor-area change, switched resident and development perspectives, and selected alternatives. They then rated five statements from 1 (strongly disagree) to 5 (strongly agree):

Q1. I can understand which buildings may be modified under each scenario.

Q2. I can understand the trade-offs among capacity, residential exposure, and street-adjacent ground release.

Q3. I can understand why switching roles changes the selected solution.

Q4. I can compare two solutions using the charts and 3D views.

Q5. The platform helps me select a solution and explain my reasons.''',table(6,'Participant ratings. Q1–Q5 correspond to the statements above.'),'''The overall mean was 4.33. Understanding permissions and role-based selection each scored 4.67; understanding objective trade-offs scored 3.67.

## 5. Discussion

Permissions change the spatial cost of additions. PC and DG meet the low addition target with less exposed housing than BL, while BL obtains substantially more capacity once the exposure ceiling rises. This crossover identifies a planning choice between limiting the affected residential area and allowing broader transformation. Unit-based exposure makes intervention location consequential: adding height in a unit can expose surrounding housing even when residential buildings themselves remain unchanged.

The governance fronts preserve objective combinations undominated by BL, including RH alternatives centred on ground release rather than additions. Their value lies in the combination of residential exposure, capacity, and released space. Comparing only maximum additions or aggregate hypervolume would obscure these alternatives.

Randomising comparable permission opportunities helps interpret this mechanism. Original PC permissions outperform random allocation in hypervolume and matched exposure, whereas DG changes in the opposite direction and RH changes little. Stakeholder assignment therefore interacts with each scenario's operators and constraints. For DG, the difference between its three-seed and ten-seed exposure results also shows why the distribution of search outcomes matters when choosing an alternative.

Role selection makes a second decision within the generated space. The public-planning choice exchanges considerable floor area for ground release, while the resident and development choices retain additions with different exposure levels. Displaying gross additions, removals, and individual building changes makes that exchange visible. Participants found permissions and role switching easier to understand than objective trade-offs, suggesting that the platform should explain the capacity–exposure–release relationship more directly.

## 6. Conclusion

The framework connects stakeholder labels to building permissions, multiobjective form generation, and role-based selection. Matched comparisons reveal lower-exposure addition opportunities under PC and DG and greater capacity under BL at higher exposure ceilings. Permission randomisation shows scenario-specific effects, while the merged-front analysis identifies governance alternatives with distinct objective combinations. The 3D platform connects these choices to building changes, supporting discussion of renewal benefits and residential costs.''','## References\n\n'+refs.strip()]
new='\n\n'.join(parts)+'\n'
NEW.write_text(new)
PACK.mkdir(parents=True,exist_ok=True)
shutil.copy2(NEW,PACK/NEW.name)
for number,path in images.items():
 target=PACK/path;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(BASE/path,target)
 # Numbered copies make the import order explicit.
 target=PACK/'figures_for_import'/f'Figure_{number:02d}.png';target.parent.mkdir(exist_ok=True);shutil.copy2(BASE/path,target)
for n in range(1,7):
 for ext in ['png','pdf','csv']:
  src=BASE/'submission_caadria2027/tables_png_20261101'/f'Table_{n:02d}.{ext}'
  target=PACK/'tables'/src.name;target.parent.mkdir(exist_ok=True);shutil.copy2(src,target)

captions=re.findall(r'^\*\*(?:Figure|Table) \d+\.\*\* .+$',new,re.M)
(PACK/'captions.txt').write_text('\n\n'.join(x.replace('**','') for x in captions)+'\n')
(PACK/'title_abstract_keywords.txt').write_text(f'{title}\n\n{abstract}\n\n{keywords}\n')
metadata=json.loads((BASE/'submission_caadria2027/metadata.json').read_text())
metadata['abstract']=abstract
(PACK/'metadata.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2)+'\n')
for f in ['references.bib','reference_audit.md','equations_latex.txt']:
 shutil.copy2(BASE/'submission_caadria2027'/f,PACK/f)

# Plain text: no title, abstract, references, image/table bodies, or captions in the Import Text file.
body=new[new.index('## 1. Introduction'):new.index('## References')]
body=re.sub(r'^\|.*\n?', '', body, flags=re.M)
body=re.sub(r'^!\[[^\]]*\]\([^\n]+\)\n?', '', body, flags=re.M)
body=re.sub(r'^\*\*(?:Table|Figure) \d+\.\*\* .+\n?', '', body, flags=re.M)
equations=re.findall(r'\\\[\n(.*?)\n\\\]',new,re.S)
linear=[
'f1 = sum(existing GFA of exposed residential buildings) / sum(existing GFA of all residential buildings)',
'f2 = sum(proposed GFA - existing GFA) / site area',
'f3 = area of released footprint within the 5 m street buffer / area of the street buffer within the site']
for eq,lin in zip(equations,linear): body=body.replace('\\[\n'+eq+'\n\\]',lin)
body=re.sub(r'^#{1,6}\s+', '',body,flags=re.M).replace('**','')
body=body.replace('\\(','').replace('\\)','')
body=re.sub(r'\n{3,}','\n\n',body).strip()+'\n'
(PACK/'Dapuqiao_ProceeDings_body_v18.txt').write_text(body)
full=new
for m in list(re.finditer(r'^\|[^\n]+\n\|[-: |]+\n(?:\|[^\n]+\n?)+',full,re.M))[::-1]:
 rows=[line.strip().strip('|').split('|') for line in m[0].strip().splitlines()]
 text='\n'.join('\t'.join(c.strip() for c in row) for i,row in enumerate(rows) if i!=1)+'\n'
 full=full[:m.start()]+text+full[m.end():]
full=re.sub(r'^!\[([^\]]*)\]\(([^)]+)\)',r'[Image: \2]',full,flags=re.M)
full=re.sub(r'^#{1,6}\s+','',full,flags=re.M).replace('**','')
(PACK/'Dapuqiao_complete_text_v18.txt').write_text(full)
placements=[]
for m in re.finditer(r'^\*\*(Figure|Table) (\d+)\.\*\* (.+)$',new,re.M):
 typ,n,cap=m[1],int(m[2]),m[3]
 path=f'figures_for_import/Figure_{n:02d}.png' if typ=='Figure' else f'tables/Table_{n:02d}.png'
 placements.append({'type':typ.lower(),'number':n,'file':path,'caption':cap})
(PACK/'figures_tables_placement.json').write_text(json.dumps(placements,ensure_ascii=False,indent=2))
words=lambda text:len(re.findall(r"\b[\w]+(?:[’-][\w]+)*\b",text))
prose=lambda text:re.sub(r'^\|.*$|^!.*$|^\*\*(?:Table|Figure).*$', '',text.split('## References')[0],flags=re.M)
report={'source':OLD.name,'draft':NEW.name,'all_words_before':words(s),'all_words_after':words(new),'prose_words_before':words(prose(s)),'prose_words_after':words(prose(new)),'figures_before':7,'figures_after':5,'tables':6,'removed_figures':['research_workflow.png','fig5_permission_null.png'],'numerical_results_recalculated':False}
(PACK/'revision_summary.json').write_text(json.dumps(report,indent=2)+'\n')
notes=f'''# v18 精简正文与导入文件

当前稿：{NEW.name}。六张表，五张图。英文总字词数按统一程序从{report['all_words_before']}降至{report['all_words_after']}，正文叙述从{report['prose_words_before']}降至{report['prose_words_after']}（不含图表及参考文献）。未重新计算实验结果。

- Dapuqiao_ProceeDings_body_v18.txt：Import Text用的纯正文，题名、摘要、关键词、图表和参考文献分别导入。
- Dapuqiao_complete_text_v18.txt：完整阅读版，含六张表、五张图注和参考文献。
- title_abstract_keywords.txt：题名、摘要、关键词。
- captions.txt及figures_tables_placement.json：新的插图顺序和图表说明。
- figures_for_import：仅五张正文图片，按新图号命名。
- tables：沿用六张表的600 dpi PNG、PDF和CSV。
- figures：供Markdown阅读稿正常显示图片。
- references.bib：沿用已核对文献。在线系统中将EOX、Esri、OpenFreeMap和OpenStreetMap四条无年份来源设为Webpage；不要补造年份。

删减内容：流程图改为方法叙述；零模型图改为结果段中的数值报告。压缩背景、流程、算子解释、平台说明和图注；讨论减少重复数字，保留空间代价、容量与暴露的交叉关系、权限分配及角色选择的解释。正文中继续明确E4–E5为后续分析。

图号对应：新图1=原图1；新图2=原图3；新图3=原图4；新图4=原图5；新图5=原图7。表号维持六表版不变。

这里未生成ProceeDings排版PDF，减少的实际页数需在系统预览中核对；优先保留新图3–5和表4–6的可读性。
'''
(PACK/'README.md').write_text(notes)
shutil.copytree(PACK,DESKTOP,dirs_exist_ok=True)
# Validate the source, identifiers, inputs, and desktop copies.
assert len(tables(new))==6
assert len(re.findall(r'^!\[',new,re.M))==5
for typ,count in [('Table',6),('Figure',5)]:
 assert sorted(set(map(int,re.findall(r'\b'+typ+r' (\d+)',new))))==list(range(1,count+1))
for a,b in zip(ts,tables(new)): assert a['rows']==b['rows'] and a['headers']==b['headers']
assert new.split('## References\n\n',1)[1].strip()==refs.strip()
assert len(equations)==3
assert not any(ord(c)<32 and c not in '\n\t' for c in new)
assert not re.search(r'^#|^\||^!\[|^\*\*(?:Table|Figure)',body,re.M)
for p in PACK.rglob('*'):
 if p.is_file(): assert hashlib.sha256(p.read_bytes()).digest()==hashlib.sha256((DESKTOP/p.relative_to(PACK)).read_bytes()).digest()
print(json.dumps(report,indent=2))
print(DESKTOP)
