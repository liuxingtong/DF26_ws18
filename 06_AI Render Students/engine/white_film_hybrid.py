import json
from functools import lru_cache
from pathlib import Path

import editorial_data_film
import intro_story
import settings
import ws05
from shapely.geometry import shape


ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "out"


BEATS = [
    {
        "key": "site_intro",
        "label": "Site and Regimes",
        "start": 0,
        "end": 2000,
        "lede": "One district, four possible reallocations of urban life.",
    },
    {
        "key": "data_shift",
        "label": "Scenario Metrics",
        "start": 3000,
        "end": 7000,
        "lede": "The same site is re-read through count, height, area, and pressure differences.",
    },
    {
        "key": "operator_logic",
        "label": "Operator Logic",
        "start": 7000,
        "end": 10000,
        "lede": "Crowd valve and night reversion explain how the district is reorganized in plan.",
    },
]


def output_path(slug):
    return OUT / slug / "white_film_hybrid.html"


def _scenario_bar_rows(metrics):
    return [
        {"key": "tourism_capture", "label": "Tourism Capture", "value": metrics["tourism_capture"]["avgHeight"]},
        {"key": "everyday_life_first", "label": "Everyday Life First", "value": metrics["everyday_life_first"]["avgHeight"]},
        {"key": "heritage_micro_economy", "label": "Heritage Micro-Economy", "value": metrics["heritage_micro_economy"]["avgHeight"]},
        {"key": "negotiated_24h_alley", "label": "Negotiated 24h Alley", "value": metrics["negotiated_24h_alley"]["avgHeight"]},
    ]


def _transform_xy(x, y, bounds, width, height, padding=30):
    minx, miny, maxx, maxy = bounds
    span_x = max(maxx - minx, 1e-9)
    span_y = max(maxy - miny, 1e-9)
    scale = min((width - padding * 2) / span_x, (height - padding * 2) / span_y)
    draw_w = span_x * scale
    draw_h = span_y * scale
    offset_x = (width - draw_w) / 2
    offset_y = (height - draw_h) / 2
    px = offset_x + (x - minx) * scale
    py = height - (offset_y + (y - miny) * scale)
    return round(px, 2), round(py, 2)


def _polygon_to_path(geom, bounds, width, height):
    def ring_to_d(coords):
        pts = [_transform_xy(x, y, bounds, width, height) for x, y in coords]
        if not pts:
            return ""
        start = pts[0]
        body = " ".join(f"L {x} {y}" for x, y in pts[1:])
        return f"M {start[0]} {start[1]} {body} Z"

    if geom.geom_type == "Polygon":
        parts = [ring_to_d(list(geom.exterior.coords))]
        for hole in geom.interiors:
            parts.append(ring_to_d(list(hole.coords)))
        return " ".join(part for part in parts if part)
    if geom.geom_type == "MultiPolygon":
        return " ".join(_polygon_to_path(part, bounds, width, height) for part in geom.geoms)
    return ""


def _line_to_path(geom, bounds, width, height):
    if geom.geom_type == "LineString":
        pts = [_transform_xy(x, y, bounds, width, height) for x, y in geom.coords]
        if not pts:
            return ""
        start = pts[0]
        body = " ".join(f"L {x} {y}" for x, y in pts[1:])
        return f"M {start[0]} {start[1]} {body}"
    if geom.geom_type == "MultiLineString":
        return " ".join(_line_to_path(part, bounds, width, height) for part in geom.geoms)
    return ""


def _points_to_svg(features, bounds, width, height):
    rows = []
    for feature in features:
        geom = shape(feature["geometry"])
        if geom.geom_type == "Point":
            cx, cy = _transform_xy(geom.x, geom.y, bounds, width, height)
            rows.append({"cx": cx, "cy": cy})
    return rows


def _mean_svg_point(rows):
    if not rows:
        return {"cx": 0, "cy": 0}
    return {
        "cx": round(sum(row["cx"] for row in rows) / len(rows), 2),
        "cy": round(sum(row["cy"] for row in rows) / len(rows), 2),
    }


def _scenario_svg_groups(collections, bounds, width, height):
    groups = {}
    for key, collection in collections.items():
        rows = []
        for feature in collection["features"]:
            geom = shape(feature["geometry"])
            if geom.geom_type not in ("Polygon", "MultiPolygon"):
                continue
            rows.append(
                {
                    "path": _polygon_to_path(geom, bounds, width, height),
                    "fill": feature["properties"].get("color", "#b8b4ae"),
                }
            )
        groups[key] = rows
    return groups


def _diff_keys(current_collection, scenario_collection):
    current_map = {}
    for feature in current_collection["features"]:
        geom = shape(feature["geometry"])
        current_map[geom.wkb_hex] = feature
    scenario_map = {}
    for feature in scenario_collection["features"]:
        geom = shape(feature["geometry"])
        scenario_map[geom.wkb_hex] = feature

    changed = set()
    for key in set(current_map) | set(scenario_map):
        left = current_map.get(key)
        right = scenario_map.get(key)
        if left is None or right is None:
            changed.add(key)
            continue
        left_props = left.get("properties", {})
        right_props = right.get("properties", {})
        if (
            left_props.get("sh") != right_props.get("sh")
            or abs(float(left_props.get("height", 0)) - float(right_props.get("height", 0))) > 0.01
            or left_props.get("tags") != right_props.get("tags")
        ):
            changed.add(key)
    return changed


