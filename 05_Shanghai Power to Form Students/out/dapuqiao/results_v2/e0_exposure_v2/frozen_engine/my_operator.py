"""
my_operator.py —— 你的算子练习场(复制粘贴模板 + 曹杨新村情境算子)
=================================================================
配套「算子替换指南.md」。内置 taper 示例 + 3 个面向工人新村(曹杨)的形态算子:
  linear_slab     沿长轴拉长板楼(沿街接建,GFA 守恒)
  courtyard_open  缩 footprint 释出大院(温和版 open_ground)
  uniform_cohort  单位制均质高度(同期建造感)

用法(在进阶 notebook 里):
    import operators as ops, my_operator as mo
    ops.register("linear_slab", mo.linear_slab)   # 已在 operators.py 永久登记,通常不必再 register
"""
import math
import random
import shapely.affinity as aff
from shapely.geometry import box


def taper(recs, target, keep=0.7, cap_m=300.0):
    """示例算子「收分塔」:footprint 缩到 keep 面积、高度按 1/keep 补偿(单栋 GFA 守恒)。"""
    out = [dict(r) for r in recs]
    f = max(keep, 1e-3) ** 0.5
    for r in out:
        if r["sh"] in target and not r.get("frozen"):
            r["geom"] = aff.scale(r["geom"], xfact=f, yfact=f, origin="centroid")
            r["h"] = min(r["h"] / max(keep, 1e-3), cap_m)
    return out


def linear_slab(recs, target, stretch=1.25, cap_m=42.0):
    """沿 OBB 长轴拉长 footprint、高度 /stretch 补偿(GFA 守恒)——工人新村板楼沿街接建。"""
    out = [dict(r) for r in recs]
    for r in out:
        if r["sh"] not in target or r.get("frozen"):
            continue
        geom = r["geom"]
        try:
            obb = geom.minimum_rotated_rectangle
            pts = list(obb.exterior.coords)[:4]
            e = [(pts[(i + 1) % 4][0] - pts[i][0], pts[(i + 1) % 4][1] - pts[i][1]) for i in range(4)]
            ln = [math.hypot(*v) for v in e]
            li = 0 if ln[0] >= ln[1] else 1
            ang = math.degrees(math.atan2(e[li][1], e[li][0]))
            cx, cy = geom.centroid.coords[0]
            g2 = aff.rotate(geom, -ang, origin=(cx, cy))
            g2 = aff.scale(g2, xfact=stretch, yfact=1.0, origin=(cx, cy))
            r["geom"] = aff.rotate(g2, ang, origin=(cx, cy))
            r["h"] = min(r["h"] / max(stretch, 1e-3), cap_m)
        except Exception:
            pass
    return out


def courtyard_open(recs, target, ratio=0.75, cap_m=36.0):
    """缩私有 footprint 释出大院共享地面、高度 /ratio 补偿(GFA 守恒)——比 open_ground 更温和,适合低层工人新村。"""
    out = [dict(r) for r in recs]
    f = max(ratio, 1e-3) ** 0.5
    for r in out:
        if r["sh"] in target and not r.get("frozen"):
            r["geom"] = aff.scale(r["geom"], xfact=f, yfact=f, origin="centroid")
            r["h"] = min(r["h"] / max(ratio, 1e-3), cap_m)
    return out


def uniform_cohort(recs, target, band_m=18.0, spread=2.0):
    """单位制均质:目标楼高度拉到 band_m±spread——工人新村同期建造、整齐划一。"""
    out = [dict(r) for r in recs]
    for i, r in enumerate(out):
        if r["sh"] in target and not r.get("frozen"):
            v = ((i * 7 + 11) % 100) / 100.0
            r["h"] = band_m + (v - 0.5) * 2 * spread
    return out


def twist(recs, target, deg=18):
    """旋转 footprint(示范算子)——可用于里弄/新村有机扭转。"""
    out = [dict(r) for r in recs]
    for r in out:
        if r["sh"] in target and not r.get("frozen"):
            r["geom"] = aff.rotate(r["geom"], deg, origin="centroid")
    return out


