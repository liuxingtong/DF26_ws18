"""
common.py — 上海:本地多源真实数据 → 离散权利 → (只调高度 / 算子配方) → 新形态(共用契约)
=================================================================
回应最初论文的方法,跑**上海本地多源真实数据**(不是 OSM)。本层负责:
  1 选地   subdistrict(name)              街道多边形(非方形、变大小)
  2 裁切   build_cache / load_buildings   AI实测高度 footprint 裁到街道 + 多源 join
  3 权利   assign_all(级联查表)           一栋 = 一个 stakeholder(EULUC→Function→AOI)
  4 高度   scenario_heights               只调高度(conserve 守恒 / grow 只增)      ← 主册
  （5 算子  operators.py / measure.py      原子算子的配方 → 形态特征                ← 进阶册）
  通用     extrude_obj / plot_footprints / ground_sat(挤体、绘图、卫星底)

两条取数据的路(见 config.py / 数据集说明.md):
  A. 离线(默认):随包带 3 站缓存 data/<slug>/buildings.parquet,不需联网、不需原始数据集。
  B. 自己建(进阶):config.DATASET_ROOT 指向你下载解压的「上海城市数据集」,build_cache() 从
     5 个 spine 文件(街道边界 × AI建筑-带高度 × EULUC × 带年份Function × 百度AOI)裁切+join 重建缓存。

纯 Python:geopandas + shapely + pandas + pyyaml。零 AI、零语意转换。
诚实:① informal 本数据无信号 → 该类保留但恒为空(不无中生有);② AI 高度对极端超高层(>~340m)可能低估;
      ③ AOI 价格/结构仅作离散 tag、不外发原值;④ EULUC 为地块(面)级、优先于建筑级 Function,
      故居住地块内零星公建会被并入「居民」——简化,非产权考证。danwei(工人新村)用途=居住→算居民,只有形态记得它是单位建的。
"""
from pathlib import Path
import warnings
warnings.filterwarnings("ignore")
import numpy as np
import pandas as pd
import yaml
import geopandas as gpd
from shapely.geometry import Polygon, MultiPolygon
from shapely.ops import triangulate
import matplotlib
from matplotlib import font_manager as _fm
# 注意:不在 import 时切后端,好让 notebook inline 显示;当 script 跑才切 Agg。
# 中文字型:**先确认机器上真的有**再选(否则会变成豆腐方块)。Windows/Mac/Linux 都覆盖。
def _set_cjk_font():
    avail = {f.name for f in _fm.fontManager.ttflist}
    for f in ("Microsoft YaHei", "Microsoft JhengHei", "SimHei",          # Windows(学生多用)
              "PingFang SC", "Arial Unicode MS", "Hiragino Sans GB",       # macOS
              "Heiti TC", "STHeiti", "Noto Sans CJK SC", "WenQuanYi Zen Hei"):  # 其余/Linux
        if f in avail:
            matplotlib.rcParams["font.sans-serif"] = [f]
            matplotlib.rcParams["axes.unicode_minus"] = False
            return f
    return None
_set_cjk_font()
import config  # 唯一的总开关:SLUG / DATASET_ROOT / SITES(学生主要改 config.py)

ENGINE = Path(__file__).resolve().parent     # engine/(程式码,学生不用进)
ROOT = ENGINE.parent                          # 包根:data/ out/ config.py *.yaml *.ipynb 都在这
DATA = ROOT / "data"
OUT = ROOT / "out"
LOOKUP_PATH = ROOT / "shanghai_lookup.yaml"
SCEN_PATH = ROOT / "power_scenarios.yaml"
UTM = 32651
FLOOR_H = 3.5

STAKEHOLDERS = ["state", "developer", "resident", "informal", "unknown"]
SH_LABEL = {"state": "State / Public", "developer": "Developer / Capital", "resident": "Residents",
            "informal": "Informal (no signal in this dataset)", "unknown": "Unknown / Unmatched"}
