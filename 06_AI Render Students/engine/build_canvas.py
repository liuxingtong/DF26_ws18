"""
build_canvas.py 交互式 HTML 画布:orbit 找角度,存角度,导出 massing / ControlNet 图。
生成自含单档 out/<slug>/canvas.html(内联 Three.js):真实卫星底 + 各体制体块;
导出模式 massing / depth / normal / segmentation / canny 作 AI 参考图或 ControlNet 条件图。
几何由 05 实算注入,零 AI,不联网(除抓一次卫星底)。
跑:python run.py canvas [slug]
"""
import base64, csv, json, sys, os, re
from pathlib import Path
import yaml
HERE = Path(__file__).resolve().parent           # engine/
ROOT = HERE.parent                                # 06 根
sys.path.insert(0, str(HERE))                     # engine 在路径上,可 import settings / ws05
import settings
import ws05
import prompt_gen
import massing as _massing   # 复用卫星抓取

OUT = ROOT / "out"
WEB = ROOT / "web"                    # 内置 three.min.js / OrbitControls.js


def _read_csv(path):
    if not path.exists() or path.stat().st_size == 0:
        return []
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _latest_dir(root, required=None):
    if not root.exists():
        return None
    candidates = sorted(path for path in root.iterdir() if path.is_dir())
    if required:
        candidates = [path for path in candidates if (path / required).exists()]
    return candidates[-1] if candidates else None


def _canvas_base_scope(slug, regimes):
    """Separate the current Dapuqiao optimizer canvas from legacy film regimes."""
    if slug == "dapuqiao":
        return ("current",), False
    return tuple(regimes), True


def _run_provenance(run_config):
    return {
        "seed": run_config.get("seed"),
        "display_status": run_config.get(
            "experiment_status", "preview_single_seed"
        ),
    }


def _latest_compatible_experiment(root, scenario_ids):
    if not root.exists():
        return None
    for candidate in sorted(
        (path for path in root.iterdir() if path.is_dir()),
        reverse=True,
    ):
        manifest_path = candidate / "experiment_manifest.json"
        if not manifest_path.exists() or not (candidate / "search_summary.csv").exists():
            continue
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("scenario") in scenario_ids:
            return candidate
    return None


def _latest_scenario_runs(optimization_root, suite_root, scenario_ids):
    """Pick the newest compatible run per scenario from single runs or suites."""
    candidates = []
    if optimization_root.exists():
        candidates.extend(
            (path.name, path)
            for path in optimization_root.iterdir()
            if path.is_dir()
        )
    if suite_root.exists():
        for suite in suite_root.iterdir():
            if not suite.is_dir():
                continue
            for scenario_id in scenario_ids:
                scenario_root = suite / scenario_id
                if not scenario_root.exists():
                    continue
                for run in scenario_root.iterdir():
                    if run.is_dir():
                        candidates.append((suite.name, run))

    def timestamp(value):
        match = re.search(r"(\d{8}_\d{6})", value)
        return match.group(1) if match else value

    latest = {}
    latest_keys = {}
    for source_key, candidate in sorted(candidates, key=lambda item: timestamp(item[0])):
        config_path = candidate / "run_config.json"
        if not config_path.exists() or not (candidate / "selected_solutions.json").exists():
            continue
        config = json.loads(config_path.read_text(encoding="utf-8"))
        scenario_id = config.get("scenario_id")
        source_timestamp = timestamp(source_key)
        if scenario_id in scenario_ids and source_timestamp >= latest_keys.get(scenario_id, ""):
            latest[scenario_id] = candidate
            latest_keys[scenario_id] = source_timestamp
    return latest


def _optimization_recs(path):
    frame = ws05.C.gpd.read_file(path)
    records = []
    for _, row in frame.iterrows():
        records.append({
            "geom": row.geometry,
            "h": float(row["height_m"]),
            "sh": str(row.get("stakeholder_proxy", row.get("stakeholder", "unknown"))),
        })
    return records


def _osm_roads(slug, ox, oy):
    """Embed the repository OSM street snapshot as local-coordinate linework."""
    path = ws05.WS05 / "data" / slug / "street_network.geojson"
    if not path.exists():
        return []
    frame = ws05.C.gpd.read_file(path).to_crs(ws05.C.UTM)
    major_classes = {"motorway", "trunk", "primary", "secondary", "tertiary"}
    roads = []
    for _, row in frame.iterrows():
        geom = row.geometry
        if geom is None or geom.is_empty:
            continue
        lines = list(geom.geoms) if geom.geom_type == "MultiLineString" else [geom]
        for line in lines:
            simple = line.simplify(0.6)
            points = [[round(x - ox, 1), round(y - oy, 1)] for x, y in simple.coords]
            if len(points) >= 2:
                roads.append({
                    "p": points,
                    "major": str(row.get("highway", "")) in major_classes,
                    "name": str(row.get("name:zh") or row.get("name") or ""),
                })
    return roads


