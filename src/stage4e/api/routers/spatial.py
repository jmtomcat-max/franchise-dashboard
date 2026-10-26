"""
Stage 4E: 3D GIS 지도 공간 검색 및 렌더링 전용 엔드포인트
프로젝트: D:/Franchise_Dashboard
위치: src/stage4e/api/routers/spatial.py

기능:
1. MapLibre / deck.gl 뷰포트 바운딩 박스(BBOX) 초고속 점포 검색 (GeoJSON 지원)
2. 개별 점포 3D 팝업 상세 정보 및 4축 배지 제공
3. 3D 밀집도 100m 격자 기둥 (deck.gl ColumnLayer 연동, 사용자 reference UI 완전 대응)
4. 상권 핫스팟 및 드론 비행 카메라 투어 경로 제공
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Query, HTTPException, Path
from fastapi.responses import JSONResponse

from src.stage4e.api.database import query_all, query_one, validate_whitelist
from src.stage4e.api.schemas import (
    StoreDetailItem, GeoJSONFeature, GeoJSONGeometry, GeoJSONFeatureCollection,
    CommercialHotspotItem, HotspotsResponse, SpatialGridItem, GridResponse, ResponseMeta
)

router = APIRouter(prefix="/api/v1/spatial", tags=["Spatial & 3D Map"])

ALLOWED_OFFICIALITIES = ["FRANCHISE_CONFIRMED", "BRAND_CONFIRMED", "UNVERIFIED", "UNMATCHED"]
ALLOWED_STATUSES = ["CATEGORY_CONFIRMED", "CATEGORY_PROVISIONAL", "AMBIGUOUS_REVIEW"]


@router.get("/stores/bbox")
def search_stores_by_bbox(
    min_lon: float = Query(..., ge=124.0, le=132.0, description="서쪽 경도"),
    min_lat: float = Query(..., ge=33.0, le=39.0, description="남쪽 위도"),
    max_lon: float = Query(..., ge=124.0, le=132.0, description="동쪽 경도"),
    max_lat: float = Query(..., ge=33.0, le=39.0, description="북쪽 위도"),
    zoom: Optional[float] = Query(None, description="현재 지도 줌레벨 (deck.gl / MapLibre)"),
    category_major_id: Optional[str] = Query(None, description="8대 대분류 필터 ('CAT_MAJ_01'~'08')"),
    category_mid_id: Optional[str] = Query(None, description="48대 중분류 필터 ('CAT_MID_0101'~'0806')"),
    brand_id: Optional[str] = Query(None, description="특정 브랜드 필터"),
    officiality: Optional[str] = Query(None, description="브랜드 공식성 필터"),
    classification_status: Optional[str] = Query(None, description="업종분류 상태 필터"),
    format: str = Query("geojson", description="응답 포맷 ('geojson' 또는 'json')"),
    exact_count: bool = Query(False, description="정확한 전체 일치 건수 카운트 실행 여부 (기본 false: 뷰포트 초고속 렌더링)"),
    limit: int = Query(500, ge=1, le=2000, description="최대 반환 점포 수 제한 (과부하 방지)"),
    offset: int = Query(0, ge=0, description="페이지 오프셋")
):
    """
    지도 화면(Bounding Box) 내 점포를 고속 공간 인덱스(lon, lat)로 검색합니다.
    (MapLibre GL JS 및 deck.gl ScatterplotLayer/IconLayer 표준 GeoJSON 반환)
    """
    if min_lon > max_lon or min_lat > max_lat:
        raise HTTPException(status_code=400, detail="유효하지 않은 좌표 범위: min 값이 max 값보다 클 수 없습니다.")

    # 줌레벨이 너무 낮은 경우(광역 뷰) 점포 전수 노출 차단 안내
    if zoom is not None and zoom < 12.0 and limit > 500:
        limit = 500  # 브라우저 GPU 메모리 보호를 위한 상한 강제

    where_clauses = [
        "lon BETWEEN ? AND ?",
        "lat BETWEEN ? AND ?",
        "lon IS NOT NULL AND lat IS NOT NULL"
    ]
    params: List[Any] = [min_lon, max_lon, min_lat, max_lat]

    if category_major_id:
        where_clauses.append("category_major_id = ?")
        params.append(category_major_id)

    if category_mid_id:
        where_clauses.append("category_mid_id = ?")
        params.append(category_mid_id)

    if brand_id:
        where_clauses.append("primary_brand_id = ?")
        params.append(brand_id)

    if officiality:
        val_off = validate_whitelist(officiality, ALLOWED_OFFICIALITIES, "officiality")
        where_clauses.append("brand_officiality = ?")
        params.append(val_off)

    if classification_status:
        val_stat = validate_whitelist(classification_status, ALLOWED_STATUSES, "classification_status")
        where_clauses.append("classification_status = ?")
        params.append(val_stat)

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
        ORDER BY is_brand_linked DESC,
                 CASE brand_officiality
                     WHEN 'FRANCHISE_CONFIRMED' THEN 0
                     WHEN 'BRAND_CONFIRMED' THEN 1
                     WHEN 'UNVERIFIED' THEN 2
                     ELSE 3
                 END ASC
        LIMIT ? OFFSET ?;
    """
    query_params = tuple(params + [limit, offset])
    rows = query_all(sql, query_params)

    # 전체 건수 최적화 (exact_count가 False이면 빠른 추정 반환)
    if exact_count:
        cnt_sql = f"SELECT COUNT(*) AS cnt FROM store_analytics_lookup WHERE {where_sql};"
        tot_row = query_one(cnt_sql, tuple(params))
        total_cnt = tot_row["cnt"] if tot_row else len(rows)
    else:
        total_cnt = len(rows)

    meta = ResponseMeta(
        timestamp=datetime.now().isoformat(),
        applied_filters={
            "bbox": [min_lon, min_lat, max_lon, max_lat],
            "zoom": zoom,
            "category_major_id": category_major_id,
            "category_mid_id": category_mid_id,
            "brand_id": brand_id,
            "officiality": officiality,
            "classification_status": classification_status
        },
        page=(offset // limit) + 1,
        page_size=limit,
        total_count=total_cnt
    )

    if format.lower() == "json":
        return JSONResponse(content={
            "data": [dict(r) for r in rows],
            "meta": meta.model_dump()
        })

    # 고속 GeoJSON FeatureCollection 조립 (메모리 및 직렬화 최적화)
    features = [
        {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [r["lon"], r["lat"]]
            },
            "properties": dict(r)
        }
        for r in rows
    ]

    return JSONResponse(content={
        "type": "FeatureCollection",
        "features": features,
        "meta": meta.model_dump()
    })