SH_COLOR = {"state": "#4a6fa5", "developer": "#c0654a", "resident": "#5a9367",
            "informal": "#c2a23c", "unknown": "#b8b8b8"}


# --------------------------------------------------------- 数据集路径(从 config.DATASET_ROOT 实时解析)
def dataset_root():
    """学生下载解压的「上海城市数据集」根目录(config.DATASET_ROOT 实时读;reload(config) 后即更新)。
    未填则回退到项目本地的 data_collection/上海城市数据集(开发者机器才有;学生机一般没有)。"""
    if getattr(config, "DATASET_ROOT", None):
        return Path(config.DATASET_ROOT)
    return ROOT.parent.parent / "data_collection" / "上海城市数据集"   # 开发者本地回退


# 5 个 spine 文件「干净布局」的相对路径(末段文件名是唯一锚点)。
_SPINE_REL = {
    "JD":  "03-行政区/2其他/乡镇街道/上海市_乡镇边界.shp",
    "AI":  "01-建筑轮廓/②AI解析/上海市_建筑-AI影像解译-带高度.shp",
    "EU":  "09-开源土地利用/09-开源土地利用/开源建设用地分类/Data/上海市-开源建设用地.shp",
    "FN":  "01-建筑轮廓/③其它/上海市_建筑-带年份-内测版.shp",
    "AOI": "02-POI&AOI/2-AOI/AOI-baiduapi/SHP/上海市_AOI.shp",
}


def _resolve_spine(src, rel):
    """先按干净布局的相对路径命中;落空就在 src 下按文件名递归找(应付解压出的同名外层目录,
    如每个分类各被压进一层同名文件夹 01-建筑轮廓/01-建筑轮廓/…)。挑路径最短、非「补充图层」副本的那个。
    都找不到则回传 canonical 路径(.exists()=False,让上层报清楚的缺文件错)。"""
    p = src / rel
    if p.exists():
        return p
    hits = [h for h in src.rglob(Path(rel).name) if h.is_file()]
    hits = [h for h in hits if "补充图层" not in str(h)] or hits
    return min(hits, key=lambda q: len(str(q))) if hits else p


def dataset_paths():
    """5 个 spine 文件路径。建缓存时用,见 数据集说明.md。对解压出的同名外层目录布局自动容错。"""
    src = dataset_root()
    return {k: _resolve_spine(src, rel) for k, rel in _SPINE_REL.items()}


# --------------------------------------------------------- 3 离散权利(级联查表)
def load_lookup(path=LOOKUP_PATH):
    return yaml.safe_load(open(path, encoding="utf-8"))


def _t(v):
    """正规化 tag 值:nan/none/空 → 「无」。"""
    if v is None:
        return ""
    s = str(v).strip()
    return "" if s.lower() in ("nan", "none", "") else s


def assign_stakeholder(row, lk):
    """级联离散:按 lk['cascade'] 顺序(euluc→function→aoi),第一个来源给出映射即定。
    一栋 = 一个 stakeholder。informal 永不在此被指派(数据无信号),保留作恒空类。"""
    for src in lk["cascade"]:
        if src == "euluc":
            m = lk["euluc"].get(_t(row.get("euluc")))
            if m:
                return m
        elif src == "function":
            m = lk["function"].get(_t(row.get("function")))
            if m and m != "unknown":
                return m
        elif src == "aoi":
            for field in ("aoi_type2", "aoi_type1", "aoi_type"):
                v = _t(row.get(field))
                if v:
                    for kw, sh in lk["aoi_contains"].items():
                        if kw in v:
                            return sh
    return lk.get("default", "unknown")


def assign_all(df, lookup=None):
    """加 'stakeholder' 栏(改 shanghai_lookup.yaml 可变这步)。"""
    lookup = lookup or load_lookup()
    df = df.copy()
    df["stakeholder"] = df.apply(lambda r: assign_stakeholder(r, lookup), axis=1)
    return df


