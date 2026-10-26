"""
Stage 4E: 브랜드 검색, 자동완성 및 지역별 분포 통계 엔드포인트
프로젝트: D:/Franchise_Dashboard
위치: src/stage4e/api/routers/brands.py
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Query, HTTPException, Path

from src.stage4e.api.database import query_all, query_one, validate_whitelist
from src.stage4e.api.schemas import (
    BrandSearchItem, BrandDistributionResponse, BrandDistributionItem,
    StoreDetailItem, ResponseMeta
)

router = APIRouter(prefix="/api/v1/analytics/brands", tags=["Brand Analytics"])

ALLOWED_OFFICIALITIES = ["FRANCHISE_CONFIRMED", "BRAND_CONFIRMED", "UNVERIFIED"]


@router.get("/search")
def search_brands(
    q: Optional[str] = Query(None, description="브랜드 검색어 (초성/완성형 자동완성 지원)"),
    region_code: str = Query("00", description="현재 선택된 지역코드 ('00' 전국, '11' 시도, '11680' 시군구)"),
    officiality: Optional[str] = Query(None, description="공식성 상태 필터 ('FRANCHISE_CONFIRMED' 등)"),
    category_major_id: Optional[str] = Query(None, description="8대 대분류 필터 ('CAT_MAJ_01'~'08')"),
    category_mid_id: Optional[str] = Query(None, description="48대 중분류 필터 ('CAT_MID_0101'~'0806')"),
    min_stores: int = Query(1, ge=1, description="최소 점포 수 필터"),
    limit: int = Query(20, ge=1, le=100, description="반환 결과 수 제한"),
    offset: int = Query(0, ge=0, description="페이지 오프셋")
):
    """5,062개 브랜드 후보를 이름, 공식성, 업종별로 고속 검색 및 자동완성합니다 (선택 지역 점포 수 동시 반환)."""
    norm_region = (region_code or "00").strip() or "00"
    where_clauses = ["n.region_code = '00' AND n.discovered_store_count >= ?"]
    params: List[Any] = [min_stores]

    if q and q.strip():
        where_clauses.append("n.brand_name_std LIKE ?")
        params.append(f"%{q.strip()}%")

    if officiality:
        val_off = validate_whitelist(officiality, ALLOWED_OFFICIALITIES, "officiality")
        where_clauses.append("n.brand_officiality = ?")
        params.append(val_off)

    if category_major_id and category_major_id not in ("", "ALL"):
        where_clauses.append("n.category_major_id = ?")
        params.append(category_major_id)

    if category_mid_id and category_mid_id not in ("", "ALL"):
        where_clauses.append("n.category_mid_id = ?")
        params.append(category_mid_id)

    where_sql = " AND ".join(where_clauses)

    if norm_region != "00":
        sql = f"""
            SELECT 
                n.internal_brand_id,
                n.brand_name_std,
                n.brand_officiality,
                n.category_major_id,
                n.category_mid_id,
                n.discovered_store_count AS nationwide_store_count,
                n.confirmed_franchisee_count,
                n.market_share_in_region AS market_share_in_nation,
                COALESCE(r.discovered_store_count, 0) AS region_store_count,
                COALESCE(r.category_share_in_region, 0.0) AS region_category_share_pct,
                r.rank_in_region AS region_rank
            FROM regional_brand_stats n
            LEFT JOIN regional_brand_stats r
                ON r.internal_brand_id = n.internal_brand_id
               AND r.region_code = ?
            WHERE {where_sql}
            ORDER BY COALESCE(r.discovered_store_count, 0) DESC, n.discovered_store_count DESC
            LIMIT ? OFFSET ?;
        """
        rows = query_all(sql, tuple([norm_region] + params + [limit, offset]))
    else:
        sql = f"""
            SELECT 
                n.internal_brand_id,
                n.brand_name_std,
                n.brand_officiality,
                n.category_major_id,
                n.category_mid_id,
                n.discovered_store_count AS nationwide_store_count,
                n.confirmed_franchisee_count,
                n.market_share_in_region AS market_share_in_nation,
                n.discovered_store_count AS region_store_count,
                n.category_share_in_region AS region_category_share_pct,
                n.rank_in_region AS region_rank
            FROM regional_brand_stats n
            WHERE {where_sql}
            ORDER BY n.discovered_store_count DESC
            LIMIT ? OFFSET ?;
        """
        rows = query_all(sql, tuple(params + [limit, offset]))

    # 총 건수
    cnt_sql = f"""
        SELECT COUNT(*) AS cnt
        FROM regional_brand_stats n
        WHERE {where_sql};
    """
    cnt_row = query_one(cnt_sql, tuple(params))
    total_cnt = cnt_row["cnt"] if cnt_row else len(rows)

    data_items = []
    for r in rows:
        item_dict = BrandSearchItem(
            internal_brand_id=r["internal_brand_id"],
            brand_name_std=r["brand_name_std"],
            brand_officiality=r["brand_officiality"],
            category_major_id=r["category_major_id"],
            category_mid_id=r["category_mid_id"],
            nationwide_store_count=r["nationwide_store_count"],
            confirmed_franchisee_count=r["confirmed_franchisee_count"],
            market_share_in_nation=r["market_share_in_nation"]
        ).model_dump()
        item_dict["region_store_count"] = r["region_store_count"]
        item_dict["region_category_share_pct"] = r["region_category_share_pct"]
        item_dict["region_rank"] = r["region_rank"]
        data_items.append(item_dict)

    meta = ResponseMeta(
        timestamp=datetime.now().isoformat(),
        applied_filters={
            "q": q,
            "region_code": norm_region,
            "officiality": officiality,
            "category_major_id": category_major_id,
            "category_mid_id": category_mid_id,
            "min_stores": min_stores
        },
        page=(offset // limit) + 1,
        page_size=limit,
        total_count=total_cnt
    )

    return {
        "data": data_items,
        "meta": meta.model_dump()
    }


@router.get("/{brand_id}/distribution", response_model=BrandDistributionResponse)
def get_brand_regional_distribution(
    brand_id: str = Path(..., description="조회할 내부 브랜드 ID (예: 'BRD_CHK_0001')"),
    region_type: str = Query("SIDO", description="분포 단위 ('SIDO' 16개 시도 또는 'SIGUNGU' 256개 시군구)")
):
    """특정 브랜드의 전국 16개 시도 또는 256개 시군구별 점포 수, 비중, 순위를 조회합니다."""
    val_rtype = validate_whitelist(region_type.upper(), ["SIDO", "SIGUNGU"], "region_type")

    # 1. 브랜드 기본 정보 (전국 기준)
    info_sql = """
        SELECT 
            internal_brand_id,
            brand_name_std,
            brand_officiality,
            category_major_id,
            category_mid_id,
            discovered_store_count AS nationwide_store_count,
            confirmed_franchisee_count,
            market_share_in_region AS market_share_in_nation
        FROM regional_brand_stats
        WHERE region_code = '00' AND internal_brand_id = ?;
    """
    info_row = query_one(info_sql, (brand_id,))
    if not info_row:
        raise HTTPException(status_code=404, detail=f"브랜드 ID '{brand_id}'를 찾을 수 없습니다.")

    brand_info = BrandSearchItem(
        internal_brand_id=info_row["internal_brand_id"],
        brand_name_std=info_row["brand_name_std"],
        brand_officiality=info_row["brand_officiality"],
        category_major_id=info_row["category_major_id"],
        category_mid_id=info_row["category_mid_id"],
        nationwide_store_count=info_row["nationwide_store_count"],
        confirmed_franchisee_count=info_row["confirmed_franchisee_count"],
        market_share_in_nation=info_row["market_share_in_nation"]
    )

    # 2. 지역별 분포 데이터
    dist_sql = f"""
        SELECT 
            b.region_code,
            r.region_name,
            b.discovered_store_count,
            b.confirmed_franchisee_count,
            b.market_share_in_region,
            b.category_share_in_region,
            b.rank_in_region
        FROM regional_brand_stats b
        JOIN regional_overall_stats r ON b.region_code = r.region_code
        WHERE b.internal_brand_id = ? AND r.region_type = ?
        ORDER BY b.discovered_store_count DESC;
    """
    dist_rows = query_all(dist_sql, (brand_id, val_rtype))

    distribution = [
        BrandDistributionItem(
            region_code=r["region_code"],
            region_name=r["region_name"],
            discovered_store_count=r["discovered_store_count"],
            confirmed_franchisee_count=r["confirmed_franchisee_count"],
            market_share_in_region=r["market_share_in_region"],
            category_share_in_region=r["category_share_in_region"],
            rank_in_region=r["rank_in_region"]
        ) for r in dist_rows
    ]

    meta = ResponseMeta(
        timestamp=datetime.now().isoformat(),
        applied_filters={
            "brand_id": brand_id,
            "region_type": val_rtype
        },
        total_count=len(distribution)
    )

    return BrandDistributionResponse(
        brand_info=brand_info,
        distribution=distribution,
        meta=meta
    )


@router.get("/{brand_id}/stores")
def get_brand_stores(
    brand_id: str = Path(..., description="내부 브랜드 ID"),
    sido_code: Optional[str] = Query(None, description="특정 시도 필터 (예: '11')"),
    sigungu_code: Optional[str] = Query(None, description="특정 시군구 필터 (예: '11680')"),
    limit: int = Query(50, ge=1, le=200, description="조회 건수 제한"),
    offset: int = Query(0, ge=0, description="페이지 오프셋")
):
    """특정 브랜드 소속 개별 점포 목록을 페이지네이션하여 조회합니다."""
    where_clauses = ["primary_brand_id = ?"]
    params: List[Any] = [brand_id]

    if sido_code:
        where_clauses.append("std_sido_code = ?")
        params.append(sido_code)

    if sigungu_code:
        where_clauses.append("std_signgu_code = ?")
        params.append(sigungu_code)

    where_sql = " AND ".join(where_clauses)

    sql = f"""
        SELECT 
            bizes_id, bizes_nm, brch_nm,
            std_sido_name, std_signgu_name, rdnm_adr, lno_adr,
            lon, lat,
            category_major_id, category_major_name,
            category_mid_id, category_mid_name,
            primary_brand_id, brand_name_std, brand_officiality,
            match_status, operation_type, classification_status,
            is_brand_linked, is_category_divergent, is_multi_brand_store, auxiliary_brand_names
        FROM store_analytics_lookup
        WHERE {where_sql}
        ORDER BY bizes_nm ASC
        LIMIT ? OFFSET ?;
    """
    rows = query_all(sql, tuple(params + [limit, offset]))

    cnt_sql = f"SELECT COUNT(*) AS cnt FROM store_analytics_lookup WHERE {where_sql};"
    tot_row = query_one(cnt_sql, tuple(params))
    total_cnt = tot_row["cnt"] if tot_row else len(rows)

    items = [StoreDetailItem(**r) for r in rows]

    meta = ResponseMeta(
        timestamp=datetime.now().isoformat(),
        applied_filters={
            "brand_id": brand_id,
            "sido_code": sido_code,
            "sigungu_code": sigungu_code
        },
        page=(offset // limit) + 1,
        page_size=limit,
        total_count=total_cnt
    )

    return {
        "data": [item.model_dump() for item in items],
        "meta": meta.model_dump()
    }