def _load_research_bundle(slug, ox, oy):
    if slug != "dapuqiao":
        return {}, {}, [], {}, {}
    config_root = ws05.WS05 / "optimization"
    load_yaml = lambda name: yaml.safe_load((config_root / name).read_text(encoding="utf-8")) or {}
    scenarios = load_yaml("scenarios.yaml")
    operators = load_yaml("operator_specs.yaml")
    roles = load_yaml("role_profiles.yaml")
    objectives = load_yaml("objectives.yaml")
    constraints = load_yaml("constraints.yaml")
    assumptions = load_yaml("research_assumptions.yaml")
    regime_definitions = ws05.ops.load_regimes(ws05.WS05 / "regimes.yaml")
    scenario_definitions = scenarios.get("scenarios", {})
    scenario_catalog = {}
    for key in (
        "public_coordination",
        "development_growth",
        "resident_heritage_priority",
    ):
        item = regime_definitions.get(key, {})
        quantitative = scenario_definitions.get(key, {})
        scenario_catalog[key] = {
            "label": quantitative.get("label", item.get("label", key)),
            "description": quantitative.get("description", item.get("desc", "")),
            "rule_description": item.get("desc", ""),
            "fingerprint": item.get("fingerprint", ""),
            "operators": quantitative.get("operator_policy", {}).get(
                "allowed_operators", [step.get("op") for step in item.get("steps", [])]
            ),
            "rule_operators": [step.get("op") for step in item.get("steps", [])],
            "status": "scenario_specific_optimization",
        }
    draft_summary_path = ws05.WS05 / "data" / slug / "drafts" / "draft_summary.json"
    draft_summary = json.loads(draft_summary_path.read_text(encoding="utf-8")) if draft_summary_path.exists() else {}
    quality_path = ws05.WS05 / "data" / slug / "formal_input_quality.json"
    formal_quality = json.loads(quality_path.read_text(encoding="utf-8")) if quality_path.exists() else {}

    optimization_root = ws05.WS05 / "out" / slug / "optimization"
    suite_root = ws05.WS05 / "out" / slug / "scenario_suites"
    scenario_ids = tuple(scenario_catalog)
    latest_by_scenario = _latest_scenario_runs(
        optimization_root, suite_root, scenario_ids
    )

    extra_data, extra_labels, extra_keys, solution_metrics = {}, {}, [], {}
    scenario_runs = {}
    role_labels = {
        "resident": "居民视角首选",
        "development": "开发实施视角首选",
        "public_planning": "公共规划视角首选",
        "balanced_compromise": "最小最差名次折中",
    }
    for scenario_id in scenario_ids:
        run = latest_by_scenario.get(scenario_id)
        if not run:
            continue
        pareto_rows = _read_csv(run / "pareto_solutions.csv")
        selected = json.loads((run / "selected_solutions.json").read_text(encoding="utf-8"))
        run_config = json.loads((run / "run_config.json").read_text(encoding="utf-8"))
        solution_roles = {}
        for role, solution_id in selected.items():
            solution_roles.setdefault(solution_id, []).append(role)
        role_keys = {}
        run_metrics = {}
        for row in pareto_rows:
            solution_id = row["solution_id"]
            matches = sorted((run / "solutions").glob(f"*__{solution_id}.geojson"))
            if not matches:
                continue
            key = f"opt_{scenario_id}_{solution_id.lower()}"
            assigned_roles = solution_roles.get(solution_id, [])
            extra_data[key] = _regime_polys(_optimization_recs(matches[0]), ox, oy)
            extra_keys.append(key)
            label_prefix = scenario_catalog[scenario_id]["label"]
            role_suffix = " / ".join(role_labels.get(role, role) for role in assigned_roles)
            extra_labels[key] = f"{label_prefix} · {role_suffix or f'Pareto 方案 {solution_id}'}"
            metric = {**row, "solution_id": solution_id, "scenario_id": scenario_id}
            solution_metrics[key] = metric
            run_metrics[key] = metric
            for role in assigned_roles:
                role_keys[role] = key
        scenario_runs[scenario_id] = {
            "directory": str(run.relative_to(ws05.WS05 / "out" / slug)),
            "pareto": pareto_rows,
            "selected": selected,
            "role_keys": role_keys,
            "solution_metrics": run_metrics,
            "run_config": run_config,
            **_run_provenance(run_config),
            "missing_role_geometries": [
                role for role in (*roles.get("roles", {}), "balanced_compromise")
                if role in selected and role not in role_keys
            ],
        }
    solution_metrics["current"] = {
        "solution_id": "S_0000",
        "residential_disruption": 0.0,
        "development_capacity": 0.0,
        "street_connected_released_ground": 0.0,
        "changed_buildings": 0,
        "feasible": True,
        "violation_count": 0,
    }

    experiment_root = ws05.WS05 / "out" / slug / "experiments"
    experiment_dir = _latest_compatible_experiment(experiment_root, scenario_ids)
    experiment = {}
    if experiment_dir:
        summary_rows = _read_csv(experiment_dir / "search_summary.csv")
        coverage_rows = _read_csv(experiment_dir / "dominance_coverage.csv")
        manifest_path = experiment_dir / "experiment_manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
        means = {}
        for backend in ("nsga2", "random"):
            subset = [row for row in summary_rows if row.get("backend") == backend]
            if subset:
                means[backend] = {
                    field: sum(float(row[field]) for row in subset) / len(subset)
                    for field in ("feasible_ratio", "pareto_count", "maximum_development_capacity", "maximum_released_ground")
                }
        experiment = {
            "run": experiment_dir.name,
            "manifest": manifest,
            "means": means,
            "coverage": {
                "nsga_over_random": sum(float(row["nsga_dominates_random_fraction"]) for row in coverage_rows) / len(coverage_rows),
                "random_over_nsga": sum(float(row["random_dominates_nsga_fraction"]) for row in coverage_rows) / len(coverage_rows),
            } if coverage_rows else {},
        }

    research = {
        "scenario_definitions": scenario_definitions,
        "scenario_catalog": scenario_catalog,
        "operators": operators.get("operators", {}),
        "roles": roles.get("roles", {}),
        "role_metadata": roles.get("metadata", {}),
        "objectives": objectives.get("objectives", {}),
        "constraints": constraints.get("constraints", {}),
        "assumptions": assumptions,
        "draft_summary": draft_summary,
        "formal_input_quality": formal_quality,
        "optimization_runs": {key: value["directory"] for key, value in scenario_runs.items()},
        "scenario_runs": scenario_runs,
        "solution_metrics": solution_metrics,
        "experiment": experiment,
    }
    return extra_data, extra_labels, extra_keys, {}, research


def _origin(recs):
    minx = min(p.bounds[0] for r in recs for p in ws05.C._polys(r["geom"]))
    miny = min(p.bounds[1] for r in recs for p in ws05.C._polys(r["geom"]))
    maxx = max(p.bounds[2] for r in recs for p in ws05.C._polys(r["geom"]))
    maxy = max(p.bounds[3] for r in recs for p in ws05.C._polys(r["geom"]))
    return minx, miny, maxx, maxy


def _regime_polys(recs, ox, oy, simplify=1.0):
    """study 楼(整个街区)→ 局部坐标多边形,in=1(全实心)。"""
    out = []
    for r in recs:
        for poly in ws05.C._polys(r["geom"]):
            ps = poly.simplify(simplify)
            xy = [[round(x - ox, 1), round(y - oy, 1)] for x, y in list(ps.exterior.coords)[:-1]]
            if len(xy) >= 3:
                out.append({"p": xy, "h": round(float(r["h"]), 1), "sh": r["sh"], "in": 1})
    return out


def _context_polys(recs, ox, oy, simplify=2.0):
    """周边语境楼 → 局部坐标多边形(粗简化省档案;跨体制不变,只嵌一次)。无 sh、in=0(透明)。"""
    out = []
    for r in recs:
        for poly in ws05.C._polys(r["geom"]):
            ps = poly.simplify(simplify)
            xy = [[round(x - ox, 1), round(y - oy, 1)] for x, y in list(ps.exterior.coords)[:-1]]
            if len(xy) >= 3:
                out.append({"p": xy, "h": round(float(r["h"]), 1)})
    return out


def build_geometry(slug, regimes=None):
    regimes = regimes or settings.REGIMES
    active_regimes, include_counterfactuals = _canvas_base_scope(slug, regimes)
    rr, regs = ws05.regime_recs(slug, active_regimes)
    if include_counterfactuals:
        cf_rr, cf_scen = ws05.counterfactual_recs(slug)
    else:
        cf_rr, cf_scen = {}, {}
    context_recs = ws05.load_context_recs(slug)                  # 周边语境(透明,跨体制不变),没有则 []
    base = rr.get("current") or next(iter(rr.values()))
    smnx, smny, smxx, smxy = _origin(base)                       # study bounds(现状 footprint,稳定)
    # 原点 = study+周边 最小角;全场景 bounds = study∪周边
    if context_recs:
        cmnx, cmny, cmxx, cmxy = _origin(context_recs)
        ox, oy = min(smnx, cmnx), min(smny, cmny)
        fmxx, fmxy = max(smxx, cmxx), max(smxy, cmxy)
    else:
        ox, oy = smnx, smny
        fmxx, fmxy = smxx, smxy
    data = {name: _regime_polys(recs, ox, oy) for name, recs in rr.items()}
    cf_keys = []
    for name, recs in cf_rr.items():
        key = "cf_" + name
        cf_keys.append(key)
        data[key] = _regime_polys(recs, ox, oy)
    context = _context_polys(context_recs, ox, oy) if context_recs else []
    labels = {name: ws05.regime_label(regs, name) for name in rr}
    labels.update({"cf_" + name: ws05.counterfactual_label(cf_scen, name) for name in cf_rr})
    optimization_data, optimization_labels, optimization_keys, role_keys, research = (
        _load_research_bundle(slug, ox, oy)
    )
    data.update(optimization_data)
    labels.update(optimization_labels)
    osm_roads = _osm_roads(slug, ox, oy)
    # 卫星底 = 全场景(study + 周边环)。优先复用仓库已有缓存，避免可选
    # contextily 不存在时把有效底图丢掉。
    sat, satext = None, None
    cache_path = OUT / slug / "ground_scene.jpg"
    cache_meta = cache_path.with_suffix(".json")
    if cache_path.exists() and cache_meta.exists():
        meta = json.loads(cache_meta.read_text(encoding="utf-8"))
        sat = "data:image/jpeg;base64," + base64.b64encode(cache_path.read_bytes()).decode()
        satext = meta.get("local")
    else:
        try:
            sat, local = ws05.C.ground_sat(ox, oy, fmxx, fmxy, cache_path, factor=6.0)
            satext = [local[0], local[1], local[2], local[3]]
        except Exception as e:
            print("  卫星底跳过:", e)
    rings = ws05.C.study_poly_rings(slug)                        # study 街区多边形(UTM 环)= 红线
    study_poly = ([[[round(x - ox, 1), round(y - oy, 1)] for x, y in ring] for ring in rings]
                  if rings else None)
    regime_keys = list(rr.keys())
    return {"regimes": regime_keys + cf_keys + optimization_keys,
            "regimeKeys": regime_keys, "counterfactualKeys": cf_keys,
            "optimizationKeys": optimization_keys, "optimizationRoleKeys": role_keys,
            "labels": labels, "colors": ws05.C.SH_COLOR,
            "sh_label": {k: v.split("(")[0] for k, v in ws05.C.SH_LABEL.items()},
            "data": data, "context": context, "sat": sat, "satExtent": satext,
            "osmRoads": osm_roads,
            "studyPoly": study_poly, "research": research,
            "bounds": [smnx - ox, smny - oy, smxx - ox, smxy - oy],   # study extent(相机取景)
            "scene": [0, 0, fmxx - ox, fmxy - oy]}                    # 全场景(深度范围)


