"""
Stage 4E: FastAPI 데이터 검증 및 응답 스키마 (Pydantic v2)
프로젝트: D:/Franchise_Dashboard
위치: src/stage4e/api/schemas.py
"""

from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field


class ResponseMeta(BaseModel):
    """모든 API 응답에 부착되는 필수 메타데이터 스키마"""
    data_reference_month: str = Field(default="2026-07", description="데이터 수집 기준월")
    universe_definition: str = Field(
        default="전국 외식업 735,185개 고유 점포 (소진공 I2 음식업, 주점 I211 및 구내식당 I20701 제외)",
        description="분석 대상 점포 모수 정의"
    )
    decoupled_axes: Dict[str, List[str]] = Field(
        default={
            "brand_officiality": ["FRANCHISE_CONFIRMED", "BRAND_CONFIRMED", "UNVERIFIED", "UNMATCHED"],
            "store_match_status": ["MATCH_VERIFIED", "MATCH_AUTO_HIGH_CONFIDENCE", "MATCH_PROVISIONAL", "REVIEW_REQUIRED", "UNMATCHED"],
            "operation_type": ["COMPANY_OPERATED", "FRANCHISED", "UNKNOWN"],
            "classification_status": ["CATEGORY_CONFIRMED", "CATEGORY_PROVISIONAL", "AMBIGUOUS_REVIEW"]
        },
        description="독립적으로 분리된 4축 상태 분류 체계"
    )
    timestamp: str = Field(..., description="응답 생성 일시 (ISO-8601)")
    applied_filters: Dict[str, Any] = Field(default_factory=dict, description="요청 시 적용된 필터 조건")
    page: Optional[int] = Field(default=None, description="현재 페이지 번호")
    page_size: Optional[int] = Field(default=None, description="페이지당 결과 수")
    total_count: Optional[int] = Field(default=None, description="조건에 일치하는 총 건수")


# 1. 전국 현황 요약
class SummaryStats(BaseModel):
    total_stores: int = Field(..., description="전국 외식업 총 고유 점포 수 (735,185건 대사)")
    brand_linked_stores: int = Field(..., description="브랜드 연결 점포 수 (프랜차이즈/체인 후보)")
    independent_stores: int = Field(..., description="미매칭 독립 점포 수")
    franchise_confirmed_stores: int = Field(..., description="공인 72개 가맹사업 브랜드 점포 수")
    brand_confirmed_stores: int = Field(..., description="공인 7개 직영 체인 브랜드 점포 수")
    unverified_brand_stores: int = Field(..., description="미검증 후보 브랜드 점포 수")
    confirmed_franchisees: int = Field(..., description="확인된 공식 가맹점 수")
    ambiguous_category_stores: int = Field(..., description="모호 분류 검토 점포 수 (104,060건)")
    confirmed_category_stores: int = Field(..., description="확정 업종 점포 수 (48,938건)")
    provisional_category_stores: int = Field(..., description="잠정 업종 점포 수 (582,187건)")
    franchise_penetration_rate: float = Field(..., description="공인 프랜차이즈 침투율 (%)")
    brand_penetration_rate: float = Field(..., description="전체 브랜드 침투율 (%)")
    total_provinces: int = Field(default=16, description="전국 시도 수")
    total_districts: int = Field(default=256, description="전국 시군구 수")
    total_candidate_brands: int = Field(default=5062, description="추출된 브랜드 후보 수")
    density_status: str = Field(default="UNAVAILABLE", description="면적 데이터 검증 상태")


class SummaryResponse(BaseModel):
    data: SummaryStats
    meta: ResponseMeta


