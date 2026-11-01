"""Render paper tables at physical print size and prepare a reduced-table draft."""
from pathlib import Path
import re, csv, json, shutil, hashlib
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
from PIL import Image, ImageOps, ImageDraw

BASE = Path(__file__).resolve().parents[1]
SOURCE = BASE / '2026-11-01_Dapuqiao_CAADRIA_English_v16_ProceeDings.md'
OUT = BASE / 'submission_caadria2027/tables_png_20261101'
DESKTOP = Path.home() / 'Desktop/CAADRIA2027_正文表格'
DRAFT = BASE / '2026-11-01_Dapuqiao_CAADRIA_English_v17_Compact_Tables.md'
KEEP = [1, 2, 4, 5, 10, 11]
NUMBER = {old: new for new, old in enumerate(KEEP, 1)}
BLOCK = re.compile(r'^\|[^\n]+\n\|[-: |]+\n(?:\|[^\n]+\n?)+', re.M)
CAP = re.compile(r'^\*\*Table (\d+)\.\*\* (.+)$', re.M)


def tables(text):
    blocks = list(BLOCK.finditer(text))
    captions = list(CAP.finditer(text))
    assert len(blocks) == len(captions)
    result = []
    for i, (block, cap) in enumerate(zip(blocks, captions), 1):
        assert int(cap[1]) == i
        rows = [[c.strip() for c in line.strip().strip('|').split('|')] for line in block[0].strip().splitlines()]
        assert all(len(r) == len(rows[0]) for r in rows)
        result.append({'number': i, 'caption': cap[2], 'headers': rows[0], 'rows': rows[2:], 'block': block[0], 'caption_block': cap[0]})
    return result


