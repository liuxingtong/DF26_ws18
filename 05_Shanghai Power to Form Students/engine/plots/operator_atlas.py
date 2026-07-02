"""算子图谱【进阶册】:把「权力算子」与「权力体制」画清楚。
  operator_demo(before, after, title)         — 单个算子的 before/after(教学核心:一个操作改了什么)
  regime_compare(before, after_by_regime)     — 现状 vs 各体制,同高度色阶,横向比形态
  feature_bars(rows)                           — 各体制的形态特征(瘦长/高度CV/重心集中/栋数)
工作单位是 recs 列表 [{geom,h,sh,frozen}](operators.py 的输出),不是 DataFrame。"""
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize
from matplotlib.cm import ScalarMappable
import common
from . import _base

HCMAP = _base.HEIGHT_CMAP
TAG_PRIORITY = [
    "relief_node",
    "night_quiet",
    "resident_return",
    "shared_frontage",
    "tourism_frontage",
    "local_service",
    "culture",
    "micro_shop",
    "heritage",
    "resident_gate",
    "residential_core",
    "emergency_access",
]
TAG_COLORS = {
    "relief_node": "#d94841",
    "night_quiet": "#6f4e7c",
    "resident_return": "#8c564b",
    "shared_frontage": "#f28e2b",
    "tourism_frontage": "#edc948",
    "local_service": "#59a14f",
    "culture": "#4e79a7",
    "micro_shop": "#76b7b2",
    "heritage": "#9c755f",
    "resident_gate": "#ff9da7",
    "residential_core": "#bab0ab",
    "emergency_access": "#e15759",
    "other": "#b8b8b8",
}
CHANGE_COLORS = {
    "geometry": "#d94841",
    "stakeholder": "#4e79a7",
    "tag": "#f28e2b",
    "height": "#59a14f",
    "frozen": "#9c755f",
    "added_or_removed": "#af7aa1",
}
CHANGE_LABELS = {
    "geometry": "Geometry changed",
    "stakeholder": "Stakeholder changed",
    "tag": "Tags changed",
    "height": "Height changed",
    "frozen": "Frozen state changed",
    "added_or_removed": "Added / removed records",
}


def _hnorm(*rec_lists):
    allh = np.concatenate([[r["h"] for r in rl] for rl in rec_lists]) if rec_lists else np.array([1.0])
    return Normalize(vmin=float(allh.min()), vmax=float(allh.max()))


def _panel(ax, recs, color_for, title):
    common.plot_footprints(ax, recs, color_for, lw=0.1)
    ax.set_title(title, fontsize=11)


def _record_changes(before_rec, after_rec, area_tol=1e-6, h_tol=1e-6):
    if before_rec is None or after_rec is None:
        return {"added_or_removed"}
    changes = set()
    if abs(before_rec["geom"].area - after_rec["geom"].area) > area_tol:
        changes.add("geometry")
    if abs(float(before_rec["h"]) - float(after_rec["h"])) > h_tol:
        changes.add("height")
    if before_rec.get("sh") != after_rec.get("sh"):
        changes.add("stakeholder")
    if tuple(before_rec.get("tags", [])) != tuple(after_rec.get("tags", [])):
        changes.add("tag")
    if bool(before_rec.get("frozen")) != bool(after_rec.get("frozen")):
        changes.add("frozen")
    return changes


def _change_kind(changes):
    for kind in ("geometry", "stakeholder", "tag", "height", "frozen", "added_or_removed"):
        if kind in changes:
            return kind
    return None


def change_summary(before, after, area_tol=1e-6, h_tol=1e-6):
    n = max(len(before), len(after))
    counts = {key: 0 for key in ("geometry", "height", "stakeholder", "tag", "frozen", "added_or_removed")}
    changed = []
    for i in range(n):
        b = before[i] if i < len(before) else None
        a = after[i] if i < len(after) else None
        changes = _record_changes(b, a, area_tol=area_tol, h_tol=h_tol)
        if not changes:
            continue
        changed.append({"index": i, "changes": changes, "kind": _change_kind(changes), "after": a, "before": b})
        for key in changes:
            counts[key] += 1
    return {
        "changed_count": len(changed),
        "geometry_count": counts["geometry"],
        "height_count": counts["height"],
        "stakeholder_count": counts["stakeholder"],
        "tag_count": counts["tag"],
        "frozen_count": counts["frozen"],
        "added_or_removed_count": counts["added_or_removed"],
        "changed": changed,
    }


