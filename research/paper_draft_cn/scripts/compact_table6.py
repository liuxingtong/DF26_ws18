"""Shorten Table 6 through cell padding while preserving type size and data."""
from pathlib import Path
import json,shutil,hashlib
from PIL import Image,ImageDraw
from export_proceedings_tables import tables,render
BASE=Path(__file__).resolve().parents[1]
root=BASE/'submission_caadria2027/tables_png_20261101'
backup=BASE/'figures/layout_backup_20261101';backup.mkdir(exist_ok=True)
for ext in ['png','pdf']:
 p=root/f'Table_06.{ext}'
 if not (backup/p.name).exists():shutil.copy2(p,backup/p.name)
with Image.open(backup/'Table_06.png') as im:before=im.size
text=(BASE/'2026-11-01_Dapuqiao_CAADRIA_English_v19_Revised.md').read_text()
table=tables(text)[5]
assert table['rows']==[['1','5','5','4','4','5'],['2','4','3','5','5','4'],['3','5','3','5','4','4'],['Mean','4.67','3.67','4.67','4.33','4.33']]
report=render(table,root/'Table_06.png',105,[.28,.144,.144,.144,.144,.144],vertical_padding=2)
after=report['pixels'];assert before[0]==after[0] and after[1]<before[1]*.75
folders=[BASE/'submission_caadria2027/concise_v18/tables',BASE/'submission_caadria2027/revised_v19/tables',Path.home()/'Desktop/CAADRIA2027_正文表格',Path.home()/'Desktop/CAADRIA2027_精简正文_v18/tables',Path.home()/'Desktop/CAADRIA2027_精简正文_v18/英文正文_v19/tables']
for folder in folders:
 assert folder.exists(),folder
 for ext in ['png','pdf']:
  src=root/f'Table_06.{ext}';dest=folder/src.name;shutil.copy2(src,dest)
  assert hashlib.sha256(src.read_bytes()).digest()==hashlib.sha256(dest.read_bytes()).digest()
# Keep the original table-set validation report consistent with the new dimensions.
p=root/'validation.json';validation=json.loads(p.read_text())
r=next(r for r in validation['retained'] if r['number']==6);r.update(report);r['vertical_padding_pt']=2
p.write_text(json.dumps(validation,ensure_ascii=False,indent=2)+'\n')
shutil.copy2(p,Path.home()/'Desktop/CAADRIA2027_正文表格'/p.name)
# Refresh the six-table contact sheet.
thumbs=[]
for n in range(1,7):
 with Image.open(root/f'Table_{n:02d}.png') as im:
  im=im.convert('RGB');im.thumbnail((1100,1100));tile=Image.new('RGB',(1140,im.height+60),'white');ImageDraw.Draw(tile).text((20,8),f'Table {n}',fill='black');tile.paste(im,(20,40));thumbs.append(tile)
sheet=Image.new('RGB',(1140,sum(im.height for im in thumbs)),'#eeeeee');y=0
for im in thumbs:sheet.paste(im,(0,y));y+=im.height
sheet.save(root/'全部表格预览.jpg',quality=94)
shutil.copy2(root/'全部表格预览.jpg',Path.home()/'Desktop/CAADRIA2027_正文表格/全部表格预览.jpg')
reduction=round((1-after[1]/before[1])*100,1)
print(json.dumps({'before':before,'after':after,'height_reduction_pct':reduction,'font_pt':9.5,'width_mm':105,'dpi':600,'data_verified':True,'copies_verified':True},indent=2))