def compact(text, original):
    # Preserve all data in the original-table archive; remove duplicated tables from the new draft.
    for old in [3, 6, 7, 8, 9]:
        t = original[old - 1]
        text = text.replace(t['block'], '').replace(t['caption_block'], '')
    start = 'Role-based selection compares objectives in priority order.'
    end = 'The framework also identifies a compromise solution.'
    a, b = text.index(start), text.index(end)
    text = text[:a] + ('Role-based selection compares objectives in priority order. Residents prioritise lower residential exposure, then greater net floor-area change, then greater ground release. Development prioritises greater net floor-area change, then greater ground release, then lower exposure. Public planning prioritises greater ground release, then lower exposure, then greater net floor-area change. When values on one objective fall within its epsilon tolerance, comparison proceeds to the next objective.\n\n') + text[b:]
    text = text.replace('Merging the ten BL fronts produces 398 non-dominated points. Table 8 reports the proportion of each governance front that remains undominated by this merged reference, calculated separately for each seed.', 'Merging the ten BL fronts produces 398 non-dominated points. Figure 4 shows the governance solutions against this reference; Figure 5 compares matched net floor-area change and exposure ceilings.')
    text = text.replace('All panels share the same axes and colour scale.', 'All panels share the same axes and colour scale. Across ten seeds, the median proportions not dominated by BL are 42.37% for PC (27.78–46.67%), 33.33% for DG (15.38–55.56%), and 57.14% for RH (36.36–90.00%).')
    text = text.replace('Lines break at missing conditions; n indicates conditions with fewer than ten matching seeds.', 'Lines break at missing conditions; n indicates conditions with fewer than ten matching seeds. At the 0.2% addition band, median minimum exposure is 16.41% for BL, 2.21% for PC, and 1.65% for DG, each with ten matching seeds; RH has no match. Under the 20% exposure ceiling, median maximum net floor-area change is 6.776%, 0.657%, 1.232%, and 0.000%, respectively.')
    text = text.replace('Positive-addition matches for RH remain missing.', 'Positive-addition matches for RH remain missing. Median paired hypervolume differences (randomised minus original permissions) are −0.01378 for PC, +0.01030 for DG, and +0.00016 for RH. At the 0.2% addition band, paired exposure differences are +0.96 percentage points for PC and −10.59 for DG.')
    # Condense experimental design without changing its scope or follow-up status.
    exp = '''| Experiment | Comparison or calculation | Research question |
|---|---|---|
| E0 Main comparison | Four methods; shared data, objectives, constraints, budget, and ten paired seeds | Which capacity, exposure, and ground-release combinations are produced? |
| E1 Permission test | Randomise permissions within units; retain eligible counts and approximately match eligible GFA | Does permission location change the Pareto front? |
| E2 Label statistics | Label rules, counts, areas, unknown labels, and label perturbation | Which buildings receive labels and interventions? |
| E3 Constraint statistics | Intensity reductions and rejections by method, seed, and constraint | Which controls restrict candidate generation? |
| E4 Exposure scale | Recalculate the same alternatives using 25, 50, and 100 m distances | How does spatial scale change exposure and rankings? |
| E5 Selection tolerance | Refilter and rerank with epsilon multiplied by 0.5 and 2 | How does tolerance change preferred solutions? |
| E6 Matched comparison | Net-addition bands, exposure ceilings, and merged BL front | How do benefits and costs compare under matched conditions? |
'''
    text = text.replace(original[3]['block'], exp)
    # Remove repeated freeze rule from scenario rows and state it once in the caption.
    scenario = '''| Scenario | Intervention focus | Main restrictions |
|---|---|---|
| PC | Limited additions, ground release, and height redistribution on developer-labelled buildings; setbacks on public assets; access improvements for residents | Protected buildings and unknown-label buildings remain unchanged |
| DG | Additions, ground release, and volume splitting on developer-labelled buildings | Residential buildings allow only low-intensity access improvements |
| RH | Ground release or height redistribution on developer-labelled buildings; low-intensity improvements to public assets and housing | Intensive residential modifications are restricted |
'''
    text = text.replace(original[0]['block'], scenario)
    text = text.replace('Intervention focus and restrictions of the three governance scenarios.', 'Intervention focus and restrictions of the three governance scenarios. Protected buildings and buildings with unknown stakeholder labels remain unchanged in all scenarios.')
    # Shorten headers, retaining all numerical cells.
    replacements = {
        '| Method | Effective evaluations | Feasibility ratio | Pareto solutions | Hypervolume | Maximum net floor-area change | Maximum ground release |': '| Method | Effective evaluations | Feasibility ratio | Pareto solutions | Hypervolume | Max. net floor-area change (%) | Max. ground release (%) |',
        '| Role | Solution ID | Residential exposure (%) | Net floor-area change (m²) | Additions (m²) | Removals (m²) | Ground release (%) |': '| Role | Solution ID | Exposure (%) | Net GFA change (m²) | Added GFA (m²) | Removed GFA (m²) | Ground release (%) |',
        '| Participant | Question 1 | Question 2 | Question 3 | Question 4 | Question 5 |': '| Participant | Q1 | Q2 | Q3 | Q4 | Q5 |',
    }
    for a, b in replacements.items(): text = text.replace(a, b)
    # Percent units moved from cells into the relevant numerical headers only.
    t5 = original[4]
    for row in t5['rows']:
        old = '| ' + ' | '.join(row) + ' |'
        new = row[:5] + [row[5].replace('%', ''), row[6].replace('%', '')]
        text = text.replace(old, '| ' + ' | '.join(new) + ' |')
    text = re.sub(r'Table (\d+)', lambda m: f'Table {NUMBER[int(m[1])]}' if int(m[1]) in NUMBER else m[0], text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text


plt.rcParams.update({'font.family': 'Times New Roman', 'font.size': 9.5, 'text.usetex': False, 'axes.unicode_minus': True})


def render(table, path, width_mm, proportions, header_labels=None, vertical_padding=5.5):
    """Size using measured glyph widths; 9.5 pt at the specified physical width."""
    headers = header_labels or table['headers']
    rows = table['rows']
    width_pt = width_mm / 25.4 * 72
    fig = plt.figure(figsize=(width_pt / 72, 1), dpi=72)
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    regular = FontProperties(family='Times New Roman', size=9.5)
    bold = FontProperties(family='Times New Roman', size=9.5, weight='bold')
    pad, leading = 5, 11.7
    avail = width_pt - 8
    widths = [avail * p / sum(proportions) for p in proportions]

    def wrap(s, width, prop):
        out = []
        for paragraph in s.split('\n'):
            line = ''
            for word in paragraph.split():
                trial = (line + ' ' + word).strip()
                if line and renderer.get_text_width_height_descent(trial, prop, False)[0] > width:
                    out.append(line); line = word
                else: line = trial
            out.append(line)
        for line in out:
            assert renderer.get_text_width_height_descent(line, prop, False)[0] <= width + 0.3, (path.name, line, width)
        return out

    content = []
    for i, row in enumerate([headers] + rows):
        prop = bold if i == 0 or row[0] == 'Mean' else regular
        wrapped = [wrap(cell, widths[j] - 2 * pad, prop) for j, cell in enumerate(row)]
        height = max(map(len, wrapped)) * leading + 2 * vertical_padding
        content.append((row, wrapped, height, prop))
    height_pt = sum(c[2] for c in content) + 10
    fig.set_size_inches(width_pt / 72, height_pt / 72)
    ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, width_pt); ax.set_ylim(height_pt, 0); ax.axis('off')
    left, right, top = 4, width_pt - 4, 4
    ax.plot([left, right], [top, top], color='black', linewidth=0.9)
    y = top
    checks = []
    for i, (row, wrapped, height, prop) in enumerate(content):
        x = left
        if row[0] == 'Mean':
            ax.plot([left, right], [y, y], color='0.55', linewidth=0.35)
        for j, lines in enumerate(wrapped):
            numeric = i > 0 and re.fullmatch(r'[\d,.+−–%() /to]+', row[j]) is not None
            ha = 'right' if numeric else 'left'
            tx = x + widths[j] - pad if numeric else x + pad
            artist = ax.text(tx, y + vertical_padding, '\n'.join(lines), fontproperties=prop, ha=ha, va='top', linespacing=leading / 9.5, color='black')
            checks.append((artist, x, x + widths[j], y, y + height))
            x += widths[j]
        y += height
        if i == 0:
            ax.plot([left, right], [y, y], color='black', linewidth=0.5)
    ax.plot([left, right], [y, y], color='black', linewidth=0.9)
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    for artist, x0, x1, y0, y1 in checks:
        box = artist.get_window_extent(renderer).transformed(ax.transData.inverted())
        assert box.x0 >= x0 - 0.4 and box.x1 <= x1 + 0.4, (path.name, artist.get_text(), 'horizontal overflow')
        assert max(box.y0, box.y1) <= y1 + 0.7, (path.name, artist.get_text(), 'vertical overflow')
    fig.savefig(path, dpi=600, facecolor='white', metadata={'Title': table['caption'], 'Software': 'Matplotlib; Times New Roman 9.5 pt; 600 dpi'})
    fig.savefig(path.with_suffix('.pdf'), facecolor='white')
    plt.close(fig)
    with Image.open(path) as im:
        assert im.mode in ('RGB', 'RGBA') and im.width > 2000
        return {'file': path.name, 'width_mm': width_mm, 'pixels': list(im.size), 'dpi': list(im.info['dpi']), 'font_pt': 9.5}


