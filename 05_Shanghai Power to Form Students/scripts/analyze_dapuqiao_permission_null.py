#!/usr/bin/env python3
"""Permission-null comparison using one pooled scale and table-level replication."""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
from pathlib import Path
import statistics
import numpy as np
from pymoo.indicators.hv import HV

SCENARIOS = ('public_coordination', 'development_growth', 'resident_heritage_priority')
MAIN_SEEDS = (11, 23, 37, 53, 71, 83, 97, 109, 127, 139)
PAIRED_SEEDS = (11, 23, 37)
BL = 'conventional_parameter_baseline'
OBJECTIVES = ('residential_disruption', 'development_capacity', 'street_connected_released_ground')


def load_run(path):
    config = json.loads((path/'run_config.json').read_text())
    search = config['search']
    if config['metric_version'] != 'actual_geometry_v2':
        raise ValueError(f'Metric version mismatch: {path}')
    if (search['population'], search['generations'], search['raw_evaluation_calls'],
        search['requested_evaluation_budget']) != (40, 50, 2000, 2000):
        raise ValueError(f'Budget mismatch: {path}')
    with (path/'all_candidates.csv').open(encoding='utf-8-sig', newline='') as f:
        rows = [r for r in csv.DictReader(f) if r['feasible'].lower() == 'true']
    values = np.asarray([[float(r[k]) for k in OBJECTIVES] for r in rows], dtype=float).reshape(-1, 3)
    if not len(values) or not np.isfinite(values).all():
        raise ValueError(f'No finite feasible candidates: {path}')
    return rows, values, config


def run_metrics(values, ideal, nadir, target=.002, tolerance=.0005):
    costs = values * np.asarray([1., -1., -1.])
    scaled = (costs-ideal)/np.maximum(nadir-ideal, 1e-12)
    if scaled.min() < -1e-8 or scaled.max() > 1+1e-8:
        raise ValueError('Candidate outside the pooled normalization bounds')
    hv = float(HV(ref_point=np.full(3, 1.1))(scaled))
    matched = values[np.abs(values[:, 1]-target) <= tolerance+1e-12]
    return dict(hypervolume=hv, matched_count=len(matched),
                min_exposure_pct=float(matched[:, 0].min()*100) if len(matched) else None)


def table_effect(real, randomized, metric):
    pairs = [(real[s][metric], randomized[s][metric]) for s in PAIRED_SEEDS
             if real[s][metric] is not None and randomized[s][metric] is not None]
    return dict(paired_seeds=len(pairs),
                median_random_minus_real=statistics.median(b-a for a,b in pairs) if pairs else None)


def write_csv(path, rows):
    with path.open('w', encoding='utf-8-sig', newline='') as f:
        w=csv.DictWriter(f, fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)


