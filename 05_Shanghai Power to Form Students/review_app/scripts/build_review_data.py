#!/usr/bin/env python3
"""Build local review layers. AMap key is read from AMAP_WEB_SERVICE_KEY and never persisted."""

from __future__ import annotations

import json
import math
import os
import time
import urllib.parse
import urllib.request
from pathlib import Path

import geopandas as gpd
from shapely.geometry import Point

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "dapuqiao"
OUT = Path(__file__).resolve().parents[1] / "public" / "data"

OFFICIAL_SOURCE = "https://www.shhuangpu.gov.cn/uploadfile/6051185f-9fc3-44b3-93e3-e4aa4c122c1a/%E9%BB%84%E6%B5%A6%E5%8C%BA%E7%AC%AC%E4%BA%8C%E6%89%B9%E6%96%87%E7%89%A9%E4%BF%9D%E6%8A%A4%E7%82%B9%E5%85%AC%E5%B8%83%E5%90%8D%E5%8D%95.pdf"
OFFICIAL = [
    (73, "荣金大戏院旧址", "建国东路11号", False),
    (74, "恒昌里", "建国东路31弄", True),
    (75, "康益里", "建国东路39弄", True),
    (76, "建国中路103弄18号住宅", "建国中路103弄18号", False),
    (77, "杨度旧居", "建国中路155弄13号", False),
    (78, "汪亚尘旧居", "建国中路155弄15号", False),
    (79, "建国中路155弄25号住宅", "建国中路155弄25号", False),
    (80, "瑞金二路215号住宅", "瑞金二路215号", False),
    (81, "合丰帽厂旧址", "泰康路248弄48-50号", True),
    (82, "勤乐邨", "泰康路316弄", True),
    (83, "海会寺旧址", "丽园路565号", True),
    (84, "漫画会旧址", "黄陂南路847弄9号", False),
    (85, "上海美术专科学校旧址", "顺昌路560号", True),
    (86, "天祥里", "永年路149弄", True),
    (87, "佛化祗园法会旧址", "永年路78弄3号", False),
    (88, "安顺里", "建国东路143弄", True),
]

# These selections are deliberately conservative: AMap provides a point/AOI clue,
# while the local building polygons provide the selectable geometry.  Records in
# MANUAL_REVIEW_IDS are left unselected because redevelopment, demolition or a
# lane-wide historic address prevents a defensible building-level assignment.
CURATED_SUGGESTIONS = {
    "HP-73": ["1296"],
    "HP-81": ["566", "569"],
    "HP-82": ["359", "371"],
    "HP-84": ["1119"],
    "HP-85": ["1196"],
    "HP-86": ["1181", "1180", "1168", "1167", "1183", "1170", "1178", "1176"],
}
MANUAL_REVIEW_IDS = {"HP-74", "HP-75", "HP-83", "HP-88"}
EVIDENCE_NOTES = {
    "HP-73": "门牌地理编码与建筑轮廓重合；名称检索未提供更可靠的独立 POI。",
    "HP-74": "历史里弄名称与现状更新项目名称发生漂移，无法仅凭高德判定原建筑范围。",
    "HP-75": "历史名称未检出，现状 AOI 为思家公寓；需人工判断历史范围与现状建筑的关系。",
    "HP-81": "门牌为 48–50 号且点位落在田子坊 AOI 内，预选两个与门牌点重合的建筑轮廓。",
    "HP-82": "检出同名勤乐邨 POI，逆地理编码 AOI 面积约 862㎡；预选 AOI 中心附近两栋建筑。",
    "HP-83": "门牌点落在丽园公园 AOI 内，旧址可能已不存在，不能强行匹配现状建筑。",
    "HP-84": "门牌可定位至最近建筑，但历史名称未被 POI 独立印证，按中等置信度预选。",
    "HP-85": "门牌点与一栋建筑轮廓重合；历史名称未被 POI 独立印证，按中等置信度预选。",
    "HP-86": "逆地理编码命中永年路149弄小区 AOI，按 AOI 面积与中心距离预选建筑组。",
    "HP-88": "逆地理编码返回的现状小区名称与历史名称、门牌关系不一致，保留人工复核。",
}
ONLINE_EVIDENCE = {
    "HP-74": [
        {
            "title": "建国东路历史建筑图文记录",
            "url": "https://blog.sina.com.cn/s/blog_5d1bdf480102vvtp.html",
            "tier": "线索",
            "note": "记录称恒昌里为建国东路17弄、16幢、建筑面积2084㎡，与官方名录的31弄存在门牌冲突。",
        }
    ],
    "HP-75": [
        {
            "title": "新民晚报《娘家康益里》",
            "url": "https://www.sohu.com/a/605943141_121286085",
            "tier": "媒体",
            "note": "作者明确回忆建国东路39弄23号属于康益里，并称2021年前后仍面临动迁。",
        },
        {
            "title": "建国东路历史建筑图文记录",
            "url": "https://blog.sina.com.cn/s/blog_5d1bdf480102vvtp.html",
            "tier": "线索",
            "note": "记录康益里建于1936年，为31幢二层砖木建筑，建筑面积2040㎡。",
        },
    ],
    "HP-83": [
        {
            "title": "海会寺旧址现场与地名志摘录",
            "url": "https://www.meipian.cn/42b3t2cx",
            "tier": "现场线索",
            "note": "2017与2022年的现场记录指向丽园路565号，称南侧大殿仍存并已挂牌。",
        },
        {
            "title": "斜土路记忆中的海会寺",
            "url": "https://www.sohu.com/a/247115306_798813",
            "tier": "地方志线索",
            "note": "文章援引地方志称寺址为丽园路567号，并指出565-2仍有部分建筑，形成门牌差异。",
        },
    ],
    "HP-88": [
        {
            "title": "上海市黄浦区房屋征收决定",
            "url": "https://www.shanghai.gov.cn/gwk/search/content/bf584fc1728a46779e00dd9b3009a69c",
            "tier": "政府",
            "note": "官方清单将建国东路143弄1—83号及169弄全部列入68街坊征收范围。",
        },
        {
            "title": "建国东路历史建筑图文记录",
            "url": "https://blog.sina.com.cn/s/blog_5d1bdf480102vvtp.html",
            "tier": "线索",
            "note": "记录称安顺里跨143弄与169弄，为87幢二层砖木建筑，建筑面积8534㎡。",
        },
    ],
}

