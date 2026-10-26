"""
Phase 5B: 공정거래위원회 외식업 거시통계 지도·대시보드 통합 라우터
프로젝트: D:/Franchise_Dashboard
위치: src/stage4e/api/routers/ftc_macro.py

엔드포인트:
- GET /api/v1/ftc/status
- GET /api/v1/ftc/benchmark/latest
- GET /api/v1/ftc/trends
- GET /api/v1/ftc/years
"""

import json
import math
import statistics
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple

from fastapi import APIRouter, Query, HTTPException, Response, status
from fastapi.responses import JSONResponse

from src.stage4e.api.ftc_database import (
    ftc_query_one,
    ftc_query_all,
    get_ftc_cached_connection,
)
from src.stage4e.api.ftc_schemas import (
    FtcStatusResponse,
    FtcBenchmarkResponse,
    FtcTrendsResponse,
    FtcYearsResponse,
    YearlyTrendItem,
    QualityNotice,
)

router = APIRouter(prefix="/api/v1/ftc", tags=["FTC Macro Analytics"])

# 한국 표준시 (KST, UTC+9)
KST = timezone(timedelta(hours=9))

# 설정 파일 경로
BASE_DIR = Path(__file__).resolve().parents[4]
MAPPING_CONFIG_PATH = BASE_DIR / "config" / "category_ftc_mapping_v1.json"

# In-Memory 캐시 저장소 (Thread-safe dict)
_CACHE_STORE: Dict[str, Tuple[datetime, Any]] = {}
CACHE_TTL_SECONDS = 3600  # 1시간 캐시

SIDO_TO_FTC_REGION: Dict[str, str] = {
    "11": "서울",
    "26": "부산",
    "27": "대구",
    "28": "인천",
    "29": "광주",
    "12": "광주",
    "30": "대전",
    "31": "울산",
    "36": "세종",
    "41": "경기",
    "42": "강원",
    "51": "강원",
    "43": "충북",
    "44": "충남",
    "45": "전북",
    "52": "전북",
    "46": "전남",
    "47": "경북",
    "48": "경남",
    "50": "제주",
}


def get_current_kst_iso() -> str:
    """한국 표준시 ISO-8601 타임스탬프를 반환합니다."""
    return datetime.now(KST).isoformat()


