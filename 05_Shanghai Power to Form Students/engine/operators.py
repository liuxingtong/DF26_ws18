"""
operators.py — 原子形态算子库(power 对 form 的「操作」)+ 配方引擎【进阶册】
=================================================================
主册「只调高度」只放开一个自由度;本库放开**形态语法**:权力改的是城市怎么长。
每个算子 = 纯函数 recs -> recs(recs 是 [{geom, h, sh, frozen}] 列表,几何 EPSG:32651 米)。
都参数可改、可单独演示(进阶 notebook 的算子图谱)。权力体制(regimes.yaml)= 这些算子的配方。
GFA 约定:某栋 GFA ∝ footprint面积 × 高度(量测时再 / 层高)。
教学要点:学生先学这 9 个操作,再学配方,再自己改 YAML / 复制粘贴换算子(见 算子替换指南.md)。
"""
import math
import numpy as np
import shapely.affinity as aff
from shapely.geometry import box
import common as C


def _aff(rec, target):
    """该 rec 是否被本算子作用:在 target 名单里且未冻结。"""
    return (rec["sh"] in target) and (not rec.get("frozen"))


def _scale(geom, area_ratio):
    f = math.sqrt(max(area_ratio, 1e-4))
    return aff.scale(geom, xfact=f, yfact=f, origin="centroid")


def _copy(recs):
    return [dict(r) for r in recs]


# ----------------------------------------------------------------- 9 个原子算子
def freeze(recs, who):
    """锁定:把 who 里的 stakeholder 标记为冻结,后续算子都跳过(state/遗产保护)。"""
    out = _copy(recs)
    for r in out:
        if r["sh"] in who:
            r["frozen"] = True
    return out


def weight_height(recs, weights, mode="conserve"):
    """按 stakeholder 权重重分配高度。conserve=总 GFA 守恒(只重分配);grow=只增。frozen 不动。"""
    out = _copy(recs)
    idx = [i for i, r in enumerate(out) if not r.get("frozen")]
    if not idx:
        return out
    w = np.array([float(weights.get(out[i]["sh"], 1.0)) for i in idx])
    a = np.array([out[i]["geom"].area for i in idx])
    h = np.array([out[i]["h"] for i in idx])
    if mode == "grow":
        for k, i in enumerate(idx):
            out[i]["h"] = h[k] * max(1.0, w[k])
        return out
    T = (a * h).sum(); S = (a * h * w).sum()
    if S <= 0:
        return out
    f = T / S
    for k, i in enumerate(idx):
        out[i]["h"] = max(h[k] * w[k] * f, 3.0)
    return out


def _center(recs, how):
    a = np.array([r["geom"].area for r in recs]); h = np.array([r["h"] for r in recs])
    cx = np.array([r["geom"].centroid.x for r in recs]); cy = np.array([r["geom"].centroid.y for r in recs])
    g = a * h
    if how == "state_centroid":
        m = np.array([r["sh"] == "state" for r in recs])
        if m.any() and g[m].sum() > 0:
            return float((cx[m] * g[m]).sum() / g[m].sum()), float((cy[m] * g[m]).sum() / g[m].sum())
    return float((cx * g).sum() / g.sum()), float((cy * g).sum() / g.sum())


def concentrate(recs, center="state_centroid", reach_frac=0.18, state_boost=2.0, cap_m=600.0, min_h=5.0):
    """中央集权:高度按到权力重心的距离收拢(守恒)。中心拔起、边缘让出。frozen 不动。"""
    out = _copy(recs)
    polys = [p for r in out for p in C._polys(r["geom"])]
    minx = min(p.bounds[0] for p in polys); maxx = max(p.bounds[2] for p in polys)
    miny = min(p.bounds[1] for p in polys); maxy = max(p.bounds[3] for p in polys)
    span = max(maxx - minx, maxy - miny)
    lam = reach_frac * span
    Px, Py = _center(out, center)
    idx = [i for i, r in enumerate(out) if not r.get("frozen")]
    a = np.array([out[i]["geom"].area for i in idx]); h = np.array([out[i]["h"] for i in idx])
    d = np.array([math.hypot(out[i]["geom"].centroid.x - Px, out[i]["geom"].centroid.y - Py) for i in idx])
    boost = np.array([state_boost if out[i]["sh"] == "state" else 1.0 for i in idx])
    w = boost * np.exp(-d / lam)
    T = (a * h).sum(); S = (a * h * w).sum()
    if S <= 0:
        return out
    f = T / S
    for k, i in enumerate(idx):
        out[i]["h"] = float(min(max(h[k] * w[k] * f, min_h), cap_m))
    out_center = (Px, Py, lam)
    for r in out:
        r["_center"] = out_center
    return out


