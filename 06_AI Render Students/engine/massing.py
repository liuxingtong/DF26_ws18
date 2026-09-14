"""
Render massing views for the 06 AI workflow.

This keeps the existing role of the module intact:
- load 05-generated regime geometry
- render a fixed-camera 3D massing view
- optionally include the OSM/satellite ground image

The renderer now also supports:
- custom background colors
- hiding the study boundary
- stable precomputed axis limits so long frame sequences do not trip 3D autoscaling
"""
from pathlib import Path
import warnings

warnings.filterwarnings("ignore")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

import settings
import ws05


ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "out"


def _bounds(recs):
    polys = [poly for rec in recs for poly in ws05.C._polys(rec["geom"])]
    minx = min(poly.bounds[0] for poly in polys)
    miny = min(poly.bounds[1] for poly in polys)
    maxx = max(poly.bounds[2] for poly in polys)
    maxy = max(poly.bounds[3] for poly in polys)
    return minx, miny, maxx, maxy


def study_rect(minx, miny, maxx, maxy, frac):
    cx, cy = (minx + maxx) / 2, (miny + maxy) / 2
    hw, hh = (maxx - minx) * frac / 2, (maxy - miny) * frac / 2
    return cx - hw, cy - hh, cx + hw, cy + hh


def _ground_texture(sx0, sy0, sx1, sy1, slug, factor=1.0):
    from PIL import Image

    cache = OUT / slug / "ground_scene.jpg"
    _, local = ws05.C.ground_sat(sx0, sy0, sx1, sy1, cache, factor=factor)
    arr = np.asarray(Image.open(cache).convert("RGB"))
    return arr, local


def _finite_faces(faces):
    for face in faces:
        for point in face:
            if len(point) != 3:
                return False
            if not all(np.isfinite(value) for value in point):
                return False
    return True


def _hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))


def _rgb_to_hex(rgb):
    return "#{:02x}{:02x}{:02x}".format(*[max(0, min(255, int(round(v)))) for v in rgb])


def _resolve_facecolor(rec, color):
    if color != "sh":
        return "#c9c4bd"
    if rec.get("sh", "").startswith("mix:"):
        from_color = _hex_to_rgb(ws05.C.SH_COLOR.get(rec.get("sh_from"), "#999999"))
        to_color = _hex_to_rgb(ws05.C.SH_COLOR.get(rec.get("sh_to"), "#999999"))
        mix = float(rec.get("mix", 0.0))
        rgb = tuple((1.0 - mix) * a + mix * b for a, b in zip(from_color, to_color))
        return _rgb_to_hex(rgb)
    return ws05.C.SH_COLOR.get(rec["sh"], "#999999")