PI = math.pi
A = 6378245.0
EE = 0.00669342162296594323


def _tlat(x, y):
    return -100 + 2*x + 3*y + .2*y*y + .1*x*y + .2*math.sqrt(abs(x)) + (20*math.sin(6*x*PI)+20*math.sin(2*x*PI))*2/3 + (20*math.sin(y*PI)+40*math.sin(y/3*PI))*2/3 + (160*math.sin(y/12*PI)+320*math.sin(y*PI/30))*2/3


def _tlon(x, y):
    return 300 + x + 2*y + .1*x*x + .1*x*y + .1*math.sqrt(abs(x)) + (20*math.sin(6*x*PI)+20*math.sin(2*x*PI))*2/3 + (20*math.sin(x*PI)+40*math.sin(x/3*PI))*2/3 + (150*math.sin(x/12*PI)+300*math.sin(x/30*PI))*2/3


def wgs_to_gcj(lon, lat):
    dlat, dlon = _tlat(lon-105, lat-35), _tlon(lon-105, lat-35)
    rad = lat/180*PI
    magic = 1-EE*math.sin(rad)**2
    sqrt = math.sqrt(magic)
    return lon + dlon*180/(A/sqrt*math.cos(rad)*PI), lat + dlat*180/((A*(1-EE))/(magic*sqrt)*PI)


def gcj_to_wgs(lon, lat):
    x, y = lon, lat
    for _ in range(3):
        gx, gy = wgs_to_gcj(x, y)
        x, y = x-(gx-lon), y-(gy-lat)
    return x, y


def amap_request(path, key, params):
    params = {"key": key, "output": "json", **params}
    url = f"https://restapi.amap.com/{path}?" + urllib.parse.urlencode(params)
    for _ in range(3):
        with urllib.request.urlopen(url, timeout=20) as response:
            result = json.load(response)
        if result.get("status") == "1":
            return result
        time.sleep(1)
    raise RuntimeError(f"AMap request failed: {result.get('info')}")


def amap_geocode(key, address):
    return amap_request("v3/geocode/geo", key, {
        "address": "上海市黄浦区" + address, "city": "上海"
    }).get("geocodes", [])


def amap_text_search(key, name):
    result = amap_request("v3/place/text", key, {
        "keywords": name, "city": "310101", "citylimit": "true", "offset": 5, "page": 1,
    })
    return result.get("pois", [])


def amap_regeo(key, glon, glat):
    result = amap_request("v3/geocode/regeo", key, {
        "location": f"{glon},{glat}", "radius": 100, "extensions": "all", "roadlevel": 0,
    })
    return result.get("regeocode", {})


def clean_geojson(frame, path, columns):
    frame = frame.to_crs(4326)[columns + ["geometry"]].copy()
    path.write_text(frame.to_json(drop_id=True), encoding="utf-8")


