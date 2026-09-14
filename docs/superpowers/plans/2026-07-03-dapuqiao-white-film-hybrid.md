# Dapuqiao White-Film Hybrid Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a white-background, plan-based 10-second HTML preview for Dapuqiao that uses real project geometry and real scenario/operator metrics instead of the current dark 3D editorial film style.

**Architecture:** Reuse the existing Dapuqiao geometry and metric pipeline from `ws05`, `intro_story`, and `editorial_data_film`, but generate a separate white-film payload and HTML surface. Keep rendering deterministic through `window.__codexRenderAt(ms)` so the preview loops cleanly now and stays exportable later without coupling this task to video output.

**Tech Stack:** Python, GeoPandas, Shapely, existing `ws05` / regime pipeline, HTML/CSS/vanilla JS, MapLibre GL, `unittest`.

---

## File Structure

### New files

- `F:\Aworks\DF2026\python基础\DF26_ws18\06_AI Render Students\engine\white_film_hybrid.py`
  - Packs the real white-film payload and writes the white-background preview HTML.
- `F:\Aworks\DF2026\python基础\DF26_ws18\06_AI Render Students\tests\test_white_film_hybrid.py`
  - Covers payload contents, real metric extraction, deterministic path helpers, and HTML generation.

### Modified files

- `F:\Aworks\DF2026\python基础\DF26_ws18\06_AI Render Students\run.py`
  - Adds an entrypoint to build the white-film preview page.

### Output artifacts

- `F:\Aworks\DF2026\python基础\DF26_ws18\06_AI Render Students\out\dapuqiao\white_film_hybrid.html`

---

### Task 1: Create the real-data white-film payload builder

**Files:**
- Create: `F:\Aworks\DF2026\python基础\DF26_ws18\06_AI Render Students\engine\white_film_hybrid.py`
- Test: `F:\Aworks\DF2026\python基础\DF26_ws18\06_AI Render Students\tests\test_white_film_hybrid.py`

- [ ] **Step 1: Write the failing test**

```python
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "engine"))

from engine import white_film_hybrid  # noqa: E402


class WhiteFilmHybridPayloadTests(unittest.TestCase):
    def test_build_payload_contains_real_scenarios_beats_and_plan_collections(self):
        payload = white_film_hybrid.build_payload("dapuqiao")

        self.assertEqual(payload["meta"]["slug"], "dapuqiao")
        self.assertEqual(payload["meta"]["durationMs"], 10000)
        self.assertEqual([beat["key"] for beat in payload["beats"]], ["site_intro", "data_shift", "operator_logic"])
        self.assertEqual(len(payload["scenarios"]), 4)
        self.assertIn("baseline", payload["collections"])
        self.assertIn("scenarioBuildings", payload["collections"])
        self.assertIn("touristSpine", payload["collections"])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
..\ .venv\Scripts\python -m unittest tests.test_white_film_hybrid -v
```

Expected:

```text
ImportError: cannot import name 'white_film_hybrid'
```

- [ ] **Step 3: Write minimal implementation**

```python
from pathlib import Path

import editorial_data_film
import settings


ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "out"


def build_payload(slug=None):
    slug = slug or settings.SLUG
    film = editorial_data_film.build_payload(slug)
    return {
        "meta": {"slug": slug, "durationMs": 10000},
        "beats": [
            {"key": "site_intro", "start": 0, "end": 2000},
            {"key": "data_shift", "start": 3000, "end": 7000},
            {"key": "operator_logic", "start": 7000, "end": 10000},
        ],
        "scenarios": film["scenarios"],
        "collections": {
            "baseline": film["collections"]["baseline"],
            "scenarioBuildings": film["collections"]["scenarioBuildings"],
            "touristSpine": film["collections"]["touristSpine"],
        },
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```powershell
..\ .venv\Scripts\python -m unittest tests.test_white_film_hybrid -v
```

Expected:

```text
OK
```

- [ ] **Step 5: Commit**

```bash
git add "06_AI Render Students/engine/white_film_hybrid.py" "06_AI Render Students/tests/test_white_film_hybrid.py"
git commit -m "feat: add white film hybrid payload skeleton"
```

---

### Task 2: Add real metrics and operator-derived overlay data

**Files:**
- Modify: `F:\Aworks\DF2026\python基础\DF26_ws18\06_AI Render Students\engine\white_film_hybrid.py`
- Test: `F:\Aworks\DF2026\python基础\DF26_ws18\06_AI Render Students\tests\test_white_film_hybrid.py`

- [ ] **Step 1: Add failing tests for real metric groups**

```python
    def test_build_payload_uses_real_project_metrics_for_cards_and_overlays(self):
        payload = white_film_hybrid.build_payload("dapuqiao")
        metrics = payload["scenarioMetrics"]
        overlays = payload["overlayGroups"]

        self.assertIn("tourism_capture", metrics)
        self.assertIn("negotiated_24h_alley", metrics)
        self.assertGreater(metrics["tourism_capture"]["buildingCount"], 0)
        self.assertGreater(metrics["tourism_capture"]["avgHeight"], 0)
        self.assertGreater(metrics["tourism_capture"]["maxHeight"], 0)
        self.assertGreaterEqual(metrics["tourism_capture"]["slenderness"], 0)
        self.assertGreaterEqual(metrics["negotiated_24h_alley"]["reliefNodes"], 1)
        self.assertGreaterEqual(metrics["negotiated_24h_alley"]["oneWayAlleys"], 1)
        self.assertGreaterEqual(metrics["negotiated_24h_alley"]["quietBuildings"], 1)
        self.assertIn("metricCards", overlays)
        self.assertIn("scenarioBars", overlays)
        self.assertIn("heritageDots", overlays)
        self.assertIn("protocolBand", overlays)
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
..\ .venv\Scripts\python -m unittest tests.test_white_film_hybrid.WhiteFilmHybridPayloadTests.test_build_payload_uses_real_project_metrics_for_cards_and_overlays -v
```

Expected:

```text
KeyError: 'scenarioMetrics'
```

- [ ] **Step 3: Expand the payload builder with real metrics**

```python
from functools import lru_cache

