"""Step4 图:套情景只调高度的新形态。
  skyline_panels(df, heights) — N 连幅 footprints,同色阶(可横比)。
  metrics(df, heights)       — 2×2:总 GFA / 平均高 / 最高 / 各角色平均高。
heights = {情景名: 逐栋新高度 Series}(由 common.scenario_heights 算好传入)。"""
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.cm import ScalarMappable
import common
from . import _base


def skyline_panels(df, heights, names=None, show=True):
    names = names or list(heights.keys())
    norm = _base.height_norm(*[heights[n] for n in names])

    a = _base.data_aspect(df)                           # figure 配到内容:消掉等比留白
    ncols = 2 if len(names) > 1 else 1                   # 2×2 排列(4 情景)
    nrows = int(np.ceil(len(names) / ncols))
    fig, axes, cax = _base.panel_grid(ncols, nrows, a, cbar=True, hspace_in=0.66)
    for ax, name in zip(axes, names):
        h = heights[name]
        hmap = dict(zip(df.index, h.values))
        _base.plot_footprints(ax, df, color_for=lambda r, _m=hmap: _base.HEIGHT_CMAP(norm(_m[r.name])))
        ax.set_title("%s\nMean %.1f m | Max %.0f m" % (_base.display_label(name), h.mean(), h.max()), fontsize=11)
    for ax in axes[len(names):]:                         # 多余格子隐藏(情景数非偶数时)
        ax.set_visible(False)
    sm = ScalarMappable(norm=norm, cmap=_base.HEIGHT_CMAP); sm.set_array([])
    fig.colorbar(sm, cax=cax).set_label(                # cax 高度 = subplots 全高
        "Building height (m) — shared scale across panels", fontsize=10)
    _base.footer(fig)
    _base.autosave(fig, "skyline_panels")
    if show:
        plt.show()
    return fig


def metrics(df, heights, names=None, show=True):
    names = names or list(heights.keys())
    base_gfa = float((df.area_m2 * heights[names[0]] / common.FLOOR_H).sum())
    gfa_x, mean_h, max_h = [], [], []
    for name in names:
        h = heights[name]
        gfa_x.append(float((df.area_m2 * h / common.FLOOR_H).sum()) / base_gfa)
        mean_h.append(float(h.mean())); max_h.append(float(h.max()))

    by_sh = {}
    for sh in common.STAKEHOLDERS:
        mask = (df["stakeholder"] == sh).values
        if not mask.any():
            continue
        by_sh[sh] = {name: float(heights[name].values[mask].mean()) for name in names}

    fig, axs = plt.subplots(2, 2, figsize=(15, 10))
    x = np.arange(len(names))
    palette = ["#888888", "#c0654a", "#5a9367", "#4a6fa5"]
    cols = [palette[i % len(palette)] for i in range(len(names))]

    axs[0, 0].bar(x, gfa_x, color=cols); axs[0, 0].axhline(1.0, ls="--", lw=1, color="k")
    display_names = [_base.display_label(name) for name in names]

    axs[0, 0].set_title("Total GFA × baseline")
    for i, v in enumerate(gfa_x):
        axs[0, 0].text(i, v, "×%.2f" % v, ha="center", va="bottom", fontsize=10)
    axs[0, 1].bar(x, mean_h, color=cols); axs[0, 1].set_title("Mean height (m)")
    for i, v in enumerate(mean_h):
        axs[0, 1].text(i, v, "%.1f" % v, ha="center", va="bottom", fontsize=10)
    axs[1, 0].bar(x, max_h, color=cols); axs[1, 0].set_title("Max height (m)")
    for i, v in enumerate(max_h):
        axs[1, 0].text(i, v, "%.0f" % v, ha="center", va="bottom", fontsize=10)
    for ax in (axs[0, 0], axs[0, 1], axs[1, 0]):
        ax.set_xticks(x); ax.set_xticklabels(display_names, rotation=12)

    n_sh = len(by_sh); w = 0.8 / max(n_sh, 1)
    for k, (sh, d) in enumerate(by_sh.items()):
        axs[1, 1].bar(x + (k - (n_sh - 1) / 2) * w, [d[n] for n in names], width=w,
                      color=_base.SH_COLOR[sh], label=_base.SH_LABEL[sh])
    axs[1, 1].set_title("Mean height by stakeholder (m)")
    axs[1, 1].set_xticks(x); axs[1, 1].set_xticklabels(display_names, rotation=12)
    axs[1, 1].legend(loc="upper center", bbox_to_anchor=(0.5, -0.12),
                     ncol=max(n_sh, 1), fontsize=8, frameon=False)

    fig.tight_layout(); fig.subplots_adjust(bottom=0.12)
    _base.autosave(fig, "metrics")
    if show:
        plt.show()
    return fig
