import json
from functools import lru_cache
from pathlib import Path

from shapely.ops import unary_union

import intro_story
import settings
import ws05


ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "out"


BEATS = [
    {
        "key": "baseline",
        "label": "Baseline Ledger",
        "start": 0,
        "end": 2300,
        "lede": "The district is first read as evidence: buildings, actors, heights, and a single shared ground condition.",
        "scenario": "tourism_capture",
    },
    {
        "key": "pressure_shift",
        "label": "Pressure Shift",
        "start": 2300,
        "end": 4900,
        "lede": "Commercial pressure thickens along the tourist spine, then releases ground back to everyday circulation.",
        "scenario": "everyday_life_first",
    },
    {
        "key": "fine_grain_survival",
        "label": "Fine-Grain Survival",
        "start": 4900,
        "end": 7500,
        "lede": "Heritage persists not as a monument, but as a fine-grain field of smaller productive fragments.",
        "scenario": "heritage_micro_economy",
    },
    {
        "key": "timed_negotiation",
        "label": "Timed Negotiation",
        "start": 7500,
        "end": 10000,
        "lede": "The alley becomes a protocol that shifts by hour: crowd release by day, resident quiet by night.",
        "scenario": "negotiated_24h_alley",
    },
]


def _scenario_metric_row(recs):
    heights = [float(rec["h"]) for rec in recs]
    areas = [float(rec.get("area", rec["geom"].area)) for rec in recs]
    building_count = len(recs)
    avg_height = sum(heights) / max(building_count, 1)
    avg_area = sum(areas) / max(building_count, 1)
    slenderness = avg_height / max(avg_area ** 0.5, 1e-6)
    union = unary_union([rec["geom"] for rec in recs])
    footprint_area = float(union.area) if not union.is_empty else 0.0
    return {
        "buildingCount": building_count,
        "avgHeight": round(avg_height, 2),
        "maxHeight": round(max(heights), 2) if heights else 0.0,
        "slenderness": round(slenderness, 3),
        "footprintArea": round(footprint_area, 1),
    }


@lru_cache(maxsize=8)
def _scenario_metrics(slug):
    regs_map, _regs = ws05.regime_recs(slug, settings.REGIMES)
    metrics = {}
    collections = {}
    for key, recs in regs_map.items():
        metrics[key] = _scenario_metric_row(recs)
        collections[key] = intro_story._collection_from_recs(recs)

    current_recs, _df = ws05.load_recs(slug)
    operator_data = intro_story._operator_metrics(current_recs)
    negotiated = metrics.get("negotiated_24h_alley", {})
    negotiated["reliefNodes"] = sum("relief_node" in rec.get("tags", []) for rec in operator_data["valved"])
    negotiated["oneWayAlleys"] = sum("one_way_alley" in rec.get("tags", []) for rec in operator_data["valved"])
    negotiated["quietBuildings"] = len(operator_data["quiet"])
    metrics["negotiated_24h_alley"] = negotiated

    return metrics, collections, operator_data


@lru_cache(maxsize=8)
def _site_payload(slug):
    site = intro_story._site_meta(slug)
    current_recs, _df = ws05.load_recs(slug)
    current_tagged = intro_story._operator_metrics(current_recs)["tagged"]
    current_gdf = intro_story._to_gdf(current_tagged)
    district_outline = unary_union([rec["geom"] for rec in current_recs]).convex_hull.buffer(20)
    tourist_spine = intro_story._build_spine(current_tagged)
    return {
        "site": site,
        "currentRecs": current_recs,
        "currentTagged": current_tagged,
        "currentGdf": current_gdf,
        "district": intro_story._polygon_feature(district_outline),
        "touristSpine": intro_story._line_feature(tourist_spine),
    }


