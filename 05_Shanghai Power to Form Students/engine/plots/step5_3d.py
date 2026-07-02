"""Step5 图:真实 footprint 挤成 3D 量体。
  city_3d(sub)        — matplotlib,程式码定角度(elev/azim)。
  city_3d_plotly(sub) — plotly,浏览器里滑鼠拖动旋转(回传 fig,自行 .show()/.write_html())。
sub 需有 'stakeholder' 与高度栏(预设 'height_m';可传 height_col 指定情景高度)。"""
import inspect
import numpy as np
import matplotlib.pyplot as plt
import common
from . import _base


def city_3d(sub, height_col="height_m", elev=30, azim=-60, top=None, show=True):
    """top 不为 None 时,只取占地最大的 top 栋画预览(几千栋时 matplotlib 才不卡)。"""
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    sub = sub[np.isfinite(sub[height_col].astype(float))]     # 丢掉高度 NaN/Inf 的楼
    if top is not None and len(sub) > top:
        sub = sub.sort_values("area_m2", ascending=False).head(top)
    ox, oy = _base.origin_of(sub)

    fig = plt.figure(figsize=(11, 7.5))
    ax = fig.add_subplot(111, projection="3d")
    # 新版 mpl(3.9+):add_collection3d 每次都急着 autoscale,边界一旦出现 NaN/Inf 就
    # ValueError: Axis limits cannot be NaN or Inf。传 autolim=False 关掉,改用下方显式 set_*lim。
    no_autolim = "autolim" in inspect.signature(ax.add_collection3d).parameters
    for _, r in sub.iterrows():
        faces = _base.building_faces(r["geom"], float(r[height_col]), ox, oy)
        pts = [c for f in faces for c in f]
        if not pts or not np.isfinite(np.asarray(pts, dtype=float)).all():
            continue                                          # 跳过含 NaN/Inf 的退化量体
        pc = Poly3DCollection(faces, facecolor=_base.SH_COLOR[r["stakeholder"]],
                              edgecolor="white", linewidths=0.1, alpha=0.92)
        ax.add_collection3d(pc, autolim=False) if no_autolim else ax.add_collection3d(pc)
    xmax = max(p.bounds[2] for g in sub["geom"] for p in common._polys(g)) - ox
    ymax = max(p.bounds[3] for g in sub["geom"] for p in common._polys(g)) - oy
    hmax = float(sub[height_col].max())
    ax.set_xlim(0, xmax); ax.set_ylim(0, ymax); ax.set_zlim(0, hmax * 1.1)
    ax.set_box_aspect((xmax, ymax, max(hmax, 1) * 4))   # z 拉高,量体才明显
    ax.set_xlabel("x (m)"); ax.set_ylabel("y (m)"); ax.set_zlabel("Height (m)")
    ax.view_init(elev=elev, azim=azim)

    handles = [plt.Rectangle((0, 0), 1, 1, facecolor=_base.SH_COLOR[s]) for s in common.STAKEHOLDERS]
    ax.legend(handles, [_base.SH_LABEL[s] for s in common.STAKEHOLDERS], loc="upper center",
              bbox_to_anchor=(0.5, -0.06), ncol=len(common.STAKEHOLDERS), fontsize=8, frameon=False)
    fig.tight_layout()
    _base.autosave(fig, "city_3d")
    if show:
        plt.show()
    return fig


def city_3d_plotly(sub, height_col="height_m"):
    import plotly.graph_objects as go
    from shapely.ops import triangulate
    ox, oy = _base.origin_of(sub)

    traces = []
    for sh in common.STAKEHOLDERS:
        rows = sub[sub["stakeholder"] == sh]
        if len(rows) == 0:
            continue
        X, Y, Z, I, J, K = [], [], [], [], [], []
        for _, r in rows.iterrows():
            h = float(r[height_col])
            for poly in common._polys(r["geom"]):
                ring = list(poly.exterior.coords)
                if len(ring) > 1 and ring[0] == ring[-1]:
                    ring = ring[:-1]
                n = len(ring)
                if n < 3:
                    continue
                base = len(X)
                for (x, y) in ring:                 # 底环
                    X.append(x - ox); Y.append(y - oy); Z.append(0.0)
                for (x, y) in ring:                 # 顶环
                    X.append(x - ox); Y.append(y - oy); Z.append(h)
                for i in range(n):                  # 墙:每边两个三角形
                    j = (i + 1) % n
                    b0, b1 = base + i, base + j
                    t0, t1 = base + n + i, base + n + j
                    I += [b0, b0]; J += [b1, t1]; K += [t1, t0]
                for tri in triangulate(poly):       # 顶盖:三角化(滤掉落在外面的)
                    if not poly.contains(tri.representative_point()):
                        continue
                    tc = list(tri.exterior.coords)[:3]
                    a = len(X)
                    for (x, y) in tc:
                        X.append(x - ox); Y.append(y - oy); Z.append(h)
                    I.append(a); J.append(a + 1); K.append(a + 2)
        if X:
            traces.append(go.Mesh3d(x=X, y=Y, z=Z, i=I, j=J, k=K,
                                    color=_base.SH_COLOR[sh], opacity=1.0,
                                    name=_base.SH_LABEL[sh], showlegend=True, flatshading=True))

    fig = go.Figure(data=traces)
    fig.update_layout(
        scene=dict(xaxis_title="x (m)", yaxis_title="y (m)", zaxis_title="Height (m)",
                   aspectmode="manual", aspectratio=dict(x=1.6, y=1.6, z=0.9)),
        legend=dict(orientation="h", yanchor="top", y=0, xanchor="center", x=0.5),
        margin=dict(l=0, r=0, t=0, b=0))
    return fig
