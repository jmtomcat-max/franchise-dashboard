"""
Phase 5B Step 2 보완 테스트: 최신 연도 자동 선택 vs 직접 지정 분리 및 원자적 대체 검증
위치: tests/test_phase5b_step2_supplement.py
"""

from pathlib import Path
from fastapi.testclient import TestClient
import pytest

from src.stage4e.api.main import app
from src.stage4e.api.routers import ftc_macro

client = TestClient(app)


def test_auto_year_selection_without_year_param():
    """
    1. 기본 선택 (year 파라미터 미전송):
       백엔드가 최신 DB 연도를 자동 판정하여 2026년 데이터를 반환하고,
       is_fallback_applied는 False여야 함.
    """
    ftc_macro._CACHE_STORE.clear()
    res = client.get("/api/v1/ftc/benchmark/latest?category_major_id=CAT_MAJ_01")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "SUCCESS"
    data = body["data"]
    assert data["benchmark_year"] == "2026"
    assert data["financial_year"] == "2025"
    assert data["is_fallback_applied"] is False
    assert data["fallback_reason"] is None


def test_manual_year_selection_with_explicit_year_param():
    """
    2. 사용자가 연도를 직접 지정 (year=2025 전송):
       백엔드는 지정된 2025년 데이터를 정확히 반환하며,
       is_fallback_applied는 False여야 함.
    """
    ftc_macro._CACHE_STORE.clear()
    res = client.get("/api/v1/ftc/benchmark/latest?category_major_id=CAT_MAJ_01&year=2025")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "SUCCESS"
    data = body["data"]
    assert data["benchmark_year"] == "2025"
    assert data["financial_year"] == "2024"
    assert data["is_fallback_applied"] is False


def test_manual_year_selection_nonexistent_year_strictly_no_fallback():
    """
    3. 사용자가 직접 지정한 연도가 존재하지 않을 경우 (year=2099):
       자동 대체되지 않고 404 NO_DATA 및 NO_DATA_FOR_REQUESTED_YEAR 에러를 명확히 반환해야 함.
    """
    ftc_macro._CACHE_STORE.clear()
    res = client.get("/api/v1/ftc/benchmark/latest?category_major_id=CAT_MAJ_01&year=2099")
    assert res.status_code == 404
    body = res.json()
    assert body["status"] == "NO_DATA"
    assert body["error_code"] == "NO_DATA_FOR_REQUESTED_YEAR"
    assert body["requested_year"] == "2099"


def test_auto_year_selection_atomic_fallback_when_latest_year_missing(monkeypatch):
    """
    4. 최신 연도 자동 선택(year 미전송) 상태에서 최신 연도(2026)에 해당 업종 데이터가 없을 때:
       백엔드가 원자적으로 이전 연도(2025)로 단일 대체하고
       is_fallback_applied=True 및 fallback_reason을 반환하며 FALLBACK_NOTICE 배지가 포함됨.
    """
    orig_ftc_query_one = ftc_macro.ftc_query_one
    
    def mock_query_one(sql, params=()):
        if "WHERE jng_biz_crtr_yr = ? AND tpbiz_mclsf_nm IN" in sql and params and params[0] == "2026":
            return {"cnt": 0, "total_recs": 0}
        return orig_ftc_query_one(sql, params)
        
    monkeypatch.setattr(ftc_macro, "ftc_query_one", mock_query_one)
    ftc_macro._CACHE_STORE.clear()
    
    try:
        # year 파라미터 없이 호출 (클라이언트 기본 선택 상태)
        res = client.get("/api/v1/ftc/benchmark/latest?category_major_id=CAT_MAJ_01")
        assert res.status_code == 200
        body = res.json()
        assert body["status"] == "SUCCESS"
        data = body["data"]
        
        # 2025년으로 안전하게 자동 대체
        assert data["benchmark_year"] == "2025"
        assert data["financial_year"] == "2024"
        assert data["is_fallback_applied"] is True
        assert "원자적 대체" in data["fallback_reason"]
        assert data["category_major_name"] == "한식"
        assert data["sample_metrics"]["total_brand_records"] > 0
        
        # 프런트엔드에서 표시할 대체 알림 배너 근거 검증
        notice_types = [n["type"] for n in data.get("quality_notices", [])]
        assert "FALLBACK_NOTICE" in notice_types
    finally:
        ftc_macro._CACHE_STORE.clear()