# ---- 打浦桥 / 田子坊:24 小时协商弄堂算子 ---------------------------------
def _copy_with_tags(recs):
    """复制 recs,并补上面向打浦桥教学情境的可协商空间标签。"""
    out = []
    for i, r in enumerate(recs):
        nr = dict(r)
        tags = set(nr.get("tags", []))
        sh = nr.get("sh")
        if sh == "resident":
            tags.update(["residential_core"])
            if i % 5 == 0:
                tags.add("resident_gate")
        elif sh == "state":
            tags.update(["emergency_access"])
        elif sh == "developer":
            tags.update(["tourism_frontage", "commercial"])
            if nr["geom"].area < 220:
                tags.add("micro_shop")
            if i % 7 == 0:
                tags.add("culture")
        if nr["geom"].area < 180 and sh in ("resident", "developer"):
            tags.add("heritage")
        nr["tags"] = sorted(tags)
        out.append(nr)
    return out


def _has_any_tag(rec, tags):
    have = set(rec.get("tags", []))
    return any(t in have for t in tags)


def _scale_area(rec, ratio, cap_m=None):
    ratio = max(float(ratio), 1e-3)
    f = ratio ** 0.5
    rec["geom"] = aff.scale(rec["geom"], xfact=f, yfact=f, origin="centroid")
    rec["h"] = rec["h"] / ratio
    if cap_m is not None:
        rec["h"] = min(rec["h"], cap_m)
    return rec


def _site_axis(recs):
    xs = [r["geom"].centroid.x for r in recs]
    ys = [r["geom"].centroid.y for r in recs]
    minx, maxx = min(xs), max(xs)
    miny, maxy = min(ys), max(ys)
    spanx, spany = maxx - minx, maxy - miny
    cx, cy = (minx + maxx) / 2, (miny + maxy) / 2
    if spanx >= spany:
        return "x", cx, cy, max(spanx, 1.0)
    return "y", cx, cy, max(spany, 1.0)


def _dist_to_spine(rec, axis):
    orient, _cx, cy, _span = axis
    c = rec["geom"].centroid
    return abs(c.y - cy) if orient == "x" else abs(c.x - _cx)


def freeze_tags(recs, tags):
    """按空间标签冻结:历史里弄、居住核心、消防通道等后续不再被改写。"""
    out = _copy_with_tags(recs)
    for r in out:
        if _has_any_tag(r, tags):
            r["frozen"] = True
    return out


def micro_lease(recs, target, above_m2=500, cell_m2=80, affordable_ratio=0.35,
                local_service_ratio=0.20, culture_ratio=0.15, min_h=6, max_h=18, seed=42):
    """微租赁:把大商业体量拆成小单元,分配给低租金经营、居民服务与文化展示。"""
    rng = random.Random(seed)
    step = math.sqrt(cell_m2)
    out = []
    for r in _copy_with_tags(recs):
        if r["sh"] not in target or r.get("frozen") or r["geom"].area <= above_m2:
            out.append(r)
            continue
        g = r["geom"]
        b = g.bounds
        pieces = []
        gx = b[0]
        while gx < b[2]:
            gy = b[1]
            while gy < b[3]:
                piece = box(gx, gy, gx + step, gy + step).intersection(g)
                if piece.area > cell_m2 * 0.25:
                    piece = piece.buffer(-step * 0.04)
                    if piece.is_valid and piece.area > cell_m2 * 0.12:
                        pieces.append(piece)
                gy += step
            gx += step
        if not pieces:
            out.append(r)
            continue
        rng.shuffle(pieces)
        n = len(pieces)
        for i, piece in enumerate(pieces):
            nr = dict(r)
            nr["geom"] = piece
            v = ((i * 13 + seed) % 100) / 100.0
            nr["h"] = float(min_h + (max_h - min_h) * v)
            tags = set(nr.get("tags", []))
            q = i / max(n, 1)
            if q < affordable_ratio:
                tags.update(["affordable_micro", "micro_shop"])
                nr["sh"] = "developer"
            elif q < affordable_ratio + local_service_ratio:
                tags.update(["local_service", "micro_shop"])
                nr["sh"] = "resident"
            elif q < affordable_ratio + local_service_ratio + culture_ratio:
                tags.update(["culture", "micro_shop"])
                nr["sh"] = "state"
            else:
                tags.update(["tourism_frontage", "micro_shop"])
            nr["tags"] = sorted(tags)
            out.append(nr)
    return out