import intro_story
import editorial_data_film
import settings
import ws05


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
        "label": "Measured Shifts",
        "start": 3000,
        "end": 7000,
        "lede": "Scenario change is translated into count, height, area, and pressure differences.",
    },
    {
        "key": "operator_logic",
        "label": "Operator Logic",
        "start": 7000,
        "end": 10000,
        "lede": "Crowd valve and night reversion explain why the plan and metrics move.",
    },
]


@lru_cache(maxsize=8)
def build_payload(slug=None):
    slug = slug or settings.SLUG
    film = editorial_data_film.build_payload(slug)
    scenario_metrics = film["scenarioMetrics"]
    overlays = {
        "metricCards": [
            {"key": "buildingCount", "label": "Buildings"},
            {"key": "avgHeight", "label": "Avg Height"},
            {"key": "maxHeight", "label": "Max Height"},
            {"key": "slenderness", "label": "Slenderness"},
        ],
        "scenarioBars": [
            {"key": "tourism_capture", "label": "Tourism Capture", "value": scenario_metrics["tourism_capture"]["avgHeight"]},
            {"key": "everyday_life_first", "label": "Everyday Life First", "value": scenario_metrics["everyday_life_first"]["avgHeight"]},
            {"key": "heritage_micro_economy", "label": "Heritage Micro-Economy", "value": scenario_metrics["heritage_micro_economy"]["avgHeight"]},
            {"key": "negotiated_24h_alley", "label": "Negotiated 24h Alley", "value": scenario_metrics["negotiated_24h_alley"]["avgHeight"]},
        ],
        "heritageDots": {
            "count": scenario_metrics["heritage_micro_economy"]["buildingCount"],
            "footprintArea": scenario_metrics["heritage_micro_economy"]["footprintArea"],
        },
        "protocolBand": {
            "reliefNodes": scenario_metrics["negotiated_24h_alley"]["reliefNodes"],
            "oneWayAlleys": scenario_metrics["negotiated_24h_alley"]["oneWayAlleys"],
            "quietBuildings": scenario_metrics["negotiated_24h_alley"]["quietBuildings"],
        },
    }
    return {
        "meta": film["meta"],
        "beats": BEATS,
        "scenarios": film["scenarios"],
        "scenarioMetrics": scenario_metrics,
        "overlayGroups": overlays,
        "collections": {
            "baseline": film["collections"]["baseline"],
            "scenarioBuildings": film["collections"]["scenarioBuildings"],
            "touristSpine": film["collections"]["touristSpine"],
            "district": film["collections"]["district"],
            "reliefNodes": film["collections"]["reliefNodes"],
            "quietBuildings": film["collections"]["quietBuildings"],
            "quietBuffer": film["collections"]["quietBuffer"],
        },
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```powershell
..\ .venv\Scripts\python -m unittest tests.test_white_film_hybrid -v
```

Expected:

```text
OK
```

- [ ] **Step 5: Commit**

```bash
git add "06_AI Render Students/engine/white_film_hybrid.py" "06_AI Render Students/tests/test_white_film_hybrid.py"
git commit -m "feat: add real metrics for white film hybrid"
```

---

### Task 3: Add deterministic output path helpers and HTML build entrypoint

**Files:**
- Modify: `F:\Aworks\DF2026\python基础\DF26_ws18\06_AI Render Students\engine\white_film_hybrid.py`
- Test: `F:\Aworks\DF2026\python基础\DF26_ws18\06_AI Render Students\tests\test_white_film_hybrid.py`

- [ ] **Step 1: Add failing tests for paths and HTML build**

```python
    def test_html_output_path_and_build_are_deterministic(self):
        out_path = white_film_hybrid.output_path("dapuqiao")
        built = white_film_hybrid.build("dapuqiao")

        self.assertEqual(out_path.name, "white_film_hybrid.html")
        self.assertEqual(built, out_path)
        self.assertTrue(built.exists())
        text = built.read_text(encoding="utf-8")
        self.assertIn("White Film Hybrid", text)
        self.assertIn("window.__codexRenderAt", text)
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
..\ .venv\Scripts\python -m unittest tests.test_white_film_hybrid.WhiteFilmHybridPayloadTests.test_html_output_path_and_build_are_deterministic -v
```

Expected:

```text
AttributeError: module 'engine.white_film_hybrid' has no attribute 'output_path'
```

- [ ] **Step 3: Add path helpers and build function**

```python
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "out"


def output_path(slug):
    return OUT / slug / "white_film_hybrid.html"


HTML_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>White Film Hybrid</title>
</head>
<body>
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
    out_path = output_path(slug)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    html = HTML_TEMPLATE.replace("__PAYLOAD__", json.dumps(payload, ensure_ascii=False))
    out_path.write_text(html, encoding="utf-8")
    return out_path
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```powershell
..\ .venv\Scripts\python -m unittest tests.test_white_film_hybrid -v
```

Expected:

```text
OK
```

- [ ] **Step 5: Commit**

```bash
git add "06_AI Render Students/engine/white_film_hybrid.py" "06_AI Render Students/tests/test_white_film_hybrid.py"
git commit -m "feat: add white film hybrid output paths"
```

---

### Task 4: Build the white-background hybrid HTML surface

**Files:**
- Modify: `F:\Aworks\DF2026\python基础\DF26_ws18\06_AI Render Students\engine\white_film_hybrid.py`
- Test: `F:\Aworks\DF2026\python基础\DF26_ws18\06_AI Render Students\tests\test_white_film_hybrid.py`

- [ ] **Step 1: Add a failing structure test for the final page language**

```python
    def test_build_writes_white_plan_page_without_progress_bar(self):
        path = white_film_hybrid.build("dapuqiao")
        text = path.read_text(encoding="utf-8")

        self.assertIn("One district, four redistributions of urban life.", text)
        self.assertIn("Scenario Metrics", text)
        self.assertIn("Operator Logic", text)
        self.assertIn("maplibre-gl.js", text)
        self.assertNotIn("timelineFill", text)
        self.assertNotIn("progressBar", text)
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
..\ .venv\Scripts\python -m unittest tests.test_white_film_hybrid.WhiteFilmHybridPayloadTests.test_build_writes_white_plan_page_without_progress_bar -v
```

Expected:

```text
AssertionError: 'Scenario Metrics' not found
```

- [ ] **Step 3: Replace the minimal template with the real white-film page**

```python
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
      --paper:#fffdfa;
      --ink:#151515;
      --muted:#67635d;
      --line:#d9d2c8;
      --panel:rgba(255,253,250,.92);
      --accentA:#dd6b3d;
      --accentB:#3d8882;
      --accentC:#b68a2d;
      --accentD:#4a64a8;
    }
    *{box-sizing:border-box}
    html,body{margin:0;height:100%;overflow:hidden;background:var(--bg);color:var(--ink);font-family:Georgia,"Times New Roman",serif}
    #map{position:fixed;inset:0}
    .sheet{position:fixed;inset:0;padding:24px;display:grid;grid-template-columns:360px 1fr 360px;gap:18px;pointer-events:none}
    .panel{background:var(--panel);border:1px solid var(--line);border-radius:24px;box-shadow:0 14px 36px rgba(30,24,16,.06)}
  </style>
