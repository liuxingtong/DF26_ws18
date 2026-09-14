# Editorial Film Data Platform Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a browser-based editorial-film data platform for Dapuqiao plus a deterministic 10-second MP4 export that visualizes scenario switching through restrained, cinematic data overlays rather than a conventional dashboard.

**Architecture:** Reuse the existing `intro_story` geometry pipeline as the spatial base, add a new metric-packing module that computes per-scenario editorial signatures, and generate a dedicated `editorial_data_film.html` page with timeline-driven overlays and a frame-accurate render hook for video export. Keep the export path deterministic by capturing the browser page frame-by-frame and encoding those frames into a 10-second video artifact.

**Tech Stack:** Python, GeoPandas, Shapely, existing `ws05` / regime pipeline, HTML/CSS/vanilla JS, MapLibre GL, Playwright for frame capture, OpenCV for video assembly, `unittest`.

---

## File Structure

### New files

- `F:\Aworks\DF2026\python基础\DF26_ws18\06_AI Render Students\engine\editorial_data_film.py`
  - Packs scenario metrics and generates the new editorial-film HTML surface.
- `F:\Aworks\DF2026\python基础\DF26_ws18\06_AI Render Students\engine\export_editorial_film.py`
  - Captures browser frames from the generated page and assembles the MP4.
- `F:\Aworks\DF2026\python基础\DF26_ws18\06_AI Render Students\tests\test_editorial_data_film.py`
  - Covers payload structure, metric availability, and export metadata helpers.

### Modified files

- `F:\Aworks\DF2026\python基础\DF26_ws18\06_AI Render Students\run.py`
  - Adds commands for generating the platform page and exporting the 10-second video.

### Output artifacts

- `F:\Aworks\DF2026\python基础\DF26_ws18\06_AI Render Students\out\dapuqiao\editorial_data_film.html`
- `F:\Aworks\DF2026\python基础\DF26_ws18\06_AI Render Students\out\dapuqiao\editorial_data_film_frames_10s_24fps\`
- `F:\Aworks\DF2026\python基础\DF26_ws18\06_AI Render Students\out\dapuqiao\editorial_data_film_10s.mp4`

---

### Task 1: Pack editorial-film metrics and story beats

**Files:**
- Create: `F:\Aworks\DF2026\python基础\DF26_ws18\06_AI Render Students\engine\editorial_data_film.py`
- Test: `F:\Aworks\DF2026\python基础\DF26_ws18\06_AI Render Students\tests\test_editorial_data_film.py`

- [ ] **Step 1: Write the failing test**

```python
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "engine"))

from engine import editorial_data_film  # noqa: E402


class EditorialDataFilmPayloadTests(unittest.TestCase):
    def test_build_payload_contains_story_beats_and_metric_signatures(self):
        payload = editorial_data_film.build_payload("dapuqiao")

        self.assertEqual(payload["meta"]["slug"], "dapuqiao")
        self.assertEqual(payload["meta"]["durationMs"], 10000)
        self.assertEqual(len(payload["beats"]), 4)
        self.assertEqual(len(payload["scenarios"]), 4)
        self.assertIn("tourism_capture", payload["scenarioMetrics"])
        self.assertIn("negotiated_24h_alley", payload["scenarioMetrics"])
        self.assertIn("baseline", payload["collections"])
        self.assertIn("touristSpine", payload["collections"])

    def test_build_payload_exposes_editorial_metrics_used_in_film(self):
        payload = editorial_data_film.build_payload("dapuqiao")
        tourism = payload["scenarioMetrics"]["tourism_capture"]
        negotiated = payload["scenarioMetrics"]["negotiated_24h_alley"]

        self.assertGreater(tourism["buildingCount"], 0)
        self.assertGreater(tourism["avgHeight"], 0)
        self.assertGreaterEqual(tourism["slenderness"], 0)
        self.assertGreaterEqual(negotiated["reliefNodes"], 1)
        self.assertGreaterEqual(negotiated["oneWayAlleys"], 1)
        self.assertGreaterEqual(negotiated["quietBuildings"], 1)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