def tag_category(rec):
    tags = set(rec.get("tags", []))
    for tag in TAG_PRIORITY:
        if tag in tags:
            return tag
    return "other"


def operator_demo(before, after, title="", color="sh", show=True):
    """单个算子的 before/after。color='sh' 按角色 / 'h' 按高度(同色阶)。"""
    has_cb = (color == "h")
    asp = _base.data_aspect(before)                        # figure 配到内容:panel 填满、无上下留白
    fig, (a0, a1), cax = _base.panel_grid(2, 1, asp, panel_w=5.0, wspace_in=0.22,
                                          title_in=(0.82 if title else 0.42), cbar=has_cb)
    if has_cb:
        norm = _hnorm(before, after)
        cf = lambda r: HCMAP(norm(r["h"]))
    else:
        cf = lambda r: _base.SH_COLOR[r["sh"]]
    _panel(a0, before, cf, "Before  |  n=%d  |  Mean %.1f m" % (len(before), np.mean([r["h"] for r in before])))
    _panel(a1, after, cf, "After  |  n=%d  |  Mean %.1f m" % (len(after), np.mean([r["h"] for r in after])))
    for ax in (a0, a1):
        ax.margins(0.01)                                 # 四周数据留白 5%→1%
    if title:
        fig.suptitle(_base.english_text(title), fontsize=13, y=0.99, va="top")
    if has_cb:
        sm = ScalarMappable(norm=norm, cmap=HCMAP); sm.set_array([])
        fig.colorbar(sm, cax=cax).set_label("Height (m)", fontsize=9)   # cax 高度 = subplots 同高
    _base.footer(fig)
    _base.autosave(fig, "operator_demo")
    if show:
        plt.show()
    return fig


def operator_diff(before, after, title="", show=True):
    """Highlight only the records changed by an operator, with change-type colors."""
    summary = change_summary(before, after)
    fig, ax = plt.subplots(1, 1, figsize=(9, 7))
    common.plot_footprints(ax, before, lambda _r: "#e6e6e6", lw=0.15)
    common.plot_footprints(ax, after, lambda _r: (1, 1, 1, 0.0), lw=0.0)
    changed_recs = [item["after"] for item in summary["changed"] if item["after"] is not None]
    kinds = [item["kind"] for item in summary["changed"] if item["after"] is not None]
    if changed_recs:
        common.plot_footprints(
            ax,
            changed_recs,
            lambda r, _m={id(rec): kind for rec, kind in zip(changed_recs, kinds)}: CHANGE_COLORS[_m[id(r)]],
            lw=0.2,
        )
    handles = []
    labels = []
    seen = []
    for kind in kinds:
        if kind and kind not in seen:
            seen.append(kind)
            handles.append(plt.Rectangle((0, 0), 1, 1, facecolor=CHANGE_COLORS[kind], edgecolor="white"))
            labels.append(CHANGE_LABELS[kind])
    if handles:
        _base.legend_below(ax, handles, labels, ncol=min(len(labels), 3), fontsize=8)
    head = _base.english_text(title) if title else "Operator diff"
    ax.set_title("%s\nChanged %d / %d records" % (head, summary["changed_count"], max(len(before), len(after))), fontsize=12)
    ax.margins(0.01)
    fig.tight_layout()
    fig.subplots_adjust(bottom=0.12)
    _base.autosave(fig, "operator_diff")
    if show:
        plt.show()
    return fig


