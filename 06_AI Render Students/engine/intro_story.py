import json
from pathlib import Path

import geopandas as gpd
from shapely.geometry import LineString, mapping
from shapely.ops import unary_union
import yaml

import settings
import ws05


ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "out"


OP_META = {
    "freeze": {"label": "Freeze", "summary": "Lock existing residential or public parcels so later steps cannot rewrite them."},
    "freeze_tags": {"label": "Freeze Tags", "summary": "Protect sensitive areas tagged as heritage, residential cores, or emergency access."},
    "split_to_towers": {"label": "Split to Towers", "summary": "Break large development slabs into finer tower-like pieces and redistribute ground coverage."},
    "slim": {"label": "Slim", "summary": "Shrink footprints and lift height so capital mass becomes thinner, taller, and more visible."},
    "densify": {"label": "Densify", "summary": "Increase height in place to push development intensity and capacity upward."},
    "open_ground": {"label": "Open Ground", "summary": "Reduce building coverage and release the ground back to movement, pause, and community use."},
    "level": {"label": "Level", "summary": "Pull extreme heights back toward a more even urban field."},
    "micro_lease": {"label": "Micro Lease", "summary": "Subdivide large commercial mass into micro-lease units for small shops, services, and culture."},
    "frontage_quota": {"label": "Frontage Quota", "summary": "Limit tourist-facing frontage so local service and cultural display keep space on the street edge."},
    "crowd_valve": {"label": "Crowd Valve", "summary": "Compress tourist frontage at peak flow and open relief nodes plus one-way circulation."},
    "night_reversion": {"label": "Night Reversion", "summary": "After 22:00, return selected consumption interfaces near housing cores back to residents."},
}

SCENARIO_COPY = {
    "tourism_capture": {
        "label": "Tourism Capture",
        "caption": "Tourist flow and commercial visibility dominate, so edge development is split, slimmed, and intensified.",
        "accent": "#ff6b3d",
    },
    "everyday_life_first": {
        "label": "Everyday Life First",
        "caption": "Resident safety, daily access, and neighborhood services come first, so commercial mass gives ground back.",
        "accent": "#6ce0d6",
    },
    "heritage_micro_economy": {
        "label": "Heritage Micro-Economy",
        "caption": "Historic fabric is not cleared and rebuilt; it is transformed into a network of micro-lease, micro-business, and culture.",
        "accent": "#f2c166",
    },
    "negotiated_24h_alley": {
        "label": "Negotiated 24h Alley",
        "caption": "The same alley switches its rights structure by time of day, producing a 24-hour negotiated spatial protocol.",
        "accent": "#8d9cff",
    },
}


def _site_meta(slug):
    site_path = ws05.C.DATA / slug / "site.yaml"
    if site_path.exists():
        return yaml.safe_load(site_path.read_text(encoding="utf-8"))
    return {}


def _to_gdf(recs):
    rows = []
    for idx, rec in enumerate(recs):
        rows.append(
            {
                "id": idx,
                "geometry": rec["geom"],
                "height": float(rec["h"]),
                "sh": rec["sh"],
                "tags": ",".join(str(v) for v in rec.get("tags", [])),
                "frozen": bool(rec.get("frozen", False)),
            }
        )
    gdf = gpd.GeoDataFrame(rows, geometry="geometry", crs=ws05.C.UTM).to_crs(4326)
    gdf["stakeholderLabel"] = gdf["sh"].map(ws05.C.SH_LABEL).fillna("Unknown")
    gdf["color"] = gdf["sh"].map(ws05.C.SH_COLOR).fillna("#9fb3c8")
    return gdf


def _feature_collection(gdf, keys=None):
    keys = keys or [c for c in gdf.columns if c != "geometry"]
    features = []
    for _, row in gdf.iterrows():
        props = {}
        for key in keys:
            value = row[key]
            if value is not None:
                props[key] = value
        features.append({"type": "Feature", "geometry": mapping(row.geometry), "properties": props})
    return {"type": "FeatureCollection", "features": features}


def _collection_from_recs(recs):
    return _feature_collection(_to_gdf(recs))


def _line_feature(line):
    gdf = gpd.GeoDataFrame([{"geometry": line}], geometry="geometry", crs=ws05.C.UTM).to_crs(4326)
    return {
        "type": "FeatureCollection",
        "features": [{"type": "Feature", "geometry": mapping(gdf.geometry.iloc[0]), "properties": {}}],
    }


