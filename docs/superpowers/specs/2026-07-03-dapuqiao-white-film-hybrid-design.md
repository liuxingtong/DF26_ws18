# Dapuqiao White-Film Hybrid Design

## Goal

Build a new 10-second browser-based preview for Dapuqiao that replaces the current dark 3D editorial film with a white-background, plan-based hybrid language.

The new direction should:

- keep buildings visibly colored
- use only real project data
- feel like a mix of an analytical newspaper spread and a speculative research diagram
- prioritize fast readability over cinematic atmosphere
- work first as an HTML preview before any MP4 export

## Why This Direction

The current editorial-film prototype is visually close to the earlier dark OSM narrative. It is strong atmospherically, but too similar in tone and too dependent on 3D volume as the main carrier of meaning.

The new white-film hybrid should instead present:

- the same site as a flat, evidence-rich field
- scenario change as a real plan transformation
- metrics as synchronized analytical evidence
- operators as legible mechanisms, not just background logic

This makes the preview feel more like a design-research artifact and less like a continuation of the existing intro film.

## Chosen Direction

Use an **Editorial Float** layout with a **Diff Map** as the dominant visual language.

This means:

- the main canvas is a nearly full-screen white plan-based map
- most buildings sit in a pale base layer
- changed-only buildings or affected subsets carry the strongest color
- data appears as floating editorial evidence cards rather than fixed side panels
- local operator callouts replace long-distance diagram arrows
- no playback progress bar is shown

## Real Data Requirement

All displayed values and geometry must come from the existing project pipeline. No placeholder figures, invented counts, or manually mocked scenario geometry should appear in the implemented preview.

### Required sources

- `06_AI Render Students/engine/ws05.py`
- `06_AI Render Students/engine/intro_story.py`
- `06_AI Render Students/engine/editorial_data_film.py`
- the existing `settings.REGIMES` flow
- the existing operator logic from the linked `05_Shanghai Power to Form Students` workspace

### Required real outputs

The preview must use real:

- site bounds
- current building geometry
- per-regime building geometry
- stakeholder colors already defined in the project
- regime step/operator chains
- `crowd_valve` and `night_reversion` derived metrics

## Visual System

### Base

- background: warm white / paper white
- linework: black to soft gray
- panels: off-white with thin editorial borders
- typography: serif headline plus neutral sans-serif data labels
- no dark HUD, no cinematic vignette, no progress bar

### Map language

- plan view only
- no fill-extrusion / no 3D building heights rendered as blocks
- the map fills the frame and acts as the main stage
- buildings are shown as flat polygons
- district outline and spine line stay visible
- operator marks appear through local highlights, changed-only emphasis, short leader notes, and nearby evidence cards

### Color logic

Preserve project-derived categories, but apply them editorially rather than saturating the entire map at all times.

The preferred logic is:

- default state: pale low-contrast base map
- emphasis state: changed-only buildings highlighted like the existing diff maps
- optional tag state: selected moments can switch to tag-based thematic coloring inspired by the existing tag maps

Additional annotation colors may be introduced for overlays, but any strong color use on buildings must still correspond to real project-derived categories or change states.

## Layout Structure

The preview page should now be organized as one immersive map plus floating evidence fragments.

### 1. Full-screen diff map

The map covers nearly the entire frame and shows:

- district outline
- active scenario geometry
- changed-only highlight logic as the main signal
- optional tag-based emphasis in selected moments
- local operator evidence near affected areas

This is the permanent anchor for the entire 10-second sequence.

### 2. Floating evidence cards

Instead of fixed left-right sidebars, the page uses 2-4 floating editorial cards that enter and leave over time. These cards can sit near map edges or near relevant zones, but should feel like a magazine spread laid over the map rather than a dashboard shell.

### 3. Minimal scenario locator

All four scenarios remain present in a compact way, but only as a light locator system. They should not read as a fixed navigation rail.

### 4. Local annotation system

Annotations should feel attached to places on the map:

