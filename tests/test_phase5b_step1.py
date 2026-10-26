"""
Phase 5B Step 1: 공정위 거시통계 백엔드 API 종합 검증 테스트 스위트
프로젝트: D:/Franchise_Dashboard
위치: tests/test_phase5b_step1.py
"""

import json
import sqlite3
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import pytest
from datetime import datetime
from fastapi.testclient import TestClient

from src.stage4e.api.main import app
from src.stage4e.api.routers import ftc_macro

client = TestClient(app)


def test_01_ftc_status():
    """1. /api/v1/ftc/status 응답 검증"""
    res = client.get("/api/v1/ftc/status")
    assert res.status_code == 200, f"Status API 실패: {res.text}"
    body = res.json()
    assert body["status"] == "SUCCESS"
    data = body["data"]
    
    assert data["latest_benchmark_year"] == "2026"
    assert data["financial_year"] == "2025"
    assert data["display_label"] == "2026년 공정위 등록 기준 · 2025 회계연도 실적"
    assert data["snapshot_status"] == "LATEST_PROVIDED_SNAPSHOT"
    assert data["is_snapshot"] is True
    assert data["collected_at"] == "2026-10-13T17:53:05+09:00"
    assert data["collected_at"] in data["version_string"]
    assert data["total_records"] == 4521
    assert data["total_brands"] == 4515
    assert data["total_franchise_stores"] == 97627
    assert data["total_direct_stores"] == 4317
    assert data["available_years"] == ["2026", "2025", "2024", "2023"]
    assert "+09:00" in body["meta"]["timestamp"]
    assert res.headers.get("cache-control") == "public, max-age=3600"


def test_02_ftc_benchmark_hansik_2026():
    """2. 2026년 한식 응답과 실제 DB 수치 전수 대사"""
    res = client.get("/api/v1/ftc/benchmark/latest?category_major_id=CAT_MAJ_01")
    assert res.status_code == 200, f"Benchmark API 실패: {res.text}"
    body = res.json()
    assert body["status"] == "SUCCESS"
    data = body["data"]
    
    # 기본 메타
    assert data["benchmark_year"] == "2026"
    assert data["financial_year"] == "2025"
    assert data["is_fallback_applied"] is False
    assert data["fallback_reason"] is None
    assert data["category_major_id"] == "CAT_MAJ_01"
    assert data["category_major_name"] == "한식"
    assert data["mapped_ftc_categories"] == ["한식"]
    assert data["mapping_type"] == "ONE_TO_ONE"
    assert data["mapping_status"] == "PROPOSED_FOR_APPROVAL"
    
    # 표본 수 대사
    sample = data["sample_metrics"]
    assert sample["total_brand_records"] == 1858
    assert sample["sales_positive_records"] == 1204
    assert sample["sales_zero_records"] == 584
    assert sample["sales_null_records"] == 70
    assert sample["total_franchise_stores"] == 29557
    assert sample["total_direct_stores"] == 1248
    
    # 매출 지표 대사
    sales = data["sales_benchmarks"]
    assert sales["median_sales_thousand_krw"] == 361174.5
    assert sales["trimmed_mean_5pct_thousand_krw"] == 394210.78
    assert sales["store_weighted_avg_thousand_krw"] == 395702.93
    assert sales["simple_avg_positive_thousand_krw"] == 437251.23
    assert sales["all_records_avg_thousand_krw"] == 294435.39
    assert sales["weighted_avg_denominator_stores"] == 27187
    
    # 창업비용 구성항목 대사
    costs = data["startup_cost_components"]
    assert costs["reported_deposit_amount"]["median_thousand_krw"] == 13800.0
    assert costs["reported_deposit_amount"]["mean_thousand_krw"] == 15592.25
    assert costs["reported_deposit_amount"]["valid_count"] == 1855
    assert costs["reported_deposit_amount"]["field_note"] == "공정위 원본 depstAmt 값이며 구성항목 합계와 항상 일치하지 않습니다."
    
    assert costs["franchise_fee_jng_amt"]["median_thousand_krw"] == 5500.0
    assert costs["education_fee_edu_amt"]["median_thousand_krw"] == 3300.0
    assert costs["guarantee_fee_grnte_amt"]["median_thousand_krw"] == 2000.0
    assert costs["interior_cost_intrr_amt"]["median_thousand_krw"] == 44000.0
    assert costs["interior_cost_per_pyeong_3_3sqm"]["median_thousand_krw"] == 1760.0
    assert costs["tentative_derived_sum"]["median_thousand_krw"] == 133400.0
    assert costs["tentative_derived_sum"]["mean_thousand_krw"] == 147690.85
    assert costs["tentative_derived_sum"]["valid_count"] == 1858
    assert costs["tentative_derived_sum"]["is_official_stat"] is False
    
    # 품질 배지 확인
    notices = data["quality_notices"]
    types = [n["type"] for n in notices]
    assert "SNAPSHOT_NOTICE" in types
    assert "ZERO_SALES_NOTICE" in types
    
    assert "+09:00" in body["meta"]["timestamp"]


