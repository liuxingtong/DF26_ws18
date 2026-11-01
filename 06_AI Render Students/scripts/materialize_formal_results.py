"""Rebuild and verify the seed-97 formal fronts used by the platform."""
from pathlib import Path
import sys,json,csv,shutil,hashlib
from concurrent.futures import ProcessPoolExecutor
W=Path(__file__).resolve().parents[2]/'05_Shanghai Power to Form Students';sys.path.insert(0,str(W))
E=W/'out/dapuqiao/results_v2/e0_exposure_v2'
def worker(method):
 from engine.optimization import data
 from engine.optimization.data import load_study,load_yaml
 from engine.optimization.amplitude import resolve_arm,apply_operator_arm,apply_baseline_arm
 from engine.optimization.models import ZoneDecision,ParameterDecision
 from engine.optimization.search import evaluate_candidate
 from engine.optimization.parameter_baseline import evaluate_parameter_candidate,build_parameter_baseline_study
 source=E/'runs'/method/'seed_97';out=E/'platform_runs'/method;out.mkdir(parents=True,exist_ok=True)
 cfg=json.loads((source/'run_config.json').read_text());data.CONFIG_ROOT=source/'config'
 for name,meta in cfg['reproducibility']['code_files'].items():
  if name.startswith('engine/'):assert hashlib.sha256((W/name).read_bytes()).hexdigest()==meta['sha256'],name
 inputs=E/'frozen_inputs'
 for name,meta in cfg['reproducibility']['input_files'].items():assert hashlib.sha256((inputs/name).read_bytes()).hexdigest()==meta['sha256']
 study=load_study('public_coordination' if method=='conventional_parameter_baseline' else method,shared_experiment_controls=True,data_root=inputs)
 _,arm=resolve_arm('v1',path=source/'config/amplitude_arms.yaml')
 specs=apply_operator_arm(load_yaml(source/'config/operator_specs.yaml')['operators'],arm)
 if method=='conventional_parameter_baseline':study=build_parameter_baseline_study(study,apply_baseline_arm(load_yaml(source/'config/parameter_baseline.yaml'),arm))
 rows=list(csv.DictReader((source/'pareto_solutions.csv').open(encoding='utf-8-sig')));ids={r['solution_id'] for r in rows}
 decisions={r['solution_id']:r for r in map(json.loads,(source/'candidate_decisions.jsonl').read_text().splitlines()) if r['solution_id'] in ids}
 (out/'solutions').mkdir(exist_ok=True)
 for row in rows:
  sid=row['solution_id'];d=decisions[sid]
  if method=='conventional_parameter_baseline':c=evaluate_parameter_candidate(study,[ParameterDecision(**{k:v for k,v in x.items() if k!='operator'}) for x in d['decisions']],sid)
  else:c=evaluate_candidate(study,[ZoneDecision(**x) for x in d['decisions']],specs,sid)
  for k,v in c.objectives.items():assert abs(v-float(row[k]))<1e-9,(method,sid,k)
  c.buildings[['bid','height_m','stakeholder_proxy','geometry']].to_file(out/'solutions'/f'pareto__{sid}.geojson',driver='GeoJSON')
 for name in ['pareto_solutions.csv','selected_solutions.json']:shutil.copy2(source/name,out/name)
 cfg['experiment_status']='formal_seed97';cfg['formal_source']=str(source.relative_to(W));(out/'run_config.json').write_text(json.dumps(cfg,ensure_ascii=False))
 print(method,len(rows),'geometries verified',flush=True)
 return len(rows)
if __name__=='__main__':
 with ProcessPoolExecutor(max_workers=4) as p:print('Total:',sum(p.map(worker,['conventional_parameter_baseline','public_coordination','development_growth','resident_heritage_priority'])))
