# Dapuqiao heritage review data freeze

## Freeze identity

- Freeze date: 2026-09-27 (Asia/Shanghai)
- Scope: Huangpu District second-batch heritage points, Dapuqiao Subdistrict, records 73–88
- Record grain: one official heritage record per row
- Coordinate display: WGS84, converted from AMap GCJ-02 responses

## Frozen decision

The package retains all 16 official records. Twelve records have provisional building-level annotations and are included in the optimization input. Four records remain in the evidence database but are excluded from building-level optimization:

| ID | Record | Reason for exclusion |
| --- | --- | --- |
| HP-74 | 恒昌里 | Official and historical sources conflict on the lane number; the historic compound boundary is unresolved. |
| HP-75 | 康益里 | Sources corroborate the historic compound, but the current AOI does not establish its building-level boundary. |
| HP-83 | 海会寺旧址 | Sources disagree between No. 565 and No. 567, and the surviving historic structure is not securely matched to a current footprint. |
| HP-88 | 安顺里 | Evidence indicates a compound spanning No. 143 Lane and No. 169 Lane; an entrance-point match would understate the extent. |

These records use `spatial_status: unresolved` and `include_in_optimization: false`. They must not be silently replaced by the nearest building. Their coordinates, candidate footprints, source notes and review reasons remain available for later correction.

## Reproduction

`scripts/build_review_data.py` reads the AMap Web Service key only from `AMAP_WEB_SERVICE_KEY`. The key is not persisted. Rebuilding can change current-map POI/AOI responses, so the committed files under `public/data/` are the frozen research snapshot; regenerate only when intentionally creating a new version.

The SHA-256 manifest is stored in `public/data/FREEZE_MANIFEST.json`.
