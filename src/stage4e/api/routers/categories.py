"""
Stage 4E: 8대 대분류 및 48대 중분류 통계 엔드포인트
프로젝트: D:/Franchise_Dashboard
위치: src/stage4e/api/routers/categories.py
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Query, HTTPException, Path

from src.stage4e.api.database import query_all, query_one, validate_whitelist
from src.stage4e.api.schemas import CategoryListResponse, CategoryStatsItem, ResponseMeta

router = APIRouter(prefix="/api/v1/analytics/categories", tags=["Category Analytics"])

ALLOWED_CAT_SORTS = ["total_stores", "stores_excluding_ambiguous", "category_share_pct", "category_rank"]


@router.get("", response_model=CategoryListResponse)
def list_category_stats(
    region_code: str = Query("00", description="지역코드 ('00' 전국, '11' 시도, '11680' 시군구 등)"),
    category_major_id: Optional[str] = Query(None, description="특정 8대 대분류 필터 ('CAT_MAJ_01' ~ '08')"),
    include_ambiguous: bool = Query(True, description="모호 분류(AMBIGUOUS_REVIEW, 104,060건) 포함 여부"),
    sort_by: str = Query("total_stores", description="정렬 필드"),
    order: str = Query("desc", description="정렬 순서 ('asc' 또는 'desc')")
):
    """
    8대 대분류 및 48대 중분류별 점포 수, 비중, 프랜차이즈 점포 수를 조회합니다.
    (모호 분류 포함/제외 필터 완비)
    """
    sort_field = validate_whitelist(sort_by, ALLOWED_CAT_SORTS, "sort_by")
    order_dir = validate_whitelist(order.upper(), ["ASC", "DESC"], "order")

    where_clauses = ["region_code = ?"]
    params: List[Any] = [region_code]

    if category_major_id:
        where_clauses.append("category_major_id = ?")
        params.append(category_major_id)

    where_sql = " AND ".join(where_clauses)

    # 모호 분류 포함 여부에 따른 정렬/조회 선택
    chosen_store_field = "total_stores" if include_ambiguous else "stores_excluding_ambiguous"
    if sort_field == "total_stores" and not include_ambiguous:
        sort_field = "stores_excluding_ambiguous"

    sql = f"""
        SELECT 
            category_major_id,
            category_major_name,
            category_mid_id,
            category_mid_name,
            total_stores,
            stores_excluding_ambiguous,
            brand_linked_stores,
            independent_stores,
            franchise_confirmed_stores,
            ambiguous_stores,
            category_share_pct,
            category_rank_in_region AS category_rank
        FROM regional_category_stats
        WHERE {where_sql}
        ORDER BY {sort_field} {order_dir};
    """
    rows = query_all(sql, tuple(params))

    items = [
        CategoryStatsItem(
            category_major_id=r["category_major_id"],
            category_major_name=r["category_major_name"],
            category_mid_id=r["category_mid_id"],
            category_mid_name=r["category_mid_name"],
            total_stores=r["total_stores"],
            stores_excluding_ambiguous=r["stores_excluding_ambiguous"],
            brand_linked_stores=r["brand_linked_stores"],
            independent_stores=r["independent_stores"],
            franchise_confirmed_stores=r["franchise_confirmed_stores"],
            ambiguous_stores=r["ambiguous_stores"],
            category_share_pct=r["category_share_pct"],
            category_rank=r["category_rank"]
        ) for r in rows
    ]

    meta = ResponseMeta(
        timestamp=datetime.now().isoformat(),
        applied_filters={
            "region_code": region_code,
            "category_major_id": category_major_id,
            "include_ambiguous": include_ambiguous,
            "sort_by": sort_by,
            "order": order
        },
        total_count=len(items)
    )

    return CategoryListResponse(data=items, meta=meta)


@router.get("/{category_major_id}")
def get_major_category_detail(
    category_major_id: str = Path(..., description="조회할 8대 대분류 ID ('CAT_MAJ_01'~'08')"),
    region_code: str = Query("00", description="지역코드 ('00' 전국 등)")
):
    """특정 8대 대분류의 하위 중분류 목록과 대분류 요약 통계를 반환합니다."""
    # 대분류 총괄 통계
    summary_sql = """
        SELECT 
            category_major_id,
            category_major_name,
            SUM(total_stores) AS total_stores,
            SUM(stores_excluding_ambiguous) AS stores_excluding_ambiguous,
            SUM(brand_linked_stores) AS brand_linked_stores,
            SUM(independent_stores) AS independent_stores,
            SUM(franchise_confirmed_stores) AS franchise_confirmed_stores,
            SUM(ambiguous_stores) AS ambiguous_stores,
            ROUND(SUM(category_share_pct), 2) AS category_share_pct
        FROM regional_category_stats
        WHERE region_code = ? AND category_major_id = ?
        GROUP BY category_major_id, category_major_name;
    """
    summary_row = query_one(summary_sql, (region_code, category_major_id))
    if not summary_row:
        raise HTTPException(status_code=404, detail=f"대분류코드 '{category_major_id}'를 찾을 수 없습니다.")

    # 하위 중분류 목록
    mid_sql = """
        SELECT 
            category_mid_id,
            category_mid_name,
            total_stores,
            stores_excluding_ambiguous,
            brand_linked_stores,
            independent_stores,
            franchise_confirmed_stores,
            ambiguous_stores,
            category_share_pct,
            category_rank_in_region AS rank_num
        FROM regional_category_stats
        WHERE region_code = ? AND category_major_id = ?
        ORDER BY total_stores DESC;
    """
    mid_rows = query_all(mid_sql, (region_code, category_major_id))

    meta = ResponseMeta(
        timestamp=datetime.now().isoformat(),
        applied_filters={
            "region_code": region_code,
            "category_major_id": category_major_id
        }
    )

    return {
        "major_category": summary_row,
        "mid_categories": mid_rows,
        "meta": meta.model_dump()
    }
