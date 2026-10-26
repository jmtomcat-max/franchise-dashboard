"""
Stage 4E: 전국 외식업 요약 통계 엔드포인트
프로젝트: D:/Franchise_Dashboard
위치: src/stage4e/api/routers/summary.py
"""

from datetime import datetime
from fastapi import APIRouter, HTTPException
from src.stage4e.api.database import query_one
from src.stage4e.api.schemas import SummaryResponse, SummaryStats, ResponseMeta

router = APIRouter(prefix="/api/v1/analytics", tags=["Analytics Summary"])


@router.get("/summary", response_model=SummaryResponse)
def get_nationwide_summary():
    """전국 외식업 총괄 통계 요약을 반환합니다 (735,185건 전수 대사)."""
    sql = """
        SELECT 
            total_stores, brand_linked_stores, independent_stores,
            franchise_confirmed_stores, brand_confirmed_stores, unverified_brand_stores,
            confirmed_franchisees, ambiguous_category_stores,
            confirmed_category_stores, provisional_category_stores,
            franchise_penetration_rate, brand_penetration_rate,
            density_status
        FROM regional_overall_stats
        WHERE region_code = '00';
    """
    row = query_one(sql)
    if not row:
        raise HTTPException(status_code=500, detail="전국 요약 통계 데이터를 찾을 수 없습니다.")

    stats = SummaryStats(
        total_stores=row["total_stores"],
        brand_linked_stores=row["brand_linked_stores"],
        independent_stores=row["independent_stores"],
        franchise_confirmed_stores=row["franchise_confirmed_stores"],
        brand_confirmed_stores=row["brand_confirmed_stores"],
        unverified_brand_stores=row["unverified_brand_stores"],
        confirmed_franchisees=row["confirmed_franchisees"],
        ambiguous_category_stores=row["ambiguous_category_stores"],
        confirmed_category_stores=row["confirmed_category_stores"],
        provisional_category_stores=row["provisional_category_stores"],
        franchise_penetration_rate=row["franchise_penetration_rate"],
        brand_penetration_rate=row["brand_penetration_rate"],
        total_provinces=16,
        total_districts=256,
        total_candidate_brands=5062,
        density_status=row["density_status"]
    )

    meta = ResponseMeta(
        timestamp=datetime.now().isoformat(),
        applied_filters={"region_code": "00"}
    )

    return SummaryResponse(data=stats, meta=meta)