..\ .venv\Scripts\python -m unittest tests.test_editorial_data_film
```

Expected:

```text
ImportError: cannot import name 'editorial_data_film'
```

- [ ] **Step 3: Write minimal implementation**

```python
from pathlib import Path

import ws05
import settings


def _baseline_metrics(recs):
    heights = [float(r["h"]) for r in recs]
    return {
        "buildingCount": len(recs),
        "avgHeight": sum(heights) / len(heights),
        "maxHeight": max(heights),
    }


def build_payload(slug=None):
    slug = slug or settings.SLUG
    current_recs, _df = ws05.load_recs(slug)
    return {
        "meta": {"slug": slug, "durationMs": 10000},
        "beats": [
            {"key": "baseline"},
            {"key": "pressure_shift"},
            {"key": "fine_grain_survival"},
            {"key": "timed_negotiation"},
        ],
        "scenarios": [
            {"key": "tourism_capture"},
            {"key": "everyday_life_first"},
            {"key": "heritage_micro_economy"},
            {"key": "negotiated_24h_alley"},
        ],
        "scenarioMetrics": {
            "tourism_capture": {**_baseline_metrics(current_recs), "slenderness": 0},
            "everyday_life_first": {**_baseline_metrics(current_recs), "slenderness": 0},
            "heritage_micro_economy": {**_baseline_metrics(current_recs), "slenderness": 0},
            "negotiated_24h_alley": {**_baseline_metrics(current_recs), "slenderness": 0, "reliefNodes": 1, "oneWayAlleys": 1, "quietBuildings": 1},
        },
        "collections": {"baseline": {"type": "FeatureCollection", "features": []}, "touristSpine": {"type": "FeatureCollection", "features": []}},
    }
```

- [ ] **Step 4: Expand the implementation to real scenario metrics**

```python
def _scenario_metric_row(recs):
    heights = [float(r["h"]) for r in recs]
    areas = [float(r["geom"].area) for r in recs]
    slenderness = (sum(heights) / max(len(heights), 1)) / max((sum(areas) / max(len(areas), 1)) ** 0.5, 1e-6)
    return {
        "buildingCount": len(recs),
        "avgHeight": round(sum(heights) / len(heights), 2),
        "maxHeight": round(max(heights), 2),
        "slenderness": round(slenderness, 3),
    }


def _scenario_metrics(slug):
    current_recs, _df = ws05.load_recs(slug)
    regs_map, regs = ws05.regime_recs(slug, settings.REGIMES)
    metrics = {}
    for key, recs in regs_map.items():
        if key == "current":
            continue
        metrics[key] = _scenario_metric_row(recs)
    tagged = ws05.ops._mo._copy_with_tags(current_recs)
    valved = ws05.ops._mo.crowd_valve(tagged, protect_tags=["resident_gate", "emergency_access"])
    night = ws05.ops._mo.night_reversion(valved, protect_tags=["residential_core", "resident_gate"])
    metrics["negotiated_24h_alley"]["reliefNodes"] = sum("relief_node" in r.get("tags", []) for r in valved)
    metrics["negotiated_24h_alley"]["oneWayAlleys"] = sum("one_way_alley" in r.get("tags", []) for r in valved)
    metrics["negotiated_24h_alley"]["quietBuildings"] = sum("night_quiet" in r.get("tags", []) for r in night)
    return metrics