def _towers(geom, k):
    """沿 OBB 长轴把 footprint 拆成 k 块(每块面积≈area/k,GFA 守恒由高度不变保证)。"""
    if k <= 1:
        return [geom]
    try:
        obb = geom.minimum_rotated_rectangle
        pts = list(obb.exterior.coords)[:4]
        e = [(pts[(i + 1) % 4][0] - pts[i][0], pts[(i + 1) % 4][1] - pts[i][1]) for i in range(4)]
        ln = [math.hypot(*v) for v in e]
        li = 0 if ln[0] >= ln[1] else 1
        L = ln[li] or 1.0
        ux, uy = e[li][0] / L, e[li][1] / L
        ang = math.degrees(math.atan2(e[li][1], e[li][0]))
        cx, cy = geom.centroid.coords[0]
        side = math.sqrt(max(geom.area / k, 1.0))
        half = max(L / 2 - side / 2, 0.0)
        offs = np.linspace(-half, half, k)
        out = []
        for o in offs:
            xk, yk = cx + ux * o, cy + uy * o
            sq = box(xk - side / 2, yk - side / 2, xk + side / 2, yk + side / 2)
            out.append(aff.rotate(sq, ang, origin=(xk, yk)))
        return out
    except Exception:
        return [geom]


def split_to_towers(recs, target, above_m2=1500, k=3):
    """拆板成塔:footprint > above_m2 的目标楼,沿长轴拆成 k 块(高度不变 → GFA 守恒)。"""
    out = []
    for r in recs:
        if _aff(r, target) and r["geom"].area > above_m2 and k > 1:
            for t in _towers(r["geom"], k):
                if t.is_valid and t.area > 1:
                    nr = dict(r); nr["geom"] = t; out.append(nr)
        else:
            out.append(dict(r))
    return out


def slim(recs, target, ratio=0.45):
    """塔化:footprint 向形心缩到 ratio 面积,高度 /ratio 补偿(单栋 GFA 守恒)→ 更细更高。"""
    out = _copy(recs)
    for r in out:
        if _aff(r, target):
            r["geom"] = _scale(r["geom"], ratio)
            r["h"] = r["h"] / ratio
    return out


def densify(recs, target, far_gain=1.8, cap_m=480.0):
    """加密:抬高度 = 加 GFA(footprint 不变)。"""
    out = _copy(recs)
    for r in out:
        if _aff(r, target):
            r["h"] = min(r["h"] * far_gain, cap_m)
    return out


def infill(recs, target, cell_m2=120, min_h=6, max_h=21, vary=0.35):
    """居民自建:把大 footprint 细分成自建小单元(细粒、低层、有机)。GFA 随高度走、不强求守恒。"""
    step = math.sqrt(cell_m2)
    out = []
    for r in recs:
        if not (_aff(r, target) and r["geom"].area > cell_m2 * 2):
            out.append(dict(r)); continue
        g = r["geom"]; b = g.bounds
        ci = 0; pieces = 0
        gx = b[0]
        while gx < b[2]:
            gy = b[1]
            while gy < b[3]:
                cell = box(gx, gy, gx + step, gy + step)
                piece = cell.intersection(g)
                if piece.area > cell_m2 * 0.28:
                    piece = piece.buffer(-step * 0.06)
                    for pp in C._polys(piece):
                        if pp.area < cell_m2 * 0.18:
                            continue
                        v = ((ci * 7 + 11) % 100) / 100.0
                        h = min_h + (max_h - min_h) * (0.5 + vary * (v - 0.5)) * (v)
                        h = max(min_h, min(h + min_h, max_h))
                        nr = dict(r); nr["geom"] = pp; nr["h"] = float(h); out.append(nr); pieces += 1
                ci += 1
                gy += step
            gx += step
        if pieces == 0:
            out.append(dict(r))
    return out


def level(recs, target, toward="median", alpha=0.6):
    """平权/趋同:目标楼高度向参考值靠拢。toward: median / p40 / 数值;alpha 强度(1=完全拉平)。"""
    out = _copy(recs)
    hs = [r["h"] for r in out if _aff(r, target)]
    if not hs:
        return out
    if toward == "median":
        ref = float(np.median(hs))
    elif isinstance(toward, str) and toward.startswith("p"):
        ref = float(np.percentile(hs, float(toward[1:])))
    else:
        ref = float(toward)
    for r in out:
        if _aff(r, target):
            r["h"] = r["h"] + alpha * (ref - r["h"])
    return out