# --------------------------------------------------------- 1+2 选地 + 裁切 + 多源 join(慢,缓存)
def subdistrict(name, JD):
    """按 name 取街道多边形(4326)。返回 (row, polygon)。"""
    jd = gpd.read_file(JD)
    row = jd[jd["name"].fillna("") == name]
    if len(row) == 0:
        row = jd[jd["name"].fillna("").str.contains(name)]
    if len(row) == 0:
        raise ValueError("找不到街道:%s" % name)
    row = row.iloc[[0]].to_crs(4326)
    return row, row.geometry.iloc[0]


def _join(cent, path, bb, cols_map):
    """cent(含 bid 的 representative-point GDF,4326)within path 的面,取 cols_map 列。返回 DataFrame[bid, 目标列...]。"""
    try:
        src = gpd.read_file(path, bbox=bb)
    except Exception:
        return pd.DataFrame({"bid": []})
    have = {k: v for k, v in cols_map.items() if k in src.columns}
    if not have:
        return pd.DataFrame({"bid": []})
    src = src[list(have) + ["geometry"]].rename(columns=have)
    src = src[src.geometry.notna()]
    j = gpd.sjoin(cent[["bid", "geometry"]], src.to_crs(4326), predicate="within", how="left")
    j = j.dropna(subset=list(have.values()), how="all").drop_duplicates("bid")
    return j[["bid"] + list(have.values())]


def build_cache(name=None, slug=None):
    """进阶:从原始「上海城市数据集」裁切 + 多源 join,写 data/<slug>/buildings.parquet(几何 32651)。
    需要 config.DATASET_ROOT 已指向解压后的数据集。返回 GeoDataFrame。详见「01_怎么选数据」notebook。"""
    slug = slug or config.SLUG
    name = name or config.site_name(slug)
    P = dataset_paths()
    if not P["AI"].exists():
        raise FileNotFoundError(
            "找不到数据集文件:%s\n请先在 config.py 把 DATASET_ROOT 指向你解压的「上海城市数据集」根目录。"
            "(没下载也没关系:随包已带 3 站缓存,直接用 load_buildings 即可。见 数据集说明.md)" % P["AI"])

    row, poly = subdistrict(name, P["JD"])
    bb = poly.bounds
    area_km2 = float(row.to_crs(UTM).area.iloc[0] / 1e6)

    ai = gpd.read_file(P["AI"], bbox=bb)
    ai = gpd.clip(ai, poly)
    ai = ai[ai.geometry.type.isin(["Polygon", "MultiPolygon"])].copy()
    ai = ai.rename(columns={"Height": "height_m", "Area": "area_src"})
    ai["height_m"] = pd.to_numeric(ai["height_m"], errors="coerce")
    ai = ai[ai["height_m"] > 0].reset_index(drop=True)
    ai["bid"] = range(len(ai))
    ai = ai.set_crs(4326, allow_override=True)

    cent = ai[["bid", "geometry"]].copy()
    cent["geometry"] = ai.geometry.representative_point()
    cent = gpd.GeoDataFrame(cent, geometry="geometry", crs=4326)

    eu = _join(cent, P["EU"], bb, {"class2": "euluc"})
    fn = _join(cent, P["FN"], bb, {"Function": "function", "Age": "age"})
    aoi = _join(cent, P["AOI"], bb, {"type1": "aoi_type1", "type2": "aoi_type2", "type": "aoi_type",
                                     "结构": "aoi_struct", "价格": "aoi_price", "时间": "aoi_year"})

    out = ai.drop(columns=[c for c in ai.columns if c not in ("bid", "height_m", "area_src", "geometry")])
    for part in (eu, fn, aoi):
        if len(part):
            out = out.merge(part, on="bid", how="left")
    out = gpd.GeoDataFrame(out, geometry="geometry", crs=4326).to_crs(UTM)
    out["area_m2"] = out.geometry.area
    out["height_source"] = "measured_ai"
    out = assign_all(out)

    d = DATA / slug
    d.mkdir(parents=True, exist_ok=True)
    out.to_parquet(d / "buildings.parquet")
    yaml.safe_dump({"name": name, "slug": slug, "area_km2": area_km2, "n": len(out),
                    "bounds_lonlat": list(poly.bounds)},
                   open(d / "site.yaml", "w", encoding="utf-8"), allow_unicode=True)
    print("  建缓存 %s(%s):%d 栋 → %s" % (name, slug, len(out), (d / "buildings.parquet").relative_to(ROOT)))
    return out


