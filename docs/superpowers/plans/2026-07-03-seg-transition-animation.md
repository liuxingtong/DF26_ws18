# Seg Transition Animation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a roughly 10-second bird's-eye animation that rotates while transitioning across four Dapuqiao regimes in the platform's segmentation color style with an OSM base map on a black background, exporting every frame to a folder.

**Architecture:** Reuse `06_AI Render Students` loading and 3D massing code, extend the renderer with background and outline controls, then add a dedicated animation module that renders two adjacent regime views per frame and blends them into the final frame sequence. Keep the transition scheduling logic pure and test it first.

**Tech Stack:** Python, unittest, matplotlib, Pillow, existing `06_AI Render Students` + `05_Shanghai Power to Form Students` helpers.

---

### Task 1: Lock the frame schedule helpers with tests

**Files:**
- Create: `F:/Aworks/DF2026/python基础/DF26_ws18/06_AI Render Students/tests/test_seg_transition.py`
- Test: `F:/Aworks/DF2026/python基础/DF26_ws18/06_AI Render Students/tests/test_seg_transition.py`

- [ ] **Step 1: Write the failing tests**

Cover:
- timeline generation for 4 regimes across a fixed frame count
- no wraparound to a fifth transition
- output folder naming helper

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest "06_AI Render Students/tests/test_seg_transition.py" -v`
Expected: FAIL because the animation module and helpers do not exist yet.

### Task 2: Implement the renderer extension and animation module

**Files:**
- Modify: `F:/Aworks/DF2026/python基础/DF26_ws18/06_AI Render Students/engine/massing.py`
- Create: `F:/Aworks/DF2026/python基础/DF26_ws18/06_AI Render Students/engine/seg_transition.py`

- [ ] **Step 1: Add renderer options**

Extend `render_massing(...)` so callers can control background color and whether the study boundary is drawn.

- [ ] **Step 2: Add the animation module**

Implement:
- pure helpers for frame scheduling and output directory naming
- regime rendering cache per frame
- per-frame PIL blending between adjacent regime renders
- rotating camera azimuth over the whole sequence
- final frame export into a dedicated output folder

- [ ] **Step 3: Run the focused tests**

Run: `python -m unittest "06_AI Render Students/tests/test_seg_transition.py" -v`
Expected: PASS

### Task 3: Add a simple command entrypoint and generate frames

**Files:**
- Modify: `F:/Aworks/DF2026/python基础/DF26_ws18/06_AI Render Students/run.py`

- [ ] **Step 1: Add a `seg-anim` command**

Wire `python run.py seg-anim [slug]` to the new module with the four configured regimes.

- [ ] **Step 2: Generate the requested output**

Run: `python "06_AI Render Students/run.py" seg-anim dapuqiao`
Expected: a new frame folder under `06_AI Render Students/out/dapuqiao/` containing the full sequence.