```

- [ ] **Step 5: Run test to verify it passes**

Run:

```powershell
..\ .venv\Scripts\python -m unittest tests.test_editorial_data_film -v
```

Expected:

```text
OK
```

- [ ] **Step 6: Commit**

```bash
git add "06_AI Render Students/engine/editorial_data_film.py" "06_AI Render Students/tests/test_editorial_data_film.py"
git commit -m "feat: add editorial film payload builder"
```

---

### Task 2: Build the editorial-film HTML page

**Files:**
- Modify: `F:\Aworks\DF2026\python基础\DF26_ws18\06_AI Render Students\engine\editorial_data_film.py`
- Test: `F:\Aworks\DF2026\python基础\DF26_ws18\06_AI Render Students\tests\test_editorial_data_film.py`

- [ ] **Step 1: Write the failing test for page generation**

```python
def test_build_writes_editorial_film_html(self):
    path = editorial_data_film.build("dapuqiao")

    self.assertTrue(path.exists())
    self.assertEqual(path.name, "editorial_data_film.html")
    text = path.read_text(encoding="utf-8")
    self.assertIn("One district, four redistributions of urban life.", text)
    self.assertIn("window.__codexRenderAt", text)
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
..\ .venv\Scripts\python -m unittest tests.test_editorial_data_film::EditorialDataFilmPayloadTests.test_build_writes_editorial_film_html -v
```

Expected:

```text
AttributeError: module 'engine.editorial_data_film' has no attribute 'build'
```

- [ ] **Step 3: Write minimal page builder**

```python
HTML_TEMPLATE = """<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><title>Editorial Data Film</title></head>
<body>
  <h1>One district, four redistributions of urban life.</h1>
  <script>
    const PAYLOAD = __PAYLOAD__;
    window.__codexRenderAt = function(ms) { return true; };
  </script>
</body>
</html>
"""


def build(slug=None):
    slug = slug or settings.SLUG
    payload = build_payload(slug)
    out_dir = Path(__file__).resolve().parent.parent / "out" / slug
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "editorial_data_film.html"
    out_path.write_text(HTML_TEMPLATE.replace("__PAYLOAD__", json.dumps(payload)), encoding="utf-8")
    return out_path