- short leaders
- local labels
- small rings or focus halos
- tiny before/after or diff evidence boxes

## Real Metrics To Show

The page should compute and display a subset of real project metrics that can change across scenarios.

### Core scenario metrics

- `buildingCount`
- `avgHeight`
- `maxHeight`
- `slenderness`
- `footprintArea`

### Operator / protocol metrics

- `reliefNodes`
- `oneWayAlleys`
- `quietBuildings`

### Optional contextual counts

- stakeholder category count
- active operator count in current regime
- number of buildings touched by selected scenario step chain

## 10-Second Sequence

The approved timing structure is:

### 0-2s: diff map established

Purpose:

- show the map as a changed-field immediately
- make the audience understand that one district is being tested through four regimes

Visual actions:

- district outline fades in
- pale base buildings appear
- changed buildings or affected subsets are highlighted first
- four scenario labels or capsules flash/step through in quick succession

### 3-7s: floating evidence cards lead

Purpose:

- convert scenario switching into measurable evidence

Visual actions:

- a `policy heatmap` card appears
- a `metrics 2x2` card appears
- an `operator diff` card appears
- the active plan state changes in sync with the cards
- no long transition easing; changes should be crisp and editorial

### 7-10s: operator evidence arrives

Purpose:

- explain the logic behind the visible scenario effects

Visual actions:

- a compact `before / after` mini card appears
- local notes or short leaders attach to affected zones
- day/night protocol markings enter for `negotiated_24h_alley`
- `crowd_valve` and `night_reversion` become spatially legible through local diff evidence rather than distant arrows

## Chart Language

Avoid repeating one visual component. Use a small editorial family of chart fragments inspired by the existing project PNG outputs.

Recommended chart family:

- `diff map` changed-only highlight view as the main base map
- `tag map` thematic coloring as a secondary map mode when useful
- `policy heatmap` floating matrix card
- `metrics 2x2` floating statistics card
- `before / after` mini twin-map card
- `operator diff` change-count card

These should be implemented as lightweight HTML/CSS/SVG/JS elements, not heavy charting libraries.

## Interaction and Preview Behavior

The first deliverable is an HTML preview, not a final video export.

The preview should support:

- automatic looping through the 10-second sequence
- deterministic `window.__codexRenderAt(ms)` rendering for future export
- clickable scenario switching if that comes cheaply from the same implementation

The preview should not require subtitles or a timeline/progress bar.

## Implementation Shape

The new direction should be implemented as a new white-film preview rather than a destructive rewrite of the already-working dark editorial film. Reuse data-packing logic where helpful, but allow the rendered page layout and rendering strategy to diverge substantially.

Recommended structure:

- keep metric-building logic in `editorial_data_film.py` or a closely related module
- create a new white-film HTML builder instead of mutating the current dark template into an unrelated design
- reuse existing geometry collections and scenario metrics where possible
- preserve deterministic rendering hooks for later frame capture

## Deliverable for the Next Step

The next implementation phase should produce:

- one HTML preview page in `out/dapuqiao/`
- white background
- full-screen plan map
- diff-map dominant coloring
- real scenario geometry and real metrics
- the approved 10-second timing
- floating editorial cards rather than fixed side panels

MP4 export is explicitly out of scope for the immediate next step.

## Risks and Constraints

### Main risk

If the layout becomes too diagram-heavy, the 10-second preview may become harder to read than the darker version.

### Guardrail

Keep the main structure readable like an editorial spread, then use diagram annotations as accents.

### Technical constraint

Because the preview must use only real data, any visual mark that implies a quantity must either:

- be computed from actual scenario/operator outputs, or
- be omitted

No decorative fake charts should be included.

## Decision Summary

Approved design decisions:

- use a white-background editorial-float direction
- preserve colored buildings
- make changed-only diff logic the primary map emphasis
- use only real project data
- remove progress-bar logic
- compress diff-map establishment to `0-2s`
- move floating evidence cards to `3-7s`
- use `7-10s` for local operator evidence
- build HTML preview first, postpone video export