@router.get("/stores/{bizes_id}")
def get_store_detail(
    bizes_id: str = Path(..., description="조회할 소진공 고유 점포 ID")
):
    """개별 점포의 3D 지도 팝업용 상세 정보 및 4차원 독립 배지 데이터를 조회합니다."""
    sql = """
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
        WHERE bizes_id = ?;
    """
    row = query_one(sql, (bizes_id,))
    if not row:
        raise HTTPException(status_code=404, detail=f"점포 ID '{bizes_id}'를 찾을 수 없습니다.")

    store_item = StoreDetailItem(**row)

    # 3D 팝업 UI용 배지 및 알림 텍스트 보강
    ui_badges = {
        "officiality_badge": {
            "label": "공인 가맹 브랜드" if row["brand_officiality"] == "FRANCHISE_CONFIRMED" else (
                "공인 직영 브랜드" if row["brand_officiality"] == "BRAND_CONFIRMED" else (
                    "미검증 브랜드 후보" if row["brand_officiality"] == "UNVERIFIED" else "독립 점포"
                )
            ),
            "color": "#D4AF37" if row["brand_officiality"] == "FRANCHISE_CONFIRMED" else (
                "#9B59B6" if row["brand_officiality"] == "BRAND_CONFIRMED" else "#7F8C8D"
            )
        },
        "operation_badge": {
            "label": "가맹점" if row["operation_type"] == "FRANCHISED" else (
                "직영점" if row["operation_type"] == "COMPANY_OPERATED" else "운영형태 미확인"
            )
        },
        "classification_badge": {
            "label": "확정 분류" if row["classification_status"] == "CATEGORY_CONFIRMED" else (
                "잠정 분류" if row["classification_status"] == "CATEGORY_PROVISIONAL" else "모호 분류 검토군"
            ),
            "is_ambiguous": row["classification_status"] == "AMBIGUOUS_REVIEW"
        },
        "divergent_alert": (
            "복합 메뉴 운영 매장 (브랜드 대표업종과 점포 개별업종 상이)"
            if row["is_category_divergent"] == 1 else None
        ),
        "multi_brand_alert": (
            f"복수 브랜드(숍인숍) 매장 [보조 브랜드: {row['auxiliary_brand_names']}]"
            if row["is_multi_brand_store"] == 1 else None
        )
    }

    meta = ResponseMeta(
        timestamp=datetime.now().isoformat(),
        applied_filters={"bizes_id": bizes_id}
    )

    return {
        "store": store_item.model_dump(),
        "ui_presentation": ui_badges,
        "meta": meta.model_dump()
    }


