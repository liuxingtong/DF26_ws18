"""Exposure must be determined by geometry, never by operation names."""
import sys
from pathlib import Path
import unittest
from shapely.geometry import box, MultiPolygon
sys.path.insert(0,str(Path(__file__).parent))
from test_optimization_framework import synthetic_city
from engine.optimization.objectives import evaluate_objectives

class ActualGeometryExposureTests(unittest.TestCase):
    def setUp(self):
        self.base,self.boundary,self.streets,*_=synthetic_city()
        self.base.loc[self.base.bid.eq('B2'),'zone_id']='Z1'
    def exposure(self,after,op='open_ground',bid='B2',changes=True):
        return evaluate_objectives(self.base,after,[{'bid':bid,'operator':op}] if changes else [],self.boundary,self.streets,{},objective_config={'numerical_resolution':{'minimum_building_height_change_m':.1,'minimum_building_footprint_change_m2':1.0}})[0]['residential_disruption']
    def test_compensated_height_exposure_is_operator_invariant(self):
        after=self.base.copy();after.loc[after.bid.eq('B2'),'height_m']=16.0
        after.loc[after.bid.eq('B2'),'geometry']=box(60,10,75,30)
        vals=[self.exposure(after,op) for op in ['open_ground','densify','parameter_height_footprint','other_name']]
        self.assertEqual(vals,[1.0]*4)
    def test_geometry_change_is_detected_without_operator_log(self):
        after=self.base.copy();after.loc[after.bid.eq('B2'),'height_m']=16.0
        self.assertEqual(self.exposure(after,changes=False),1.0)
    def test_noop_does_not_expose_neighbours(self):
        self.assertEqual(self.exposure(self.base.copy(),'densify'),0.0)
    def test_subresolution_height_does_not_expose_neighbours(self):
        after=self.base.copy();after.loc[after.bid.eq('B2'),'height_m']=12.05
        self.assertEqual(self.exposure(after,'densify'),0.0)
    def test_threshold_height_exposes_neighbours(self):
        after=self.base.copy();after.loc[after.bid.eq('B2'),'height_m']=12.1
        self.assertEqual(self.exposure(after),1.0)
    def test_height_reduction_alone_does_not_expose_neighbours(self):
        after=self.base.copy();after.loc[after.bid.eq('B2'),'height_m']=10.0
        self.assertEqual(self.exposure(after,'heritage_step_down'),0.0)
    def test_shrink_without_height_or_split_only_has_direct_effect(self):
        after=self.base.copy();after.loc[after.bid.eq('B2'),'geometry']=box(60,10,75,30)
        self.assertEqual(self.exposure(after,'parameter_height_footprint'),0.0)
    def test_physical_split_exposes_neighbours_under_any_name(self):
        after=self.base.copy();after.loc[after.bid.eq('B2'),'geometry']=MultiPolygon([box(60,10,68,30),box(72,10,80,30)])
        self.assertEqual(self.exposure(after,'open_ground'),1.0)
    def test_existing_multipart_is_not_a_new_split(self):
        self.base.loc[self.base.bid.eq('B2'),'geometry']=MultiPolygon([box(60,10,68,30),box(72,10,80,30)])
        after=self.base.copy();after.loc[after.bid.eq('B2'),'geometry']=MultiPolygon([box(60,10,67,30),box(73,10,80,30)])
        self.assertEqual(self.exposure(after,'split_to_towers'),0.0)
    def test_missing_zone_never_connects_unmatched_buildings(self):
        self.base['zone_id']=None;after=self.base.copy();after.loc[after.bid.eq('B2'),'height_m']=16.0
        self.assertEqual(self.exposure(after),0.0)
    def test_direct_residential_change_is_detected_without_log(self):
        after=self.base.copy();after.loc[after.bid.eq('B1'),'geometry']=box(10,10,20,30)
        self.assertEqual(self.exposure(after,bid='B1',changes=False),1.0)
    def test_different_shape_at_equal_area_is_a_direct_change(self):
        after=self.base.copy();after.loc[after.bid.eq('B1'),'geometry']=box(11,10,31,30)
        self.assertEqual(self.exposure(after,bid='B1',changes=False),1.0)
