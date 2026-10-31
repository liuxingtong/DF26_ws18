import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from test_optimization_framework import synthetic_city
from engine.optimization.operators import _eligible_for_operator,apply_decisions,build_operator_availability
import engine.optimization.permission_null as null

class PermissionNullTests(unittest.TestCase):
    def setUp(self):
        self.b,self.boundary,self.streets,self.zones,self.controls,self.s,self.specs=synthetic_city()
        # Two equal-GFA buildings within the same unit, with different stakeholder labels.
        self.b['zone_id']='Z1';self.b['height_m']=10.;self.b['base_height_m']=10.
        self.s={'operator_policy':{'allowed_operators':['densify'],'stakeholder_targets':{'densify':['developer']},'maximum_intensity':{'densify':1}},'defaults':{}}
    def test_random_permission_changes_objects_without_relabelling(self):
        before=self.b.copy()
        table,diag=null.generate_permission_table(self.b,self.s,seed=7,max_attempts=100)
        self.assertEqual(table['densify'],['B1'])
        self.assertTrue(self.b.equals(before))
        self.assertEqual(diag['densify']['gfa_relative_error'],0.)
        scenario={**self.s,'permission_overrides':table}
        mask=_eligible_for_operator(self.b,'densify',scenario)
        self.assertEqual(self.b.loc[mask,'bid'].tolist(),['B1'])
        after,changes=apply_decisions(self.b,[__import__('engine.optimization.models',fromlist=['ZoneDecision']).ZoneDecision('Z1','densify',1)],self.controls,self.specs,scenario=scenario)
        self.assertEqual([r['bid'] for r in changes],['B1'])
    def test_table_reproducible_and_validated(self):
        a,diag=null.generate_permission_table(self.b,self.s,seed=7)
        b,_=null.generate_permission_table(self.b,self.s,seed=7)
        self.assertEqual(a,b)
        null.validate_permission_table(self.b,self.s,a)
    def test_frozen_heritage_never_in_pool(self):
        self.b.loc[self.b.bid.eq('B1'),'heritage']=True
        a,diag=null.generate_permission_table(self.b,self.s,seed=1)
        self.assertEqual(a['densify'],['B2'])
        self.assertEqual(diag['densify']['randomizable_units'],0)
    def test_mismatched_count_or_area_is_rejected(self):
        with self.assertRaises(ValueError):null.validate_permission_table(self.b,self.s,{'densify':[]})
        self.b.loc[self.b.bid.eq('B1'),'height_m']=20
        with self.assertRaises(ValueError):null.validate_permission_table(self.b,self.s,{'densify':['B1']})
    def test_unmatchable_alternative_is_not_silently_used(self):
        self.b.loc[self.b.bid.eq('B1'),'height_m']=20
        with self.assertRaises(RuntimeError):null.generate_permission_table(self.b,self.s,seed=3,max_attempts=30)