def frontage_quota(recs, primary_routes="tourist_spine", frontage_buffer_m=8,
                   max_tourism_ratio=0.45, min_local_service_ratio=0.15,
                   min_micro_shop_ratio=0.25, min_culture_ratio=0.15, seed=42):
    """界面配额:游客主线两侧不让旅游消费界面独占,保留居民服务、小店和文化展示。"""
    out = _copy_with_tags(recs)
    axis = _site_axis(out)
    frontage = [i for i, r in enumerate(out) if _dist_to_spine(r, axis) <= frontage_buffer_m]
    if not frontage:
        return out
    rng = random.Random(seed)
    rng.shuffle(frontage)
    n = len(frontage)
    targets = {
        "local_service": int(math.ceil(n * min_local_service_ratio)),
        "micro_shop": int(math.ceil(n * min_micro_shop_ratio)),
        "culture": int(math.ceil(n * min_culture_ratio)),
    }
    cursor = 0
    for tag, count in targets.items():
        for idx in frontage[cursor:cursor + count]:
            if out[idx].get("frozen"):
                continue
            tags = set(out[idx].get("tags", []))
            tags.add(tag)
            if tag == "local_service":
                out[idx]["sh"] = "resident"
            elif tag == "culture":
                out[idx]["sh"] = "state"
            out[idx]["tags"] = sorted(tags)
        cursor += count
    tourism = [i for i in frontage if "tourism_frontage" in out[i].get("tags", [])]
    allowed = int(math.floor(n * max_tourism_ratio))
    for idx in tourism[allowed:]:
        if not out[idx].get("frozen"):
            tags = set(out[idx].get("tags", []))
            tags.discard("tourism_frontage")
            tags.add("shared_frontage")
            out[idx]["tags"] = sorted(tags)
    return out


def crowd_valve(recs, route="tourist_spine", crowd_threshold=0.75,
                one_way_links=True, protect_tags=None, relief_nodes=3):
    """客流阀门:高峰时压缩游客主线商业占用,为疏散节点和消防通行让出地面。"""
    protect_tags = protect_tags or []
    out = _copy_with_tags(recs)
    if crowd_threshold < 0.5:
        return out
    axis = _site_axis(out)
    candidates = [r for r in out if not r.get("frozen")
                  and not _has_any_tag(r, protect_tags)
                  and "tourism_frontage" in r.get("tags", [])
                  and _dist_to_spine(r, axis) <= 18]
    candidates.sort(key=lambda r: r["geom"].area, reverse=True)
    for i, r in enumerate(candidates):
        tags = set(r.get("tags", []))
        if i < relief_nodes:
            _scale_area(r, 0.72, cap_m=24)
            tags.add("relief_node")
        else:
            _scale_area(r, 0.90, cap_m=30)
        if one_way_links:
            tags.add("one_way_alley")
        r["tags"] = sorted(tags)
    return out


def night_reversion(recs, start_hour=22, quiet_buffer_m=10,
                    commercial_shutdown_ratio=0.60, protect_tags=None):
    """夜间归还:22 点后将靠近居住核心的部分消费界面降噪、收摊并归还通行。"""
    protect_tags = protect_tags or []
    out = _copy_with_tags(recs)
    residents = [r for r in out if _has_any_tag(r, ["residential_core", "resident_gate"])]
    if not residents:
        return out
    for r in out:
        if r.get("frozen") or _has_any_tag(r, protect_tags):
            continue
        if "commercial" not in r.get("tags", []) and "tourism_frontage" not in r.get("tags", []):
            continue
        c = r["geom"].centroid
        near = any(c.distance(rr["geom"].centroid) <= quiet_buffer_m for rr in residents)
        if not near:
            continue
        tags = set(r.get("tags", []))
        tags.update(["night_quiet", "resident_return"])
        r["tags"] = sorted(tags)
        keep = max(1.0 - commercial_shutdown_ratio, 0.15)
        _scale_area(r, keep, cap_m=18)
        r["h"] = max(r["h"] * keep, 3.0)
    return out


if __name__ == "__main__":
    import sys, pathlib
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
    import config, common as C, operators as ops
    df = C.assign_all(C.current_buildings(config.SLUG))
    recs = C.to_recs(df)
    after = linear_slab(recs, target=["resident"], stretch=1.2)
    import numpy as np
    print("linear_slab 自测 OK | before 平均高 %.1f → after %.1f | 栋数 %d→%d" % (
        np.mean([r["h"] for r in recs]), np.mean([r["h"] for r in after]), len(recs), len(after)))