</head>
<body>
  <div id="map"></div>
  <div class="sheet">
    <div class="panel" id="leftPanel"></div>
    <div></div>
    <div class="panel" id="rightPanel"></div>
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

- [ ] **Step 4: Implement the actual layout and beat logic**

```javascript
const BEAT_WINDOWS = [
  { key: "site_intro", start: 0, end: 2000 },
  { key: "data_shift", start: 3000, end: 7000 },
  { key: "operator_logic", start: 7000, end: 10000 },
];

function activeScenarioKey(elapsed) {
  if (elapsed < 500) return "tourism_capture";
  if (elapsed < 1000) return "everyday_life_first";
  if (elapsed < 1500) return "heritage_micro_economy";
  if (elapsed < 2000) return "negotiated_24h_alley";
  if (elapsed < 5000) return "tourism_capture";
  if (elapsed < 6000) return "everyday_life_first";
  if (elapsed < 7000) return "heritage_micro_economy";
  return "negotiated_24h_alley";
}

function renderAtElapsed(elapsedMs) {
  const elapsed = ((elapsedMs % PAYLOAD.meta.durationMs) + PAYLOAD.meta.durationMs) % PAYLOAD.meta.durationMs;
  const scenarioKey = activeScenarioKey(elapsed);
  const scenario = PAYLOAD.scenarios.find((item) => item.key === scenarioKey);
  map.getSource("buildings").setData(PAYLOAD.collections.scenarioBuildings[scenarioKey] || PAYLOAD.collections.baseline);
  renderScenarioCards(scenarioKey);
  renderMetricCards(scenarioKey);
  renderBars(scenarioKey);
  renderOperatorNotes(elapsed, scenarioKey);
  return true;
}

window.__codexRenderAt = renderAtElapsed;
```