CSS = """
:root{--accent:#0f5e63;--accent2:#d66b42;--ink:#18201f;--muted:#677472;--line:#dfe6e4;--bg:#eef1f0;}
*{box-sizing:border-box;} body{margin:0;background:var(--bg);color:var(--ink);
 font:14px/1.6 "Helvetica Neue","PingFang SC","Microsoft YaHei",system-ui,sans-serif;height:100vh;overflow:hidden;}
#stage{position:fixed;inset:0;} #cv{width:100%;height:100%;display:block;}
.panel{position:fixed;top:12px;left:12px;width:390px;max-height:calc(100vh - 24px);overflow:auto;
 background:rgba(255,255,255,.94);backdrop-filter:blur(6px);border:1px solid var(--line);border-radius:12px;
 padding:14px 15px;box-shadow:0 2px 12px rgba(0,0,0,.1);}
.panel h1{font-size:16px;margin:0 0 3px;} .panel .sub{font-size:11.5px;color:var(--muted);margin:0 0 10px;}
.grp{margin:10px 0 4px;font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.06em;}
.row{display:flex;flex-wrap:wrap;gap:5px;}
button{font:inherit;font-size:12px;border:1px solid var(--line);background:#fff;color:var(--ink);
 border-radius:16px;padding:5px 11px;cursor:pointer;box-shadow:0 1px 2px rgba(0,0,0,.05);}
button:hover{background:#f2f6f6;} button.on{background:var(--accent);border-color:var(--accent);color:#fff;}
button.big{width:100%;border-radius:9px;padding:8px;margin-top:5px;font-weight:600;}
button.acc{background:var(--accent);color:#fff;border-color:var(--accent);}
.ang{display:flex;align-items:center;gap:6px;margin-top:5px;font-size:12px;}
.ang a{color:var(--accent);cursor:pointer;text-decoration:underline;flex:1;}
.ang .x{color:#c0654a;cursor:pointer;}
.legend{display:flex;flex-wrap:wrap;gap:6px 10px;margin-top:6px;font-size:11.5px;}
.legend i{width:10px;height:10px;border-radius:2px;display:inline-block;margin-right:4px;vertical-align:-1px;}
.hint{position:fixed;right:12px;bottom:10px;font-size:11.5px;color:#5a6468;background:rgba(255,255,255,.7);
 padding:2px 8px;border-radius:6px;} #prm{font-size:11.5px;color:#333;margin-top:6px;white-space:pre-wrap;
 max-height:120px;overflow:auto;background:#f6f8f8;border:1px solid var(--line);border-radius:7px;padding:7px;}
.note{font-size:11px;color:var(--muted);margin-top:8px;line-height:1.5;}
.rep{display:inline-block;margin:0 0 4px;color:var(--accent);text-decoration:none;font-size:12px;
 border:1px solid var(--line);border-radius:14px;padding:4px 11px;background:#fff;}
.rep:hover{background:#f2f6f6;}
.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:5px;margin:7px 0 10px;}
.stat{padding:7px 4px;border:1px solid var(--line);border-radius:8px;background:#f7f9f8;text-align:center;}
.stat b{display:block;font-size:15px;line-height:1.2;color:var(--accent);}.stat span{font-size:9.5px;color:var(--muted);}
.card{border:1px solid var(--line);background:#fff;border-radius:9px;padding:9px 10px;margin:6px 0;}
.card h3{font-size:12.5px;margin:0 0 3px;}.card p{font-size:11.5px;margin:2px 0;color:#36413f;line-height:1.55;}
.card .meta{font-size:10.5px;color:var(--muted);}.cards{display:grid;grid-template-columns:1fr 1fr;gap:6px;}
.role{border-left:3px solid var(--accent);}.operator{border-left:3px solid var(--accent2);}
.pill{display:inline-block;font-size:10px;border-radius:10px;padding:1px 6px;margin:2px 3px 0 0;background:#edf4f3;color:#285d59;}
.warning{border-left:3px solid #c99027;background:#fffaf0;}.ok{border-left:3px solid #3d8b68;background:#f3faf6;}
#paretoPlot{display:block;width:100%;height:190px;background:#f8faf9;border:1px solid var(--line);border-radius:8px;}
.axis{stroke:#9ca9a6;stroke-width:1}.dot{stroke:#fff;stroke-width:1.5;cursor:pointer;transition:r .12s}.dot:hover,.dot:focus{stroke:#17201f;stroke-width:2.5;outline:none}.dot.sel{stroke:#17201f;stroke-width:2.5}
.pareto-legend{display:flex;align-items:center;justify-content:flex-end;gap:6px;font-size:10px;color:var(--muted);margin-top:4px}
.pareto-legend .good{color:#43885f}.pareto-legend .bad{color:#c44d45}
.metric-grid{display:grid;grid-template-columns:1fr 1fr;gap:5px;margin-top:6px;}.metric{background:#f5f7f6;border-radius:7px;padding:6px;}
.metric b{display:block;font-size:12px}.metric span{font-size:9.5px;color:var(--muted)}
details{border-top:1px solid var(--line);margin-top:7px;padding-top:5px;}summary{cursor:pointer;font-size:11.5px;font-weight:650;}
@media(max-width:700px){.panel{width:calc(100vw - 20px);left:10px;top:10px;max-height:56vh}.hint{display:none}.cards{grid-template-columns:1fr}.stats{grid-template-columns:repeat(2,1fr)}}
"""


