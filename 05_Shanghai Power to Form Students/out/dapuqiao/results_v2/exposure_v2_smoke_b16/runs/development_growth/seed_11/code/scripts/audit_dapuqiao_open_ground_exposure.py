"""Read-only audit of archived Pareto exposure; does not change search/scoring."""
import csv,json,hashlib,sys
from pathlib import Path
from collections import defaultdict
import statistics
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))


def read(p):
 with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def write(p,rows):
 p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=rows[0]);w.writeheader();w.writerows(rows)

def main():
 import argparse
 ap=argparse.ArgumentParser();ap.add_argument('--runs',type=Path,required=True);ap.add_argument('--inputs',type=Path);ap.add_argument('--resident-weights',type=Path);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args()
 if a.resident_weights:
  residents=json.loads(a.resident_weights.read_text())
 else:
  if a.inputs is None:ap.error('--inputs or --resident-weights required')
  from engine.optimization.data import load_study
  study=load_study('public_coordination',data_root=a.inputs,shared_experiment_controls=True)
  res=study.buildings[study.buildings.residential_proxy]
  residents=[(str(r.bid),str(r.zone_id),r.geometry.area*float(r.height_m)) for _,r in res.iterrows()]
 total=sum(g for _,_,g in residents)
 oldops={'densify','split_to_towers','heritage_step_down','parameter_height_footprint'}
 details=[];byrun=[];hashes=[]
 for run in sorted(a.runs.glob('*/seed_*')):
  if not (run/'ops_log.csv').exists():continue
  method=run.parent.name;seed=int(run.name[5:]);log=read(run/'ops_log.csv');g=defaultdict(list)
  for r in log:g[r['solution_id']].append(r)
  front=read(run/'pareto_solutions.csv');selections=json.loads((run/'selected_solutions.json').read_text())
  for r in front:
   sid=r['solution_id'];changes=g.get(sid,[])
   # Empty change set valid only for unchanged solution.
   if not changes and float(r['changed_buildings'])>0:raise ValueError(f'Missing ops log {method}/{seed}/{sid}')
   ids={r['bid'] for r in changes};zones={str(r['zone_id']) for r in changes if r['operator'] in oldops}
   raised=[r for r in changes if r['operator']=='open_ground' and float(r['after_height_m'])-float(r['before_height_m'])>.1]
   added={str(r['zone_id']) for r in raised}
   old=sum(v for bid,z,v in residents if bid in ids or z in zones)/total
   new=sum(v for bid,z,v in residents if bid in ids or z in zones|added)/total
   err=abs(old-float(r['residential_disruption']))
   if err>1e-8:raise ValueError(f'Archived f1 could not be reproduced: {method}/{seed}/{sid}: {err}')
   details.append(dict(method=method,seed=seed,solution_id=sid,roles=';'.join(k for k,v in selections.items() if v==sid),
     open_ground_raised_buildings=len(raised),old_exposure_pct=old*100,diagnostic_exposure_pct=new*100,delta_pp=(new-old)*100))
  sub=[r for r in details if r['method']==method and r['seed']==seed]
  byrun.append(dict(method=method,seed=seed,pareto_count=len(sub),open_ground_raised_solutions=sum(r['open_ground_raised_buildings']>0 for r in sub),
    exposure_increased_solutions=sum(r['delta_pp']>1e-8 for r in sub),max_delta_pp=max(r['delta_pp'] for r in sub)))
  p=run/'ops_log.csv';hashes.append(dict(path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
 summary=[]
 for m in sorted({r['method'] for r in details}):
  sub=[r for r in details if r['method']==m];diff=[r['delta_pp'] for r in sub]
  summary.append(dict(method=m,pareto_count=len(sub),open_ground_raised_solutions=sum(r['open_ground_raised_buildings']>0 for r in sub),
     exposure_increased_solutions=sum(d>1e-8 for d in diff),median_delta_pp=statistics.median(diff),max_delta_pp=max(diff)))
 write(a.output/'pareto_exposure_audit.csv',details);write(a.output/'audit_by_seed.csv',byrun);write(a.output/'audit_summary.csv',summary)
 (a.output/'provenance.json').write_text(json.dumps(dict(diagnostic='Archived tag-based exposure plus open_ground height gain >0.1m; fixed original Pareto sets; no re-search or re-ranking',all_original_exposure_values_reproduced=True,inputs=str(a.inputs),ops_sources=hashes),indent=2))
 print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
