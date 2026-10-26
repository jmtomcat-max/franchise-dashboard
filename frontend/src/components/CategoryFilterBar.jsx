import React from 'react';

/**
 * 8대 대분류 메타데이터 정의 (config/food_category_taxonomy_v1.json 기준)
 */
export const CATEGORY_MAJOR_LIST = [
  { 
    id: 'ALL', 
    name: '전체', 
    icon: '🍽️', 
    description: '모든 외식 업종',
    color: '#0f172a', // Slate 900
    bgLight: 'rgba(15, 23, 42, 0.08)',
    ramp: ['#94a3b8', '#64748b', '#475569', '#334155', '#1e293b']
  },
  { 
    id: 'CAT_MAJ_01', 
    name: '한식', 
    icon: '🍚', 
    description: '한식 일반 및 전통 요리',
    color: '#059669', // Emerald Green
    bgLight: 'rgba(5, 150, 105, 0.12)',
    ramp: ['#34d399', '#10b981', '#059669', '#047857', '#064e3b']
  },
  { 
    id: 'CAT_MAJ_02', 
    name: '중식', 
    icon: '🥟', 
    description: '중화요리 및 아시안 퓨전',
    color: '#dc2626', // Crimson Red
    bgLight: 'rgba(220, 38, 38, 0.12)',
    ramp: ['#f87171', '#ef4444', '#dc2626', '#b91c1c', '#991b1b']
  },
  { 
    id: 'CAT_MAJ_03', 
    name: '일식', 
    icon: '🍣', 
    description: '초밥, 돈가스 및 일식',
    color: '#2563eb', // Royal Blue
    bgLight: 'rgba(37, 99, 235, 0.12)',
    ramp: ['#60a5fa', '#3b82f6', '#2563eb', '#1d4ed8', '#1e40af']
  },
  { 
    id: 'CAT_MAJ_04', 
    name: '양식·세계음식', 
    icon: '🍝', 
    description: '서양식 및 세계 각국 요리',
    color: '#d97706', // Amber Gold
    bgLight: 'rgba(217, 119, 6, 0.12)',
    ramp: ['#fbbf24', '#f59e0b', '#d97706', '#b45309', '#92400e']
  },
  { 
    id: 'CAT_MAJ_05', 
    name: '치킨·패스트푸드', 
    icon: '🍗', 
    description: '치킨, 피자 및 햄버거',
    color: '#ea580c', // Tangerine Orange
    bgLight: 'rgba(234, 88, 12, 0.12)',
    ramp: ['#fb923c', '#f97316', '#ea580c', '#c2410c', '#9a3412']
  },
  { 
    id: 'CAT_MAJ_06', 
    name: '분식·간편식', 
    icon: '🍢', 
    description: '김밥, 떡볶이 및 간편식',
    color: '#e11d48', // Rose Coral
    bgLight: 'rgba(225, 29, 72, 0.12)',
    ramp: ['#fb7185', '#f43f5e', '#e11d48', '#be123c', '#9f1239']
  },
  { 
    id: 'CAT_MAJ_07', 
    name: '카페·음료', 
    icon: '☕', 
    description: '커피 및 음료 전문점',
    color: '#9333ea', // Violet Purple
    bgLight: 'rgba(147, 51, 234, 0.12)',
    ramp: ['#c084fc', '#a855f7', '#9333ea', '#7e22ce', '#6b21a8']
  },
  { 
    id: 'CAT_MAJ_08', 
    name: '베이커리·디저트', 
    icon: '🥐', 
    description: '제과제빵 및 디저트·빙수',
    color: '#0891b2', // Cyan Teal
    bgLight: 'rgba(8, 145, 178, 0.12)',
    ramp: ['#22d3ee', '#06b6d4', '#0891b2', '#0e7490', '#155e75']
  },
  // 검토 보류 및 미매핑 예외 상태 검증용 탭
  { 
    id: 'CAT_MAJ_99', 
    name: '기타 외식 (미매핑)', 
    icon: '🔍', 
    description: '배타적 매핑 불가 업종', 
    isUnmapped: true,
    color: '#64748b', // Slate
    bgLight: 'rgba(100, 116, 139, 0.12)',
    ramp: ['#94a3b8', '#64748b', '#475569', '#334155', '#1e293b']
  }
];