def build_context(slug=None, margin_m=800):
    """渲染用【06 专用】:study 街区外的周边体量(仅 geom+height,不做多源 join、不贴角色)。
    写 data/<slug>/context.parquet(几何 32651)= 缓冲多边形(study 外扩 margin_m 米)内、study 多边形外的 AI 建筑。
    只供 06 当**透明语境**渲染(ControlNet canny/depth 需要周边边缘/深度);05 主流程完全不读它。需 DATASET_ROOT。
    另把 study 多边形(UTM 环)+ margin 追加进 site.yaml(不动既有键),供 06 画研究范围红线。"""
    slug = slug or config.SLUG
    name = config.site_name(slug)
    P = dataset_paths()
    if not P["AI"].exists():
        raise FileNotFoundError(
            "找不到 AI 建筑数据:%s\n请先在 config.py 把 DATASET_ROOT 指向解压的「上海城市数据集」。周边语境需原始数据。" % P["AI"])
    row, poly = subdistrict(name, P["JD"])                       # 4326 study 多边形
    poly_utm = gpd.GeoSeries([poly], crs=4326).to_crs(UTM).iloc[0]
    buf_utm = poly_utm.buffer(margin_m)
    buf_4326 = gpd.GeoSeries([buf_utm], crs=UTM).to_crs(4326).iloc[0]

    ai = gpd.read_file(P["AI"], bbox=buf_4326.bounds)
    ai = ai[ai.geometry.type.isin(["Polygon", "MultiPolygon"])].copy()
    ai = ai.rename(columns={"Height": "height_m"})
    ai["height_m"] = pd.to_numeric(ai["height_m"], errors="coerce")
    ai = ai[ai["height_m"] > 0]
    ai = ai.set_crs(4326, allow_override=True).to_crs(UTM)
    rp = ai.geometry.representative_point()
    keep = rp.within(buf_utm) & (~rp.within(poly_utm))           # 环内、study 外 = 周边
    sub = ai[keep].copy()
    sub["geometry"] = sub.geometry.difference(poly_utm)          # 减去 study 面:跨界楼不再重叠实心 study(免接缝双边)
    sub = sub[~sub.geometry.is_empty & sub.geometry.notna()]
    ctx = gpd.GeoDataFrame(sub[["height_m", "geometry"]], geometry="geometry", crs=UTM).reset_index(drop=True)
    ctx["area_m2"] = ctx.geometry.area

    d = DATA / slug
    d.mkdir(parents=True, exist_ok=True)
    ctx.to_parquet(d / "context.parquet")
    # 06 专用 metadata 写**独立 sidecar** data/<slug>/context.yaml(不碰 05 的 site.yaml,
    # 免得 build_cache 重写 site.yaml 时把 study_poly_utm 清掉 → 红线消失)。
    yaml.safe_dump({
        "margin_m": int(margin_m), "n": int(len(ctx)),
        "study_poly_utm": [[[round(x, 2), round(y, 2)] for x, y in p.exterior.coords] for p in _polys(poly_utm)],
    }, open(d / "context.yaml", "w", encoding="utf-8"), allow_unicode=True)
    print("  建周边语境 %s:环内 study 外 %d 栋(margin %dm)→ %s" % (
        slug, len(ctx), margin_m, (d / "context.parquet").relative_to(ROOT)))
    return ctx


