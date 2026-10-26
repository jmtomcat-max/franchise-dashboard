"""
Phase 4 Stage 4E: 종합 무결성 및 API 자동 테스트 스위트 (15개 시나리오)
프로젝트: D:/Franchise_Dashboard
위치: tests/test_phase4_stage4e.py
"""

import sys
import sqlite3
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.stage4e.api.main import app
from src.stage4e.api.database import ANALYTICS_DB_PATH, query_one, query_all

RAW_V2_DB_PATH = BASE_DIR / "data" / "nationwide_food_stores_v2.sqlite3"
BRAND_MASTER_DB_PATH = BASE_DIR / "data" / "brand_master_v1.sqlite3"
CATEGORY_MASTER_DB_PATH = BASE_DIR / "data" / "food_category_master_v1.sqlite3"

client = TestClient(app)


# 1. 전국·지역별 점포수 합계 일치 (전국 735,185 = 16개 시도 합 = 256개 시군구 합)
def test_01_regional_store_counts_reconciliation():
    r_nation = query_one("SELECT total_stores FROM regional_overall_stats WHERE region_code = '00'")
    nation_stores = r_nation["total_stores"]
    assert nation_stores == 735185, f"전국 점포수 불일치: {nation_stores} != 735,185"

    r_sido = query_one("SELECT SUM(total_stores) as sum_stores, COUNT(*) as cnt FROM regional_overall_stats WHERE region_type = 'SIDO'")
    sido_sum, sido_cnt = r_sido["sum_stores"], r_sido["cnt"]
    assert sido_cnt == 16, f"시도 수 불일치: {sido_cnt} != 16"
    assert sido_sum == 735185, f"16개 시도 점포수 합계 불일치: {sido_sum} != 735,185"

    r_sigungu = query_one("SELECT SUM(total_stores) as sum_stores, COUNT(*) as cnt FROM regional_overall_stats WHERE region_type = 'SIGUNGU'")
    sigungu_sum, sigungu_cnt = r_sigungu["sum_stores"], r_sigungu["cnt"]
    assert sigungu_cnt == 256, f"시군구 수 불일치: {sigungu_cnt} != 256"
    assert sigungu_sum == 735185, f"256개 시군구 점포수 합계 불일치: {sigungu_sum} != 735,185"


# 2. 브랜드 N:M 중복 없는 전체 집계 (외식업 총 점포수는 bizes_id 고유 카운트)
def test_02_zero_double_counting_in_overall_metrics():
    r1 = query_one("SELECT COUNT(*) as total_cnt, COUNT(DISTINCT bizes_id) as distinct_cnt FROM store_analytics_lookup")
    assert r1["total_cnt"] == r1["distinct_cnt"] == 735185, f"점포 고유성 위반: {r1}"

    r2 = query_one("""
        SELECT total_stores, brand_linked_stores + independent_stores as sum_parts
        FROM regional_overall_stats
        WHERE region_code = '00'
    """)
    assert r2["total_stores"] == r2["sum_parts"] == 735185, f"브랜드연결 + 독립점포 합계 불일치: {r2}"


# 3. 8대 대분류와 48중분류 점포수 대사 (합계 = 735,185)
def test_03_category_hierarchy_reconciliation():
    r1 = query_one("SELECT COUNT(DISTINCT category_major_id) as maj_cnt, COUNT(DISTINCT category_mid_id) as mid_cnt FROM regional_category_stats WHERE region_code = '00'")
    assert r1["maj_cnt"] == 8, f"대분류 수 불일치: {r1['maj_cnt']} != 8"
    assert r1["mid_cnt"] == 48, f"중분류 수 불일치: {r1['mid_cnt']} != 48"

    r2 = query_one("SELECT SUM(total_stores) as cat_total FROM regional_category_stats WHERE region_code = '00'")
    assert r2["cat_total"] == 735185, f"48대 중분류 점포수 합계 불일치: {r2['cat_total']} != 735,185"


# 4. 공식 가맹사업 브랜드와 실제 가맹점 구분 (발견 점포 수와 확인된 가맹점 수 분리)
def test_04_franchise_brand_vs_franchisee_decoupling():
    res = client.get("/api/v1/analytics/summary")
    assert res.status_code == 200
    data = res.json()["data"]

    assert data["franchise_confirmed_stores"] > 0
    assert "confirmed_franchisees" in data
    # 발견 점포 수와 확인된 가맹점 수는 별개 지표로 제공됨
    assert data["franchise_confirmed_stores"] >= data["confirmed_franchisees"]