```

- [ ] **Step 4: Replace the minimal template with the film layout**

```python
HTML_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Editorial Data Film</title>
  <link href="https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.css" rel="stylesheet" />
  <style>
    body { margin: 0; background: #05080d; color: #f6f8fb; font-family: "Segoe UI", Arial, sans-serif; overflow: hidden; }
    #map { position: fixed; inset: 0; }
    .left-panel { position: fixed; left: 22px; top: 22px; width: 360px; padding: 20px; border-radius: 22px; background: rgba(8,12,20,.82); border: 1px solid rgba(255,255,255,.12); }
    .right-panel { position: fixed; right: 22px; top: 22px; width: 360px; padding: 20px; border-radius: 22px; background: rgba(8,12,20,.82); border: 1px solid rgba(255,255,255,.12); }
    .bottom-strip { position: fixed; left: 22px; right: 22px; bottom: 18px; padding: 14px 16px; border-radius: 18px; background: rgba(7,12,20,.9); border: 1px solid rgba(255,255,255,.12); }
  </style>
</head>
<body>
  <div id="map"></div>
  <div class="left-panel">
    <div>Urban Reading to Urban Rewriting</div>
    <h1>One district, four redistributions of urban life.</h1>
    <p id="lede"></p>
    <div id="baselineNumbers"></div>
  </div>
  <div class="right-panel">
    <div id="scenarioStack"></div>
    <div id="beatCaption"></div>
  </div>
  <div class="bottom-strip">
    <div id="timelineProgress"></div>
    <div id="operatorRail"></div>
  </div>
  <script src="https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.js"></script>
  <script>
    const PAYLOAD = __PAYLOAD__;
    window.__codexRenderAt = function(ms) { return true; };
  </script>
</body>
</html>
"""
```

- [ ] **Step 5: Add the timed beat logic**

```javascript
const BEATS = [
  { start: 0, end: 2000, key: "baseline", lede: "Baseline conditions appear as restrained numeric evidence." },
  { start: 2000, end: 4500, key: "pressure_shift", lede: "Pressure shifts from intensified frontage toward released ground." },
  { start: 4500, end: 7500, key: "fine_grain_survival", lede: "Historic fabric survives by fragmenting into smaller productive units." },
  { start: 7500, end: 10000, key: "timed_negotiation", lede: "The alley becomes a scheduled protocol rather than a fixed spatial order." }
];

function renderAtElapsed(elapsedMs) {
  const beat = BEATS.find((item) => elapsedMs >= item.start && elapsedMs < item.end) || BEATS[BEATS.length - 1];
  document.getElementById("lede").textContent = beat.lede;
  document.getElementById("timelineProgress").style.width = `${(elapsedMs / PAYLOAD.meta.durationMs) * 100}%`;
  return beat.key;
}

window.__codexRenderAt = function(ms) {
  renderAtElapsed(((ms % PAYLOAD.meta.durationMs) + PAYLOAD.meta.durationMs) % PAYLOAD.meta.durationMs);
  return true;
};
```

- [ ] **Step 6: Run tests and open the page**

Run:

```powershell
..\ .venv\Scripts\python -m unittest tests.test_editorial_data_film -v
..\ .venv\Scripts\python run.py editorial-data-film dapuqiao
```

Expected:

```text
OK
editorial data film: ...\out\dapuqiao\editorial_data_film.html
```

- [ ] **Step 7: Commit**

```bash
git add "06_AI Render Students/engine/editorial_data_film.py" "06_AI Render Students/tests/test_editorial_data_film.py"
git commit -m "feat: add editorial film html surface"
```

---

### Task 3: Add a deterministic export pipeline for 10-second MP4 output

**Files:**
- Create: `F:\Aworks\DF2026\python基础\DF26_ws18\06_AI Render Students\engine\export_editorial_film.py`
- Modify: `F:\Aworks\DF2026\python基础\DF26_ws18\06_AI Render Students\run.py`
- Test: `F:\Aworks\DF2026\python基础\DF26_ws18\06_AI Render Students\tests\test_editorial_data_film.py`

- [ ] **Step 1: Write the failing export test**

```python
def test_frame_output_dir_and_video_path_are_deterministic(self):
    frames_dir = editorial_data_film.frame_output_dir("dapuqiao", duration_s=10, fps=24)
    video_path = editorial_data_film.video_output_path("dapuqiao", duration_s=10)

    self.assertEqual(frames_dir.name, "editorial_data_film_frames_10s_24fps")
    self.assertEqual(video_path.name, "editorial_data_film_10s.mp4")
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
..\ .venv\Scripts\python -m unittest tests.test_editorial_data_film -v
```

Expected:

```text
AttributeError: module 'engine.editorial_data_film' has no attribute 'frame_output_dir'
```

- [ ] **Step 3: Add deterministic path helpers**

```python
def frame_output_dir(slug, duration_s=10, fps=24):
    return OUT / slug / f"editorial_data_film_frames_{duration_s}s_{fps}fps"


def video_output_path(slug, duration_s=10):
    return OUT / slug / f"editorial_data_film_{duration_s}s.mp4"
```

- [ ] **Step 4: Create the export helper module**

```python
from pathlib import Path

import cv2

import editorial_data_film


def assemble_video_from_frames(slug, duration_s=10, fps=24):
    frames_dir = editorial_data_film.frame_output_dir(slug, duration_s=duration_s, fps=fps)
    video_path = editorial_data_film.video_output_path(slug, duration_s=duration_s)
    frames = sorted(frames_dir.glob("frame_*.jpg"))
    first = cv2.imread(str(frames[0]))
    height, width = first.shape[:2]
    writer = cv2.VideoWriter(str(video_path), cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height))
    for frame in frames:
        image = cv2.imread(str(frame))
        writer.write(image)
    writer.release()
    return video_path
```

- [ ] **Step 5: Add run.py entrypoints**

```python
    import editorial_data_film
    import export_editorial_film

    elif cmd == "editorial-data-film":
        slug = rest[0] if rest else settings.SLUG
        path = editorial_data_film.build(slug)
        print("editorial data film:", path)
    elif cmd == "editorial-data-film-video":
        slug = rest[0] if rest else settings.SLUG
        video = export_editorial_film.assemble_video_from_frames(slug, duration_s=10, fps=24)
        print("editorial data film video:", video)
```

- [ ] **Step 6: Run tests and a dry export path check**

Run:

```powershell
..\ .venv\Scripts\python -m unittest tests.test_editorial_data_film -v
..\ .venv\Scripts\python run.py editorial-data-film dapuqiao
```

Expected:

```text
OK
editorial data film: ...\editorial_data_film.html
```

- [ ] **Step 7: Commit**

```bash
git add "06_AI Render Students/engine/editorial_data_film.py" "06_AI Render Students/engine/export_editorial_film.py" "06_AI Render Students/run.py" "06_AI Render Students/tests/test_editorial_data_film.py"
git commit -m "feat: add editorial film export pipeline"
```

---

### Task 4: Implement the cinematic overlays and final 10-second sequence behavior

**Files:**
- Modify: `F:\Aworks\DF2026\python基础\DF26_ws18\06_AI Render Students\engine\editorial_data_film.py`
- Test: `F:\Aworks\DF2026\python基础\DF26_ws18\06_AI Render Students\tests\test_editorial_data_film.py`

- [ ] **Step 1: Add a failing structure test for beat-specific overlays**

```python
def test_build_payload_contains_editorial_overlay_groups(self):
    payload = editorial_data_film.build_payload("dapuqiao")

    self.assertIn("baselineNumbers", payload["overlayGroups"])
    self.assertIn("pressureBand", payload["overlayGroups"])
    self.assertIn("heritageParticles", payload["overlayGroups"])
    self.assertIn("dayNightBand", payload["overlayGroups"])
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
..\ .venv\Scripts\python -m unittest tests.test_editorial_data_film -v
```

Expected:

```text
KeyError: 'overlayGroups'
```

- [ ] **Step 3: Pack overlay groups into the payload**

```python
payload["overlayGroups"] = {
    "baselineNumbers": [
        {"label": "Buildings", "value": payload["stats"]["buildingCount"]},
        {"label": "Avg Height", "value": payload["scenarioMetrics"]["tourism_capture"]["avgHeight"]},
        {"label": "Stakeholders", "value": len(payload["stats"]["stakeholderCounts"])},
    ],
    "pressureBand": {
        "from": payload["scenarioMetrics"]["tourism_capture"]["slenderness"],
        "to": payload["scenarioMetrics"]["everyday_life_first"]["slenderness"],
    },
    "heritageParticles": {
        "count": payload["scenarioMetrics"]["heritage_micro_economy"]["buildingCount"],
    },
    "dayNightBand": {
        "reliefNodes": payload["scenarioMetrics"]["negotiated_24h_alley"]["reliefNodes"],
        "quietBuildings": payload["scenarioMetrics"]["negotiated_24h_alley"]["quietBuildings"],
    },
}
```

- [ ] **Step 4: Wire those groups into the page animation**

```javascript
function renderBaselineNumbers() {
  const container = document.getElementById("baselineNumbers");
  container.innerHTML = PAYLOAD.overlayGroups.baselineNumbers
    .map((item) => `<div><strong>${item.value}</strong><span>${item.label}</span></div>`)
    .join("");
}

function renderPressureBand(progress) {
  const band = document.getElementById("pressureBand");
  band.style.transform = `scaleX(${0.4 + progress * 0.6})`;
}

function renderHeritageParticles(progress) {
  const field = document.getElementById("heritageParticles");
  field.style.opacity = `${0.15 + progress * 0.85}`;
}

function renderDayNightBand(progress) {
  const band = document.getElementById("dayNightBand");
  band.style.background = `linear-gradient(90deg, rgba(255,107,61,${0.3 + progress * 0.3}), rgba(108,224,214,${0.3 + progress * 0.3}))`;
}
```

- [ ] **Step 5: Verify the page behavior manually**

Run:

```powershell
..\ .venv\Scripts\python run.py editorial-data-film dapuqiao
```

Expected:

```text
editorial data film: ...\editorial_data_film.html
```

Manual checks:

- Beat 1 shows restrained numbers only
- Beat 2 emphasizes a shifting pressure band
- Beat 3 introduces fine-grain heritage particles
- Beat 4 resolves into a negotiated day-night band with node pulses

- [ ] **Step 6: Commit**

```bash
git add "06_AI Render Students/engine/editorial_data_film.py" "06_AI Render Students/tests/test_editorial_data_film.py"
git commit -m "feat: add editorial film data overlays"
```

---

### Task 5: Capture frames and ship the final 10-second MP4

**Files:**
- Modify: `F:\Aworks\DF2026\python基础\DF26_ws18\06_AI Render Students\engine\export_editorial_film.py`

- [ ] **Step 1: Add a browser capture helper**

```python
def capture_frame_indices(duration_s=10, fps=24):
    return list(range(duration_s * fps))
```

- [ ] **Step 2: Use Playwright to render deterministic frames**

```python
async def capture_frames(page_path, frames_dir, duration_s=10, fps=24):
    from playwright.async_api import async_playwright

    total_frames = duration_s * fps
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1920, "height": 1080}, device_scale_factor=1)
        await page.goto(page_path.as_uri(), wait_until="networkidle")
        await page.wait_for_timeout(3000)
        for i in range(total_frames):
            elapsed = (i / fps) * 1000
            await page.evaluate("(ms) => window.__codexRenderAt(ms)", elapsed)
            await page.wait_for_timeout(20)
            await page.screenshot(path=str(frames_dir / f"frame_{i:04d}.jpg"), type="jpeg", quality=92)
        await browser.close()
```

- [ ] **Step 3: Add a synchronous export entrypoint**

```python
def export_video(slug, duration_s=10, fps=24):
    html_path = editorial_data_film.build(slug)
    frames_dir = editorial_data_film.frame_output_dir(slug, duration_s=duration_s, fps=fps)
    frames_dir.mkdir(parents=True, exist_ok=True)
    asyncio.run(capture_frames(html_path, frames_dir, duration_s=duration_s, fps=fps))
    return assemble_video_from_frames(slug, duration_s=duration_s, fps=fps)
```

- [ ] **Step 4: Run the final export**

Run:

```powershell
..\ .venv\Scripts\python run.py editorial-data-film-video dapuqiao
```

Expected:

```text
editorial data film video: ...\out\dapuqiao\editorial_data_film_10s.mp4
```

- [ ] **Step 5: Verify the artifact**

Check:

- `out/dapuqiao/editorial_data_film.html` opens in browser
- `out/dapuqiao/editorial_data_film_frames_10s_24fps` contains 240 frames
- `out/dapuqiao/editorial_data_film_10s.mp4` exists
- system media metadata reports about `10` seconds duration

- [ ] **Step 6: Commit**

```bash
git add "06_AI Render Students/engine/export_editorial_film.py"
git commit -m "feat: export editorial film mp4"
```

---

## Spec Coverage Check

- Editorial-film positioning is covered by Task 2 and Task 4.
- The 10-second four-beat structure is covered by Task 2 and Task 4.
- Reuse of current geometry and scenario outputs is covered by Task 1.
- Deterministic video export is covered by Task 3 and Task 5.
- Restrained cinematic overlays instead of dashboard widgets are covered by Task 4.

## Placeholder Check

- No `TODO`, `TBD`, or generic "add validation later" instructions remain.
- Each task includes explicit files, commands, and code targets.

## Type Consistency Check

- Payload entry names are consistent across tasks: `scenarioMetrics`, `overlayGroups`, `frame_output_dir`, `video_output_path`, `build`, `export_video`.
- Output artifact names are consistent: `editorial_data_film.html`, `editorial_data_film_frames_10s_24fps`, `editorial_data_film_10s.mp4`.