def test_03_all_8_major_categories():
    """3. 8대 대분류 전수 정상 응답 및 복수 매핑 계산 검증"""
    major_ids = [
        ("CAT_MAJ_01", "한식", "ONE_TO_ONE", ["한식"]),
        ("CAT_MAJ_02", "중식", "ONE_TO_ONE", ["중식"]),
        ("CAT_MAJ_03", "일식", "ONE_TO_ONE", ["일식"]),
        ("CAT_MAJ_04", "양식·세계음식", "MANY_TO_ONE", ["서양식", "기타 외국식"]),
        ("CAT_MAJ_05", "치킨·패스트푸드", "MANY_TO_ONE", ["치킨", "패스트푸드", "피자"]),
        ("CAT_MAJ_06", "분식·간편식", "ONE_TO_ONE", ["분식"]),
        ("CAT_MAJ_07", "카페·음료", "MANY_TO_ONE", ["커피", "음료 (커피 외)"]),
        ("CAT_MAJ_08", "베이커리·디저트", "MANY_TO_ONE", ["제과제빵", "아이스크림/빙수"]),
    ]
    for maj_id, maj_nm, m_type, ftc_cats in major_ids:
        res = client.get(f"/api/v1/ftc/benchmark/latest?category_major_id={maj_id}")
        assert res.status_code == 200, f"{maj_id} 응답 실패: {res.text}"
        data = res.json()["data"]
        assert data["category_major_id"] == maj_id
        assert data["category_major_name"] == maj_nm
        assert data["mapping_type"] == m_type
        assert data["mapped_ftc_categories"] == ftc_cats
        assert data["sample_metrics"]["total_brand_records"] > 0
        assert data["sales_benchmarks"]["median_sales_thousand_krw"] > 0


def test_04_unmapped_category_handling():
    """4. 매핑 불가 또는 존재하지 않는 카테고리 요청 시 HTTP 400 에러 처리"""
    res = client.get("/api/v1/ftc/benchmark/latest?category_major_id=CAT_MAJ_99")
    assert res.status_code == 400
    body = res.json()
    assert body["status"] == "UNMAPPED_CATEGORY"
    assert body["error_code"] == "ERR_CATEGORY_UNMAPPED"


def test_05_explicit_year_and_no_fallback():
    """5. 명시적 연도 조회 시 자동 대체 금지 및 404 처리"""
    # 2024년 명시 요청 -> 2024년 데이터가 나와야 하고 대체되지 않음
    res_2024 = client.get("/api/v1/ftc/benchmark/latest?category_major_id=CAT_MAJ_01&year=2024")
    assert res_2024.status_code == 200
    data_2024 = res_2024.json()["data"]
    assert data_2024["benchmark_year"] == "2024"
    assert data_2024["financial_year"] == "2023"
    assert data_2024["is_fallback_applied"] is False
    
    # 2027년 (부재 연도) 명시 요청 -> 다른 연도로 대체 금지, 404 NO_DATA_FOR_REQUESTED_YEAR 반환
    res_2027 = client.get("/api/v1/ftc/benchmark/latest?category_major_id=CAT_MAJ_01&year=2027")
    assert res_2027.status_code == 404
    body_2027 = res_2027.json()
    assert body_2027["status"] == "NO_DATA"
    assert body_2027["error_code"] == "NO_DATA_FOR_REQUESTED_YEAR"
    assert body_2027["requested_year"] == "2027"


