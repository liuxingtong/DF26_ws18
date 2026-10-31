import sys,json
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from engine.optimization.models import ZoneDecision,ParameterDecision
import run_dapuqiao_optimization as exporter

def test_zone_decision_archive_preserves_full_precision():
    c=SimpleNamespace(solution_id='N_00001',decisions=[ZoneDecision('Z1','densify',.12345678901234567)])
    r=json.loads(json.dumps(exporter.decision_record(c)))
    assert r['solution_id']==c.solution_id
    assert r['decision_type']=='zone_operator'
    assert r['decisions'][0]['intensity']==c.decisions[0].intensity

def test_parameter_archive_has_unrounded_values():
    c=SimpleNamespace(solution_id='P_00001',decisions=[ParameterDecision('Z1',1.123456789012345,.876543210987654)])
    r=json.loads(json.dumps(exporter.decision_record(c)))
    assert r['decision_type']=='parameter'
    assert r['decisions'][0]['height_multiplier']==c.decisions[0].height_multiplier
    assert r['decisions'][0]['footprint_ratio']==c.decisions[0].footprint_ratio