const SIDO_SHORT_NAMES = {
  '00': '전국',
  '11': '서울',
  '26': '부산',
  '27': '대구',
  '28': '인천',
  '29': '광주',
  '30': '대전',
  '31': '울산',
  '36': '세종',
  '41': '경기',
  '42': '강원',
  '43': '충북',
  '44': '충남',
  '45': '전북',
  '46': '전남',
  '47': '경북',
  '48': '경남',
  '50': '제주'
};

export default function CategoryFilterBar({
  selectedCategory,
  onSelectCategory,
  midCategories = [],
  selectedMidCategory = null,
  onSelectMidCategory = null,
  midCategoriesLoading = false,
  yearsList = [],
  selectedYear,
  onSelectYear,
  yearsLoading = false,
  statusMeta = null,
  benchmarkData = null,
  sedaReferenceMonth = null,
  sedaProvenanceText = null,
  sidoList = [],
  selectedSido = '11',
  onSelectSido,
  sigunguList = [],
  selectedSigungu = '11215',
  onSelectSigungu,
  regionsLoading = false,
  isFtcDrawerOpen = false,
  onToggleFtcDrawer
}) {
  const activeMajorObj = CATEGORY_MAJOR_LIST.find((c) => c.id === selectedCategory);
  const showMidSubbar = Boolean(
    selectedCategory &&
    selectedCategory !== 'ALL' &&
    !activeMajorObj?.isUnmapped &&
    (midCategoriesLoading || midCategories.length > 0)
  );
  // 공정위 배지 상태 판정 (선택 연도의 결산연도는 같은 응답(bData)의 필드만 엄격히 사용하고 타 응답 폴백 차단)
  const bData = benchmarkData?.data;
  const ftcBenchmarkYear = bData ? bData.benchmark_year : (statusMeta?.latest_benchmark_year || null);
  const ftcFinancialYear = bData ? (bData.financial_year || null) : (statusMeta?.financial_year || null);
  const isFallback = Boolean(bData?.is_fallback_applied);

  let ftcTagText = '공정위 기준연도 확인 불가';
  let ftcTagTitle = '공정거래위원회 거시통계 기준연도 확인 불가';
  let ftcTagClass = 'tag-ftc tag-unverified';

  const finYearText = ftcFinancialYear ? `${ftcFinancialYear}년 결산` : '결산연도 확인 불가';

  if (ftcBenchmarkYear) {
    if (isFallback) {
      ftcTagText = `공정위 ${ftcBenchmarkYear}년 대체 (${finYearText})`;
      ftcTagTitle = bData?.fallback_reason || `이전 이용 가능 연도(${ftcBenchmarkYear}년 등록, ${finYearText})로 대체 표출 중`;
      ftcTagClass = 'tag-ftc tag-ftc-fallback';
    } else if (ftcBenchmarkYear === '2026') {
      ftcTagText = `공정위 2026년 등록 (${finYearText}) · 진행형 스냅샷`;
      ftcTagTitle = `공정위 2026년 등록 기준 (${finYearText}) 가맹본부 정기등록 진행형 스냅샷 (모집단 30% 미등록)`;
      ftcTagClass = 'tag-ftc tag-ftc-snapshot';
    } else if (ftcBenchmarkYear === '2025') {
      ftcTagText = `공정위 2025년 등록 (${finYearText}) · 최신 완결 후보`;
      ftcTagTitle = `공정위 2025년 등록 기준 (${finYearText}) 최신 완결 후보 (공식 행정 마감 여부 미확인)`;
      ftcTagClass = 'tag-ftc tag-ftc-candidate';
    } else {
      ftcTagText = `공정위 ${ftcBenchmarkYear}년 등록 (${finYearText})`;
      ftcTagTitle = `공정위 ${ftcBenchmarkYear}년 등록 기준 (${finYearText})`;
      ftcTagClass = 'tag-ftc';
    }
  }

  // 모바일 390px 화면용 초간결 공정위 태그 텍스트 (텍스트 말줄임 완전 방지)
  const mobileFtcTagText = ftcBenchmarkYear ? `공정위 ${ftcBenchmarkYear} ↗` : '공정위 ↗';

  const sedaText = sedaProvenanceText || (sedaReferenceMonth ? `소진공 ${sedaReferenceMonth} 공간 전수` : '소진공 기준월 확인 불가');
  const sedaTitle = sedaReferenceMonth 
    ? `소상공인시장진흥공단 ${sedaReferenceMonth} 외식업 점포 공간 전수 (개별 사업장 단위)` 
    : '소상공인시장진흥공단 데이터 기준월 확인 불가';

  return (
    <nav className="category-filter-bar" aria-label="외식업종, 지역 및 기준연도 선택 바">
      <div className="filter-bar-inner">
        {/* 1. 지역 선택기 (시도 / 시군구 2단계 드릴다운) */}
        <div className="region-selector-container" aria-label="분석 대상 지역 선택">
          <span className="region-section-label">지역 선택:</span>
          
          {/* 시도 드롭다운 (모바일 58px 폭 내 말줄임 차단을 위한 간결 명칭 적용) */}
          <div className="region-select-wrapper">
            <select
              id="sido-select"
              className="region-select-dropdown"
              value={selectedSido || '00'}
              onChange={(e) => onSelectSido && onSelectSido(e.target.value)}
              disabled={regionsLoading}
              aria-label="시도 행정구역 선택"
            >
              <option value="00">전국</option>
              {sidoList.map((sido) => (
                <option key={sido.region_code} value={sido.region_code}>
                  {SIDO_SHORT_NAMES[sido.region_code] || sido.region_name}
                </option>
              ))}
            </select>
            <span className="select-arrow" aria-hidden="true">▾</span>
          </div>

          {/* 시군구 드롭다운 */}
          <div className="region-select-wrapper">
            <select
              id="sigungu-select"
              className="region-select-dropdown"
              value={selectedSigungu || ''}
              onChange={(e) => onSelectSigungu && onSelectSigungu(e.target.value)}
              disabled={regionsLoading || selectedSido === '00' || sigunguList.length === 0}
              aria-label="시군구 기초자치단체 선택"
            >
              <option value="">{selectedSido === '00' ? '전국 단위 요약' : '시군구 전체 (시도 단위)'}</option>
              {sigunguList.map((sgg) => (
                <option key={sgg.region_code} value={sgg.region_code}>
                  {sgg.region_name}
                </option>
              ))}
            </select>
            <span className="select-arrow" aria-hidden="true">▾</span>
          </div>
        </div>

        {/* 2. 기준연도 선택기 (공정위 벤치마크) */}
        <div className="year-selector-container">
          <label htmlFor="ftc-year-select" className="year-select-label">
            공정위 연도:
          </label>
          <div className="year-select-wrapper">
            <select
              id="ftc-year-select"
              className="year-select-dropdown"
              value={selectedYear || ''}
              onChange={(e) => onSelectYear(e.target.value ? e.target.value : null)}
              disabled={yearsLoading || yearsList.length === 0}
              aria-label="공정위 등록 기준연도 선택"
            >
              <option value="">최신(자동)</option>
              {yearsList.map((item) => (
                <option key={item.benchmark_year} value={item.benchmark_year}>
                  {item.benchmark_year}년
                </option>
              ))}
            </select>
            <span className="select-arrow" aria-hidden="true">▾</span>
          </div>

          {/* 연도 선택 모드 뱃지 (자동 선택 vs 수동 지정) */}
          <span 
            className={`year-mode-pill ${selectedYear ? 'mode-manual' : 'mode-auto'}`}
            title={selectedYear ? '사용자가 연도를 직접 지정함 (이전 연도 대체 미적용)' : 'DB 기준 최신 연도 자동 판정 (필요 시 단일 이전 연도 자동 대체)'}
          >
            {selectedYear ? '직접 지정' : '자동 판정'}
          </span>
        </div>

        {/* 3. 데이터 정직성 출처 태그 (Provenance Badges) */}
        <div className="filter-provenance-tags" aria-label="데이터 원천 및 성격 명시">
          <span className={`provenance-tag tag-seda ${!sedaReferenceMonth ? 'tag-unverified' : ''}`} title={sedaTitle}>
            {sedaText}
          </span>
          <span 
            className={`provenance-tag ${ftcTagClass}`} 
            title={ftcTagTitle}
          >
            <span className="desktop-ftc-label">{ftcTagText}</span>
            <span className="mobile-ftc-label">{mobileFtcTagText}</span>
          </span>
        </div>

        {/* 4. 업종 탭 목록 */}
        <div className="category-tabs-container" role="tablist" aria-label="8대 외식업 대분류 목록">
          <span className="category-section-label" title="선택한 업종은 지도 점포, 점포 목록, 상위 브랜드에 적용됩니다">업종 필터:</span>
          <div className="category-tabs-scroll">
            {CATEGORY_MAJOR_LIST.map((cat) => {
              const isSelected = selectedCategory === cat.id;
              return (
                <button
                  key={cat.id}
                  role="tab"
                  id={`tab-${cat.id}`}
                  aria-selected={isSelected}
                  aria-controls="ftc-benchmark-panel"
                  className={`category-tab-btn ${isSelected ? 'active' : ''} ${cat.isUnmapped ? 'unmapped-tab' : ''}`}
                  style={isSelected ? { 
                    borderColor: cat.color, 
                    backgroundColor: cat.bgLight,
                    color: cat.color 
                  } : {}}
                  onClick={() => onSelectCategory(cat.id)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ' || e.key === 'Spacebar') {
                      e.preventDefault();
                      onSelectCategory(cat.id);
                    }
                  }}
                  tabIndex={0}
                  title={cat.description}
                >
                  <span className="tab-icon" aria-hidden="true">{cat.icon}</span>
                  <span className="tab-name" style={isSelected ? { fontWeight: 700 } : {}}>{cat.name}</span>
                  {isSelected && (
                    <span 
                      className="tab-active-indicator" 
                      aria-hidden="true" 
                      style={{ backgroundColor: cat.color }} 
                    />
                  )}
                </button>
              );
            })}
          </div>
        </div>
      </div>

      {/* 5. 48개 중분류 2단계 드릴다운 슬림 서브바 (8대 대분류 선택 시 자동 펼침) */}
      {showMidSubbar && (
        <div
          className="mid-category-subbar"
          role="tablist"
          aria-label={`${activeMajorObj?.name || '선택 업종'} 하위 중분류 필터`}
          style={{ '--major-color': activeMajorObj?.color || '#2563eb' }}
        >
          <span className="mid-subbar-label">
            <span className="mid-subbar-icon">{activeMajorObj?.icon}</span>
            <span>{activeMajorObj?.name} 중분류:</span>
          </span>
          <div className="mid-subbar-chips">
            <button
              type="button"
              role="tab"
              aria-selected={!selectedMidCategory}
              className={`mid-chip-btn ${!selectedMidCategory ? 'active' : ''}`}
              onClick={() => onSelectMidCategory && onSelectMidCategory(null)}
            >
              <span>전체 {activeMajorObj?.name}</span>
            </button>
            {midCategories.map((mid) => {
              const isMidActive = selectedMidCategory === mid.category_mid_id;
              return (
                <button
                  key={mid.category_mid_id}
                  type="button"
                  role="tab"
                  aria-selected={isMidActive}
                  className={`mid-chip-btn ${isMidActive ? 'active' : ''}`}
                  onClick={() =>
                    onSelectMidCategory &&
                    onSelectMidCategory(isMidActive ? null : mid.category_mid_id)
                  }
                  title={`${mid.category_mid_name}: 현재 지역 ${Number(mid.total_stores || 0).toLocaleString()}개소 (지역 비중 ${mid.category_share_pct ?? 0}%)`}
                >
                  <span className="mid-chip-name">{mid.category_mid_name}</span>
                  <span className="mid-chip-count">
                    {Number(mid.total_stores || 0).toLocaleString()}
                  </span>
                </button>
              );
            })}
          </div>
        </div>
      )}
    </nav>
  );
}
