"""Step0 图:先看真实的地方 —— Esri 卫星 + figure-ground(footprint 依 stakeholder 著色)。
上海版几何已是 EPSG:32651;卫星底用 contextily 抓 Esri World Imagery(需联网)。零 AI。
诚实:卫星为 Esri 公开底图(年份依其更新);footprint/权利为多源离散读法。"""
import warnings; warnings.filterwarnings("ignore")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
import common
from . import _base


def _bbox_3857(df, utm=common.UTM, pad=0.06):
    import pyproj
    from shapely.ops import transform as shp_transform
    to3857 = pyproj.Transformer.from_crs(utm, 3857, always_xy=True).transform
    xs, ys = [], []
    for g in df["geom"]:
        for p in common._polys(shp_transform(to3857, g)):
            x0, y0, x1, y1 = p.bounds
            xs += [x0, x1]; ys += [y0, y1]
    w, e, s, n = min(xs), max(xs), min(ys), max(ys)
    dx, dy = (e - w) * pad, (n - s) * pad
    return (w - dx, e + dx, s - dy, n + dy)


def _draw_footprints(ax, df, utm=common.UTM, alpha=.62):
    import pyproj
    from shapely.ops import transform as shp_transform
    to3857 = pyproj.Transformer.from_crs(utm, 3857, always_xy=True).transform
    for _, r in df.iterrows():
        for p in common._polys(shp_transform(to3857, r["geom"])):
            xs, ys = p.exterior.xy
            ax.fill(xs, ys, facecolor=_base.SH_COLOR[r["stakeholder"]], alpha=alpha,
                    edgecolor="white", linewidth=.12)


def _legend(ax):
    handles = [Patch(fc=_base.SH_COLOR[sh], label=_base.SH_LABEL[sh].split("(")[0])
               for sh in common.STAKEHOLDERS]
    ax.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, -0.02),
              ncol=len(handles), fontsize=8, frameon=False)


def satellite_figureground(df, utm=common.UTM, zoom=16, show=True):
    """三连幅:纯卫星 / figure-ground(角色著色)/ 叠图。需 contextily + 联网;失败请跳过。"""
    import contextily as ctx
    ext = _bbox_3857(df, utm)
    img, iext = ctx.bounds2img(ext[0], ext[2], ext[1], ext[3], source=ctx.providers.Esri.WorldImagery, zoom=zoom)

    A = (ext[3] - ext[2]) / (ext[1] - ext[0])            # 影像 高/宽 比 → figure 配到内容,消上下留白
    pw = 6.4                                             # 单幅宽(英寸)
    fig, axes = plt.subplots(1, 3, figsize=(3 * pw + 0.8, pw * A + 1.5))
    axes[0].imshow(img, extent=iext); axes[0].set_title("1. Real Satellite Imagery (Esri)", fontsize=12)
    axes[1].set_facecolor("white"); _draw_footprints(axes[1], df, utm, alpha=1.0)
    axes[1].set_title("2. Figure-Ground by Stakeholder", fontsize=12); _legend(axes[1])
    axes[2].imshow(img, extent=iext, alpha=.92); _draw_footprints(axes[2], df, utm, alpha=.6)
    axes[2].set_title("3. Overlay: Imagery + Discrete Reading", fontsize=12); _legend(axes[2])
    for ax in axes:
        ax.set_xlim(ext[0], ext[1]); ax.set_ylim(ext[2], ext[3]); ax.set_aspect("equal"); ax.axis("off")
    _base.footer(fig, y=-0.005)
    fig.tight_layout(); fig.subplots_adjust(top=0.93, bottom=0.13)   # 下方留白≈上方
    _base.autosave(fig, "satellite_figureground")
    if show:
        plt.show()
    return fig
