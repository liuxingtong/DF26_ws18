"""Batch-run original vs wujiaochang scenario sets; save figures to separate out/ subfolders."""
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "engine"))

import common
import plots

_PRESETS = {
    "original": {
        "file": "power_scenarios_original.yaml",
        "compare": ["current", "community_led", "developer_renewal", "max_change"],
        "out_dir": "results_original",
    },
    "wujiaochang": {
        "file": "power_scenarios_wujiaochang.yaml",
        "compare": ["current", "developer_led", "community_led", "max_change"],
        "out_dir": "results_wujiaochang",
    },
}


def _save(fig, out_dir: Path, name: str, dpi: int = 120) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / name
    fig.savefig(path, dpi=dpi, bbox_inches="tight")
    plt.close(fig)
    return path


def run_preset(key: str, df) -> None:
    preset = _PRESETS[key]
    out_dir = common.OUT / preset["out_dir"]
    scen = common.load_scenarios(common.ROOT / preset["file"])
    names = preset["compare"]

    print("\n=== %s ===" % key)
    print("  yaml:", preset["file"])
    print("  compare:", names)
    print("  out:", out_dir.relative_to(common.ROOT))

    p = _save(plots.policy_heatmap(scen, show=False), out_dir, "policy_heatmap.png")
    print("  ->", p)

    heights = {n: common.scenario_heights(df, scen[n]) for n in names}

    p = _save(plots.skyline_panels(df, heights, names=names, show=False), out_dir, "skyline_panels.png")
    print("  ->", p)

    p = _save(plots.metrics(df, heights, names=names, show=False), out_dir, "metrics.png")
    print("  ->", p)


def main() -> None:
    import config
    print("PLACE =", config.PLACE)
    print("LAT/LON =", config.LAT, config.LON, "| RADIUS_M =", config.RADIUS_M)
    df = common.assign_all(common.current_buildings())
    print("buildings:", len(df))

    for key in _PRESETS:
        run_preset(key, df)

    print("\nDone. Images under out/results_original/ and out/results_wujiaochang/")


if __name__ == "__main__":
    main()
