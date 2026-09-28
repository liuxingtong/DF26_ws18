import inspect
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

import geopandas as gpd
import pandas as pd
from shapely.geometry import LineString, box


WS05 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WS05))

from engine.optimization.constraints import check_constraints, constraint_policy  # noqa: E402
from engine.optimization.data import CONFIG_ROOT, load_study, load_yaml  # noqa: E402
from engine.optimization.models import CandidateEvaluation, ZoneDecision  # noqa: E402
from engine.optimization.models import ParameterDecision  # noqa: E402
from engine.optimization.metrics import (  # noqa: E402
    front_distribution,
    holm_adjust,
    hypervolume,
    paired_wilcoxon,
    spacing,
)
from engine.optimization.nsga2 import run_nsga2  # noqa: E402
from engine.optimization.objectives import build_objective_context, evaluate_objectives  # noqa: E402
from engine.optimization.operators import apply_decisions  # noqa: E402
from engine.optimization.operators import build_operator_availability  # noqa: E402
from engine.optimization.operators import build_operator_impact_counts  # noqa: E402
from engine.optimization.pareto import nondominated, pareto_sets  # noqa: E402
from engine.optimization.parameter_baseline import (  # noqa: E402
    apply_parameter_decisions,
    run_parameter_baseline,
)
from engine.optimization.roles import evaluate_roles  # noqa: E402


def synthetic_city():
    buildings = gpd.GeoDataFrame(
        [
            {"bid": "B1", "height_m": 10.0, "stakeholder_proxy": "resident",
             "residential_proxy": True, "heritage": False, "editable": True, "zone_id": "Z1",
             "geometry": box(10, 10, 30, 30)},
            {"bid": "B2", "height_m": 12.0, "stakeholder_proxy": "developer",
             "residential_proxy": False, "heritage": False, "editable": True, "zone_id": "Z2",
             "geometry": box(60, 10, 80, 30)},
        ],
        crs=32651,
    )
    buildings["base_height_m"] = buildings["height_m"]
    buildings["base_area_m2"] = buildings.geometry.area
    boundary = gpd.GeoDataFrame([{"geometry": box(0, 0, 100, 100)}], crs=32651)
    streets = gpd.GeoDataFrame([{"geometry": LineString([(0, 5), (100, 5)])}], crs=32651)
    zones = gpd.GeoDataFrame([
        {"zone_id": "Z1", "geometry": box(0, 0, 50, 100)},
        {"zone_id": "Z2", "geometry": box(50, 0, 100, 100)},
    ], crs=32651)
    controls = pd.DataFrame([
        {"zone_id": "Z1", "height_limit_m": 30, "max_far": 5, "max_coverage_ratio": 0.8},
        {"zone_id": "Z2", "height_limit_m": 30, "max_far": 5, "max_coverage_ratio": 0.8},
    ])
    scenario = {"defaults": {"minimum_residential_retention": 0.8, "street_access_buffer_m": 10}}
    specs = {
        "noop": {},
        "densify": {"parameters": {"maximum_height_gain_ratio": 0.3}},
        "open_ground": {"parameters": {"minimum_footprint_ratio": 0.75, "compensate_gfa": True}},
    }
    return buildings, boundary, streets, zones, controls, scenario, specs