def _scenario_diff_groups(current_collection, scenario_collections, bounds, width, height):
    current_map = {shape(feature["geometry"]).wkb_hex: feature for feature in current_collection["features"]}
    groups = {}
    stats = {}
    for key, collection in scenario_collections.items():
        changed_keys = _diff_keys(current_collection, collection)
        rows = []
        stakeholder_changed = 0
        for feature in collection["features"]:
            geom = shape(feature["geometry"])
            geom_key = geom.wkb_hex
            if geom_key not in changed_keys:
                continue
            props = feature.get("properties", {})
            fill = props.get("color", "#dd6b3d")
            rows.append({"path": _polygon_to_path(geom, bounds, width, height), "fill": fill})
            current_feature = current_map.get(geom_key)
            if current_feature and current_feature.get("properties", {}).get("sh") != props.get("sh"):
                stakeholder_changed += 1
        groups[key] = rows
        stats[key] = {
            "changedCount": len(rows),
            "stakeholderChanged": stakeholder_changed,
            "tagChanged": max(len(rows) - stakeholder_changed, 0),
        }
    return groups, stats


def _stakeholder_matrix(slug):
    regs_map, _regs = ws05.regime_recs(slug, settings.REGIMES)
    keys = ["state", "developer", "resident", "unknown"]
    rows = {}
    for scenario_key, recs in regs_map.items():
        if scenario_key == "current":
            continue
        row = {}
        for key in keys:
            heights = [float(rec["h"]) for rec in recs if rec.get("sh") == key]
            row[key] = round(sum(heights) / max(len(heights), 1), 2) if heights else 0.0
        rows[scenario_key] = row
    return rows


@lru_cache(maxsize=8)
def build_payload(slug=None):
    slug = slug or settings.SLUG
    film = editorial_data_film.build_payload(slug)
    intro = intro_story.build_intro_payload(slug)
    metrics = film["scenarioMetrics"]
    stakeholder_matrix = _stakeholder_matrix(slug)
    bounds = film["meta"]["bounds"]
    svg_width = 920
    svg_height = 720
    district_geom = shape(film["collections"]["district"]["features"][0]["geometry"])
    spine_geom = shape(film["collections"]["touristSpine"]["features"][0]["geometry"])
    relief_points = _points_to_svg(intro["collections"]["reliefNodes"]["features"], bounds, svg_width, svg_height)
    quiet_points = _points_to_svg(intro["collections"]["quietBuildings"]["features"], bounds, svg_width, svg_height)
    spine_mid = spine_geom.interpolate(0.5, normalized=True)
    spine_mid_svg = {
        "cx": _transform_xy(spine_mid.x, spine_mid.y, bounds, svg_width, svg_height)[0],
        "cy": _transform_xy(spine_mid.x, spine_mid.y, bounds, svg_width, svg_height)[1],
    }
    scenario_diff_groups, diff_stats = _scenario_diff_groups(
        film["collections"]["baseline"], film["collections"]["scenarioBuildings"], bounds, svg_width, svg_height
    )
    baseline_cards = [
        {"key": "buildingCount", "label": "Buildings"},
        {"key": "avgHeight", "label": "Avg Height"},
        {"key": "maxHeight", "label": "Max Height"},
        {"key": "slenderness", "label": "Slenderness"},
    ]
    return {
        "meta": {
            "slug": slug,
            "title": "White Film Hybrid",
            "siteName": film["meta"]["siteName"],
            "durationMs": 10000,
            "center": film["meta"]["center"],
            "bounds": film["meta"]["bounds"],
        },
        "beats": BEATS,
        "scenarios": film["scenarios"],
        "stats": film["stats"],
        "scenarioMetrics": metrics,
        "overlayGroups": {
            "metricCards": baseline_cards,
            "scenarioBars": _scenario_bar_rows(metrics),
            "heritageDots": {
                "count": metrics["heritage_micro_economy"]["buildingCount"],
                "footprintArea": metrics["heritage_micro_economy"]["footprintArea"],
            },
            "protocolBand": {
                "reliefNodes": metrics["negotiated_24h_alley"]["reliefNodes"],
                "oneWayAlleys": metrics["negotiated_24h_alley"]["oneWayAlleys"],
                "quietBuildings": metrics["negotiated_24h_alley"]["quietBuildings"],
            },
            "pressureBand": film["overlayGroups"]["pressureBand"],
            "diffStats": diff_stats,
            "stakeholderMatrix": stakeholder_matrix,
        },
        "planSvg": {
            "width": svg_width,
            "height": svg_height,
            "districtPath": _polygon_to_path(district_geom, bounds, svg_width, svg_height),
            "touristSpinePath": _line_to_path(spine_geom, bounds, svg_width, svg_height),
            "baselineBuildings": _scenario_svg_groups({"current": film["collections"]["baseline"]}, bounds, svg_width, svg_height)["current"],
            "scenarioBuildings": _scenario_svg_groups(film["collections"]["scenarioBuildings"], bounds, svg_width, svg_height),
            "scenarioDiffs": scenario_diff_groups,
            "reliefNodes": relief_points,
            "quietPoints": quiet_points,
            "anchors": {
                "spineMid": spine_mid_svg,
                "reliefCenter": _mean_svg_point(relief_points),
                "quietCenter": _mean_svg_point(quiet_points),
            },
        },
        "collections": {
            "baseline": film["collections"]["baseline"],
            "scenarioBuildings": film["collections"]["scenarioBuildings"],
            "touristSpine": film["collections"]["touristSpine"],
            "district": film["collections"]["district"],
            "reliefNodes": intro["collections"]["reliefNodes"],
            "quietBuildings": intro["collections"]["quietBuildings"],
            "quietBuffer": intro["collections"]["quietBuffer"],
        },
    }