def viewer_js(geom):
    return "const GEOM=%s;\n" % json.dumps(geom, separators=(",", ":"), default=str) + r"""
const COL=GEOM.colors;
let scene,cam,renderer,controls,groundSat,groundOsm,osmGroup,boundary,baselineOverlay,groups={},cur=GEOM.regimes[0],mode="massing",basemap="osm",saved=[];
let baselineOverlayOn=true;
let selectedScenario=null,selectedRole=null;
let matDepth,matNormal,edges=[],ctxMeshes=[],ctxEdges=[];
const edgeMat=new THREE.LineBasicMaterial({color:0xffffff});   // canny:白色硬边
function buildGroup(name){
  if(groups[name])return groups[name];
  if(!GEOM.data[name])return null;
  const g=new THREE.Group();g.visible=false;scene.add(g);groups[name]=g;
  for(const r of GEOM.data[name]){
    const sh=new THREE.Shape();r.p.forEach((pt,i)=>i?sh.lineTo(pt[0],pt[1]):sh.moveTo(pt[0],pt[1]));
    const geo=new THREE.ExtrudeGeometry(sh,{depth:1,bevelEnabled:false});
    const m=new THREE.MeshLambertMaterial({color:new THREE.Color(COL[r.sh]||"#b9b1a8")});
    const mesh=new THREE.Mesh(geo,m);mesh.scale.z=r.h;mesh.userData=r;g.add(mesh);
    const el=new THREE.LineSegments(new THREE.EdgesGeometry(geo,15),edgeMat);
    el.visible=false;el.userData=r;mesh.add(el);edges.push(el);
  }
  return g;
}
function buildBaselineOverlay(){
  if(baselineOverlay||!GEOM.data.current)return baselineOverlay;
  baselineOverlay=new THREE.Group();scene.add(baselineOverlay);
  const material=new THREE.LineBasicMaterial({color:0xffb000,transparent:true,opacity:.72});
  for(const r of GEOM.data.current){
    const sh=new THREE.Shape();r.p.forEach((pt,i)=>i?sh.lineTo(pt[0],pt[1]):sh.moveTo(pt[0],pt[1]));
    const geo=new THREE.ExtrudeGeometry(sh,{depth:1,bevelEnabled:false});
    const line=new THREE.LineSegments(new THREE.EdgesGeometry(geo,15),material);
    line.scale.z=r.h;baselineOverlay.add(line);
  }
  return baselineOverlay;
}
function init(){
  const st=document.getElementById("stage"),w=st.clientWidth,h=st.clientHeight;
  scene=new THREE.Scene(); scene.background=new THREE.Color(0xeef1f0);
  cam=new THREE.PerspectiveCamera(48,w/h,1,20000); cam.up.set(0,0,1);
  renderer=new THREE.WebGLRenderer({canvas:document.getElementById("cv"),antialias:true,preserveDrawingBuffer:true});
  renderer.setPixelRatio(Math.min(devicePixelRatio,2)); renderer.setSize(w,h);
  if(THREE.sRGBEncoding!==undefined)renderer.outputEncoding=THREE.sRGBEncoding;
  scene.add(new THREE.HemisphereLight(0xffffff,0xb7c1c2,0.62));
  scene.add(new THREE.AmbientLight(0xffffff,0.20));
  const dl=new THREE.DirectionalLight(0xffffff,0.48); dl.position.set(0.6,-1,1.4); scene.add(dl);
  const b=GEOM.bounds, cx=(b[0]+b[2])/2, cy=(b[1]+b[3])/2, span=Math.max(b[2]-b[0],b[3]-b[1]);
  // 卫星地面
  if(GEOM.sat){const tx=new THREE.TextureLoader().load(GEOM.sat); if(THREE.sRGBEncoding!==undefined)tx.encoding=THREE.sRGBEncoding;
    const se=GEOM.satExtent, gw=se[2]-se[0], gh=se[3]-se[1];
    groundSat=new THREE.Mesh(new THREE.PlaneGeometry(gw,gh),new THREE.MeshBasicMaterial({map:tx}));
    groundSat.position.set((se[0]+se[2])/2,(se[1]+se[3])/2,-0.35); scene.add(groundSat);}
  // 仓库中的 OSM 道路快照：浅色底面 + 主次道路矢量线。
  {const se=GEOM.satExtent||GEOM.scene,gw=se[2]-se[0],gh=se[3]-se[1];
    groundOsm=new THREE.Mesh(new THREE.PlaneGeometry(gw,gh),new THREE.MeshBasicMaterial({color:0xe1ddd5}));
    groundOsm.position.set((se[0]+se[2])/2,(se[1]+se[3])/2,-0.34);scene.add(groundOsm);
    osmGroup=new THREE.Group();scene.add(osmGroup);
    for(const r of (GEOM.osmRoads||[])){const pts=r.p.map(p=>new THREE.Vector3(p[0],p[1],-0.18));
      const mat=new THREE.LineBasicMaterial({color:r.major?0x3f3a35:0x746d66,transparent:true,opacity:r.major?1:.95});
      const line=new THREE.Line(new THREE.BufferGeometry().setFromPoints(pts),mat);line.userData=r;osmGroup.add(line);}}
  // 红色研究范围边界 = study 街区多边形(整个 study 都实心),z 略高于地面
  if(GEOM.studyPoly){const zz=0.3; boundary=new THREE.Group();
    for(const ring of GEOM.studyPoly){
      const pts=ring.map(p=>new THREE.Vector3(p[0],p[1],zz));
      boundary.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints(pts),new THREE.LineBasicMaterial({color:0xe02424})));}
    scene.add(boundary);}
  // 方案按需创建；几十个 Pareto 解不会在首屏一次性变成数万网格。
  const first=buildGroup(cur);if(first)first.visible=true;
  // 周边语境体块(透明,跨体制不变 → 只建一次,始终可见)
  if(GEOM.context && GEOM.context.length){const g=new THREE.Group(); scene.add(g);
    for(const r of GEOM.context){
      const sh=new THREE.Shape(); r.p.forEach((pt,i)=> i?sh.lineTo(pt[0],pt[1]):sh.moveTo(pt[0],pt[1]));
      const geo=new THREE.ExtrudeGeometry(sh,{depth:1,bevelEnabled:false});
      const m=new THREE.MeshLambertMaterial({color:new THREE.Color("#b9b1a8")});
      const mesh=new THREE.Mesh(geo,m); mesh.scale.z=r.h; mesh.userData={in:0,sh:"context"}; g.add(mesh); ctxMeshes.push(mesh);
      const el=new THREE.LineSegments(new THREE.EdgesGeometry(geo,15),edgeMat);
      el.visible=false; el.userData={in:0}; mesh.add(el); ctxEdges.push(el);
    }
  }
  // 深度:自定义 shader,把**场景实际距离范围**映射成灰阶(近=白、远=黑) 正经 ControlNet depth
  matDepth=new THREE.ShaderMaterial({uniforms:{uNear:{value:1},uFar:{value:1000}},
    vertexShader:"varying float vD; void main(){vec4 mv=modelViewMatrix*vec4(position,1.0); vD=-mv.z; gl_Position=projectionMatrix*mv;}",
    fragmentShader:"uniform float uNear,uFar; varying float vD; void main(){float d=clamp((vD-uNear)/(uFar-uNear),0.0,1.0); float g=1.0-d; gl_FragColor=vec4(g,g,g,1.0);}"});
  matNormal=new THREE.MeshNormalMaterial();
  cam.position.set(cx+span*0.5,cy-span*0.75,span*0.6);
  controls=new THREE.OrbitControls(cam,renderer.domElement); controls.target.set(cx,cy,30);
  controls.enableDamping=true; controls.dampingFactor=.08; controls.update();
  applyMode(); window.addEventListener("resize",onresize); animate();
}
function onresize(){const st=document.getElementById("stage");cam.aspect=st.clientWidth/st.clientHeight;
  cam.updateProjectionMatrix();renderer.setSize(st.clientWidth,st.clientHeight);}
function animate(){requestAnimationFrame(animate);controls.update();
  if(mode==="depth"){const s=GEOM.scene||GEOM.bounds,span=Math.max(s[2]-s[0],s[3]-s[1]);
    const dist=cam.position.distanceTo(controls.target);
    matDepth.uniforms.uNear.value=Math.max(1,dist-span*0.75); matDepth.uniforms.uFar.value=dist+span*0.75;}
  renderer.render(scene,cam);}
// —— 模式:材质切换(massing 素模 / depth / normal / segmentation)——
function styleMesh(m,massing,seg,canny){
  const inside=m.userData.in!==0;                          // in=1 study 实心 / in=0 周边透明
  if(massing){ m.material.color.set(inside?"#b9b1a8":"#cbc5bd");
    m.material.transparent=!inside; m.material.opacity=inside?1.0:0.38; }
  else{ m.material.transparent=false; m.material.opacity=1.0;
    if(seg) m.material.color.set(COL[m.userData.sh]||"#999");
    else if(canny) m.material.color.set(0x000000); }       // 黑面遮挡,只留白色硬边
  m.material.needsUpdate=true;
}
function applyMode(){
  const massing=(mode==="massing"), seg=(mode==="segmentation"), canny=(mode==="canny");
  scene.overrideMaterial = (mode==="depth")?matDepth : (mode==="normal")?matNormal : null;
  if(groundSat) groundSat.visible = massing && basemap==="satellite";
  if(groundOsm) groundOsm.visible = massing && basemap==="osm";
  if(osmGroup) osmGroup.visible = massing && basemap==="osm";
  if(boundary) boundary.visible = massing;                 // 红线只在 massing 显示
  if(baselineOverlay)baselineOverlay.visible=baselineOverlayOn&&massing&&cur!=="current";
  // 背景:massing 浅灰,normal/seg 白,depth/canny 黑
  scene.background=new THREE.Color(massing?0xeef1f0:((mode==="normal"||seg)?0xffffff:0x000000));
  for(const name in groups) for(const m of groups[name].children){ if(m.isMesh) styleMesh(m,massing,seg,canny); }
  for(const m of ctxMeshes) styleMesh(m,massing,seg,canny);   // 周边语境同规则(depth/normal/seg/canny 都含,给 ControlNet 语境)
  edgeMat.color.set(canny?0xffffff:0x2b2b2b);               // canny 白硬边;massing 深灰勾透明周边
  for(const el of edges) el.visible = canny;                        // study 实心:只有 canny 显硬边
  for(const el of ctxEdges) el.visible = canny || massing;          // 周边透明:massing 勾轮廓 + canny 硬边
  document.querySelectorAll("[data-mode]").forEach(b=>b.classList.toggle("on",b.dataset.mode===mode));
}
function setRegime(name){const target=buildGroup(name);if(!target)return;cur=name;for(const k in groups)groups[k].visible=(k===cur);
  if(cur!=="current")buildBaselineOverlay();
  applyMode();
  document.querySelectorAll("[data-reg]").forEach(b=>b.classList.toggle("on",b.dataset.reg===name));
  document.getElementById("prm").textContent=GEOM.prompts?GEOM.prompts[name]||"":"";
  renderSolutionMetrics(name);highlightPareto(name);}
function setMode(m){mode=m;applyMode();}
function setBasemap(name){basemap=name;applyMode();document.querySelectorAll("[data-basemap]").forEach(b=>b.classList.toggle("on",b.dataset.basemap===name));}
function toggleBaselineOverlay(){baselineOverlayOn=!baselineOverlayOn;applyMode();const b=document.getElementById("baselineOverlayButton");if(b)b.classList.toggle("on",baselineOverlayOn);}
function esc(v){return String(v??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));}
function num(v,d=3){const n=Number(v);return Number.isFinite(n)?n.toFixed(d):"—";}
function pct(v,d=1){const n=Number(v);return Number.isFinite(n)?`${(n*100).toFixed(d)}%`:"—";}
function currentScenarioRun(){return ((GEOM.research||{}).scenario_runs||{})[selectedScenario]||{};}
function renderSolutionMetrics(key){const el=document.getElementById("solutionMetrics"),r=GEOM.research||{};
  if(!el)return;const m=(r.solution_metrics||{})[key];
  if(!m){el.innerHTML='<div class="note">当前显示规则情景的三维推演。角色选择会保留这个情景并标出其共同 Pareto 首选；需要时再点“查看该角色的 Pareto 首选方案”。</div>';return;}
  el.innerHTML=`<div class="card ok"><h3>${esc(GEOM.labels[key]||m.solution_id)}</h3><div class="metric-grid">
    <div class="metric"><b>${pct(m.residential_disruption)}</b><span>居住影响暴露 · 越低越好</span></div>
    <div class="metric"><b>${num(m.development_capacity,4)}</b><span>正向增建量 · 越高越好</span></div>
    <div class="metric"><b>${pct(m.street_connected_released_ground,3)}</b><span>临街释放地面 · 越高越好</span></div>
    <div class="metric"><b>${num(m.net_gfa_change_m2,0)} m²</b><span>净 GFA 变化 · 可正可负</span></div>
    <div class="metric"><b>${esc(m.changed_buildings||0)}</b><span>发生形态变化的建筑</span></div></div>
    <p class="meta">方案 ${esc(m.solution_id)} · 可行=${esc(m.feasible)} · 违规=${esc(m.violation_count||0)}</p></div>`;}
function renderPareto(){const sr=currentScenarioRun(),rows=sr.pareto||[],svg=document.getElementById("paretoPlot");if(!svg)return;
  if(!rows.length){svg.innerHTML='<text x="12" y="28" font-size="12" fill="#8a5d16">该情景尚无可读取的优化运行结果。</text>';return;}
  const W=340,H=210,L=42,R=12,T=12,B=38;
  const xs=rows.map(x=>Number(x.development_capacity)),ys=rows.map(x=>Number(x.street_connected_released_ground));
  const ds=rows.map(x=>Number(x.residential_disruption));
  const minmax=a=>[Math.min(...a),Math.max(...a)],xr=minmax(xs),yr=minmax(ys),dr=minmax(ds);
  const sx=x=>L+(x-xr[0])/(xr[1]-xr[0]||1)*(W-L-R),sy=y=>H-B-(y-yr[0])/(yr[1]-yr[0]||1)*(H-T-B);
  const selectedIds=new Set(Object.values(sr.selected||{}));let body="";
  for(const t of [0,.5,1]){const xv=xr[0]+t*(xr[1]-xr[0]),yv=yr[0]+t*(yr[1]-yr[0]),xx=sx(xv),yy=sy(yv);
    body+=`<line x1="${xx}" y1="${T}" x2="${xx}" y2="${H-B}" stroke="#e2e7e5"/><text x="${xx}" y="${H-B+14}" text-anchor="middle" font-size="9" fill="#677472">${pct(xv,1)}</text>`;
    body+=`<line x1="${L}" y1="${yy}" x2="${W-R}" y2="${yy}" stroke="#e2e7e5"/><text x="${L-5}" y="${yy+3}" text-anchor="end" font-size="9" fill="#677472">${pct(yv,2)}</text>`;}
  body+=`<line class="axis" x1="${L}" y1="${H-B}" x2="${W-R}" y2="${H-B}"/><line class="axis" x1="${L}" y1="${T}" x2="${L}" y2="${H-B}"/>
    <text x="${W/2}" y="${H-6}" text-anchor="middle" font-size="10" fill="#677472">正向增建量 / 场地面积 →</text>
    <text x="11" y="${H/2}" transform="rotate(-90 11 ${H/2})" text-anchor="middle" font-size="10" fill="#677472">临街释放地面 →</text>`;
  for(const row of rows){const d=Number(row.residential_disruption),t=(d-dr[0])/(dr[1]-dr[0]||1),red=Math.round(72+160*t),green=Math.round(142-70*t);
    const sid=row.solution_id,selected=selectedIds.has(sid),key=Object.keys(sr.solution_metrics||{}).find(k=>sr.solution_metrics[k].solution_id===sid);
    body+=`<circle class="dot ${selected?'sel':''}" tabindex="0" role="button" aria-label="查看方案 ${esc(sid)}" data-sid="${esc(sid)}" data-key="${esc(key||'')}" cx="${sx(Number(row.development_capacity))}" cy="${sy(Number(row.street_connected_released_ground))}" r="${selected?5.5:4}" fill="rgb(${red},${green},92)"><title>${esc(sid)}｜居住影响暴露 ${pct(d)}｜正向增建量 ${num(row.development_capacity,4)}｜净GFA ${num(row.net_gfa_change_m2,0)}m²｜释放 ${pct(row.street_connected_released_ground,3)}</title></circle>`;}
  svg.setAttribute("viewBox",`0 0 ${W} ${H}`);svg.innerHTML=body;
  svg.querySelectorAll(".dot").forEach(dot=>{const open=()=>{const key=dot.dataset.key;if(key)setRegime(key);};dot.onclick=open;dot.onkeydown=e=>{if(e.key==="Enter"||e.key===" "){e.preventDefault();open();}};});}
function highlightPareto(key){const r=GEOM.research||{},m=(r.solution_metrics||{})[key],svg=document.getElementById("paretoPlot");if(!svg)return;
  svg.querySelectorAll(".dot").forEach(d=>d.classList.toggle("sel",!!m&&d.dataset.sid===m.solution_id));}
function selectScenario(key){const r=GEOM.research||{},s=(r.scenario_catalog||{})[key];if(!s)return;
  selectedScenario=key;
  document.querySelectorAll("[data-scenario]").forEach(b=>b.classList.toggle("on",b.dataset.scenario===key));
  const opLabels={freeze:"锁定主体",freeze_tags:"锁定保护对象",split_to_towers:"大体量拆分",heritage_step_down:"敏感对象退台",public_space_reconfiguration:"公共空间重构",courtyard_access_improvement:"院落通行改善",slim:"缩小轮廓",densify:"增加容量",open_ground:"释放地面",level:"平缓高度",micro_lease:"细分经营单元",frontage_quota:"沿街业态配额",crowd_valve:"客流阀门",night_reversion:"夜间归还"};
  const sr=currentScenarioRun(),cfg=sr.run_config||{},policy=((cfg.search||{}).operator_policy)||{};
  const statusLabel=sr.display_status==="preview_single_seed"?"平台预览（非正式实验）":esc(sr.display_status||"结果状态未标注");
  document.getElementById("scenarioDetail").innerHTML=`<div class="card"><h3>${esc(s.label)}</h3><p>${esc(s.description)}</p><div>${(policy.allowed_operators||s.operators||[]).map(op=>`<span class="pill">${esc(opLabels[op]||op)}</span>`).join("")}</div><p class="meta">${(sr.pareto||[]).length} 个 Pareto 方案 · ${statusLabel} · seed ${esc(sr.seed??"—")} · 运行 ${esc(sr.directory||"—")}</p></div>`;
  renderPareto();renderScenarioTechnical();
  const roleKey=(sr.role_keys||{})[selectedRole],fallbackKey=roleKey||Object.keys(sr.solution_metrics||{})[0]||"current";setRegime(fallbackKey);
  renderCombination();}
function selectRole(role){const r=GEOM.research||{},v=(r.roles||{})[role],key=(currentScenarioRun().role_keys||{})[role];if(!v)return;
  selectedRole=role;
  document.querySelectorAll("[data-role-view]").forEach(b=>b.classList.toggle("on",b.dataset.roleView===role));
  if(key)setRegime(key);renderCombination();}
function renderCombination(){const r=GEOM.research||{},s=(r.scenario_catalog||{})[selectedScenario],v=(r.roles||{})[selectedRole],key=(currentScenarioRun().role_keys||{})[selectedRole],m=(r.solution_metrics||{})[key];
  const el=document.getElementById("roleViewDetail");if(!el||!s||!v)return;
  if(!key||!m){el.innerHTML=`<div class="card warning"><h3>${esc(s.label)} × ${esc(v.label)}</h3><p>该角色首选方案缺少可验证的三维几何，因此不切换模型，也不把上一方案冒充为当前组合。</p></div>`;return;}
  el.innerHTML=`<div class="card ok"><h3>${esc(s.label)} × ${esc(v.label)}</h3><p>当前三维形态是${esc(v.label)}按离散优先级在该情景独立 Pareto 解集中的首选方案。</p><p class="meta">组合方案 ${esc((m||{}).solution_id||"—")} · 逐级排序只发生在求解之后，不回写优化循环。</p></div>`;}
function renderScenarioTechnical(){const r=GEOM.research||{},sr=currentScenarioRun(),cfg=sr.run_config||{},search=cfg.search||{},scenarioId=cfg.scenario_id||selectedScenario;
  const scenarioDefs=r.scenario_definitions||{},s=scenarioDefs[scenarioId]||{},def=s.defaults||{},impl=s.implementation||{},ranges=s.uncertainty_ranges||{};
  const range=(name,formatter)=>{const v=ranges[name];return Array.isArray(v)?`${formatter(v[0])}–${formatter(v[1])}`:"—";};
  const operatorRanges=[["densify_intensity","增建强度"],["open_ground_intensity","释放强度"],["split_to_towers_intensity","拆分强度"],["heritage_step_down_intensity","退台强度"],["public_space_reconfiguration_intensity","公共空间重构强度"],["courtyard_access_improvement_intensity","院落改善强度"]].filter(([k])=>Array.isArray(ranges[k])).map(([k,label])=>`<span class="pill">${label}范围 ${range(k,x=>num(x,2))}</span>`).join("");
  document.getElementById("scenarioCard").innerHTML=`<h3>${esc(s.label||scenarioId)}</h3><p>${esc(s.description||"")}</p><div class="row"><span class="pill">住宅保留范围 ${range("minimum_residential_retention",x=>pct(x,0))}</span><span class="pill">改动分区范围 ${range("maximum_changed_zone_ratio",x=>pct(x,0))}</span><span class="pill">改动建筑范围 ${range("maximum_changed_building_ratio",x=>pct(x,0))}</span>${operatorRanges}</div><p class="meta">当前三维运行使用范围内参考值：住宅保留 ${pct(def.minimum_residential_retention,0)}，最多改变 ${pct(impl.maximum_changed_building_ratio,0)} 建筑。它们是研究参数，不是法规阈值。</p>`;
  document.getElementById("workflowCard").innerHTML=`<p><b>城市数据</b> → 情景约束与主体权限 → 38 个道路围合单元 → 算子和强度 → 约束修复 → NSGA-II → 该情景 Pareto 解集 → 三类角色按离散优先级逐级排序 → 三维比较</p><p class="meta">平台预览 · seed ${esc(sr.seed??"—")} · ${esc(sr.directory||"—")} · 种群 ${esc(search.population||"—")} × ${esc(search.generations||"—")} 代 · ${esc(search.unique_evaluations||"—")} 次唯一评价 · 无角色数值权重</p>`;
  const avail=search.operator_availability||{},zoneCount=Object.keys(avail).length,opCount=k=>Object.values(avail).filter(xs=>xs.includes(k)).length;
  document.querySelectorAll("[data-op-availability]").forEach(el=>{const k=el.dataset.opAvailability;el.textContent=zoneCount?`${opCount(k)} / ${zoneCount} 个更新单元可用`:'当前情景不可用';});
  const balancedKey=(sr.role_keys||{}).balanced_compromise,solutionButtons=document.getElementById("solutionButtons");
  solutionButtons.innerHTML=balancedKey?`<button data-solution-key="${esc(balancedKey)}">查看最小最差主体名次的折中方案</button>`:'<span class="note">该情景尚无折中方案。</span>';
  solutionButtons.querySelectorAll("[data-solution-key]").forEach(b=>b.onclick=()=>setRegime(b.dataset.solutionKey));}
function renderResearch(){const r=GEOM.research||{},d=r.draft_summary||{},q=(r.formal_input_quality||{}).counts||{},ass=(r.assumptions||{}).profile||{};
  const stats=document.getElementById("researchStats");if(!stats)return;
  stats.innerHTML=[[q.buildings||d.building_count||1370,"建筑"],[q.intervention_zones||d.zone_count||38,"更新单元"],[q.heritage_building_footprints||21,"遗产冻结建筑"],[3,"优化目标"]].map(x=>`<div class="stat"><b>${x[0]}</b><span>${x[1]}</span></div>`).join("");
  const scenarioButtons=document.getElementById("scenarioButtons");
  scenarioButtons.innerHTML=Object.entries(r.scenario_catalog||{}).map(([k,v])=>`<button data-scenario="${esc(k)}">${esc(v.label)}</button>`).join("");
  scenarioButtons.querySelectorAll("[data-scenario]").forEach(b=>b.onclick=()=>selectScenario(b.dataset.scenario));
  const roleText={resident:"先减少居住影响暴露，再比较临街释放，最后比较正向增建量。",development:"先比较正向增建量，再比较临街释放，最后比较居住影响暴露。",public_planning:"先比较临街释放，再比较居住影响暴露，最后比较正向增建量。"};
  const shortObjective={residential_disruption:"居住影响暴露",development_capacity:"正向增建量",street_connected_released_ground:"临街释放"};
  document.getElementById("rolesList").innerHTML=Object.entries(r.roles||{}).map(([k,v])=>`<div class="card role"><h3>${esc(v.label)}</h3><p>${roleText[k]||"对同一组 Pareto 方案进行后评价。"}</p><div>${(v.priority_order||[]).map((o,i)=>`<span class="pill">${i+1}. ${esc(shortObjective[o]||o)}</span>`).join("")}</div><p class="meta">离散优先级 · epsilon 内视为同档 · 不使用精确权重</p></div>`).join("");
  const roleViewButtons=document.getElementById("roleViewButtons");
  roleViewButtons.innerHTML=Object.entries(r.roles||{}).map(([k,v])=>`<button data-role-view="${esc(k)}">${esc(v.label)}</button>`).join("");
  roleViewButtons.querySelectorAll("[data-role-view]").forEach(b=>b.onclick=()=>selectRole(b.dataset.roleView));
  const opText={noop:"保持现状，作为基线和可行解。",densify:"先计算单元剩余 FAR 与逐栋限高，再按请求增量比例分配高度。",open_ground:"缩小首层轮廓释放临街地面，在限高允许时增高以尽量补偿建筑面积。",split_to_towers:"只对面积达到门槛的大体量沿主轴切出间隙，并在限高内补偿建筑面积。",heritage_step_down:"在同一更新单元内把高度从住宅与遗产附近转移到较远位置，总容量近似守恒。",public_space_reconfiguration:"公共主体的非遗产资产只从最近道路一侧形成浅退界，不增高；它表示候选公共空间，不是施工设计。",courtyard_access_improvement:"居民住宅从临街方向切出受面积上限约束的窄通行缺口，不拆楼、不增容；它表示潜在通道。"};
  document.getElementById("operatorsList").innerHTML=Object.entries(r.operators||{}).map(([k,v])=>`<div class="card operator"><h3>${esc(v.label)} <span class="pill">${esc(k)}</span></h3><p>${opText[k]||esc(v.action)}</p><p class="meta" data-op-availability="${esc(k)}">可用性随所选情景更新</p></div>`).join("");
  document.getElementById("objectivesList").innerHTML=Object.values(r.objectives||{}).map(v=>`<div class="card"><h3>${esc(v.label)} <span class="pill">${esc(v.direction)}</span></h3><p>${esc(v.definition)}</p></div>`).join("");
  const constraintLabels={geometry_validity:"几何有效",study_boundary:"不越研究边界",heritage_unchanged:"保护对象不变",height_limit:"逐栋限高",zone_far:"单元容积率",zone_coverage:"单元覆盖率",residential_retention:"住宅保留",new_overlap:"新增体量不重叠",change_scope:"改动范围"};
  document.getElementById("constraintsList").innerHTML=Object.keys(r.constraints||{}).map(k=>`<span class="pill">${esc(constraintLabels[k]||k)}</span>`).join(" ");
  const e=r.experiment||{},em=e.means||{},cov=e.coverage||{},manifest=e.manifest||{};document.getElementById("experimentCard").innerHTML=e.run?`<div class="card ${Number(cov.nsga_over_random)>Number(cov.random_over_nsga)?'ok':'warning'}"><h3>当前模型搜索对比 · ${esc(e.run)}</h3><p>情景 ${esc(manifest.scenario||'—')} · ${esc((manifest.seeds||[]).length||'—')} 个随机种子；评价预算 ${esc(manifest.equal_effective_independent_evaluation_budget||manifest.equal_evaluation_budget||'—')} / 算法 / 种子。NSGA-II 平均 Pareto ${num((em.nsga2||{}).pareto_count,1)}，随机搜索 ${num((em.random||{}).pareto_count,1)}。</p><p>支配覆盖 C(NSGA,随机)=${pct(cov.nsga_over_random)}；C(随机,NSGA)=${pct(cov.random_over_nsga)}。</p><p class="meta">这是算法搜索对比；角色偏好只在求解后按离散顺序选择。</p></div>`:'<div class="card warning">当前三情景尚无同预算算法对比；旧情景的搜索结果不在这里显示。</div>';
  renderPareto();renderSolutionMetrics(cur);const firstScenario=Object.keys(r.scenario_catalog||{})[0],firstRole=Object.keys(r.roles||{})[0];if(firstScenario)selectScenario(firstScenario);if(firstRole)selectRole(firstRole);}
// —— 导出 ——
function dl(name){renderer.render(scene,cam);
  renderer.domElement.toBlob(bl=>{const a=document.createElement("a");a.href=URL.createObjectURL(bl);
    a.download=name;a.click();},"image/png");}
function exportCurrent(){dl(`${GEOM.slug}_${cur}_${mode}.png`);}
const MODES=["massing","depth","normal","segmentation","canny"];
async function exportAllModes(a){const keep=mode;
  for(const m of MODES){setMode(m);await new Promise(r=>setTimeout(r,120));dl(`${GEOM.slug}_${cur}_${a!==undefined?("ang"+a+"_"):""}${m}.png`);}
  setMode(keep);}
function saveAngle(){saved.push({p:cam.position.toArray(),t:controls.target.toArray()});renderAngles();}
function gotoAngle(i){const a=saved[i];cam.position.fromArray(a.p);controls.target.fromArray(a.t);controls.update();}
function delAngle(i){saved.splice(i,1);renderAngles();}
function renderAngles(){const el=document.getElementById("angs");el.innerHTML=saved.map((a,i)=>
  `<div class="ang"><a onclick="gotoAngle(${i})">角度 ${i+1}</a><span class="x" onclick="delAngle(${i})"></span></div>`).join("")||
  '<div class="note">还没保存角度。转到满意的视角,点「保存当前角度」。</div>';}
async function exportAllSaved(){if(!saved.length){alert("先保存至少一个角度");return;}
  for(let i=0;i<saved.length;i++){gotoAngle(i);await new Promise(r=>setTimeout(r,150));await exportAllModes(i+1);}}
window.addEventListener("DOMContentLoaded",()=>{init();
  document.querySelectorAll("[data-reg]").forEach(b=>b.onclick=()=>setRegime(b.dataset.reg));
  document.querySelectorAll("[data-mode]").forEach(b=>b.onclick=()=>setMode(b.dataset.mode));
  document.querySelectorAll("[data-basemap]").forEach(b=>b.onclick=()=>setBasemap(b.dataset.basemap));
  renderResearch();setRegime(cur);});
"""


