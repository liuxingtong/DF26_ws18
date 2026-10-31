"""prints for 01 数据:怎么选、怎么拼 —— 看一眼数据集状态 / 拼好的表 / 多源覆盖率。"""
import config
import common
from ._base import _say


def spine_paths():
    """看 5 个 spine 档的路径、以及你机器上有没有(没有 = 还没下数据集,用随包缓存即可)。"""
    for k, p in common.dataset_paths().items():
        _say("%-4s %s  ->  %s" % (k, "有" if p.exists() else "无", p))
    _say("\nDATASET_ROOT =", config.DATASET_ROOT, " (None = 用随包缓存,离线)")


def prepared(df, source):
    """common.build_or_load() 之后的回报。source='cache' 时提醒是走随包缓存。"""
    if source == "cache":
        _say("未设 DATASET_ROOT(或数据集不在)→ 用随包缓存。想自己建:见 数据集说明.md")
    _say("拼好了:%d 栋  ·  %s" % (len(df), config.site_name()))


def coverage(df):
    """看一眼多源覆盖率(euluc/function)+ 前 8 栋的多源栏。"""
    show = [c for c in ["height_m", "euluc", "function", "aoi_type2", "aoi_type1"] if c in df.columns]
    _say("覆盖率:")
    for c in ["euluc", "function"]:
        if c in df.columns:
            _say("  %-9s %.0f%%" % (c, df[c].apply(common._t).ne("").mean() * 100))
    _say("\n样例(前 8 栋的多源列):")
    _say(df[show].head(8).to_string())