@lru_cache(maxsize=8)
def build_payload(slug=None):
    slug = slug or settings.SLUG
    site_data = _site_payload(slug)
    metrics, scenario_collections, operator_data = _scenario_metrics(slug)

    stakeholder_counts = {}
    for sh in sorted({rec["sh"] for rec in site_data["currentTagged"]}):
        stakeholder_counts[sh] = sum(rec["sh"] == sh for rec in site_data["currentTagged"])

    baseline_metric_cards = [
        {"label": "Buildings", "value": metrics["current"]["buildingCount"]},
        {"label": "Avg Height", "value": metrics["current"]["avgHeight"]},
        {"label": "Stakeholder Types", "value": len(stakeholder_counts)},
    ]
    overlay_groups = {
        "baselineNumbers": baseline_metric_cards,
        "pressureBand": {
            "from": metrics["tourism_capture"]["slenderness"],
            "to": metrics["everyday_life_first"]["slenderness"],
            "tourismHeight": metrics["tourism_capture"]["avgHeight"],
            "everydayHeight": metrics["everyday_life_first"]["avgHeight"],
        },
        "heritageParticles": {
            "count": metrics["heritage_micro_economy"]["buildingCount"],
            "footprintArea": metrics["heritage_micro_economy"]["footprintArea"],
        },
        "dayNightBand": {
            "reliefNodes": metrics["negotiated_24h_alley"]["reliefNodes"],
            "oneWayAlleys": metrics["negotiated_24h_alley"]["oneWayAlleys"],
            "quietBuildings": metrics["negotiated_24h_alley"]["quietBuildings"],
        },
    }

    quiet_points = [{"geometry": rec["geom"].centroid, "weight": round(float(rec["h"]), 1)} for rec in operator_data["quiet"][:80]]

    return {
        "meta": {
            "slug": slug,
            "title": "Editorial Data Film",
            "siteName": site_data["site"].get("name", slug),
            "durationMs": 10000,
            "center": list(site_data["currentGdf"].geometry.union_all().centroid.coords[0]),
            "bounds": site_data["site"].get("bounds_lonlat"),
        },
        "beats": BEATS,
        "scenarios": [
            {
                "key": key,
                "label": intro_story.SCENARIO_COPY.get(key, {}).get("label", key),
                "caption": intro_story.SCENARIO_COPY.get(key, {}).get("caption", ""),
                "accent": intro_story.SCENARIO_COPY.get(key, {}).get("accent", "#9fb3c8"),
                "ops": [step["op"] for step in ws05.regime_recs(slug, settings.REGIMES)[1].get(key, {}).get("steps", [])],
            }
            for key in settings.REGIMES
            if key != "current"
        ],
        "scenarioMetrics": {key: value for key, value in metrics.items() if key != "current"},
        "stats": {
            "buildingCount": metrics["current"]["buildingCount"],
            "avgHeight": metrics["current"]["avgHeight"],
            "stakeholderCounts": stakeholder_counts,
        },
        "overlayGroups": overlay_groups,
        "collections": {
            "baseline": intro_story._collection_from_recs(site_data["currentTagged"]),
            "district": site_data["district"],
            "touristSpine": site_data["touristSpine"],
            "quietBuildings": intro_story._point_collection(quiet_points, "weight"),
            "scenarioBuildings": scenario_collections,
        },
    }


def frame_output_dir(slug, duration_s=10, fps=24):
    return OUT / slug / f"editorial_data_film_frames_{duration_s}s_{fps}fps"


def video_output_path(slug, duration_s=10):
    return OUT / slug / f"editorial_data_film_{duration_s}s.mp4"


