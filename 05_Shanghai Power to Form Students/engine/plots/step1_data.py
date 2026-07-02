"""Step1 图:灰 footprints(还没贴角色)+ 实测高度直方图。
上海版 height_source 全是 measured_ai(AI影像解译-带高度,实测),不再是 OSM 的 levels×3.5 估算——
所以这里直接画实测高度分布,并标出 >100m 的真超高层 token(OSM/新加坡版没有的东西)。"""
import numpy as np
import matplotlib.pyplot as plt
from . import _base


def data_overview(df, show=True):
    """左:真实 footprints 全灰;右:实测高度分布(标平均、p90、>100m 超高层)。"""
    h = df["height_m"].astype(float)
    fig, (axL, axR) = plt.subplots(1, 2, figsize=(15, 7))

    _base.plot_footprints(axL, df, color_for=lambda r: "#9a9a9a")
    axL.set_title("Building Footprints (gray: geometry only, before stakeholder mapping)", fontsize=12)

    hi = int(h.max())
    bins = range(0, hi + 8, max(3, hi // 80 * 3 or 3))
    axR.hist(h, bins=bins, color="#4a6fa5", label="Measured height (measured_ai)")
    n_hi = int((h > 100).sum())
    if n_hi:
        axR.hist(h[h > 100], bins=bins, color="#c0654a", label="Super-tall >100 m ×%d" % n_hi)
    axR.axvline(h.mean(), color="#222", ls="--", lw=1.2, label="Mean %.1f m" % h.mean())
    axR.axvline(h.quantile(.9), color="#5a9367", ls=":", lw=1.2, label="P90 %.1f m" % h.quantile(.9))
    axR.set_xlabel("Height (m)  |  Max %.0f m" % h.max()); axR.set_ylabel("Building count")
    axR.set_title("Measured Height Distribution (AI-derived, not floor-count estimates)", fontsize=12)
    axR.legend(loc="upper right", fontsize=9, frameon=False)

    _base.footer(fig, y=-0.005)
    fig.tight_layout(); fig.subplots_adjust(top=0.92, bottom=0.10)   # 下方留白≈上方
    _base.autosave(fig, "data_overview")
    if show:
        plt.show()
    return fig
