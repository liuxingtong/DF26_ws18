"""Local, single-user recomputation service for the Dapuqiao canvas."""

from __future__ import annotations

import json
import math
import sys
import threading
import time
from dataclasses import replace
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import build_canvas
import ws05


WS05 = ws05.WS05
sys.path.insert(0, str(WS05))
from engine.optimization.data import CONFIG_ROOT, load_study, load_yaml  # noqa: E402
from engine.optimization.nsga2 import run_nsga2  # noqa: E402
from engine.optimization.roles import evaluate_roles  # noqa: E402

sys.path.insert(0, str(WS05 / "scripts"))
from run_dapuqiao_optimization import export_run  # noqa: E402


SCENARIOS = {"public_coordination", "development_growth", "resident_heritage_priority"}
BOUNDS = {
    "minimum_residential_retention": (0.5, 1.0),
    "maximum_changed_building_ratio": (0.01, 1.0),
    "height_limit_m": (10.0, 200.0),
    "max_far": (0.1, 10.0),
    "max_coverage_ratio": (0.01, 1.0),
}
state = {"state": "idle", "message": "Ready"}
lock = threading.Lock()


def validate(payload):
    if not isinstance(payload, dict) or payload.get("scenario") not in SCENARIOS:
        raise ValueError("Choose one of the three current governance scenarios")
    values = payload.get("values")
    if not isinstance(values, dict) or set(values) != set(BOUNDS):
        raise ValueError("All five settings are required")
    clean = {}
    for key, (lower, upper) in BOUNDS.items():
        value = values[key]
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not lower <= value <= upper:
            raise ValueError(f"{key} must be between {lower} and {upper}")
        clean[key] = float(value)
    return payload["scenario"], clean


def run(scenario, values):
    try:
        study = load_study(scenario, shared_experiment_controls=True)
        if study.blockers:
            raise RuntimeError("; ".join(study.blockers))
        scenario_config = dict(study.scenario)
        scenario_config["defaults"] = {**scenario_config.get("defaults", {}), **{
            key: values[key] for key in ("minimum_residential_retention", "height_limit_m", "max_far", "max_coverage_ratio")
        }}
        scenario_config["implementation"] = {**scenario_config.get("implementation", {}),
            "maximum_changed_building_ratio": values["maximum_changed_building_ratio"]}
        scenario_config["interactive_settings"] = values
        controls = study.controls.copy()
        for key in ("height_limit_m", "max_far", "max_coverage_ratio"):
            controls[key] = values[key]
        study = replace(study, scenario=scenario_config, controls=controls)
        with lock:
            state.update(state="running", message="Running NSGA-II with the selected settings…")
        operators = load_yaml(CONFIG_ROOT / "operator_specs.yaml").get("operators", {})
        candidates, front, metadata = run_nsga2(study, operators, population=20, generations=20, seed=11)
        roles = load_yaml(CONFIG_ROOT / "role_profiles.yaml")
        role_rows, selections = evaluate_roles(front, roles, study.objective_config.get("epsilon", {}))
        stamp = time.strftime("%Y%m%d_%H%M%S")
        output = WS05 / "out" / "dapuqiao" / "optimization" / f"{scenario}__interactive_{stamp}"
        export_run(study, candidates, front, role_rows, selections, seed=11, samples=0,
                   search_metadata=metadata, output_dir=output)
        (output / "interactive_settings.json").write_text(
            json.dumps({"scenario": scenario, "values": values, "status": "new_interactive_run"},
                       ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        with lock:
            state.update(state="running", message="Updating 3D solutions…")
        build_canvas.build("dapuqiao")
        with lock:
            state.update(state="complete", message=f"New run complete: {output.name}")
    except Exception as exc:
        with lock:
            state.update(state="error", message=f"Recomputation failed: {exc}")


def serve(port=8765):
    build_canvas.build("dapuqiao")
    canvas = build_canvas.OUT / "dapuqiao" / "canvas.html"

    class Handler(BaseHTTPRequestHandler):
        def respond(self, code, value):
            body = json.dumps(value, ensure_ascii=False).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if self.path.startswith("/api/status"):
                with lock:
                    self.respond(200, dict(state))
            elif self.path in ("/", "/canvas.html"):
                body = canvas.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            else:
                self.send_error(404)

        def do_POST(self):
            if self.path != "/api/recalculate":
                self.send_error(404)
                return
            try:
                size = int(self.headers.get("Content-Length", "0"))
                if size > 8192:
                    raise ValueError("Request is too large")
                scenario, values = validate(json.loads(self.rfile.read(size)))
            except (ValueError, TypeError, json.JSONDecodeError) as exc:
                self.respond(400, {"error": str(exc)})
                return
            with lock:
                if state["state"] == "running":
                    self.respond(409, {"error": "A run is already in progress"})
                    return
                state.update(state="running", message="Loading frozen research inputs…")
            threading.Thread(target=run, args=(scenario, values), daemon=True).start()
            self.respond(202, {"state": "running"})

    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"Canvas: http://127.0.0.1:{port}/")
    server.serve_forever()
