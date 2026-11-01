"""Compare exported per-seed Pareto sets to the merged BL Pareto front.

Inputs must be pareto_solutions.csv, never all_candidates.csv. Original files
are read-only. Annotated copies and a complete source checksum list are saved.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import statistics
from pathlib import Path

METHODS = {'conventional_parameter_baseline': 'BL', 'public_coordination': 'PC',
           'development_growth': 'DG', 'resident_heritage_priority': 'RH'}
SEEDS = [11,23,37,53,71,83,97,109,127,139]
TOLERANCE = 1e-12

def vector(r):
    return (float(r['residential_disruption']), -float(r['development_capacity']),
            -float(r['street_connected_released_ground']))

def dominates(a, b):
    av, bv = vector(a), vector(b)
    return all(x <= y + TOLERANCE for x,y in zip(av,bv)) and any(x < y - TOLERANCE for x,y in zip(av,bv))

def front(rows):
    return [r for i,r in enumerate(rows) if not any(dominates(q,r) for j,q in enumerate(rows) if j != i)]

def write_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows: raise ValueError(f'Empty output: {path}')
    with path.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

def analyze(runs, output, seeds=SEEDS):
    sources=[]; indexed={}
    for method,label in METHODS.items():
        for seed in seeds:
            p=runs/method/f'seed_{seed}'/'pareto_solutions.csv'
            with p.open(encoding='utf-8-sig',newline='') as f: rows=list(csv.DictReader(f))
            if not rows: raise ValueError(f'Empty Pareto set: {p}')
            if any(r.get('feasible','true').strip().lower() != 'true' for r in rows):
                raise ValueError(f'Infeasible row in Pareto export: {p}')
            indexed[label,seed]=[{**r,'method':label,'seed':seed} for r in rows]
            sources.append({'path':str(p),'rows':len(rows),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
    summary_path=runs.parent/'run_summary.csv'
    if summary_path.exists():
        with summary_path.open(encoding='utf-8-sig',newline='') as f:
            expected={(METHODS[r['method_id']],int(r['seed'])):int(r['pareto_count']) for r in csv.DictReader(f)}
        for key,rs in indexed.items():
            if key in expected and len(rs)!=expected[key]:
                raise ValueError(f'Pareto export count differs from formal run summary: {key}, {len(rs)} vs {expected[key]}')
    baseline=front([r for seed in seeds for r in indexed['BL',seed]])
    write_csv(output/'baseline_merged_front.csv',baseline)
    detail=[]; annotated=[]
    for (label,seed),rows in indexed.items():
        marked=[{**r,'dominated_by_baseline':any(dominates(b,r) for b in baseline)} for r in rows]
        write_csv(output/'annotated'/label/f'seed_{seed}'/'pareto.csv',marked)
        annotated+=marked
        if label=='BL': continue
        outside=[r for r in marked if not r['dominated_by_baseline']]
        detail.append({'method':label,'seed':seed,'pareto_count':len(rows),
                       'not_dominated_count':len(outside),'not_dominated_pct':100*len(outside)/len(rows)})
    summary=[]
    for label in ['PC','DG','RH']:
        vals=[r['not_dominated_pct'] for r in detail if r['method']==label]
        outside=[r for r in annotated if r['method']==label and not r['dominated_by_baseline']]
        summary.append({'method':label,'median_pct':statistics.median(vals),'min_pct':min(vals),'max_pct':max(vals),
                        'outside_count':len(outside),'outside_zero_exposure_count':sum(abs(float(r['residential_disruption']))<=TOLERANCE for r in outside)})
    write_csv(output/'pareto_annotated.csv',annotated)
    write_csv(output/'dominance_by_seed.csv',detail)
    write_csv(output/'dominance_summary.csv',summary)
    (output/'provenance.json').write_text(json.dumps({'seeds':seeds,'denominator':'exported per-seed Pareto set',
        'baseline':'all 10 BL exported Pareto sets, merged and filtered by exact dominance',
        'tolerance':TOLERANCE,'epsilon_reapplied':False,'sources':sources,'baseline_front_count':len(baseline)},indent=2))
    print(json.dumps(summary,indent=2))
    return summary

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--runs',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();analyze(a.runs,a.output)