HTML = """<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><link rel="icon" href="data:,"><title>%s · 多目标更新推演</title>
<style>%s</style></head><body>
<div id="stage"><canvas id="cv"></canvas></div>
<div class="panel">
  <h1>%s · 多目标更新推演</h1>
  <p class="sub">研究假设、空间算子、Pareto 方案与三维形态放在同一个可追溯界面中。</p>
  <a class="rep" href="report.html">完整报告</a>
  <div id="researchStats" class="stats"></div>

  <div class="grp">第一步 · 选择一种研究情景</div>
  <div id="scenarioButtons" class="row"></div>
  <div id="scenarioDetail"></div>
  <div class="note">三个情景分别改变可操作范围和规则边界；切换后保留当前角色，并按同一套离散优先级从新解集中选择。</div>

  <div class="grp">第二步 · 叠加一种角色视角</div>
  <div id="roleViewButtons" class="row"></div>
  <div id="roleViewDetail"></div>
  <div id="solutionMetrics"></div>
  <div id="solutionButtons" class="row"></div>

  <div class="grp">第三步 · 阅读当前情景的 Pareto 取舍</div>
  <svg id="paretoPlot" aria-label="Pareto 方案散点图"></svg>
  <div class="pareto-legend"><span class="good">低居住扰动</span><span>→</span><span class="bad">高居住扰动</span></div>
  <div class="card"><p><b>怎么看：</b>点越靠右，逐栋正向增建量越多；点越靠上，释放的临街地面越多；颜色越绿，直接修改或与强形态操作同处一个更新单元的住宅越少。黑圈标出当前角色按优先级逐级比较后的首选。</p><p class="meta">正向增建量不是净增长，净 GFA 在方案卡片中单列。三个情景分别计算，只有同一张图内的点可以直接比较。</p></div>

  <details><summary>查看定量优化设置、算子和角色优先级</summary>
    <div class="grp">共同的定量优化任务</div>
    <div id="scenarioCard" class="card"></div>
    <div class="grp">计算流程</div><div id="workflowCard" class="card"></div>
    <div class="grp">三类角色的离散优先级</div><div id="rolesList" class="cards"></div>
    <div class="grp">形态算子</div><div id="operatorsList"></div>
    <div class="grp">三个优化目标</div><div id="objectivesList"></div>
    <div class="grp">硬约束</div><div id="constraintsList" class="card"></div>
  </details>

  <div class="grp">算法对比</div>
  <div id="experimentCard"></div>

  <div class="grp">三维显示</div>
  <div class="row">
    <button data-mode="massing" class="on">体块 massing</button>
    <button data-mode="depth">深度 depth</button>
    <button data-mode="normal">法线 normal</button>
    <button data-mode="segmentation">分色 seg</button>
    <button data-mode="canny">边缘 canny</button>
    <button id="baselineOverlayButton" class="on" onclick="toggleBaselineOverlay()">橙线叠加现状</button>
  </div>
  <div class="legend">%s</div>

  <div class="grp">三维底图</div>
  <div class="row">
    <button data-basemap="osm" class="on">OSM 道路</button>
    <button data-basemap="satellite">卫星影像</button>
    <button data-basemap="none">关闭底图</button>
  </div>

  <details><summary>角度与图片导出</summary>
    <button class="big acc" onclick="saveAngle()">保存当前角度</button><div id="angs"></div>
    <button class="big" onclick="exportCurrent()">导出当前视图</button>
    <button class="big" onclick="exportAllModes()">当前角度全部 5 模式</button>
    <button class="big" onclick="exportAllSaved()">所有保存角度 × 全部模式</button>
    <div id="prm"></div>
    <div class="note">PNG 命名 <code>%s_&lt;方案&gt;_&lt;模式&gt;.png</code>；条件图不含底图。</div>
  </details>

  <details><summary>研究边界与限制</summary>
    <div class="note">当前平台使用公共协调、开发增长、居民生活与遗产保护三个研究情景。遗产硬约束采用 12 条已匹配官方记录对应的 21 个冻结建筑轮廓；4 条范围未决历史记录与 32 栋未匹配更新单元建筑分别记录、分别排除。情景参数以范围披露，当前三维方案是范围内参考值的一次求解，不能解释为法定规划。</div>
  </details>
</div>
<div class="hint">拖拽=旋转 滚轮=缩放 右键=平移</div>
<script>%s</script>
<script>%s</script>
<script>%s</script>
</body></html>"""