def render_massing(
    recs,
    path,
    color="mono",
    cam=None,
    dpi=None,
    zmax=None,
    title=None,
    ground=None,
    slug=None,
    context_recs=None,
    background="#ffffff",
    show_study_outline=True,
    figure_size_px=None,
):
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection

    cam = cam or settings.CAM
    dpi = dpi or settings.MASSING_DPI
    slug = slug or settings.SLUG
    context_recs = context_recs or []

    tagged = [(rec, True) for rec in recs] + [(rec, False) for rec in context_recs]
    allrecs = [item[0] for item in tagged]
    minx, miny, maxx, maxy = _bounds(allrecs)
    ox, oy = minx, miny
    xmax, ymax = maxx - ox, maxy - oy
    zmax = zmax or max((rec["h"] for rec in allrecs), default=1) * 1.05

    if figure_size_px:
        width_px, height_px = figure_size_px
        figsize = (width_px / dpi, height_px / dpi)
    else:
        figsize = (9, 7)

    fig = plt.figure(figsize=figsize, facecolor=background)
    ax = fig.add_subplot(111, projection="3d", computed_zorder=False)
    ax.set_facecolor(background)
    fig.subplots_adjust(left=0, right=1, bottom=0, top=1)
    ax.set_autoscale_on(False)
    ax.set_xlim(0, xmax)
    ax.set_ylim(0, ymax)
    ax.set_zlim(0, zmax)

    if ground == "sat":
        try:
            arr, local = _ground_texture(minx, miny, maxx, maxy, slug, factor=1.0)
            step = max(1, max(arr.shape[:2]) // 300)
            tex = (arr[::step, ::step] / 255.0)[::-1]
            ny, nx = tex.shape[:2]
            gx0, gy0, gx1, gy1 = local[0], local[1], local[2], local[3]
            xs = np.linspace(gx0, gx1, nx)
            ys = np.linspace(gy0, gy1, ny)
            X, Y = np.meshgrid(xs, ys)
            Z = np.zeros_like(X)
            ax.plot_surface(
                X,
                Y,
                Z,
                rstride=1,
                cstride=1,
                facecolors=tex,
                shade=False,
                linewidth=0,
                antialiased=False,
                zorder=0,
            )
        except Exception as exc:
            print("  ground skipped:", exc)

    azim_rad = np.radians(cam["azim"])
    ca, sa = np.cos(azim_rad), np.sin(azim_rad)

    def _depth(rec):
        centroid = rec["geom"].centroid
        return centroid.x * ca + centroid.y * sa

    order = sorted(range(len(tagged)), key=lambda idx: _depth(tagged[idx][0]))

    for zorder_index, idx in enumerate(order):
        rec, is_study = tagged[idx]
        h = float(rec["h"])
        if not is_study:
            h = min(h, zmax)
        facecolor = _resolve_facecolor(rec, color) if is_study else "#c9c4bd"
        alpha = 1.0 if is_study else 0.22
        edgecolor = "#6f6a63" if is_study else "#a8a29a"
        faces = ws05.plots.building_faces(rec["geom"], h, ox, oy)
        if not faces or not _finite_faces(faces):
            continue
        collection = Poly3DCollection(
            faces,
            facecolor=facecolor,
            edgecolor=edgecolor,
            linewidths=0.06,
            alpha=alpha,
            zorder=2 + zorder_index,
        )
        ax.add_collection3d(collection)

    if show_study_outline:
        rings = ws05.C.study_poly_rings(slug)
        if rings:
            for ring in rings:
                ax.plot(
                    [point[0] - ox for point in ring],
                    [point[1] - oy for point in ring],
                    zs=0,
                    zdir="z",
                    color="#e02424",
                    linewidth=2.0,
                    zorder=10**6,
                )
        else:
            smnx, smny, smxx, smxy = _bounds(recs)
            ax.plot(
                [smnx - ox, smxx - ox, smxx - ox, smnx - ox, smnx - ox],
                [smny - oy, smny - oy, smxy - oy, smxy - oy, smny - oy],
                zs=0,
                zdir="z",
                color="#e02424",
                linewidth=2.0,
                zorder=10**6,
            )

    vexag = 4.0
    ax.set_box_aspect((xmax, ymax, max(zmax * vexag, xmax * 0.06)))
    ax.view_init(elev=cam["elev"], azim=cam["azim"])
    ax.set_axis_off()
    if title:
        ax.set_title(title, fontsize=12)

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    save_kwargs = {"dpi": dpi, "facecolor": background}
    if not figure_size_px:
        save_kwargs["bbox_inches"] = "tight"
    fig.savefig(path, **save_kwargs)
    plt.close(fig)
    return path


def massing_for_regimes(slug=None, regimes=None, color="mono", ext="jpg", ground="sat"):
    slug = slug or settings.SLUG
    regimes = regimes or settings.REGIMES
    regime_recs, _ = ws05.regime_recs(slug, regimes)
    context_recs = ws05.load_context_recs(slug)
    zmax = max(max((rec["h"] for rec in recs), default=1) for recs in regime_recs.values()) * 1.05
    out = {}
    for name, recs in regime_recs.items():
        out_path = OUT / slug / f"massing_{name}.{ext}"
        render_massing(
            recs,
            out_path,
            color=color,
            zmax=zmax,
            ground=ground,
            slug=slug,
            context_recs=context_recs,
        )
        out[name] = out_path
        print("  ->", out_path.relative_to(ROOT))
    return out


if __name__ == "__main__":
    import sys

    target_slug = sys.argv[1] if len(sys.argv) > 1 else settings.SLUG
    print(f"== massing reference: {target_slug} ==")
    massing_for_regimes(target_slug)
    print("done")
