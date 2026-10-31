"""Permission-matched random tables; building labels and exposure masks stay fixed."""
from copy import deepcopy
import numpy as np
from .operators import _eligible_for_operator, operator_policy


def _sets(buildings, scenario, operator):
    valid=buildings['zone_id'].notna() & ~buildings['heritage'].fillna(False)
    original=buildings[valid & _eligible_for_operator(buildings,operator,scenario)]
    unrestricted=deepcopy(scenario);unrestricted.pop('permission_overrides',None)
    unrestricted['operator_policy']['stakeholder_targets']={}
    pool=buildings[valid & _eligible_for_operator(buildings,operator,unrestricted)]
    return original,pool


def validate_permission_table(buildings, scenario, table, tolerance=.05):
    allowed,_,_=operator_policy(scenario)
    if set(table)!=allowed:raise ValueError('Permission table must cover exactly the allowed operators')
    report={}
    indexed=buildings.set_index(buildings['bid'].astype(str))
    for op in sorted(allowed):
        original,pool=_sets(buildings,scenario,op)
        ids=list(map(str,table[op]))
        if len(ids)!=len(set(ids)) or not set(ids)<=set(pool['bid'].astype(str)):
            raise ValueError(f'{op}: duplicate IDs or frozen/ineligible buildings')
        selected=indexed.loc[ids] if ids else indexed.iloc[:0]
        counts=lambda d:{str(k):int(v) for k,v in d.groupby(d['zone_id'].astype(str)).size().items()}
        if counts(original)!=counts(selected):raise ValueError(f'{op}: per-zone counts differ')
        gfa=lambda d:float((d.geometry.area*d['height_m']/3.5).sum())
        target=gfa(original);actual=gfa(selected)
        error=abs(actual-target)/target if target else (0. if not actual else float('inf'))
        if error>tolerance+1e-12:raise ValueError(f'{op}: GFA matching error {error:.4f} exceeds {tolerance}')
        randomizable=sum(0<n<len(pool[pool['zone_id'].astype(str)==str(z)]) for z,n in original.groupby(original['zone_id'].astype(str)).size().items())
        report[op]={'count':len(ids),'original_gfa_m2':target,'randomized_gfa_m2':actual,'gfa_relative_error':error,
                    'randomizable_units':int(randomizable),'changed_membership':set(ids)!=set(original['bid'].astype(str))}
    return report


def generate_permission_table(buildings, scenario, seed, max_attempts=10000, tolerance=.05):
    rng=np.random.default_rng(seed);allowed,_,_=operator_policy(scenario);table={};attempts={}
    for op in sorted(allowed):
        original,pool=_sets(buildings,scenario,op)
        quotas=original.groupby(original['zone_id'].astype(str)).size().to_dict()
        pools={str(z):g['bid'].astype(str).to_numpy() for z,g in pool.groupby(pool['zone_id'].astype(str))}
        target=float((original.geometry.area*original['height_m']/3.5).sum())
        gfa_by_id=dict(zip(pool['bid'].astype(str),pool.geometry.area*pool['height_m']/3.5))
        flexible=any(0<n<len(pools[str(z)]) for z,n in quotas.items())
        original_ids=set(original['bid'].astype(str))
        for attempt in range(1,max_attempts+1):
            ids=sorted(str(b) for z,n in sorted(quotas.items()) for b in rng.choice(pools[str(z)],size=n,replace=False))
            if flexible and set(ids)==original_ids:continue
            total=sum(float(gfa_by_id[b]) for b in ids)
            if (not target and not total) or (target and abs(total-target)/target<=tolerance+1e-12):
                table[op]=ids;attempts[op]=attempt;break
        else:raise RuntimeError(f'{op}: no non-identical area-matched permission set after {max_attempts} attempts')
    diagnostics=validate_permission_table(buildings,scenario,table,tolerance)
    for op in diagnostics:diagnostics[op]['attempts']=attempts[op]
    return table,diagnostics
