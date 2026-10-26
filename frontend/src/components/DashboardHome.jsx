import React, { useState, useEffect, useRef, useMemo } from 'react';
import './DashboardHome.css';
import { CATEGORY_MAJOR_LIST } from './CategoryFilterBar';
import { searchBrands } from '../services/api';

const DONUT_PALETTE = {
  CAT_MAJ_01: '#10b981', // 한식 - Emerald
  CAT_MAJ_07: '#3b82f6', // 카페·음료 - Blue
  CAT_MAJ_05: '#8b5cf6', // 치킨·패스트푸드 - Purple
  CAT_MAJ_06: '#f59e0b', // 분식·간편식 - Amber
  CAT_MAJ_03: '#ec4899', // 일식 - Pink
  CAT_MAJ_02: '#ef4444', // 중식 - Red
  CAT_MAJ_04: '#06b6d4', // 양식·세계음식 - Cyan
  CAT_MAJ_08: '#14b8a6', // 베이커리·디저트 - Teal
  CAT_MAJ_99: '#94a3b8'  // 기타 - Slate
};

function formatKrwCompact(thousandKrw) {
  if (thousandKrw == null || isNaN(thousandKrw) || thousandKrw <= 0) return '-';
  const manwon = Math.round(thousandKrw / 10);
  // 1조원 이상 (100,000,000만원 = 10,000억원)
  if (manwon >= 100000000) {
    const jo = (manwon / 100000000).toFixed(1);
    return `${parseFloat(jo).toLocaleString('ko-KR')}조원`;
  }
  // 1,000억원 이상
  if (manwon >= 10000000) {
    const eok = Math.round(manwon / 10000);
    return `${eok.toLocaleString('ko-KR')}억원`;
  }
  // 1억원 이상
  if (manwon >= 10000) {
    const eok = (manwon / 10000).toFixed(1);
    return `${parseFloat(eok).toLocaleString('ko-KR')}억원`;
  }
  // 1억원 미만 (만원 단위)
  return `${manwon.toLocaleString('ko-KR')}만원`;
}

function formatManwon(thousandKrw) {
  if (thousandKrw == null || isNaN(thousandKrw) || thousandKrw <= 0) return '-';
  const manwon = Math.round(thousandKrw / 10);
  if (manwon >= 100000000) {
    const jo = Math.floor(manwon / 100000000);
    const remEok = Math.round((manwon % 100000000) / 10000);
    return remEok > 0 ? `${jo}조 ${remEok.toLocaleString('ko-KR')}억원` : `${jo}조원`;
  }
  if (manwon >= 10000) {
    const eok = Math.floor(manwon / 10000);
    const remMan = Math.round(manwon % 10000);
    return remMan > 0 ? `${eok}억 ${remMan.toLocaleString('ko-KR')}만원` : `${eok}억원`;
  }
  return `${manwon.toLocaleString('ko-KR')}만원`;
}

function formatStoreCountCompact(count) {
  if (count == null || isNaN(count)) return '0개';
  if (count >= 10000) {
    const man = (count / 10000).toFixed(1);
    return `${parseFloat(man).toLocaleString('ko-KR')}만개`;
  }
  return `${count.toLocaleString('ko-KR')}개`;
}

