"""
Stage 4E: 종합 무결성 및 품질 검증기 (Validator)
프로젝트: D:/Franchise_Dashboard
위치: src/stage4e/validator.py

실행:
    python src/stage4e/validator.py
"""

import sys
import json
import time
import sqlite3
from pathlib import Path
from datetime import datetime

# Windows 콘솔 인코딩 보호
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

BASE_DIR = Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.stage4e.api.database import ANALYTICS_DB_PATH, query_one, query_all

RAW_V2_DB_PATH = BASE_DIR / "data" / "nationwide_food_stores_v2.sqlite3"
BRAND_MASTER_DB_PATH = BASE_DIR / "data" / "brand_master_v1.sqlite3"
CATEGORY_MASTER_DB_PATH = BASE_DIR / "data" / "food_category_master_v1.sqlite3"
OUTPUT_REPORT_PATH = BASE_DIR / "reports" / "phase4_stage4e_validation.json"


def run_full_validation() -> dict:
    print("=" * 70)
    print("Franchise Dashboard - Phase 4 Stage 4E 종합 무결성 검증기 가동")
    print("=" * 70)

    start_time = time.time()
    results = {
        "timestamp": datetime.now().isoformat(),
        "database": str(ANALYTICS_DB_PATH),
        "checks": [],
        "overall_status": "PASS",
        "metrics_summary": {}
    }

    def record_check(check_id: str, name: str, passed: bool, expected: any, actual: any, details: str = ""):
        status = "PASS" if passed else "FAIL"
        results["checks"].append({
            "check_id": check_id,
            "name": name,
            "status": status,
            "expected": expected,
            "actual": actual,
            "details": details
        })
        symbol = "[PASS]" if passed else "[FAIL]"
        print(f"{symbol} {check_id}: {name} -> {status} (Expected: {expected}, Actual: {actual})")
        if not passed:
            results["overall_status"] = "FAIL"

    # 1. 전국 총 점포수 대사
    r1 = query_one("SELECT total_stores FROM regional_overall_stats WHERE region_code = '00'")
    cnt_nation = r1["total_stores"] if r1 else 0
    record_check("CHK_01", "전국 외식업 총 점포수 일치 (735,185)", cnt_nation == 735185, 735185, cnt_nation)

    # 2. 16개 시도 합계 대사
    r2 = query_one("SELECT SUM(total_stores) as s, COUNT(*) as c FROM regional_overall_stats WHERE region_type = 'SIDO'")
    sido_sum, sido_cnt = (r2["s"], r2["c"]) if r2 else (0, 0)
    record_check("CHK_02", "16개 시도 점포수 합계 일치 (735,185)", sido_sum == 735185 and sido_cnt == 16, {"sum": 735185, "count": 16}, {"sum": sido_sum, "count": sido_cnt})

    # 3. 256개 시군구 합계 대사
    r3 = query_one("SELECT SUM(total_stores) as s, COUNT(*) as c FROM regional_overall_stats WHERE region_type = 'SIGUNGU'")
    sgg_sum, sgg_cnt = (r3["s"], r3["c"]) if r3 else (0, 0)
    record_check("CHK_03", "256개 시군구 점포수 합계 일치 (735,185)", sgg_sum == 735185 and sgg_cnt == 256, {"sum": 735185, "count": 256}, {"sum": sgg_sum, "count": sgg_cnt})

    # 4. store_analytics_lookup 고유성 대사
    r4 = query_one("SELECT COUNT(*) as t, COUNT(DISTINCT bizes_id) as d FROM store_analytics_lookup")
    tot_stores, dist_stores = (r4["t"], r4["d"]) if r4 else (0, 0)
    record_check("CHK_04", "점포 룩업 테이블 1:1 고유성 무결성 (중복 0건)", tot_stores == dist_stores == 735185, 735185, {"total": tot_stores, "distinct": dist_stores})

    # 5. 브랜드 연결 점포 + 독립 점포 합계 대사
    r5 = query_one("SELECT brand_linked_stores, independent_stores, total_stores FROM regional_overall_stats WHERE region_code = '00'")
    b_stores = r5["brand_linked_stores"]
    ind_stores = r5["independent_stores"]
    tot_rec = r5["total_stores"]
    record_check("CHK_05", "브랜드 연결 점포(168,295) + 독립 점포(566,890) = 전체 점포(735,185)", (b_stores + ind_stores == 735185 and b_stores == 168295 and ind_stores == 566890), 735185, b_stores + ind_stores)

    # 6. 8대 대분류 점포수 합계 대사
    r6 = query_one("SELECT COUNT(DISTINCT category_major_id) as c FROM regional_category_stats WHERE region_code = '00'")
    maj_cnt = r6["c"] if r6 else 0
    record_check("CHK_06", "8대 확정 외식업 대분류 체계 일치", maj_cnt == 8, 8, maj_cnt)

    # 7. 48개 중분류 점포수 합계 대사
    r7 = query_one("SELECT COUNT(DISTINCT category_mid_id) as c, SUM(total_stores) as s FROM regional_category_stats WHERE region_code = '00'")
    mid_cnt, mid_sum = (r7["c"], r7["s"]) if r7 else (0, 0)
    record_check("CHK_07", "48개 확정 외식업 중분류 체계 및 점포수 합계 일치 (735,185)", mid_cnt == 48 and mid_sum == 735185, {"count": 48, "sum": 735185}, {"count": mid_cnt, "sum": mid_sum})

    # 8. 모호 분류(104,060건) 격리 대사
    r8 = query_one("SELECT SUM(stores_excluding_ambiguous) as exc, SUM(ambiguous_stores) as amb FROM regional_category_stats WHERE region_code = '00'")
    exc_sum, amb_sum = (r8["exc"], r8["amb"]) if r8 else (0, 0)
    record_check("CHK_08", "모호 분류(104,060) 격리 필터 대사 (확정: 631,125 + 모호: 104,060 = 735,185)", amb_sum == 104060 and exc_sum == 631125, {"ambiguous": 104060, "confirmed": 631125}, {"ambiguous": amb_sum, "confirmed": exc_sum})

    # 9. 샵인샵 복수 브랜드 점포 대사
    r9 = query_one("SELECT COUNT(*) as c FROM store_analytics_lookup WHERE is_multi_brand_store = 1")
    multi_cnt = r9["c"] if r9 else 0
    record_check("CHK_09", "복수 브랜드 샵인샵 점포 수 대사 (23건)", multi_cnt == 23, 23, multi_cnt)

    # 10. 3D 상권 핫스팟 및 드론 투어 좌표 대사
    r10 = query_all("SELECT hotspot_id, hotspot_name, pitch, bearing, zoom FROM commercial_hotspots")
    hot_cnt = len(r10)
    gwangjin_ok = any("광진" in h["hotspot_name"] and h["pitch"] == 60.0 for h in r10)
    record_check("CHK_10", "3D GIS 상권 핫스팟 10곳 및 광진구 드론 투어 파라미터 탑재", hot_cnt == 10 and gwangjin_ok, {"count": 10, "gwangjin_pitch": 60.0}, {"count": hot_cnt, "gwangjin_found": gwangjin_ok})

    # 11. 100m 격자 기둥 (ColumnLayer) 밀집도 데이터 대사
    r11 = query_one("SELECT COUNT(*) as c, SUM(total_stores) as s FROM spatial_density_grid_100m")
    grid_cnt, grid_sum = (r11["c"], r11["s"]) if r11 else (0, 0)
    record_check("CHK_11", "전국 100m 정밀 격자 기둥(ColumnLayer) 밀집도 셀 생성 및 점포 대사 (밀집도 >= 3개소)", grid_cnt == 76745 and grid_sum == 587500, {"grid_cells": 76745, "stores_sum": 587500}, {"grid_cells": grid_cnt, "stores_sum": grid_sum})

    # 12. 메트릭 정의 (4축 독립성 및 가이드라인)
    r12 = query_one("SELECT COUNT(*) as c FROM metric_definitions")
    metric_cnt = r12["c"] if r12 else 0
    record_check("CHK_12", "비즈니스 메트릭 공식 정의 및 해석 가이드라인 10종 완비", metric_cnt >= 10, ">= 10", metric_cnt)

    # 13. 원본 데이터베이스 3종 불변성 (V2 원본, 브랜드 마스터, 카테고리 마스터)
    c1 = sqlite3.connect(str(RAW_V2_DB_PATH))
    cnt_v2 = c1.cursor().execute("SELECT COUNT(*) FROM stores;").fetchone()[0]
    c1.close()

    c2 = sqlite3.connect(str(BRAND_MASTER_DB_PATH))
    cur2 = c2.cursor()
    cnt_bm = cur2.execute("SELECT COUNT(*) FROM brands;").fetchone()[0]
    links_bm = cur2.execute("SELECT COUNT(*) FROM store_brand_links;").fetchone()[0]
    c2.close()

    c3 = sqlite3.connect(str(CATEGORY_MASTER_DB_PATH))
    cnt_cm = c3.cursor().execute("SELECT COUNT(*) FROM store_category_classifications;").fetchone()[0]
    c3.close()

    raw_immutability = (cnt_v2 == 735185 and cnt_bm == 5063 and links_bm == 735208 and cnt_cm == 735185)
    record_check("CHK_13", "선행 원본 데이터베이스 3종 불변성 보존 (변조 0건)", raw_immutability, 
                 {"v2_stores": 735185, "brand_master": 5063, "brand_links": 735208, "category_master": 735185},
                 {"v2_stores": cnt_v2, "brand_master": cnt_bm, "brand_links": links_bm, "category_master": cnt_cm})

    # 14. 4개 분리 축 무결성 (공식성, 매칭 신뢰도, 운영 형태, 카테고리 확정상태)
    r14 = query_one("""
        SELECT 
            COUNT(DISTINCT brand_officiality) as off_cnt,
            COUNT(DISTINCT match_status) as match_cnt,
            COUNT(DISTINCT operation_type) as op_cnt,
            COUNT(DISTINCT classification_status) as cat_cnt
        FROM store_analytics_lookup
    """)
    axes_ok = (r14["off_cnt"] >= 3 and r14["match_cnt"] >= 3 and r14["op_cnt"] >= 3 and r14["cat_cnt"] >= 2)
    record_check("CHK_14", "4개 비즈니스 축 독립성 및 다차원 상태 격리 유지", axes_ok, "Independent 4-axes", dict(r14))

    # 15. 지역별 브랜드 랭킹 테이블 무결성
    r15 = query_one("SELECT COUNT(*) as c FROM regional_brand_rankings")
    rank_cnt = r15["c"] if r15 else 0
    record_check("CHK_15", "전국 및 지역별 브랜드 랭킹 데이터 탑재 (Top 20/10)", rank_cnt > 90000, "> 90,000", rank_cnt)

    elapsed = round(time.time() - start_time, 3)
    results["elapsed_seconds"] = elapsed
    results["metrics_summary"] = {
        "total_stores": cnt_nation,
        "provinces": sido_cnt,
        "districts": sgg_cnt,
        "major_categories": maj_cnt,
        "mid_categories": mid_cnt,
        "brand_linked_stores": b_stores,
        "independent_stores": ind_stores,
        "ambiguous_category_stores": amb_sum,
        "confirmed_category_stores": exc_sum,
        "shop_in_shop_stores": multi_cnt,
        "grid_cells_100m": grid_cnt,
        "hotspots_3d": hot_cnt,
        "ranking_records": rank_cnt
    }

    OUTPUT_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print("=" * 70)
    print(f"검증 완료! 총 소요시간: {elapsed}초, 최종 판정: {results['overall_status']}")
    print(f"상세 검증 결과 저장 위치: {OUTPUT_REPORT_PATH}")
    print("=" * 70)
    return results


if __name__ == "__main__":
    res = run_full_validation()
    if res["overall_status"] != "PASS":
        sys.exit(1)