class OptimizationFrameworkTests(unittest.TestCase):
    def test_operator_is_explicit_and_traced(self):
        buildings, _, _, _, controls, _, specs = synthetic_city()
        after, changes = apply_decisions(
            buildings, [ZoneDecision("Z2", "densify", 1.0)], controls, specs
        )
        self.assertEqual(len(changes), 1)
        self.assertEqual(changes[0]["bid"], "B2")
        self.assertAlmostEqual(float(after.loc[after.bid.eq("B2"), "height_m"].iloc[0]), 15.6)
        self.assertEqual(float(buildings.loc[buildings.bid.eq("B2"), "height_m"].iloc[0]), 12.0)

    def test_open_ground_improves_released_ground_proxy(self):
        buildings, boundary, streets, _, controls, scenario, specs = synthetic_city()
        after, changes = apply_decisions(
            buildings, [ZoneDecision("Z1", "open_ground", 1.0)], controls, specs
        )
        objectives, _ = evaluate_objectives(
            buildings, after, changes, boundary, streets, scenario,
            objective_config={"measurement": {"street_access_buffer_m": 10.0}},
        )
        self.assertGreater(objectives["street_connected_released_ground"], 0)
        self.assertGreater(objectives["residential_disruption"], 0)
        self.assertTrue(after.loc[after.bid.eq("B1"), "geometry"].iloc[0].within(
            buildings.loc[buildings.bid.eq("B1"), "geometry"].iloc[0]
        ))

    def test_development_capacity_sums_positive_building_gfa_not_net_change(self):
        buildings, boundary, streets, _, _, scenario, _ = synthetic_city()
        candidate = buildings.copy()
        candidate.loc[candidate.bid.eq("B1"), "geometry"] = box(10, 10, 20, 20)
        candidate.loc[candidate.bid.eq("B2"), "height_m"] = 13.0
        changes = [{"bid": "B1", "operator": "open_ground"},
                   {"bid": "B2", "operator": "densify"}]
        objectives, descriptors = evaluate_objectives(
            buildings, candidate, changes, boundary, streets, scenario
        )
        self.assertGreater(objectives["development_capacity"], 0.0)
        self.assertLess(descriptors["net_gfa_change_m2"], 0.0)
        self.assertAlmostEqual(
            descriptors["positive_gfa_increment_m2"], 400.0 / 3.5
        )

    def test_street_buffer_is_fixed_by_objective_config(self):
        buildings, boundary, streets, _, _, scenario, _ = synthetic_city()
        config = {"measurement": {"street_access_buffer_m": 5.0}}
        first = build_objective_context(
            buildings, boundary, streets,
            {**scenario, "defaults": {"street_access_buffer_m": 1.0}}, config,
        )
        second = build_objective_context(
            buildings, boundary, streets,
            {**scenario, "defaults": {"street_access_buffer_m": 99.0}}, config,
        )
        self.assertEqual(first.street_access_buffer_m, 5.0)
        self.assertTrue(first.street_access.equals(second.street_access))

    def test_sub_resolution_change_is_filtered(self):
        buildings, _, _, _, controls, _, specs = synthetic_city()
        after, changes = apply_decisions(
            buildings,
            [ZoneDecision("Z2", "densify", 0.001)],
            controls,
            specs,
            minimum_change={
                "minimum_building_gfa_change_m2": 1.0,
                "minimum_building_footprint_change_m2": 1.0,
                "minimum_building_height_change_m": 0.1,
            },
        )
        self.assertEqual(changes, [])
        self.assertEqual(
            float(after.loc[after.bid.eq("B2"), "height_m"].iloc[0]), 12.0
        )

    def test_height_violation_is_reported(self):
        buildings, boundary, _, zones, controls, scenario, _ = synthetic_city()
        candidate = buildings.copy()
        candidate.loc[candidate.bid.eq("B2"), "height_m"] = 40
        violations = check_constraints(buildings, candidate, boundary, zones, controls, scenario)
        self.assertIn("height_limit", {item.code for item in violations})
        violation = next(item for item in violations if item.code == "height_limit")
        self.assertEqual(violation.severity, "blocking")
        self.assertEqual(violation.action, "reject_candidate")

    def test_constraint_policy_covers_all_emitted_codes(self):
        policy = constraint_policy()
        configured = {
            str(rule["violation_code"]): rule for rule in policy.values()
        }
        expected = {
            "geometry", "boundary", "heritage", "height_limit", "zone_far",
            "zone_coverage", "residential_retention", "new_overlap", "change_scope",
        }
        self.assertEqual(set(configured), expected)
        self.assertTrue(all(rule.get("severity") == "blocking" for rule in configured.values()))
        self.assertTrue(
            all(rule.get("handling") == "reject_candidate" for rule in configured.values())
        )

    def test_public_space_context_is_excluded_from_objective_inputs(self):
        parameters = inspect.signature(evaluate_objectives).parameters
        self.assertNotIn("public_space", parameters)
        config = load_yaml(CONFIG_ROOT / "objectives.yaml")
        dependency = config["data_dependencies"]["street_connected_released_ground"]
        self.assertEqual(
            set(dependency["required_layers"]),
            {"buildings.parquet", "street_network.geojson", "study_boundary.geojson"},
        )
        self.assertEqual(
            set(dependency["excluded_context_layers"]),
            {
                "public_space_candidates.geojson", "public_space_verification.json",
                "alley_entrances.geojson", "alley_entrance_verification.json",
            },
        )
        study = load_study("tourism_capture")
        self.assertEqual(study.blockers, [])
        self.assertTrue(
            study.public_space_candidates["include_in_objective"].eq(False).all()
        )
        self.assertEqual(len(study.alley_entrances), 2)
        self.assertTrue(study.alley_entrances["include_in_optimization"].eq(False).all())
        self.assertTrue(study.alley_entrances["include_in_objective"].eq(False).all())
        self.assertEqual(
            study.alley_entrance_verification["summary"]["verified_research_entrance"],
            1,
        )
        self.assertEqual(
            study.formal_input_quality["counts"][
                "heritage_official_records_unresolved_and_excluded"
            ],
            4,
        )
        self.assertEqual(
            study.formal_input_quality["counts"]["buildings_unmatched_and_frozen"],
            32,
        )

    def test_densify_allocates_only_remaining_zone_far(self):
        buildings, boundary, streets, zones, controls, scenario, specs = synthetic_city()
        controls["max_far"] = controls["max_far"].astype(float)
        controls.loc[controls["zone_id"].eq("Z2"), "max_far"] = 0.30
        after, changes = apply_decisions(
            buildings, [ZoneDecision("Z2", "densify", 1.0)], controls, specs, zones
        )
        # Z2 is 5,000 m². FAR 0.30 allows 1,500 m² GFA, or height 13.125 m
        # for the single 400 m² footprint. The raw 30% request would be 15.6 m.
        actual_height = float(after.loc[after.bid.eq("B2"), "height_m"].iloc[0])
        self.assertAlmostEqual(actual_height, 13.125)
        self.assertLess(float(changes[0]["capacity_allocation_ratio"]), 1.0)
        violations = check_constraints(buildings, after, boundary, zones, controls, scenario)
        self.assertNotIn("zone_far", {item.code for item in violations})

    def test_operator_availability_excludes_frozen_zone(self):
        buildings, _, _, zones, controls, _, _ = synthetic_city()
        buildings.loc[buildings["zone_id"].eq("Z1"), "heritage"] = True
        buildings.loc[buildings["zone_id"].eq("Z1"), "editable"] = False
        availability = build_operator_availability(buildings, zones, controls)
        self.assertEqual(availability["Z1"], ("noop",))
        self.assertIn("densify", availability["Z2"])
        self.assertIn("open_ground", availability["Z2"])
        impacts = build_operator_impact_counts(buildings, zones, controls)
        self.assertEqual(impacts[("Z1", "open_ground")], 0)
        self.assertEqual(impacts[("Z2", "open_ground")], 1)

    def test_scenario_policy_limits_operator_targets_and_intensity(self):
        buildings, _, _, zones, controls, _, specs = synthetic_city()
        scenario = {"operator_policy": {
            "allowed_operators": ["open_ground"],
            "stakeholder_targets": {"open_ground": ["developer"]},
            "maximum_intensity": {"open_ground": 0.4},
        }}
        availability = build_operator_availability(buildings, zones, controls, scenario)
        self.assertEqual(availability["Z1"], ("noop",))
        self.assertEqual(availability["Z2"], ("noop", "open_ground"))
        after, changes = apply_decisions(
            buildings, [ZoneDecision("Z2", "open_ground", 1.0)], controls, specs, zones,
            scenario=scenario,
        )
        self.assertEqual(len(changes), 1)
        self.assertAlmostEqual(changes[0]["intensity"], 0.4)
        self.assertLess(after.loc[after.bid.eq("B2"), "geometry"].iloc[0].area, 400.0)

    def test_only_new_overlap_is_reported(self):
        buildings, boundary, _, zones, controls, scenario, _ = synthetic_city()
        candidate = buildings.copy()
        candidate.loc[candidate.bid.eq("B2"), "geometry"] = box(25, 10, 70, 30)
        violations = check_constraints(buildings, candidate, boundary, zones, controls, scenario)
        self.assertIn("new_overlap", {item.code for item in violations})

    def test_changed_building_scope_is_enforced(self):
        buildings, boundary, _, zones, controls, scenario, _ = synthetic_city()
        candidate = buildings.copy()
        candidate["height_m"] = candidate["height_m"] + 1.0
        limited = {
            **scenario,
            "implementation": {"maximum_changed_building_ratio": 0.25},
        }
        violations = check_constraints(
            buildings, candidate, boundary, zones, controls, limited
        )
        self.assertIn("change_scope", {item.code for item in violations})

    def test_pareto_and_role_evaluation(self):
        def candidate(sid, residential, development, public):
            return CandidateEvaluation(
                sid, [], None, [],
                {"residential_disruption": residential, "development_capacity": development,
                 "street_connected_released_ground": public},
                {}, [],
            )

        candidates = [candidate("A", 0.1, 0.1, 0.1), candidate("B", 0.2, 0.2, 0.2),
                      candidate("C", 0.3, 0.05, 0.05)]
        front = nondominated(candidates)
        self.assertEqual({item.solution_id for item in front}, {"A", "B"})
        config = {"roles": {"resident": {"weights": {
            "residential_disruption": 1.0,
            "development_capacity": 0.0,
            "street_connected_released_ground": 0.0,
        }, "thresholds": {}}}}
        _, selected = evaluate_roles(front, config)
        self.assertEqual(selected["resident"], "A")

    def test_pareto_pipeline_keeps_full_front_and_filters_epsilon_equivalents(self):
        def candidate(sid, disruption, development, bid):
            return CandidateEvaluation(
                sid, [], None,
                [{"bid": bid, "after_height_m": 10.0, "after_area_m2": 10.0}],
                {"residential_disruption": disruption, "development_capacity": development,
                 "street_connected_released_ground": 0.0},
                {}, [],
            )

        config = {
            "epsilon": {
                "residential_disruption": 0.001,
                "development_capacity": 0.0005,
                "street_connected_released_ground": 0.00005,
            },
            "normalization_reference": {
                "residential_disruption": {"minimum": 0.0, "maximum": 0.3},
                "development_capacity": {"minimum": 0.0, "maximum": 0.01},
                "street_connected_released_ground": {"minimum": 0.0, "maximum": 0.0025},
            },
        }
        full, epsilon_front, representatives, diagnostics = pareto_sets(
            [candidate("A", 0.0, 0.0, "A"), candidate("B", 0.0005, 0.0002, "B")], config
        )
        self.assertEqual(len(full), 2)
        self.assertEqual(len(epsilon_front), 1)
        self.assertEqual(len(representatives), 1)
        self.assertEqual(diagnostics["full_pareto_count"], 2)
        self.assertEqual(diagnostics["objective_duplicate_count"], 1)

    def test_fixed_role_bounds_make_scores_independent_of_other_candidates(self):
        def candidate(sid, disruption, development, released):
            return CandidateEvaluation(
                sid, [], None, [],
                {"residential_disruption": disruption,
                 "development_capacity": development,
                 "street_connected_released_ground": released},
                {}, [],
            )

        a = candidate("A", 0.1, 0.004, 0.001)
        b = candidate("B", 0.2, 0.008, 0.002)
        c = candidate("C", 0.01, 0.0001, 0.0001)
        config = {"roles": {"planner": {"weights": {
            "residential_disruption": 0.4,
            "development_capacity": 0.3,
            "street_connected_released_ground": 0.3,
        }, "thresholds": {}}}}
        bounds = {
            "residential_disruption": {"minimum": 0.0, "maximum": 0.3},
            "development_capacity": {"minimum": 0.0, "maximum": 0.01},
            "street_connected_released_ground": {"minimum": 0.0, "maximum": 0.0025},
        }
        first, _ = evaluate_roles([a, b], config, bounds)
        second, _ = evaluate_roles([a, c], config, bounds)
        score = lambda rows: next(row["score"] for row in rows if row["solution_id"] == "A")
        self.assertAlmostEqual(score(first), score(second))

    def test_nsga2_backend_runs_single_pass(self):
        buildings, boundary, streets, zones, controls, scenario, specs = synthetic_city()
        study = SimpleNamespace(
            buildings=buildings,
            boundary=boundary,
            streets=streets,
            zones=zones,
            controls=controls,
            scenario={**scenario, "implementation": {"maximum_changed_zone_ratio": 0.5}},
            blockers=[],
        )
        candidates, front, metadata = run_nsga2(
            study, specs, population=4, generations=1, seed=11
        )
        self.assertGreaterEqual(len(candidates), 2)
        self.assertGreaterEqual(len(front), 1)
        self.assertEqual(metadata["backend"], "nsga2")
        self.assertEqual(metadata["effective_evaluation_budget"], 4)
        self.assertEqual(metadata["unique_evaluations"], 4)
        self.assertFalse(metadata["building_scope_repair_enabled"])
        self.assertTrue(metadata["convergence"])

    def test_parameter_baseline_ignores_stakeholder_editability_but_not_heritage(self):
        buildings, boundary, streets, zones, controls, scenario, _ = synthetic_city()
        buildings.loc[buildings["bid"].eq("B2"), "editable"] = False
        study = SimpleNamespace(
            buildings=buildings,
            boundary=boundary,
            streets=streets,
            zones=zones,
            controls=controls,
            scenario={**scenario, "implementation": {"maximum_changed_building_ratio": 1.0}},
        )
        after, changes = apply_parameter_decisions(
            study, [ParameterDecision("Z2", 1.2, 1.0)]
        )
        self.assertEqual({item["bid"] for item in changes}, {"B2"})
        self.assertGreater(float(after.loc[after["bid"].eq("B2"), "height_m"].iloc[0]), 12.0)
        study.buildings.loc[study.buildings["bid"].eq("B2"), "heritage"] = True
        _, protected_changes = apply_parameter_decisions(
            study, [ParameterDecision("Z2", 1.2, 0.8)]
        )
        self.assertEqual(protected_changes, [])

    def test_parameter_baseline_records_monotone_convergence(self):
        buildings, boundary, streets, zones, controls, scenario, _ = synthetic_city()
        study = SimpleNamespace(
            buildings=buildings,
            boundary=boundary,
            streets=streets,
            zones=zones,
            controls=controls,
            scenario={**scenario, "implementation": {
                "maximum_changed_zone_ratio": 1.0,
                "maximum_changed_building_ratio": 1.0,
            }},
            objective_config={"measurement": {"street_access_buffer_m": 5.0}},
            blockers=[],
        )
        config = {"baseline": {
            "id": "test_parameter_baseline",
            "label": "Test parameter baseline",
            "parameters": {
                "height_multiplier": {"min": 1.0, "max": 1.3},
                "footprint_ratio": {"min": 0.75, "max": 1.0},
            },
            "implementation": {
                "maximum_changed_zone_ratio": 1.0,
                "maximum_changed_building_ratio": 1.0,
            },
        }}
        _, _, metadata = run_parameter_baseline(
            study, config, population=4, generations=2, seed=19,
            evaluation_budget=4,
        )
        self.assertTrue(metadata["convergence"])
        effective = [
            row["effective_independent_evaluations"]
            for row in metadata["convergence"]
        ]
        calls = [row["evaluation_calls"] for row in metadata["convergence"]]
        self.assertEqual(effective, sorted(effective))
        self.assertEqual(calls, sorted(calls))
        self.assertEqual(effective[-1], 4)

    def test_quality_metrics_are_deterministic(self):
        candidate = CandidateEvaluation(
            "A", [], None, [],
            {"residential_disruption": 0.0, "development_capacity": 1.0,
             "street_connected_released_ground": 1.0},
            {}, [],
        )
        config = {"normalization_reference": {
            "residential_disruption": {"minimum": 0.0, "maximum": 1.0},
            "development_capacity": {"minimum": 0.0, "maximum": 1.0},
            "street_connected_released_ground": {"minimum": 0.0, "maximum": 1.0},
        }}
        self.assertAlmostEqual(hypervolume([candidate], config, (1.0, 1.0, 1.0)), 1.0)
        self.assertEqual(spacing([candidate], config), 0.0)
        rows = front_distribution([candidate], "epsilon_filtered")
        self.assertEqual(len(rows), 3)
        development = next(row for row in rows if row["objective"] == "development_capacity")
        self.assertEqual(development["direction"], "maximize")
        self.assertEqual(development["minimum"], 1.0)
        self.assertEqual(development["maximum"], 1.0)

    def test_paired_statistics_respect_metric_direction_and_ties(self):
        result = paired_wilcoxon(
            [3.0, 2.0, 2.0, 1.0],
            [2.0, 2.0, 1.0, 0.5],
            higher_is_better=False,
        )
        self.assertEqual(result["comparison_wins"], 3)
        self.assertEqual(result["ties"], 1)
        self.assertEqual(result["comparison_losses"], 0)
        self.assertGreater(result["rank_biserial_effect"], 0.0)

    def test_holm_adjustment_is_monotone_in_sorted_p_values(self):
        adjusted = holm_adjust([0.04, 0.01, 0.03, 0.20])
        ordered = sorted(zip([0.04, 0.01, 0.03, 0.20], adjusted))
        adjusted_in_p_order = [value for _, value in ordered]
        self.assertEqual(adjusted_in_p_order, sorted(adjusted_in_p_order))
        self.assertTrue(all(0.0 <= value <= 1.0 for value in adjusted))

    def test_nsga2_is_reproducible_for_same_seed(self):
        buildings, boundary, streets, zones, controls, scenario, specs = synthetic_city()
        study = SimpleNamespace(
            buildings=buildings,
            boundary=boundary,
            streets=streets,
            zones=zones,
            controls=controls,
            scenario={**scenario, "implementation": {
                "maximum_changed_zone_ratio": 0.5,
                "maximum_changed_building_ratio": 1.0,
            }},
            blockers=[],
        )
        first, _, first_metadata = run_nsga2(
            study, specs, population=4, generations=2, seed=17
        )
        second, _, second_metadata = run_nsga2(
            study, specs, population=4, generations=2, seed=17
        )
        first_signature = [
            ([vars(item) for item in candidate.decisions], candidate.objectives)
            for candidate in first
        ]
        second_signature = [
            ([vars(item) for item in candidate.decisions], candidate.objectives)
            for candidate in second
        ]
        self.assertEqual(first_signature, second_signature)
        self.assertEqual(first_metadata["convergence"], second_metadata["convergence"])
        self.assertGreaterEqual(len(first_metadata["convergence"]), 2)
        effective = [
            row["effective_independent_evaluations"]
            for row in first_metadata["convergence"]
        ]
        self.assertEqual(effective, sorted(effective))
        evaluation_calls = [
            row["evaluation_calls"] for row in first_metadata["convergence"]
        ]
        self.assertEqual(evaluation_calls, sorted(evaluation_calls))


if __name__ == "__main__":
    unittest.main()