# 5. 미검증 브랜드 후보 별도 조회 (UNVERIFIED 브랜드 분리)
def test_05_unverified_brand_candidates_isolation():
    res = client.get("/api/v1/analytics/brands/search?officiality=UNVERIFIED&limit=10")
    assert res.status_code == 200
    items = res.json()["data"]
    assert len(items) > 0
    for it in items:
        assert it["brand_officiality"] == "UNVERIFIED"


# 6. 미매칭 점포의 독립점 오판 방지 (UNMATCHED vs 독립 사업자)
def test_06_unmatched_stores_neutral_presentation():
    r1 = query_one("SELECT COUNT(*) as unmatched_cnt FROM store_analytics_lookup WHERE is_brand_linked = 0 AND brand_officiality = 'UNMATCHED'")
    assert r1["unmatched_cnt"] == 566890, f"미매칭 점포 수 불일치: {r1['unmatched_cnt']} != 566,890"

    # 메트릭 정의에 독립 사업자 확정이 아닌 미매칭 분류임이 명시되어 있는지 확인
    r2 = query_one("SELECT interpretation_guide FROM metric_definitions WHERE metric_key = 'INDEPENDENT_STORES'")
    assert "독립 사업자로 법적 확정된 것은 아님" in r2["interpretation_guide"]


# 7. 모호 업종 제외/포함 필터 (include_ambiguous=true/false 대사)
def test_07_ambiguous_category_filter():
    res_inc = client.get("/api/v1/analytics/categories?region_code=00&include_ambiguous=true")
    assert res_inc.status_code == 200
    data_inc = res_inc.json()["data"]
    sum_inc = sum(c["total_stores"] for c in data_inc)
    assert sum_inc == 735185, f"모호 포함 합계 불일치: {sum_inc} != 735,185"

    res_exc = client.get("/api/v1/analytics/categories?region_code=00&include_ambiguous=false")
    assert res_exc.status_code == 200
    data_exc = res_exc.json()["data"]
    sum_exc = sum(c["stores_excluding_ambiguous"] for c in data_exc)
    assert sum_exc == 735185 - 104060 == 631125, f"모호 제외 합계 불일치: {sum_exc} != 631,125"


# 8. 잘못된 지역코드 및 업종코드 입력 (404/400 예외 처리 및 SQL 인젝션 방어)
def test_08_invalid_inputs_and_injection_prevention():
    # 존재하지 않는 지역코드
    res_404 = client.get("/api/v1/analytics/regions/99999")
    assert res_404.status_code == 404

    # 잘못된 정렬 필드 (화이트리스트 차단 -> 400 Bad Request)
    res_bad_sort = client.get("/api/v1/analytics/regions?sort_by=INVALID_COL_DROP_TABLE")
    assert res_bad_sort.status_code == 400

    # 잘못된 BBOX 좌표
    res_bad_bbox = client.get("/api/v1/spatial/stores/bbox?min_lon=130.0&min_lat=38.0&max_lon=125.0&max_lat=35.0")
    assert res_bad_bbox.status_code == 400


# 9. 23개 복수 브랜드 점포 (고유 점포 735,185 + 23 = 735,208 링크 대사)
def test_09_multi_brand_shop_in_shop_stores():
    r1 = query_one("SELECT COUNT(*) as cnt FROM store_analytics_lookup WHERE is_multi_brand_store = 1")
    assert r1["cnt"] == 23, f"복수 브랜드 점포 수 불일치: {r1['cnt']} != 23"

    # 복수 브랜드 점포 상세 조회 시 보조 브랜드 알림 확인
    r2 = query_one("SELECT bizes_id FROM store_analytics_lookup WHERE is_multi_brand_store = 1 LIMIT 1")
    sample_bizes = r2["bizes_id"]
    res = client.get(f"/api/v1/spatial/stores/{sample_bizes}")
    assert res.status_code == 200
    ui_pres = res.json()["ui_presentation"]
    assert ui_pres["multi_brand_alert"] is not None


