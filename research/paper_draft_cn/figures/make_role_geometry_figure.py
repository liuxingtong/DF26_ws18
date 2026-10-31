"""Reconstruct archived role picks and verify geometry against archived changes."""
import sys,csv,json,argparse,hashlib
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from matplotlib.collections import PolyCollection
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
R=Path(__file__).resolve().parents[3];W=R/'05_Shanghai Power to Form Students';sys.path.insert(0,str(W))
from engine.optimization import data as data_module
from engine.optimization.data import load_study,load_yaml
from engine.optimization.models import ZoneDecision
from engine.optimization.search import evaluate_candidate
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--run',type=Path,default=W/'out/dapuqiao/results_v2/e0_formal_remote_20261029/runs/public_coordination/seed_97')
parser.add_argument('--inputs',type=Path)
parser.add_argument('--figure-output',type=Path,default=Path(__file__).resolve().parent)
parser.add_argument('--table-output',type=Path)
a=parser.parse_args();P=a.run;F=a.figure_output
config=json.loads((P/'run_config.json').read_text())
version=config.get('metric_version','legacy_operator_tags')
scenario=config['scenario_id'];seed=config['seed']
OUT=a.table_output or P.parent.parent.parent/'role_geometry'
inputs=a.inputs or P/'inputs'
data_module.CONFIG_ROOT=P/'config'
if version=='actual_geometry_v2':
 for name,item in config['reproducibility']['input_files'].items():
  assert hashlib.sha256((inputs/name).read_bytes()).hexdigest()==item['sha256'],('input checksum',name)
 for name,item in config['reproducibility']['code_files'].items():
  if name.startswith('engine/'):
   assert hashlib.sha256((W/name).read_bytes()).hexdigest()==item['sha256'],('engine checksum',name)
study=load_study(scenario,shared_experiment_controls=config.get('control_envelope','shared')=='shared',data_root=inputs)
assert not study.blockers,study.blockers
if 'permission_table' in config:study.scenario['permission_overrides']=config['permission_table']['permissions']
ops=load_yaml(P/'config/operator_specs.yaml')['operators']
from engine.optimization.amplitude import resolve_arm,apply_operator_arm
arm=config.get('amplitude_arm','v1');arm=arm.get('amplitude_arm') if isinstance(arm,dict) else arm
_,overrides=resolve_arm(arm,path=P/'config/amplitude_arms.yaml');ops=apply_operator_arm(ops,overrides)
roles=['resident','development','public_planning'];names=['Residents','Development','Public planning'];selections=json.load(open(P/'selected_solutions.json'))
colors={'densify':'#E69F00','open_ground':'#56B4E9','split_to_towers':'#D55E00','heritage_step_down':'#CC79A7','public_space_reconfiguration':'#009E73','courtyard_access_improvement':'#0072B2'}
results=[];checks=[]
rows={r['solution_id']:r for r in csv.DictReader((P/'all_candidates.csv').open(encoding='utf-8-sig'))}
lossless={r['solution_id']:r for r in (json.loads(line) for line in (P/'candidate_decisions.jsonl').read_text().splitlines())} if (P/'candidate_decisions.jsonl').exists() else {}
for role in roles:
 sid=selections[role]
 if sid in lossless:
  record=lossless[sid]
  assert record['decision_type']=='zone_operator',record['decision_type']
  c=evaluate_candidate(study,[ZoneDecision(**d) for d in record['decisions']],ops,sid)
  assert c.feasible,(sid,'reconstructed solution is infeasible')
  for key,value in c.objectives.items():assert abs(float(rows[sid][key])-value)<1e-9,(sid,key)
  for key in ['net_gfa_change_m2','gross_added_m2','gross_removed_m2','changed_buildings']:
   assert abs(float(rows[sid][key])-float(c.descriptors[key]))<1e-5,(sid,key)
  archived={'changes':c.changes,'objectives':c.objectives}
  check={'role':role,'solution_id':sid,'complete_precision_decisions':True,'input_and_engine_hashes_match':True,'objectives_match':True,'descriptors_match':True}
 else:
  files=[p for p in (P/'provenance').glob('*.json') if json.load(open(p))['solution_id']==sid];assert len(files)==1
  archived=json.load(open(files[0]));c=evaluate_candidate(study,[ZoneDecision(**d) for d in archived['decisions']],ops,sid)
  saved={str(r['bid']):r for r in archived['changes']};recreated={str(r['bid']):r for r in c.changes}
  assert saved.keys()==recreated.keys(),(sid,'changed IDs differ')
  for bid in saved:
   for field in ['before_height_m','after_height_m','before_area_m2','after_area_m2']:
    assert abs(float(saved[bid][field])-float(recreated[bid][field]))<1e-5,(sid,bid,field)
  for key,value in archived['objectives'].items():assert abs(c.objectives[key]-value)<1e-9,(sid,key)
  check={'role':role,'solution_id':sid,'changed_ids_and_geometry_measures_match':True,'objectives_match':True}
 results.append((role,c,archived));checks.append(check)