HTML_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>White Film Hybrid</title>
  <link href="https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.css" rel="stylesheet" />
  <style>
    :root{
      --bg:#f6f3ed;
      --paper:rgba(255,253,249,.94);
      --ink:#171513;
      --muted:#6d675f;
      --line:#ddd4c9;
      --soft:#eee8df;
      --pale:#dcd5cb;
      --accentA:#f28e24;
      --accentB:#4f78ad;
      --accentC:#be5f38;
      --accentD:#6a9f74;
      --shadow:0 16px 34px rgba(28,21,14,.07);
    }
    *{box-sizing:border-box}
    html,body{margin:0;height:100%;overflow:hidden;background:var(--bg);color:var(--ink);font-family:Georgia,"Times New Roman",serif}
    body{
      background:
        linear-gradient(180deg, rgba(255,255,255,.68), rgba(255,255,255,.68)),
        repeating-linear-gradient(0deg, rgba(0,0,0,.012), rgba(0,0,0,.012) 1px, transparent 1px, transparent 28px),
        var(--bg);
    }
    #map{display:none}
    .grain{position:fixed;inset:0;pointer-events:none;background-image:radial-gradient(rgba(0,0,0,.025) 1px, transparent 1px);background-size:4px 4px;opacity:.18}
    .stage{position:fixed;inset:0;overflow:hidden}
    .map-shell{position:absolute;inset:22px;border-radius:30px;background:rgba(255,252,247,.58);border:1px solid rgba(0,0,0,.05)}
    .map-grid{position:absolute;inset:0;border-radius:30px;overflow:hidden;background:linear-gradient(90deg, rgba(0,0,0,.03) 1px, transparent 1px),linear-gradient(180deg, rgba(0,0,0,.03) 1px, transparent 1px);background-size:94px 94px;opacity:.28}
    .plan-svg{position:absolute;left:50%;top:52%;width:min(88vw,1180px);height:auto;transform:translate(-50%,-50%);filter:drop-shadow(0 32px 36px rgba(35,27,19,.07))}
    .district-fill{fill:#faf6f0;opacity:.96}
    .district-line{fill:none;stroke:#26221d;stroke-width:1.3}
    .baseline-shape{fill:rgba(193,186,177,.46);stroke:rgba(70,61,53,.08);stroke-width:.35}
    .diff-shape{stroke:rgba(58,46,35,.16);stroke-width:.4}
    .spine-line{fill:none;stroke:#f28e24;stroke-width:1.7;stroke-dasharray:7 6;opacity:.42}
    .relief-node{fill:#f28e24;stroke:#fffdfa;stroke-width:1.15;opacity:0}
    .quiet-point{fill:#4f78ad;stroke:#fffdfa;stroke-width:.9;opacity:0}
    .leader{stroke:rgba(30,24,18,.48);stroke-width:1.1;fill:none;opacity:0}
    .halo{fill:none;stroke-width:1.4;opacity:0}
    .halo.relief{stroke:#f28e24}
    .halo.quiet{stroke:#4f78ad}
    .halo.spine{stroke:#be5f38}
    .floating{position:absolute;min-width:220px;max-width:340px;padding:14px 16px;border-radius:22px;background:var(--paper);border:1px solid var(--line);box-shadow:var(--shadow);backdrop-filter:blur(10px);opacity:0;visibility:hidden;transform:translateY(18px) scale(.98);transition:opacity .25s ease, transform .25s ease, visibility .25s ease;pointer-events:none}
    .floating.visible{opacity:1;visibility:visible;transform:translateY(0) scale(1)}
    .hero{left:28px;top:28px;max-width:400px;padding:18px 20px 16px}
    .eyebrow{font:11px/1.2 Arial,sans-serif;letter-spacing:.16em;text-transform:uppercase;color:var(--muted)}
    h1{margin:8px 0 10px;font-size:34px;line-height:1.03;font-weight:600;letter-spacing:-.03em}
    .lede{margin:0;font:14px/1.65 Arial,sans-serif;color:#3e3a35}
    .scenario-ribbon{position:absolute;left:50%;top:30px;transform:translateX(-50%);display:flex;gap:8px}
    .scenario-chip{padding:8px 12px;border-radius:999px;border:1px solid var(--line);background:rgba(255,253,249,.9);font:12px/1 Arial,sans-serif;color:#534d46;opacity:.42;transition:all .22s ease}
    .scenario-chip.active{opacity:1;background:#f9f3e9;border-color:#bfb3a4}
    .operator-strip{position:absolute;left:50%;top:68px;transform:translateX(-50%);display:flex;gap:8px;opacity:0;visibility:hidden;transition:all .24s ease}
    .operator-strip.visible{opacity:1;visibility:visible}
    .operator-chip{padding:6px 11px;border-radius:999px;border:1px solid #dbcdbd;background:rgba(255,250,244,.95);font:11px/1 Arial,sans-serif;letter-spacing:.08em;text-transform:uppercase;color:#6a635c;box-shadow:0 10px 22px rgba(28,21,14,.05)}
    .operator-chip.active{border-color:#c7a57e;background:#fff7ee;color:#3f3428}
    .badge{display:inline-flex;align-items:center;gap:8px;padding:8px 12px;border-radius:999px;border:1px solid var(--line);background:rgba(255,253,249,.92);font:12px/1 Arial,sans-serif;color:#514b44}
    .beat-tag{position:absolute;right:28px;top:30px}
    .section-title{font:11px/1.2 Arial,sans-serif;letter-spacing:.16em;text-transform:uppercase;color:var(--muted)}
    .tiny-note{margin-top:8px;font:12px/1.5 Arial,sans-serif;color:#4a453f}
    .matrix-card{right:32px;top:104px;width:320px}
    .matrix-grid{margin-top:10px;display:grid;grid-template-columns:96px repeat(4,1fr);gap:6px;align-items:stretch}
    .axis-cell{font:10px/1.2 Arial,sans-serif;color:#635e57;display:flex;align-items:center;justify-content:center;text-align:center}
    .axis-cell.row{justify-content:flex-start;padding-left:4px}
    .heat-cell{height:42px;border-radius:12px;display:flex;align-items:center;justify-content:center;font:11px/1.2 Arial,sans-serif;color:#201b17}
    .metrics-card{left:34px;bottom:36px;width:318px}
    .metric-band{margin-top:10px;padding:10px 12px;border-radius:16px;background:#fffdfa;border:1px solid var(--line)}
    .metric-band-head{display:flex;justify-content:space-between;gap:12px;font:10px/1.2 Arial,sans-serif;letter-spacing:.12em;text-transform:uppercase;color:var(--muted)}
    .metric-bar-row{margin-top:9px;display:grid;grid-template-columns:76px 1fr 42px;gap:8px;align-items:center}
    .metric-bar-row b{font:10px/1.2 Arial,sans-serif;color:#5f5952;text-transform:uppercase;letter-spacing:.1em}
    .metric-track{height:10px;border-radius:999px;background:#efe6da;overflow:hidden}
    .metric-fill{height:100%;border-radius:999px;background:linear-gradient(90deg, #e1bf92, #bc7c4f)}
    .metric-value{font:600 12px/1 Arial,sans-serif;color:#4d4640;text-align:right}
    .metrics-grid{margin-top:10px;display:grid;grid-template-columns:repeat(2,1fr);gap:8px}
    .metric-box{padding:10px 11px;border-radius:16px;background:#fffdfa;border:1px solid var(--line)}
    .metric-box strong{display:block;font:600 26px/1 Arial,sans-serif}
    .metric-box span{display:block;margin-top:5px;font:10px/1.2 Arial,sans-serif;letter-spacing:.12em;text-transform:uppercase;color:var(--muted)}
    .diff-card{right:34px;bottom:40px;width:286px}
    .diff-big{display:flex;gap:10px;margin-top:12px}
    .diff-pill{flex:1;padding:12px;border-radius:18px;background:#fffdfa;border:1px solid var(--line);text-align:center}
    .diff-pill strong{display:block;font:600 30px/1 Arial,sans-serif}
    .diff-pill span{display:block;margin-top:6px;font:10px/1.2 Arial,sans-serif;letter-spacing:.12em;text-transform:uppercase;color:var(--muted)}
    .diff-rows{margin-top:12px;display:grid;gap:8px}
    .diff-row{display:grid;grid-template-columns:80px 1fr 40px;gap:8px;align-items:center}
    .diff-row b{font:10px/1.2 Arial,sans-serif;color:#615a53;text-transform:uppercase;letter-spacing:.12em}
    .diff-row .track{height:8px;border-radius:999px;background:#efe6da;overflow:hidden}
    .diff-row .fill{height:100%;border-radius:999px;background:linear-gradient(90deg, #f2b567, #cf6b44)}
    .diff-row .val{font:600 12px/1 Arial,sans-serif;color:#514941;text-align:right}
    .before-card{right:360px;bottom:52px;width:360px}
    .mini-pair{margin-top:10px;display:grid;grid-template-columns:1fr 1fr;gap:10px}
    .mini-map{padding:8px;border-radius:16px;border:1px solid var(--line);background:#fffdfa}
    .mini-map b{display:block;margin-bottom:6px;font:10px/1.2 Arial,sans-serif;letter-spacing:.14em;text-transform:uppercase;color:var(--muted)}
    .mini-svg{width:100%;height:auto;display:block}
    .operator-note{position:absolute;padding:10px 12px;border-radius:18px;background:rgba(255,253,249,.97);border:1px solid var(--line);box-shadow:var(--shadow);max-width:240px;opacity:0;visibility:hidden;transform:translateY(10px);transition:all .22s ease}
    .operator-note.visible{opacity:1;visibility:visible;transform:translateY(0)}
    .operator-note b{display:block;margin-bottom:6px;font:11px/1.2 Arial,sans-serif;letter-spacing:.14em;text-transform:uppercase;color:var(--muted)}
    .operator-note p{margin:0;font:12px/1.5 Arial,sans-serif;color:#3f3a34}
    .note-a{left:12%;top:16%}
    .note-b{right:17%;top:25%}
    .note-c{left:16%;bottom:20%}
    .footer-note{position:absolute;left:50%;bottom:20px;transform:translateX(-50%);padding:10px 16px;border-radius:999px;border:1px solid var(--line);background:rgba(255,253,249,.95);font:12px/1.4 Arial,sans-serif;color:#4c463f}
  </style>
</head>
<body>
  <div id="map"></div>
  <div class="grain"></div>
  <div class="stage">
    <div class="map-shell">
      <div class="map-grid"></div>
      <svg class="plan-svg" id="planSvg" viewBox="0 0 920 720" preserveAspectRatio="xMidYMid meet">
        <defs>
          <marker id="arrowhead" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto">
            <polygon points="0 0, 6 3, 0 6" fill="rgba(33,28,23,.55)"></polygon>
          </marker>
        </defs>
        <path class="district-fill" id="districtFill"></path>
        <path class="district-line" id="districtLine"></path>
        <g id="baselineLayer"></g>
        <path class="spine-line" id="spineLine"></path>
        <g id="diffLayer"></g>
        <g id="operatorLayer"></g>
        <g id="reliefLayer"></g>
        <g id="quietLayer"></g>
      </svg>
    </div>
    <div class="floating hero visible" id="heroCard">
      <div class="eyebrow">Urban Reading to Urban Rewriting</div>
      <h1>One district, four redistributions of urban life.</h1>
      <p class="lede" id="lede"></p>
    </div>
    <div class="scenario-ribbon" id="scenarioStrip"></div>
    <div class="operator-strip" id="operatorStrip"></div>
    <div class="badge beat-tag" id="beatTitle">Site and Regimes</div>
    <div class="floating matrix-card" id="heatmapCard">
      <div class="section-title">Policy Heatmap</div>
      <div class="tiny-note">Scenario Metrics through stakeholder response.</div>
      <div class="matrix-grid" id="matrixGrid"></div>
    </div>
    <div class="floating metrics-card" id="metricsCard">
      <div class="section-title">Scenario Metrics</div>
      <div class="metric-band">
        <div class="metric-band-head"><span>Scenario Profile</span><span id="metricBandLabel">Active Regime</span></div>
        <div id="metricBars"></div>
      </div>
      <div class="metrics-grid" id="metricGrid"></div>
    </div>
    <div class="floating diff-card" id="diffCard">
      <div class="section-title">Operator Diff</div>
      <div class="tiny-note" id="diffCaption">Changed buildings and stakeholder shifts under the active regime.</div>
      <div class="diff-big">
        <div class="diff-pill"><strong id="changedCount">0</strong><span>Changed</span></div>
        <div class="diff-pill"><strong id="stakeholderChanged">0</strong><span>Stakeholder</span></div>
        <div class="diff-pill"><strong id="tagChanged">0</strong><span>Tags</span></div>
      </div>
      <div class="diff-rows" id="diffRows"></div>
    </div>
    <div class="floating before-card" id="beforeCard">
      <div class="section-title">Before / After</div>
      <div class="mini-pair">
        <div class="mini-map">
          <b>Before</b>
          <svg class="mini-svg" id="miniBefore" viewBox="0 0 220 160" preserveAspectRatio="xMidYMid meet"></svg>
        </div>
        <div class="mini-map">
          <b>After</b>
          <svg class="mini-svg" id="miniAfter" viewBox="0 0 220 160" preserveAspectRatio="xMidYMid meet"></svg>
        </div>
      </div>
    </div>
    <div class="operator-note note-a" id="ann1"><b>Crowd Valve</b><p>Main spine pressure is compressed and redistributed into local relief pockets.</p></div>
    <div class="operator-note note-b" id="ann2"><b>Operator Logic</b><p>Floating cards enter only when evidence needs to be read; the map stays dominant.</p></div>
    <div class="operator-note note-c" id="ann3"><b>Night Reversion</b><p>Quiet buildings are pinned back onto the map as a timed residential claim.</p></div>
    <div class="footer-note" id="footerNote">Diff-map view: only changed buildings stay loud.</div>
  </div>
  <script src="https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.js"></script>
  <script>
    const PAYLOAD = __PAYLOAD__;
    const SCENARIO_ORDER = ["tourism_capture","everyday_life_first","heritage_micro_economy","negotiated_24h_alley"];
    const OP_LABELS = {
      freeze: "Freeze",
      split_to_towers: "Split Towers",
      slim: "Slim",
      densify: "Densify",
      open_ground: "Open Ground",
      level: "Level",
      freeze_tags: "Freeze Tags",
      micro_lease: "Micro Lease",
      frontage_quota: "Frontage Quota",
      crowd_valve: "Crowd Valve",
      night_reversion: "Night Reversion",
      quiet_edge: "Quiet Edge",
      time_share: "Time Share",
    };
    const lede = document.getElementById("lede");
    const heroCard = document.getElementById("heroCard");
    const beatTitle = document.getElementById("beatTitle");
    const metricGrid = document.getElementById("metricGrid");
    const metricBars = document.getElementById("metricBars");
    const metricBandLabel = document.getElementById("metricBandLabel");
    const scenarioStrip = document.getElementById("scenarioStrip");
    const operatorStrip = document.getElementById("operatorStrip");
    const matrixGrid = document.getElementById("matrixGrid");
    const footerNote = document.getElementById("footerNote");
    const heatmapCard = document.getElementById("heatmapCard");
    const metricsCard = document.getElementById("metricsCard");
    const diffCard = document.getElementById("diffCard");
    const beforeCard = document.getElementById("beforeCard");
    const changedCount = document.getElementById("changedCount");
    const stakeholderChanged = document.getElementById("stakeholderChanged");
    const tagChanged = document.getElementById("tagChanged");
    const diffCaption = document.getElementById("diffCaption");
    const diffRows = document.getElementById("diffRows");
    const annotations = ["ann1","ann2","ann3"].map((id) => document.getElementById(id));
    const districtFill = document.getElementById("districtFill");
    const districtLine = document.getElementById("districtLine");
    const baselineLayer = document.getElementById("baselineLayer");
    const diffLayer = document.getElementById("diffLayer");
    const spineLine = document.getElementById("spineLine");
    const operatorLayer = document.getElementById("operatorLayer");
    const reliefLayer = document.getElementById("reliefLayer");
    const quietLayer = document.getElementById("quietLayer");
    const miniBefore = document.getElementById("miniBefore");
    const miniAfter = document.getElementById("miniAfter");

    function scenarioByKey(key) { return PAYLOAD.scenarios.find((item) => item.key === key); }

    PAYLOAD.scenarios.forEach((scenario) => {
      const chip = document.createElement("div");
      chip.className = "scenario-chip";
      chip.dataset.key = scenario.key;
      chip.textContent = scenario.label;
      scenarioStrip.appendChild(chip);
    });

    districtFill.setAttribute("d", PAYLOAD.planSvg.districtPath);
    districtLine.setAttribute("d", PAYLOAD.planSvg.districtPath);
    spineLine.setAttribute("d", PAYLOAD.planSvg.touristSpinePath);
    baselineLayer.innerHTML = PAYLOAD.planSvg.baselineBuildings.map((row) => `<path class="baseline-shape" d="${row.path}"></path>`).join("");

    function scalePath(path, sx, sy, tx, ty) {
      return path.replace(/([ML]) ([\\d.-]+) ([\\d.-]+)/g, (_, cmd, x, y) => `${cmd} ${Number(x) * sx + tx} ${Number(y) * sy + ty}`);
    }

    function beatForElapsed(elapsed) {
      const beats = PAYLOAD.beats;
      for (const beat of beats) if (elapsed >= beat.start && elapsed < beat.end) return beat;
      if (elapsed < 3000) return beats[0];
      if (elapsed < 7000) return beats[1];
      return beats[2];
    }

    function scenarioKeyForElapsed(elapsed) {
      if (elapsed < 500) return "tourism_capture";
      if (elapsed < 1000) return "everyday_life_first";
      if (elapsed < 1500) return "heritage_micro_economy";
      if (elapsed < 2000) return "negotiated_24h_alley";
      if (elapsed < 4000) return "tourism_capture";
      if (elapsed < 5000) return "everyday_life_first";
      if (elapsed < 6000) return "heritage_micro_economy";
      return "negotiated_24h_alley";
    }

    function setScenarioActive(key) {
      document.querySelectorAll(".scenario-chip").forEach((node) => node.classList.toggle("active", node.dataset.key === key));
    }

    function renderOperatorStrip(key, elapsed) {
      const scenario = scenarioByKey(key);
      const ops = (scenario.ops || []).map((op) => OP_LABELS[op] || op.replace(/_/g, " "));
      operatorStrip.innerHTML = ops.map((label, index) => `<div class="operator-chip ${elapsed >= 7000 || index === ops.length - 1 ? "active" : ""}">${label}</div>`).join("");
      operatorStrip.classList.toggle("visible", elapsed >= 3000);
    }

    function renderPlanScenario(key) {
      const rows = PAYLOAD.planSvg.scenarioDiffs[key] || [];
      diffLayer.innerHTML = rows.map((row) => `<path class="diff-shape" d="${row.path}" fill="${row.fill}"></path>`).join("");
    }

    function renderMiniMaps(key) {
      const sx = 0.22, sy = 0.22, tx = 8, ty = 4;
      miniBefore.innerHTML = [`<path d="${scalePath(PAYLOAD.planSvg.districtPath, sx, sy, tx, ty)}" fill="#faf6f0" stroke="#9d9488" stroke-width="1"></path>`, ...PAYLOAD.planSvg.baselineBuildings.map((row) => `<path d="${scalePath(row.path, sx, sy, tx, ty)}" fill="rgba(193,186,177,.58)" stroke="rgba(60,50,42,.08)" stroke-width=".3"></path>`)].join("");
      miniAfter.innerHTML = [`<path d="${scalePath(PAYLOAD.planSvg.districtPath, sx, sy, tx, ty)}" fill="#faf6f0" stroke="#9d9488" stroke-width="1"></path>`, ...PAYLOAD.planSvg.baselineBuildings.map((row) => `<path d="${scalePath(row.path, sx, sy, tx, ty)}" fill="rgba(223,217,208,.55)" stroke="rgba(60,50,42,.06)" stroke-width=".3"></path>`), ...(PAYLOAD.planSvg.scenarioDiffs[key] || []).map((row) => `<path d="${scalePath(row.path, sx, sy, tx, ty)}" fill="${row.fill}" stroke="rgba(60,50,42,.12)" stroke-width=".3"></path>`)].join("");
    }

    function renderPointGroups(key, operatorVisible) {
      const reliefOpacity = operatorVisible ? 0.92 : 0.0;
      const quietOpacity = key === "negotiated_24h_alley" ? 0.72 : 0.0;
      reliefLayer.innerHTML = PAYLOAD.planSvg.reliefNodes.map((row) => `<circle class="relief-node" cx="${row.cx}" cy="${row.cy}" r="4.6" style="opacity:${reliefOpacity}"></circle>`).join("");
      quietLayer.innerHTML = PAYLOAD.planSvg.quietPoints.map((row) => `<circle class="quiet-point" cx="${row.cx}" cy="${row.cy}" r="2.5" style="opacity:${quietOpacity}"></circle>`).join("");
    }

    function renderMetricCards(key) {
      const metrics = PAYLOAD.scenarioMetrics[key];
      const bandRows = [
        { label: "Avg H", value: metrics.avgHeight, max: 40 },
        { label: "Max H", value: metrics.maxHeight, max: 240 },
        { label: "Footprint", value: metrics.footprintArea, max: 180000 },
      ];
      metricBandLabel.textContent = scenarioByKey(key).label;
      metricBars.innerHTML = bandRows.map((row) => {
        const width = Math.max(8, Math.min(100, row.value / row.max * 100));
        const display = row.value >= 100 ? row.value.toFixed(0) : row.value.toFixed(1).replace(/\\.0$/, "");
        return `<div class="metric-bar-row"><b>${row.label}</b><div class="metric-track"><div class="metric-fill" style="width:${width}%"></div></div><div class="metric-value">${display}</div></div>`;
      }).join("");
      metricGrid.innerHTML = PAYLOAD.overlayGroups.metricCards.map((item) => {
        let value = metrics[item.key];
        if (typeof value === "number") value = Number(value).toFixed(item.key === "slenderness" ? 3 : 1).replace(/\\.0$/, "");
        return `<div class="metric-box"><strong>${value}</strong><span>${item.label}</span></div>`;
      }).join("");
    }

    function heatColor(value, min, max) {
      const t = (value - min) / Math.max(max - min, 1e-6);
      const hue = 210 - t * 170;
      const light = 92 - t * 28;
      return `hsl(${hue}, 58%, ${light}%)`;
    }

    function renderHeatmap() {
      const cols = [["state", "State"], ["developer", "Capital"], ["resident", "Residents"], ["unknown", "Unknown"]];
      const values = SCENARIO_ORDER.flatMap((scenarioKey) => cols.map((col) => PAYLOAD.overlayGroups.stakeholderMatrix[scenarioKey][col[0]]));
      const min = Math.min(...values), max = Math.max(...values);
      matrixGrid.innerHTML = [`<div class="axis-cell"></div>`, ...cols.map((col) => `<div class="axis-cell">${col[1]}</div>`), ...SCENARIO_ORDER.flatMap((scenarioKey) => {
        const label = scenarioByKey(scenarioKey).label.replace("Negotiated 24h Alley", "24h Alley");
        return [`<div class="axis-cell row">${label}</div>`, ...cols.map((col) => {
          const value = PAYLOAD.overlayGroups.stakeholderMatrix[scenarioKey][col[0]];
          return `<div class="heat-cell" style="background:${heatColor(value, min, max)}">${value ? value.toFixed(1) : "-"}</div>`;
        })];
      })].join("");
    }

    function renderDiffCard(key) {
      const stats = PAYLOAD.overlayGroups.diffStats[key];
      changedCount.textContent = stats.changedCount;
      stakeholderChanged.textContent = stats.stakeholderChanged;
      tagChanged.textContent = stats.tagChanged;
      diffCaption.textContent = `${scenarioByKey(key).label}: changed-only map with local evidence.`;
      const rows = [
        { label: "Changed", value: stats.changedCount, max: stats.changedCount },
        { label: "Stakeholder", value: stats.stakeholderChanged, max: stats.changedCount },
        { label: "Tag", value: stats.tagChanged, max: stats.changedCount },
      ];
      diffRows.innerHTML = rows.map((row) => {
        const width = Math.max(4, row.value / Math.max(row.max, 1) * 100);
        return `<div class="diff-row"><b>${row.label}</b><div class="track"><div class="fill" style="width:${width}%"></div></div><div class="val">${row.value}</div></div>`;
      }).join("");
    }

    function renderOperatorLayer(elapsed) {
      const visible = elapsed >= 7000;
      annotations.forEach((node) => node.classList.toggle("visible", visible));
      spineLine.style.opacity = visible ? "0.84" : "0.36";
      if (!visible) { operatorLayer.innerHTML = ""; return; }
      const anchors = PAYLOAD.planSvg.anchors;
      operatorLayer.innerHTML = `
        <line class="leader" x1="150" y1="118" x2="${anchors.spineMid.cx}" y2="${anchors.spineMid.cy}" marker-end="url(#arrowhead)" style="opacity:1"></line>
        <line class="leader" x1="790" y1="148" x2="${anchors.reliefCenter.cx}" y2="${anchors.reliefCenter.cy}" marker-end="url(#arrowhead)" style="opacity:1"></line>
        <line class="leader" x1="170" y1="588" x2="${anchors.quietCenter.cx}" y2="${anchors.quietCenter.cy}" marker-end="url(#arrowhead)" style="opacity:1"></line>
        <circle class="halo spine" cx="${anchors.spineMid.cx}" cy="${anchors.spineMid.cy}" r="18" style="opacity:1"></circle>
        <circle class="halo relief" cx="${anchors.reliefCenter.cx}" cy="${anchors.reliefCenter.cy}" r="16" style="opacity:1"></circle>
        <circle class="halo quiet" cx="${anchors.quietCenter.cx}" cy="${anchors.quietCenter.cy}" r="18" style="opacity:1"></circle>
      `;
    }

    function cardVis(card, show) { card.classList.toggle("visible", show); }

    function renderAtElapsed(elapsedMs) {
      const duration = PAYLOAD.meta.durationMs;
      const elapsed = ((elapsedMs % duration) + duration) % duration;
      const beat = beatForElapsed(elapsed);
      const key = scenarioKeyForElapsed(elapsed);
      const scenario = scenarioByKey(key);
      lede.textContent = beat.lede;
      beatTitle.textContent = beat.label;
      footerNote.textContent = scenario.caption;
      setScenarioActive(key);
      renderOperatorStrip(key, elapsed);
      renderPlanScenario(key);
      renderMetricCards(key);
      renderHeatmap();
      renderDiffCard(key);
      renderMiniMaps(key);
      renderPointGroups(key, elapsed >= 7000);
      renderOperatorLayer(elapsed);
      cardVis(heroCard, elapsed < 2600);
      cardVis(heatmapCard, elapsed >= 3000 && elapsed < 5400);
      cardVis(metricsCard, elapsed >= 3600 && elapsed < 7200);
      cardVis(diffCard, elapsed >= 4700 && elapsed < 8600);
      cardVis(beforeCard, elapsed >= 7200);
      districtFill.style.opacity = beat.key === "site_intro" ? "0.82" : "0.94";
      return true;
    }

    let manualElapsed = null;
    window.__codexRenderAt = (ms) => {
      manualElapsed = ms;
      return renderAtElapsed(ms);
    };
    let loopStart = null;
    function frame(ts) {
      if (loopStart === null) loopStart = ts;
      if (manualElapsed !== null) {
        requestAnimationFrame(frame);
        return;
      }
      renderAtElapsed(ts - loopStart);
      requestAnimationFrame(frame);
    }
    requestAnimationFrame(frame);
  </script>
</body>
</html>
"""


def build(slug=None):
    slug = slug or settings.SLUG
    payload = build_payload(slug)
    out_path = output_path(slug)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    html = HTML_TEMPLATE.replace("__PAYLOAD__", json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
    out_path.write_text(html, encoding="utf-8")
    return out_path