def has_cache(slug=None):
    slug = slug or config.SLUG
    return (DATA / slug / "buildings.parquet").exists()


def has_context(slug=None):
    slug = slug or config.SLUG
    return (DATA / slug / "context.parquet").exists()


def load_context(slug=None):
    """读 data/<slug>/context.parquet(周边语境 geom+height+area_m2);加 'geom' 列。没有则回 None。
    仅 06 渲染当透明语境用;05 主流程不碰。"""
    slug = slug or config.SLUG
    p = DATA / slug / "context.parquet"
    if not p.exists():
        return None
    gdf = gpd.read_parquet(p)
    df = pd.DataFrame(gdf.drop(columns="geometry"))
    df["geom"] = list(gdf.geometry)
    return df


def study_poly_rings(slug=None):
    """study 多边形的外环坐标(UTM 32651,list of rings);build_context 时写入 data/<slug>/context.yaml。没有则回 None。
    06 用来画『研究范围 = 整个街区多边形』的红色边界。独立 sidecar,不受 05 的 site.yaml 重写影响。"""
    slug = slug or config.SLUG
    p = DATA / slug / "context.yaml"
    if not p.exists():
        return None
    try:
        return yaml.safe_load(open(p, encoding="utf-8")).get("study_poly_utm")
    except Exception:
        return None


def load_buildings(slug=None):
    """读缓存的 per-site buildings(几何 32651);加 'geom' 列。回传 DataFrame。"""
    slug = slug or config.SLUG
    gdf = gpd.read_parquet(DATA / slug / "buildings.parquet")
    df = pd.DataFrame(gdf.drop(columns="geometry"))
    df["geom"] = list(gdf.geometry)
    if "stakeholder" not in df.columns:
        df = assign_all(df)
    return df


def current_buildings(slug=None):
    """整条管线的取数据入口:缓存在就直接读(离线);缓存缺、但 DATASET_ROOT 已设 → 现建再读。"""
    slug = slug or config.SLUG
    if has_cache(slug):
        return load_buildings(slug)
    if getattr(config, "DATASET_ROOT", None):
        build_cache(config.site_name(slug), slug)
        return load_buildings(slug)
    raise FileNotFoundError(
        "没有 %s 的缓存,且未设 config.DATASET_ROOT。\n"
        "→ 随包自带 lujiazui/caoyang/yuyuan 三站缓存,把 SLUG 设成其一即可离线跑;\n"
        "→ 想换别的街道,请下载「上海城市数据集」并设 DATASET_ROOT,见 数据集说明.md。" % slug)


def site_meta(slug=None):
    slug = slug or config.SLUG
    return yaml.safe_load(open(DATA / slug / "site.yaml", encoding="utf-8"))


# --------------------------------------------------------- 4 权力情景(只调高度;与 osm 版同引擎)
def load_scenarios(path=SCEN_PATH):
    return yaml.safe_load(open(path, encoding="utf-8"))["scenarios"]


def apply_scenario(height_m, stakeholder, scenario):
    """grow:只增不减。h' = max(既有, min(h×mult, cap))。"""
    pol = (scenario or {}).get(stakeholder, {})
    h = height_m * max(1.0, float(pol.get("mult", 1.0)))
    if "cap_m" in pol:
        h = min(h, float(pol["cap_m"]))
    return max(h, height_m)