export default function DashboardHome({
  summaryData,
  summaryMeta,
  nationalRegionDetail,
  regionDetail,
  selectedRegionInfo,
  isNationwide,
  sidoList = [],
  sigunguList = [],
  selectedSido,
  selectedSigungu,
  onSelectSido,
  onSelectSigungu,
  regionsLoading,
  selectedCategory,
  onSelectCategory,
  midCategories = [],
  selectedMidCategory,
  onSelectMidCategory,
  topBrandsState,
  benchmarkData,
  trendsData,
  ftcLoading,
  selectedYear,
  onSelectYear,
  yearsList = [],
  hotspots = [],
  hotspotsLoading,
  onOpenMap,
  onOpenMapWithHotspot,
  onOpenMapWithBrand,
  onOpenMapWithRegion,
  onOpenIntro,
  onRefresh,
  isRefreshing,
  apiStatus
}) {
  // 좌측 내비게이션 활성 탭
  const [activeNav, setActiveNav] = useState('dashboard');
  // 막대 차트 지표 모드 ('category_total_est' | 'category_monthly_supply' | 'category_sales' | 'category_cost' | 'yearly_trends')
  const [barChartMode, setBarChartMode] = useState('category_total_est');
  // 막대 차트 호버 인덱스
  const [hoveredBarIdx, setHoveredBarIdx] = useState(null);
  // 도넛 차트 호버 업종 ID
  const [hoveredDonutId, setHoveredDonutId] = useState(null);

  // 상단 글로벌 브랜드 검색창 상태
  const [brandQuery, setBrandQuery] = useState('');
  const [brandResults, setBrandResults] = useState([]);
  const [brandSearching, setBrandSearching] = useState(false);
  const [showBrandDropdown, setShowBrandDropdown] = useState(false);
  const [selectedBrandPreview, setSelectedBrandPreview] = useState(null);
  const searchBoxRef = useRef(null);

  // 섹션 스크롤 Refs
  const overviewSectionRef = useRef(null);
  const categorySectionRef = useRef(null);
  const ftcSectionRef = useRef(null);
  const brandSectionRef = useRef(null);
  const hotspotSectionRef = useRef(null);

  // 외부 클릭 시 검색 드롭다운 닫기
  useEffect(() => {
    function handleClickOutside(e) {
      if (searchBoxRef.current && !searchBoxRef.current.contains(e.target)) {
        setShowBrandDropdown(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // 실시간 브랜드 자동완성 검색
  useEffect(() => {
    const q = brandQuery.trim();
    if (!q) {
      setBrandResults([]);
      setBrandSearching(false);
      return;
    }
    const controller = new AbortController();
    setBrandSearching(true);
    const timer = setTimeout(() => {
      const regionCode = selectedSigungu || (selectedSido !== '00' ? selectedSido : '00');
      searchBrands(
        {
          q,
          regionCode,
          categoryMajorId: selectedCategory !== 'ALL' ? selectedCategory : null,
          limit: 10
        },
        controller.signal
      )
        .then((res) => {
          setBrandResults(res.data || []);
        })
        .catch(() => {})
        .finally(() => {
          if (!controller.signal.aborted) setBrandSearching(false);
        });
    }, 180);

    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [brandQuery, selectedSido, selectedSigungu, selectedCategory]);

  // 현재 활성 지역명
  const regionTitle = isNationwide
    ? '대한민국 전국'
    : (selectedRegionInfo?.region_name || '선택 지역');

  // 활성 통계 데이터 추출
  const activeRegionStats = isNationwide
    ? summaryData
    : (regionDetail?.region_stats || summaryData);

  const majorCompositionRaw = useMemo(() => {
    const comp = isNationwide
      ? (nationalRegionDetail?.category_composition || regionDetail?.category_composition || [])
      : (regionDetail?.category_composition || nationalRegionDetail?.category_composition || []);
    return Array.isArray(comp) ? comp : [];
  }, [isNationwide, nationalRegionDetail, regionDetail]);

  const currentCatMeta = useMemo(() => {
    return CATEGORY_MAJOR_LIST.find((c) => c.id === selectedCategory) || CATEGORY_MAJOR_LIST[0];
  }, [selectedCategory]);

  const matchedCatStat = useMemo(() => {
    if (selectedCategory === 'ALL') return null;
    return majorCompositionRaw.find((c) => c.category_major_id === selectedCategory) || null;
  }, [selectedCategory, majorCompositionRaw]);

  const matchedMidStat = useMemo(() => {
    if (!selectedMidCategory || !Array.isArray(midCategories)) return null;
    return midCategories.find((m) => m.category_mid_id === selectedMidCategory) || null;
  }, [selectedMidCategory, midCategories]);

  const displayStats = matchedMidStat || matchedCatStat || activeRegionStats || {};
  const totalStores = displayStats.total_stores ?? displayStats.stores ?? summaryData?.total_stores ?? 735185;
  const franchiseStores = displayStats.franchise_confirmed_stores ?? summaryData?.franchise_confirmed_stores ?? 0;
  const brandLinkedStores = displayStats.brand_linked_stores ?? summaryData?.brand_linked_stores ?? 0;
  const independentStores =
    displayStats.independent_stores ??
    Math.max(0, totalStores - brandLinkedStores);

  const franchiseRate = Number(
    displayStats.franchise_penetration_rate ??
      (totalStores > 0 ? (franchiseStores / totalStores) * 100 : 0)
  ).toFixed(1);

  const brandRate = Number(
    displayStats.brand_penetration_rate ??
      (totalStores > 0 ? (brandLinkedStores / totalStores) * 100 : 0)
  ).toFixed(1);

  const independentRate = Math.max(0, 100 - Number(brandRate)).toFixed(1);
  const candidateOnlyRate = Math.max(0, Number(brandRate) - Number(franchiseRate)).toFixed(1);

  // 8대 업종 도넛 세그먼트 계산
  const donutSegments = useMemo(() => {
    const validList = majorCompositionRaw.filter(
      (item) => item.category_major_id && item.category_major_id !== 'CAT_MAJ_99'
    );
    const sumStores = validList.reduce((acc, cur) => acc + (cur.total_stores || cur.stores || 0), 0) || 1;
    let cumulativePct = 0;

    return validList.map((item) => {
      const count = item.total_stores || item.stores || 0;
      const pct = (count / sumStores) * 100;
      const startPct = cumulativePct;
      cumulativePct += pct;
      const meta = CATEGORY_MAJOR_LIST.find((c) => c.id === item.category_major_id);
      return {
        id: item.category_major_id,
        name: item.category_major_name || meta?.name || item.category_major_id,
        icon: meta?.icon || '🍽️',
        count,
        pct: Number(pct.toFixed(1)),
        rawPct: pct,
        startPct,
        color: DONUT_PALETTE[item.category_major_id] || meta?.color || '#10b981'
      };
    });
  }, [majorCompositionRaw]);

  const totalEightMajorStores = useMemo(() => {
    return donutSegments.reduce((acc, cur) => acc + cur.count, 0);
  }, [donutSegments]);

  // 공정위 재무 벤치마크 추출
  const ftcData = benchmarkData?.data || {};
  const ftcSales = ftcData.sales_benchmarks || {};
  const ftcCosts = ftcData.startup_cost_components || {};
  const ftcCategoryComp = Array.isArray(ftcData.category_comparison) ? ftcData.category_comparison : [];
  const yearlySeries = Array.isArray(trendsData?.data?.yearly_series) ? trendsData.data.yearly_series : [];

  const medianSalesKrw = ftcSales.median_sales_thousand_krw || 0;
  const medianStartupCostKrw = ftcCosts.tentative_derived_sum?.median_thousand_krw || 0;
  const salesPerAreaKrw = ftcSales.median_area_sales_thousand_krw || 0;

  // 8대 업종별 추정 연매출 & 식자재 발주 규모 (구/시도/전국 단위 통계 모델링)
  const estimatedSalesAnalytics = useMemo(() => {
    const salesMap = {};
    ftcCategoryComp.forEach((cat) => {
      salesMap[cat.category_major_id] = cat.median_sales_thousand_krw || 0;
    });

    const DEFAULT_MEDIAN_SALES = {
      CAT_MAJ_01: 361174, // 한식 (약 3.61억원)
      CAT_MAJ_02: 412334, // 중식 (약 4.12억원)
      CAT_MAJ_03: 323361, // 일식 (약 3.23억원)
      CAT_MAJ_04: 326027, // 양식·세계음식 (약 3.26억원)
      CAT_MAJ_05: 193120, // 치킨·패스트푸드 (약 1.93억원)
      CAT_MAJ_06: 247174, // 분식·간편식 (약 2.47억원)
      CAT_MAJ_07: 167029, // 카페·음료 (약 1.67억원)
      CAT_MAJ_08: 174990  // 베이커리·디저트 (약 1.75억원)
    };

    let totalEstSalesThousand = 0;
    const items = donutSegments.map((seg) => {
      const unitSales = salesMap[seg.id] || DEFAULT_MEDIAN_SALES[seg.id] || 280000;
      const estTotalSales = seg.count * unitSales; // 천원 단위
      totalEstSalesThousand += estTotalSales;

      // 외식업 표준 식자재 매입 원가율 약 32% (월간 환산: / 12)
      const monthlyFoodSupply = (estTotalSales * 0.32) / 12;

      return {
        id: seg.id,
        name: seg.name,
        shortName: seg.name.split('·')[0],
        storeCount: seg.count,
        unitSalesThousand: unitSales,
        estTotalSalesThousand: estTotalSales,
        monthlyFoodSupplyThousand: monthlyFoodSupply,
        formattedTotalSales: formatKrwCompact(estTotalSales),
        formattedUnitSales: formatKrwCompact(unitSales),
        formattedMonthlySupply: formatKrwCompact(monthlyFoodSupply)
      };
    });

    // 지역 전체 월간 식자재 발주 파이
    const totalMonthlyFoodPurchasingThousand = (totalEstSalesThousand * 0.32) / 12;

    // 개인 독립점포 비율 반영
    const indepRatio = totalStores > 0 ? (independentStores / totalStores) : 0.8;
    const indepMonthlyFoodPurchasingThousand = totalMonthlyFoodPurchasingThousand * indepRatio;

    return {
      items,
      totalEstSalesThousand,
      totalMonthlyFoodPurchasingThousand,
      indepMonthlyFoodPurchasingThousand,
      formattedTotalEstSales: formatKrwCompact(totalEstSalesThousand),
      formattedMonthlyFoodPurchasing: formatKrwCompact(totalMonthlyFoodPurchasingThousand),
      formattedIndepMonthlySupply: formatKrwCompact(indepMonthlyFoodPurchasingThousand)
    };
  }, [donutSegments, ftcCategoryComp, totalStores, independentStores]);

  // 막대 차트 데이터 구성
  const barChartItems = useMemo(() => {
    // 1. 구/시도/전국 8대 업종별 추정 연매출 모드 (기본값)
    if (barChartMode === 'category_total_est') {
      return estimatedSalesAnalytics.items.map((item) => ({
        key: item.id,
        label: `${item.name} 추정 연매출`,
        shortLabel: item.shortName,
        value: item.estTotalSalesThousand,
        subLabel: `점포 ${item.storeCount.toLocaleString()}개 × 중위 ${item.formattedUnitSales}`,
        subDetail: `월 식자재 발주 약 ${item.formattedMonthlySupply}`,
        formatted: item.formattedTotalSales,
        isSelected: selectedCategory !== 'ALL' ? selectedCategory === item.id : item.id === 'CAT_MAJ_01'
      }));
    }

    // 2. 8대 업종별 월간 식자재 추정 발주액 모드
    if (barChartMode === 'category_monthly_supply') {
      return estimatedSalesAnalytics.items.map((item) => ({
        key: item.id,
        label: `${item.name} 월 식자재 발주`,
        shortLabel: item.shortName,
        value: item.monthlyFoodSupplyThousand,
        subLabel: `식자재 원가율 32% 기준 추정`,
        subDetail: `${regionTitle} 점포 ${item.storeCount.toLocaleString()}개소`,
        formatted: `${item.formattedMonthlySupply} / 월`,
        isSelected: selectedCategory !== 'ALL' ? selectedCategory === item.id : item.id === 'CAT_MAJ_01'
      }));
    }

    // 3. 연도별 가맹점 매출 추이 모드
    if (barChartMode === 'yearly_trends' && yearlySeries.length > 0) {
      return yearlySeries.map((yr) => {
        const yearVal = yr.benchmark_year || yr.year;
        const finYearVal = yr.financial_year;
        const val = yr.median_sales_thousand_krw || yr.simple_avg_thousand_krw || 0;
        return {
          key: String(yearVal),
          label: `${yearVal}년 공시${finYearVal ? ` (${finYearVal}년 결산)` : ''}`,
          shortLabel: `${yearVal}년`,
          value: val,
          subLabel: `공시 표본 ${yr.sample_count?.toLocaleString() || 0}개사`,
          subDetail: null,
          formatted: formatKrwCompact(val),
          isSelected: selectedYear ? String(selectedYear) === String(yearVal) : String(yearVal) === '2025'
        };
      });
    }

    // 4. 업종별 점포당 평균 연매출 벤치마크 (단일 점포 발주력) 및 점포개설비
    if (ftcCategoryComp.length > 0) {
      const ordered = [...ftcCategoryComp].sort((a, b) =>
        String(a.category_major_id).localeCompare(String(b.category_major_id))
      );
      return ordered.map((cat) => {
        const val =
          barChartMode === 'category_cost'
            ? cat.median_cost_thousand_krw || 0
            : cat.median_sales_thousand_krw || 0;
        const shortName = (cat.category_major_name || '')
          .replace('·세계음식', '')
          .replace('·패스트푸드', '')
          .replace('·간편식', '')
          .replace('·음료', '')
          .replace('·디저트', '');
        return {
          key: cat.category_major_id,
          label: barChartMode === 'category_cost' ? `${cat.category_major_name} 개설비` : `${cat.category_major_name} 점포당 연매출`,
          shortLabel: shortName,
          value: val,
          subLabel: barChartMode === 'category_cost' ? `개설비 중위값` : `가맹점 중위 매출`,
          subDetail: `투자회수비율 ${cat.sales_to_cost_ratio || '-'}배`,
          formatted: formatKrwCompact(val),
          isSelected:
            selectedCategory !== 'ALL'
              ? selectedCategory === cat.category_major_id
              : cat.category_major_id === 'CAT_MAJ_01'
        };
      });
    }

    return donutSegments.map((seg) => ({
      key: seg.id,
      label: seg.name,
      shortLabel: seg.name.split('·')[0],
      value: seg.count,
      subLabel: `점유율 ${seg.pct}%`,
      subDetail: null,
      formatted: `${seg.count.toLocaleString()}개`,
      isSelected: selectedCategory === seg.id
    }));
  }, [barChartMode, estimatedSalesAnalytics, yearlySeries, ftcCategoryComp, donutSegments, selectedCategory, selectedYear, regionTitle]);

  const maxBarValue = useMemo(() => {
    return Math.max(1, ...barChartItems.map((i) => i.value || 0));
  }, [barChartItems]);

  const activeBarIndex = useMemo(() => {
    if (hoveredBarIdx !== null && barChartItems[hoveredBarIdx]) return hoveredBarIdx;
    const foundIdx = barChartItems.findIndex((i) => i.isSelected);
    return foundIdx >= 0 ? foundIdx : 0;
  }, [hoveredBarIdx, barChartItems]);

  // 상위 브랜드 목록 (Top 8)
  const topBrands = useMemo(() => {
    const raw = topBrandsState?.list?.length
      ? topBrandsState.list
      : (regionDetail?.top_brands || nationalRegionDetail?.top_brands || []);
    return raw.slice(0, 8);
  }, [topBrandsState, regionDetail, nationalRegionDetail]);

  const cr5Pct = useMemo(() => {
    return topBrands
      .slice(0, 5)
      .reduce((acc, cur) => acc + Number(cur.share_pct || cur.region_category_share_pct || 0), 0)
      .toFixed(1);
  }, [topBrands]);

  const handleNavClick = (navId, ref) => {
    setActiveNav(navId);
    if (ref && ref.current) {
      ref.current.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  };

  return (
    <div className="finora-dashboard-root">
      {/* 1. 좌측 사이드바 내비게이션 (유일한 지도 진입점은 하단 프로모 카드) */}
      <aside className="finora-sidebar" aria-label="대시보드 메인 내비게이션">
        <div className="finora-brand-box">
          <div className="finora-logo-mark" aria-hidden="true">
            <svg viewBox="0 0 36 36" fill="none" xmlns="http://www.w3.org/2000/svg">
              <rect width="36" height="36" rx="11" fill="url(#finoraGreenGrad)" />
              <path
                d="M18 8C13.5 8 10 11.5 10 16C10 21.25 18 28 18 28C18 28 26 21.25 26 16C26 11.5 22.5 8 18 8Z"
                stroke="#ffffff"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
              <circle cx="18" cy="15.5" r="3" fill="#ffffff" />
              <defs>
                <linearGradient id="finoraGreenGrad" x1="0" y1="0" x2="36" y2="36" gradientUnits="userSpaceOnUse">
                  <stop stopColor="#0d4a32" />
                  <stop offset="1" stopColor="#10b981" />
                </linearGradient>
              </defs>
            </svg>
          </div>
          <div className="finora-brand-text">
            <span className="finora-brand-name">Food Market Map</span>
            <span className="finora-brand-tagline">식자재 유통 잠재 거래처 발굴 인텔리전스</span>
          </div>
        </div>

        <nav className="finora-nav-list">
          <button
            type="button"
            className={`finora-nav-item ${activeNav === 'dashboard' ? 'active' : ''}`}
            onClick={() => handleNavClick('dashboard', overviewSectionRef)}
          >
            <span className="nav-icon">🏠</span>
            <span className="nav-label">대시보드 홈</span>
          </button>

          <button
            type="button"
            className={`finora-nav-item ${activeNav === 'categories' ? 'active' : ''}`}
            onClick={() => handleNavClick('categories', categorySectionRef)}
          >
            <span className="nav-icon">🍽️</span>
            <span className="nav-label">8대 업종 점유율</span>
          </button>

          <button
            type="button"
            className={`finora-nav-item ${activeNav === 'ftc' ? 'active' : ''}`}
            onClick={() => handleNavClick('ftc', ftcSectionRef)}
          >
            <span className="nav-icon">💰</span>
            <span className="nav-label">점포 매출·발주력</span>
          </button>

          <button
            type="button"
            className={`finora-nav-item ${activeNav === 'brands' ? 'active' : ''}`}
            onClick={() => handleNavClick('brands', brandSectionRef)}
          >
            <span className="nav-icon">🏆</span>
            <span className="nav-label">주요 브랜드 네트워크</span>
          </button>

          <button
            type="button"
            className={`finora-nav-item ${activeNav === 'hotspots' ? 'active' : ''}`}
            onClick={() => handleNavClick('hotspots', hotspotSectionRef)}
          >
            <span className="nav-icon">🔥</span>
            <span className="nav-label">고밀도 상권 핫스팟</span>
          </button>
        </nav>

        {/* 좌측 하단 프로모션 카드: 단일 지정 3D 상권 지도 진입 버튼 */}
        <div className="finora-sidebar-promo">
          <div className="promo-illustration" aria-hidden="true">
            <svg viewBox="0 0 120 76" fill="none" xmlns="http://www.w3.org/2000/svg">
              <ellipse cx="60" cy="66" rx="46" ry="8" fill="#10b981" fillOpacity="0.18" />
              <rect x="28" y="30" width="16" height="34" rx="4" fill="#059669" />
              <rect x="50" y="14" width="20" height="50" rx="4" fill="#0f5132" />
              <rect x="76" y="24" width="16" height="40" rx="4" fill="#10b981" />
              <circle cx="60" cy="12" r="7" fill="#fbbf24" />
            </svg>
          </div>
          <h4 className="promo-title">
            입체적인 공간 분석이
            <br />
            알짜 납품처를 발굴합니다
          </h4>
          <p className="promo-sub">73.5만 점포 밀집도 · 식자재 배송 루트 기획</p>
          <button type="button" className="promo-cta-btn" onClick={onOpenMap}>
            <span>3D 상권 지도 열기</span>
            <span className="promo-arrow">→</span>
          </button>
        </div>
      </aside>

      {/* 2. 메인 콘텐츠 영역 */}
      <div className="finora-main-area">
        {/* 상단 헤더 바 */}
        <header className="finora-topbar">
          <div className="finora-search-wrapper" ref={searchBoxRef}>
            <span className="search-icon" aria-hidden="true">🔍</span>
            <input
              type="text"
              className="finora-search-input"
              placeholder="브랜드 검색 (예: 메가커피, 스타벅스, 교촌치킨, 한솥도시락...)"
              value={brandQuery}
              onChange={(e) => {
                setBrandQuery(e.target.value);
                setShowBrandDropdown(true);
              }}
              onFocus={() => setShowBrandDropdown(true)}
            />
            {brandQuery && (
              <button
                type="button"
                className="search-clear-btn"
                onClick={() => {
                  setBrandQuery('');
                  setBrandResults([]);
                  setSelectedBrandPreview(null);
                }}
                aria-label="검색어 지우기"
              >
                ✕
              </button>
            )}

            {showBrandDropdown && brandQuery.trim().length > 0 && (
              <div className="finora-search-dropdown" role="listbox">
                <div className="dropdown-head">
                  <span>브랜드 검색 결과 ({brandResults.length}건)</span>
                  <span className="dropdown-region-tag">{regionTitle} 기준</span>
                </div>
                {brandSearching ? (
                  <div className="dropdown-empty">브랜드 데이터베이스 검색 중...</div>
                ) : brandResults.length === 0 ? (
                  <div className="dropdown-empty">일치하는 브랜드 후보가 없습니다.</div>
                ) : (
                  <ul className="dropdown-list">
                    {brandResults.map((b) => (
                      <li key={b.internal_brand_id} className="dropdown-item">
                        <div
                          className="dropdown-item-info"
                          onClick={() => {
                            setSelectedBrandPreview(b);
                            setShowBrandDropdown(false);
                          }}
                        >
                          <span className="dropdown-brand-name">{b.brand_name_std}</span>
                          <span className="dropdown-brand-meta">
                            전국 {b.nationwide_store_count?.toLocaleString()}개 · 지역{' '}
                            <strong>{b.region_store_count?.toLocaleString()}개</strong>
                          </span>
                        </div>
                        <button
                          type="button"
                          className="dropdown-map-btn"
                          onClick={() => {
                            setShowBrandDropdown(false);
                            onOpenMapWithBrand(b);
                          }}
                        >
                          📍 지도 위치
                        </button>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            )}
          </div>

          <div className="finora-topbar-controls">
            <div className="finora-select-group" aria-label="분석 지역 및 업종 필터">
              <select
                className="finora-pill-select"
                value={selectedSido}
                onChange={(e) => onSelectSido(e.target.value)}
                aria-label="시도 선택"
              >
                <option value="00">🌍 전국 (17개 시도)</option>
                {sidoList.map((s) => (
                  <option key={s.region_code} value={s.region_code}>
                    📍 {s.region_name}
                  </option>
                ))}
              </select>

              {selectedSido !== '00' && (
                <select
                  className="finora-pill-select"
                  value={selectedSigungu}
                  onChange={(e) => onSelectSigungu(e.target.value)}
                  disabled={regionsLoading}
                  aria-label="시군구 선택"
                >
                  <option value="">전체 시군구</option>
                  {sigunguList.map((g) => (
                    <option key={g.region_code} value={g.region_code}>
                      {g.region_name}
                    </option>
                  ))}
                </select>
              )}

              <select
                className="finora-pill-select category-select"
                value={selectedCategory}
                onChange={(e) => onSelectCategory(e.target.value)}
                aria-label="8대 외식 업종 선택"
              >
                {CATEGORY_MAJOR_LIST.filter((c) => !c.isUnmapped).map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.icon} {c.name}
                  </option>
                ))}
              </select>
            </div>

            {onOpenIntro && (
              <button
                type="button"
                className="finora-intro-btn"
                onClick={onOpenIntro}
                title="3D 공간 인텔리전스 시네마틱 인트로 다시보기"
                aria-label="시네마틱 인트로 열기"
              >
                <span className="finora-intro-icon">🎬</span>
                <span className="finora-intro-label">시네마틱 인트로</span>
              </button>
            )}

            <div className="finora-profile-chip" title="소상공인시장진흥공단 & 공정거래위원회 공식 데이터 연동">
              <div className="profile-avatar">KR</div>
              <div className="profile-meta">
                <span className="profile-name">공공데이터 엔진</span>
                <span className="profile-role">
                  <span className="online-dot" /> 실시간 연동
                </span>
              </div>
            </div>
          </div>
        </header>

        {/* 선택된 브랜드 요약 배너 */}
        {selectedBrandPreview && (
          <div className="finora-brand-spotlight-banner" role="region" aria-label="선택 브랜드 요약">
            <div className="spotlight-left">
              <span className="spotlight-badge">브랜드 포커스</span>
              <h3 className="spotlight-title">{selectedBrandPreview.brand_name_std}</h3>
              <span className="spotlight-stats">
                전국 총 <strong>{selectedBrandPreview.nationwide_store_count?.toLocaleString()}개</strong> 점포 ·{' '}
                {regionTitle} <strong>{selectedBrandPreview.region_store_count?.toLocaleString()}개</strong> 출점 (업종 점유율{' '}
                {selectedBrandPreview.region_category_share_pct ?? 0}%)
              </span>
            </div>
            <div className="spotlight-actions">
              <button
                type="button"
                className="spotlight-map-btn"
                onClick={() => onOpenMapWithBrand(selectedBrandPreview)}
              >
                📍 3D 지도에서 이 브랜드 점포 위치 보기 →
              </button>
              <button
                type="button"
                className="spotlight-close-btn"
                onClick={() => setSelectedBrandPreview(null)}
              >
                닫기 ✕
              </button>
            </div>
          </div>
        )}

        {/* 3. 대시보드 본문 레이아웃 (정돈된 3-Tier 균등 높이 벤토 그리드) */}
        <div className="finora-bento-grid">
          {/* =========================================================================
              TIER 1: 총괄 개황 (3개 균등 높이 카드)
              [1] Hero 총괄 모수 카드  |  [2] 8대 업종 도넛 차트  |  [3] 식자재 배송 물류 밀집도
              ========================================================================= */}
          <section className="finora-tier finora-tier-overview" ref={overviewSectionRef}>
            {/* Card 1: Hero 총괄 모수 카드 */}
            <div className="finora-card finora-hero-card" aria-label="식자재 납품 대상 외식 점포 모수">
              <div className="hero-top-row">
                <div>
                  <h1 className="hero-greeting">
                    {regionTitle} 식자재 납품 잠재 고객 분석 📦
                  </h1>
                  <p className="hero-subtitle">
                    소진공 공간 전수({summaryMeta?.data_reference_month || '2025.12'}) 기반 B2B 영업 타깃 분석
                  </p>
                </div>
                <span className="hero-health-pill">✓ 실측 잠재 고객</span>
              </div>

              <div className="hero-balance-row">
                <div className="hero-balance-info">
                  <span className="hero-balance-label">
                    {selectedCategory === 'ALL'
                      ? `${regionTitle} 식자재 납품 대상 외식 점포 모수`
                      : `${regionTitle} [${currentCatMeta.icon} ${currentCatMeta.name}] 타깃 점포 수`}
                  </span>
                  <div className="hero-balance-number">
                    {totalStores.toLocaleString()}
                    <span className="hero-balance-unit">개소</span>
                  </div>
                  <div className="hero-delta-row">
                    <span className="hero-delta-positive">
                      🎯 자유 발주 개인 독립점 {independentStores.toLocaleString()}개 ({independentRate}%)
                    </span>
                    <span className="hero-delta-compare">
                      · {regionTitle} 외식업 추정 연매출 {estimatedSalesAnalytics.formattedTotalEstSales} (월 발주 약 {estimatedSalesAnalytics.formattedMonthlyFoodPurchasing})
                    </span>
                  </div>
                </div>

                <div className="hero-wallet-graphic" aria-hidden="true">
                  <svg viewBox="0 0 150 110" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <rect x="28" y="34" width="96" height="64" rx="14" fill="#063724" />
                    <rect x="22" y="28" width="96" height="64" rx="14" fill="#10b981" />
                    <rect x="34" y="14" width="68" height="36" rx="8" fill="#dcfce7" transform="rotate(-8 34 14)" />
                    <rect x="42" y="22" width="32" height="6" rx="3" fill="#059669" transform="rotate(-8 42 22)" />
                    <circle cx="96" cy="60" r="8" fill="#fbbf24" />
                    <circle cx="18" cy="86" r="11" fill="#f59e0b" />
                    <circle cx="128" cy="88" r="9" fill="#fbbf24" />
                  </svg>
                </div>
              </div>
            </div>

            {/* Card 2: 8대 외식업종 식자재 납품 시장 구성 (도넛 차트) */}
            <div
              ref={categorySectionRef}
              className="finora-card finora-donut-card"
              aria-label="8대 외식업종 식자재 납품 시장 구성"
            >
              <div className="finora-card-header">
                <div>
                  <h2 className="finora-card-title">8대 업종별 식자재 납품 시장 구성</h2>
                  <span className="finora-card-sub">농·축·수산·가공식품 등 품목별 외식 점포 수요처 비중</span>
                </div>
                <select
                  className="finora-mini-select"
                  value={selectedCategory}
                  onChange={(e) => onSelectCategory(e.target.value)}
                  aria-label="업종 필터 선택"
                >
                  <option value="ALL">전체 업종</option>
                  {CATEGORY_MAJOR_LIST.filter((c) => !c.isUnmapped).map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name}
                    </option>
                  ))}
                </select>
              </div>

              <div className="finora-donut-body">
                {/* 좌측 SVG 도넛 차트 */}
                <div className="donut-svg-container">
                  <svg viewBox="0 0 140 140" className="finora-donut-svg">
                    <circle
                      cx="70"
                      cy="70"
                      r="50"
                      fill="none"
                      stroke="#f1f5f9"
                      strokeWidth="18"
                    />
                    {donutSegments.map((seg) => {
                      const radius = 50;
                      const circumference = 2 * Math.PI * radius;
                      const strokeLength = (seg.rawPct / 100) * circumference;
                      const strokeOffset = -((seg.startPct / 100) * circumference);
                      const isHovered = hoveredDonutId === seg.id || selectedCategory === seg.id;

                      return (
                        <circle
                          key={seg.id}
                          cx="70"
                          cy="70"
                          r={radius}
                          fill="none"
                          stroke={seg.color}
                          strokeWidth={isHovered ? '22' : '18'}
                          strokeDasharray={`${Math.max(0, strokeLength - 1.2)} ${circumference}`}
                          strokeDashoffset={strokeOffset}
                          transform="rotate(-90 70 70)"
                          className="donut-segment-arc"
                          onMouseEnter={() => setHoveredDonutId(seg.id)}
                          onMouseLeave={() => setHoveredDonutId(null)}
                          onClick={() =>
                            onSelectCategory(selectedCategory === seg.id ? 'ALL' : seg.id)
                          }
                        />
                      );
                    })}
                  </svg>
                  <div className="donut-center-label">
                    <span className="donut-center-value">
                      {hoveredDonutId
                        ? `${donutSegments.find((s) => s.id === hoveredDonutId)?.pct || 0}%`
                        : totalEightMajorStores.toLocaleString()}
                    </span>
                    <span className="donut-center-sub">
                      {hoveredDonutId
                        ? donutSegments.find((s) => s.id === hoveredDonutId)?.name
                        : '8대 업종 점포'}
                    </span>
                  </div>
                </div>

                {/* 우측 업종 범례 리스트 (한 줄로 깔끔하게 표시, 글자 분할 방지) */}
                <ul className="donut-legend-list">
                  {donutSegments.slice(0, 6).map((seg) => {
                    const isSelected = selectedCategory === seg.id;
                    return (
                      <li
                        key={seg.id}
                        className={`donut-legend-item ${isSelected ? 'active' : ''}`}
                        onClick={() =>
                          onSelectCategory(selectedCategory === seg.id ? 'ALL' : seg.id)
                        }
                        onMouseEnter={() => setHoveredDonutId(seg.id)}
                        onMouseLeave={() => setHoveredDonutId(null)}
                      >
                        <div className="legend-left">
                          <span
                            className="legend-dot"
                            style={{ backgroundColor: seg.color }}
                          />
                          <span className="legend-name" title={seg.name}>{seg.name}</span>
                        </div>
                        <div className="legend-right">
                          <span className="legend-pct">{seg.pct}%</span>
                          <span className="legend-count">
                            {seg.count.toLocaleString()}개
                          </span>
                        </div>
                      </li>
                    );
                  })}
                </ul>
              </div>
            </div>

            {/* Card 3: 식자재 배송 물류 밀집도 & 효율 카드 */}
            <div className="finora-card finora-logistics-card" aria-label="식자재 배송 물류 밀집도">
              <div className="finora-card-header">
                <div>
                  <span className="logistics-eyebrow">🚚 B2B DISTRIBUTION LOGISTICS</span>
                  <h2 className="finora-card-title">식자재 배송 밀집도 & 물류 효율</h2>
                </div>
                <span className="logistics-badge">밀집도 A+</span>
              </div>

              <div className="logistics-body">
                <p className="logistics-desc">
                  100m 격자 내 점포 밀집도가 높을수록 배송 차량당 회전율과 집중 납품 영업 효율이 극대화됩니다.
                </p>

                <div className="logistics-metrics-grid">
                  <div className="logistics-metric-box">
                    <span className="metric-box-label">물류비 절감 효과</span>
                    <strong className="metric-box-val text-emerald">최대 35% ↓</strong>
                    <span className="metric-box-sub">반경 1km 집중 납품 시</span>
                  </div>
                  <div className="logistics-metric-box">
                    <span className="metric-box-label">배송 순회 규모</span>
                    <strong className="metric-box-val">18~24개소</strong>
                    <span className="metric-box-sub">차량 1대당 일일 납품처</span>
                  </div>
                </div>

                <div className="logistics-footer-tip">
                  <span className="tip-icon">📍</span>
                  <span className="tip-text">좌측 사이드바 하단 버튼으로 3D 입체 밀집도를 확인할 수 있습니다.</span>
                </div>
              </div>
            </div>
          </section>

          {/* =========================================================================
              QUICK FILTER STRIP: 8대 업종 즉시 필터링 바 (한 줄 가로 스트립)
              ========================================================================= */}
          <div className="finora-category-pill-strip" role="toolbar" aria-label="8대 외식업종 품목별 타깃 필터">
            <div className="pill-strip-label">
              <span className="pill-strip-title">식자재 품목별 타깃 필터</span>
              <span className="pill-strip-sub">업종을 선택하면 점포 모수와 발주력 통계가 즉시 재계산됩니다</span>
            </div>
            <div className="pill-strip-scroll">
              <button
                type="button"
                className={`cat-pill-btn ${selectedCategory === 'ALL' ? 'active' : ''}`}
                onClick={() => onSelectCategory('ALL')}
              >
                <span className="cat-pill-icon">🌍</span>
                <span className="cat-pill-name">전체 외식업</span>
                <span className="cat-pill-badge">{totalStores.toLocaleString()}개</span>
              </button>
              {CATEGORY_MAJOR_LIST.filter((c) => !c.isUnmapped).map((cat) => {
                const seg = donutSegments.find((s) => s.id === cat.id);
                const isSelected = selectedCategory === cat.id;
                return (
                  <button
                    key={cat.id}
                    type="button"
                    className={`cat-pill-btn ${isSelected ? 'active' : ''}`}
                    onClick={() => onSelectCategory(isSelected ? 'ALL' : cat.id)}
                  >
                    <span className="cat-pill-icon">{cat.icon}</span>
                    <span className="cat-pill-name">{cat.name}</span>
                    {seg && <span className="cat-pill-badge">{seg.count.toLocaleString()}개</span>}
                  </button>
                );
              })}
            </div>

            {/* 선택된 대분류에 속한 48대 세부 중분류 서브 칩 */}
            {selectedCategory !== 'ALL' && midCategories.length > 0 && (
              <div className="finora-midcat-substrip">
                <span className="midcat-substrip-label">└ 세부 품목:</span>
                <button
                  type="button"
                  className={`midcat-chip ${!selectedMidCategory ? 'active' : ''}`}
                  onClick={() => onSelectMidCategory(null)}
                >
                  {currentCatMeta.name} 전체
                </button>
                {midCategories.map((mid) => {
                  const isMidActive = selectedMidCategory === mid.category_mid_id;
                  return (
                    <button
                      key={mid.category_mid_id}
                      type="button"
                      className={`midcat-chip ${isMidActive ? 'active' : ''}`}
                      onClick={() => onSelectMidCategory(isMidActive ? null : mid.category_mid_id)}
                    >
                      {mid.category_mid_name} ({(mid.total_stores || 0).toLocaleString()}개)
                    </button>
                  );
                })}
              </div>
            )}
          </div>

          {/* =========================================================================
              TIER 2: 매출 및 납품 타깃 구조 (3개 균등 높이 카드)
              [1] 점포 연매출 막대차트 (1.2fr)  |  [2] 납품 영업 타깃 게이지 (1fr)  |  [3] 점포당 발주력 지표 (0.8fr)
              ========================================================================= */}
          <section className="finora-tier finora-tier-financials" ref={ftcSectionRef}>
            {/* Card 1: 8대 업종별 점포 연매출 / 추정 연매출 (발주 규모) */}
            <div className="finora-card finora-bar-card" aria-label="업종별 점포 매출 및 식자재 발주력 벤치마크">
              <div className="finora-card-header barchart-card-header">
                <div className="barchart-title-block">
                  <div className="barchart-title-badge-row">
                    <h2 className="finora-card-title">
                      {barChartMode === 'category_total_est' && `${regionTitle} 8대 업종별 시장규모`}
                      {barChartMode === 'category_monthly_supply' && `${regionTitle} 8대 업종별 식자재 발주액`}
                      {barChartMode === 'category_sales' && '8대 업종별 점포당 중위 연매출'}
                      {barChartMode === 'category_cost' && '8대 업종별 점포 개설비용'}
                      {barChartMode === 'yearly_trends' && '연도별 외식 가맹점 매출 추이'}
                    </h2>
                    {(barChartMode === 'category_total_est' || barChartMode === 'category_monthly_supply') && (
                      <span className="est-badge" title="소진공 실측 점포수와 공정위 중위매출을 결합한 통계 추정 모델">
                        📊 통계 추정치
                      </span>
                    )}
                  </div>
                  <span className="finora-card-sub">
                    {barChartMode === 'category_total_est' && `소진공 실측 점포수 × 공정위 중위매출 결합 외식업 연매출`}
                    {barChartMode === 'category_monthly_supply' && '외식업 식자재 원가율 32% 기준 월간 발주 규모'}
                    {barChartMode === 'category_sales' && '가맹점 1곳당 연간 실질 중위 매출액 (공정위 공시)'}
                    {barChartMode === 'category_cost' && '가맹본부별 신규 점포 개설 부담금 (창업 비용)'}
                    {barChartMode === 'yearly_trends' && '최근 5개년 외식업 가맹점 매출 추이 (공정위)'}
                  </span>
                </div>

                <div className="barchart-header-controls">
                  <select
                    className="finora-mini-select"
                    value={barChartMode}
                    onChange={(e) => {
                      setBarChartMode(e.target.value);
                      setHoveredBarIdx(null);
                    }}
                    aria-label="차트 지표 전환"
                  >
                    <option value="category_total_est">업종별 추정 연매출</option>
                    <option value="category_monthly_supply">월 식자재 발주액</option>
                    <option value="category_sales">점포당 중위매출</option>
                    <option value="category_cost">점포개설비</option>
                    <option value="yearly_trends">연도별 매출추이</option>
                  </select>
                </div>
              </div>

              <div className="finora-barchart-stage">
                <div className="barchart-y-axis" aria-hidden="true">
                  <span>{formatKrwCompact(maxBarValue)}</span>
                  <span>{formatKrwCompact(maxBarValue * 0.75)}</span>
                  <span>{formatKrwCompact(maxBarValue * 0.5)}</span>
                  <span>{formatKrwCompact(maxBarValue * 0.25)}</span>
                  <span>0원</span>
                </div>

                <div className="barchart-bars-wrap">
                  {barChartItems.map((item, idx) => {
                    const heightPct = Math.max(12, Math.round((item.value / maxBarValue) * 100));
                    const isActive = idx === activeBarIndex;

                    return (
                      <div
                        key={item.key}
                        className={`barchart-col ${isActive ? 'active' : ''}`}
                        onMouseEnter={() => setHoveredBarIdx(idx)}
                        onMouseLeave={() => setHoveredBarIdx(null)}
                        onClick={() => {
                          if (barChartMode !== 'yearly_trends' && String(item.key).startsWith('CAT_MAJ_')) {
                            onSelectCategory(item.key);
                          }
                        }}
                      >
                        {isActive && (
                          <div className="barchart-floating-tooltip">
                            <span className="tooltip-cat">{item.label}</span>
                            <strong className="tooltip-val">{item.formatted}</strong>
                            {item.subDetail && (
                              <span className="tooltip-sub">{item.subDetail}</span>
                            )}
                          </div>
                        )}

                        <div className="barchart-bar-track">
                          <div
                            className={`barchart-bar-fill ${isActive ? 'bar-active' : ''}`}
                            style={{ height: `${heightPct}%` }}
                          />
                        </div>
                        <span className="barchart-x-label">{item.shortLabel}</span>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>

            {/* Card 2: 납품 영업 타깃 구조 (독립점포 vs 가맹점 게이지) */}
            <div className="finora-card finora-gauge-card" aria-label="납품 영업 타깃 구조">
              <div className="finora-card-header">
                <div>
                  <h2 className="finora-card-title">납품 영업 타깃 구조 (독립점 vs 가맹점)</h2>
                  <span className="finora-card-sub">{regionTitle} 자유 발주 개인 점포 vs 본사 폐쇄몰 가맹점</span>
                </div>
              </div>

              <div className="finora-gauge-body">
                <div className="gauge-ring-box">
                  <svg viewBox="0 0 150 150" className="finora-ring-svg">
                    <circle
                      cx="75"
                      cy="75"
                      r="56"
                      fill="none"
                      stroke="#e2e8f0"
                      strokeWidth="15"
                    />
                    <circle
                      cx="75"
                      cy="75"
                      r="56"
                      fill="none"
                      stroke="#3b82f6"
                      strokeWidth="15"
                      strokeLinecap="round"
                      strokeDasharray={`${(Number(brandRate) / 100) * 351.8} 351.8`}
                      transform="rotate(-90 75 75)"
                    />
                    <circle
                      cx="75"
                      cy="75"
                      r="56"
                      fill="none"
                      stroke="#059669"
                      strokeWidth="15"
                      strokeLinecap="round"
                      strokeDasharray={`${(Number(independentRate) / 100) * 351.8} 351.8`}
                      transform="rotate(-90 75 75)"
                    />
                  </svg>
                  <div className="gauge-ring-center">
                    <span className="gauge-ring-pct">{independentRate}%</span>
                    <span className="gauge-ring-caption">자유발주 점포</span>
                  </div>
                </div>

                <ul className="gauge-breakdown-list">
                  <li>
                    <span className="gb-dot" style={{ background: '#059669' }} />
                    <span className="gb-name">개인 독립점 (자유 발주)</span>
                    <strong className="gb-val" title={`${independentStores.toLocaleString()}개 점포`}>
                      {independentRate}% ({formatStoreCountCompact(independentStores)})
                    </strong>
                  </li>
                  <li>
                    <span className="gb-dot" style={{ background: '#3b82f6' }} />
                    <span className="gb-name">중소 브랜드 연계 점포</span>
                    <strong className="gb-val">{candidateOnlyRate}%</strong>
                  </li>
                  <li>
                    <span className="gb-dot" style={{ background: '#94a3b8' }} />
                    <span className="gb-name">공식 프랜차이즈 가맹점</span>
                    <strong className="gb-val" title={`${franchiseStores.toLocaleString()}개 점포`}>
                      {franchiseRate}% ({formatStoreCountCompact(franchiseStores)})
                    </strong>
                  </li>
                  <li>
                    <span className="gb-dot" style={{ background: '#f59e0b' }} />
                    <span className="gb-name">상위 5대 브랜드 점유율</span>
                    <strong className="gb-val">{cr5Pct}%</strong>
                  </li>
                </ul>
              </div>

              <div className="finora-insight-banner">
                <span className="insight-trophy">💡</span>
                <div className="insight-copy">
                  <strong>
                    {regionTitle}은 자유 발주 가능한 개인 독립점포 비중이 {independentRate}%({independentStores.toLocaleString()}개)입니다!
                  </strong>
                  <p>
                    본사 폐쇄몰 강제 사입이 없어 유통사가 직접 납품 계약을 체결할 수 있는 1차 핵심 영업 타깃입니다.
                  </p>
                </div>
              </div>
            </div>

            {/* Card 3: 점포당 식자재 발주력 지표 & 구/지역 추정 연매출 */}
            <div className="finora-card finora-bills-card" aria-label="점포 규모 및 식자재 발주력 지표">
              <div className="finora-card-header">
                <div>
                  <h2 className="finora-card-title">{regionTitle} 식자재 발주 시장규모</h2>
                  <span className="finora-card-sub">
                    외식업 추정 연매출 <strong>{estimatedSalesAnalytics.formattedTotalEstSales}</strong>
                  </span>
                </div>
                <span className="bills-tag est-tag" title="소진공 실측 점포수와 공정위 중위매출을 결합한 통계 추정 모델">
                  📊 통계 추정치
                </span>
              </div>

              <ul className="finora-bills-list">
                <li className="bill-item">
                  <div className="bill-icon tone-emerald">💰</div>
                  <div className="bill-info">
                    <span className="bill-title">{regionTitle} 외식업 추정 연매출</span>
                    <span className="bill-sub">소진공 실측 점포 {totalStores.toLocaleString()}개소 × 공정위 중위매출 결합</span>
                  </div>
                  <strong className="bill-amount">{estimatedSalesAnalytics.formattedTotalEstSales}</strong>
                </li>

                <li className="bill-item">
                  <div className="bill-icon tone-blue">📦</div>
                  <div className="bill-info">
                    <span className="bill-title">월간 식자재 추정 발주 파이</span>
                    <span className="bill-sub">외식업 표준 식자재 원가율(매출의 약 32%) 적용</span>
                  </div>
                  <strong className="bill-amount">{estimatedSalesAnalytics.formattedMonthlyFoodPurchasing}</strong>
                </li>

                <li className="bill-item">
                  <div className="bill-icon tone-purple">🎯</div>
                  <div className="bill-info">
                    <span className="bill-title">자유발주 독립점 추정 발주액</span>
                    <span className="bill-sub">본사 강제사입 없는 1차 핵심 직납 공략 파이 ({independentRate}%)</span>
                  </div>
                  <strong className="bill-amount">{estimatedSalesAnalytics.formattedIndepMonthlySupply}</strong>
                </li>

                <li className="bill-item">
                  <div className="bill-icon tone-amber">🏬</div>
                  <div className="bill-info">
                    <span className="bill-title">점포당 연평균 중위 매출</span>
                    <span className="bill-sub">가맹점 1곳당 연간 실질 발주 규모 기준</span>
                  </div>
                  <strong className="bill-amount">{formatManwon(medianSalesKrw)}</strong>
                </li>
              </ul>

              <div className="bills-footnote">
                ※ 산출 근거: 소진공 2025.12 실측 점포수 × 공정위 업종별 중위매출액 (식자재 원가율 32% 기준 통계 모델링 추정치)
              </div>
            </div>
          </section>

          {/* =========================================================================
              TIER 3: 브랜드 네트워크 & 고밀도 상권 핫스팟 (2열 와이드 그리드)
              [1] 대량 납품 제안 가능 주요 브랜드 네트워크 (Wide Table - 1.6fr)
              [2] 식자재 고밀도 납품 상권 Top 4 (1fr)
              ========================================================================= */}
          <section className="finora-tier finora-tier-execution" ref={brandSectionRef}>
            {/* Card 1: 주요 브랜드 리더보드 (와이드 테이블) */}
            <div className="finora-card finora-table-card" aria-label="상위 프랜차이즈 브랜드 랭킹">
              <div className="finora-card-header">
                <div>
                  <h2 className="finora-card-title">
                    대량 납품 제안 가능 주요 브랜드 네트워크
                  </h2>
                  <span className="finora-card-sub">
                    {regionTitle} · {selectedCategory === 'ALL' ? '전체 외식업' : currentCatMeta.name} 기준 가맹 점포망
                  </span>
                </div>
              </div>

              <div className="finora-table-wrap">
                <table className="finora-transactions-table">
                  <colgroup>
                    <col style={{ width: '48px' }} />
                    <col style={{ width: '28%' }} />
                    <col style={{ width: '92px' }} />
                    <col style={{ width: '22%' }} />
                    <col style={{ width: '28%' }} />
                    <col style={{ width: '70px' }} />
                  </colgroup>
                  <thead>
                    <tr>
                      <th>순위</th>
                      <th>브랜드명</th>
                      <th>구분</th>
                      <th className="text-right">출점 점포 (점유율)</th>
                      <th>영업 제안 타깃</th>
                      <th className="text-right">지도</th>
                    </tr>
                  </thead>
                  <tbody>
                    {topBrands.length === 0 ? (
                      <tr>
                        <td colSpan={6} className="table-empty-cell">
                          브랜드 순위 데이터를 불러오는 중입니다...
                        </td>
                      </tr>
                    ) : (
                      topBrands.slice(0, 6).map((brand, i) => {
                        const count =
                          brand.store_count ??
                          brand.region_store_count ??
                          brand.discovered_store_count ??
                          0;
                        const share =
                          brand.share_pct ??
                          brand.region_category_share_pct ??
                          brand.market_share_in_nation ??
                          0;
                        const isConfirmed =
                          brand.brand_officiality === 'FRANCHISE_CONFIRMED';

                        return (
                          <tr key={brand.internal_brand_id || brand.brand_name_std || i}>
                            <td className="rank-cell">#{i + 1}</td>
                            <td>
                              <div className="brand-cell-main">
                                <span
                                  className={`brand-avatar-circle rank-${i < 3 ? i + 1 : 'other'}`}
                                >
                                  {(brand.brand_name_std || 'B').slice(0, 1)}
                                </span>
                                <span className="brand-name-text" title={brand.brand_name_std}>
                                  {brand.brand_name_std}
                                </span>
                              </div>
                            </td>
                            <td>
                              <span
                                className={`officiality-tag ${isConfirmed ? 'confirmed' : 'candidate'}`}
                              >
                                {isConfirmed ? '공식가맹' : '브랜드후보'}
                              </span>
                            </td>
                            <td className="text-right amount-cell">
                              <span className="store-count-strong">
                                {count.toLocaleString()}개
                              </span>
                              <span className="store-share-sub">({share}%)</span>
                            </td>
                            <td>
                              <span className="target-proposal-text">
                                {isConfirmed ? 'HQ 본사 일괄 납품 제안' : '점포별 개별 납품 계약'}
                              </span>
                            </td>
                            <td className="text-right">
                              <button
                                type="button"
                                className="table-map-jump-btn"
                                onClick={() => onOpenMapWithBrand(brand)}
                                title={`${brand.brand_name_std} 점포 위치를 3D 지도에서 확인`}
                              >
                                📍 지도
                              </button>
                            </td>
                          </tr>
                        );
                      })
                    )}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Card 2: 대한민국 핵심 상권 핫스팟 (식자재 고밀도 납품 권역) */}
            <div
              ref={hotspotSectionRef}
              className="finora-card finora-hotspots-card"
              aria-label="식자재 고밀도 납품 상권 Top 4"
            >
              <div className="finora-card-header">
                <div>
                  <h2 className="finora-card-title">식자재 고밀도 납품 상권 Top 4</h2>
                  <span className="finora-card-sub">상권 내 점포 밀집 클러스터 (집중 배송 타깃)</span>
                </div>
              </div>

              <ul className="finora-activity-list">
                {(hotspots.length > 0 ? hotspots.slice(0, 4) : []).map((spot, idx) => {
                  const spotEstMonthlySupply = formatKrwCompact(Math.round(((spot.store_count || 0) * 320000 * 0.32) / 12));
                  return (
                    <li
                      key={spot.hotspot_id || idx}
                      className="activity-item"
                      onClick={() => onOpenMapWithHotspot(spot)}
                    >
                      <div className="activity-badge">#{idx + 1}</div>
                      <div className="activity-info">
                        <span className="activity-name">{spot.hotspot_name}</span>
                        <span className="activity-meta">
                          {spot.dominant_category_name || '핵심 상권'} · 독립점 {Math.max(0, 100 - (spot.franchise_ratio || 0))}% · 월 발주 {spotEstMonthlySupply}
                        </span>
                      </div>
                      <div className="activity-right">
                        <strong className="activity-count">
                          {(spot.store_count || 0).toLocaleString()}개 점포
                        </strong>
                        <span className="activity-fly">상세 보기 ↗</span>
                      </div>
                    </li>
                  );
                })}
              </ul>

              <div className="hotspot-footer-insight">
                <span className="insight-truck-icon">🚚</span>
                <p className="insight-truck-text">
                  상위 고밀도 상권 집중 영업 시 배송 차량 1대로 일일 최대 30개 점포 순회 납품이 가능합니다.
                </p>
              </div>
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