@router.get("/density/grid", response_model=GridResponse)
def get_spatial_density_grid(
    sigungu_code: Optional[str] = Query(None, description="특정 시군구코드 (예: '11215' 광진구)"),
    sido_code: Optional[str] = Query(None, description="특정 시도코드 (예: '11' 서울특별시)"),
    category_major_id: Optional[str] = Query(None, description="8대 대분류 필터 ('CAT_MAJ_01'~'08')"),
    category_mid_id: Optional[str] = Query(None, description="48대 중분류 필터 ('CAT_MID_0101'~'0806')"),
    min_stores: int = Query(3, ge=1, description="표시할 최소 점포 수"),
    limit: int = Query(1000, ge=1, le=5000, description="반환 격자 수 제한")
):
    """
    3D GIS 대시보드의 '격자 기둥'(deck.gl ColumnLayer / MapLibre 3D Extrusion) 렌더링 데이터를 조회합니다.
    - 전체 업종 조회 시: 사전 집계된 `spatial_density_grid_100m` 테이블에서 초고속 반환
    - 특정 대분류/중분류 필터 지정 시: `store_analytics_lookup`에서 해당 업종의 100m 격자 밀집도를 실시간 계산하여 반환
    """
    norm_maj = category_major_id.strip() if category_major_id and category_major_id.strip() not in ("", "ALL") else None
    norm_mid = category_mid_id.strip() if category_mid_id and category_mid_id.strip() not in ("", "ALL") else None

    if norm_maj or norm_mid:
        where_clauses = ["lon IS NOT NULL AND lat IS NOT NULL"]
        params: List[Any] = []

        if sigungu_code:
            where_clauses.append("std_signgu_code = ?")
            params.append(sigungu_code)
        if sido_code:
            where_clauses.append("std_sido_code = ?")
            params.append(sido_code)
        if norm_maj:
            where_clauses.append("category_major_id = ?")
            params.append(norm_maj)
        if norm_mid:
            where_clauses.append("category_mid_id = ?")
            params.append(norm_mid)

        where_sql = " AND ".join(where_clauses)
        # 특정 업종/중분류 필터 시 밀집도 기둥이 충분히 표현되도록 최소 점포 임계치를 유연하게 조정 (중분류 1개 이상, 대분류 2개 이상)
        effective_min = 1 if norm_mid else min(min_stores, 2)

        sql = f"""
            SELECT
                COALESCE(MAX(std_signgu_code), '00000') AS sgg_code,
                ROUND(lon, 3) AS center_lon,
                ROUND(lat, 3) AS center_lat,
                COUNT(*) AS total_stores,
                SUM(CASE WHEN is_brand_linked = 1 THEN 1 ELSE 0 END) AS brand_stores,
                COALESCE(MAX(category_major_name), '기타') AS top_category_name
            FROM store_analytics_lookup
            WHERE {where_sql}
            GROUP BY ROUND(lon, 3), ROUND(lat, 3)
            HAVING COUNT(*) >= ?
            ORDER BY total_stores DESC
            LIMIT ?;
        """
        rows = query_all(sql, tuple(params + [effective_min, limit]))

        # 만약 대분류 필터에서 2개 이상 격자가 너무 적으면(5개 미만) 1개 이상으로 자동 완화하여 빈 지도를 방지
        if len(rows) < 5 and effective_min > 1:
            rows = query_all(sql, tuple(params + [1, limit]))

        items = []
        for r in rows:
            c_lon = float(r["center_lon"])
            c_lat = float(r["center_lat"])
            sgg = r["sgg_code"]
            grid_id = f"GRID_{sgg}_{int(round(c_lon * 1000))}_{int(round(c_lat * 1000))}"
            tot = int(r["total_stores"])
            items.append(
                SpatialGridItem(
                    grid_id=grid_id,
                    center_lon=c_lon,
                    center_lat=c_lat,
                    min_lon=round(c_lon - 0.0005, 6),
                    min_lat=round(c_lat - 0.00045, 6),
                    max_lon=round(c_lon + 0.0005, 6),
                    max_lat=round(c_lat + 0.00045, 6),
                    total_stores=tot,
                    brand_stores=int(r["brand_stores"] or 0),
                    top_category_name=r["top_category_name"],
                    column_height_m=round(tot * 8.5, 1)
                )
            )

        meta = ResponseMeta(
            timestamp=datetime.now().isoformat(),
            applied_filters={
                "sigungu_code": sigungu_code,
                "sido_code": sido_code,
                "category_major_id": norm_maj,
                "category_mid_id": norm_mid,
                "min_stores": effective_min
            },
            total_count=len(items)
        )
        return GridResponse(data=items, meta=meta)

    where_clauses = ["total_stores >= ?"]
    params = [min_stores]

    if sigungu_code:
        where_clauses.append("sigungu_code = ?")
        params.append(sigungu_code)

    if sido_code:
        where_clauses.append("sido_code = ?")
        params.append(sido_code)

    where_sql = " AND ".join(where_clauses)

    sql = f"""
        SELECT 
            grid_id, center_lon, center_lat,
            min_lon, min_lat, max_lon, max_lat,
            total_stores, brand_stores, top_category_name, column_height_m
        FROM spatial_density_grid_100m
        WHERE {where_sql}
        ORDER BY total_stores DESC
        LIMIT ?;
    """
    rows = query_all(sql, tuple(params + [limit]))

    items = [
        SpatialGridItem(
            grid_id=r["grid_id"],
            center_lon=r["center_lon"],
            center_lat=r["center_lat"],
            min_lon=r["min_lon"],
            min_lat=r["min_lat"],
            max_lon=r["max_lon"],
            max_lat=r["max_lat"],
            total_stores=r["total_stores"],
            brand_stores=r["brand_stores"],
            top_category_name=r["top_category_name"],
            column_height_m=r["column_height_m"]
        ) for r in rows
    ]

    meta = ResponseMeta(
        timestamp=datetime.now().isoformat(),
        applied_filters={
            "sigungu_code": sigungu_code,
            "sido_code": sido_code,
            "category_major_id": None,
            "category_mid_id": None,
            "min_stores": min_stores
        },
        total_count=len(items)
    )

    return GridResponse(data=items, meta=meta)