def _polygon_feature(geom):
    gdf = gpd.GeoDataFrame([{"geometry": geom}], geometry="geometry", crs=ws05.C.UTM).to_crs(4326)
    return {
        "type": "FeatureCollection",
        "features": [{"type": "Feature", "geometry": mapping(gdf.geometry.iloc[0]), "properties": {}}],
    }


def _point_collection(points, metric_key):
    if not points:
        return {"type": "FeatureCollection", "features": []}
    gdf = gpd.GeoDataFrame(points, geometry="geometry", crs=ws05.C.UTM).to_crs(4326)
    return _feature_collection(gdf, [metric_key])


def _build_spine(recs):
    axis = ws05.ops._mo._site_axis(recs)
    orient, cx, cy, _span = axis
    union = unary_union([rec["geom"] for rec in recs])
    minx, miny, maxx, maxy = union.bounds
    if orient == "x":
        return LineString([(minx, cy), (maxx, cy)])
    return LineString([(cx, miny), (cx, maxy)])


def _scenario_sequences(base_recs, regs, regime_names):
    sequences = {}
    for name in regime_names:
        if name == "current":
            continue
        cur = [dict(rec) for rec in base_recs]
        steps = []
        for step in regs[name]["steps"]:
            op = step["op"]
            fn = ws05.ops.OPS[op]
            kwargs = {k: v for k, v in step.items() if k != "op"}
            cur = fn(cur, **kwargs)
            meta = OP_META.get(op, {"label": op, "summary": "This operator redistributes built form and spatial rights."})
            steps.append(
                {
                    "op": op,
                    "label": meta["label"],
                    "summary": meta["summary"],
                    "collection": _collection_from_recs(cur),
                    "buildingCount": len(cur),
                }
            )
        sequences[name] = {
            "label": SCENARIO_COPY.get(name, {}).get("label", ws05.regime_label(regs, name)),
            "caption": SCENARIO_COPY.get(name, {}).get("caption", ""),
            "accent": SCENARIO_COPY.get(name, {}).get("accent", "#9fb3c8"),
            "steps": steps,
            "finalCollection": steps[-1]["collection"] if steps else _collection_from_recs(cur),
        }
    return sequences


def _all_operators(regs, regime_names):
    seen = []
    used = set()
    for name in regime_names:
        if name == "current":
            continue
        for step in regs.get(name, {}).get("steps", []):
            op = step["op"]
            if op in used:
                continue
            used.add(op)
            meta = OP_META.get(op, {"label": op, "summary": "This operator redistributes built form and spatial rights."})
            seen.append(
                {
                    "key": op,
                    "label": meta["label"],
                    "summary": meta["summary"],
                    "accent": SCENARIO_COPY.get(name, {}).get("accent", "#9fb3c8"),
                }
            )
    return seen


def _operator_metrics(recs):
    tagged = ws05.ops._mo._copy_with_tags(recs)
    valved = ws05.ops._mo.crowd_valve(
        tagged,
        route="tourist_spine",
        crowd_threshold=0.75,
        one_way_links=True,
        protect_tags=["resident_gate", "emergency_access"],
        relief_nodes=3,
    )
    night = ws05.ops._mo.night_reversion(
        valved,
        start_hour=22,
        quiet_buffer_m=10,
        commercial_shutdown_ratio=0.60,
        protect_tags=["residential_core", "resident_gate"],
    )
    relief_points = []
    for rec in valved:
        if "relief_node" in rec.get("tags", []):
            relief_points.append({"geometry": rec["geom"].centroid, "weight": round(rec["geom"].area, 1)})
    quiet_recs = [rec for rec in night if "night_quiet" in rec.get("tags", [])]
    residents = [rec for rec in tagged if ws05.ops._mo._has_any_tag(rec, ["residential_core", "resident_gate"])]
    quiet_buffer = unary_union([rec["geom"].centroid.buffer(10) for rec in residents[:60]]) if residents else None
    return {
        "tagged": tagged,
        "valved": valved,
        "night": night,
        "relief": relief_points,
        "quiet": quiet_recs,
        "quietBuffer": quiet_buffer,
    }


