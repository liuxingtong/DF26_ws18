"""
engine/prints — notebook 里所有「文字回报」的单一入口(view 层:只印人话,不算数据)。
=================================================================
契约:每个 prints.* 只收「已算好的」df / res / recs,负责印成人话;算是 common/operators 的事。
notebook 只 `import prints`,就能拿到下面所有函式(这个档把各分册的函式摊平到 prints.*)。

分册:
  data       01 数据    : spine_paths / prepared / coverage
  mapping    02 映射    : loaded / lookup_rules / assign_trace / counterfactual / stakeholders
  skyline    03 天际线  : headline / skipped / scenarios / obj_written
  power_ops  04 进阶    : op_list / regimes / features / registered
共用:_base.ready(setup 就绪回报)· _base._say(印字底座)。
"""
from ._base import ready
from .data import spine_paths, prepared, coverage
from .mapping import loaded, lookup_rules, assign_trace, counterfactual, stakeholders
from .skyline import headline, skipped, scenarios, obj_written
from .power_ops import op_list, regimes, features, registered

__all__ = [
    "ready",
    "spine_paths", "prepared", "coverage",
    "loaded", "lookup_rules", "assign_trace", "counterfactual", "stakeholders",
    "headline", "skipped", "scenarios", "obj_written",
    "op_list", "regimes", "features", "registered",
]