@router.get("/hotspots", response_model=HotspotsResponse)
def list_commercial_hotspots(
    sido_code: Optional[str] = Query(None, description="시도코드 필터 (예: '11')"),
    sigungu_code: Optional[str] = Query(None, description="시군구코드 필터 (예: '11215', 지정 시 해당 시군구 동적 핫스팟 Top 5 보장)"),
    category_major_id: Optional[str] = Query(None, description="8대 대분류 필터 ('CAT_MAJ_01'~'08')")
):
    """
    주요 상권 핫스팟 및 3D 드론 비행 카메라 경로(피치, 방위각, 줌레벨) 목록을 반환합니다.
    - 고정 10개 상권이 없는 시군구(전국 246개 시군구)나 특정 업종 필터 선택 시에도,
      실제 점포 밀집도 상위 클러스터(Top 5)를 동적 추출하여 빈 화면 없이 핵심 상권을 안내합니다.
    """
    norm_sido = sido_code.strip() if sido_code and sido_code.strip() not in ("", "00") else None
    norm_sgg = sigungu_code.strip() if sigungu_code and sigungu_code.strip() != "" else None
    norm_maj = category_major_id.strip() if category_major_id and category_major_id.strip() not in ("", "ALL") else None

    # 1. 기본 조회 (필터가 전혀 없거나, 특정 업종 없이 정적 핫스팟이 존재하는 경우 우선 활용)
    if not norm_maj:
        static_where = []
        static_params: List[Any] = []
        if norm_sgg:
            static_where.append("sigungu_code = ?")
            static_params.append(norm_sgg)
        elif norm_sido:
            static_where.append("sido_code = ?")
            static_params.append(norm_sido)

        where_clause = f"WHERE {' AND '.join(static_where)}" if static_where else ""
        sql = f"""
            SELECT 
                hotspot_id, hotspot_name, sido_code, sigungu_code,
                center_lon, center_lat, pitch, bearing, zoom,
                store_count, franchise_ratio, dominant_category_name, description, tour_order
            FROM commercial_hotspots
            {where_clause}
            ORDER BY tour_order ASC;
        """
        static_rows = query_all(sql, tuple(static_params))
        # 전국 기본 조회이거나 정적 핫스팟이 3개 이상 충분하면 즉시 반환
        if not norm_sgg and not norm_sido and static_rows:
            items = [CommercialHotspotItem(**r) for r in static_rows]
            return HotspotsResponse(
                data=items,
                meta=ResponseMeta(
                    timestamp=datetime.now().isoformat(),
                    applied_filters={"sido_code": norm_sido, "sigungu_code": norm_sgg, "category_major_id": None},
                    total_count=len(items)
                )
            )
    else:
        static_rows = []

    # 2. 선택된 시군구/시도 또는 특정 업종 기준으로 실시간 핵심 상권 클러스터(Top 5) 동적 추출
    dyn_where = ["lon IS NOT NULL AND lat IS NOT NULL"]
    dyn_params: List[Any] = []
    if norm_sgg:
        dyn_where.append("std_signgu_code = ?")
        dyn_params.append(norm_sgg)
    elif norm_sido:
        dyn_where.append("std_sido_code = ?")
        dyn_params.append(norm_sido)
    if norm_maj:
        dyn_where.append("category_major_id = ?")
        dyn_params.append(norm_maj)

    # 약 200m~300m 상권 블록 단위(경위도 0.002도 격자)로 군집화하여 상위 5대 상권 추출
    dyn_sql = f"""
        SELECT
            COALESCE(MAX(std_sido_code), '11') AS sido_code,
            COALESCE(MAX(std_signgu_code), '11215') AS sigungu_code,
            COALESCE(MAX(std_signgu_name), '선택 지역') AS sgg_name,
            ROUND(AVG(lon), 5) AS center_lon,
            ROUND(AVG(lat), 5) AS center_lat,
            COUNT(*) AS store_count,
            ROUND(SUM(CASE WHEN brand_officiality IN ('FRANCHISE_CONFIRMED', 'BRAND_CONFIRMED') THEN 1 ELSE 0 END) * 100.0 / NULLIF(COUNT(*), 0), 1) AS franchise_ratio,
            COALESCE(MAX(category_major_name), '한식') AS dominant_category_name,
            COALESCE(MAX(category_mid_name), '') AS dominant_mid_name,
            COALESCE(MAX(rdnm_adr), MAX(lno_adr), '') AS sample_addr
        FROM store_analytics_lookup
        WHERE {" AND ".join(dyn_where)}
        GROUP BY CAST(ROUND(lon / 0.0025) AS INT), CAST(ROUND(lat / 0.0022) AS INT)
        HAVING COUNT(*) >= 3
        ORDER BY store_count DESC
        LIMIT 8;
    """
    dyn_rows = query_all(dyn_sql, tuple(dyn_params))

    def extract_street_or_dong(addr: str, sgg_name: str, idx: int) -> str:
        if not addr:
            return f"{sgg_name} 중심상권 #{idx}"
        parts = addr.strip().split()
        # 예: "서울특별시 광진구 아차산로 241" -> "광진구 아차산로 상권"
        if len(parts) >= 3:
            return f"{parts[1]} {parts[2]} 핵심상권"
        return f"{sgg_name} 핵심상권 #{idx}"

    combined_items: List[CommercialHotspotItem] = [CommercialHotspotItem(**r) for r in static_rows]
    seen_coords = [(it.center_lon, it.center_lat) for it in combined_items]

    for idx, r in enumerate(dyn_rows, start=1):
        if len(combined_items) >= 5:
            break
        c_lon = float(r["center_lon"])
        c_lat = float(r["center_lat"])
        # 기존 정적 핫스팟과 너무 가까운(약 300m 이내) 중복 블록은 건너뜀
        if any(abs(c_lon - slon) < 0.003 and abs(c_lat - slat) < 0.003 for slon, slat in seen_coords):
            continue
        seen_coords.append((c_lon, c_lat))
        order_no = len(combined_items) + 1
        street_label = extract_street_or_dong(r["sample_addr"], r["sgg_name"], order_no)
        cat_label = r["dominant_mid_name"] if norm_maj and r["dominant_mid_name"] else r["dominant_category_name"]
        combined_items.append(
            CommercialHotspotItem(
                hotspot_id=f"DYN_HOTSPOT_{r['sigungu_code']}_{order_no}",
                hotspot_name=street_label,
                sido_code=r["sido_code"],
                sigungu_code=r["sigungu_code"],
                center_lon=c_lon,
                center_lat=c_lat,
                pitch=54.0,
                bearing=-22.0,
                zoom=15.6,
                store_count=int(r["store_count"]),
                franchise_ratio=float(r["franchise_ratio"] or 0.0),
                dominant_category_name=cat_label,
                description=f"{r['sgg_name']} 내 점포 밀집도 상위 #{order_no}위 상권 클러스터",
                tour_order=order_no
            )
        )

    meta = ResponseMeta(
        timestamp=datetime.now().isoformat(),
        applied_filters={
            "sido_code": norm_sido,
            "sigungu_code": norm_sgg,
            "category_major_id": norm_maj
        },
        total_count=len(combined_items)
    )

    return HotspotsResponse(data=combined_items, meta=meta)