def build_intro_payload(slug=None):
    slug = slug or settings.SLUG
    site = _site_meta(slug)
    current_recs, _df = ws05.load_recs(slug)
    _regs_map, regs = ws05.regime_recs(slug, settings.REGIMES)
    current_tagged_data = _operator_metrics(current_recs)
    current_tagged = current_tagged_data["tagged"]
    current_gdf = _to_gdf(current_tagged)
    district_outline = unary_union([rec["geom"] for rec in current_recs]).convex_hull.buffer(20)
    tourist_spine = _build_spine(current_tagged)
    sequences = _scenario_sequences(current_recs, regs, settings.REGIMES)

    stakeholder_counts = {}
    for sh in sorted({rec["sh"] for rec in current_tagged}):
        stakeholder_counts[sh] = sum(rec["sh"] == sh for rec in current_tagged)

    payload = {
        "meta": {
            "slug": slug,
            "title": "Dapuqiao 24h Negotiated District",
            "siteName": site.get("name", slug),
            "center": list(current_gdf.geometry.union_all().centroid.coords[0]),
            "bounds": site.get("bounds_lonlat"),
            "colors": ws05.C.SH_COLOR,
            "durationMs": 15000,
        },
        "stats": {
            "buildingCount": len(current_tagged),
            "stakeholderCounts": stakeholder_counts,
            "operatorMetrics": {
                "crowdValve": {
                    "reliefNodes": sum("relief_node" in rec.get("tags", []) for rec in current_tagged_data["valved"]),
                    "oneWayAlleys": sum("one_way_alley" in rec.get("tags", []) for rec in current_tagged_data["valved"]),
                },
                "nightReversion": {
                    "quietBuildings": len(current_tagged_data["quiet"]),
                },
            },
        },
        "operators": [
            {
                "key": "crowd_valve",
                "label": "Crowd Valve",
                "accent": "#ff6b3d",
                "summary": "At peak flow, tourist frontage along the main spine is compressed to release relief nodes and one-way movement.",
                "metrics": [
                    f"{sum('relief_node' in rec.get('tags', []) for rec in current_tagged_data['valved'])} relief nodes",
                    f"{sum('one_way_alley' in rec.get('tags', []) for rec in current_tagged_data['valved'])} one-way alleys",
                ],
            },
            {
                "key": "night_reversion",
                "label": "Night Reversion",
                "accent": "#6ce0d6",
                "summary": "After 22:00, nightlife interfaces near the residential core contract and quiet access returns to residents.",
                "metrics": [
                    f"{len(current_tagged_data['quiet'])} buildings in quiet mode",
                    "22:00 start / 10m quiet buffer",
                ],
            },
        ],
        "allOperators": _all_operators(regs, settings.REGIMES),
        "scenarios": [
            {
                "key": name,
                "label": SCENARIO_COPY.get(name, {}).get("label", ws05.regime_label(regs, name)),
                "ops": [step["op"] for step in regs.get(name, {}).get("steps", [])],
                "accent": SCENARIO_COPY.get(name, {}).get("accent", "#9fb3c8"),
                "caption": SCENARIO_COPY.get(name, {}).get("caption", ""),
            }
            for name in settings.REGIMES
            if name != "current"
        ],
        "scenarioSequences": sequences,
        "collections": {
            "current": _feature_collection(current_gdf),
            "district": _polygon_feature(district_outline),
            "touristSpine": _line_feature(tourist_spine),
            "reliefNodes": _point_collection(current_tagged_data["relief"], "weight"),
            "quietBuildings": _collection_from_recs(current_tagged_data["quiet"]),
            "quietBuffer": _polygon_feature(current_tagged_data["quietBuffer"]) if current_tagged_data["quietBuffer"] else {"type": "FeatureCollection", "features": []},
        },
    }
    return payload


def frame_output_dir(slug, duration_s=15, fps=24):
    return OUT / slug / f"intro_story_frames_{duration_s}s_{fps}fps"


def video_output_path(slug, duration_s=15):
    return OUT / slug / f"intro_story_dark_{duration_s}s.mp4"


def capture_frame_indices(duration_s=15, fps=24):
    return list(range(duration_s * fps))