def test_06_fallback_scenario_simulation(monkeypatch):
    """6. 운영 DB를 변경하지 않고 기본 최신연도 부재 시 2025 원자적 대체 시뮬레이션 검증"""
    orig_ftc_query_one = ftc_macro.ftc_query_one
    
    # chk_row 호출 시 2026년에 업종 레코드가 0건인 것으로 가상 모킹
    def mock_query_one(sql, params=()):
        if "WHERE jng_biz_crtr_yr = ? AND tpbiz_mclsf_nm IN" in sql and params and params[0] == "2026":
            return {"cnt": 0, "total_recs": 0}
        return orig_ftc_query_one(sql, params)
        
    monkeypatch.setattr(ftc_macro, "ftc_query_one", mock_query_one)
    # 캐시 무효화
    ftc_macro._CACHE_STORE.clear()
    
    res = client.get("/api/v1/ftc/benchmark/latest?category_major_id=CAT_MAJ_01")
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["benchmark_year"] == "2025"
    assert data["financial_year"] == "2024"
    assert data["is_fallback_applied"] is True
    assert "2025년 실적으로 원자적 대체" in data["fallback_reason"]
    
    # 품질 배지에 FALLBACK_NOTICE 포함 확인
    badges = [n["type"] for n in data["quality_notices"]]
    assert "FALLBACK_NOTICE" in badges
    
    # 캐시 복원
    ftc_macro._CACHE_STORE.clear()


def test_07_ftc_trends():
    """7. /api/v1/ftc/trends 4개년 시계열 추세 검증"""
    res = client.get("/api/v1/ftc/trends?category_major_id=CAT_MAJ_01")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "SUCCESS"
    data = body["data"]
    
    assert data["category_major_id"] == "CAT_MAJ_01"
    assert data["trend_mode"] == "FULL_POPULATION_CROSS_SECTIONAL"
    assert data["balanced_panel_active"] is False
    assert "생존편향" in data["panel_inactive_reason"]
    
    series = data["yearly_series"]
    assert len(series) == 4
    years = [s["benchmark_year"] for s in series]
    assert years == ["2023", "2024", "2025", "2026"]
    
    # 2026년 스냅샷 배지 확인
    s_2026 = next(s for s in series if s["benchmark_year"] == "2026")
    assert s_2026["is_snapshot"] is True
    assert s_2026["snapshot_badge"] == "최신 제공 스냅샷"
    
    # 거시 가이드 문구 검증
    assert "2026년은 수집 시점의 최신 제공 스냅샷으로 이전 연도와 모집단이 달라, 점포 수 차이를 산업 성장·감소로 직접 해석할 수 없습니다." in data["macro_guidance"]


def test_08_ftc_years():
    """8. /api/v1/ftc/years 연도 메타 목록 검증"""
    res = client.get("/api/v1/ftc/years")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "SUCCESS"
    data = body["data"]
    
    assert len(data) == 4
    assert data[0]["benchmark_year"] == "2026"
    assert data[0]["is_default"] is True
    assert data[0]["is_snapshot"] is True
    assert data[1]["benchmark_year"] == "2025"
    assert data[1]["is_default"] is False


def test_09_existing_apis_regression():
    """9. 기존 5대 분석 API 무손실 회귀 검증"""
    # 9.1 요약 API
    res_summary = client.get("/api/v1/analytics/summary")
    assert res_summary.status_code == 200, f"Summary 회귀 실패: {res_summary.text}"
    summary_data = res_summary.json()["data"]
    assert summary_data["total_stores"] == 735185
    assert summary_data["franchise_confirmed_stores"] == 48002
    
    # 9.2 시도 API
    res_regions = client.get("/api/v1/analytics/regions?region_type=SIDO")
    assert res_regions.status_code == 200
    assert len(res_regions.json()["data"]) == 16
    
    # 9.3 카테고리 API
    res_cats = client.get("/api/v1/analytics/categories")
    assert res_cats.status_code == 200
    assert len(res_cats.json()["data"]) == 48  # 48대 중분류 표준 체계 일치
    
    # 9.4 브랜드 검색 API
    res_brands = client.get("/api/v1/analytics/brands/search?keyword=스타벅스")
    assert res_brands.status_code == 200
    assert len(res_brands.json()["data"]) >= 1
    
    # 9.5 공간 핫스팟 API
    res_hotspots = client.get("/api/v1/spatial/hotspots")
    assert res_hotspots.status_code == 200
    assert len(res_hotspots.json()["data"]) >= 5


