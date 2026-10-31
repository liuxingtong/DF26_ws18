"""prints for 04 进阶:权力算子 —— 算子清单 / 体制配方 / 形态特征 / 自订算子登记确认。
（档名 power_ops 避免和 engine/operators.py 混淆;函式内才 import operators 模型层。)"""
import config
from ._base import _say


def op_list(recs):
    """站点 + 栋数 + 9 个算子的清单(power 对 form 的『操作』)。"""
    import operators as ops
    _say("%s · %d 栋。算子清单:" % (config.site_name(), len(recs)))
    _say("  ", list(ops.OPS.keys()))


def regimes(regs=None):
    """印 regimes.yaml:每种权力体制的形态特征 + 算子配方(按序串起的操作)。"""
    import operators as ops
    regs = regs or ops.load_regimes()
    for name, r in regs.items():
        _say("【%s】%s" % (r["label"], r.get("feature", r.get("fingerprint", ""))))
        _say("   配方:", " → ".join(s["op"] for s in r["steps"]))


def features(rows, labels=None):
    """印 measure.compare() 的形态特征表(瘦长 / 高度CV / 重心集中 / 栋数)。"""
    labels = labels or {}
    for n, m in rows.items():
        _say("  %-20s 瘦长 %.2f · 高度CV %.2f · 重心集中 %.2f · 栋数 %d" %
             (labels.get(n, n), m["slender"], m["h_cv"], m["concentration"], m["n"]))


def registered(name):
    """确认自订算子已登记进 OPS(和内建 9 个平权)。"""
    import operators as ops
    _say("现在 OPS 里多了:", name in ops.OPS)