def scenario_heights(df, scenario):
    """conserve(默认):总 GFA 守恒、权力只重分配,new_h = h×w×(ΣGFA/Σ(GFA·w));grow:见 apply_scenario。"""
    mode = (scenario or {}).get("_mode", "conserve")
    if mode == "grow":
        return df.apply(lambda r: apply_scenario(r["height_m"], r["stakeholder"], scenario), axis=1)
    w = df["stakeholder"].map(lambda sh: float((scenario or {}).get(sh, {}).get("mult", 1.0)))
    gfa = df["area_m2"] * df["height_m"]
    T = float(gfa.sum()); S = float((gfa * w).sum())
    if S <= 0:
        return df["height_m"]
    return (df["height_m"] * w * (T / S)).clip(lower=3.0)


# --------------------------------------------------------- recs 桥(进阶册 operators 的工作单位)
def to_recs(df):
    """DataFrame(含 geom/height_m/stakeholder)→ records 列表 [{geom, h, sh, area, frozen}]。
    主册用 DataFrame(只调高度),进阶册 operators.py 用 recs(改几何)——共用同一份载入。"""
    recs = []
    for _, r in df.iterrows():
        recs.append({"geom": r["geom"], "h": float(r["height_m"]),
                     "sh": r["stakeholder"], "area": float(r.get("area_m2", r["geom"].area)),
                     "frozen": False})
    return recs


# --------------------------------------------------------- 通用工具(绘图 / OBJ / 卫星底)
def _polys(geom):
    if isinstance(geom, Polygon):
        return [geom]
    if isinstance(geom, MultiPolygon):
        return list(geom.geoms)
    return []


def gfa_of(recs):
    return sum(r["geom"].area * r["h"] for r in recs)


def plot_footprints(ax, df_or_recs, color_for, lw=0.2):
    """footprint 著色(批量 PolyCollection,几千~上万栋也秒画)。df_or_recs 可为 DataFrame 或 recs 列表。"""
    from matplotlib.collections import PolyCollection
    rows = (r for _, r in df_or_recs.iterrows()) if hasattr(df_or_recs, "iterrows") else iter(df_or_recs)
    verts, colors = [], []
    for r in rows:
        col = color_for(r)
        for p in _polys(r["geom"]):
            verts.append(list(p.exterior.coords)); colors.append(col)
    if verts:
        ax.add_collection(PolyCollection(verts, facecolors=colors, edgecolors="white", linewidths=lw), autolim=True)
        ax.autoscale_view()
    ax.set_aspect("equal"); ax.set_xticks([]); ax.set_yticks([])


def save_fig(fig, name, out=OUT):
    import matplotlib.pyplot as plt
    out.mkdir(parents=True, exist_ok=True)
    p = out / name
    fig.savefig(p, dpi=120, bbox_inches="tight"); plt.close(fig)
    print("  -> wrote", p.relative_to(ROOT)); return p


def _ring(poly):
    c = list(poly.exterior.coords)
    if len(c) > 1 and c[0] == c[-1]:
        c = c[:-1]
    return c


def _iter_geom_h(df_or_recs, height_col="height_m"):
    """统一迭代 (geom, h):DataFrame 用 height_col;recs 用 'h'。"""
    if hasattr(df_or_recs, "iterrows"):
        for _, r in df_or_recs.iterrows():
            yield r["geom"], float(r[height_col])
    else:
        for r in df_or_recs:
            yield r["geom"], float(r["h"])