def test_10_dynamic_new_year_addition(monkeypatch):
    """10. 새 연도(예: 2027)가 DB에 추가된 상황 시뮬레이션 (운영 DB 미수정)"""
    mock_years = ["2027", "2026", "2025", "2024", "2023"]
    monkeypatch.setattr(ftc_macro, "get_ftc_available_years", lambda: mock_years)
    
    orig_ftc_query_one = ftc_macro.ftc_query_one
    def mock_query_one_for_2027(sql, params=()):
        if "FROM ftc_ingestion_audit_logs" in sql and params and params[0] == "2027":
            return {
                "jng_biz_crtr_yr": "2027",
                "post_total_count": 5000,
                "completed_at": "2027-04-15 10:30:00"
            }
        if "FROM ftc_brand_macro_records" in sql and params and params[0] == "2027":
            return {
                "total_brands": 4980,
                "total_franchise_stores": 105000,
                "total_direct_stores": 5200
            }
        # 2027년 한식 요약 레코드가 아직 0건인 상황 (직전 이용 가능 연도 2026으로 대체 트리거)
        if "WHERE jng_biz_crtr_yr = ? AND tpbiz_mclsf_nm IN" in sql and params and params[0] == "2027":
            return {"cnt": 0, "total_recs": 0}
        return orig_ftc_query_one(sql, params)

    monkeypatch.setattr(ftc_macro, "ftc_query_one", mock_query_one_for_2027)
    ftc_macro._CACHE_STORE.clear()

    # 10.2 /status 호출 시 2027을 최신 연도로 동적 반영
    res_status = client.get("/api/v1/ftc/status")
    assert res_status.status_code == 200
    st_data = res_status.json()["data"]
    assert st_data["latest_benchmark_year"] == "2027"
    assert st_data["financial_year"] == "2026"
    assert st_data["display_label"] == "2027년 공정위 등록 기준 · 2026 회계연도 실적"
    assert st_data["is_snapshot"] is True
    assert st_data["collected_at"] == "2027-04-15T19:30:00+09:00"
    assert st_data["available_years"] == mock_years
    assert "2027년 공정위 등록 기준 스냅샷" in st_data["version_string"]

    # 10.3 /years 호출 시 2027이 기본(is_default=True)이고, 2026이 완결 후보(is_default=False)로 자동 변경
    res_years = client.get("/api/v1/ftc/years")
    assert res_years.status_code == 200
    yr_data = res_years.json()["data"]
    assert yr_data[0]["benchmark_year"] == "2027"
    assert yr_data[0]["is_default"] is True
    assert yr_data[0]["is_snapshot"] is True
    assert "최신 스냅샷" in yr_data[0]["label"]
    assert yr_data[1]["benchmark_year"] == "2026"
    assert yr_data[1]["is_default"] is False
    assert yr_data[1]["is_snapshot"] is False
    assert "최신 완결 후보" in yr_data[1]["label"]

    # 10.4 /trends 호출 시 macro_guidance에 2027이 최신 스냅샷으로 동적 반영
    res_trends = client.get("/api/v1/ftc/trends?category_major_id=CAT_MAJ_01")
    assert res_trends.status_code == 200
    tr_data = res_trends.json()["data"]
    assert "2027년은 수집 시점의 최신 제공 스냅샷으로" in tr_data["macro_guidance"]

    # 10.5 /benchmark/latest 기본 조회 시 2027에 데이터가 없으므로 실제 이용 가능한 2026으로 원자적 대체
    res_bench = client.get("/api/v1/ftc/benchmark/latest?category_major_id=CAT_MAJ_01")
    assert res_bench.status_code == 200
    bn_data = res_bench.json()["data"]
    assert bn_data["benchmark_year"] == "2026"
    assert bn_data["financial_year"] == "2025"
    assert bn_data["is_fallback_applied"] is True
    assert "2027년 등록 데이터 부재로 이전 이용 가능 연도인 2026년 실적으로 원자적 대체" in bn_data["fallback_reason"]

    ftc_macro._CACHE_STORE.clear()


