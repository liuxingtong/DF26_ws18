# config.py —— 换地方:只填中心点 LAT/LON + 半径 RADIUS_M,保存后 Run All(或重跑任何 step)。
# Change location: set the center LAT/LON + RADIUS_M, then Run All. BBOX & UTM are auto-derived.
PLACE = "五角场"  # 地名,仅用于标注 / label only
LAT = 31.310400  # 中心点纬度 latitude;填了就抓这个新地方(需 pip install osmnx + 联网)
LON = 121.517208  # 中心点经度 longitude
RADIUS_M = 1200  # 中心到边的距离(米);范围约 2×RADIUS_M 见方

# ===== 以下自动推导,通常不用改 / auto-derived — usually leave as is =====
import math

if LAT is None or LON is None:  # 默认:用自带的大巴窑数据(离线,不需 osmnx)
    BBOX = (103.838, 1.327, 103.862, 1.348)
    UTM = 32648
    BUNDLED = True
else:  # 换地方:中心点+半径 → BBOX;经度 → UTM
    _dlat = RADIUS_M / 111320.0
    _dlon = RADIUS_M / (111320.0 * math.cos(math.radians(LAT)))
    BBOX = (LON - _dlon, LAT - _dlat, LON + _dlon, LAT + _dlat)  # (W, S, E, N)
    UTM = (32600 if LAT >= 0 else 32700) + int((LON + 180) // 6) + 1
    BUNDLED = False
