"""Step2 图:角色著色图 + 各角色栋数/面积占比长条。df 需已有 'stakeholder' 栏。"""
import numpy as np
import matplotlib.pyplot as plt
import common
from . import _base


def power_map(df, show=True):
    """左:真实 footprint 依角色著色;右:栋数 / 面积占比小长条。"""
    order = common.STAKEHOLDERS
    counts = df["stakeholder"].value_counts()
    areas = df.groupby("stakeholder")["area_m2"].sum()
    n_by = np.array([int(counts.get(sh, 0)) for sh in order], float)
    a_by = np.array([float(areas.get(sh, 0.0)) for sh in order], float)
    n_share = n_by / n_by.sum() if n_by.sum() else n_by
    a_share = a_by / a_by.sum() if a_by.sum() else a_by

    fig, (ax_map, ax_bar) = plt.subplots(1, 2, figsize=(15, 8),
                                         gridspec_kw={"width_ratios": [3, 1]})
    _base.plot_footprints(ax_map, df, lambda r: _base.SH_COLOR[r["stakeholder"]])
    handles = [plt.Rectangle((0, 0), 1, 1, facecolor=_base.SH_COLOR[sh], edgecolor="white")
               for sh in order]
    labels = ["%s (%s, n=%d)" % (sh, _base.SH_LABEL[sh], int(n_by[i]))
              for i, sh in enumerate(order)]
    _base.legend_below(ax_map, handles, labels)

    y = np.arange(len(order)); bw = 0.38
    colors = [_base.SH_COLOR[sh] for sh in order]
    ax_bar.barh(y + bw / 2, n_share, height=bw, color=colors, edgecolor="white", label="Building share")
    ax_bar.barh(y - bw / 2, a_share, height=bw, color=colors, edgecolor="white",
                alpha=0.5, label="Area share")
    ax_bar.set_yticks(y)
    ax_bar.set_yticklabels([_base.SH_LABEL[sh] for sh in order], fontsize=8)
    ax_bar.invert_yaxis(); ax_bar.set_xlabel("Share")
    ax_bar.legend(loc="upper center", bbox_to_anchor=(0.5, -0.09), ncol=2, fontsize=8, frameon=False)

    _base.footer(fig, y=-0.005)
    fig.tight_layout(); fig.subplots_adjust(top=0.95, bottom=0.15)   # 下方装图例(非空白),footer 贴近
    _base.autosave(fig, "power_map")
    if show:
        plt.show()
    return fig