def extrude_obj(df_or_recs, height_col="height_m", origin=None):
    """真实 footprint 挤成量体 OBJ(墙 + 三角顶盖)。回传 (obj_str, n_verts, n_faces)。接受 DataFrame 或 recs。"""
    items = list(_iter_geom_h(df_or_recs, height_col))
    polys_all = [p for g, _ in items for p in _polys(g)]
    if origin is None:
        minx = min(p.bounds[0] for p in polys_all); miny = min(p.bounds[1] for p in polys_all)
        origin = (minx, miny)
    ox, oy = origin
    V, F = [], []

    def addv(x, y, z):
        V.append((x - ox, y - oy, z)); return len(V)

    for geom, h in items:
        for poly in _polys(geom):
            ring = _ring(poly)
            n = len(ring)
            if n < 3:
                continue
            base_b = len(V)
            for (x, y) in ring:
                addv(x, y, 0.0)
            base_t = len(V)
            for (x, y) in ring:
                addv(x, y, h)
            for i in range(n):
                j = (i + 1) % n
                b0, b1 = base_b + i + 1, base_b + j + 1
                t0, t1 = base_t + i + 1, base_t + j + 1
                F.append((b0, b1, t1)); F.append((b0, t1, t0))
            for tri in triangulate(poly):
                if not poly.contains(tri.representative_point()):
                    continue
                tc = list(tri.exterior.coords)[:3]
                a = addv(tc[0][0], tc[0][1], h); b = addv(tc[1][0], tc[1][1], h); c = addv(tc[2][0], tc[2][1], h)
                F.append((a, b, c))
    lines = ["# shanghai_power_to_form (DF26_ws18) — real Shanghai footprints extruded (meters, EPSG:32651-local)",
             "# %d items, height=%s" % (len(items), height_col)]
    for (x, y, z) in V:
        lines.append("v %.3f %.3f %.3f" % (x, y, z))
    for (a, b, c) in F:
        lines.append("f %d %d %d" % (a, b, c))
    return "\n".join(lines) + "\n", len(V), len(F)


def ground_sat(minx, miny, maxx, maxy, cache_png, factor=2.0):
    """抓比 patch 宽 factor× 的真实卫星图(Esri)贴 viewer 地面 → 体块坐在真实上海上。
    返回 (data_uri_jpeg, local_extent[lx0,ly0,lx1,ly1]),local 相对 (minx,miny) 与 footprint 同系。"""
    import json as _json, base64, contextily as ctx, pyproj
    from PIL import Image
    cache_png = Path(cache_png); meta_p = cache_png.with_suffix(".json")
    req = [round(minx, 1), round(miny, 1), round(maxx, 1), round(maxy, 1)]   # 缓存身份 = 请求范围
    if cache_png.exists() and meta_p.exists():
        meta = _json.load(open(meta_p))
        # 只有 bounds 相符才复用(dict 新格式);旧格式(meta=list)或范围变了(加 context / 改 margin)→ 视为过期,重抓
        if isinstance(meta, dict) and meta.get("bounds") == req:
            return "data:image/jpeg;base64," + base64.b64encode(cache_png.read_bytes()).decode(), meta["local"]
    cx, cy = (minx + maxx) / 2, (miny + maxy) / 2
    hw, hh = (maxx - minx) / 2 * factor, (maxy - miny) / 2 * factor
    to4326 = pyproj.Transformer.from_crs(UTM, 4326, always_xy=True).transform
    cs = [to4326(cx - hw, cy - hh), to4326(cx + hw, cy - hh), to4326(cx - hw, cy + hh), to4326(cx + hw, cy + hh)]
    lons = [p[0] for p in cs]; lats = [p[1] for p in cs]
    span = max(2 * hw, 2 * hh); zoom = 16 if span < 2500 else (15 if span < 6500 else 14)
    img, ext = ctx.bounds2img(min(lons), min(lats), max(lons), max(lats), ll=True,
                              source=ctx.providers.Esri.WorldImagery, zoom=zoom)
    fr = pyproj.Transformer.from_crs(3857, UTM, always_xy=True).transform
    ux0, uy0 = fr(ext[0], ext[2]); ux1, uy1 = fr(ext[1], ext[3])
    local = [ux0 - minx, uy0 - miny, ux1 - minx, uy1 - miny]
    arr = img[:, :, :3] if (getattr(img, "ndim", 0) == 3 and img.shape[2] >= 3) else img
    cache_png.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(arr).save(cache_png, "JPEG", quality=82)
    _json.dump({"local": local, "bounds": req}, open(meta_p, "w"))       # 存 bounds 供下次比对失效
    return "data:image/jpeg;base64," + base64.b64encode(cache_png.read_bytes()).decode(), local