OUT.mkdir(parents=True,exist_ok=True)
(OUT/'reconstruction_checks.json').write_text(json.dumps(checks,indent=2))
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':7,'svg.fonttype':'none','pdf.fonttype':42})
fig=plt.figure(figsize=(8.0,3.2));gs=fig.add_gridspec(2,3,height_ratios=[1.5,1],hspace=.15,wspace=.32)
minx,miny,maxx,maxy=study.buildings.total_bounds;cx=(minx+maxx)/2;cy=(miny+maxy)/2
baseline=study.buildings.set_index(study.buildings.bid.astype(str));class_names=['resident','developer','state'];bars=[];table=[]
az=np.deg2rad(25);el=np.deg2rad(35)
basis=np.array([[np.cos(az),-np.sin(az),0],[-np.sin(az)*np.sin(el),-np.cos(az)*np.sin(el),np.cos(el)],[np.sin(az)*np.cos(el),np.cos(az)*np.cos(el),np.sin(el)]])
height=max(float(c.buildings.height_m.max()) for _,c,_ in results)/1000
limits=np.array([[(x-cx)/1000,(y-cy)/1000,z] for x in [minx,maxx] for y in [miny,maxy] for z in [0,height]])@basis.T
for i,(role,c,archived) in enumerate(results):
 ax=fig.add_subplot(gs[0,i]);changes={str(r['bid']):r for r in archived['changes']};faces=[];facecolors=[];edgecolors=[]
 for _,row in c.buildings.iterrows():
  bid=str(row.bid);col=colors.get(changes.get(bid,{}).get('operator'),'#dddddd');edge='#111111' if bool(row.heritage) else '#aaaaaa'
  geom=row.geometry.simplify(.3,preserve_topology=True)
  for poly in getattr(geom,'geoms',[geom]):
   if poly.geom_type!='Polygon':continue
   xy=np.array(poly.exterior.coords);xy=(xy-[cx,cy])/1000;h=float(row.height_m)/1000
   faces.append([(x,y,h) for x,y in xy]);facecolors.append(col);edgecolors.append(edge)
   for a,b in zip(xy[:-1],xy[1:]):
    faces.append([(a[0],a[1],0),(b[0],b[1],0),(b[0],b[1],h),(a[0],a[1],h)]);facecolors.append(col);edgecolors.append(edge)
 # Orthographic axonometric projection, identical camera and scale for all roles.
 az=np.deg2rad(25);el=np.deg2rad(35)
 basis=np.array([[np.cos(az),-np.sin(az),0],[-np.sin(az)*np.sin(el),-np.cos(az)*np.sin(el),np.cos(el)],[np.sin(az)*np.cos(el),np.cos(az)*np.cos(el),np.sin(el)]])
 projected=[np.asarray(face)@basis.T for face in faces]
 order=sorted(range(len(faces)),key=lambda k:float(projected[k][:,2].mean()))
 ax.add_collection(PolyCollection([projected[k][:,:2] for k in order],facecolors=[facecolors[k] for k in order],edgecolors=[edgecolors[k] for k in order],linewidths=.10))
 ax.set_xlim(limits[:,0].min(),limits[:,0].max());ax.set_ylim(limits[:,1].min(),limits[:,1].max());ax.set_aspect('equal');ax.set_axis_off();ax.set_title(names[i]+' / '+c.solution_id,fontsize=8,pad=3)
 delta={k:0. for k in class_names}
 for _,row in c.buildings.iterrows():
  base=baseline.loc[str(row.bid)];cl=str(base.stakeholder_proxy)
  change=(row.geometry.area*float(row.height_m)-base.geometry.area*float(base.height_m))/3.5
  delta[cl]=delta.get(cl,0)+change
 assert abs(sum(delta.values())-c.descriptors['net_gfa_change_m2'])<1e-5
 bars.append(delta)
 table.append({'scenario':scenario,'seed':seed,'role':role,'solution_id':c.solution_id,'residential_exposure_pct':c.objectives['residential_disruption']*100,'net_gfa_change_m2':c.descriptors['net_gfa_change_m2'],'gross_added_m2':c.descriptors['gross_added_m2'],'gross_removed_m2':c.descriptors['gross_removed_m2'],'street_release_pct':c.objectives['street_connected_released_ground']*100,**{k+'_net_gfa_m2':v for k,v in delta.items()}})
# Comparable bar axes under all three views.
yvals=[v/1000 for d in bars for v in d.values()];lo=min(0,min(yvals))*1.15;hi=max(0,max(yvals))*1.2
for i,d in enumerate(bars):
 ax=fig.add_subplot(gs[1,i]);ax.bar([0,1,2],[d[k]/1000 for k in class_names],color=['#0072B2','#E69F00','#009E73'],width=.55);ax.axhline(0,color='#777777',lw=.6);ax.set(xticks=[0,1,2],xticklabels=['Resident','Developer','Public'],ylim=(lo,hi));ax.tick_params(labelsize=6);ax.spines[['top','right']].set_visible(False)
 if i==0:ax.set_ylabel('Net GFA change (1,000 m²)')
 else:ax.tick_params(labelleft=False)
fig.legend(handles=[Patch(facecolor=v,label=k.replace('_',' ')) for k,v in colors.items()]+[Patch(facecolor='#dddddd',label='Unchanged'),Patch(facecolor='white',edgecolor='black',label='Heritage')],loc='upper center',bbox_to_anchor=(.5,1.01),ncol=4,frameon=False,fontsize=6)
fig.subplots_adjust(top=.75,bottom=.12,left=.09,right=.98)
F.mkdir(parents=True,exist_ok=True)
figure_name='fig6_role_picks_exposure_v2' if version=='actual_geometry_v2' else 'fig6_role_picks_archived'
for ext in ['png','pdf','svg']:fig.savefig(F/f'{figure_name}.{ext}',dpi=300,bbox_inches='tight',pad_inches=.04)
with (OUT/'role_picks.csv').open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.DictWriter(f,fieldnames=table[0]);w.writeheader();w.writerows(table)
print(json.dumps(checks));print('Saved role figure and table:',version)