HTML_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Editorial Data Film</title>
  <link href="https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.css" rel="stylesheet" />
  <style>
    :root{
      --bg:#04070d;
      --panel:rgba(8,12,20,.82);
      --line:rgba(255,255,255,.12);
      --soft:rgba(224,233,245,.76);
      --soft2:rgba(224,233,245,.5);
      --white:#f5f8fc;
      --hot:#ff6b3d;
      --cool:#6ce0d6;
      --gold:#f2c166;
      --violet:#8d9cff;
    }
    *{box-sizing:border-box}
    html,body{margin:0;height:100%;overflow:hidden;background:var(--bg);color:var(--white);font-family:"Segoe UI","Helvetica Neue",Arial,sans-serif}
    #map{position:fixed;inset:0}
    .grain,.vignette,.scan{position:fixed;inset:0;pointer-events:none}
    .grain{background-image:radial-gradient(rgba(255,255,255,.03) 1px, transparent 1px);background-size:3px 3px;mix-blend-mode:soft-light;opacity:.18}
    .vignette{background:radial-gradient(circle at 50% 48%, transparent 32%, rgba(0,0,0,.64) 100%)}
    .scan{background:linear-gradient(180deg, rgba(255,255,255,.03), transparent 18%, transparent 82%, rgba(255,255,255,.02))}
    .hud{position:fixed;inset:0;padding:24px;display:grid;grid-template-columns:400px 1fr 390px;gap:18px;pointer-events:none}
    .panel{border:1px solid var(--line);border-radius:26px;background:var(--panel);backdrop-filter:blur(18px);box-shadow:0 16px 48px rgba(0,0,0,.34)}
    .left{padding:22px;align-self:start}
    .right{padding:18px;align-self:start}
    .center{position:relative}
    .eyebrow{font-size:11px;letter-spacing:.18em;text-transform:uppercase;color:rgba(255,255,255,.56)}
    h1{margin:10px 0 12px;font-size:34px;line-height:1.06;font-weight:700}
    .lede{margin:0;font-size:14px;line-height:1.65;color:var(--soft)}
    .numbers{margin-top:18px;display:grid;grid-template-columns:repeat(3,1fr);gap:10px}
    .number-card{padding:12px;border-radius:18px;background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.06)}
    .number-card strong{display:block;font-size:26px;line-height:1}
    .number-card span{display:block;margin-top:6px;font-size:11px;letter-spacing:.12em;text-transform:uppercase;color:rgba(255,255,255,.54)}
    .figure{position:absolute;left:50%;top:50%;width:min(44vw,640px);height:min(44vw,640px);transform:translate(-50%,-52%);display:flex;align-items:center;justify-content:center;pointer-events:none}
    .ring{position:absolute;border-radius:50%;border:1px solid rgba(255,255,255,.08)}
    .ring.r1{width:100%;height:100%}
    .ring.r2{width:78%;height:78%}
    .ring.r3{width:54%;height:54%}
    .crosshair{position:absolute;inset:50% auto auto 50%;width:72%;height:1px;background:linear-gradient(90deg,transparent,rgba(255,255,255,.24),transparent);transform:translate(-50%,-50%)}
    .crosshair.v{width:1px;height:72%}
    .beat-mark{position:absolute;left:50%;top:50%;transform:translate(-50%,-50%);text-align:center}
    .beat-mark .kicker{font-size:12px;letter-spacing:.22em;text-transform:uppercase;color:rgba(255,255,255,.5)}
    .beat-mark .title{margin-top:10px;font-size:42px;line-height:1.02;font-weight:700;text-shadow:0 6px 28px rgba(0,0,0,.45)}
    .scenario-stack{display:flex;flex-direction:column;gap:10px;pointer-events:auto}
    .scenario-card{padding:14px 16px;border-radius:18px;border:1px solid rgba(255,255,255,.07);background:rgba(255,255,255,.035);opacity:.38;transition:all .28s ease;cursor:pointer}
    .scenario-card.active{opacity:1;transform:translateX(-8px);border-color:rgba(255,255,255,.22);background:rgba(255,255,255,.08)}
    .scenario-card h3{margin:0;font-size:15px;display:flex;align-items:center;gap:8px}
    .scenario-card p{margin:8px 0 0;font-size:12px;line-height:1.55;color:var(--soft)}
    .dot{width:10px;height:10px;border-radius:50%}
    .metrics-film{margin-top:14px;padding:14px;border-radius:18px;border:1px solid rgba(255,255,255,.07);background:rgba(255,255,255,.03)}
    .metrics-film .label{font-size:11px;letter-spacing:.16em;text-transform:uppercase;color:rgba(255,255,255,.5)}
    .pressure-track{position:relative;height:11px;border-radius:999px;background:rgba(255,255,255,.08);overflow:hidden;margin-top:12px}
    .pressure-fill{position:absolute;left:0;top:0;bottom:0;width:50%;border-radius:999px;background:linear-gradient(90deg,var(--cool),var(--hot))}
    .metric-line{display:flex;justify-content:space-between;margin-top:10px;font-size:12px;color:var(--soft)}
    .particle-field{position:relative;height:110px;margin-top:12px;border-radius:16px;background:rgba(255,255,255,.03);overflow:hidden}
    .particle{position:absolute;width:6px;height:6px;border-radius:50%;background:var(--gold);box-shadow:0 0 12px rgba(242,193,102,.6)}
    .day-night{position:relative;height:74px;margin-top:12px;border-radius:18px;overflow:hidden;background:linear-gradient(90deg, rgba(255,107,61,.12), rgba(108,224,214,.12))}
    .day-night::before{content:"";position:absolute;inset:0;background:linear-gradient(90deg, rgba(255,107,61,.32), rgba(108,224,214,.32));transform-origin:left center;transform:scaleX(.35)}
    .day-night-grid{position:absolute;inset:0;display:grid;grid-template-columns:repeat(3,1fr);place-items:center;font-size:12px;color:var(--white)}
    .bottom-strip{position:fixed;left:24px;right:24px;bottom:18px;padding:14px 16px 16px;border-radius:20px;border:1px solid var(--line);background:rgba(7,12,20,.88);display:grid;grid-template-columns:1fr 330px;gap:14px}
    .timeline-label{display:flex;justify-content:space-between;font-size:12px;color:rgba(255,255,255,.72)}
    .timeline{height:6px;border-radius:999px;background:rgba(255,255,255,.08);overflow:hidden;margin-top:8px}
    .timeline > div{height:100%;width:0;background:linear-gradient(90deg,var(--cool),#c6f7f1,var(--hot))}
    .capsules{display:flex;gap:8px;overflow:hidden;margin-top:12px;white-space:nowrap}
    .capsule{padding:7px 11px;border-radius:999px;border:1px solid rgba(255,255,255,.08);background:rgba(255,255,255,.04);font-size:11px;opacity:.42;transition:all .25s ease}
    .capsule.active{opacity:1;background:rgba(255,255,255,.1);border-color:rgba(255,255,255,.2)}
    .caption-note{align-self:end;font-size:12px;line-height:1.6;color:var(--soft)}
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
      <h1>One district, four redistributions of urban life.</h1>
      <p class="lede" id="lede"></p>
      <div class="numbers" id="baselineNumbers"></div>
    </div>

    <div class="center">
      <div class="figure">
        <div class="ring r1"></div>
        <div class="ring r2"></div>
        <div class="ring r3"></div>
        <div class="crosshair"></div>
        <div class="crosshair v"></div>
        <div class="beat-mark">
          <div class="kicker" id="beatKicker">Baseline Ledger</div>
          <div class="title" id="beatTitle">Read the district as evidence.</div>
        </div>
      </div>
    </div>

    <div class="panel right">
      <div class="eyebrow">Scenario Regimes</div>
      <div class="scenario-stack" id="scenarioStack"></div>
      <div class="metrics-film">
        <div class="label" id="overlayLabel">Baseline Numbers</div>
        <div id="overlayBody"></div>
      </div>
    </div>
  </div>

  <div class="bottom-strip">
    <div>
      <div class="timeline-label"><span id="stageName">Baseline Ledger</span><span>10s editorial film</span></div>
      <div class="timeline"><div id="timelineFill"></div></div>
      <div class="capsules" id="capsules"></div>
    </div>
    <div class="caption-note" id="noteText">The map, the operators, and the metrics are synchronized into one timed spatial narrative.</div>
  </div>

  <script src="https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.js"></script>
  <script>
    const PAYLOAD = __PAYLOAD__;
    const EXPORT_MS = new URLSearchParams(window.location.search).get("frameMs");
    const EXPORT_MODE = new URLSearchParams(window.location.search).get("export") === "1";
    const SCENARIO_ORDER = ["tourism_capture", "everyday_life_first", "heritage_micro_economy", "negotiated_24h_alley"];

    const beatKicker = document.getElementById("beatKicker");
    const beatTitle = document.getElementById("beatTitle");
    const lede = document.getElementById("lede");
    const stageName = document.getElementById("stageName");
    const timelineFill = document.getElementById("timelineFill");
    const overlayLabel = document.getElementById("overlayLabel");
    const overlayBody = document.getElementById("overlayBody");
    const noteText = document.getElementById("noteText");

    const baselineNumbers = document.getElementById("baselineNumbers");
    PAYLOAD.overlayGroups.baselineNumbers.forEach((item) => {
      const div = document.createElement("div");
      div.className = "number-card";
      div.innerHTML = `<strong>${item.value}</strong><span>${item.label}</span>`;
      baselineNumbers.appendChild(div);
    });

    const capsules = document.getElementById("capsules");
    SCENARIO_ORDER.forEach((key) => {
      const scenario = PAYLOAD.scenarios.find((item) => item.key === key);
      const div = document.createElement("div");
      div.className = "capsule";
      div.dataset.key = key;
      div.textContent = scenario ? scenario.label : key;
      capsules.appendChild(div);
    });

    const scenarioStack = document.getElementById("scenarioStack");
    PAYLOAD.scenarios.forEach((scenario, index) => {
      const div = document.createElement("div");
      div.className = "scenario-card" + (index === 0 ? " active" : "");
      div.dataset.key = scenario.key;
      div.innerHTML = `<h3><span class="dot" style="background:${scenario.accent}"></span>${scenario.label}</h3><p>${scenario.caption}</p>`;
      div.addEventListener("click", () => {
        const beat = PAYLOAD.beats.find((item) => item.scenario === scenario.key) || PAYLOAD.beats[0];
        renderFilmFrame(beat.start + 20);
      });
      scenarioStack.appendChild(div);
    });

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
      zoom: 14.18,
      pitch: 52,
      bearing: -18,
      antialias: true
    });

    let loopStart = null;

    function activeScenarioKey(elapsed) {
      const beat = PAYLOAD.beats.find((item) => elapsed >= item.start && elapsed < item.end) || PAYLOAD.beats[PAYLOAD.beats.length - 1];
      return beat.scenario;
    }

    function setScenarioActive(key) {
      document.querySelectorAll(".scenario-card").forEach((el) => el.classList.toggle("active", el.dataset.key === key));
      document.querySelectorAll(".capsule").forEach((el) => el.classList.toggle("active", el.dataset.key === key));
    }

    function renderOverlay(key, beatProgress) {
      if (key === "tourism_capture" || key === "everyday_life_first") {
        const pressure = PAYLOAD.overlayGroups.pressureBand;
        const width = 42 + beatProgress * 46;
        overlayLabel.textContent = "Pressure Band";
        overlayBody.innerHTML = `
          <div class="pressure-track"><div class="pressure-fill" style="width:${width}%"></div></div>
          <div class="metric-line"><span>Tourism slenderness</span><span>${pressure.from}</span></div>
          <div class="metric-line"><span>Everyday slenderness</span><span>${pressure.to}</span></div>
          <div class="metric-line"><span>Height swing</span><span>${pressure.tourismHeight}m / ${pressure.everydayHeight}m</span></div>
        `;
        return;
      }
      if (key === "heritage_micro_economy") {
        const data = PAYLOAD.overlayGroups.heritageParticles;
        const count = Math.max(18, Math.min(58, Math.round(data.count / 8)));
        let particles = "";
        for (let i = 0; i < count; i += 1) {
          const x = (i * 31) % 100;
          const y = (i * 17) % 100;
          const scale = 0.55 + ((i % 7) / 10);
          const opacity = 0.18 + ((i % 5) / 10);
          particles += `<span class="particle" style="left:${x}%;top:${y}%;transform:scale(${scale});opacity:${opacity}"></span>`;
        }
        overlayLabel.textContent = "Heritage Particles";
        overlayBody.innerHTML = `
          <div class="particle-field">${particles}</div>
          <div class="metric-line"><span>Micro-fragments</span><span>${data.count}</span></div>
          <div class="metric-line"><span>Active footprint</span><span>${data.footprintArea}</span></div>
        `;
        return;
      }
      if (key === "negotiated_24h_alley") {
        const data = PAYLOAD.overlayGroups.dayNightBand;
        const scale = 0.35 + beatProgress * 0.55;
        overlayLabel.textContent = "Day / Night Protocol";
        overlayBody.innerHTML = `
          <div class="day-night" style="--scale:${scale}">
            <div class="day-night-grid">
              <span>${data.reliefNodes} relief nodes</span>
              <span>${data.oneWayAlleys} one-way alleys</span>
              <span>${data.quietBuildings} quiet buildings</span>
            </div>
          </div>
        `;
        overlayBody.querySelector(".day-night").style.setProperty("transform", `scaleX(${0.96 + beatProgress * 0.04})`);
        overlayBody.querySelector(".day-night").style.setProperty("opacity", `${0.62 + beatProgress * 0.38}`);
        return;
      }
      overlayLabel.textContent = "Baseline Numbers";
      overlayBody.innerHTML = `
        <div class="metric-line"><span>Buildings</span><span>${PAYLOAD.stats.buildingCount}</span></div>
        <div class="metric-line"><span>Average height</span><span>${PAYLOAD.stats.avgHeight}m</span></div>
        <div class="metric-line"><span>Stakeholder groups</span><span>${Object.keys(PAYLOAD.stats.stakeholderCounts).length}</span></div>
      `;
    }

    function renderFilmFrame(elapsedMs) {
      const duration = PAYLOAD.meta.durationMs;
      const elapsed = ((elapsedMs % duration) + duration) % duration;
      const beat = PAYLOAD.beats.find((item) => elapsed >= item.start && elapsed < item.end) || PAYLOAD.beats[PAYLOAD.beats.length - 1];
      const beatProgress = (elapsed - beat.start) / Math.max(beat.end - beat.start, 1);
      const scenarioKey = activeScenarioKey(elapsed);
      const scenario = PAYLOAD.scenarios.find((item) => item.key === scenarioKey);
      const metrics = PAYLOAD.scenarioMetrics[scenarioKey];

      setScenarioActive(scenarioKey);
      beatKicker.textContent = beat.label;
      beatTitle.textContent = scenario ? scenario.label : beat.label;
      stageName.textContent = beat.label;
      lede.textContent = beat.lede;
      noteText.textContent = scenario ? scenario.caption : beat.lede;
      timelineFill.style.width = `${(elapsed / duration) * 100}%`;

      map.getSource("buildings").setData(PAYLOAD.collections.scenarioBuildings[scenarioKey] || PAYLOAD.collections.baseline);
      map.setPaintProperty("district-fill", "fill-color", scenario ? scenario.accent : "#112033");
      map.setPaintProperty("district-fill", "fill-opacity", 0.08 + beatProgress * 0.14);
      map.setPaintProperty("tourist-spine", "line-opacity", scenarioKey === "tourism_capture" || scenarioKey === "negotiated_24h_alley" ? 0.65 : 0.18);
      map.setPaintProperty("tourist-spine-glow", "line-opacity", scenarioKey === "tourism_capture" ? 0.42 : scenarioKey === "negotiated_24h_alley" ? 0.26 : 0.08);
      map.setPaintProperty("quiet-points", "circle-opacity", scenarioKey === "negotiated_24h_alley" ? 0.92 : scenarioKey === "heritage_micro_economy" ? 0.24 : 0.0);
      map.setPaintProperty("quiet-points", "circle-radius", scenarioKey === "negotiated_24h_alley" ? 2.4 + beatProgress * 4.8 : 1.8);
      map.setPaintProperty("buildings", "fill-extrusion-opacity", 0.78 + beatProgress * 0.16);
      map.easeTo({
        center: PAYLOAD.meta.center,
        zoom: 14.12 + beatProgress * 0.42,
        pitch: 50 + beatProgress * 10,
        bearing: -20 + (SCENARIO_ORDER.indexOf(scenarioKey) * 8) + beatProgress * 4,
        duration: 0
      });

      renderOverlay(scenarioKey, beatProgress);

      const numberValues = [
        metrics ? metrics.buildingCount : PAYLOAD.stats.buildingCount,
        metrics ? metrics.avgHeight : PAYLOAD.stats.avgHeight,
        Object.keys(PAYLOAD.stats.stakeholderCounts).length
      ];
      [...baselineNumbers.children].forEach((node, idx) => {
        const strong = node.querySelector("strong");
        strong.textContent = numberValues[idx];
      });
      return true;
    }

    function animate(ts) {
      if (loopStart === null) loopStart = ts;
      renderFilmFrame(ts - loopStart);
      requestAnimationFrame(animate);
    }

    window.__codexRenderAt = (ms) => renderFilmFrame(ms);

    map.on("load", () => {
      map.addSource("district", { type: "geojson", data: PAYLOAD.collections.district });
      map.addSource("buildings", { type: "geojson", data: PAYLOAD.collections.baseline });
      map.addSource("touristSpine", { type: "geojson", data: PAYLOAD.collections.touristSpine });
      map.addSource("quietPoints", { type: "geojson", data: PAYLOAD.collections.quietBuildings });

      map.addLayer({ id: "district-fill", type: "fill", source: "district", paint: { "fill-color": "#112033", "fill-opacity": 0.18 } });
      map.addLayer({ id: "tourist-spine-glow", type: "line", source: "touristSpine", paint: { "line-color": "#ff6b3d", "line-width": 14, "line-opacity": 0.0, "line-blur": 10 } });
      map.addLayer({ id: "tourist-spine", type: "line", source: "touristSpine", paint: { "line-color": "#ffe3d3", "line-width": 2.2, "line-opacity": 0.0, "line-dasharray": [1.2, 1.5] } });
      map.addLayer({
        id: "buildings",
        type: "fill-extrusion",
        source: "buildings",
        paint: {
          "fill-extrusion-color": ["coalesce", ["get", "color"], "#9fb3c8"],
          "fill-extrusion-height": ["get", "height"],
          "fill-extrusion-base": 0,
          "fill-extrusion-opacity": 0.85
        }
      });
      map.addLayer({
        id: "quiet-points",
        type: "circle",
        source: "quietPoints",
        paint: {
          "circle-color": "#6ce0d6",
          "circle-opacity": 0.0,
          "circle-radius": 0,
          "circle-stroke-color": "#ffffff",
          "circle-stroke-width": 1
        }
      });
      map.addLayer({ id: "district-line", type: "line", source: "district", paint: { "line-color": "#d7eef7", "line-width": 1.1, "line-opacity": 0.46 } });

      map.fitBounds([[PAYLOAD.meta.bounds[0], PAYLOAD.meta.bounds[1]], [PAYLOAD.meta.bounds[2], PAYLOAD.meta.bounds[3]]], {
        padding: { top: 110, right: 430, bottom: 110, left: 430 },
        duration: 0
      });

      if (EXPORT_MODE && EXPORT_MS !== null) {
        window.__codexRenderAt(Number(EXPORT_MS) || 0);
      } else {
        requestAnimationFrame(animate);
      }
    });
  </script>
</body>
</html>
"""


def build(slug=None):
    slug = slug or settings.SLUG
    payload = build_payload(slug)
    out_dir = OUT / slug
    out_dir.mkdir(parents=True, exist_ok=True)
    html = HTML_TEMPLATE.replace("__PAYLOAD__", json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
    out_path = out_dir / "editorial_data_film.html"
    out_path.write_text(html, encoding="utf-8")
    return out_path
