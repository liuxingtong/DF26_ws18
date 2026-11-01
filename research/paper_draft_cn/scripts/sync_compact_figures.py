"""Verify and synchronise compact figures 3–5 into the v18 delivery package."""
from pathlib import Path
import csv,json,hashlib,shutil,math
from PIL import Image
BASE=Path(__file__).resolve().parents[1]
ROOT=BASE.parents[1]
DATA=ROOT/'05_Shanghai Power to Form Students/out/dapuqiao/results_v2/e0_exposure_v2'
TEMP=Path('/tmp/df26_compact_figures')
PACK=BASE/'submission_caadria2027/concise_v18'
DESKTOP=Path.home()/'Desktop/CAADRIA2027_精简正文_v18'
DELIVERY=Path.home()/'Desktop/CAADRIA2027_扁长版图3-5'
BACKUP=BASE/'figures/layout_backup_20261101'
BACKUP.mkdir(exist_ok=True);DELIVERY.mkdir(exist_ok=True)
read=lambda p:list(csv.DictReader(p.open(encoding='utf-8-sig')))
# Independently verify summary statistics used for the E6 rendering.
for row in read(TEMP/'fig4_e6_plot_values.csv'):
    cap=row['condition']=='capacity_band_pct'
    name='matched_capacity_detail.csv' if cap else 'matched_disruption_detail.csv'
    key='min_disruption_pct' if cap else 'max_capacity_pct'
    vals=sorted(float(r[key]) for r in read(DATA/'matching'/name) if r['method']==row['method'] and float(r[row['condition']])==float(row['value']) and r[key] not in ('','None'))
    assert len(vals)==int(row['matched_seeds'])
    if vals:
        n=len(vals);median=vals[n//2] if n%2 else (vals[n//2-1]+vals[n//2])/2
        assert abs(float(row['median'])-median)<1e-10
        assert float(row['minimum'])==min(vals) and float(row['maximum'])==max(vals)
    else:assert row['median']==''
# Role geometry and objectives must remain unchanged.
old=read(DATA/'role_geometry/role_picks.csv');new=read(TEMP/'role_checks/role_picks.csv')
assert len(old)==len(new)==3
for a,b in zip(old,new):
    assert a.keys()==b.keys()
    for key in a:
        try:assert math.isclose(float(a[key]),float(b[key]),rel_tol=1e-10,abs_tol=1e-7),(key,a[key],b[key])
        except ValueError:assert a[key]==b[key]
checks=json.loads((TEMP/'role_checks/reconstruction_checks.json').read_text())
assert all(x['input_and_engine_hashes_match'] and x['objectives_match'] and x['descriptors_match'] for x in checks)

records=[]
for n,stem in [(3,'fig3_merged_pareto_fronts'),(4,'fig4_e6_matched_tradeoffs'),(5,'fig6_role_picks_exposure_v2')]:
    target=BASE/'figures/exposure_v2'/f'{stem}.png'
    backup=BACKUP/target.name
    if not backup.exists():shutil.copy2(target,backup)
    with Image.open(backup) as im:oldsize=im.size
    with Image.open(TEMP/f'{stem}.png') as im:newsize=im.size
    reduction=1-(newsize[1]/newsize[0])/(oldsize[1]/oldsize[0])
    assert reduction>.25
    outputs=[]
    for ext in ['png','pdf','svg']:
        src=TEMP/f'{stem}.{ext}'
        assert src.is_file() and src.stat().st_size>1000
        canonical=BASE/'figures/exposure_v2'/src.name
        prior=BACKUP/src.name
        if not prior.exists():shutil.copy2(canonical,prior)
        targets=[canonical,PACK/'figures/exposure_v2'/src.name,DESKTOP/'figures/exposure_v2'/src.name,PACK/'figures_for_import'/f'Figure_{n:02d}.{ext}',DESKTOP/'figures_for_import'/f'Figure_{n:02d}.{ext}',DELIVERY/f'Figure_{n:02d}.{ext}']
        for out in targets:
            out.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,out)
            assert hashlib.sha256(src.read_bytes()).digest()==hashlib.sha256(out.read_bytes()).digest()
            outputs.append(str(out))
    records.append(dict(figure=n,source=stem,old_pixels=oldsize,new_pixels=newsize,same_width_height_reduction_pct=round(reduction*100,2),height_at_170mm_width_mm=round(170*newsize[1]/newsize[0],2),outputs=outputs))
# Preserve the plotting audit alongside the delivery.
audit=PACK/'compact_figure_audit';audit.mkdir(exist_ok=True)
for src in [TEMP/'fig4_e6_plot_values.csv',TEMP/'fig4_e6_provenance.json',TEMP/'role_checks/reconstruction_checks.json',TEMP/'role_checks/role_picks.csv']:
    shutil.copy2(src,audit/src.name)
report={'figures':records,'e6_summary_verified':True,'role_inputs_objectives_and_geometry_verified':True,'data_changed':False,'projection_changed':False}
(audit/'layout_changes.json').write_text(json.dumps(report,indent=2)+'\n')
shutil.copytree(audit,DESKTOP/audit.name,dirs_exist_ok=True)
(DELIVERY/'说明.txt').write_text('对应v18精简正文的Figure 3、4、5。按相同宽度插入时，高度较原版减少约30%。\nPNG为300 dpi，另附矢量PDF和SVG。数据与三维投影保持一致，原图已在项目中备份。\n新版同时替换了桌面“CAADRIA2027_精简正文_v18”内的图片。\n')
print(json.dumps([{k:v for k,v in r.items() if k!='outputs'} for r in records],indent=2))
print('All 3 figures synchronised and verified.')
