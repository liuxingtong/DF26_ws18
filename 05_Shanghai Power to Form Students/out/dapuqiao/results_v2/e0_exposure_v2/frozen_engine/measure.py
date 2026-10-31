"""
measure.py — 形态诊断【进阶册】:让每个体制的「形态特征」可量化、可比较
=================================================================
对一组 recs 算一套指标;对比 现状 vs 各体制,就能读出每种权力的形态规律。
  far 容积率 · coverage 覆盖率 · n 栋数 · h_mean/h_max 高度 · h_cv 高度不均(集权↑)
  grain 中位 footprint(细粒↓)· slender 瘦长比 中位(塔化↑)
  concentration 重心 λ 内 GFA 占比(集权↑;用现状的重心+λ 作固定参照)
"""
import math
import numpy as np
import common as C


def ref_center(recs, reach_frac=0.18):
    """现状的权力重心(政府/公共 GFA 加权质心)+ λ —— 作为前后对比的固定参照。"""
    a = np.array([r["geom"].area for r in recs]); h = np.array([r["h"] for r in recs])
    cx = np.array([r["geom"].centroid.x for r in recs]); cy = np.array([r["geom"].centroid.y for r in recs])
    g = a * h
    m = np.array([r["sh"] == "state" for r in recs])
    if m.any() and g[m].sum() > 0:
        Px, Py = float((cx[m] * g[m]).sum() / g[m].sum()), float((cy[m] * g[m]).sum() / g[m].sum())
    else:
        Px, Py = float((cx * g).sum() / g.sum()), float((cy * g).sum() / g.sum())
    polys = [p for r in recs for p in C._polys(r["geom"])]
    minx = min(p.bounds[0] for p in polys); maxx = max(p.bounds[2] for p in polys)
    miny = min(p.bounds[1] for p in polys); maxy = max(p.bounds[3] for p in polys)
    return Px, Py, reach_frac * max(maxx - minx, maxy - miny)


def diagnose(recs, slug=None, center=None):
    site = C.site_meta(slug)["area_km2"] * 1e6
    a = np.array([r["geom"].area for r in recs]); h = np.array([r["h"] for r in recs])
    gfl = a * h / C.FLOOR_H
    Px, Py, lam = center if center else ref_center(recs)
    d = np.array([math.hypot(r["geom"].centroid.x - Px, r["geom"].centroid.y - Py) for r in recs])
    near = d <= lam
    return {
        "n": len(recs), "far": float(gfl.sum() / site), "coverage": float(a.sum() / site),
        "h_mean": float(h.mean()), "h_max": float(h.max()), "h_cv": float(h.std() / h.mean()),
        "grain": float(np.median(a)), "slender": float(np.median(h / np.sqrt(a))),
        "concentration": float(gfl[near].sum() / gfl.sum()),
    }


def compare(before, after_by_regime, slug=None):
    """现状 + 各体制 的指标表(dict of dict),重心参照固定为现状的。"""
    ctr = ref_center(before)
    rows = {"current": diagnose(before, slug, ctr)}
    for name, recs in after_by_regime.items():
        rows[name] = diagnose(recs, slug, ctr)
    return rows, ctr