def main():
    text = SOURCE.read_text()
    original = tables(text)
    assert len(original) == 11
    revised = compact(text, original)
    retained = tables(revised)
    assert len(retained) == 6
    assert set(map(int, re.findall(r'Table (\d+)', revised))) == set(range(1, 7))
    for t, old in zip(retained, KEEP):
        if old not in [1, 4, 5]:
            assert t['rows'] == original[old - 1]['rows']
    DRAFT.write_text(revised)
    OUT.mkdir(parents=True, exist_ok=True)
    archive = OUT / '原版11张表_备份'; archive.mkdir(exist_ok=True)
    layouts = [(170, [0.22, 0.45, 0.33]), (170, [0.20, 0.44, 0.36]), (170, [0.19, 0.27, 0.27, 0.27]), (170, [0.19, 0.15, 0.38, 0.28]), (170, [0.10, 0.16, 0.13, 0.13, 0.16, 0.16, 0.16]), (125, [0.28, 0.18, 0.18, 0.18, 0.18]), (115, [0.32, 0.17, 0.17, 0.17, 0.17]), (105, [0.24, 0.27, 0.49]), (145, [0.18, 0.34, 0.48]), (170, [0.17, 0.16, 0.13, 0.16, 0.13, 0.13, 0.12]), (145, [0.28, 0.144, 0.144, 0.144, 0.144, 0.144])]
    for t, (width, props) in zip(original, layouts):
        render(t, archive / f'Original_Table_{t["number"]:02d}.png', width, props)
    config = [(170, [0.10, 0.53, 0.37]), (170, [0.20, 0.44, 0.36]), (170, [0.19, 0.43, 0.38]), (170, [0.10, 0.16, 0.13, 0.13, 0.16, 0.16, 0.16]), (170, [0.17, 0.16, 0.13, 0.16, 0.13, 0.13, 0.12]), (105, [0.28, 0.144, 0.144, 0.144, 0.144, 0.144])]
    records = []
    for t, old, (width, props) in zip(retained, KEEP, config):
        filename = f'Table_{t["number"]:02d}.png'
        record = render(t, OUT / filename, width, props, vertical_padding=2 if old == 11 else 5.5)
        record.update({'number': t['number'], 'original_number': old, 'caption': t['caption']})
        records.append(record)
        with (OUT / f'Table_{t["number"]:02d}.csv').open('w', newline='') as f:
            csv.writer(f).writerows([t['headers']] + t['rows'])
    (OUT / 'captions.txt').write_text('\n\n'.join(f'Table {t["number"]}. {t["caption"]}' for t in retained) + '\n')
    (OUT / 'updated_figure_captions.txt').write_text('\n\n'.join(re.sub(r'\*\*', '', m[0]) for m in re.finditer(r'^\*\*Figure [456]\.\*\* .+$', revised, re.M)) + '\n')
    (OUT / 'validation.json').write_text(json.dumps({'source': str(SOURCE), 'revised_draft': str(DRAFT), 'retained': records, 'original_table_count': 11, 'retained_table_count': 6, 'cell_overflow_checks': 'passed'}, ensure_ascii=False, indent=2))
    notes = '''正文表格 PNG（2026-11-01）

根目录的 Table_01–06.png 对应英文 v17 精简稿，建议用于正文。
原版全部11张表另存于“原版11张表_备份”，没有丢弃数据。

保留及编号：
Table 1 ← 原表1：三种治理情景。
Table 2 ← 原表2：六类形态算子。
Table 3 ← 原表4：E0–E6实验设计，合并重复的目的/研究问题列。
Table 4 ← 原表5：四组主实验总体结果。
Table 5 ← 原表10：同一情景下三个角色的首选方案。
Table 6 ← 原表11：三名参与者的五项评分。

正文精简：
原表3：角色优先级改成方法段的一段话。
原表6、7：与图5重复，移除独立表；在图注保留关键匹配数字。
原表8：BL支配比例并入图4图注。
原表9：零模型差值并入图6图注。
更新后的图4–6图注见updated_figure_captions.txt，需与精简稿同时替换。
原始数字均保留在原版备份中，保留表的统计值没有重新计算。

排版：
600 dpi，白底、黑字、Times New Roman 9.5 pt、三线表，不用竖线或背景色。
多数表按170 mm宽设计，评分表为105 mm宽；导入时尽量保持建议宽度。
PNG不内嵌表号和图注，避免与ProceeDings自动编号重复；图注见captions.txt。
PDF为矢量备份，CSV为可编辑表格数据。
请按Table编号分别导入，并将captions.txt中的文字粘贴到平台表注字段。
精简稿为新文件，不覆盖原v16正文及已有的手动修改文本。
'''
    (OUT / '使用说明与删减清单.txt').write_text(notes)
    # A quick inspection sheet is separate from upload images.
    thumbs = []
    for r in records:
        with Image.open(OUT / r['file']) as im:
            im = im.convert('RGB'); im.thumbnail((1100, 1100))
            tile = Image.new('RGB', (1140, im.height + 60), 'white')
            ImageDraw.Draw(tile).text((20, 8), f'Table {r["number"]} (original {r["original_number"]})', fill='black')
            tile.paste(im, (20, 40)); thumbs.append(tile)
    sheet = Image.new('RGB', (1140, sum(im.height for im in thumbs)), '#eeeeee')
    y = 0
    for im in thumbs: sheet.paste(im, (0, y)); y += im.height
    sheet.save(OUT / '全部表格预览.jpg', quality=94)
    shutil.copytree(OUT, DESKTOP, dirs_exist_ok=True)
    # Source Markdown uses paths relative to the paper directory; desktop gets a standalone text copy.
    (DESKTOP / '英文正文_v17_精简表格版.txt').write_text(revised)
    for p in OUT.rglob('*'):
        if p.is_file():
            assert hashlib.sha256(p.read_bytes()).digest() == hashlib.sha256((DESKTOP / p.relative_to(OUT)).read_bytes()).digest()
    print(json.dumps({'desktop': str(DESKTOP), 'draft': str(DRAFT), 'tables': records}, ensure_ascii=False, indent=2))

if __name__ == '__main__': main()
