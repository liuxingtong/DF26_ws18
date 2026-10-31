"""
engine/plots — 所有绘图(view 层)。notebook 只 import 这一个。
=================================================================
分工:
  common.py = model(算):载数据 / 贴角色 / 算高度 / 算子 / 挤 OBJ。
  plots/    = view(画):每个 step 一个图,共用核心在 _base。
  notebook  = controller(串):算交给 common/operators/measure,画交给 plots。

契约:plot func 只收「已算好的」df / heights / recs / scenarios,不重算、不读档。

主册(只调高度):
  plots.satellite_figureground(df)         # step0(需联网)
  plots.data_overview(df)                   # step1
  plots.power_map(df)                       # step2
  plots.policy_heatmap(scenarios)           # step3
  plots.skyline_panels(df, heights);  plots.metrics(df, heights)   # step4
  plots.city_3d(sub);  plots.city_3d_plotly(sub)                   # step5
进阶册(算子配方):
  plots.operator_demo(before, after, "拆板成塔")
  plots.regime_compare(before, after_by_regime, labels=...)
  plots.feature_bars(rows, labels=...)
"""
from ._base import (SH_COLOR, SH_LABEL, HEIGHT_CMAP,
                    plot_footprints, legend_below, height_norm, footer, save_fig,
                    origin_of, building_faces, capture, autosave)
from .step0_satellite import satellite_figureground
from .step1_data import data_overview
from .step2_power import power_map
from .step3_policy import policy_heatmap
from .step4_form import skyline_panels, metrics
from .step5_3d import city_3d, city_3d_plotly
from .operator_atlas import operator_demo, operator_diff, tag_map, regime_compare, feature_bars

__all__ = [
    "SH_COLOR", "SH_LABEL", "HEIGHT_CMAP",
    "plot_footprints", "legend_below", "height_norm", "footer", "save_fig",
    "origin_of", "building_faces", "capture", "autosave",
    "satellite_figureground", "data_overview", "power_map", "policy_heatmap",
    "skyline_panels", "metrics", "city_3d", "city_3d_plotly",
    "operator_demo", "operator_diff", "tag_map", "regime_compare", "feature_bars",
]
