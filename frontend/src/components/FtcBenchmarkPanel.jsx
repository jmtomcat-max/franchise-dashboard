import React, { useState, useRef, useEffect, useMemo } from 'react';
import { calculateFtcYoyComparison } from '../utils/ftcYoyComparison';

/**
 * 금액을 읽기 쉬운 만원 / 억원 단위로 포맷팅합니다.
 * @param {number} thousandKrw 천원 단위 수치
 */
function formatCurrency(thousandKrw) {
  if (thousandKrw === null || thousandKrw === undefined || isNaN(thousandKrw)) {
    return '-';
  }
  const manwon = thousandKrw / 10;
  if (manwon >= 10000) {
    const eok = (manwon / 10000).toFixed(2);
    return `${Number(manwon).toLocaleString('ko-KR', { maximumFractionDigits: 0 })}만원 (${eok}억원)`;
  }
  return `${Number(manwon).toLocaleString('ko-KR', { maximumFractionDigits: 0 })}만원`;
}

function formatManwonOnly(thousandKrw) {
  if (thousandKrw === null || thousandKrw === undefined || isNaN(thousandKrw)) {
    return '-';
  }
  const manwon = Math.round(thousandKrw / 10);
  return `${manwon.toLocaleString('ko-KR')}만원`;
}

function formatEokShort(thousandKrw) {
  if (thousandKrw === null || thousandKrw === undefined || isNaN(thousandKrw)) {
    return '-';
  }
  const eok = (thousandKrw / 100000).toFixed(2);
  return `${eok}억`;
}

const SIDO_FALLBACK_NAMES = {
  '00': '전국',
  '11': '서울',
  '26': '부산',
  '27': '대구',
  '28': '인천',
  '29': '광주',
  '12': '광주',
  '30': '대전',
  '31': '울산',
  '36': '세종',
  '41': '경기',
  '42': '강원',
  '51': '강원',
  '43': '충북',
  '44': '충남',
  '45': '전북',
  '52': '전북',
  '46': '전남',
  '47': '경북',
  '48': '경남',
  '50': '제주'
};