- [ ] **Step 5: Run tests and build the preview page**

Run:

```powershell
..\ .venv\Scripts\python -m unittest tests.test_white_film_hybrid -v
..\ .venv\Scripts\python run.py white-film-hybrid dapuqiao
```

Expected:

```text
OK
white film hybrid: ...\out\dapuqiao\white_film_hybrid.html
```

- [ ] **Step 6: Commit**

```bash
git add "06_AI Render Students/engine/white_film_hybrid.py" "06_AI Render Students/tests/test_white_film_hybrid.py"
git commit -m "feat: add white film hybrid preview page"
```

---

### Task 5: Add the run.py entrypoint and verify the real preview artifact

**Files:**
- Modify: `F:\Aworks\DF2026\python基础\DF26_ws18\06_AI Render Students\run.py`
- Test: `F:\Aworks\DF2026\python基础\DF26_ws18\06_AI Render Students\tests\test_white_film_hybrid.py`

- [ ] **Step 1: Add a failing smoke test for the module path helper**

```python
    def test_output_path_points_to_out_slug_directory(self):
        path = white_film_hybrid.output_path("dapuqiao")
        self.assertIn("out", str(path))
        self.assertEqual(path.parent.name, "dapuqiao")
```

- [ ] **Step 2: Run test to verify it passes before the CLI change**

Run:

```powershell
..\ .venv\Scripts\python -m unittest tests.test_white_film_hybrid.WhiteFilmHybridPayloadTests.test_output_path_points_to_out_slug_directory -v
```

Expected:

```text
OK
```

- [ ] **Step 3: Add the new CLI command**

```python
    import white_film_hybrid

    elif cmd == "white-film-hybrid":
        slug = rest[0] if rest else settings.SLUG
        path = white_film_hybrid.build(slug)
        print("white film hybrid:", path)
```

- [ ] **Step 4: Run the preview builder and verify the artifact**

Run:

```powershell
..\ .venv\Scripts\python run.py white-film-hybrid dapuqiao
```

Expected:

```text
white film hybrid: ...\out\dapuqiao\white_film_hybrid.html
```

Manual checks:

- the page opens from the output path
- the background is white rather than dark
- buildings are flat colored polygons rather than 3D extrusions
- no progress bar is visible
- the four scenarios remain visible while the active scenario changes
- the metric cards and mini-charts use real numbers from the payload
- the final segment shows operator explanations tied to `crowd_valve` and `night_reversion`

- [ ] **Step 5: Commit**

```bash
git add "06_AI Render Students/run.py"
git commit -m "feat: add white film hybrid command"
```

---

## Spec Coverage Check

- White background, plan-based redesign is covered by Task 4.
- Real geometry and real metrics only are covered by Task 1 and Task 2.
- Building color preservation is covered by Task 4 through flat polygon rendering instead of new mock geometry.
- `0-2s / 3-7s / 7-10s` timing is covered by Task 1 and Task 4.
- Removal of the progress bar is covered by Task 4.
- HTML preview first, no MP4 requirement, is covered by Task 3 through Task 5.

## Placeholder Check

- No `TODO`, `TBD`, or deferred placeholders remain.
- Each task includes exact files, commands, and concrete code targets.

## Type Consistency Check

- Shared names remain consistent across tasks: `build_payload`, `build`, `output_path`, `scenarioMetrics`, `overlayGroups`, `collections`, `window.__codexRenderAt`.
- Output artifact name remains consistent: `white_film_hybrid.html`.