def tag_map(recs, title="", show=True):
    """Color records by their most informative negotiated-space tag."""
    fig, ax = plt.subplots(1, 1, figsize=(9, 7))
    common.plot_footprints(ax, recs, lambda r: TAG_COLORS[tag_category(r)], lw=0.15)
    used = []
    for r in recs:
        cat = tag_category(r)
        if cat not in used:
            used.append(cat)
    handles = [plt.Rectangle((0, 0), 1, 1, facecolor=TAG_COLORS[tag], edgecolor="white") for tag in used]
    labels = [tag.replace("_", " ") for tag in used]
    if handles:
        _base.legend_below(ax, handles, labels, ncol=min(len(labels), 4), fontsize=8)
    ax.set_title(_base.english_text(title) if title else "Tag map", fontsize=12)
    ax.margins(0.01)
    fig.tight_layout()
    fig.subplots_adjust(bottom=0.14)
    _base.autosave(fig, "tag_map")
    if show:
        plt.show()
    return fig


def regime_compare(before, after_by_regime, names=None, labels=None,
                   ncols=2, pad=0.1, hpad=0.32, show=True):
    """现状 + 各体制,按**新高度**同色阶著色,一眼看权力长出的形态。
    自动 grid:ncols 列 × ceil(n/ncols) 行(默认 2 列)。
    pad=左右两 panel 空白(wspace),hpad=上下两 row 空白(hspace,需留双行标题)。"""
    names = names or list(after_by_regime.keys())
    seq = [("current", before)] + [(n, after_by_regime[n]) for n in names]
    norm = _hnorm(*[r for _, r in seq])
    cf = lambda r: HCMAP(norm(r["h"]))
    n = len(seq)
    ncols = max(1, min(ncols, n))
    nrows = int(np.ceil(n / ncols))
    asp = _base.data_aspect(before)                # figure 配到内容:每 panel 填满、无上下留白
    fig, axes, cax = _base.panel_grid(ncols, nrows, asp, panel_w=4.8,
                                      title_in=0.5, hspace_in=0.72, cbar=True)
    for ax, (name, recs) in zip(axes, seq):
        lab = _base.display_label((labels or {}).get(name, name))
        _panel(ax, recs, cf, "%s\nn=%d | Mean %.1f m" % (lab, len(recs), np.mean([r["h"] for r in recs])))
        ax.margins(0.01)                          # 每 panel 数据留白 5%→1%
    for ax in axes[n:]:                            # 多余格子(n 为奇数时最后一格)隐藏
        ax.set_visible(False)
    sm = ScalarMappable(norm=norm, cmap=HCMAP); sm.set_array([])
    fig.colorbar(sm, cax=cax).set_label(           # cax 高度 = 整片 subplots(跨全部 row)同高
        "Building height (m) — shared scale across regimes", fontsize=10)
    _base.footer(fig)
    _base.autosave(fig, "regime_compare")
    if show:
        plt.show()
    return fig


def feature_bars(rows, labels=None, show=True):
    """rows = measure.compare(...) 的第一个返回值。画 4 个特征指标的体制对照。"""
    names = list(rows.keys())
    lab = ["Current" if n == "current" else _base.display_label((labels or {}).get(n, n)) for n in names]
    metrics = [("slender", "Slenderness (tower tendency)"), ("h_cv", "Height CV (centralization)"),
               ("concentration", "Centroid concentration"), ("n", "Building count (fine grain)")]
    fig, axs = plt.subplots(2, 2, figsize=(14, 9))
    palette = ["#888888", "#c0654a", "#4a6fa5", "#5a9367", "#c2a23c"]
    x = np.arange(len(names))
    for ax, (key, title) in zip(axs.ravel(), metrics):
        vals = [rows[n][key] for n in names]
        ax.bar(x, vals, color=[palette[i % len(palette)] for i in range(len(names))])
        ax.set_title(title, fontsize=12)
        ax.set_xticks(x); ax.set_xticklabels(lab, rotation=14, fontsize=9)
        for i, v in enumerate(vals):
            ax.text(i, v, ("%.2f" % v) if key != "n" else ("%d" % v),
                    ha="center", va="bottom", fontsize=9)
    fig.suptitle("Power regimes → quantified morphological signatures", fontsize=13)
    fig.tight_layout(); fig.subplots_adjust(top=0.92)
    _base.autosave(fig, "feature_bars")
    if show:
        plt.show()
    return fig