HTML_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Dapuqiao Intro Story</title>
  <link href="https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.css" rel="stylesheet" />
  <style>
    :root{
      --bg:#04070d;
      --panel:rgba(8,12,20,.82);
      --line:rgba(255,255,255,.12);
      --soft:rgba(228,238,255,.72);
      --soft2:rgba(228,238,255,.5);
      --hot:#ff6b3d;
      --cool:#6ce0d6;
      --gold:#f2c166;
      --violet:#8d9cff;
    }
    *{box-sizing:border-box}
    html,body{margin:0;height:100%;overflow:hidden;background:var(--bg);font-family:"Segoe UI","Helvetica Neue",Arial,sans-serif;color:#f6f8fb}
    #map{position:fixed;inset:0}
    .grain,.vignette,.scan{position:fixed;inset:0;pointer-events:none}
    .grain{background-image:radial-gradient(rgba(255,255,255,.03) 1px, transparent 1px);background-size:3px 3px;mix-blend-mode:soft-light;opacity:.2}
    .vignette{background:radial-gradient(circle at 50% 45%, transparent 34%, rgba(0,0,0,.58) 100%)}
    .scan{background:linear-gradient(to bottom, rgba(108,224,214,.05), transparent 24%, transparent 76%, rgba(255,107,61,.05));opacity:.85}
    .hud{position:fixed;inset:0;display:grid;grid-template-columns:390px 1fr 410px;pointer-events:none}
    .panel{margin:22px;padding:18px;border:1px solid var(--line);border-radius:22px;background:var(--panel);backdrop-filter:blur(16px);box-shadow:0 18px 50px rgba(0,0,0,.34)}
    .left{align-self:start}
    .right{align-self:start;justify-self:end}
    .eyebrow{font-size:11px;letter-spacing:.18em;text-transform:uppercase;color:rgba(255,255,255,.56)}
    h1{margin:8px 0 10px;font-size:34px;line-height:1.06;font-weight:700;letter-spacing:.01em}
    .lede{margin:0;color:var(--soft);font-size:14px;line-height:1.6}
    .metric-grid{margin-top:18px;display:grid;grid-template-columns:1fr 1fr;gap:10px}
    .metric{padding:12px;border-radius:16px;background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.07)}
    .metric strong{display:block;font-size:22px}
    .metric span{font-size:11px;color:rgba(255,255,255,.64);text-transform:uppercase;letter-spacing:.08em}
    .chips{margin-top:16px;display:flex;gap:8px;flex-wrap:wrap;pointer-events:auto}
    .chip{padding:7px 12px;border-radius:999px;border:1px solid var(--line);background:rgba(255,255,255,.04);font-size:12px;color:#dce7f7;cursor:pointer}
    .chip.active{background:rgba(255,255,255,.15)}
    .section-title{margin:0 0 10px;font-size:12px;letter-spacing:.16em;text-transform:uppercase;color:rgba(255,255,255,.48)}
    .scenario-card{padding:14px;border-radius:18px;border:1px solid rgba(255,255,255,.07);background:rgba(255,255,255,.04)}
    .scenario-card + .scenario-card{margin-top:10px}
    .scenario-card h3{margin:0 0 8px;font-size:15px}
    .scenario-card p{margin:0;color:var(--soft);font-size:12px;line-height:1.6}
    .accent{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:8px}
    .scenario-card{opacity:.44;transform:translateX(0);transition:opacity .3s ease, transform .3s ease, border-color .3s ease;pointer-events:auto;cursor:pointer}
    .scenario-card.active{opacity:1;transform:translateX(-6px);border-color:rgba(255,255,255,.22)}
    .scenario-card .caption{margin-top:8px;color:var(--soft2)}
    .step-strip{margin-top:14px;padding:12px;border-radius:18px;background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.07)}
    .step-title{font-size:12px;color:rgba(255,255,255,.56);text-transform:uppercase;letter-spacing:.14em}
    .step-name{margin-top:8px;font-size:18px;font-weight:700}
    .step-summary{margin-top:6px;font-size:12px;color:var(--soft);line-height:1.6}
    .step-dots{display:flex;gap:7px;flex-wrap:wrap;margin-top:12px}
    .step-dots span{width:10px;height:10px;border-radius:50%;background:rgba(255,255,255,.12);display:block}
    .step-dots span.active{background:linear-gradient(135deg,#fff,var(--cool))}
    .bottom{position:fixed;left:22px;right:22px;bottom:18px;display:flex;gap:14px;align-items:flex-end}
    .stage-line{flex:1;padding:14px 16px 16px;border-radius:18px;border:1px solid var(--line);background:rgba(7,12,20,.9)}
    .stage-label{display:flex;justify-content:space-between;font-size:12px;color:rgba(255,255,255,.72)}
    .timeline{height:6px;border-radius:999px;background:rgba(255,255,255,.08);overflow:hidden;margin-top:10px}
    .timeline > div{height:100%;width:0;background:linear-gradient(90deg,var(--cool),#a3f0e8,var(--hot))}
    .operator-rail{margin-top:12px;display:flex;gap:8px;align-items:center;flex-wrap:nowrap;overflow:hidden}
    .operator-pill{display:inline-flex;align-items:center;gap:8px;padding:7px 11px;border-radius:999px;border:1px solid rgba(255,255,255,.08);background:rgba(255,255,255,.04);font-size:11px;color:rgba(255,255,255,.68);white-space:nowrap;opacity:.52;transform:scale(.98);transition:opacity .25s ease, transform .25s ease, border-color .25s ease, background .25s ease}
    .operator-pill i{display:inline-block;width:7px;height:7px;border-radius:50%}
    .operator-pill.active{opacity:1;transform:scale(1);border-color:rgba(255,255,255,.22);background:rgba(255,255,255,.1);color:#f7fbff}
    .tooltip{position:fixed;min-width:180px;padding:10px 12px;border-radius:14px;border:1px solid var(--line);background:rgba(5,9,16,.92);pointer-events:none;opacity:0;transform:translate(12px,12px);transition:opacity .15s ease}
    .tooltip strong{display:block;margin-bottom:4px}
    .tooltip small{color:rgba(255,255,255,.58)}
    .maplibregl-ctrl-bottom-right,.maplibregl-ctrl-bottom-left{display:none}
  </style>
</head>
<body>
  <div id="map"></div>
  <div class="grain"></div>
  <div class="vignette"></div>
  <div class="scan"></div>

  <div class="hud">
    <div class="panel left">
      <div class="eyebrow">Urban Reading to Urban Rewriting</div>
      <h1>Dapuqiao as a Negotiated Urban Machine</h1>
      <p class="lede" id="lede"></p>
      <div class="chips">
        <button class="chip active" data-stage="0">01 Location</button>
        <button class="chip" data-stage="1">02 Stakeholders</button>
        <button class="chip" data-stage="2">03 Operators</button>
        <button class="chip" data-stage="3">04 Scenarios</button>
      </div>
      <div class="metric-grid">
        <div class="metric"><span>Buildings</span><strong id="buildingCount"></strong></div>
        <div class="metric"><span>Stakeholders</span><strong id="stakeholderKinds"></strong></div>
      </div>
    </div>
    <div></div>
    <div class="panel right">
      <p class="section-title">Regimes</p>
      <div id="scenarioCards"></div>
      <div class="step-strip">
        <div class="step-title">Current Morphing Step</div>
        <div class="step-name" id="stepName">Current</div>
        <div class="step-summary" id="stepSummary">Current massing is visible.</div>
        <div class="step-dots" id="stepDots"></div>
      </div>
    </div>
  </div>

  <div class="bottom">
    <div class="stage-line">
      <div class="stage-label"><span id="stageName"></span><span>0-15s intro loop / scenario cards are clickable</span></div>
      <div class="timeline"><div id="progressBar"></div></div>
      <div class="operator-rail" id="operatorRail"></div>
    </div>
  </div>

  <div class="tooltip" id="tooltip"></div>

  <script src="https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.js"></script>
  <script>
    const PAYLOAD = __PAYLOAD__;
    const STAGES = [
      { name: "Reading the site", lede: "Enter Dapuqiao through a dark OSM map and read its boundary, alley spine, and overall spatial envelope." },
      { name: "Mapping stakeholders", lede: "Recolor buildings by capital, residents, public actors, and unresolved parcels to reveal who already occupies the fabric." },
      { name: "Activating operators", lede: "Use the negotiated_24h_alley chain to show how one alley is reorganized across different times of day." },
      { name: "Opening scenarios", lede: "The four regimes do not just rename the site; they trigger different operator chains and produce different urban forms." }
    ];

    const stageName = document.getElementById("stageName");
    const lede = document.getElementById("lede");
    const progressBar = document.getElementById("progressBar");
    const tooltip = document.getElementById("tooltip");
    const stepName = document.getElementById("stepName");
    const stepSummary = document.getElementById("stepSummary");
    const stepDots = document.getElementById("stepDots");

    document.getElementById("buildingCount").textContent = PAYLOAD.stats.buildingCount;
    document.getElementById("stakeholderKinds").textContent = Object.keys(PAYLOAD.stats.stakeholderCounts).length;

    const operatorRail = document.getElementById("operatorRail");
    PAYLOAD.allOperators.forEach((op) => {
      const div = document.createElement("div");
      div.className = "operator-pill";
      div.dataset.key = op.key;
      div.innerHTML = `<i style="background:${op.accent}"></i><span>${op.label}</span>`;
      operatorRail.appendChild(div);
    });

    const scenarioCards = document.getElementById("scenarioCards");
    PAYLOAD.scenarios.forEach((scenario, idx) => {
      const div = document.createElement("div");
      div.className = "scenario-card" + (idx === 0 ? " active" : "");
      div.dataset.key = scenario.key;
      div.innerHTML = `<h3><span class="accent" style="background:${scenario.accent}"></span>${scenario.label}</h3><p>${scenario.ops.join(" -> ")}</p><p class="caption">${scenario.caption}</p>`;
      div.addEventListener("click", () => playScenarioSequence(scenario.key, true));
      scenarioCards.appendChild(div);
    });

    const chips = [...document.querySelectorAll(".chip")];
    chips.forEach((chip) => chip.addEventListener("click", () => jumpToStage(Number(chip.dataset.stage))));

    const map = new maplibregl.Map({
      container: "map",
      style: {
        version: 8,
        sources: {
          base: {
            type: "raster",
            tiles: ["https://basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"],
            tileSize: 256,
            attribution: "OSM / CARTO"
          }
        },
        layers: [{ id: "base", type: "raster", source: "base", paint: { "raster-brightness-max": 0.72, "raster-saturation": -0.35 } }]
      },
      center: PAYLOAD.meta.center,
      zoom: 14.2,
      pitch: 48,
      bearing: -18,
      antialias: true
    });

    let loopStart = null;
    let manualScenarioUntil = 0;
    let manualStage = null;
    let currentScenarioKey = null;
    let currentStepIndex = -1;

    map.on("load", () => {
      map.addSource("district", { type: "geojson", data: PAYLOAD.collections.district });
      map.addSource("buildings", { type: "geojson", data: PAYLOAD.collections.current });
      map.addSource("touristSpine", { type: "geojson", data: PAYLOAD.collections.touristSpine });
      map.addSource("reliefNodes", { type: "geojson", data: PAYLOAD.collections.reliefNodes });
      map.addSource("quietBuffer", { type: "geojson", data: PAYLOAD.collections.quietBuffer });
      map.addSource("quietBuildings", { type: "geojson", data: PAYLOAD.collections.quietBuildings });

      map.addLayer({ id: "district-fill", type: "fill", source: "district", paint: { "fill-color": "#0e1c2c", "fill-opacity": 0.22 } });
      map.addLayer({ id: "quiet-buffer", type: "fill", source: "quietBuffer", paint: { "fill-color": "#6ce0d6", "fill-opacity": 0.0 } });
      map.addLayer({
        id: "buildings",
        type: "fill-extrusion",
        source: "buildings",
        paint: {
          "fill-extrusion-color": ["get", "color"],
          "fill-extrusion-height": ["get", "height"],
          "fill-extrusion-base": 0,
          "fill-extrusion-opacity": 0.78
        }
      });
      map.addLayer({ id: "quiet-buildings", type: "line", source: "quietBuildings", paint: { "line-color": "#6ce0d6", "line-width": 1.3, "line-opacity": 0.0 } });
      map.addLayer({ id: "tourist-spine-glow", type: "line", source: "touristSpine", paint: { "line-color": "#ff6b3d", "line-width": 12, "line-opacity": 0.0, "line-blur": 8 } });
      map.addLayer({ id: "tourist-spine", type: "line", source: "touristSpine", paint: { "line-color": "#ffd0b7", "line-width": 2.2, "line-opacity": 0.0, "line-dasharray": [1.2, 1.6] } });
      map.addLayer({
        id: "relief-nodes",
        type: "circle",
        source: "reliefNodes",
        paint: { "circle-color": "#ff6b3d", "circle-stroke-color": "#fff4eb", "circle-stroke-width": 1, "circle-radius": 0, "circle-opacity": 0.0 }
      });
      map.addLayer({ id: "district-line", type: "line", source: "district", paint: { "line-color": "#d9f7ff", "line-width": 1.2, "line-opacity": 0.52 } });

      map.fitBounds([[PAYLOAD.meta.bounds[0], PAYLOAD.meta.bounds[1]], [PAYLOAD.meta.bounds[2], PAYLOAD.meta.bounds[3]]], {
        padding: { top: 130, right: 470, bottom: 120, left: 420 },
        duration: 0
      });
      bindHover();
      setStepInfo(null, null);
      requestAnimationFrame(frame);
    });

    function bindHover() {
      map.on("mousemove", "buildings", (e) => {
        const feature = e.features && e.features[0];
        if (!feature) return;
        const p = feature.properties || {};
        tooltip.style.opacity = 1;
        tooltip.style.left = `${e.point.x}px`;
        tooltip.style.top = `${e.point.y}px`;
        tooltip.innerHTML = `<strong>${p.stakeholderLabel || p.sh}</strong><div>${Number(p.height || 0).toFixed(1)} m</div><small>${String(p.tags || "").replaceAll(",", " · ")}</small>`;
      });
      map.on("mouseleave", "buildings", () => { tooltip.style.opacity = 0; });
    }

    function jumpToStage(stageIndex) {
      loopStart = performance.now() - stageIndex * 3750;
      manualStage = null;
    }

    function setScenarioActive(key) {
      document.querySelectorAll(".scenario-card").forEach((card) => {
        card.classList.toggle("active", card.dataset.key === key);
      });
    }

    function setOperatorActive(opKey) {
      document.querySelectorAll(".operator-pill").forEach((card) => {
        card.classList.toggle("active", card.dataset.key === opKey);
      });
    }

    function setStepInfo(key, stepIndex) {
      if (!key || stepIndex === null || stepIndex < 0) {
        stepName.textContent = "Current";
        stepSummary.textContent = "Current massing and the existing stakeholder distribution are visible.";
        stepDots.innerHTML = "";
        setOperatorActive(null);
        return;
      }
      const sequence = PAYLOAD.scenarioSequences[key];
      const step = sequence.steps[stepIndex];
      stepName.textContent = `${sequence.label} · ${step.label}`;
      stepSummary.textContent = step.summary;
      stepDots.innerHTML = sequence.steps.map((_, idx) => `<span class="${idx === stepIndex ? "active" : ""}"></span>`).join("");
      setOperatorActive(step.op);
    }

    function setBuildings(collection) {
      map.getSource("buildings").setData(collection);
    }

    function playScenarioSequence(key, userTriggered=false) {
      currentScenarioKey = key;
      manualScenarioUntil = performance.now() + 6000;
      manualStage = 3;
      setScenarioActive(key);
      const sequence = PAYLOAD.scenarioSequences[key];
      if (!sequence) return;
      sequence.steps.forEach((step, idx) => {
        setTimeout(() => {
          if (performance.now() > manualScenarioUntil + 200) return;
          currentStepIndex = idx;
          setBuildings(step.collection);
          setStepInfo(key, idx);
        }, idx * 700);
      });
      setTimeout(() => {
        if (performance.now() <= manualScenarioUntil + 300) {
          setBuildings(sequence.finalCollection);
          currentStepIndex = sequence.steps.length - 1;
          setStepInfo(key, currentStepIndex);
        }
      }, sequence.steps.length * 700);
      if (userTriggered) {
        stageName.textContent = "Scenario chain playback";
        lede.textContent = sequence.caption;
      }
    }

    function frame(ts) {
      if (!loopStart) loopStart = ts;
      const elapsed = (ts - loopStart) % PAYLOAD.meta.durationMs;
      renderAtElapsed(elapsed, ts);
      requestAnimationFrame(frame);
    }

    function renderAtElapsed(elapsed, ts) {
      const autoStage = Math.min(3, Math.floor(elapsed / 3750));
      const stage = (manualStage !== null && ts < manualScenarioUntil) ? manualStage : autoStage;
      const local = (elapsed % 3750) / 3750;

      progressBar.style.width = `${(elapsed / PAYLOAD.meta.durationMs) * 100}%`;
      chips.forEach((chip, idx) => chip.classList.toggle("active", idx === stage));
      stageName.textContent = STAGES[stage].name;
      lede.textContent = STAGES[stage].lede;

      if (!(manualStage !== null && ts < manualScenarioUntil)) {
        driveAutoSequence(stage, local);
      }
      animateMap(stage, local, elapsed / PAYLOAD.meta.durationMs);
    }

    window.__codexRenderAt = (elapsedMs) => {
      manualStage = null;
      manualScenarioUntil = 0;
      renderAtElapsed(((elapsedMs % PAYLOAD.meta.durationMs) + PAYLOAD.meta.durationMs) % PAYLOAD.meta.durationMs, performance.now() + 1000);
      return true;
    };

    function driveAutoSequence(stage, local) {
      if (stage === 0 || stage === 1) {
        if (currentScenarioKey !== null) {
          currentScenarioKey = null;
          currentStepIndex = -1;
          setBuildings(PAYLOAD.collections.current);
          setStepInfo(null, null);
        }
        return;
      }
      if (stage === 2) {
        const key = "negotiated_24h_alley";
        const sequence = PAYLOAD.scenarioSequences[key];
        const idx = Math.min(sequence.steps.length - 1, Math.floor(local * sequence.steps.length));
        if (currentScenarioKey !== key || currentStepIndex !== idx) {
          currentScenarioKey = key;
          currentStepIndex = idx;
          setScenarioActive(key);
          setBuildings(sequence.steps[idx].collection);
          setStepInfo(key, idx);
        }
        return;
      }
      if (stage === 3) {
        const scenarios = PAYLOAD.scenarios;
        const idx = Math.min(scenarios.length - 1, Math.floor(local * scenarios.length));
        const scenario = scenarios[idx];
        const sequence = PAYLOAD.scenarioSequences[scenario.key];
        const stepIdx = sequence.steps.length - 1;
        if (currentScenarioKey !== scenario.key || currentStepIndex !== stepIdx) {
          currentScenarioKey = scenario.key;
          currentStepIndex = stepIdx;
          setScenarioActive(scenario.key);
          setBuildings(sequence.finalCollection);
          setStepInfo(scenario.key, stepIdx);
        }
      }
    }

    function animateMap(stage, local, totalT) {
      const introZoom = 13.85 + local * 0.85;
      const stakeholderZoom = 14.7 + Math.sin(local * Math.PI) * 0.08;
      const operatorZoom = 14.78 + Math.sin(local * Math.PI) * 0.14;
      const scenarioZoom = 14.86 + Math.sin(local * Math.PI) * 0.06;
      if (stage === 0) {
        map.easeTo({ center: PAYLOAD.meta.center, zoom: introZoom, pitch: 40 + local * 14, bearing: -26 + local * 10, duration: 0 });
      } else if (stage === 1) {
        map.easeTo({ center: PAYLOAD.meta.center, zoom: stakeholderZoom, pitch: 54, bearing: -14, duration: 0 });
      } else if (stage === 2) {
        map.easeTo({ center: PAYLOAD.meta.center, zoom: operatorZoom, pitch: 58, bearing: -8 + local * 12, duration: 0 });
      } else {
        map.easeTo({ center: PAYLOAD.meta.center, zoom: scenarioZoom, pitch: 60, bearing: 2 + local * 16, duration: 0 });
      }

      const pulse = 0.45 + 0.55 * Math.sin(totalT * Math.PI * 8) ** 2;
      map.setPaintProperty("district-line", "line-opacity", 0.35 + pulse * 0.3);
      map.setPaintProperty("buildings", "fill-extrusion-opacity", stage >= 1 ? 0.9 : 0.45 + local * 0.22);

      const operatorOn = stage >= 2;
      map.setPaintProperty("tourist-spine", "line-opacity", operatorOn ? 0.78 : 0.0);
      map.setPaintProperty("tourist-spine-glow", "line-opacity", operatorOn ? 0.28 + pulse * 0.25 : 0.0);
      map.setPaintProperty("relief-nodes", "circle-opacity", operatorOn ? 0.88 : 0.0);
      map.setPaintProperty("relief-nodes", "circle-radius", operatorOn ? 4 + pulse * 7 : 0);
      map.setPaintProperty("quiet-buffer", "fill-opacity", operatorOn ? 0.08 + pulse * 0.08 : 0.0);
      map.setPaintProperty("quiet-buildings", "line-opacity", operatorOn ? 0.88 : 0.0);

      if (stage === 3 && currentScenarioKey) {
        const scenario = PAYLOAD.scenarioSequences[currentScenarioKey];
        map.setPaintProperty("district-fill", "fill-color", scenario.accent);
        map.setPaintProperty("district-fill", "fill-opacity", 0.1 + pulse * 0.12);
      } else {
        map.setPaintProperty("district-fill", "fill-color", "#0e1c2c");
        map.setPaintProperty("district-fill", "fill-opacity", 0.22);
      }
    }
  </script>
</body>
</html>
"""


def build(slug=None):
    slug = slug or settings.SLUG
    payload = build_intro_payload(slug)
    out_dir = OUT / slug
    out_dir.mkdir(parents=True, exist_ok=True)
    html = HTML_TEMPLATE.replace("__PAYLOAD__", json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
    out_path = out_dir / "intro_story_dark.html"
    out_path.write_text(html, encoding="utf-8")
    return out_path