def main():
    key = os.environ.get("AMAP_WEB_SERVICE_KEY")
    if not key:
        raise SystemExit("Set AMAP_WEB_SERVICE_KEY for this one-off build; it is never stored.")
    OUT.mkdir(parents=True, exist_ok=True)
    buildings = gpd.read_parquet(DATA / "buildings.parquet")
    projected = buildings.to_crs(32651)
    proxy = gpd.read_file(DATA / "drafts" / "heritage_buildings.draft.geojson")
    proxy_ids = set(proxy["bid"].astype(str))
    reviews = []
    for number, name, address, compound in OFFICIAL:
        record_id = f"HP-{number}"
        geocodes = amap_geocode(key, address)
        first = geocodes[0]
        glon, glat = map(float, first["location"].split(","))
        pois = amap_text_search(key, name)
        exact_poi = next((poi for poi in pois if poi.get("name") == name), None)
        regeo = amap_regeo(key, glon, glat)
        aois = regeo.get("aois") or []
        aoi = aois[0] if aois else {}
        lon, lat = gcj_to_wgs(glon, glat)
        point = gpd.GeoSeries([Point(lon, lat)], crs=4326).to_crs(32651).iloc[0]
        distances = projected.geometry.distance(point).sort_values()
        candidates = []
        for idx, distance in distances.head(12).items():
            if distance > (45 if compound else 20):
                continue
            row = projected.loc[idx]
            candidates.append({"bid": str(row.bid), "distance_m": round(float(distance), 1), "stakeholder": str(row.stakeholder), "in_existing_proxy": str(row.bid) in proxy_ids})
        nearest = candidates[0] if candidates else None
        review_required = record_id in MANUAL_REVIEW_IDS
        if record_id in CURATED_SUGGESTIONS:
            suggested = CURATED_SUGGESTIONS[record_id]
            confidence = "high" if record_id in {"HP-73", "HP-81", "HP-82", "HP-86"} else "medium"
        elif review_required:
            suggested = []
            confidence = "review"
        else:
            suggested = [nearest["bid"]] if nearest and nearest["distance_m"] <= 10 else []
            confidence = "high" if suggested else "review"
            review_required = not bool(suggested)
        reviews.append({
            "id": record_id, "number": number, "name": name, "address": address,
            "official_source": OFFICIAL_SOURCE, "amap_formatted_address": first.get("formatted_address"),
            "amap_level": first.get("level"), "amap_candidate_count": len(geocodes),
            "amap_poi_name": exact_poi.get("name") if exact_poi else None,
            "amap_poi_address": exact_poi.get("address") if exact_poi else None,
            "amap_aoi_name": aoi.get("name"), "amap_aoi_area_m2": aoi.get("area"),
            "location": [lon, lat], "compound": compound, "review_required": review_required,
            "match_status": "manual_review" if review_required else "preannotated",
            "spatial_status": "unresolved" if review_required else "preannotated",
            "include_in_optimization": not review_required,
            "exclusion_reason": EVIDENCE_NOTES.get(record_id) if review_required else None,
            "evidence_confidence": confidence,
            "evidence_reason": EVIDENCE_NOTES.get(record_id, "门牌地理编码与最近建筑距离不超过 10m，预选最近建筑。"),
            "online_evidence": ONLINE_EVIDENCE.get(record_id, []),
            "suggested_bids": suggested,
            "candidates": candidates,
        })
        time.sleep(.45)
    clean_geojson(buildings, OUT / "buildings.geojson", ["bid", "stakeholder"])
    zones = gpd.read_file(DATA / "drafts" / "intervention_zones.draft.geojson")
    clean_geojson(zones, OUT / "zones.geojson", ["zone_id", "review_status"])
    streets = gpd.read_file(DATA / "street_network.geojson")
    street_cols = [c for c in ["name", "highway"] if c in streets.columns]
    clean_geojson(streets, OUT / "streets.geojson", street_cols)
    clean_geojson(proxy, OUT / "heritage_proxy.geojson", ["bid", "review_status"])
    public = gpd.read_file(DATA / "public_space_candidates.geojson")
    clean_geojson(public, OUT / "public_spaces.geojson", ["name", "research_status"])
    payload = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "coordinate_note": "AMap GCJ-02 results converted to WGS84 for local GeoJSON display.",
        "official_source": OFFICIAL_SOURCE,
        "reviews": reviews,
    }
    (OUT / "review_cases.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "review_cases": len(reviews),
        "preannotated": sum(r["match_status"] == "preannotated" for r in reviews),
        "manual_review": sum(r["review_required"] for r in reviews),
        "output": str(OUT),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