def scale(recs, target, factor=2.0):
    """放大/缩小:把目标楼的 footprint 依「几何中心」线性缩放 factor 倍(高度不变)。
    factor=2 → 边长×2、footprint 面积×4(GFA 随面积×4,不守恒);<1 则缩小。"""
    out = _copy(recs)
    for r in out:
        if _aff(r, target):
            r["geom"] = aff.scale(r["geom"], xfact=factor, yfact=factor, origin="centroid")
    return out


def scale_graded(recs, target, center="global_centroid", factor=2.0, reach_frac=0.25, min_factor=1.0):
    """渐变放大:目标楼 footprint 依「到建筑中心点的距离」渐变缩放(高度不变)。
    近中心→接近 factor 倍;越远→衰减到 min_factor 倍。factor>1 放大、<1 缩小。
    GFA 随面积变(不守恒)。center: state_centroid=以 state 质心为中心;其它=全体 GFA 质心。
    reach_frac: 衰减尺度(占全域跨度的比例,越大范围越广)。"""
    out = _copy(recs)
    polys = [p for r in out for p in C._polys(r["geom"])]
    minx = min(p.bounds[0] for p in polys); maxx = max(p.bounds[2] for p in polys)
    miny = min(p.bounds[1] for p in polys); maxy = max(p.bounds[3] for p in polys)
    span = max(maxx - minx, maxy - miny)
    lam = max(reach_frac * span, 1e-6)
    Px, Py = _center(out, center)
    for r in out:
        if _aff(r, target):
            d = math.hypot(r["geom"].centroid.x - Px, r["geom"].centroid.y - Py)
            g = math.exp(-d / lam)                        # 1(中心)→ 0(远)
            f = min_factor + (factor - min_factor) * g    # 渐变缩放比
            r["geom"] = aff.scale(r["geom"], xfact=f, yfact=f, origin="centroid")
    return out


def open_ground(recs, target, ratio=0.6, cap_m=200.0):
    """共享/开放:缩私有 footprint 释放共享地面,高度 /ratio 补偿(GFA 守恒,但不激进塔化),封顶。"""
    out = _copy(recs)
    for r in out:
        if _aff(r, target):
            r["geom"] = _scale(r["geom"], ratio)
            r["h"] = min(r["h"] / ratio, cap_m)
    return out


# OPS：算子名 → 函数。加自己的算子时,在这里登记一行(见 算子替换指南.md)。
OPS = {"freeze": freeze, "weight_height": weight_height, "concentrate": concentrate,
       "split_to_towers": split_to_towers, "slim": slim, "densify": densify,
       "infill": infill, "level": level, "open_ground": open_ground, "scale": scale,
       "scale_graded": scale_graded}

# 自定义算子(engine/my_operator.py):与内置算子平权,可直接写进 regimes.yaml
import my_operator as _mo
taper = _mo.taper
linear_slab = _mo.linear_slab
courtyard_open = _mo.courtyard_open
uniform_cohort = _mo.uniform_cohort
twist = _mo.twist
freeze_tags = _mo.freeze_tags
micro_lease = _mo.micro_lease
frontage_quota = _mo.frontage_quota
crowd_valve = _mo.crowd_valve
night_reversion = _mo.night_reversion
OPS.update({
    "taper": taper,
    "linear_slab": linear_slab,
    "courtyard_open": courtyard_open,
    "uniform_cohort": uniform_cohort,
    "twist": twist,
    "freeze_tags": freeze_tags,
    "micro_lease": micro_lease,
    "frontage_quota": frontage_quota,
    "crowd_valve": crowd_valve,
    "night_reversion": night_reversion,
})


def register(name, fn):
    """运行时登记一个新算子(notebook 里复制粘贴自己的算子后调用,不必改本文件)。"""
    OPS[name] = fn


def apply_regime(recs, recipe):
    """按 recipe['steps'] 顺序施加算子。返回新 recs(不改原始)。"""
    cur = _copy(recs)
    for step in recipe["steps"]:
        op = OPS[step["op"]]
        kw = {k: v for k, v in step.items() if k not in ("op",)}
        cur = op(cur, **kw)
    return cur


def load_regimes(path=None):
    import yaml
    path = path or (C.ROOT / "regimes.yaml")
    return yaml.safe_load(open(path, encoding="utf-8"))
