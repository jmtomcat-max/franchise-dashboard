"""
Stage 4E: 시도 및 시군구 지역별 외식업 통계 엔드포인트
프로젝트: D:/Franchise_Dashboard
위치: src/stage4e/api/routers/regions.py
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Query, HTTPException, Path

from src.stage4e.api.database import query_all, query_one, validate_whitelist
from src.stage4e.api.schemas import RegionListResponse, RegionStatsItem, ResponseMeta

router = APIRouter(prefix="/api/v1/analytics/regions", tags=["Regional Analytics"])

ALLOWED_SORT_FIELDS = [
    "total_stores", "franchise_confirmed_stores", "brand_linked_stores",
    "franchise_penetration_rate", "brand_penetration_rate", "region_name"
]
ALLOWED_ORDERS = ["ASC", "DESC", "asc", "desc"]


@router.get("", response_model=RegionListResponse)
def list_regions(
    region_type: Optional[str] = Query(None, description="지역 구분 ('SIDO' 또는 'SIGUNGU')"),
    sido_code: Optional[str] = Query(None, description="상위 시도코드 (예: '11' 서울특별시 내 시군구 조회)"),
    category_major_id: Optional[str] = Query(None, description="8대 대분류 코드 ('CAT_MAJ_01'~'08')"),
    category_mid_id: Optional[str] = Query(None, description="48대 중분류 코드 ('CAT_MID_0101'~'0806')"),
    sort_by: str = Query("total_stores", description="정렬 기준 필드"),
    order: str = Query("desc", description="정렬 순서 ('asc' 또는 'desc')"),
    limit: int = Query(100, ge=1, le=300, description="조회 건수 제한"),
    offset: int = Query(0, ge=0, description="페이지 오프셋")
):
    """시도(16개) 및 시군구(256개) 단위 외식업/프랜차이즈 통계 목록을 조회합니다 (업종 대/중분류 필터 지원)."""
    sort_field = validate_whitelist(sort_by, ALLOWED_SORT_FIELDS, "sort_by")
    order_dir = validate_whitelist(order.upper(), ["ASC", "DESC"], "order")

    norm_maj = category_major_id.strip() if category_major_id and category_major_id.strip() not in ("", "ALL") else None
    norm_mid = category_mid_id.strip() if category_mid_id and category_mid_id.strip() not in ("", "ALL") else None

    where_clauses = ["r.region_code != '00'"]
    params: List[Any] = []

    if region_type:
        val_type = validate_whitelist(region_type.upper(), ["SIDO", "SIGUNGU"], "region_type")
        where_clauses.append("r.region_type = ?")
        params.append(val_type)

    if sido_code:
        where_clauses.append("m.sido_code = ?")
        params.append(sido_code)

    where_sql = " AND ".join(where_clauses)

    if norm_maj or norm_mid:
        cat_clauses = []
        cat_params: List[Any] = []
        if norm_maj:
            cat_clauses.append("c.category_major_id = ?")
            cat_params.append(norm_maj)
        if norm_mid:
            cat_clauses.append("c.category_mid_id = ?")
            cat_params.append(norm_mid)
        cat_where_sql = " AND ".join(cat_clauses)

        sql = f"""
            SELECT 
                r.region_code,
                r.region_name,
                r.region_type,
                COALESCE(SUM(c.total_stores), 0) AS total_stores,
                COALESCE(SUM(c.brand_linked_stores), 0) AS brand_linked_stores,
                COALESCE(SUM(c.independent_stores), 0) AS independent_stores,
                COALESCE(SUM(c.franchise_confirmed_stores), 0) AS franchise_confirmed_stores,
                COALESCE(SUM(c.franchise_confirmed_stores), 0) AS confirmed_franchisees,
                COALESCE(SUM(c.ambiguous_stores), 0) AS ambiguous_category_stores,
                ROUND(COALESCE(SUM(c.franchise_confirmed_stores), 0) * 100.0 / NULLIF(SUM(c.total_stores), 0), 2) AS franchise_penetration_rate,
                ROUND(COALESCE(SUM(c.brand_linked_stores), 0) * 100.0 / NULLIF(SUM(c.total_stores), 0), 2) AS brand_penetration_rate,
                m.center_lon,
                m.center_lat,
                r.density_status
            FROM regional_overall_stats r
            JOIN regions_master m ON r.region_code = m.region_code
            LEFT JOIN regional_category_stats c
                ON c.region_code = r.region_code AND {cat_where_sql}
            WHERE {where_sql}
            GROUP BY r.region_code, r.region_name, r.region_type, m.center_lon, m.center_lat, r.density_status
            ORDER BY {sort_field} {order_dir}
            LIMIT ? OFFSET ?;
        """
        query_params = tuple(cat_params + params + [limit, offset])
    else:
        sql = f"""
            SELECT 
                r.region_code,
                r.region_name,
                r.region_type,
                r.total_stores,
                r.brand_linked_stores,
                r.independent_stores,
                r.franchise_confirmed_stores,
                r.confirmed_franchisees,
                r.ambiguous_category_stores,
                r.franchise_penetration_rate,
                r.brand_penetration_rate,
                m.center_lon,
                m.center_lat,
                r.density_status
            FROM regional_overall_stats r
            JOIN regions_master m ON r.region_code = m.region_code
            WHERE {where_sql}
            ORDER BY r.{sort_field} {order_dir}
            LIMIT ? OFFSET ?;
        """
        query_params = tuple(params + [limit, offset])

    rows = query_all(sql, query_params)

    # 전체 건수 카운트
    cnt_sql = f"""
        SELECT COUNT(*) AS cnt
        FROM regional_overall_stats r
        JOIN regions_master m ON r.region_code = m.region_code
        WHERE {where_sql};
    """
    tot_row = query_one(cnt_sql, tuple(params))
    total_cnt = tot_row["cnt"] if tot_row else len(rows)

    items = [
        RegionStatsItem(
            region_code=r["region_code"],
            region_name=r["region_name"],
            region_type=r["region_type"],
            total_stores=r["total_stores"] or 0,
            brand_linked_stores=r["brand_linked_stores"] or 0,
            independent_stores=r["independent_stores"] or 0,
            franchise_confirmed_stores=r["franchise_confirmed_stores"] or 0,
            confirmed_franchisees=r["confirmed_franchisees"] or 0,
            ambiguous_category_stores=r["ambiguous_category_stores"] or 0,
            franchise_penetration_rate=r["franchise_penetration_rate"] or 0.0,
            brand_penetration_rate=r["brand_penetration_rate"] or 0.0,
            center_lon=r["center_lon"],
            center_lat=r["center_lat"],
            density_status=r["density_status"]
        ) for r in rows
    ]

    meta = ResponseMeta(
        timestamp=datetime.now().isoformat(),
        applied_filters={
            "region_type": region_type,
            "sido_code": sido_code,
            "category_major_id": norm_maj,
            "category_mid_id": norm_mid,
            "sort_by": sort_by,
            "order": order
        },
        page=(offset // limit) + 1,
        page_size=limit,
        total_count=total_cnt
    )

    return RegionListResponse(data=items, meta=meta)


@router.get("/{region_code}")
def get_region_detail(
    region_code: str = Path(..., description="조회할 지역코드 (예: '11680' 강남구, '11' 서울, '00' 전국)"),
    category_major_id: Optional[str] = Query(
        None,
        description="8대 대분류 코드 ('CAT_MAJ_01'~'08'). 지정하면 상위 브랜드를 해당 업종 내 순위(CATEGORY_TOP10)로 반환하고, 미지정 시 전 업종 순위(OVERALL_TOP20)를 반환합니다."
    ),
    category_mid_id: Optional[str] = Query(
        None,
        description="48대 중분류 코드 ('CAT_MID_0101'~'0806'). 지정하면 해당 중분류 소속 상위 브랜드 및 중분류 통계를 반환합니다."
    )
):
    """특정 지역의 종합 통계, 상위 브랜드 10개, 8대 대분류 업종 구성을 조회합니다."""
    # 1. 종합 통계 (전국 '00' 조회 시에도 동작하도록 LEFT JOIN 적용)
    overall_sql = """
        SELECT 
            r.region_code, r.region_name, r.region_type,
            r.total_stores, r.brand_linked_stores, r.independent_stores,
            r.franchise_confirmed_stores, r.confirmed_franchisees,
            r.ambiguous_category_stores,
            r.franchise_penetration_rate, r.brand_penetration_rate,
            COALESCE(m.center_lon, 127.7669) AS center_lon,
            COALESCE(m.center_lat, 35.9078) AS center_lat,
            r.density_status
        FROM regional_overall_stats r
        LEFT JOIN regions_master m ON r.region_code = m.region_code
        WHERE r.region_code = ?;
    """
    overall_row = query_one(overall_sql, (region_code,))
    if not overall_row:
        raise HTTPException(status_code=404, detail=f"지역코드 '{region_code}'를 찾을 수 없습니다.")

    # 2. 8대 대분류 구성 (업종별 점포 총수·가맹/브랜드/독립 분해 포함)
    maj_cat_sql = """
        SELECT 
            category_major_id,
            category_major_name,
            SUM(total_stores) AS stores,
            SUM(total_stores) AS total_stores,
            SUM(brand_linked_stores) AS brand_linked_stores,
            SUM(independent_stores) AS independent_stores,
            SUM(franchise_confirmed_stores) AS franchise_confirmed_stores,
            ROUND(SUM(franchise_confirmed_stores) * 100.0 / NULLIF(SUM(total_stores), 0), 2) AS franchise_penetration_rate,
            ROUND(SUM(brand_linked_stores) * 100.0 / NULLIF(SUM(total_stores), 0), 2) AS brand_penetration_rate,
            ROUND(SUM(total_stores) * 100.0 / ?, 2) AS share_pct
        FROM regional_category_stats
        WHERE region_code = ?
        GROUP BY category_major_id, category_major_name
        ORDER BY stores DESC;
    """
    maj_cats = query_all(maj_cat_sql, (overall_row["total_stores"], region_code))

    # 3. 상위 10개 브랜드 (중분류 지정 -> 대분류 지정 -> 전 업종 순위 순으로 정밀 조회)
    norm_mid = category_mid_id.strip() if category_mid_id and category_mid_id.strip() not in ("", "ALL") else None
    norm_maj = category_major_id.strip() if category_major_id and category_major_id.strip() not in ("", "ALL") else None

    if norm_mid:
        mid_tot_row = query_one(
            "SELECT SUM(total_stores) AS cnt FROM regional_category_stats WHERE region_code = ? AND category_mid_id = ?;",
            (region_code, norm_mid)
        )
        mid_total = (mid_tot_row["cnt"] if mid_tot_row and mid_tot_row["cnt"] else overall_row["total_stores"]) or 1
        top_brands_sql = """
            SELECT
                ROW_NUMBER() OVER (ORDER BY discovered_store_count DESC) AS rank_num,
                internal_brand_id,
                brand_name_std,
                brand_officiality,
                discovered_store_count AS store_count,
                ROUND(discovered_store_count * 100.0 / ?, 2) AS share_pct
            FROM regional_brand_stats
            WHERE region_code = ? AND category_mid_id = ? AND discovered_store_count > 0
            ORDER BY discovered_store_count DESC
            LIMIT 10;
        """
        top_brands = query_all(top_brands_sql, (mid_total, region_code, norm_mid))
    elif norm_maj:
        cat_total = next((c["stores"] for c in maj_cats if c["category_major_id"] == norm_maj), 0) or overall_row["total_stores"] or 1
        top_brands_sql = """
            SELECT 
                ROW_NUMBER() OVER (ORDER BY SUM(store_count) DESC, MIN(rank_num) ASC) AS rank_num,
                internal_brand_id,
                brand_name_std,
                brand_officiality,
                SUM(store_count) AS store_count,
                ROUND(SUM(store_count) * 100.0 / ?, 2) AS share_pct
            FROM regional_brand_rankings
            WHERE region_code = ? AND ranking_type = 'CATEGORY_TOP10' AND category_major_id = ?
            GROUP BY internal_brand_id, brand_name_std, brand_officiality
            ORDER BY store_count DESC, MIN(rank_num) ASC
            LIMIT 10;
        """
        top_brands = query_all(top_brands_sql, (cat_total, region_code, norm_maj))
    else:
        top_brands_sql = """
            SELECT 
                rank_num, internal_brand_id, brand_name_std, brand_officiality, store_count, share_pct
            FROM regional_brand_rankings
            WHERE region_code = ? AND ranking_type = 'OVERALL_TOP20'
            ORDER BY rank_num ASC
            LIMIT 10;
        """
        top_brands = query_all(top_brands_sql, (region_code,))

    meta = ResponseMeta(
        timestamp=datetime.now().isoformat(),
        applied_filters={
            "region_code": region_code,
            "category_major_id": norm_maj,
            "category_mid_id": norm_mid
        }
    )

    return {
        "region_stats": dict(overall_row),
        "top_brands": top_brands,
        "category_composition": maj_cats,
        "meta": meta.model_dump()
    }