def parse_utc_to_kst(utc_str: str) -> str:
    """
    SQLite CURRENT_TIMESTAMP(UTC 문자열, 예: '2026-10-13 08:53:05')을
    한국 표준시(KST, UTC+9) ISO-8601 형식(+09:00 명시)으로 변환합니다.
    예: '2026-10-13T17:53:05+09:00'
    """
    try:
        # 형식 1: 'YYYY-MM-DD HH:MM:SS'
        dt_utc = datetime.strptime(utc_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
    except ValueError:
        try:
            # 형식 2: 'YYYY-MM-DDTHH:MM:SS'
            dt_utc = datetime.fromisoformat(utc_str).replace(tzinfo=timezone.utc)
        except Exception:
            # 파싱 실패 시 현재 KST 반환
            return get_current_kst_iso()
    dt_kst = dt_utc.astimezone(KST)
    return dt_kst.isoformat()


def load_mapping_config() -> Dict[str, Any]:
    """업종 매핑 설정 파일을 로드합니다."""
    if not MAPPING_CONFIG_PATH.exists():
        raise FileNotFoundError(f"매핑 설정 파일을 찾을 수 없습니다: {MAPPING_CONFIG_PATH}")
    with open(MAPPING_CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def get_ftc_available_years() -> List[str]:
    """
    DB에서 수집 완료(status = 'COMPLETED') 감사 기록이 존재하며
    실제 업종 요약(ftc_industry_macro_summary) 데이터가 존재하는 유효 기준연도 목록을
    최신순(내림차순)으로 동적 추출합니다.
    수집 미완료(IN_PROGRESS / FAILED) 상태이거나 완료 기록이 없는 연도는
    기본값 및 제공 연도 목록에서 원천적으로 제외됩니다.
    """
    rows = ftc_query_all("""
        SELECT DISTINCT s.jng_biz_crtr_yr
        FROM ftc_industry_macro_summary s
        INNER JOIN ftc_ingestion_audit_logs a 
            ON s.jng_biz_crtr_yr = a.jng_biz_crtr_yr
        WHERE a.status = 'COMPLETED'
        ORDER BY s.jng_biz_crtr_yr DESC
    """)
    if rows:
        return [r["jng_biz_crtr_yr"] for r in rows]

    # audit_logs에만 완료된 경우 폴백 (데이터 적재 정합성 대비)
    audit_rows = ftc_query_all("""
        SELECT DISTINCT jng_biz_crtr_yr
        FROM ftc_ingestion_audit_logs
        WHERE status = 'COMPLETED'
        ORDER BY jng_biz_crtr_yr DESC
    """)
    if audit_rows:
        return [r["jng_biz_crtr_yr"] for r in audit_rows]

    # COMPLETED 기록이 전혀 없는 극단적 상황 시 summary 단독 (status 조회 시 명확한 오류 발생)
    fallback_rows = ftc_query_all("""
        SELECT DISTINCT jng_biz_crtr_yr
        FROM ftc_industry_macro_summary
        ORDER BY jng_biz_crtr_yr DESC
    """)
    return [r["jng_biz_crtr_yr"] for r in fallback_rows]


def calc_median(values: List[float]) -> float:
    """중앙값을 계산합니다."""
    if not values:
        return 0.0
    return float(statistics.median(values))


def calc_trimmed_mean_5pct(values: List[float]) -> float:
    """상하위 5% 절사평균을 계산합니다."""
    if not values:
        return 0.0
    n = len(values)
    k = int(math.floor(n * 0.05))
    sorted_vals = sorted(values)
    trimmed_vals = sorted_vals[k : n - k] if k > 0 else sorted_vals
    if not trimmed_vals:
        return float(statistics.mean(values))
    return float(statistics.mean(trimmed_vals))


# ==============================================================================
# 1. GET /api/v1/ftc/status
# ==============================================================================

@router.get(
    "/status",
    response_model=FtcStatusResponse,
    summary="공정위 거시통계 최신 적재 상태 및 메타데이터 조회",
    description="대시보드 헤더 및 벤치마크 패널에 표출할 최신 기준연도, 회계연도, 수집 시각, 확정 모수, 버전 문자열을 반환합니다."
)
def get_ftc_status(response: Response):
    cache_key = "ftc_status"
    now = datetime.now()
    if cache_key in _CACHE_STORE:
        cached_time, cached_val = _CACHE_STORE[cache_key]
        if (now - cached_time).total_seconds() < CACHE_TTL_SECONDS:
            response.headers["Cache-Control"] = "no-cache"
            return cached_val

    available_years = get_ftc_available_years()
    if not available_years:
        raise HTTPException(
            status_code=500,
            detail={"status": "ERROR", "error_code": "ERR_FTC_STATUS_FAILED", "message": "수집 완료된 공정위 적재 연도 데이터를 찾을 수 없습니다."}
        )

    latest_year = available_years[0]

    # 최신 감사 로그 조회 (해당 최신 연도의 완료 기록)
    audit = ftc_query_one("""
        SELECT jng_biz_crtr_yr, post_total_count, completed_at
        FROM ftc_ingestion_audit_logs
        WHERE status = 'COMPLETED' AND jng_biz_crtr_yr = ?
        ORDER BY audit_id DESC
        LIMIT 1
    """, (latest_year,))
    
    if not audit:
        # 최신 연도에 COMPLETED 수집 기록이 없을 때:
        # 이전 연도의 post_total_count와 completed_at을 최신 연도 메타데이터로 섞어 표시하는 것을 엄격히 차단합니다.
        # 다른 연도의 완료 로그를 도용하지 않고 명확한 오류(HTTP 500)를 반환합니다.
        raise HTTPException(
            status_code=500,
            detail={
                "status": "ERROR",
                "error_code": "ERR_FTC_STATUS_NO_COMPLETED_AUDIT",
                "message": f"최신 기준연도({latest_year})에 대한 수집 완료(COMPLETED) 기록이 존재하지 않아 메타데이터를 제공할 수 없습니다.",
                "latest_year": latest_year
            }
        )

    raw_utc_completed_at = audit["completed_at"]
    kst_collected_at = parse_utc_to_kst(raw_utc_completed_at)
    total_records = audit["post_total_count"]

    # 브랜드 수 및 점포 수 합계 조회
    summary_totals = ftc_query_one("""
        SELECT 
            COUNT(DISTINCT als_brand_mng_no) as total_brands,
            SUM(frcs_cnt) as total_franchise_stores,
            SUM(dms_cnt) as total_direct_stores
        FROM ftc_brand_macro_records
        WHERE jng_biz_crtr_yr = ?
    """, (latest_year,))

    total_brands = summary_totals["total_brands"] if summary_totals else total_records
    total_franchise_stores = summary_totals["total_franchise_stores"] if summary_totals else 0
    total_direct_stores = summary_totals["total_direct_stores"] if summary_totals else 0

    # 회계연도는 기준연도 - 1
    financial_year = str(int(latest_year) - 1)

    result_data = {
        "status": "SUCCESS",
        "data": {
            "latest_benchmark_year": latest_year,
            "financial_year": financial_year,
            "display_label": f"{latest_year}년 공정위 등록 기준 · {financial_year} 회계연도 실적",
            "snapshot_status": "LATEST_PROVIDED_SNAPSHOT",
            "is_snapshot": True,  # DB의 최신 등록 연도는 수집 시점 기준 최신 스냅샷
            "collected_at": kst_collected_at,
            "total_records": total_records,
            "total_brands": total_brands,
            "total_franchise_stores": total_franchise_stores,
            "total_direct_stores": total_direct_stores,
            "available_years": available_years,
            "version_string": f"{latest_year}년 공정위 등록 기준 스냅샷 (수집시각: {kst_collected_at}, 확정모수: {total_records}건)",
            "macro_notice": "수집 시점 기준 최신 제공 스냅샷이며 향후 모수가 변동될 수 있습니다."
        },
        "meta": {
            "calculation_method": "Actual DB query from ftc_ingestion_audit_logs and ftc_brand_macro_records",
            "timestamp": get_current_kst_iso()
        }
    }

    _CACHE_STORE[cache_key] = (now, result_data)
    response.headers["Cache-Control"] = "no-cache"
    return result_data


# ==============================================================================
# 2. GET /api/v1/ftc/benchmark/latest
# ==============================================================================

@router.get(
    "/benchmark/latest",
    summary="업종별 공정위 거시 벤치마크 조회",
    description="8대 대분류 ID에 대응하는 벤치마크를 반환합니다. 기본 조회 시 최신 연도 부재 시 실제 이용 가능한 이전 연도로 원자적 대체합니다."
)
def get_latest_benchmark(
    response: Response,
    category_major_id: str = Query(..., description="8대 대분류 코드 (ALL 또는 CAT_MAJ_01 ~ CAT_MAJ_08)"),
    year: Optional[str] = Query(None, description="기준연도 수동 지정 (기본값: 최신연도). 명시적 지정 시 자동 대체되지 않음."),
    sido_code: Optional[str] = Query(None, description="시도 코드 (예: '11' 서울, '41' 경기, '00' 전국)")
):
    mapping_cfg = load_mapping_config()
    category_map = {m["category_major_id"]: m for m in mapping_cfg["mappings"]}
    all_ftc_cats: List[str] = []
    for m in mapping_cfg["mappings"]:
        for fc in m["ftc_categories"]:
            if fc not in all_ftc_cats:
                all_ftc_cats.append(fc)
    category_map["ALL"] = {
        "category_major_id": "ALL",
        "category_major_name": "전체 외식업",
        "mapping_type": "MANY_TO_ONE",
        "status": "PROPOSED_FOR_APPROVAL",
        "ftc_categories": all_ftc_cats,
    }

    if category_major_id not in category_map:
        return JSONResponse(
            status_code=400,
            content={
                "status": "UNMAPPED_CATEGORY",
                "error_code": "ERR_CATEGORY_UNMAPPED",
                "message": f"선택하신 업종({category_major_id})은 공정위 거시통계와 배타적 매핑이 불가합니다 (상태: UNMAPPED_REVIEW)."
            }
        )

    cat_info = category_map[category_major_id]
    target_ftc_categories = cat_info["ftc_categories"]

    available_years = get_ftc_available_years()
    if not available_years:
        raise HTTPException(status_code=500, detail="이용 가능한 공정위 연도 데이터가 없습니다.")

    db_latest_year = available_years[0]

    # 연도 결정 로직
    is_explicit_year = (year is not None)
    target_year = year if is_explicit_year else db_latest_year

    # 명시적 연도 요청 시 유효성 검증
    if is_explicit_year:
        exists_check = ftc_query_one("""
            SELECT 1 FROM ftc_industry_macro_summary 
            WHERE jng_biz_crtr_yr = ? LIMIT 1
        """, (target_year,))
        if not exists_check:
            return JSONResponse(
                status_code=404,
                content={
                    "status": "NO_DATA",
                    "error_code": "NO_DATA_FOR_REQUESTED_YEAR",
                    "message": f"요청하신 연도({target_year})에 해당하는 공정위 등록 데이터가 존재하지 않습니다. 사용자가 지정한 연도는 다른 연도로 자동 대체되지 않습니다.",
                    "requested_year": target_year
                }
            )

    # 시도 지역 매핑 (예: '11' -> '서울')
    norm_sido = (sido_code or "00").strip()[:2]
    rgn_name = SIDO_TO_FTC_REGION.get(norm_sido) if norm_sido != "00" else None

    # 캐시 확인
    cache_key = f"benchmark_{category_major_id}_{target_year}_{is_explicit_year}_{norm_sido}"
    now = datetime.now()
    if cache_key in _CACHE_STORE:
        cached_time, cached_val = _CACHE_STORE[cache_key]
        if (now - cached_time).total_seconds() < CACHE_TTL_SECONDS:
            response.headers["Cache-Control"] = "no-cache"
            return cached_val

    # 대체(Fallback) 여부 판단
    is_fallback = False
    fallback_reason = None
    applied_year = target_year

    placeholders = ",".join(["?"] * len(target_ftc_categories))
    
    # 1. target_year에 매핑된 업종 데이터가 존재하는지 확인
    chk_row = ftc_query_one(f"""
        SELECT COUNT(*) as cnt, SUM(record_count) as total_recs
        FROM ftc_industry_macro_summary
        WHERE jng_biz_crtr_yr = ? AND tpbiz_mclsf_nm IN ({placeholders})
    """, tuple([applied_year] + target_ftc_categories))

    has_data = (chk_row and chk_row["total_recs"] is not None and chk_row["total_recs"] > 0)

    if not has_data:
        if is_explicit_year:
            # 사용자가 직접 연도를 명시한 경우 -> 자동 대체 절대 금지, 404 반환
            return JSONResponse(
                status_code=404,
                content={
                    "status": "NO_DATA",
                    "error_code": "NO_DATA_FOR_REQUESTED_YEAR",
                    "message": f"요청하신 연도({target_year})에 해당 업종({cat_info['category_major_name']}) 데이터가 존재하지 않습니다. 사용자가 지정한 연도는 다른 연도로 자동 대체되지 않습니다.",
                    "requested_year": target_year
                }
            )
        else:
            # 기본 최신연도 조회에서 데이터가 없는 경우 -> DB에서 실제 이용 가능한 이전 연도들을 역순 탐색
            found_fallback_year = None
            for prior_yr in available_years:
                if prior_yr >= applied_year:
                    continue
                prior_chk = ftc_query_one(f"""
                    SELECT SUM(record_count) as total_recs
                    FROM ftc_industry_macro_summary
                    WHERE jng_biz_crtr_yr = ? AND tpbiz_mclsf_nm IN ({placeholders})
                """, tuple([prior_yr] + target_ftc_categories))
                if prior_chk and prior_chk["total_recs"] and prior_chk["total_recs"] > 0:
                    found_fallback_year = prior_yr
                    break

            if not found_fallback_year:
                # 모든 연도에 데이터가 없는 경우
                return JSONResponse(
                    status_code=404,
                    content={
                        "status": "NO_DATA",
                        "error_code": "NO_DATA_FOR_CATEGORY",
                        "message": f"선택하신 업종({cat_info['category_major_name']})에 대해 이용 가능한 공정위 등록 데이터가 존재하지 않습니다."
                    }
                )

            # 이용 가능한 실제 이전 연도로 원자적 대체
            applied_year = found_fallback_year
            is_fallback = True
            fallback_reason = f"{db_latest_year}년 등록 데이터 부재로 이전 이용 가능 연도인 {applied_year}년 실적으로 원자적 대체 표출 중"

    # 통계 집계 수행 (원자적 단일 연도)
    conn = get_ftc_cached_connection()
    cur = conn.cursor()

    # 전국 기준 중앙값 (지역 선택 시 전국 대비 격차 계산용)
    cur.execute(f"""
        SELECT avg_sls_amt 
        FROM ftc_brand_macro_records
        WHERE jng_biz_crtr_yr = ? AND tpbiz_mclsf_nm IN ({placeholders}) AND avg_sls_amt > 0
        ORDER BY avg_sls_amt ASC
    """, tuple([applied_year] + target_ftc_categories))
    nat_sales_values = [r["avg_sls_amt"] for r in cur.fetchall()]
    nat_median_sls = round(calc_median(nat_sales_values), 1)

    cur.execute(f"""
        SELECT tentative_startup_cost_thousand
        FROM ftc_brand_macro_records
        WHERE jng_biz_crtr_yr = ? AND tpbiz_mclsf_nm IN ({placeholders}) AND tentative_startup_cost_thousand IS NOT NULL
    """, tuple([applied_year] + target_ftc_categories))
    nat_cost_values = [r[0] for r in cur.fetchall()]
    nat_median_cost = round(calc_median(nat_cost_values), 1)

    # 시도 필터 적용 가능 여부 확인 (해당 시도 + 업종에 양수 매출 레코드가 있는지)
    region_fallback = False
    active_rgn_name = rgn_name
    if active_rgn_name:
        cur.execute(f"""
            SELECT COUNT(*) as pos_cnt
            FROM ftc_brand_macro_records
            WHERE jng_biz_crtr_yr = ? AND tpbiz_mclsf_nm IN ({placeholders}) AND jnghq_rgn_nm = ? AND avg_sls_amt > 0
        """, tuple([applied_year] + target_ftc_categories + [active_rgn_name]))
        rgn_chk = cur.fetchone()
        if not rgn_chk or (rgn_chk["pos_cnt"] or 0) == 0:
            region_fallback = True
            active_rgn_name = None

    if active_rgn_name:
        # 선택 시도(jnghq_rgn_nm) 기준 원천 레코드 집계
        cur.execute(f"""
            SELECT 
                COUNT(*) as total_brand_records,
                SUM(CASE WHEN avg_sls_amt > 0 THEN 1 ELSE 0 END) as sales_positive_records,
                SUM(CASE WHEN avg_sls_amt = 0 THEN 1 ELSE 0 END) as sales_zero_records,
                SUM(CASE WHEN avg_sls_amt IS NULL THEN 1 ELSE 0 END) as sales_null_records,
                SUM(COALESCE(frcs_cnt, 0)) as total_franchise_stores,
                SUM(COALESCE(dms_cnt, 0)) as total_direct_stores,
                SUM(CASE WHEN avg_sls_amt > 0 THEN avg_sls_amt ELSE 0 END) as total_sls_amount,
                SUM(CASE WHEN avg_sls_amt > 0 AND frcs_cnt > 0 THEN avg_sls_amt * frcs_cnt ELSE 0 END) as total_weighted_sls_amount,
                SUM(CASE WHEN avg_sls_amt > 0 AND frcs_cnt > 0 THEN frcs_cnt ELSE 0 END) as weighted_avg_denominator_stores
            FROM ftc_brand_macro_records
            WHERE jng_biz_crtr_yr = ? AND tpbiz_mclsf_nm IN ({placeholders}) AND jnghq_rgn_nm = ?
        """, tuple([applied_year] + target_ftc_categories + [active_rgn_name]))
        sum_row = dict(cur.fetchone())
    else:
        # 전국 기준 Summary 테이블 합산
        cur.execute(f"""
            SELECT 
                SUM(record_count) as total_brand_records,
                SUM(sls_positive_record_count) as sales_positive_records,
                SUM(sls_zero_record_count) as sales_zero_records,
                SUM(sls_null_record_count) as sales_null_records,
                SUM(sum_frcs_cnt) as total_franchise_stores,
                SUM(sum_dms_cnt) as total_direct_stores,
                SUM(sum_sls_amount) as total_sls_amount,
                SUM(sum_weighted_sls_amount) as total_weighted_sls_amount,
                SUM(denom_store_weighted_sls) as weighted_avg_denominator_stores
            FROM ftc_industry_macro_summary
            WHERE jng_biz_crtr_yr = ? AND tpbiz_mclsf_nm IN ({placeholders})
        """, tuple([applied_year] + target_ftc_categories))
        sum_row = dict(cur.fetchone())

    pos_cnt = sum_row["sales_positive_records"] or 0
    zero_cnt = sum_row["sales_zero_records"] or 0
    tot_amt = sum_row["total_sls_amount"] or 0.0
    simple_avg_pos = round(tot_amt / pos_cnt, 2) if pos_cnt > 0 else 0.0
    all_rec_avg = round(tot_amt / (pos_cnt + zero_cnt), 2) if (pos_cnt + zero_cnt) > 0 else 0.0

    weighted_denom = sum_row["weighted_avg_denominator_stores"] or 0
    weighted_amt = sum_row["total_weighted_sls_amount"] or 0.0
    store_weighted_avg = round(weighted_amt / weighted_denom, 2) if weighted_denom > 0 else 0.0

    # 2. 개별 레코드에서 매출 중앙값 & 5% 절사평균 계산
    if active_rgn_name:
        cur.execute(f"""
            SELECT avg_sls_amt 
            FROM ftc_brand_macro_records
            WHERE jng_biz_crtr_yr = ? AND tpbiz_mclsf_nm IN ({placeholders}) AND jnghq_rgn_nm = ? AND avg_sls_amt > 0
            ORDER BY avg_sls_amt ASC
        """, tuple([applied_year] + target_ftc_categories + [active_rgn_name]))
        sales_values = [r["avg_sls_amt"] for r in cur.fetchall()]
    else:
        sales_values = nat_sales_values

    median_sls = round(calc_median(sales_values), 1)
    trimmed_5pct = round(calc_trimmed_mean_5pct(sales_values), 2)

    # 3. 창업비용 구성항목 계산
    cost_cols = [
        ("reported_deposit_amount", "depst_amt", "공정위 원본 depstAmt 값이며 구성항목 합계와 항상 일치하지 않습니다.", None, None),
        ("franchise_fee_jng_amt", "jng_bzmn_jng_amt", None, None, None),
        ("education_fee_edu_amt", "jng_bzmn_edu_amt", None, None, None),
        ("guarantee_fee_grnte_amt", "jng_bzmn_grnte_amt", None, None, None),
        ("interior_cost_intrr_amt", "intrr_amt", None, None, None),
        ("interior_cost_per_pyeong_3_3sqm", "unit_area_intrr_amt", None, None, None),
        ("tentative_derived_sum", "tentative_startup_cost_thousand", None, False, "본 합계는 공정위 공인 공식 총창업비용이 아니며 원본 항목(예치금+기타+인테리어)을 합산한 잠정 파생 지표입니다.")
    ]
    startup_costs = {}
    for key_name, col_name, note, is_off, disc in cost_cols:
        if active_rgn_name:
            cur.execute(f"""
                SELECT {col_name}
                FROM ftc_brand_macro_records
                WHERE jng_biz_crtr_yr = ? AND tpbiz_mclsf_nm IN ({placeholders}) AND jnghq_rgn_nm = ? AND {col_name} IS NOT NULL
            """, tuple([applied_year] + target_ftc_categories + [active_rgn_name]))
        else:
            cur.execute(f"""
                SELECT {col_name}
                FROM ftc_brand_macro_records
                WHERE jng_biz_crtr_yr = ? AND tpbiz_mclsf_nm IN ({placeholders}) AND {col_name} IS NOT NULL
            """, tuple([applied_year] + target_ftc_categories))
        vals = [r[0] for r in cur.fetchall()]
        cost_item = {
            "median_thousand_krw": round(calc_median(vals), 1) if vals else 0.0,
            "mean_thousand_krw": round(float(statistics.mean(vals)), 2) if vals else 0.0,
            "valid_count": len(vals)
        }
        if note:
            cost_item["field_note"] = note
        if is_off is not None:
            cost_item["is_official_stat"] = is_off
        if disc:
            cost_item["disclaimer"] = disc
        startup_costs[key_name] = cost_item

    # 3-B. 8대 업종별 매출 vs 창업비용 한눈에 비교 배열 (category_comparison) 생성
    category_comparison = []
    for m_item in mapping_cfg["mappings"]:
        cid = m_item["category_major_id"]
        cname = m_item["category_major_name"]
        fcats = m_item["ftc_categories"]
        c_ph = ",".join(["?"] * len(fcats))
        if active_rgn_name:
            cur.execute(f"""
                SELECT avg_sls_amt, tentative_startup_cost_thousand
                FROM ftc_brand_macro_records
                WHERE jng_biz_crtr_yr = ? AND tpbiz_mclsf_nm IN ({c_ph}) AND jnghq_rgn_nm = ?
            """, tuple([applied_year] + fcats + [active_rgn_name]))
            c_rows = cur.fetchall()
            c_sales = [r["avg_sls_amt"] for r in c_rows if r["avg_sls_amt"] and r["avg_sls_amt"] > 0]
            c_costs = [r["tentative_startup_cost_thousand"] for r in c_rows if r["tentative_startup_cost_thousand"] is not None]
        else:
            c_sales = []
            c_costs = []

        # 해당 시도에 표본이 없거나 전국 모드인 경우 전국 표본 사용
        used_national_for_cat = False
        if not c_sales:
            used_national_for_cat = bool(active_rgn_name)
            cur.execute(f"""
                SELECT avg_sls_amt, tentative_startup_cost_thousand
                FROM ftc_brand_macro_records
                WHERE jng_biz_crtr_yr = ? AND tpbiz_mclsf_nm IN ({c_ph})
            """, tuple([applied_year] + fcats))
            c_rows = cur.fetchall()
            c_sales = [r["avg_sls_amt"] for r in c_rows if r["avg_sls_amt"] and r["avg_sls_amt"] > 0]
            c_costs = [r["tentative_startup_cost_thousand"] for r in c_rows if r["tentative_startup_cost_thousand"] is not None]

        med_s = round(calc_median(c_sales), 1) if c_sales else 0.0
        med_c = round(calc_median(c_costs), 1) if c_costs else 0.0
        ratio = round(med_s / med_c, 2) if med_c > 0 else 0.0
        category_comparison.append({
            "category_major_id": cid,
            "category_major_name": cname,
            "brand_count": len(c_sales),
            "median_sales_thousand_krw": med_s,
            "median_cost_thousand_krw": med_c,
            "sales_to_cost_ratio": ratio,
            "is_national_fallback": used_national_for_cat
        })

    # 연매출 내림차순 정렬
    category_comparison.sort(key=lambda x: x["median_sales_thousand_krw"], reverse=True)

    # 4. 품질 안내 배지 (Quality Notices) 동적 생성
    quality_notices = []
    if region_fallback and rgn_name:
        quality_notices.append({
            "type": "REGION_FALLBACK_NOTICE",
            "badge": f"{rgn_name} 표본 부재 → 전국 대체",
            "message": f"선택하신 {rgn_name} 지역에 해당 업종 등록 가맹본부 표본이 없어 전국 통계로 대체 표시 중입니다."
        })
    if applied_year == db_latest_year:
        quality_notices.append({
            "type": "SNAPSHOT_NOTICE",
            "badge": "최신 제공 스냅샷",
            "message": "수집 시점 기준 최신 제공 스냅샷이며 향후 모수가 변동될 수 있습니다."
        })
    elif is_fallback:
        quality_notices.append({
            "type": "FALLBACK_NOTICE",
            "badge": f"{applied_year}년 대체 표시",
            "message": f"{db_latest_year}년 스냅샷 미등록으로 {applied_year}년 실적으로 일괄 전환되었습니다 (최신 완결 후보 연도이며 공식 마감 여부는 확인되지 않음)."
        })

    # 0원 매출 비율 알림
    total_brands = sum_row["total_brand_records"] or 0
    if total_brands > 0 and zero_cnt > 0:
        zero_ratio = round((zero_cnt / total_brands) * 100, 1)
        if zero_ratio >= 10.0:
            quality_notices.append({
                "type": "ZERO_SALES_NOTICE",
                "badge": f"매출 0원 공시 {zero_ratio}%",
                "message": f"전체 브랜드 중 {zero_cnt}개({zero_ratio}%)가 매출 0원으로 공시되어 있어 단순평균 대신 중앙값(Median) 지표를 확인하십시오."
            })

    financial_year = str(int(applied_year) - 1)
    med_cost_cur = startup_costs.get("tentative_derived_sum", {}).get("median_thousand_krw", 0.0)
    region_label = active_rgn_name if active_rgn_name else "전국"

    result_data = {
        "status": "SUCCESS",
        "data": {
            "benchmark_year": applied_year,
            "financial_year": financial_year,
            "display_label": f"{region_label} · {applied_year}년 공정위 등록 ({financial_year} 결산)",
            "is_fallback_applied": is_fallback,
            "fallback_reason": fallback_reason,
            "category_major_id": category_major_id,
            "category_major_name": cat_info["category_major_name"],
            "mapped_ftc_categories": target_ftc_categories,
            "mapping_type": cat_info["mapping_type"],
            "mapping_status": "PROPOSED_FOR_APPROVAL",
            "region_context": {
                "sido_code": norm_sido,
                "region_name": region_label,
                "requested_region_name": rgn_name or "전국",
                "is_regional": bool(active_rgn_name),
                "is_fallback_to_national": region_fallback,
                "national_median_sales_thousand_krw": nat_median_sls,
                "national_median_cost_thousand_krw": nat_median_cost,
                "sales_vs_national_pct": round(((median_sls - nat_median_sls) / nat_median_sls) * 100, 1) if nat_median_sls > 0 else 0.0,
                "cost_vs_national_pct": round(((med_cost_cur - nat_median_cost) / nat_median_cost) * 100, 1) if nat_median_cost > 0 else 0.0,
            },
            "category_comparison": category_comparison,
            "sample_metrics": {
                "total_brand_records": total_brands,
                "sales_positive_records": pos_cnt,
                "sales_zero_records": zero_cnt,
                "sales_null_records": sum_row["sales_null_records"] or 0,
                "total_franchise_stores": sum_row["total_franchise_stores"] or 0,
                "total_direct_stores": sum_row["total_direct_stores"] or 0
            },
            "sales_benchmarks": {
                "median_sales_thousand_krw": median_sls,
                "trimmed_mean_5pct_thousand_krw": trimmed_5pct,
                "store_weighted_avg_thousand_krw": store_weighted_avg,
                "simple_avg_positive_thousand_krw": simple_avg_pos,
                "all_records_avg_thousand_krw": all_rec_avg,
                "recommended_primary_metric": "median_sales_thousand_krw",
                "recommended_secondary_metric": "trimmed_mean_5pct_thousand_krw",
                "weighted_avg_denominator_stores": weighted_denom
            },
            "startup_cost_components": startup_costs,
            "quality_notices": quality_notices
        },
        "meta": {
            "calculation_method": "Actual DB values from ftc_industry_macro_summary and ftc_brand_macro_records",
            "timestamp": get_current_kst_iso()
        }
    }

    _CACHE_STORE[cache_key] = (now, result_data)
    response.headers["Cache-Control"] = "no-cache"
    return result_data


# ==============================================================================
# 3. GET /api/v1/ftc/trends
# ==============================================================================

@router.get(
    "/trends",
    response_model=FtcTrendsResponse,
    summary="업종별 다년도 거시 추세 조회",
    description="선택한 8대 대분류에 대응하는 DB 전체 기준연도 시계열 추세를 반환합니다."
)
def get_multi_year_trends(
    response: Response,
    category_major_id: str = Query(..., description="8대 대분류 ID (ALL 또는 CAT_MAJ_01 ~ CAT_MAJ_08)"),
    sido_code: Optional[str] = Query(None, description="시도 코드 (예: '11' 서울, '41' 경기, '00' 전국)")
):
    mapping_cfg = load_mapping_config()
    category_map = {m["category_major_id"]: m for m in mapping_cfg["mappings"]}
    all_ftc_cats: List[str] = []
    for m in mapping_cfg["mappings"]:
        for fc in m["ftc_categories"]:
            if fc not in all_ftc_cats:
                all_ftc_cats.append(fc)
    category_map["ALL"] = {
        "category_major_id": "ALL",
        "category_major_name": "전체 외식업",
        "mapping_type": "MANY_TO_ONE",
        "status": "PROPOSED_FOR_APPROVAL",
        "ftc_categories": all_ftc_cats,
    }

    if category_major_id not in category_map:
        return JSONResponse(
            status_code=400,
            content={
                "status": "UNMAPPED_CATEGORY",
                "error_code": "ERR_CATEGORY_UNMAPPED",
                "message": f"선택하신 업종({category_major_id})은 거시 시계열 분석 대상이 아닙니다."
            }
        )

    cat_info = category_map[category_major_id]
    target_ftc_categories = cat_info["ftc_categories"]

    norm_sido = (sido_code or "00").strip()[:2]
    rgn_name = SIDO_TO_FTC_REGION.get(norm_sido) if norm_sido != "00" else None

    cache_key = f"trends_{category_major_id}_{norm_sido}"
    now = datetime.now()
    if cache_key in _CACHE_STORE:
        cached_time, cached_val = _CACHE_STORE[cache_key]
        if (now - cached_time).total_seconds() < CACHE_TTL_SECONDS:
            response.headers["Cache-Control"] = "no-cache"
            return cached_val

    available_years = get_ftc_available_years()
    if not available_years:
        raise HTTPException(status_code=500, detail="이용 가능한 공정위 연도 데이터가 없습니다.")

    db_latest_year = available_years[0]
    years_ascending = sorted(available_years)  # 시계열 차트는 과거순(오름차순) 정렬

    conn = get_ftc_cached_connection()
    cur = conn.cursor()

    # 해당 시도에 최소 1개 연도라도 양수 매출 레코드가 있는지 확인
    placeholders = ",".join(["?"] * len(target_ftc_categories))
    active_rgn_name = rgn_name
    if active_rgn_name:
        cur.execute(f"""
            SELECT COUNT(*) as pos_cnt
            FROM ftc_brand_macro_records
            WHERE tpbiz_mclsf_nm IN ({placeholders}) AND jnghq_rgn_nm = ? AND avg_sls_amt > 0
        """, tuple(target_ftc_categories + [active_rgn_name]))
        rgn_chk = cur.fetchone()
        if not rgn_chk or (rgn_chk["pos_cnt"] or 0) == 0:
            active_rgn_name = None

    yearly_series = []

    for yr in years_ascending:
        if active_rgn_name:
            cur.execute(f"""
                SELECT 
                    COUNT(*) as total_brand_records,
                    SUM(CASE WHEN avg_sls_amt > 0 THEN 1 ELSE 0 END) as sales_positive_records,
                    SUM(COALESCE(frcs_cnt, 0)) as total_franchise_stores,
                    SUM(COALESCE(dms_cnt, 0)) as total_direct_stores,
                    SUM(CASE WHEN avg_sls_amt > 0 THEN avg_sls_amt ELSE 0 END) as total_sls_amount,
                    SUM(CASE WHEN avg_sls_amt > 0 AND frcs_cnt > 0 THEN avg_sls_amt * frcs_cnt ELSE 0 END) as total_weighted_sls_amount,
                    SUM(CASE WHEN avg_sls_amt > 0 AND frcs_cnt > 0 THEN frcs_cnt ELSE 0 END) as weighted_avg_denominator_stores
                FROM ftc_brand_macro_records
                WHERE jng_biz_crtr_yr = ? AND tpbiz_mclsf_nm IN ({placeholders}) AND jnghq_rgn_nm = ?
            """, tuple([yr] + target_ftc_categories + [active_rgn_name]))
            s_row = dict(cur.fetchone())
        else:
            cur.execute(f"""
                SELECT 
                    SUM(record_count) as total_brand_records,
                    SUM(sls_positive_record_count) as sales_positive_records,
                    SUM(sum_frcs_cnt) as total_franchise_stores,
                    SUM(sum_dms_cnt) as total_direct_stores,
                    SUM(sum_sls_amount) as total_sls_amount,
                    SUM(sum_weighted_sls_amount) as total_weighted_sls_amount,
                    SUM(denom_store_weighted_sls) as weighted_avg_denominator_stores
                FROM ftc_industry_macro_summary
                WHERE jng_biz_crtr_yr = ? AND tpbiz_mclsf_nm IN ({placeholders})
            """, tuple([yr] + target_ftc_categories))
            s_row = dict(cur.fetchone())

        pos_cnt = s_row["sales_positive_records"] or 0
        tot_amt = s_row["total_sls_amount"] or 0.0
        simple_avg = round(tot_amt / pos_cnt, 2) if pos_cnt > 0 else 0.0

        w_denom = s_row["weighted_avg_denominator_stores"] or 0
        w_amt = s_row["total_weighted_sls_amount"] or 0.0
        weighted_avg = round(w_amt / w_denom, 2) if w_denom > 0 else 0.0

        if active_rgn_name:
            cur.execute(f"""
                SELECT avg_sls_amt 
                FROM ftc_brand_macro_records
                WHERE jng_biz_crtr_yr = ? AND tpbiz_mclsf_nm IN ({placeholders}) AND jnghq_rgn_nm = ? AND avg_sls_amt > 0
                ORDER BY avg_sls_amt ASC
            """, tuple([yr] + target_ftc_categories + [active_rgn_name]))
        else:
            cur.execute(f"""
                SELECT avg_sls_amt 
                FROM ftc_brand_macro_records
                WHERE jng_biz_crtr_yr = ? AND tpbiz_mclsf_nm IN ({placeholders}) AND avg_sls_amt > 0
                ORDER BY avg_sls_amt ASC
            """, tuple([yr] + target_ftc_categories))
        sales_vals = [r["avg_sls_amt"] for r in cur.fetchall()]

        median_sls = round(calc_median(sales_vals), 1)
        trimmed_5pct = round(calc_trimmed_mean_5pct(sales_vals), 2)

        fin_year = str(int(yr) - 1)
        is_snap = (yr == db_latest_year)

        item = {
            "benchmark_year": yr,
            "financial_year": fin_year,
            "is_snapshot": is_snap,
            "sample_count": s_row["total_brand_records"] or 0,
            "total_franchise_stores": s_row["total_franchise_stores"] or 0,
            "total_direct_stores": s_row["total_direct_stores"] or 0,
            "median_sales_thousand_krw": median_sls,
            "trimmed_mean_5pct_thousand_krw": trimmed_5pct,
            "store_weighted_avg_thousand_krw": weighted_avg,
            "simple_avg_thousand_krw": simple_avg,
            "denom_stores": w_denom
        }
        if is_snap:
            item["snapshot_badge"] = "최신 제공 스냅샷"

        yearly_series.append(item)

    result_data = {
        "status": "SUCCESS",
        "data": {
            "category_major_id": category_major_id,
            "category_major_name": cat_info["category_major_name"],
            "trend_mode": "FULL_POPULATION_CROSS_SECTIONAL",
            "balanced_panel_active": False,
            "panel_inactive_reason": "존속 브랜드 균형 패널은 생존편향 위험으로 인해 비활성화 상태 유지",
            "yearly_series": yearly_series,
            "macro_guidance": f"금액 지표는 물가변동 미반영 명목금액이며, {db_latest_year}년은 수집 시점의 최신 제공 스냅샷으로 이전 연도와 모집단이 달라, 점포 수 차이를 산업 성장·감소로 직접 해석할 수 없습니다."
        },
        "meta": {
            "calculation_method": "Multi-year cross-sectional actual DB query from ftc_industry_macro_summary and ftc_brand_macro_records",
            "timestamp": get_current_kst_iso()
        }
    }

    _CACHE_STORE[cache_key] = (now, result_data)
    response.headers["Cache-Control"] = "no-cache"
    return result_data


# ==============================================================================
# 4. GET /api/v1/ftc/years
# ==============================================================================

@router.get(
    "/years",
    response_model=FtcYearsResponse,
    summary="수동 연도 선택용 연도 메타 목록 조회",
    description="사용자가 연도를 수동으로 변경할 때 사용할 연도 목록과 기본값 정보를 DB 기반으로 동적 제공합니다."
)
def get_available_years(response: Response):
    cache_key = "ftc_years"
    now = datetime.now()
    if cache_key in _CACHE_STORE:
        cached_time, cached_val = _CACHE_STORE[cache_key]
        if (now - cached_time).total_seconds() < 86400:
            response.headers["Cache-Control"] = "public, max-age=86400"
            return cached_val

    available_years = get_ftc_available_years()
    if not available_years:
        raise HTTPException(status_code=500, detail="이용 가능한 공정위 연도 데이터가 없습니다.")

    db_latest_year = available_years[0]
    previous_year = available_years[1] if len(available_years) > 1 else None

    data = []
    for yr in available_years:
        fin_year = str(int(yr) - 1)
        if yr == db_latest_year:
            item = {
                "benchmark_year": yr,
                "financial_year": fin_year,
                "is_default": True,
                "is_snapshot": True,
                "label": f"{yr}년 공정위 등록 (최신 스냅샷)"
            }
        elif yr == previous_year:
            item = {
                "benchmark_year": yr,
                "financial_year": fin_year,
                "is_default": False,
                "is_snapshot": False,
                "label": f"{yr}년 공정위 등록 (최신 완결 후보)"
            }
        else:
            item = {
                "benchmark_year": yr,
                "financial_year": fin_year,
                "is_default": False,
                "is_snapshot": False,
                "label": f"{yr}년 공정위 등록 ({fin_year} 실적)"
            }
        data.append(item)

    result_data = {
        "status": "SUCCESS",
        "data": data,
        "meta": {
            "timestamp": get_current_kst_iso()
        }
    }

    _CACHE_STORE[cache_key] = (now, result_data)
    response.headers["Cache-Control"] = "public, max-age=86400"
    return result_data
