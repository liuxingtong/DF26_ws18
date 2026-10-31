"""prints for 02 映射:谁算谁的 —— 查表规则 / 一栋怎么被判定 / 反事实前后 / 角色栋数。"""
import config
import common
from ._base import _say


def loaded(df):
    """载入回报(02 开头那行)。"""
    _say("载入 %d 栋  ·  %s" % (len(df), config.site_name()))


def lookup_rules(lk=None):
    """印 shanghai_lookup.yaml 的级联顺序 + EULUC 用途→权利方主表 + 预设值。"""
    lk = lk or common.load_lookup()
    _say("级联顺序:", lk["cascade"])
    _say("\nEULUC 用途 → 权利方(主键,政商可分):")
    for k, v in lk["euluc"].items():
        _say("   %-10s -> %s" % (k, v))
    _say("\n默认(都不中):", lk["default"], " · informal 不在表中(数据无信号 → 恒空)")


def assign_trace(df, n=6, lk=None):
    """走查:前 n 栋的多源栏位 → assign_stakeholder 判出哪个角色(看它在哪一级命中)。"""
    lk = lk or common.load_lookup()
    cols = [c for c in ["euluc", "function", "aoi_type2", "aoi_type1"] if c in df.columns]
    for _, r in df.head(n).iterrows():
        fields = {c: common._t(r.get(c)) for c in cols}
        _say("%-22s -> %s" % (str(fields), common.assign_stakeholder(r, lk)))


def counterfactual(res):
    """印 common.counterfactual() 的回传:把某用途改判后,分布改前/改后。"""
    _say("把『%s』从 %s 改判给 %s:" % (res["flip"], res["frm"], res["to"]))
    _say("  改前:", res["before"])
    _say("  改后:", res["after"])


def stakeholders(df, label="各角色栋数"):
    """各角色栋数(value_counts)。02/03 共用。"""
    _say("%s:" % label, df.stakeholder.value_counts().to_dict())
