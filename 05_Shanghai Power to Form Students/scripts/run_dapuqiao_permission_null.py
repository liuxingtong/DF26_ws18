#!/usr/bin/env python3
"""Run permission-matched random controls without changing residential labels."""
from __future__ import annotations
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import hashlib
import json
from pathlib import Path
import sys
import time

WS05 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WS05))
from engine.optimization.amplitude import apply_operator_arm, resolve_arm
from engine.optimization.data import CONFIG_ROOT, load_study, load_yaml
from engine.optimization.nsga2 import run_nsga2
from engine.optimization.permission_null import generate_permission_table, validate_permission_table
from engine.optimization.roles import evaluate_roles
from run_dapuqiao_optimization import export_run

SCENARIOS = ('public_coordination', 'development_growth', 'resident_heritage_priority')


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n')
    temporary.replace(path)


def make_tables(root, count):
    records = []
    for scenario_index, scenario in enumerate(SCENARIOS):
        study = load_study(scenario, shared_experiment_controls=True)
        if study.blockers:
            raise RuntimeError(study.blockers)
        signatures = set()
        for k in range(count):
            table_seed = 20261031 + 100000*scenario_index + k
            table, diagnostics = generate_permission_table(study.buildings, study.scenario, table_seed)
            if not any(d['changed_membership'] for d in diagnostics.values()):
                raise RuntimeError(f'{scenario}: no randomizable permissions')
            digest = hashlib.sha256(json.dumps(table, sort_keys=True).encode()).hexdigest()
            if digest in signatures:
                raise RuntimeError(f'{scenario}: duplicate permission table {k}; refusing artificial replication')
            signatures.add(digest)
            record = dict(scenario=scenario, table_index=k, table_seed=table_seed,
                          sha256=digest, permissions=table, diagnostics=diagnostics)
            path = root/'tables'/scenario/f'table_{k:02d}.json'
            if path.exists() and json.loads(path.read_text()) != record:
                raise RuntimeError(f'Existing permission table differs: {path}')
            write_json(path, record)
            records.append((scenario, k))
    return records


def run_one(root, scenario, k, seed, population, generations, budget):
    output = root/'runs'/scenario/f'table_{k:02d}'/f'seed_{seed}'
    status = root/'status'/f'{scenario}__table_{k:02d}__seed_{seed}.json'
    write_json(status, dict(state='running', scenario=scenario, table=k, seed=seed))
    try:
        study = load_study(scenario, shared_experiment_controls=True)
        if study.blockers:
            raise RuntimeError(study.blockers)
        record = json.loads((root/'tables'/scenario/f'table_{k:02d}.json').read_text())
        validate_permission_table(study.buildings, study.scenario, record['permissions'])
        study.scenario['permission_overrides'] = record['permissions']
        study.retain_candidate_geometries = False
        _, arm = resolve_arm('v1')
        specs = apply_operator_arm(load_yaml(CONFIG_ROOT/'operator_specs.yaml')['operators'], arm)
        started = time.perf_counter()
        candidates, front, metadata = run_nsga2(study, specs, population=population,
            generations=generations, seed=seed, evaluation_budget=budget, fixed_raw_budget=True)
        runtime = time.perf_counter()-started
        role_rows, selections = evaluate_roles(front, load_yaml(CONFIG_ROOT/'role_profiles.yaml'),
                                               study.objective_config.get('epsilon', {}))
        export_run(study, candidates, front, role_rows, selections, seed=seed, samples=0,
            search_metadata=metadata, output_dir=output, method_id=scenario, export_geometries=False,
            optimization_runtime_seconds=runtime,
            extra_run_config=dict(experiment='permission_null', permission_table=record,
                                  amplitude_arm='v1', control_envelope='shared'))
        result = dict(state='completed', scenario=scenario, table=k, seed=seed,
                      runtime_seconds=runtime, pareto_count=len(front), candidates=len(candidates))
        write_json(status, result)
        return result
    except Exception as exc:
        write_json(status, dict(state='failed', scenario=scenario, table=k, seed=seed, error=repr(exc)))
        raise


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', required=True, type=Path)
    p.add_argument('--tables', type=int, default=10)
    p.add_argument('--seeds', default='11,23,37')
    p.add_argument('--population', type=int, default=40)
    p.add_argument('--generations', type=int, default=50)
    p.add_argument('--evaluation-budget', type=int, default=2000)
    p.add_argument('--jobs', type=int, default=10)
    p.add_argument('--dry-run', action='store_true')
    args = p.parse_args()
    root = args.output.resolve()
    seeds = [int(x) for x in args.seeds.split(',')]
    tables = make_tables(root, args.tables)
    write_json(root/'manifest.json', dict(metric_version='actual_geometry_v2', tables=args.tables,
        seeds=seeds, population=args.population, generations=args.generations,
        budget=args.evaluation_budget, fixed_raw_budget=True, amplitude_arm='v1',
        gfa_tolerance=.05, per_zone_counts='exact', tasks=len(tables)*len(seeds)))
    print(f'Validated {len(tables)} distinct matched tables; {len(tables)*len(seeds)} searches', flush=True)
    if args.dry_run:
        return
    with ProcessPoolExecutor(max_workers=args.jobs) as pool:
        futures = [pool.submit(run_one, root, scenario, k, seed, args.population, args.generations,
                               args.evaluation_budget) for scenario, k in tables for seed in seeds]
        for future in as_completed(futures):
            print(json.dumps(future.result()), flush=True)
    write_json(root/'completed.json', dict(state='completed', tasks=len(tables)*len(seeds)))


if __name__ == '__main__':
    main()
