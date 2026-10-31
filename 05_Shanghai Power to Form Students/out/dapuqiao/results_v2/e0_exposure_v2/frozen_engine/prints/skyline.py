"""prints for 03 城市天际线 —— 站点摘要 / 可选步骤略过 / 可用情景 / OBJ 写档回报。"""
import config
import common
from ._base import _say


def headline(df):
    """站点一行摘要:名称 · 栋数 · 最高。"""
    _say("%s · %d 栋 · 最高 %.0fm" % (config.site_name(), len(df), float(df["height_m"].max())))


def skipped(what, e):
    """某个需联网/额外套件的步骤失败时的友善略过(如 step0 卫星)。"""
    _say("跳过%s(没网或缺 contextily):" % what, e)


def scenarios(scen):
    """印可用的权力情景名单(power_scenarios.yaml 的 key)。"""
    _say("可用情景:", list(scen.keys()))


def obj_written(path, nv, nf):
    """common.export_obj() 之后的回报:写到哪、几个顶点/面。"""
    _say("OBJ 写到 %s  · verts %d faces %d" % (path.relative_to(common.ROOT), nv, nf))