def analyze(main_root, null_root, output, target=.002, tolerance=.0005):
    # Refuse partial batches; a permission table is the replicate, not each seed.
    if not (null_root.parent/'completed.json').exists():
        raise ValueError('The permission-null batch has not completed')
    for seed in MAIN_SEEDS:
        status=json.loads((main_root.parent/'status'/f'seed_{seed}.json').read_text())
        if status['state'] != 'completed':raise ValueError(f'Main seed {seed} is incomplete')
    tasks = [('real', method, None, seed, main_root/method/f'seed_{seed}')
             for method in (BL, *SCENARIOS) for seed in MAIN_SEEDS]
    tasks += [('random', method, k, seed, null_root/method/f'table_{k:02d}'/f'seed_{seed}')
              for method in SCENARIOS for k in range(10) for seed in PAIRED_SEEDS]
    loaded=[]; input_signature=None; sources={}; table_hashes={}
    for source, method, k, seed, path in tasks:
        rows, values, config = load_run(path)
        if config['seed'] != seed or config['method_id'] != method:
            raise ValueError(f'Run identity mismatch: {path}')
        signature={name:item['sha256'] for name,item in config['reproducibility']['input_files'].items()}
        if input_signature is None:input_signature=signature
        if signature != input_signature:raise ValueError(f'Input mismatch: {path}')
        if source == 'random':
            table=config['permission_table']
            if table['table_index'] != k:raise ValueError(f'Wrong permission table: {path}')
            digest=hashlib.sha256(json.dumps(table['permissions'],sort_keys=True).encode()).hexdigest()
            if digest != table['sha256']:raise ValueError(f'Permission table checksum mismatch: {path}')
            key=(method,k)
            if key in table_hashes and table_hashes[key]!=digest:raise ValueError(f'Seed-specific table changed: {path}')
            table_hashes[key]=digest
            if any(d['gfa_relative_error']>.05+1e-12 for d in table['diagnostics'].values()):
                raise ValueError(f'Unmatched permission area: {path}')
        sources[str(path/'all_candidates.csv')]=hashlib.sha256((path/'all_candidates.csv').read_bytes()).hexdigest()
        loaded.append((source,method,k,seed,values))
    for method in SCENARIOS:
        if len({table_hashes[method,k] for k in range(10)})!=10:
            raise ValueError(f'Duplicate permission tables: {method}')
    pool=np.vstack([values*np.array([1.,-1.,-1.]) for *_,values in loaded])
    ideal=pool.min(axis=0);nadir=pool.max(axis=0)
    detail=[]
    for source,method,k,seed,values in loaded:
        detail.append(dict(source=source,method=method,table=k,seed=seed,
                           **run_metrics(values,ideal,nadir,target,tolerance)))
    effects=[]
    for method in SCENARIOS:
        real={r['seed']:r for r in detail if r['source']=='real' and r['method']==method}
        for k in range(10):
            random={r['seed']:r for r in detail if r['source']=='random' and r['method']==method and r['table']==k}
            for metric in ('hypervolume','min_exposure_pct'):
                effects.append(dict(method=method,table=k,metric=metric,**table_effect(real,random,metric)))
    output.mkdir(parents=True,exist_ok=True)
    write_csv(output/'run_metrics.csv',detail);write_csv(output/'table_paired_effects.csv',effects)
    provenance=dict(metric_version='actual_geometry_v2',normalization='all feasible candidates from 40 real and 90 null runs',
                    ideal=ideal.tolist(),nadir=nadir.tolist(),reference_point=[1.1]*3,
                    capacity_target_pct=target*100,capacity_tolerance_pp=tolerance*100,
                    paired_seeds=list(PAIRED_SEEDS),replication='10 permission tables per scenario; three paired seeds per table',
                    missing_matches='No interpolation or zero imputation',sources=sources,input_sha256=input_signature)
    (output/'provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
    draw(detail,output)
    return detail,effects


def draw(detail, output):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':8,'pdf.fonttype':42,'svg.fonttype':'none',
                         'axes.spines.top':False,'axes.spines.right':False})
    fig,axes=plt.subplots(2,3,figsize=(7.2,4.1),sharey='row',layout='constrained')
    for col,(method,label) in enumerate(zip(SCENARIOS,('PC','DG','RH'))):
        axes[0,col].set_title(label,fontweight='bold')
        for row,metric in enumerate(('hypervolume','min_exposure_pct')):
            ax=axes[row,col]
            real=[r for r in detail if r['source']=='real' and r['method']==method]
            other=[r[metric] for r in real if r['seed'] not in PAIRED_SEEDS and r[metric] is not None]
            paired=[r[metric] for r in real if r['seed'] in PAIRED_SEEDS and r[metric] is not None]
            ax.scatter(np.linspace(-.09,.09,len(other)),other,s=15,c='#a5a5a5',alpha=.6,zorder=2)
            ax.scatter(np.linspace(-.07,.07,len(paired)),paired,s=23,c='#0072B2',zorder=3)
            if len(paired)==3:ax.plot([-.16,.16],[statistics.median(paired)]*2,c='#222222',lw=1.3)
            medians=[]
            for k in range(10):
                values=[r[metric] for r in detail if r['source']=='random' and r['method']==method and r['table']==k]
                # Plot only complete three-seed table medians; retain all missingness in CSV.
                if len(values)==3 and all(v is not None for v in values):medians.append(statistics.median(values))
            ax.scatter(1+np.linspace(-.1,.1,len(medians)),medians,s=23,c='#D55E00',marker='D',zorder=3)
            if medians:ax.plot([.84,1.16],[statistics.median(medians)]*2,c='#222222',lw=1.3)
            ax.text(.98,.97,f'{len(paired)}/3 real seeds; {len(medians)}/10 tables',ha='right',va='top',transform=ax.transAxes,fontsize=6.5)
            if not paired and not medians:ax.text(.5,.45,'No matched candidates',ha='center',transform=ax.transAxes,color='#666666')
            ax.set(xticks=[0,1],xticklabels=['Real\nseeds','Random\ntable medians'],xlim=(-.4,1.4))
            ax.grid(axis='y',color='#e8e8e8',lw=.5);ax.set_axisbelow(True)
            if col==0:ax.set_ylabel('Hypervolume' if row==0 else 'Matched residential exposure (%)')
    fig.legend(handles=[Line2D([],[],marker='o',ls='',color='#0072B2',label='Matched paired real seeds (up to 3)'),
                        Line2D([],[],marker='o',ls='',color='#a5a5a5',label='Other real seeds (n=7)'),
                        Line2D([],[],marker='D',ls='',color='#D55E00',label='Random table median (3 seeds)')],
               loc='outside lower center',ncol=3,frameon=False,fontsize=7)
    for ext in ('png','pdf','svg'):fig.savefig(output/f'fig5_permission_null.{ext}',dpi=300,bbox_inches='tight')
    plt.close(fig)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--main-runs',type=Path,required=True);p.add_argument('--null-runs',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--capacity-target-pct',type=float,default=.2)
    p.add_argument('--capacity-tolerance-pp',type=float,default=.05)
    a=p.parse_args();analyze(a.main_runs,a.null_runs,a.output,a.capacity_target_pct/100,a.capacity_tolerance_pp/100)