# 2. 지역별 통계
class RegionStatsItem(BaseModel):
    region_code: str = Field(..., description="행정구역 코드 ('11', '11680' 등)")
    region_name: str = Field(..., description="지역명 (예: 서울특별시 강남구)")
    region_type: str = Field(..., description="'SIDO' 또는 'SIGUNGU'")
    total_stores: int = Field(..., description="지역 내 고유 점포 수")
    brand_linked_stores: int = Field(..., description="브랜드 연결 점포 수")
    independent_stores: int = Field(..., description="독립 점포 수")
    franchise_confirmed_stores: int = Field(..., description="공인 프랜차이즈 점포 수")
    confirmed_franchisees: int = Field(..., description="확인된 가맹점 수")
    ambiguous_category_stores: int = Field(..., description="모호 분류 점포 수")
    franchise_penetration_rate: float = Field(..., description="공인 프랜차이즈 침투율 (%)")
    brand_penetration_rate: float = Field(..., description="전체 브랜드 침투율 (%)")
    center_lon: Optional[float] = Field(None, description="지역 중심 경도")
    center_lat: Optional[float] = Field(None, description="지역 중심 위도")
    density_status: str = Field(default="UNAVAILABLE", description="밀집도 산출 상태")


class RegionListResponse(BaseModel):
    data: List[RegionStatsItem]
    meta: ResponseMeta


# 3. 업종별 통계
class CategoryStatsItem(BaseModel):
    category_major_id: str = Field(..., description="8대 대분류 ID ('CAT_MAJ_01'~'08')")
    category_major_name: str = Field(..., description="8대 대분류명 (한식, 카페·음료 등)")
    category_mid_id: str = Field(..., description="48대 중분류 ID ('CAT_MID_0101'~'0806')")
    category_mid_name: str = Field(..., description="48대 중분류명")
    total_stores: int = Field(..., description="업종 총 점포 수 (모호 분류 포함)")
    stores_excluding_ambiguous: int = Field(..., description="모호 분류 제외 순수 확정 점포 수")
    brand_linked_stores: int = Field(..., description="브랜드 소속 점포 수")
    independent_stores: int = Field(..., description="독립 점포 수")
    franchise_confirmed_stores: int = Field(..., description="공인 프랜차이즈 점포 수")
    ambiguous_stores: int = Field(..., description="모호 분류 점포 수")
    category_share_pct: float = Field(..., description="지역/전국 대비 비중 (%)")
    category_rank: int = Field(..., description="순위")


class CategoryListResponse(BaseModel):
    data: List[CategoryStatsItem]
    meta: ResponseMeta


# 4. 브랜드 검색 및 상세
class BrandSearchItem(BaseModel):
    internal_brand_id: str = Field(..., description="내부 브랜드 ID ('BRD_xxxx')")
    brand_name_std: str = Field(..., description="표준 브랜드명")
    brand_officiality: str = Field(..., description="공식성 상태")
    category_major_id: str = Field(..., description="대표 대분류 ID")
    category_mid_id: str = Field(..., description="대표 중분류 ID")
    nationwide_store_count: int = Field(..., description="전국 발견 점포 수")
    confirmed_franchisee_count: int = Field(..., description="확인된 가맹점 수")
    market_share_in_nation: float = Field(..., description="전국 점유율 (%)")


class BrandDistributionItem(BaseModel):
    region_code: str = Field(..., description="지역코드")
    region_name: str = Field(..., description="지역명")
    discovered_store_count: int = Field(..., description="지역 내 발견 점포 수")
    confirmed_franchisee_count: int = Field(..., description="확인된 가맹점 수")
    market_share_in_region: float = Field(..., description="지역 외식업 내 점포 비중 (%)")
    category_share_in_region: float = Field(..., description="동일 업종 내 경쟁 비중 (%)")
    rank_in_region: int = Field(..., description="지역 내 순위")


class BrandDistributionResponse(BaseModel):
    brand_info: BrandSearchItem
    distribution: List[BrandDistributionItem]
    meta: ResponseMeta