export default function FtcBenchmarkPanel({
  categoryInfo,
  isAllCategory = false,
  onSelectCategory,
  selectedSido = '11',
  selectedRegionInfo = null,
  benchmarkData,
  trendsData,
  loading = false,
  error = null,
  onRetry,
  selectedYear,
  onSelectYear,
  yearsList = [],
  isDrawerOpen = false,
  onCloseDrawer,
  onToggleDrawer
}) {
  // ESC 키로 드로어 닫기 핸들러
  useEffect(() => {
    if (!isDrawerOpen) return;
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        if (onCloseDrawer) onCloseDrawer();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isDrawerOpen, onCloseDrawer]);

  // URL 쿼리 파라미터 기반 모바일 확장 모드 지원
  const urlParams = typeof window !== 'undefined' ? new URLSearchParams(window.location.search) : null;
  const initialMobileExpanded = urlParams && urlParams.get('mobile_expand') === 'true';

  // 데스크톱 접기/펼치기 상태 (기본: 펼침)
  const [isCollapsed, setIsCollapsed] = useState(false);
  // 모바일 바텀시트 확장 상태
  const [isMobileExpanded, setIsMobileExpanded] = useState(initialMobileExpanded);
  // 창업비용 상세 아코디언 토글
  const [showCostDetails, setShowCostDetails] = useState(false);

  // Phase 5D Step 2: 2024 대비 2025 완결후보 전년비 파생 계산 (useMemo)
  const yearlySeries = trendsData?.data?.yearly_series;
  const yoyComparison = useMemo(() => {
    return calculateFtcYoyComparison(yearlySeries);
  }, [yearlySeries]);

  // 모바일 터치 스와이프 제스처 핸들링 Ref
  const touchStartYRef = useRef(0);
  const touchStartTimeRef = useRef(0);

  const handleTouchStart = (e) => {
    if (e.touches && e.touches.length > 0) {
      touchStartYRef.current = e.touches[0].clientY;
      touchStartTimeRef.current = Date.now();
    }
  };

  const handleTouchEnd = (e) => {
    if (e.changedTouches && e.changedTouches.length > 0) {
      const touchEndY = e.changedTouches[0].clientY;
      const diffY = touchEndY - touchStartYRef.current;
      // 위로 드래그 시 확장 (-30px 이하)
      if (diffY < -30) {
        setIsMobileExpanded(true);
      } 
      // 아래로 드래그 시 축소 (+30px 이상)
      else if (diffY > 30) {
        setIsMobileExpanded(false);
      }
    }
  };

  const themeColor = categoryInfo?.color || '#059669';
  const drawerClass = isDrawerOpen ? 'drawer-open open' : 'drawer-closed';
  const panelClasses = `ftc-benchmark-panel ${drawerClass} ${isCollapsed ? 'collapsed' : ''} ${isMobileExpanded ? 'mobile-expanded' : 'mobile-collapsed'}`;

  // 1. 로딩 상태
  if (loading) {
    return (
      <aside 
        className={panelClasses}
        aria-label="공정위 거시 벤치마크 패널"
        aria-busy="true"
        id="ftc-benchmark-panel"
      >
        <div className="panel-header">
          <div className="skeleton-line shimmer" style={{ width: '60%', height: '22px' }} />
          <div className="panel-header-actions desktop-only">
            {onCloseDrawer && (
              <button 
                className="drawer-close-btn"
                onClick={onCloseDrawer}
                aria-label="공정위 패널 닫기"
              >
                ✕ 닫기
              </button>
            )}
            <button 
              className="collapse-toggle-btn"
              onClick={() => setIsCollapsed(!isCollapsed)}
              aria-label={isCollapsed ? '패널 펼치기' : '패널 접기'}
            >
              {isCollapsed ? '펼치기 ▾' : '접기 ▴'}
            </button>
          </div>
        </div>
        <div className="panel-body">
          <div className="skeleton-card shimmer" style={{ height: '70px', marginBottom: '10px' }} />
          <div className="skeleton-card shimmer" style={{ height: '110px', marginBottom: '10px' }} />
          <div className="skeleton-card shimmer" style={{ height: '80px' }} />
        </div>
      </aside>
    );
  }

  // 2. 매핑 불가 상태 (HTTP 400 또는 UNMAPPED_CATEGORY)
  if (error && (error.status === 400 || error.data?.status === 'UNMAPPED_CATEGORY')) {
    return (
      <aside 
        className={panelClasses}
        aria-label="공정위 거시 벤치마크 패널"
        id="ftc-benchmark-panel"
      >
        <div className="panel-header">
          <div className="panel-title-group">
            <span className="panel-category-badge unmapped">매핑 검토</span>
            <h3 className="panel-title">{categoryInfo?.name || '선택 업종'}</h3>
          </div>
          <div className="panel-header-actions desktop-only">
            {onCloseDrawer && (
              <button 
                className="drawer-close-btn"
                onClick={onCloseDrawer}
                aria-label="공정위 패널 닫기"
              >
                ✕ 닫기
              </button>
            )}
            <button 
              className="collapse-toggle-btn"
              onClick={() => setIsCollapsed(!isCollapsed)}
              aria-label={isCollapsed ? '패널 펼치기' : '패널 접기'}
            >
              {isCollapsed ? '펼치기 ▾' : '접기 ▴'}
            </button>
          </div>
        </div>
        <div className="panel-body">
          <div className="unmapped-notice-card" role="alert">
            <div className="notice-icon">ℹ️</div>
            <div className="notice-content">
              <strong>거시 벤치마크 미제공 (배타적 매핑 불가)</strong>
              <p>
                선택하신 업종(<code>{categoryInfo?.name}</code>)은 공정위 15개 업종 분류와 배타적 매핑이 불가한 기타 복합 업종(UNMAPPED_REVIEW)입니다.
              </p>
              <p className="notice-sub">
                추정치 임의 매핑을 차단하며, 지도 상권 밀집도 분석은 계속 정상 제공됩니다.
              </p>
            </div>
          </div>
        </div>
      </aside>
    );
  }

  // 3. 데이터 부재 상태 (HTTP 404 NO_DATA)
  if (error && (error.status === 404 || error.data?.status === 'NO_DATA')) {
    return (
      <aside 
        className={panelClasses}
        aria-label="공정위 거시 벤치마크 패널"
        id="ftc-benchmark-panel"
      >
        <div className="panel-header">
          <div className="panel-title-group">
            <span className="panel-category-badge nodata">데이터 없음</span>
            <h3 className="panel-title">{categoryInfo?.name}</h3>
          </div>
          <div className="panel-header-actions desktop-only">
            {onCloseDrawer && (
              <button 
                className="drawer-close-btn"
                onClick={onCloseDrawer}
                aria-label="공정위 패널 닫기"
              >
                ✕ 닫기
              </button>
            )}
            <button 
              className="collapse-toggle-btn"
              onClick={() => setIsCollapsed(!isCollapsed)}
              aria-label={isCollapsed ? '패널 펼치기' : '패널 접기'}
            >
              {isCollapsed ? '펼치기 ▾' : '접기 ▴'}
            </button>
          </div>
        </div>
        <div className="panel-body">
          <div className="no-data-card" role="alert">
            <div className="notice-icon">📂</div>
            <div className="notice-content">
              <strong>요청 연도 등록 데이터 부재</strong>
              <p>{error.data?.message || '요청하신 연도에 해당하는 공정위 등록 데이터가 존재하지 않습니다.'}</p>
              {selectedYear && (
                <button 
                  className="reset-year-btn"
                  onClick={() => onSelectYear(null)}
                >
                  최신 연도 자동 조회로 복귀
                </button>
              )}
            </div>
          </div>
        </div>
      </aside>
    );
  }

  // 4. 일반 API 오류
  if (error || !benchmarkData) {
    return (
      <aside 
        className={panelClasses}
        aria-label="공정위 거시 벤치마크 패널"
        id="ftc-benchmark-panel"
      >
        <div className="panel-header">
          <div className="panel-title-group">
            <span className="panel-category-badge error">연결 오류</span>
            <h3 className="panel-title">{categoryInfo?.name || '공정위 거시 벤치마크'}</h3>
          </div>
          <div className="panel-header-actions desktop-only">
            {onCloseDrawer && (
              <button 
                className="drawer-close-btn"
                onClick={onCloseDrawer}
                aria-label="공정위 패널 닫기"
              >
                ✕ 닫기
              </button>
            )}
            <button 
              className="collapse-toggle-btn"
              onClick={() => setIsCollapsed(!isCollapsed)}
              aria-label={isCollapsed ? '패널 펼치기' : '패널 접기'}
            >
              {isCollapsed ? '펼치기 ▾' : '접기 ▴'}
            </button>
          </div>
        </div>
        <div className="panel-body">
          <div className="api-error-card" role="alert">
            <div className="notice-icon">⚠️</div>
            <div className="notice-content">
              <strong>공정위 거시통계 조회 지연</strong>
              <p>{error?.message || '데이터를 불러오는 중 문제가 발생했습니다.'}</p>
              {onRetry && (
                <button className="panel-retry-btn" onClick={onRetry}>
                  다시 시도
                </button>
              )}
            </div>
          </div>
        </div>
      </aside>
    );
  }

  const data = benchmarkData.data;
  const sample = data.sample_metrics || {};
  const sales = data.sales_benchmarks || {};
  const costs = data.startup_cost_components || {};
  const notices = data.quality_notices || [];
  const fallbackRegionName = SIDO_FALLBACK_NAMES[selectedSido] || '전국';
  const regionCtx = data.region_context || {
    region_name: fallbackRegionName,
    is_regional: selectedSido !== '00' && fallbackRegionName !== '전국'
  };
  const categoryComparison = Array.isArray(data.category_comparison) ? data.category_comparison : [];
  const maxCatCompVal = categoryComparison.reduce(
    (acc, cur) => Math.max(acc, cur.median_sales_thousand_krw || 0, cur.median_cost_thousand_krw || 0),
    1
  );

  // 창업비용 구성 계산 (가맹비, 교육비, 보증금, 인테리어 비율)
  const feeJng = costs.franchise_fee_jng_amt?.median_thousand_krw || 0;
  const feeEdu = costs.education_fee_edu_amt?.median_thousand_krw || 0;
  const feeGrnte = costs.guarantee_fee_grnte_amt?.median_thousand_krw || 0;
  const feeIntrr = costs.interior_cost_intrr_amt?.median_thousand_krw || 0;
  const costSum = feeJng + feeEdu + feeGrnte + feeIntrr;
  const pctJng = costSum > 0 ? (feeJng / costSum) * 100 : 10;
  const pctEdu = costSum > 0 ? (feeEdu / costSum) * 100 : 5;
  const pctGrnte = costSum > 0 ? (feeGrnte / costSum) * 100 : 5;
  const pctIntrr = costSum > 0 ? (feeIntrr / costSum) * 100 : 80;

  // 매출 3대 지표 비교 바 계산 (최대값 기준 정규화)
  const maxSalesVal = Math.max(
    sales.median_sales_thousand_krw || 1,
    sales.trimmed_mean_5pct_thousand_krw || 1,
    sales.store_weighted_avg_thousand_krw || 1
  );

  const finYearText = data.financial_year ? `${data.financial_year}년 결산` : '결산연도 확인 불가';

  return (
    <aside 
      className={panelClasses}
      aria-label="공정위 거시 벤치마크 패널"
      id="ftc-benchmark-panel"
      style={{ '--category-theme': themeColor }}
    >
      {/* 모바일 축소 바텀시트 앵커 바 (탭 및 실제 스와이프 제스처 듀얼 지원) */}
      <div 
        className="mobile-bottom-sheet-handle"
        onClick={() => setIsMobileExpanded(!isMobileExpanded)}
        onTouchStart={handleTouchStart}
        onTouchEnd={handleTouchEnd}
        role="button"
        tabIndex={0}
        aria-expanded={isMobileExpanded}
        aria-label="공정위 벤치마크 바텀시트 확장/축소 토글 (탭 또는 위아래 스와이프)"
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            setIsMobileExpanded(!isMobileExpanded);
          }
        }}
      >
        <div className="handle-bar" aria-hidden="true" />
        <div className="mobile-summary-row">
          <span className="mobile-summary-tag">공정위 {regionCtx.region_name}</span>
          <span className="mobile-summary-cat" style={{ color: themeColor }}>
            {categoryInfo?.icon} {data.category_major_name}
          </span>
          <span className="mobile-summary-kpi">
            중위 <strong>{formatEokShort(sales.median_sales_thousand_krw)}</strong>
          </span>
          <span className="mobile-summary-sub">({regionCtx.region_name} 기준)</span>
          <span className="mobile-summary-badge">
            {data.is_fallback_applied 
              ? `${data.benchmark_year}년 대체` 
              : data.benchmark_year === '2026'
                ? `${data.benchmark_year} 스냅샷`
                : `${data.benchmark_year} 등록`}
          </span>
          <span className="mobile-expand-icon" aria-hidden="true">
            {isMobileExpanded ? '▼ 축소' : '▲ 상세'}
          </span>
          {onCloseDrawer && (
            <button 
              type="button"
              className="mobile-drawer-close-btn"
              onClick={(e) => {
                e.stopPropagation();
                onCloseDrawer();
              }}
              aria-label="공정위 바텀시트 닫기"
              title="닫기"
            >
              ✕
            </button>
          )}
        </div>
      </div>

      {/* 데스크톱 패널 헤더 */}
      <div className="panel-header desktop-only">
        <div className="panel-title-group">
          <div className="title-badge-row">
            <span className="panel-category-badge" style={{ backgroundColor: themeColor }}>
              📍 {regionCtx.region_name} · {categoryInfo?.icon} {data.category_major_name}
            </span>
            <span className="panel-year-badge">
              {data.benchmark_year}년 등록 ({finYearText})
            </span>
            {data.is_fallback_applied ? (
              <span className="fallback-pill" title={data.fallback_reason}>
                ⚠️ {data.benchmark_year}년 대체 표출 ({finYearText})
              </span>
            ) : data.benchmark_year === '2026' ? (
              <span className="badge-meta badge-snapshot-amber" title="가맹본부 정보공개서 정기등록 진행 중 스냅샷 (모집단 30% 미등록)">
                진행형 스냅샷
              </span>
            ) : data.benchmark_year === '2025' ? (
              <span className="badge-meta badge-candidate-teal" title="공식 행정 마감 여부 미확인 최신 완결 후보">
                최신 완결 후보 (공식마감 미확인)
              </span>
            ) : null}
            <span className="badge-meta provenance-badge-ftc">공정위 거시 공시</span>
          </div>
          <h3 className="panel-heading">
            {regionCtx.is_regional
              ? `${regionCtx.region_name} 지역 매출·창업비용 분석${selectedRegionInfo?.region_name && selectedRegionInfo.region_code?.length === 5 ? ` (${selectedRegionInfo.region_name} 상권 선택됨)` : ''}`
              : '전국 등록 가맹본부 매출·창업비용 분석'}
          </h3>
        </div>
        <div className="panel-header-actions desktop-only">
          {onCloseDrawer && (
            <button 
              className="drawer-close-btn"
              onClick={onCloseDrawer}
              aria-label="공정위 패널 닫기"
              title="공정위 패널 닫기 (ESC)"
            >
              ✕ 닫기
            </button>
          )}
          <button 
            className="collapse-toggle-btn"
            onClick={() => setIsCollapsed(!isCollapsed)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                setIsCollapsed(!isCollapsed);
              }
            }}
            aria-label={isCollapsed ? '패널 펼치기' : '패널 접기'}
          >
            {isCollapsed ? '펼치기 ▾' : '접기 ▴'}
          </button>
        </div>
      </div>

      {/* 접힌 상태(데스크톱) 미니 바 */}
      {isCollapsed && (
        <div className="collapsed-mini-bar desktop-only" onClick={() => setIsCollapsed(false)}>
          <span>📊 {data.category_major_name} 중위매출: {formatManwonOnly(sales.median_sales_thousand_krw)} ({data.benchmark_year}년 등록 · {finYearText})</span>
          <button 
            className="mini-open-btn"
            onClick={(e) => {
              e.stopPropagation();
              setIsCollapsed(false);
            }}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                e.stopPropagation();
                setIsCollapsed(false);
              }
            }}
            aria-label="패널 다시 펼치기"
          >
            펼치기
          </button>
        </div>
      )}

      {/* 패널 메인 본문 */}
      {!isCollapsed && (
        <div className="panel-body">
          {/* 모바일 확장 시 첫 화면 즉각 인지용 콤팩트 출처/비귀속 배너 */}
          <div className="mobile-first-screen-notice mobile-only" role="note">
            <span className="notice-icon">📌</span>
            <span>공정위 정기공시 {regionCtx.region_name} 가맹본부 벤치마크 (개별 점포·특정 브랜드 실적 아님)</span>
          </div>

          {/* 단일 이전 연도 대체 안내 배너 (원자적 대체 적용 시) */}
          {data.is_fallback_applied && (
            <div className="fallback-alert-banner" role="status">
              <span className="alert-icon">⚠️</span>
              <div className="alert-text">
                <strong>{data.fallback_reason}</strong>
                <p className="fallback-sub">
                  ※ 분모·분자 혼합 없이 <strong>{data.benchmark_year}년 단일 등록연도 ({finYearText}) 기준</strong>으로 제공됩니다.
                </p>
              </div>
            </div>
          )}

          {/* 2026년 진행형 스냅샷 인라인 경고 콜아웃 (호버 불필요, 상시 가시) */}
          {data.benchmark_year === '2026' && (
            <div className="snapshot-inline-alert" role="alert">
              <span className="alert-icon">⚠️</span>
              <div className="alert-content">
                <strong>진행형 스냅샷:</strong> 2026년은 정기공시 진행 중(약 30% 미등록 결손)으로 2025년과 직접 비교가 불가합니다.
              </div>
            </div>
          )}

          {/* 품질 및 스냅샷 안내 배지 라인 */}
          <div className="quality-badges-row">
            {notices.map((n, idx) => (
              <span key={idx} className={`quality-pill pill-${n.type.toLowerCase()}`} title={n.message}>
                {n.badge}
              </span>
            ))}
            <span className="quality-pill pill-sample">
              공시 표본 {sample.sales_positive_records?.toLocaleString()}개 브랜드 (유효 매출 기준)
            </span>
          </div>

          {/* 1. 대표 매출 Hero 섹션 (지역×업종 중앙값 강조 + 전국 대비 격차 배지 + 3대 지표 비교 바) */}
          <section className="visual-hero-section" aria-label="대표 가맹점 연간 매출액">
            <div className="hero-top-row">
              <span className="hero-label">
                {regionCtx.region_name} · {data.category_major_name} 가맹점 연매출 (중앙값)
              </span>
              {regionCtx.is_regional ? (
                <span
                  className={`hero-region-diff ${regionCtx.sales_vs_national_pct >= 0 ? 'up' : 'down'}`}
                  title={`전국 동일 업종 중위 매출(${formatManwonOnly(regionCtx.national_median_sales_thousand_krw)}) 대비`}
                >
                  전국 대비 {regionCtx.sales_vs_national_pct >= 0 ? `+${regionCtx.sales_vs_national_pct}% ▲` : `${regionCtx.sales_vs_national_pct}% ▼`}
                </span>
              ) : (
                <span className="hero-tag" style={{ borderColor: themeColor, color: themeColor }}>전국 기준</span>
              )}
            </div>
            
            <div className="hero-main-stat">
              <span className="hero-stat-number" style={{ color: themeColor }}>
                {formatCurrency(sales.median_sales_thousand_krw)}
              </span>
            </div>

            {/* 특정 브랜드 및 지역 점포 비귀속 상시 안내문 */}
            <div className="hero-scope-disclaimer">
              {regionCtx.is_regional
                ? `* ${regionCtx.region_name} 소재 ${data.category_major_name} 가맹본부(${sample.sales_positive_records}개 브랜드) 공시 기준 (전국 중위: ${formatManwonOnly(regionCtx.national_median_sales_thousand_krw)})`
                : `* 공정위 정기공시 전국 ${data.category_major_name} 가맹본부 기준 거시 통계이며, 개별 점포의 실적이 아닙니다.`}
            </div>

            {/* 시각적 3대 지표 비교 바 (Comparison Bars) */}
            <div className="benchmark-compare-bars">
              <div className="compare-bar-item active-benchmark">
                <div className="bar-label-row">
                  <span className="bar-title">중앙값 (대표)</span>
                  <span className="bar-val">{formatManwonOnly(sales.median_sales_thousand_krw)}</span>
                </div>
                <div className="bar-track">
                  <div 
                    className="bar-fill" 
                    style={{ 
                      width: `${(sales.median_sales_thousand_krw / maxSalesVal) * 100}%`,
                      backgroundColor: themeColor
                    }} 
                  />
                </div>
              </div>

              <div className="compare-bar-item">
                <div className="bar-label-row">
                  <span className="bar-title">5% 절사평균</span>
                  <span className="bar-val">{formatManwonOnly(sales.trimmed_mean_5pct_thousand_krw)}</span>
                </div>
                <div className="bar-track">
                  <div 
                    className="bar-fill" 
                    style={{ 
                      width: `${(sales.trimmed_mean_5pct_thousand_krw / maxSalesVal) * 100}%`,
                      backgroundColor: '#3b82f6'
                    }} 
                  />
                </div>
              </div>

              <div className="compare-bar-item">
                <div className="bar-label-row">
                  <span className="bar-title">
                    점포수 가중평균
                    {sales.weighted_avg_denominator_stores ? (
                      <span className="bar-denom-badge" title="가중평균 산출 대상 유효 가맹점 수">
                        {' '}(분모: {sales.weighted_avg_denominator_stores.toLocaleString()}개점)
                      </span>
                    ) : null}
                  </span>
                  <span className="bar-val">{formatManwonOnly(sales.store_weighted_avg_thousand_krw)}</span>
                </div>
                <div className="bar-track">
                  <div 
                    className="bar-fill" 
                    style={{ 
                      width: `${(sales.store_weighted_avg_thousand_krw / maxSalesVal) * 100}%`,
                      backgroundColor: '#8b5cf6'
                    }} 
                  />
                </div>
              </div>
            </div>
          </section>

          {/* 1-B. 8대 외식업종별 연매출 vs 창업비용(투자효율) 한눈에 비교 섹션 */}
          {categoryComparison.length > 0 && (
            <section className="ftc-cat-comp-section" aria-label="8대 업종별 매출 및 창업비용 비교">
              <div className="ftc-cat-comp-header">
                <div>
                  <span className="ftc-cat-comp-title">
                    📊 8대 업종별 연매출 vs 창업비용 비교 ({regionCtx.region_name})
                  </span>
                  <p className="ftc-cat-comp-sub">
                    업종을 클릭하면 해당 업종으로 즉시 전환됩니다 · <span className="legend-blue">■ 연매출</span> <span className="legend-amber">■ 창업비용</span>
                  </p>
                </div>
                {!isAllCategory && onSelectCategory && (
                  <button
                    type="button"
                    className="ftc-cat-reset-btn"
                    onClick={() => onSelectCategory('ALL')}
                  >
                    전체 업종 보기
                  </button>
                )}
              </div>
              <div className="ftc-cat-comp-list">
                {categoryComparison.map((c, idx) => {
                  const isSelectedCat = data.category_major_id === c.category_major_id;
                  const salesPct = Math.min(100, Math.max(6, (c.median_sales_thousand_krw / maxCatCompVal) * 100));
                  const costPct = Math.min(100, Math.max(6, (c.median_cost_thousand_krw / maxCatCompVal) * 100));
                  return (
                    <button
                      type="button"
                      key={c.category_major_id}
                      className={`ftc-cat-comp-row ${isSelectedCat ? 'active' : ''}`}
                      onClick={() => onSelectCategory && onSelectCategory(c.category_major_id)}
                      title={`${c.category_major_name} 클릭 시 해당 업종 상세 분석으로 전환`}
                    >
                      <div className="ftc-cat-row-top">
                        <span className="ftc-cat-rank">#{idx + 1}</span>
                        <span className="ftc-cat-name">{c.category_major_name}</span>
                        <span className="ftc-cat-nums">
                          매출 <strong className="s-val">{formatEokShort(c.median_sales_thousand_krw)}</strong>
                          {' · '}
                          비용 <strong className="c-val">{formatEokShort(c.median_cost_thousand_krw)}</strong>
                        </span>
                        <span className="ftc-cat-ratio" title="창업비용 대비 연매출 배율 (연매출 ÷ 창업비용)">
                          {c.sales_to_cost_ratio}배
                        </span>
                      </div>
                      <div className="ftc-cat-bars">
                        <div className="ftc-cat-bar-track">
                          <div className="ftc-cat-bar-sales" style={{ width: `${salesPct}%` }} />
                        </div>
                        <div className="ftc-cat-bar-track">
                          <div className="ftc-cat-bar-cost" style={{ width: `${costPct}%` }} />
                        </div>
                      </div>
                    </button>
                  );
                })}
              </div>
            </section>
          )}

          {/* 2. 다년도 거시 매출 추세 차트 (레퍼런스 동영상 스타일의 고대비 바 차트) */}
          {trendsData && trendsData.data?.yearly_series && (
            <section className="visual-trends-section" aria-label="다년도 거시 시계열 추세">
              <div className="trends-section-header">
                <span className="trends-section-title">{regionCtx.region_name} 다년도 매출 추세 (연도별 비교)</span>
                <span className="trends-badge">{regionCtx.region_name} 표본 횡단면</span>
              </div>

              {/* 고품질 연도별 막대 차트 (레퍼런스 영상 00:09~00:15 스타일 - 키보드 접근성 완비) */}
              <div className="trends-bars-chart">
                {trendsData.data.yearly_series.map((yrItem) => {
                  const isCurrentSelected = yrItem.benchmark_year === data.benchmark_year;
                  const isSnap = yrItem.is_snapshot;
                  // 최대 5억원 기준 막대 높이 % (최소 20%)
                  const barHeightPct = Math.min(100, Math.max(22, (yrItem.median_sales_thousand_krw / 450000) * 100));

                  return (
                    <div 
                      key={yrItem.benchmark_year}
                      className={`chart-bar-column ${isCurrentSelected ? 'selected' : ''} ${isSnap ? 'is-snapshot' : ''}`}
                      onClick={() => onSelectYear(yrItem.benchmark_year)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' || e.key === ' ') {
                          e.preventDefault();
                          onSelectYear(yrItem.benchmark_year);
                        }
                      }}
                      role="button"
                      tabIndex={0}
                      aria-label={`${yrItem.benchmark_year}년 거시 벤치마크 선택 (${isSnap ? '진행형 스냅샷' : (yrItem.benchmark_year === '2025' ? '최신 완결 후보' : '확정치')})`}
                      aria-pressed={isCurrentSelected}
                      title={`${yrItem.benchmark_year}년 등록 (${yrItem.financial_year ? `${yrItem.financial_year}년 결산` : '결산연도 확인 불가'}): 중위매출 ${formatManwonOnly(yrItem.median_sales_thousand_krw)} [${isSnap ? '진행형 스냅샷 (전년 직접 비교 불가)' : (yrItem.benchmark_year === '2025' ? '최신 완결 후보 (공식마감 미확인)' : '확정치')}] - Enter 또는 클릭하여 선택`}
                    >
                      {/* 상단 볼드 수치 배지 (레퍼런스 동영상 시그니처 룩) */}
                      <div className={`bar-value-pill ${isSnap ? 'pill-snap' : ''}`}>
                        {formatEokShort(yrItem.median_sales_thousand_krw)}
                      </div>

                      <div className="bar-stick-wrapper">
                        <div 
                          className={`bar-stick ${isSnap ? 'stick-snapshot' : ''}`}
                          style={{ 
                            height: `${barHeightPct}%`,
                            backgroundColor: isSnap ? '#f59e0b' : (isCurrentSelected ? themeColor : '#94a3b8')
                          }}
                        >
                          {isSnap && <div className="stick-stripe-overlay" />}
                        </div>
                      </div>

                      <div className="bar-x-label">
                        <span>{yrItem.benchmark_year}</span>
                        {isSnap && <span className="snap-tag snap-amber">스냅샷</span>}
                        {yrItem.benchmark_year === '2025' && <span className="snap-tag snap-teal">완결후보</span>}
                      </div>
                    </div>
                  );
                })}
              </div>

              <div className="trends-caption">
                * 물가변동 미반영 명목금액 · 2026년은 진행형 스냅샷(모집단 30% 미등록 결손)으로 2025년과 직접 비교 불가 · 2025년은 공식 행정마감 미확인 최신 완결 후보
              </div>
            </section>
          )}

          {/* 2-1. 공정위 2024 대비 2025 완결후보 전년비 보조 비교 블록 (Phase 5D Step 2) */}
          {yoyComparison && (
            <section 
              className="ftc-yoy-comparison-block" 
              aria-label="2024년 대비 2025년 거시 전년비 보조 비교"
            >
              <div className="yoy-header">
                <div className="yoy-title-group">
                  <span className="yoy-title">{regionCtx.region_name} 2024년 대비 2025년 전년비 비교</span>
                  <span className="yoy-status-badge">
                    {yoyComparison.statusNotice2025}
                  </span>
                </div>
                {yoyComparison.isAvailable && (
                  <span className="yoy-sample-info">
                    표본: 2024년 {yoyComparison.baseYearSampleCount != null ? Number(yoyComparison.baseYearSampleCount).toLocaleString('ko-KR') : '-'}개사 → 2025년 {yoyComparison.targetYearSampleCount != null ? Number(yoyComparison.targetYearSampleCount).toLocaleString('ko-KR') : '-'}개사
                  </span>
                )}
              </div>

              {!yoyComparison.isAvailable ? (
                <div className="yoy-notice-banner yoy-notice-fallback" role="note">
                  <span className="yoy-notice-badge">비교 불가</span>
                  <span className="yoy-notice-text">
                    2024년 대비 2025년 전년비 보조 비교 불가 ({yoyComparison.reason || '시계열 데이터 누락'})
                  </span>
                </div>
              ) : (
                <div className="yoy-metrics-grid" role="list" aria-label="4대 전년비 비교 지표">
                  {yoyComparison.metrics.map((metric) => {
                    const isUp = metric.direction === '증가';
                    const isDown = metric.direction === '감소';
                    const isSame = metric.direction === '변동 없음';
                    const isBlocked = !metric.isCalculable || metric.direction === '비교 불가';

                    const dirClass = isUp 
                      ? 'dir-up' 
                      : isDown 
                        ? 'dir-down' 
                        : isSame 
                          ? 'dir-same' 
                          : 'dir-blocked';

                    const dirSymbol = isUp ? '▲ +' : isDown ? '▼ -' : isSame ? '-' : '';

                    return (
                      <div 
                        key={metric.id} 
                        className={`yoy-metric-card ${dirClass}`}
                        role="listitem"
                        tabIndex={0}
                        aria-label={`${metric.label}: 2024년 ${metric.formatted2024}, 2025년 ${metric.formatted2025}, ${isBlocked ? `비교 불가 (${metric.reason || ''})` : `${metric.direction} ${metric.diffAmountText} (${metric.diffRateText})`}`}
                      >
                        <div className="yoy-card-top">
                          <span className="yoy-metric-label">{metric.label}</span>
                          <span className={`yoy-direction-badge ${dirClass}`}>
                            {dirSymbol} {metric.direction}
                          </span>
                        </div>

                        <div className="yoy-values-row">
                          <span className="yoy-val-24" title="2024년 확정 등록치">
                            '24: {metric.formatted2024}
                          </span>
                          <span className="yoy-arrow" aria-hidden="true">→</span>
                          <span className="yoy-val-25" title="2025년 완결 후보치">
                            '25: {metric.formatted2025}
                          </span>
                        </div>

                        <div className="yoy-diff-row">
                          {isBlocked ? (
                            <span className="yoy-diff-blocked" title={metric.reason || '비교 불가'}>
                              {metric.reason ? `비교 불가 (${metric.reason})` : '비교 불가'}
                            </span>
                          ) : (
                            <>
                              <span className={`yoy-diff-amt ${dirClass}`}>
                                {metric.diffAmountText}
                              </span>
                              <span className={`yoy-diff-rate ${dirClass}`}>
                                ({metric.diffRateText})
                              </span>
                            </>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}

              <div className="yoy-caption">
                <span>* 2025년은 최신 완결 후보이며 공정위 공식 행정 마감 여부는 미확인 상태입니다.</span>
                <span>* 2026년 진행형 스냅샷은 본 전년비 비교에서 전수 제외되었으며 전년과 직접 비교가 불가합니다.</span>
                <span>* 공정위 {regionCtx.region_name} 등록 가맹본부 통계이며, 특정 브랜드 및 개별 가맹점의 실제 실적·수익률이 아닙니다.</span>
              </div>
            </section>
          )}

          {/* 3. 창업비용 4대 항목 가로 분할 바 (Stacked Breakdown Bar) */}
          <section className="visual-cost-section" aria-label="창업비용 4대 구성항목">
            <div className="cost-section-top">
              <span className="cost-section-title">{regionCtx.region_name} 창업비용 4대 구성항목 (중앙값)</span>
              <button 
                className="cost-detail-toggle"
                onClick={() => setShowCostDetails(!showCostDetails)}
                aria-expanded={showCostDetails}
              >
                {showCostDetails ? '접기 ▲' : '항목상세 ▼'}
              </button>
            </div>

            {/* 가로 분할 비례 바 (Stacked Progress Bar) */}
            <div className="cost-stacked-bar">
              <div 
                className="cost-segment segment-jng" 
                style={{ width: `${pctJng}%` }} 
                title={`가맹비: ${formatManwonOnly(feeJng)} (${pctJng.toFixed(1)}%)`}
              />
              <div 
                className="cost-segment segment-edu" 
                style={{ width: `${pctEdu}%` }} 
                title={`교육비: ${formatManwonOnly(feeEdu)} (${pctEdu.toFixed(1)}%)`}
              />
              <div 
                className="cost-segment segment-grnte" 
                style={{ width: `${pctGrnte}%` }} 
                title={`보증금: ${formatManwonOnly(feeGrnte)} (${pctGrnte.toFixed(1)}%)`}
              />
              <div 
                className="cost-segment segment-intrr" 
                style={{ width: `${pctIntrr}%` }} 
                title={`인테리어: ${formatManwonOnly(feeIntrr)} (${pctIntrr.toFixed(1)}%)`}
              />
            </div>

            {/* 4대 구성항목 칩 그리드 */}
            <div className="cost-chips-grid">
              <div className="cost-chip-item">
                <span className="dot dot-jng" />
                <span className="chip-name">가맹비</span>
                <span className="chip-val">{formatManwonOnly(feeJng)}</span>
              </div>
              <div className="cost-chip-item">
                <span className="dot dot-edu" />
                <span className="chip-name">교육비</span>
                <span className="chip-val">{formatManwonOnly(feeEdu)}</span>
              </div>
              <div className="cost-chip-item">
                <span className="dot dot-grnte" />
                <span className="chip-name">보증금</span>
                <span className="chip-val">{formatManwonOnly(feeGrnte)}</span>
              </div>
              <div className="cost-chip-item highlight">
                <span className="dot dot-intrr" />
                <span className="chip-name">인테리어</span>
                <span className="chip-val">{formatManwonOnly(feeIntrr)}</span>
              </div>
            </div>

            {/* 잠정 파생 합계 안내 (공식 총창업비용 단정 금지 원칙 준수) */}
            {costs.tentative_derived_sum && (
              <div className="cost-tentative-tag-box">
                <span className="tentative-badge">{regionCtx.region_name} 파생 합산</span>
                <span className="tentative-text">
                  항목 합산 잠정 창업비용: <strong>중위 {formatCurrency(costs.tentative_derived_sum.median_thousand_krw)}</strong>
                  {regionCtx.is_regional && regionCtx.cost_vs_national_pct != null && (
                    <span style={{ marginLeft: '6px', fontSize: '0.72rem', fontWeight: 700, color: '#64748b' }}>
                      (전국 대비 {regionCtx.cost_vs_national_pct >= 0 ? `+${regionCtx.cost_vs_national_pct}%` : `${regionCtx.cost_vs_national_pct}%`})
                    </span>
                  )}
                </span>
              </div>
            )}

            {/* 상세 아코디언 */}
            {showCostDetails && (
              <div className="cost-details-panel">
                <div className="detail-row">
                  <span className="detail-key">인테리어 평당(3.3㎡)</span>
                  <span className="detail-val">{formatManwonOnly(costs.interior_cost_per_pyeong_3_3sqm?.median_thousand_krw)}</span>
                </div>
                <div className="detail-row">
                  <span className="detail-key">예치금 (depstAmt 원본)</span>
                  <span className="detail-val">{formatManwonOnly(costs.reported_deposit_amount?.median_thousand_krw)}</span>
                </div>
                <div className="detail-disclaimer">
                  ※ 잠정 합계는 공정위 공인 총창업비용이 아니며, 공시 원본 4개 항목을 단순 합산한 참고 지표입니다.
                </div>
              </div>
            )}
          </section>

          {/* 4. 점포 규모 및 표본 현황 스트립 */}
          <div className="sample-status-strip">
            <div className="strip-col">
              <span className="strip-title">{regionCtx.region_name} 본부 가맹점망</span>
              <span className="strip-num">
                가맹 <strong>{sample.total_franchise_stores?.toLocaleString()}</strong>개 · 직영 {sample.total_direct_stores?.toLocaleString()}개
              </span>
            </div>
            <div className="strip-col">
              <span className="strip-title">{regionCtx.region_name} 공시 표본 수</span>
              <span className="strip-num">
                총 <strong>{sample.total_brand_records?.toLocaleString()}개</strong> 브랜드 (매출 0원: {sample.sales_zero_records?.toLocaleString()}개)
              </span>
            </div>
          </div>

          {/* 푸터 메타 */}
          <div className="panel-footer-meta">
            <span>출처: 공정거래위원회 가맹사업정보제공시스템 (가맹본부 정기공시 정보공개서)</span>
            <span>집계단위: {regionCtx.region_name} 등록 가맹본부 기준 통계 (개별 매장 실측치 아님)</span>
          </div>
        </div>
      )}
    </aside>
  );
}