def build(slug=None):
    slug = slug or settings.SLUG
    geom = build_geometry(slug)
    geom["slug"] = slug
    regime_prompts = {
        r: d["prompt"]
        for r, d in prompt_gen.build_all(slug, geom["regimeKeys"]).items()
    }
    cf_prompts = {
        key: "反事实高度情景:%s。Footprint 与角色标签不变,只按 power_scenarios.yaml 重分配高度。"
        % geom["labels"][key]
        for key in geom.get("counterfactualKeys", [])
    }
    opt_prompts = {
        key: "多目标优化代表方案。形态由明确算子、规划约束和 Pareto 筛选产生；角色只在优化完成后评价，不回写目标。"
        for key in geom.get("optimizationKeys", [])
    }
    geom["prompts"] = {**regime_prompts, **cf_prompts, **opt_prompts}
    three = (WEB / "three.min.js").read_text(encoding="utf-8")
    orbit = (WEB / "OrbitControls.js").read_text(encoding="utf-8")
    place = geom["labels"].get(geom["regimes"][0], slug)
    site_name = ws05.C.site_meta(slug)["name"]
    legend = "".join('<span><i style="background:%s"></i>%s</span>' % (geom["colors"][sh], geom["sh_label"].get(sh, sh))
                     for sh in ["state", "developer", "resident", "unknown"])
    html = HTML % (site_name, CSS, site_name, legend, slug, three, orbit, viewer_js(geom))
    p = OUT / slug / "canvas.html"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(html, encoding="utf-8")
    print("写了:", p.relative_to(ROOT), "| %.2f MB" % (p.stat().st_size / 1e6))
    return p


if __name__ == "__main__":
    try:                                   # Windows 控制台 cp950 会崩,强制 utf-8
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    if len(sys.argv) > 1:
        build(sys.argv[1])
    else:
        for s in settings.REPORT_SITES if hasattr(settings, "REPORT_SITES") else [settings.SLUG]:
            print("=== %s ===" % s); build(s)
