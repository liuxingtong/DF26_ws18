from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any

import geopandas as gpd
import pandas as pd
import yaml
from shapely.geometry import box


WS05 = Path(__file__).resolve().parents[2]
DATA_ROOT = WS05 / "data" / "dapuqiao"
CONFIG_ROOT = WS05 / "optimization"
TARGET_CRS = "EPSG:32651"


@dataclass
class StudyData:
    buildings: gpd.GeoDataFrame
    boundary: gpd.GeoDataFrame
    streets: gpd.GeoDataFrame
    services: gpd.GeoDataFrame
    public_space_candidates: gpd.GeoDataFrame
    public_space_verification: dict[str, Any]
    alley_entrances: gpd.GeoDataFrame
    alley_entrance_verification: dict[str, Any]
    zones: gpd.GeoDataFrame | None
    controls: pd.DataFrame | None
    heritage: gpd.GeoDataFrame | None
    scenario: dict[str, Any]
    objective_config: dict[str, Any]
    blockers: list[str]
    warnings: list[str]
    source_status: dict[str, str]
    formal_input_quality: dict[str, Any]


def load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _read_geojson(path: Path, target_crs: Any) -> gpd.GeoDataFrame:
    frame = gpd.read_file(path)
    if frame.crs is None:
        frame = frame.set_crs(4326)
    return frame.to_crs(target_crs)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _normalise_buildings(frame: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    frame = frame.copy()
    if frame.crs is None:
        frame = frame.set_crs(TARGET_CRS)
    frame = frame.to_crs(TARGET_CRS).reset_index(drop=True)
    if "bid" not in frame:
        frame["bid"] = [f"B_{index:05d}" for index in range(len(frame))]
    frame["bid"] = frame["bid"].astype(str)
    if "height_m" not in frame:
        raise ValueError("buildings.parquet 缺少 height_m")
    if "stakeholder" not in frame:
        raise ValueError("buildings.parquet 缺少 stakeholder；请先运行现有主体映射")
    frame["height_m"] = pd.to_numeric(frame["height_m"], errors="coerce")
    frame = frame[frame.geometry.notna() & frame["height_m"].gt(0)].copy()
    frame["base_height_m"] = frame["height_m"].astype(float)
    frame["base_area_m2"] = frame.geometry.area.astype(float)
    frame["stakeholder_proxy"] = frame["stakeholder"].fillna("unknown").astype(str)
    frame["residential_proxy"] = frame["stakeholder_proxy"].eq("resident")
    frame["heritage"] = False
    frame["editable"] = ~frame["stakeholder_proxy"].eq("state")
    frame["zone_id"] = None
    return frame


def _attach_heritage(buildings: gpd.GeoDataFrame, heritage: gpd.GeoDataFrame | None) -> gpd.GeoDataFrame:
    if heritage is None or heritage.empty:
        return buildings
    result = buildings.copy()
    if "bid" in heritage.columns:
        ids = set(heritage["bid"].dropna().astype(str))
        result["heritage"] = result["bid"].isin(ids)
    else:
        joined = gpd.sjoin(
            result[["bid", "geometry"]],
            heritage[["geometry"]],
            how="inner",
            predicate="intersects",
        )
        result["heritage"] = result["bid"].isin(set(joined["bid"]))
    result.loc[result["heritage"], "editable"] = False
    return result


def _attach_zones(buildings: gpd.GeoDataFrame, zones: gpd.GeoDataFrame | None) -> gpd.GeoDataFrame:
    if zones is None or zones.empty:
        return buildings
    if "zone_id" not in zones:
        raise ValueError("intervention_zones.geojson 缺少 zone_id")
    result = buildings.drop(columns=["zone_id"]).copy()
    points = result[["bid", "geometry"]].copy()
    points["geometry"] = points.geometry.representative_point()
    joined = gpd.sjoin(points, zones[["zone_id", "geometry"]], how="left", predicate="within")
    zone_by_bid = joined.drop_duplicates("bid").set_index("bid")["zone_id"]
    result["zone_id"] = result["bid"].map(zone_by_bid)
    return result


def build_research_grid_zones(boundary: gpd.GeoDataFrame, target_cells: int = 25) -> gpd.GeoDataFrame:
    """Deterministic debug grid. It is never presented as planning or cadastral data."""
    geom = boundary.geometry.union_all()
    minx, miny, maxx, maxy = geom.bounds
    side_count = max(2, round(target_cells ** 0.5))
    width = (maxx - minx) / side_count
    height = (maxy - miny) / side_count
    rows = []
    counter = 1
    for ix in range(side_count):
        for iy in range(side_count):
            cell = box(minx + ix * width, miny + iy * height,
                       minx + (ix + 1) * width, miny + (iy + 1) * height).intersection(geom)
            if not cell.is_empty and cell.area > 1:
                rows.append({"zone_id": f"DEMO_Z{counter:02d}", "constraint_status": "research_demo", "geometry": cell})
                counter += 1
    return gpd.GeoDataFrame(rows, geometry="geometry", crs=boundary.crs)


def build_research_controls(zones: gpd.GeoDataFrame, scenario: dict[str, Any]) -> pd.DataFrame:
    defaults = scenario.get("defaults", {})
    return pd.DataFrame({
        "zone_id": zones["zone_id"].astype(str),
        "height_limit_m": float(defaults.get("height_limit_m", 36.0)),
        "max_far": float(defaults.get("max_far", 3.0)),
        "max_coverage_ratio": float(defaults.get("max_coverage_ratio", 0.60)),
        "allow_new_building": True,
        "constraint_status": "research_demo",
        "source": "scenario defaults; not official planning data",
    })


def load_study(
    scenario_name: str = "dapuqiao_tourism_livability",
    *,
    research_demo: bool = False,
    shared_experiment_controls: bool = False,
    data_root: Path = DATA_ROOT,
) -> StudyData:
    scenarios = load_yaml(CONFIG_ROOT / "scenarios.yaml").get("scenarios", {})
    if scenario_name not in scenarios:
        raise KeyError(f"未知情景：{scenario_name}")
    scenario = deepcopy(scenarios[scenario_name])
    objective_config = load_yaml(CONFIG_ROOT / "objectives.yaml")
    shared_defaults: dict[str, Any] = {}
    if shared_experiment_controls:
        assumptions = load_yaml(CONFIG_ROOT / "research_assumptions.yaml")
        shared_defaults = deepcopy(
            assumptions.get("planning_controls", {}).get("provisional_defaults", {})
        )
        if not shared_defaults:
            raise ValueError("research_assumptions.yaml 缺少共同 planning_controls.provisional_defaults")
        scenario.setdefault("defaults", {}).update(shared_defaults)

    buildings = _normalise_buildings(gpd.read_parquet(data_root / "buildings.parquet"))
    boundary = _read_geojson(data_root / "study_boundary.geojson", buildings.crs)
    streets = _read_geojson(data_root / "street_network.geojson", buildings.crs)
    services = _read_geojson(data_root / "public_services.geojson", buildings.crs)
    spaces = _read_geojson(data_root / "public_space_candidates.geojson", buildings.crs)
    alley_entrances_path = data_root / "alley_entrances.geojson"
    alley_entrances = (
        _read_geojson(alley_entrances_path, buildings.crs)
        if alley_entrances_path.exists()
        else gpd.GeoDataFrame(geometry=[], crs=buildings.crs)
    )

    zone_path = data_root / "intervention_zones.geojson"
    controls_path = data_root / "planning_controls.csv"
    heritage_path = data_root / "heritage_buildings.geojson"
    quality_path = data_root / "formal_input_quality.json"
    public_space_verification_path = data_root / "public_space_verification.json"
    alley_verification_path = data_root / "alley_entrance_verification.json"
    draft_zone_path = data_root / "drafts" / "intervention_zones.draft.geojson"
    draft_controls_path = data_root / "drafts" / "planning_controls.draft.csv"
    draft_heritage_path = data_root / "drafts" / "heritage_buildings.draft.geojson"
    zones = _read_geojson(zone_path, buildings.crs) if zone_path.exists() else None
    controls = pd.read_csv(controls_path) if controls_path.exists() else None
    heritage = _read_geojson(heritage_path, buildings.crs) if heritage_path.exists() else None
    formal_input_quality = (
        json.loads(quality_path.read_text(encoding="utf-8"))
        if quality_path.exists() else {}
    )
    public_space_verification = (
        json.loads(public_space_verification_path.read_text(encoding="utf-8"))
        if public_space_verification_path.exists() else {}
    )
    alley_entrance_verification = (
        json.loads(alley_verification_path.read_text(encoding="utf-8"))
        if alley_verification_path.exists() else {}
    )

    blockers: list[str] = []
    warnings: list[str] = []
    def input_status(frame, fallback: str = "available") -> str:
        if frame is None:
            return "missing"
        for column in ("input_status", "review_status"):
            if column in frame.columns:
                values = set(frame[column].dropna().astype(str))
                if values == {"formal_paper_model_input"}:
                    return "formal_paper_model_input"
                if values == {"frozen_research_input"}:
                    return "frozen_research_input"
        if "freeze_id" in frame.columns:
            return "frozen_research_annotation"
        return fallback

    status = {
        "buildings": "available",
        "study_boundary": "available_osm",
        "street_network": "available_osm",
        "public_services": "available_osm_candidate",
        "public_space": "context_only_mixed_verification",
        "public_space_verification": (
            "available_context_only" if public_space_verification else "missing"
        ),
        "alley_entrances": (
            "context_only_partial_verification" if len(alley_entrances) else "missing"
        ),
        "alley_entrance_verification": (
            "available_context_only" if alley_entrance_verification else "missing"
        ),
        "intervention_zones": input_status(zones),
        "planning_controls": input_status(controls),
        "heritage": input_status(heritage),
    }
    if zones is None:
        blockers.append("缺少 intervention_zones.geojson")
    if controls is None:
        blockers.append("缺少 planning_controls.csv")
    if heritage is None:
        blockers.append("缺少 heritage_buildings.geojson")
    canonical_paths = (zone_path, controls_path, heritage_path)
    if all(path.exists() for path in canonical_paths):
        if quality_path.exists():
            expected_hashes = formal_input_quality.get("sha256", {})
            mismatches = [
                path.name for path in canonical_paths
                if expected_hashes.get(path.name) != _sha256(path)
            ]
            if mismatches:
                blockers.append(
                    "规范输入与 formal_input_quality.json 的 SHA-256 不一致："
                    + ", ".join(mismatches)
                )
                status["formal_input_quality"] = "hash_mismatch"
            else:
                status["formal_input_quality"] = "verified_sha256"
        else:
            warnings.append("缺少 formal_input_quality.json，无法校验规范输入冻结哈希")
            status["formal_input_quality"] = "missing"

        if "zone_id" not in zones or zones["zone_id"].astype(str).duplicated().any():
            blockers.append("intervention_zones.geojson 的 zone_id 缺失或不唯一")
        elif "zone_id" not in controls:
            blockers.append("planning_controls.csv 缺少 zone_id")
        else:
            zone_ids = set(zones["zone_id"].astype(str))
            control_ids = set(controls["zone_id"].astype(str))
            if zone_ids != control_ids or controls["zone_id"].astype(str).duplicated().any():
                blockers.append("planning_controls.csv 未与更新单元一一对应")
        required_numeric = {"height_limit_m", "max_far", "max_coverage_ratio"}
        if not required_numeric.issubset(controls.columns):
            blockers.append("planning_controls.csv 缺少限高、FAR 或覆盖率字段")
        elif controls[list(required_numeric)].apply(pd.to_numeric, errors="coerce").isna().any().any():
            blockers.append("planning_controls.csv 存在空白或非数值控制指标")
        if not zones.geometry.is_valid.all():
            blockers.append("intervention_zones.geojson 存在无效几何")
        if "bid" not in heritage:
            blockers.append("heritage_buildings.geojson 缺少 bid")
        else:
            heritage_ids = set(heritage["bid"].dropna().astype(str))
            building_ids = set(buildings["bid"].astype(str))
            if not heritage_ids.issubset(building_ids):
                blockers.append("heritage_buildings.geojson 包含未知建筑 bid")
    verified_space_count = int(
        spaces.get("research_status", pd.Series(dtype=str))
        .eq("verified_public_park_context")
        .sum()
    )
    unresolved_space_count = int(len(spaces) - verified_space_count)
    if "include_in_objective" not in spaces.columns:
        warnings.append("公共空间背景层缺少 include_in_objective 字段；当前目标函数仍不会读取该图层")
    elif spaces["include_in_objective"].fillna(False).astype(bool).any():
        blockers.append("公共空间背景层含 include_in_objective=true，与当前目标函数口径冲突")
    if public_space_verification:
        summary = public_space_verification.get("summary", {})
        expected = {
            "candidate_count": len(spaces),
            "verified_public_park_context": verified_space_count,
            "unverified_excluded": int(
                spaces.get("research_status", pd.Series(dtype=str))
                .eq("candidate_unverified_excluded")
                .sum()
            ),
            "included_in_objective": int(
                spaces.get("include_in_objective", pd.Series(False, index=spaces.index))
                .fillna(False).astype(bool).sum()
            ),
        }
        mismatches = [key for key, value in expected.items() if summary.get(key) != value]
        if mismatches:
            warnings.append(
                "public_space_verification.json 与背景图层不一致：" + ", ".join(mismatches)
            )
    else:
        warnings.append("缺少 public_space_verification.json；公共空间逐项核查证据未进入追溯")
    warnings.append(
        "公共空间层仅作背景且不参与目标函数："
        f"{verified_space_count} 处已确认公共公园身份，"
        f"{unresolved_space_count} 处候选继续冻结；"
        "当前 OSM 多边形不能作为实测面积或法定权属边界"
    )

    alley_verified = int(
        alley_entrances.get("research_status", pd.Series(dtype=str))
        .eq("verified_research_entrance")
        .sum()
    )
    alley_frozen = int(
        alley_entrances.get("research_status", pd.Series(dtype=str))
        .eq("osm_candidate_unverified_frozen")
        .sum()
    )
    if "include_in_objective" in alley_entrances.columns:
        if alley_entrances["include_in_objective"].fillna(False).astype(bool).any():
            blockers.append("弄堂入口背景层含 include_in_objective=true，与当前目标函数口径冲突")
    elif len(alley_entrances):
        warnings.append("弄堂入口背景层缺少 include_in_objective 字段")
    if "include_in_optimization" in alley_entrances.columns:
        if alley_entrances["include_in_optimization"].fillna(False).astype(bool).any():
            blockers.append("弄堂入口背景层含 include_in_optimization=true，与冻结口径冲突")
    if alley_entrance_verification:
        alley_summary = alley_entrance_verification.get("summary", {})
        alley_expected = {
            "candidate_count": len(alley_entrances),
            "verified_research_entrance": alley_verified,
            "unverified_frozen": alley_frozen,
            "included_in_optimization": int(
                alley_entrances.get(
                    "include_in_optimization", pd.Series(False, index=alley_entrances.index)
                ).fillna(False).astype(bool).sum()
            ),
            "included_in_objective": int(
                alley_entrances.get(
                    "include_in_objective", pd.Series(False, index=alley_entrances.index)
                ).fillna(False).astype(bool).sum()
            ),
            "exhaustive_inventory": False,
        }
        alley_mismatches = [
            key for key, value in alley_expected.items() if alley_summary.get(key) != value
        ]
        if alley_mismatches:
            warnings.append(
                "alley_entrance_verification.json 与背景图层不一致："
                + ", ".join(alley_mismatches)
            )
    elif len(alley_entrances):
        warnings.append("缺少 alley_entrance_verification.json；入口证据未进入追溯")
    warnings.append(
        "弄堂入口仅作非穷尽背景且不参与优化："
        f"{alley_verified} 处研究级核实，{alley_frozen} 处候选冻结；"
        "坐标不是实测门点，不能推导通行能力或开放时段"
    )

    if research_demo:
        if zones is None:
            if draft_zone_path.exists():
                zones = _read_geojson(draft_zone_path, buildings.crs)
                status["intervention_zones"] = "research_draft_osm_road_blocks"
            else:
                zones = build_research_grid_zones(boundary)
                status["intervention_zones"] = "research_demo_grid"
        if controls is None:
            if draft_controls_path.exists():
                controls = pd.read_csv(draft_controls_path)
                status["planning_controls"] = "research_draft_existing_form_defaults"
            else:
                controls = build_research_controls(zones, scenario)
                status["planning_controls"] = "research_demo_defaults"
        # Research-demo controls can either reproduce the original scenario-
        # specific envelopes or use the paper experiment's one frozen envelope.
        # The latter is required for fair cross-method comparison.
        defaults = scenario.get("defaults", {})
        if controls is not None:
            controls = controls.copy()
            for column in ("height_limit_m", "max_far", "max_coverage_ratio"):
                if column in defaults:
                    controls[column] = float(defaults[column])
            controls["scenario_id"] = scenario.get("id", scenario_name)
            if shared_experiment_controls:
                controls["source"] = "shared paper-experiment assumption; not official planning data"
                status["planning_controls"] = "shared_paper_experiment_assumption"
            else:
                controls["source"] = "scenario-specific research assumption; not official planning data"
                status["planning_controls"] = "scenario_specific_research_assumption"
        if heritage is None:
            if draft_heritage_path.exists():
                heritage = _read_geojson(draft_heritage_path, buildings.crs)
                status["heritage"] = "research_assumption_tianzifang_conservative_proxy"
            else:
                status["heritage"] = "research_demo_empty"
        warnings.append("当前使用研究假设输入；可用于披露假设的方法实验，不得解释为法定规划结果")
        if shared_experiment_controls:
            warnings.append("五组论文对照固定使用同一限高、FAR、覆盖率、住宅保留率与街道缓冲口径")
        blockers = []

    buildings = _attach_heritage(buildings, heritage)
    buildings = _attach_zones(buildings, zones)
    if zones is not None and buildings["zone_id"].isna().any():
        unmatched = buildings["zone_id"].isna()
        buildings.loc[unmatched, "editable"] = False
        warnings.append(f"{int(unmatched.sum())} 栋建筑未匹配更新单元，已冻结为不可编辑背景")

    return StudyData(
        buildings=buildings,
        boundary=boundary,
        streets=streets,
        services=services,
        public_space_candidates=spaces,
        public_space_verification=public_space_verification,
        alley_entrances=alley_entrances,
        alley_entrance_verification=alley_entrance_verification,
        zones=zones,
        controls=controls,
        heritage=heritage,
        scenario=scenario,
        objective_config=objective_config,
        blockers=blockers,
        warnings=warnings,
        source_status=status,
        formal_input_quality=formal_input_quality,
    )


def audit_dict(study: StudyData) -> dict[str, Any]:
    return {
        "counts": {
            "buildings": int(len(study.buildings)),
            "streets": int(len(study.streets)),
            "public_services": int(len(study.services)),
            "public_space_candidates": int(len(study.public_space_candidates)),
            "public_space_verified_context": int(
                study.public_space_candidates.get("research_status", pd.Series(dtype=str))
                .eq("verified_public_park_context")
                .sum()
            ),
            "public_space_unverified_excluded": int(
                study.public_space_candidates.get("research_status", pd.Series(dtype=str))
                .eq("candidate_unverified_excluded")
                .sum()
            ),
            "alley_entrance_candidates": int(len(study.alley_entrances)),
            "alley_entrances_verified_context": int(
                study.alley_entrances.get("research_status", pd.Series(dtype=str))
                .eq("verified_research_entrance").sum()
            ),
            "alley_entrances_unverified_frozen": int(
                study.alley_entrances.get("research_status", pd.Series(dtype=str))
                .eq("osm_candidate_unverified_frozen").sum()
            ),
            "heritage_official_records_unresolved_and_excluded": int(
                study.formal_input_quality.get("counts", {}).get(
                    "heritage_official_records_unresolved_and_excluded", 0
                )
            ),
            "buildings_unmatched_to_zones_and_frozen": int(
                study.formal_input_quality.get("counts", {}).get(
                    "buildings_unmatched_and_frozen", 0
                )
            ),
            "intervention_zones": int(len(study.zones)) if study.zones is not None else 0,
            "heritage_features": int(len(study.heritage)) if study.heritage is not None else 0,
        },
        "crs": f"EPSG:{study.buildings.crs.to_epsg()}" if study.buildings.crs.to_epsg() else str(study.buildings.crs),
        "source_status": study.source_status,
        "blockers": study.blockers,
        "warnings": study.warnings,
    }