# 10. 브랜드·지역·업종 교차 필터
def test_10_cross_filters():
    # 서울 강남구(11680) 내 치킨·패스트푸드(CAT_MAJ_05) 점포 BBOX 검색
    res = client.get(
        "/api/v1/spatial/stores/bbox?min_lon=127.02&min_lat=37.49&max_lon=127.04&max_lat=37.51"
        "&category_major_id=CAT_MAJ_05&limit=20"
    )
    assert res.status_code == 200
    features = res.json()["features"]
    assert len(features) > 0
    for f in features:
        assert f["properties"]["category_major_id"] == "CAT_MAJ_05"


# 11. 대용량 BBOX 검색 (응답 유효성 및 limit 제한 동작)
def test_11_large_bbox_search_limits():
    res = client.get(
        "/api/v1/spatial/stores/bbox?min_lon=126.90&min_lat=37.45&max_lon=127.15&max_lat=37.60&limit=500"
    )
    assert res.status_code == 200
    features = res.json()["features"]
    assert len(features) <= 500


# 12. 페이지네이션 및 응답 제한
def test_12_pagination():
    res_p1 = client.get("/api/v1/analytics/regions?limit=10&offset=0")
    assert res_p1.status_code == 200
    data_p1 = res_p1.json()["data"]
    assert len(data_p1) == 10

    res_p2 = client.get("/api/v1/analytics/regions?limit=10&offset=10")
    assert res_p2.status_code == 200
    data_p2 = res_p2.json()["data"]
    assert len(data_p2) == 10

    # 1페이지와 2페이지의 첫 번째 항목이 서로 다른지 검증
    assert data_p1[0]["region_code"] != data_p2[0]["region_code"]


# 13. API 응답 스키마 및 에러 처리 (필수 메타데이터 4축 분리 포함)
def test_13_response_metadata_and_axes():
    res = client.get("/api/v1/analytics/summary")
    assert res.status_code == 200
    meta = res.json()["meta"]

    assert meta["data_reference_month"] == "2026-07"
    assert "735,185" in meta["universe_definition"]
    assert "decoupled_axes" in meta
    axes = meta["decoupled_axes"]
    assert "brand_officiality" in axes
    assert "store_match_status" in axes
    assert "operation_type" in axes
    assert "classification_status" in axes


# 14. 3D 상권 핫스팟 및 100m 격자 기둥 (Reference UI 연동 검증)
def test_14_3d_hotspots_and_grid_pillars():
    # 핫스팟 검증
    res_hot = client.get("/api/v1/spatial/hotspots")
    assert res_hot.status_code == 200
    hotspots = res_hot.json()["data"]
    assert len(hotspots) == 10
    gwangjin_hotspot = next(h for h in hotspots if "광진" in h["hotspot_name"])
    assert gwangjin_hotspot["sigungu_code"] == "11215"
    assert gwangjin_hotspot["pitch"] == 60.0

    # 광진구 100m 격자 기둥 검증
    res_grid = client.get("/api/v1/spatial/density/grid?sigungu_code=11215&limit=10")
    assert res_grid.status_code == 200
    grid_items = res_grid.json()["data"]
    assert len(grid_items) > 0
    assert grid_items[0]["column_height_m"] > 0


# 15. 원본 DB 불변성 검증 (기존 DB 3개 보존 및 레코드 불변)
def test_15_source_databases_immutability():
    con1 = sqlite3.connect(str(RAW_V2_DB_PATH))
    cnt1 = con1.cursor().execute("SELECT COUNT(*) FROM stores;").fetchone()[0]
    con1.close()
    assert cnt1 == 735185, f"V2 원본 점포 수 변조: {cnt1} != 735,185"

    con2 = sqlite3.connect(str(BRAND_MASTER_DB_PATH))
    cnt2 = con2.cursor().execute("SELECT COUNT(*) FROM brands;").fetchone()[0]
    links2 = con2.cursor().execute("SELECT COUNT(*) FROM store_brand_links;").fetchone()[0]
    con2.close()
    assert cnt2 == 5063, f"브랜드 마스터 건수 변조: {cnt2} != 5,063"
    assert links2 == 735208, f"브랜드 링크 건수 변조: {links2} != 735,208"

    con3 = sqlite3.connect(str(CATEGORY_MASTER_DB_PATH))
    cnt3 = con3.cursor().execute("SELECT COUNT(*) FROM store_category_classifications;").fetchone()[0]
    con3.close()
    assert cnt3 == 735185, f"카테고리 마스터 점포수 변조: {cnt3} != 735,185"
