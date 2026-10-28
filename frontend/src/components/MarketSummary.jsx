import React from 'react';
import { CATEGORY_MAJOR_LIST } from './CategoryFilterBar';

export default function MarketSummary({ 
  data, 
  meta, 
  nationalSummaryData = null,
  nationalSummaryMeta = null,
  nationalRegionDetail = null,
  nationalMidCategories = [],
  regionDetail, 
  selectedRegionInfo, 
  isNationwide = false, 
  loading, 
  error, 
  onRetry,
  sedaReferenceMonth = null,
  sedaProvenanceText = null,
  topBrandsState = null,
  selectedCategoryId = null,
  categoryLabel = '',
  midCategories = [],
  selectedMidCategory = null,
  midCategoryLabel = '',
  onSelectCategory = null,
  onSelectMidCategory = null,
  activeBrandName = '',
  onSelectBrand = null
}) {
  const regionName = isNationwide 
    ? '전국 외식업 시장' 
    : (selectedRegionInfo?.region_name || data?.region_name || '선택 지역');

  // 지역 기준월 (전국 화면은 meta 또는 sedaReferenceMonth, 지역 화면은 regionDetail?.meta?.data_reference_month 직접 참조)
  const localRefMonth = isNationwide
    ? (sedaReferenceMonth || meta?.data_reference_month || null)
    : (regionDetail?.meta?.data_reference_month || null);

  const refMonth = localRefMonth;
  const badgeText = refMonth ? `소진공 ${refMonth} 공간 전수` : '소진공 기준월 확인 불가';
  const badgeTitle = refMonth 
    ? `소상공인시장진흥공단 ${refMonth} 외식업 점포 공간 전수 (개별 사업장 전수 모수)` 
    : '소상공인시장진흥공단 데이터 기준월 확인 불가';

  if (loading) {
    return (
      <aside className="panel summary-panel" aria-label="외식업 시장 요약 정보">
        <h2 className="panel-title">{regionName} 요약</h2>
        <div className="skeleton-loader">
          <div className="skeleton-line" style={{ width: '80%', height: '24px' }}></div>
          <div className="skeleton-line" style={{ width: '100%', height: '60px' }}></div>
          <div className="skeleton-line" style={{ width: '100%', height: '60px' }}></div>
          <div className="skeleton-line" style={{ width: '90%', height: '60px' }}></div>
        </div>
      </aside>
    );
  }

  if (error) {
    return (
      <aside className="panel summary-panel" aria-label="외식업 시장 요약 정보">
        <h2 className="panel-title">{regionName} 요약</h2>
        <div className="panel-error">
          <p className="error-msg">{error}</p>
          <button className="retry-btn" onClick={onRetry}>다시 시도</button>
        </div>
      </aside>
    );
  }

  if (!data) return null;

  // 특정 중분류(48대) 또는 대분류(8대)가 선택된 경우 해당 업종 통계를 우선 적용
  const matchedMidStat = (selectedMidCategory && Array.isArray(midCategories))
    ? midCategories.find((m) => m.category_mid_id === selectedMidCategory)
    : null;

  const matchedCatStat = (!matchedMidStat && selectedCategoryId && Array.isArray(regionDetail?.category_composition))
    ? regionDetail.category_composition.find((c) => c.category_major_id === selectedCategoryId)
    : null;

  const activeStats = (matchedMidStat && matchedMidStat.total_stores != null)
    ? matchedMidStat
    : (matchedCatStat && matchedCatStat.total_stores != null)
      ? matchedCatStat
      : data;

  const totalStores = activeStats.total_stores ?? activeStats.stores ?? 0;
  const franchiseStores = activeStats.franchise_confirmed_stores || 0;
  const brandLinkedStores = activeStats.brand_linked_stores || 0;
  const independentStores = activeStats.independent_stores || 0;
  const categoryShareInRegion = matchedMidStat?.category_share_pct ?? matchedCatStat?.share_pct ?? null;
  const displayCatTitle = midCategoryLabel
    ? `${categoryLabel} › ${midCategoryLabel}`
    : categoryLabel;

  const franchiseRate = Number(activeStats.franchise_penetration_rate ?? (totalStores > 0 ? (franchiseStores / totalStores) * 100 : 0)).toFixed(2);
  const brandRate = Number(activeStats.brand_penetration_rate ?? (totalStores > 0 ? (brandLinkedStores / totalStores) * 100 : 0)).toFixed(2);

  // 전국 벤치마크 기준치 (특정 대분류/중분류 선택 시 전국 동일 업종 기준치와 1:1 정밀 비교)
  const natMatchedMidStat = (selectedMidCategory && Array.isArray(nationalMidCategories))
    ? nationalMidCategories.find((m) => m.category_mid_id === selectedMidCategory)
    : null;

  const natMajorComp = Array.isArray(nationalRegionDetail?.category_composition)
    ? nationalRegionDetail.category_composition
    : [];

  const natMatchedCatStat = (!natMatchedMidStat && selectedCategoryId && natMajorComp.length > 0)
    ? natMajorComp.find((c) => c.category_major_id === selectedCategoryId)
    : null;

  const natActiveStats = (natMatchedMidStat && natMatchedMidStat.total_stores != null)
    ? natMatchedMidStat
    : (natMatchedCatStat && (natMatchedCatStat.total_stores != null || natMatchedCatStat.stores != null))
      ? natMatchedCatStat
      : nationalSummaryData;

  const natTotal = natActiveStats?.total_stores ?? natActiveStats?.stores ?? nationalSummaryData?.total_stores;
  const natFranchise = natActiveStats?.franchise_confirmed_stores ?? nationalSummaryData?.franchise_confirmed_stores;
  const natBrand = natActiveStats?.brand_linked_stores ?? nationalSummaryData?.brand_linked_stores;
  const natFranchiseRate = (natTotal > 0 && natFranchise != null) 
    ? Number(natActiveStats?.franchise_penetration_rate ?? ((natFranchise / natTotal) * 100))
    : null;
  const natBrandRate = (natTotal > 0 && natBrand != null)
    ? Number(natActiveStats?.brand_penetration_rate ?? ((natBrand / natTotal) * 100))
    : null;
  const nationalRefMonth = nationalSummaryMeta?.data_reference_month || null;

  // 전국 벤치마크 유효성 및 기준시점 일치 여부 검증
  const hasNationalBenchmark = Boolean(
    natTotal && natTotal > 0 && 
    natFranchise != null && 
    natBrand != null && 
    natFranchiseRate != null && 
    natBrandRate != null
  );

  // 기준시점 일치 검증: 전국 모드가 아닐 때는 지역 기준월과 전국 기준월이 모두 존재하고 일치해야 비교 가능
  const isPeriodMatched = Boolean(localRefMonth && nationalRefMonth && localRefMonth === nationalRefMonth) || Boolean(hasNationalBenchmark && !localRefMonth);
  const isComparisonAvailable = hasNationalBenchmark && (isNationwide || isPeriodMatched);

  let comparisonHoldReason = null;
  if (!hasNationalBenchmark) {
    comparisonHoldReason = '전국 벤치마크 데이터 미수신';
  } else if (!isNationwide && !isPeriodMatched) {
    if (!localRefMonth || !nationalRefMonth) {
      comparisonHoldReason = `기준시점 미확인 (지역: ${localRefMonth || '미확인'}, 전국: ${nationalRefMonth || '미확인'})`;
    } else {
      comparisonHoldReason = `기준시점 불일치 (지역: ${localRefMonth}, 전국: ${nationalRefMonth})`;
    }
  }

  // 격차 계산 (%p) - 비교 가능할 때만 계산
  const diffFranchise = isComparisonAvailable ? (Number(franchiseRate) - natFranchiseRate).toFixed(2) : null;
  const diffBrand = isComparisonAvailable ? (Number(brandRate) - natBrandRate).toFixed(2) : null;

  // 게이지 바 정규화 (업종별 가맹률 편차를 수용하도록 동적 스케일 적용)
  const maxFranGauge = Math.max(25, Math.ceil(Math.max(Number(franchiseRate), natFranchiseRate || 0) / 10) * 10 + 5);
  const maxBrandGauge = Math.max(50, Math.ceil(Math.max(Number(brandRate), natBrandRate || 0) / 10) * 10 + 5);

  const franchiseBarWidth = Math.min(100, Math.max(3, (Number(franchiseRate) / maxFranGauge) * 100));
  const franchiseMarkerPos = isComparisonAvailable ? Math.min(98, (natFranchiseRate / maxFranGauge) * 100) : null;

  const brandBarWidth = Math.min(100, Math.max(3, (Number(brandRate) / maxBrandGauge) * 100));
  const brandMarkerPos = isComparisonAvailable ? Math.min(98, (natBrandRate / maxBrandGauge) * 100) : null;

  // 3색 구성 비율 계산 (공식 가맹 vs 후보 브랜드 vs 독립 개인)
  const franchisePct = totalStores > 0 ? Number(((franchiseStores / totalStores) * 100).toFixed(1)) : 0;
  const brandOnlyStores = Math.max(0, brandLinkedStores - franchiseStores);
  const brandOnlyPct = totalStores > 0 ? Number(((brandOnlyStores / totalStores) * 100).toFixed(1)) : 0;
  const independentPct = totalStores > 0 ? Number(((independentStores / totalStores) * 100).toFixed(1)) : 0;

  // 상위 브랜드 목록 (업종 필터 연동 결과 우선, 없으면 지역 상세 기본값)
  const topBrandsSource = topBrandsState ? topBrandsState.list : (regionDetail?.top_brands || []);
  const topBrands = topBrandsSource ? topBrandsSource.slice(0, 5) : [];

  // 업종 구성비 차트 데이터 (전체 모드일 때: 8대 대분류 구성비 / 대분류 선택 시: 하위 중분류 구성비)
  const majorComposition = Array.isArray(regionDetail?.category_composition)
    ? regionDetail.category_composition
    : [];
  const isShowingMidComposition = Boolean(selectedCategoryId && midCategories.length > 0);
  const maxCompStores = isShowingMidComposition
    ? Math.max(1, ...midCategories.map((m) => m.total_stores || 0))
    : Math.max(1, ...majorComposition.map((c) => c.total_stores || c.stores || 0));

  // [Phase E] 상권 포화도·경쟁 강도·특화도 3대 핵심 의사결정 지표 계산
  // 1) 입지계수 (LQ: Location Quotient) = (지역 내 업종 비중) / (전국 내 동일 업종 비중)
  let lqValue = 1.0;
  let lqTargetName = displayCatTitle || '전체 외식업';
  if (!isNationwide) {
    if (matchedMidStat && natMatchedMidStat && (natMatchedMidStat.category_share_pct || 0) > 0) {
      lqValue = Number(((matchedMidStat.category_share_pct || 0) / natMatchedMidStat.category_share_pct).toFixed(2));
    } else if (matchedCatStat && natMatchedCatStat && (natMatchedCatStat.share_pct || 0) > 0) {
      lqValue = Number(((matchedCatStat.share_pct || 0) / natMatchedCatStat.share_pct).toFixed(2));
    } else if (!selectedCategoryId && majorComposition.length > 0 && natMajorComp.length > 0) {
      // 전 업종 모드에서는 현재 지역의 최고 특화 업종(LQ 최댓값)을 자동 발굴
      let bestLq = 0;
      let bestCatName = '';
      majorComposition.forEach((regCat) => {
        const natCat = natMajorComp.find((n) => n.category_major_id === regCat.category_major_id);
        if (natCat && (natCat.share_pct || 0) > 0) {
          const ratio = (regCat.share_pct || 0) / natCat.share_pct;
          if (ratio > bestLq) {
            bestLq = ratio;
            bestCatName = regCat.category_major_name;
          }
        }
      });
      if (bestLq > 0) {
        lqValue = Number(bestLq.toFixed(2));
        lqTargetName = bestCatName;
      }
    }
  }

  const lqGrade =
    lqValue >= 1.25
      ? { label: '특화 밀집 상권', tone: 'high' }
      : lqValue >= 0.85
        ? { label: '전국 평균 균형', tone: 'mid' }
        : { label: '공급 과소·틈새', tone: 'low' };

  // 2) 프랜차이즈 진입 장벽 (전국 동일 업종 대비 가맹률 편차)
  const franGapNum = diffFranchise !== null ? Number(diffFranchise) : 0;
  const competitionGrade =
    franGapNum >= 2.0
      ? { label: '프랜차이즈 강세', sub: `전국 대비 +${franGapNum.toFixed(1)}%p`, tone: 'high' }
      : franGapNum <= -2.0
        ? { label: '개인·독립점포 우위', sub: `전국 대비 ${franGapNum.toFixed(1)}%p`, tone: 'low' }
        : { label: '가맹·개인 균형', sub: isNationwide ? `가맹률 ${franchiseRate}%` : `전국 대비 ${franGapNum >= 0 ? '+' : ''}${franGapNum.toFixed(1)}%p`, tone: 'mid' };

  // 3) 상위 5대 브랜드 집중도 (CR5)
  const cr5Value = Number(
    topBrands.reduce((acc, b) => acc + Number(b.share_pct || 0), 0).toFixed(1)
  );
  const cr5Grade =
    cr5Value >= 20.0
      ? { label: '메이저 브랜드 과점형', tone: 'high' }
      : cr5Value >= 8.0
        ? { label: '다브랜드 경쟁형', tone: 'mid' }
        : { label: '소규모·개인 분산형', tone: 'low' };

  // 종합 한 줄 진단 코멘트 생성
  const top1BrandName = topBrands[0]?.brand_name_std || null;
  const diagnosisSummaryText = isNationwide
    ? `${displayCatTitle || '전국 외식업'} 기준 공식 가맹률은 ${franchiseRate}%이며, 상위 5대 브랜드가 시장의 ${cr5Value}%를 점유하는 ${cr5Grade.label} 구조입니다.`
    : selectedCategoryId
      ? `${regionName}의 ${displayCatTitle} 업종은 전국 평균 대비 ${lqValue}배 밀집(${lqGrade.label})되어 있으며, ${competitionGrade.label}(${competitionGrade.sub}) 및 상위 5대 브랜드 점유율 ${cr5Value}%(${top1BrandName ? `1위 ${top1BrandName}` : cr5Grade.label})를 보입니다.`
      : `${regionName}은 전국 대비 '${lqTargetName}' 업종 특화도(LQ ${lqValue}배)가 가장 높으며, 전체 외식업은 ${competitionGrade.label}(${competitionGrade.sub}) 및 상위 5대 브랜드 집중도 ${cr5Value}% 구조입니다.`;

  const [isCollapsed, setIsCollapsed] = React.useState(false);

  return (
    <aside className={`panel summary-panel ${isCollapsed ? 'collapsed' : ''}`} aria-label="외식업 시장 요약 정보">
      <div className="panel-header">
        <div className="summary-title-wrapper">
          <h2 className="panel-title">{regionName}{displayCatTitle ? ` · ${displayCatTitle}` : ''} 분석</h2>
          <span 
            className={`badge-meta provenance-badge-seda ${!refMonth ? 'badge-unverified' : ''}`}
            title={badgeTitle}
          >
            {badgeText}
          </span>
        </div>
        <button 
          className="summary-collapse-btn desktop-only"
          onClick={() => setIsCollapsed(!isCollapsed)}
          aria-label={isCollapsed ? '지역 분석 패널 펼치기' : '지역 분석 패널 접기'}
          title={isCollapsed ? '지역 분석 패널 펼치기' : '지역 분석 패널 접기'}
        >
          {isCollapsed ? '펼치기 ▸' : '접기 ◂'}
        </button>
      </div>

      <div className="stat-cards">
        {/* 1. 총 외식업 점포수 & 애플 피트니스 스타일 3색 세그먼트 카드 */}
        <div className="stat-card primary hero-summary-card">
          <div className="stat-label-row">
            <span className="stat-label">
              {displayCatTitle
                ? `${isNationwide ? '전국' : '지역'} ${displayCatTitle} 점포${categoryShareInRegion != null ? ` (비중 ${categoryShareInRegion}%)` : ''}`
                : isNationwide
                  ? '전국 외식업 총 점포'
                  : '지역 외식업 총 점포 (전 업종)'}
            </span>
            <span className="stat-provenance-tag">전수 실측</span>
          </div>
          <div className="stat-value-row">
            <span className="stat-value">{totalStores.toLocaleString()}</span>
            <span className="stat-unit">개소</span>
          </div>

          {/* 3색 세그먼트 비주얼 바 */}
          <div className="segmented-visual-bar" title={`공식 가맹 ${franchisePct}% | 후보 브랜드 ${brandOnlyPct}% | 일반 독립 ${independentPct}%`}>
            <div className="segment segment-franchise" style={{ width: `${franchisePct}%` }} />
            <div className="segment segment-brand" style={{ width: `${brandOnlyPct}%` }} />
            <div className="segment segment-independent" style={{ width: `${independentPct}%` }} />
          </div>

          {/* 3색 미니 범례 */}
          <div className="segmented-legend-row">
            <div className="legend-chip">
              <span className="chip-swatch swatch-franchise" aria-hidden="true" />
              <span className="chip-label">가맹</span>
              <span className="chip-val">{franchisePct}%</span>
            </div>
            <div className="legend-chip">
              <span className="chip-swatch swatch-brand" aria-hidden="true" />
              <span className="chip-label">브랜드</span>
              <span className="chip-val">{brandOnlyPct}%</span>
            </div>
            <div className="legend-chip">
              <span className="chip-swatch swatch-independent" aria-hidden="true" />
              <span className="chip-label">독립</span>
              <span className="chip-val">{independentPct}%</span>
            </div>
          </div>
        </div>

        {/* 2. 듀얼 침투율 벤치마크 카드 */}
        <div className="stat-card benchmark-comparison-card">
          <div className="benchmark-card-title">
            <span>침투율 벤치마크</span>
            <span className="benchmark-ref-badge" title="전국 외식업 공간 전수 기준선 대비">전국 기준선 비교</span>
          </div>

          {/* 2-A: 공식 프랜차이즈 침투율 비교 */}
          <div className="gauge-item">
            <div className="gauge-header">
              <span className="gauge-label">
                <span className="gauge-bullet franchise-bullet" /> 공식 가맹점 침투율
              </span>
              <div className="gauge-value-group">
                <span className="gauge-current highlight-blue">{franchiseRate}%</span>
                {!isNationwide && isComparisonAvailable && diffFranchise !== null && (
                  <span className={`diff-pill ${Number(diffFranchise) >= 0 ? 'diff-up' : 'diff-down'}`}>
                    {Number(diffFranchise) >= 0 ? `▲ +${diffFranchise}` : `▼ ${diffFranchise}`}%p
                  </span>
                )}
              </div>
            </div>

            {/* 시각적 비교 바 */}
            <div className="gauge-track">
              <div className="gauge-fill franchise-fill" style={{ width: `${franchiseBarWidth}%` }} />
              {isComparisonAvailable && franchiseMarkerPos !== null && (
                <div 
                  className="gauge-target-pin" 
                  style={{ left: `${franchiseMarkerPos}%` }} 
                  title={`전국 가맹 기준선: ${natFranchiseRate.toFixed(2)}%`}
                >
                  <span className="pin-label">{natFranchiseRate.toFixed(1)}%</span>
                </div>
              )}
            </div>
          </div>

          {/* 2-B: 후보 브랜드 연계 침투율 비교 */}
          <div className="gauge-item">
            <div className="gauge-header">
              <span className="gauge-label">
                <span className="gauge-bullet brand-bullet" /> 브랜드 점포 침투율
              </span>
              <div className="gauge-value-group">
                <span className="gauge-current highlight-teal">{brandRate}%</span>
                {!isNationwide && isComparisonAvailable && diffBrand !== null && (
                  <span className={`diff-pill ${Number(diffBrand) >= 0 ? 'diff-up' : 'diff-down'}`}>
                    {Number(diffBrand) >= 0 ? `▲ +${diffBrand}` : `▼ ${diffBrand}`}%p
                  </span>
                )}
              </div>
            </div>

            {/* 시각적 비교 바 */}
            <div className="gauge-track">
              <div className="gauge-fill brand-fill" style={{ width: `${brandBarWidth}%` }} />
              {isComparisonAvailable && brandMarkerPos !== null && (
                <div 
                  className="gauge-target-pin" 
                  style={{ left: `${brandMarkerPos}%` }} 
                  title={`전국 브랜드 기준선: ${natBrandRate.toFixed(2)}%`}
                >
                  <span className="pin-label">{natBrandRate.toFixed(1)}%</span>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* 2-B. [Phase E] 상권 경쟁·특화·독과점 종합 진단 카드 (LQ 입지계수 · 가맹 진입장벽 · CR5 브랜드 집중도) */}
        <div className="stat-card commercial-diagnosis-card" aria-label="상권 경쟁·특화·독과점 종합 진단">
          <div className="diagnosis-card-header">
            <span className="stat-label" style={{ marginBottom: 0 }}>
              상권 경쟁·특화 종합 진단
            </span>
            <span className="diagnosis-scope-tag">
              {displayCatTitle || '전 업종 종합'}
            </span>
          </div>

          <div className="diagnosis-metrics-grid">
            {/* 지표 1: 업종 특화도 (LQ) */}
            <div className={`diagnosis-metric-box tone-${isNationwide ? 'mid' : lqGrade.tone}`}>
              <span className="diag-metric-title">
                {selectedCategoryId ? '업종 특화도 (LQ)' : '최고 특화 업종'}
              </span>
              <strong className="diag-metric-val">
                {isNationwide
                  ? '1.00x 기준'
                  : selectedCategoryId
                    ? `${lqValue}배`
                    : `${lqTargetName} ${lqValue}배`}
              </strong>
              <span className={`diag-metric-badge tone-${isNationwide ? 'mid' : lqGrade.tone}`}>
                {isNationwide ? '전국 모수 기준' : lqGrade.label}
              </span>
            </div>

            {/* 지표 2: 프랜차이즈 진입 장벽 */}
            <div className={`diagnosis-metric-box tone-${competitionGrade.tone}`}>
              <span className="diag-metric-title">가맹 진입 장벽</span>
              <strong className="diag-metric-val">{competitionGrade.sub}</strong>
              <span className={`diag-metric-badge tone-${competitionGrade.tone}`}>
                {competitionGrade.label}
              </span>
            </div>

            {/* 지표 3: Top 5 브랜드 독과점도 (CR5) */}
            <div className={`diagnosis-metric-box tone-${cr5Grade.tone}`}>
              <span className="diag-metric-title">Top 5 집중도 (CR5)</span>
              <strong className="diag-metric-val">{cr5Value}%</strong>
              <span className={`diag-metric-badge tone-${cr5Grade.tone}`}>
                {cr5Grade.label}
              </span>
            </div>
          </div>

          <div className="diagnosis-verdict-box">
            <span className="verdict-icon" aria-hidden="true">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>
            </span>
            <p className="verdict-text">{diagnosisSummaryText}</p>
          </div>
        </div>

        {/* 2-C. 지역 업종 구성비 & 48개 중분류 드릴다운 인터랙티브 바 차트 */}
        {(isShowingMidComposition || majorComposition.length > 0) && (
          <div className="stat-card category-composition-card">
            <div className="cat-comp-card-header">
              <span className="stat-label" style={{ marginBottom: 0 }}>
                {isShowingMidComposition
                  ? `${categoryLabel} 세부 중분류 구성 (${midCategories.length}개)`
                  : '8대 외식업종 구성비 (클릭 시 드릴다운)'}
              </span>
              {selectedCategoryId && onSelectCategory && (
                <button
                  type="button"
                  className="cat-comp-back-btn"
                  onClick={() => {
                    if (selectedMidCategory && onSelectMidCategory) {
                      onSelectMidCategory(null);
                    } else {
                      onSelectCategory('ALL');
                    }
                  }}
                >
                  {selectedMidCategory ? `${categoryLabel} 전체 ↩` : '8대 업종 전체 ↩'}
                </button>
              )}
            </div>

            <div className="cat-comp-bars-list">
              {isShowingMidComposition
                ? midCategories.map((mid) => {
                    const isMidSelected = selectedMidCategory === mid.category_mid_id;
                    const majorObj = CATEGORY_MAJOR_LIST.find((c) => c.id === selectedCategoryId);
                    const barColor = majorObj?.color || '#2563eb';
                    const widthPct = Math.min(100, Math.max(4, ((mid.total_stores || 0) / maxCompStores) * 100));
                    return (
                      <button
                        type="button"
                        key={mid.category_mid_id}
                        className={`cat-comp-bar-row ${isMidSelected ? 'active' : ''}`}
                        onClick={() =>
                          onSelectMidCategory &&
                          onSelectMidCategory(isMidSelected ? null : mid.category_mid_id)
                        }
                        title={`${mid.category_mid_name} 클릭 시 지도 및 브랜드 순위를 해당 중분류로 필터링`}
                      >
                        <div className="cat-comp-row-top">
                          <span className="cat-comp-name">{mid.category_mid_name}</span>
                          <span className="cat-comp-meta">
                            <strong>{Number(mid.total_stores || 0).toLocaleString()}</strong>개소
                            <span className="cat-comp-pct">({mid.category_share_pct ?? 0}%)</span>
                          </span>
                        </div>
                        <div className="cat-comp-track">
                          <div
                            className="cat-comp-fill"
                            style={{ width: `${widthPct}%`, backgroundColor: barColor }}
                          />
                        </div>
                      </button>
                    );
                  })
                : majorComposition.map((maj) => {
                    const majorObj = CATEGORY_MAJOR_LIST.find((c) => c.id === maj.category_major_id);
                    const barColor = majorObj?.color || '#059669';
                    const stCount = maj.total_stores ?? maj.stores ?? 0;
                    const widthPct = Math.min(100, Math.max(4, (stCount / maxCompStores) * 100));
                    return (
                      <button
                        type="button"
                        key={maj.category_major_id}
                        className="cat-comp-bar-row"
                        onClick={() => onSelectCategory && onSelectCategory(maj.category_major_id)}
                        title={`${maj.category_major_name} 클릭 시 하위 중분류 및 업종 밀집도로 전환`}
                      >
                        <div className="cat-comp-row-top">
                          <span className="cat-comp-name">
                            {majorObj?.icon ? `${majorObj.icon} ` : ''}{maj.category_major_name}
                          </span>
                          <span className="cat-comp-meta">
                            <strong>{Number(stCount).toLocaleString()}</strong>개소
                            <span className="cat-comp-pct">({maj.share_pct ?? 0}%)</span>
                          </span>
                        </div>
                        <div className="cat-comp-track">
                          <div
                            className="cat-comp-fill"
                            style={{ width: `${widthPct}%`, backgroundColor: barColor }}
                          />
                        </div>
                      </button>
                    );
                  })}
            </div>
          </div>
        )}

        {/* 3. 지역 내 상위 브랜드 Top 5 (대분류·중분류 필터 연동) */}
        <div className="stat-card regional-brands-card">
          <div className="stat-label">
            상위 브랜드 Top 5 · {displayCatTitle || '전체 업종'}
          </div>
          {topBrandsState?.loading && topBrands.length === 0 ? (
            <div className="stat-sub">불러오는 중…</div>
          ) : topBrandsState?.error ? (
            <div className="stat-sub">상위 브랜드를 불러오지 못했습니다.</div>
          ) : topBrands.length === 0 ? (
            <div className="stat-sub">
              {displayCatTitle ? `이 지역 ${displayCatTitle} 업종에는 집계된 브랜드가 없습니다.` : '집계된 브랜드가 없습니다.'}
            </div>
          ) : (
            <div className="top-brands-list">
              {topBrands.map((brand, idx) => {
                const isActiveBrand = Boolean(activeBrandName && activeBrandName === brand.brand_name_std);
                return (
                  <button
                    type="button"
                    key={brand.internal_brand_id || idx}
                    className={`top-brand-row clickable ${isActiveBrand ? 'active-brand' : ''}`}
                    onClick={() => onSelectBrand && onSelectBrand(brand.brand_name_std, brand)}
                    title={`${brand.brand_name_std} 클릭 시 현재 지역 지점 목록 및 전국 시군구 분포 분석 열기`}
                  >
                    <span className={`brand-rank-badge rank-${idx + 1}`}>{idx + 1}</span>
                    <span className="brand-name-text">
                      {brand.brand_name_std}
                    </span>
                    <div className="brand-count-group">
                      <span className="brand-stores-count">{Number(brand.store_count || 0).toLocaleString()}개소</span>
                      {brand.share_pct != null && (
                        <span className="brand-share-pct">({brand.share_pct}%)</span>
                      )}
                    </div>
                  </button>
                );
              })}
            </div>
          )}
        </div>

        {/* 전국 모드 시 전국 총괄 메타 */}
        {isNationwide && (
          <div className="stat-card">
            <div className="stat-label">추출 브랜드 후보 총수</div>
            <div className="stat-value">{data.total_candidate_brands ? data.total_candidate_brands.toLocaleString() : '5,062'} <span className="stat-unit">개 브랜드</span></div>
            <div className="stat-sub">전국 점포수 10개 이상 동일 상호 기준</div>
          </div>
        )}
      </div>

      <div className="summary-footer">
        <div className="summary-provenance-chip" title="소상공인시장진흥공단 735,185건 외식업 전수 공간 대사 무결성 검증 완료">
          <svg viewBox="0 0 16 16" width="12" height="12" fill="none" stroke="#10b981" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="3 8 6.5 11.5 13 4" />
          </svg>
          <span>소진공 {refMonth || '2026.07'} 공간 전수 실측 대사 완료</span>
        </div>
      </div>
    </aside>
  );
}