# 5. 공간 및 지도 점포 검색
class StoreDetailItem(BaseModel):
    bizes_id: str = Field(..., description="소진공 고유 점포 번호")
    bizes_nm: str = Field(..., description="상호명")
    brch_nm: Optional[str] = Field(None, description="지점명")
    std_sido_name: str = Field(..., description="시도명")
    std_signgu_name: str = Field(..., description="시군구명")
    rdnm_adr: Optional[str] = Field(None, description="도로명주소")
    lno_adr: Optional[str] = Field(None, description="지번주소")
    lon: float = Field(..., description="경도 (WGS84)")
    lat: float = Field(..., description="위도 (WGS84)")
    category_major_id: str = Field(..., description="8대 대분류 ID")
    category_major_name: str = Field(..., description="8대 대분류명")
    category_mid_id: str = Field(..., description="48대 중분류 ID")
    category_mid_name: str = Field(..., description="48대 중분류명")
    primary_brand_id: str = Field(..., description="주 브랜드 ID")
    brand_name_std: Optional[str] = Field(None, description="표준 브랜드명")
    brand_officiality: str = Field(..., description="브랜드 공식성")
    match_status: str = Field(..., description="매칭 신뢰도 상태")
    operation_type: str = Field(..., description="운영 형태 (FRANCHISED, COMPANY_OPERATED, UNKNOWN)")
    classification_status: str = Field(..., description="업종분류 상태 (CATEGORY_CONFIRMED, CATEGORY_PROVISIONAL, AMBIGUOUS_REVIEW)")
    is_brand_linked: int = Field(..., description="브랜드 소속 여부 (1/0)")
    is_category_divergent: int = Field(..., description="복합메뉴/업종불일치 여부 (1/0)")
    is_multi_brand_store: int = Field(..., description="23개 복수 후보 매장 여부 (1/0)")
    auxiliary_brand_names: Optional[str] = Field(None, description="보조 브랜드명")


class GeoJSONGeometry(BaseModel):
    type: str = "Point"
    coordinates: List[float] = Field(..., description="[lon, lat]")


class GeoJSONFeature(BaseModel):
    type: str = "Feature"
    geometry: GeoJSONGeometry
    properties: StoreDetailItem


class GeoJSONFeatureCollection(BaseModel):
    type: str = "FeatureCollection"
    features: List[GeoJSONFeature]
    meta: ResponseMeta


# 6. 3D 상권 핫스팟 및 드론 비행 투어
class CommercialHotspotItem(BaseModel):
    hotspot_id: str = Field(..., description="핫스팟 ID ('HOTSPOT_01' 등)")
    hotspot_name: str = Field(..., description="핫스팟 명칭 (예: 광진 건대입구 맛의거리)")
    sido_code: str = Field(..., description="시도코드")
    sigungu_code: str = Field(..., description="시군구코드")
    center_lon: float = Field(..., description="카메라 중심 경도")
    center_lat: float = Field(..., description="카메라 중심 위도")
    pitch: float = Field(..., description="3D 틸트 카메라 각도")
    bearing: float = Field(..., description="카메라 방위각")
    zoom: float = Field(..., description="권장 줌레벨")
    store_count: int = Field(..., description="상권 내 점포 수")
    franchise_ratio: float = Field(..., description="프랜차이즈 점유율 (%)")
    dominant_category_name: str = Field(..., description="최다 업종")
    description: Optional[str] = Field(None, description="상권 비즈니스 인사이트")
    tour_order: int = Field(..., description="투어 순서")


class HotspotsResponse(BaseModel):
    data: List[CommercialHotspotItem]
    meta: ResponseMeta


# 7. 3D 100m 밀집도 격자 기둥 (deck.gl ColumnLayer 연동)
class SpatialGridItem(BaseModel):
    grid_id: str = Field(..., description="격자 셀 고유키")
    center_lon: float = Field(..., description="셀 중심 경도")
    center_lat: float = Field(..., description="셀 중심 위도")
    min_lon: float = Field(..., description="바운딩 박스 서쪽")
    min_lat: float = Field(..., description="바운딩 박스 남쪽")
    max_lon: float = Field(..., description="바운딩 박스 동쪽")
    max_lat: float = Field(..., description="바운딩 박스 북쪽")
    total_stores: int = Field(..., description="셀 내 점포 수")
    brand_stores: int = Field(..., description="셀 내 브랜드 점포 수")
    top_category_name: str = Field(..., description="대표 업종명")
    column_height_m: float = Field(..., description="3D 기둥 렌더링 높이 (m)")


class GridResponse(BaseModel):
    data: List[SpatialGridItem]
    meta: ResponseMeta