def site_ground(minx, miny, maxx, maxy, slug=None, factor=2.0):
    slug = slug or config.SLUG
    try:
        return ground_sat(minx, miny, maxx, maxy, OUT / slug / "ground_sat.jpg", factor)
    except Exception as e:
        print("  卫星底失败", slug, e); return None, None


def honest_note(place="上海"):
    return ("本地多源真实数据(AI建筑-实测高度 + EULUC用途 + 带年份Function + 百度AOI)· "
            "「谁的权利」为用途的离散级联查表、非产权考证 · informal 本数据无信号(恒空)· "
            "danwei工人新村按用途算居民(形态记得它是单位建的)· AOI价格/结构仅作离散tag不外发 · %s 教学样本" % place)


# --------------------------------------------------------- 取数据入口的两种「准备」(让 notebook 一行取数据)
def build_or_load(slug=None):
    """01「亲手建缓存」那格的核心:有数据集就**现建**、否则读**随包缓存**。
    返回 (df, source);source ∈ {'built','cache'}。学生看一行,build/load 的分支细节藏在这里。"""
    slug = slug or config.SLUG
    if getattr(config, "DATASET_ROOT", None) and dataset_paths()["AI"].exists():
        build_cache(config.site_name(slug), slug)        # 从原始多源数据现建
        return load_buildings(slug), "built"
    return current_buildings(slug), "cache"               # 随包缓存(离线)


# --------------------------------------------------------- 反事实:改一条查表 → 看分布变化(02 的工作单位)
def counterfactual(df, frm="developer", to="state", lookup=None):
    """把 euluc 表里**第一条**映射到 frm 的用途改判给 to,返回 {flip, frm, to, before, after}。
    只在内存里试、**不动 YAML**;满意了再去真正改 shanghai_lookup.yaml。"""
    import copy
    lk = copy.deepcopy(lookup or load_lookup())
    flip = next((k for k, v in lk["euluc"].items() if v == frm), None)
    if flip is not None:
        lk["euluc"][flip] = to
    return {"flip": flip, "frm": frm, "to": to,
            "before": assign_all(df).stakeholder.value_counts().to_dict(),
            "after": assign_all(df, lk).stakeholder.value_counts().to_dict()}


# --------------------------------------------------------- 挤 OBJ 并落盘(03 step5 的「写档」那半步)
def export_obj(df, slug=None, name="city_current.obj", height_col="height_m"):
    """真实 footprint 按 height_col 挤成量体 OBJ,写到 out/<slug>/<name>。回传 (path, n_verts, n_faces)。
    mkdir / write_text 这些 I/O 细节藏在这里,notebook 只关心『挤出来、写下去』。"""
    slug = slug or config.SLUG
    d = OUT / slug
    d.mkdir(parents=True, exist_ok=True)
    obj, nv, nf = extrude_obj(df, height_col=height_col)
    p = d / name
    p.write_text(obj, encoding="utf-8")
    return p, nv, nf


if __name__ == "__main__":
    import sys
    slug = sys.argv[1] if len(sys.argv) > 1 else config.SLUG
    df = current_buildings(slug)
    print("== %s (%s) ==" % (config.site_name(slug), slug))
    print("栋数:", len(df), "| 面积km2:", round(site_meta(slug)["area_km2"], 2))
    h = df["height_m"].astype(float)
    print("高度 实测 m: med %.1f / p90 %.1f / max %.1f" % (h.median(), h.quantile(.9), h.max()))
    print("stakeholder:", df.stakeholder.value_counts().to_dict())
    eu = df["euluc"].apply(_t).ne("").mean() if "euluc" in df else 0
    print("EULUC 覆盖 %.0f%% | unknown %.0f%%" % (eu * 100, (df.stakeholder == "unknown").mean() * 100))
    print(honest_note())
