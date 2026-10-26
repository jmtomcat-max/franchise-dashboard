"""
Phase 5B: 공정거래위원회 거시통계 API 응답 스키마
프로젝트: D:/Franchise_Dashboard
위치: src/stage4e/api/ftc_schemas.py

준수 규격:
- reports/phase5b_ftc_dashboard_api_contract_r1.json
- reports/phase5b_ftc_dashboard_integration_design_r1.md
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


# ==============================================================================
# 공통 메타 및 에러 스키마
# ==============================================================================

class ResponseMeta(BaseModel):
    calculation_method: Optional[str] = Field(None, description="계산 출처 및 방법")
    timestamp: str = Field(..., description="ISO-8601 한국 표준시 타임스탬프 (+09:00)")


class FtcErrorResponse(BaseModel):
    status: str = Field(..., description="에러 상태 코드명")
    error_code: str = Field(..., description="세부 에러 코드")
    message: str = Field(..., description="에러 안내 메시지")
    requested_year: Optional[str] = Field(None, description="요청된 연도 (해당 시)")


# ==============================================================================
# 1. /api/v1/ftc/status
# ==============================================================================

class FtcStatusData(BaseModel):
    latest_benchmark_year: str = Field(..., description="최신 기준연도 (예: 2026)")
    financial_year: str = Field(..., description="실제 결산 회계연도 (예: 2025)")
    display_label: str = Field(..., description="화면 노출용 라벨")
    snapshot_status: str = Field(..., description="스냅샷 상태 코드")
    is_snapshot: bool = Field(..., description="스냅샷 여부")
    collected_at: str = Field(..., description="수집 완료 일시")
    total_records: int = Field(..., description="전체 외식업 레코드 수")
    total_brands: int = Field(..., description="전체 고유 브랜드 수")
    total_franchise_stores: int = Field(..., description="전체 가맹점 수 합계")
    total_direct_stores: int = Field(..., description="전체 직영점 수 합계")
    available_years: List[str] = Field(..., description="이용 가능한 4개년 목록")
    version_string: str = Field(..., description="상세 버전 안내 문자열")
    macro_notice: str = Field(..., description="거시통계 주의 안내")


class FtcStatusResponse(BaseModel):
    status: str = Field("SUCCESS", description="응답 상태")
    data: FtcStatusData
    meta: ResponseMeta


# ==============================================================================
# 2. /api/v1/ftc/benchmark/latest
# ==============================================================================

class SampleMetrics(BaseModel):
    total_brand_records: int = Field(..., description="전체 브랜드 레코드 수")
    sales_positive_records: int = Field(..., description="양수(>0) 매출 브랜드 수")
    sales_zero_records: int = Field(..., description="0원(=0) 매출 공시 브랜드 수")
    sales_null_records: int = Field(..., description="결측(NULL) 매출 브랜드 수")
    total_franchise_stores: int = Field(..., description="가맹점 수 합계")
    total_direct_stores: int = Field(..., description="직영점 수 합계")


class SalesBenchmarks(BaseModel):
    median_sales_thousand_krw: float = Field(..., description="매출액 중앙값 (1순위 권장 대표값, 천원)")
    trimmed_mean_5pct_thousand_krw: float = Field(..., description="매출액 5% 절사평균 (2순위 권장 대표값, 천원)")
    store_weighted_avg_thousand_krw: float = Field(..., description="점포 수 가중평균 매출액 (천원)")
    simple_avg_positive_thousand_krw: float = Field(..., description="양수 매출 브랜드 단순평균 (천원)")
    all_records_avg_thousand_krw: float = Field(..., description="0원 포함 전체 브랜드 단순평균 (천원)")
    recommended_primary_metric: str = Field("median_sales_thousand_krw", description="권장 1순위 대표값 필드명")
    recommended_secondary_metric: str = Field("trimmed_mean_5pct_thousand_krw", description="권장 2순위 대표값 필드명")
    weighted_avg_denominator_stores: int = Field(..., description="가중평균 산출에 사용된 실제 가맹점 수 분모")


class CostItem(BaseModel):
    median_thousand_krw: float = Field(..., description="중앙값 (천원)")
    mean_thousand_krw: float = Field(..., description="산술평균 (천원)")
    valid_count: int = Field(..., description="유효 공시 표본 수")
    field_note: Optional[str] = Field(None, description="항목 안내 설명")
    is_official_stat: Optional[bool] = Field(None, description="공식 통계 여부")
    disclaimer: Optional[str] = Field(None, description="법적 면책 안내")


class StartupCostComponents(BaseModel):
    reported_deposit_amount: CostItem = Field(..., description="공정위 depstAmt (가맹본부 보고 보증금액)")
    franchise_fee_jng_amt: CostItem = Field(..., description="가맹비")
    education_fee_edu_amt: CostItem = Field(..., description="교육비")
    guarantee_fee_grnte_amt: CostItem = Field(..., description="보증금")
    interior_cost_intrr_amt: CostItem = Field(..., description="인테리어 비용")
    interior_cost_per_pyeong_3_3sqm: CostItem = Field(..., description="3.3㎡당 인테리어 비용")
    tentative_derived_sum: CostItem = Field(..., description="항목 합산 잠정 창업비용 (참고용)")


class QualityNotice(BaseModel):
    type: str = Field(..., description="품질 알림 유형 (SNAPSHOT_NOTICE, ZERO_SALES_NOTICE, FALLBACK_NOTICE 등)")
    badge: str = Field(..., description="화면 배지 라벨")
    message: str = Field(..., description="품질 상세 안내 메시지")


class FtcBenchmarkData(BaseModel):
    benchmark_year: str = Field(..., description="적용된 기준연도")
    financial_year: str = Field(..., description="실제 결산 회계연도")
    display_label: str = Field(..., description="화면 표출 라벨")
    is_fallback_applied: bool = Field(..., description="직전 연도 대체 적용 여부")
    fallback_reason: Optional[str] = Field(None, description="대체 적용 사유")
    category_major_id: str = Field(..., description="8대 외식업 대분류 코드")
    category_major_name: str = Field(..., description="8대 외식업 대분류 명칭")
    mapped_ftc_categories: List[str] = Field(..., description="연계된 공정위 중분류 목록")
    mapping_type: str = Field(..., description="매핑 유형 (ONE_TO_ONE, MANY_TO_ONE)")
    mapping_status: str = Field("PROPOSED_FOR_APPROVAL", description="매핑 승인 상태")
    sample_metrics: SampleMetrics
    sales_benchmarks: SalesBenchmarks
    startup_cost_components: StartupCostComponents
    quality_notices: List[QualityNotice] = Field(default_factory=list)


class FtcBenchmarkResponse(BaseModel):
    status: str = Field("SUCCESS", description="응답 상태")
    data: FtcBenchmarkData
    meta: ResponseMeta


# ==============================================================================
# 3. /api/v1/ftc/trends
# ==============================================================================

class YearlyTrendItem(BaseModel):
    benchmark_year: str = Field(..., description="기준연도")
    financial_year: str = Field(..., description="회계연도")
    is_snapshot: bool = Field(..., description="스냅샷 여부")
    snapshot_badge: Optional[str] = Field(None, description="스냅샷 배지 (해당 시)")
    sample_count: int = Field(..., description="전체 브랜드 표본 수")
    total_franchise_stores: int = Field(..., description="가맹점 수 합계")
    total_direct_stores: int = Field(..., description="직영점 수 합계")
    median_sales_thousand_krw: float = Field(..., description="매출액 중앙값 (천원)")
    trimmed_mean_5pct_thousand_krw: float = Field(..., description="매출액 5% 절사평균 (천원)")
    store_weighted_avg_thousand_krw: float = Field(..., description="점포 수 가중평균 매출액 (천원)")
    simple_avg_thousand_krw: float = Field(..., description="단순평균 매출액 (천원)")
    denom_stores: int = Field(..., description="가중평균 분모 가맹점 수")


class FtcTrendsData(BaseModel):
    category_major_id: str = Field(..., description="8대 대분류 ID")
    category_major_name: str = Field(..., description="8대 대분류 명칭")
    trend_mode: str = Field("FULL_POPULATION_CROSS_SECTIONAL", description="추세 모드")
    balanced_panel_active: bool = Field(False, description="균형 패널 활성 여부 (생존편향 방지 기본 False)")
    panel_inactive_reason: str = Field(..., description="패널 비활성 사유 안내")
    yearly_series: List[YearlyTrendItem]
    macro_guidance: str = Field(..., description="거시 시계열 해석 가이드")


class FtcTrendsResponse(BaseModel):
    status: str = Field("SUCCESS", description="응답 상태")
    data: FtcTrendsData
    meta: ResponseMeta


# ==============================================================================
# 4. /api/v1/ftc/years
# ==============================================================================

class YearMetaItem(BaseModel):
    benchmark_year: str = Field(..., description="기준연도")
    financial_year: str = Field(..., description="회계연도")
    is_default: bool = Field(..., description="기본 선택 연도 여부")
    is_snapshot: bool = Field(..., description="스냅샷 여부")
    label: str = Field(..., description="셀렉터 표출용 라벨")


class FtcYearsResponse(BaseModel):
    status: str = Field("SUCCESS", description="응답 상태")
    data: List[YearMetaItem]
    meta: ResponseMeta