def test_11_utc_to_kst_conversion():
    """11. SQLite UTC CURRENT_TIMESTAMP -> KST(+09:00) 명시적 변환 및 표시 문구 일관성 검증"""
    # 11.1 단위 변환 함수 검증 (표준 포맷 'YYYY-MM-DD HH:MM:SS')
    utc_sample = "2026-10-13 08:53:05"
    expected_kst = "2026-10-13T17:53:05+09:00"
    assert ftc_macro.parse_utc_to_kst(utc_sample) == expected_kst

    # ISO 포맷 입력 케이스 검증
    iso_sample = "2026-01-01T00:00:00"
    assert ftc_macro.parse_utc_to_kst(iso_sample) == "2026-01-01T09:00:00+09:00"

    # 11.2 실제 API 응답에서의 UTC -> KST 변환 일관성 검증
    ftc_macro._CACHE_STORE.clear()
    res = client.get("/api/v1/ftc/status")
    assert res.status_code == 200
    data = res.json()["data"]

    # completed_at 원본(2026-10-13 08:53:05 UTC)이 KST ISO 문자열로 제공되는지 확인
    assert data["collected_at"] == "2026-10-13T17:53:05+09:00"
    assert data["collected_at"].endswith("+09:00")

    # version_string 내의 수집시각도 동일한 KST 기준인지 확인
    assert f"수집시각: {data['collected_at']}" in data["version_string"]
    assert "2026-10-13 08:53:05" not in data["version_string"]


def test_12_status_safety_when_latest_year_has_no_completed_audit(monkeypatch):
    """12. DB상 최신 연도에 COMPLETED 수집 기록이 없을 때의 /status 안전성 검증
    - 이전 연도의 post_total_count와 completed_at을 최신 연도 메타데이터로 위장 도용하지 않음.
    - COMPLETED 기록이 없는 연도는 기본값에서 제외되거나, 명확한 오류 상태(HTTP 500)를 반환함.
    """
    ftc_macro._CACHE_STORE.clear()

    # 시나리오 1: summary에 2027년이 존재하더라도, audit_logs에 2027년 COMPLETED 기록이 없는 경우
    # get_ftc_available_years()가 2027년을 기본값에서 자동으로 제외하고 2026년을 최신으로 선택하는지 검증
    orig_ftc_query_all = ftc_macro.ftc_query_all
    def mock_query_all(sql):
        # INNER JOIN 쿼리에서 2027년은 제외되고 2026, 2025, 2024, 2023만 반환
        if "INNER JOIN ftc_ingestion_audit_logs" in sql:
            return [
                {"jng_biz_crtr_yr": "2026"},
                {"jng_biz_crtr_yr": "2025"},
                {"jng_biz_crtr_yr": "2024"},
                {"jng_biz_crtr_yr": "2023"}
            ]
        return orig_ftc_query_all(sql)

    monkeypatch.setattr(ftc_macro, "ftc_query_all", mock_query_all)
    years = ftc_macro.get_ftc_available_years()
    assert years[0] == "2026"
    assert "2027" not in years

    res_status = client.get("/api/v1/ftc/status")
    assert res_status.status_code == 200
    st_data = res_status.json()["data"]
    # 2026년의 완료 메타데이터가 정상 표출되며 2027년이 섞이지 않음
    assert st_data["latest_benchmark_year"] == "2026"
    assert st_data["total_records"] == 4521
    assert st_data["collected_at"] == "2026-10-13T17:53:05+09:00"

    ftc_macro._CACHE_STORE.clear()

    # 시나리오 2: available_years가 2027년으로 전달되었으나 2027년에 대한 COMPLETED audit 로그가 전혀 없는 경우
    # 이전 연도(2026년) 로그를 도용하지 않고 HTTP 500 에러를 명확히 반환하는지 검증
    monkeypatch.setattr(ftc_macro, "get_ftc_available_years", lambda: ["2027", "2026", "2025"])

    orig_ftc_query_one = ftc_macro.ftc_query_one
    def mock_query_one_no_audit(sql, params=()):
        if "FROM ftc_ingestion_audit_logs" in sql and params and params[0] == "2027":
            # 2027년 COMPLETED 기록 없음
            return None
        return orig_ftc_query_one(sql, params)

    monkeypatch.setattr(ftc_macro, "ftc_query_one", mock_query_one_no_audit)

    res_err = client.get("/api/v1/ftc/status")
    assert res_err.status_code == 500
    err_body = res_err.json()
    assert err_body["detail"]["status"] == "ERROR"
    assert err_body["detail"]["error_code"] == "ERR_FTC_STATUS_NO_COMPLETED_AUDIT"
    assert "2027" in err_body["detail"]["message"]

    ftc_macro._CACHE_STORE.clear()


if __name__ == "__main__":
    pytest.main(["-v", __file__])


