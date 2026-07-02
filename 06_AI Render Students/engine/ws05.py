"""接入隔壁 05 的引擎(不重复数据/算子/形态逻辑)。
把 05 根(config.py)和 05/engine 加进 sys.path,设好 05 的 config.SLUG,暴露给 07。
07 总开关命名 settings.py 而非 config.py,避免和 05 的 config 撞名。"""
import sys
from pathlib import Path
import importlib
# 确保能找到 07 的 settings.py
_07ROOT = Path(__file__).resolve().parent.parent
if str(_07ROOT) not in sys.path:
    sys.path.insert(0, str(_07ROOT))
import settings   # 07 总开关

WS05 = Path(settings.WS05).resolve()
_ENGINE = WS05 / "engine"
for p in (str(WS05), str(_ENGINE)):     # 根+engine 都要在路径上
    if p not in sys.path:
        sys.path.insert(0, p)

import config as ws05_config            # 05 的 config.py
import common as C                       # 05 引擎:缓存/角色/高度/recs/OBJ
import operators as ops                  # 05 引擎:9 算子+配方
import measure as M                      # 05 引擎:形态指纹
import plots                             # 05 引擎:绘图


def use_site(slug=None):
    """切到某站点(设好 05 的 config.SLUG)。返回 slug。"""
    slug = slug or settings.SLUG
    ws05_config.SLUG = slug
    importlib.reload  # noqa 占位:config 模块级状态
    return slug


def load_recs(slug=None):
    """读某站点楼宇 recs 列表 [{geom,h,sh,frozen}]。"""
    slug = use_site(slug)
    df = C.assign_all(C.current_buildings(slug))
    return C.to_recs(df), df


def regime_recs(slug=None, regimes=None):
    """对某站点施加各权力体制,得 {regime: recs}(current=现状基线)。"""
    regimes = regimes or settings.REGIMES
    recs, _ = load_recs(slug)
    regs = ops.load_regimes(WS05 / "regimes.yaml")
    out = {}
    for name in regimes:
        out[name] = recs if name == "current" else ops.apply_regime(recs, regs[name])
    return out, regs


def counterfactual_recs(slug=None, scenarios=None):
    """对某站点施加高度反事实情景,得 {scenario: recs}(footprint 不变,只换 h)。"""
    scenarios = scenarios or getattr(settings, "COUNTERFACTUAL_SCENARIOS", [])
    if not scenarios:
        return {}, {}
    slug = use_site(slug)
    df = C.assign_all(C.current_buildings(slug))
    scen = C.load_scenarios()
    out = {}
    for name in scenarios:
        d = df.copy()
        if name != "current":
            d["height_m"] = C.scenario_heights(d, scen[name]).values
        out[name] = C.to_recs(d)
    return out, scen


def counterfactual_label(scenarios, name):
    labels = {
        "current": "现状",
        "tourism_capture": "旅游流量资本主导",
        "everyday_life_first": "居民安全与日常生活优先",
        "heritage_micro_economy": "遗产与小商户共生",
        "negotiated_24h_alley": "24小时协商弄堂",
        "developer_led": "开发商主导",
        "community_led": "社区主导",
        "state_eco": "国家生态",
        "developer_renewal": "开发更新增量",
    }
    return labels.get(name, name)


def load_context_recs(slug=None):
    """读某站点周边语境 recs（透明语境层，供 canny/depth/massing 的 ControlNet 语境）。
    无 context.parquet 则回 []。frozen=True、in_study=0、sh='context'（不参与算子/形态度量）。"""
    slug = use_site(slug)
    df = C.load_context(slug)
    if df is None or len(df) == 0:
        return []
    recs = []
    for _, r in df.iterrows():
        recs.append({"geom": r["geom"], "h": float(r["height_m"]), "sh": "context",
                     "area": float(r.get("area_m2", r["geom"].area)), "frozen": True, "in_study": 0})
    return recs


def regime_label(regs, name):
    return "现状" if name == "current" else regs.get(name, {}).get("label", name)
