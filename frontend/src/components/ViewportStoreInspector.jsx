import React, { memo, useCallback, useMemo, useState, useEffect, useRef } from 'react';
import { STORE_TYPE_META, getStoreType } from './MapContainer';
import { searchBrands, fetchBrandDistribution, fetchBrandStores } from '../services/api';
import { CATEGORY_MAJOR_LIST } from './CategoryFilterBar';

const PAGE_SIZE = 80;

const FILTERS = [
  { id: 'all', label: '전체', dotColor: null },
  { id: 'franchise', label: '프랜차이즈', dotColor: STORE_TYPE_META.franchise.color },
  { id: 'candidate', label: '후보', dotColor: STORE_TYPE_META.candidate.color },
  { id: 'indie', label: '독립', dotColor: STORE_TYPE_META.indie.color }
];

function getOfficialityMeta(officiality) {
  if (officiality === 'FRANCHISE_CONFIRMED') {
    return { label: '공식 가맹', className: 'franchise', color: STORE_TYPE_META.franchise.color };
  }
  if (officiality === 'BRAND_CONFIRMED') {
    return { label: '브랜드 확인', className: 'franchise', color: STORE_TYPE_META.franchise.color };
  }
  if (officiality === 'UNVERIFIED') {
    return { label: '브랜드 후보', className: 'candidate', color: STORE_TYPE_META.candidate.color };
  }
  return { label: '개인·독립', className: 'indie', color: STORE_TYPE_META.indie.color };
}

const StoreRow = memo(function StoreRow({ store, active, onSelect }) {
  const type = getStoreType(store);
  const meta = STORE_TYPE_META[type];
  const title = store.brch_nm ? `${store.bizes_nm} ${store.brch_nm}` : store.bizes_nm;
  const linked = type !== 'indie' && store.brand_name_std;
  return (
    <li>
      <button
        type="button"
        className={`vsi-row ${active ? 'active' : ''}`}
        onClick={() => onSelect(store)}
      >
        <span className="vsi-dot" style={{ backgroundColor: meta.color }} aria-hidden="true" />
        <span className="vsi-row-body">
          <span className="vsi-row-title">{title}</span>
          <span className="vsi-row-sub">
            {store.category_mid_name || store.category_major_name}
            {linked ? ` · ${store.brand_name_std}` : ''}
            {store.rdnm_adr ? ` · ${store.rdnm_adr}` : ''}
          </span>
        </span>
        <span className={`vsi-badge ${type}`}>{meta.label}</span>
      </button>
    </li>
  );
});

const BrandRow = memo(function BrandRow({ brand, regionName, isNationwide, onSelectBrand }) {
  const offMeta = getOfficialityMeta(brand.brand_officiality);
  const majorObj = CATEGORY_MAJOR_LIST.find((c) => c.id === brand.category_major_id);
  const regionCount = Number(brand.region_store_count ?? 0);
  const natCount = Number(brand.nationwide_store_count ?? 0);

  return (
    <li>
      <button
        type="button"
        className="vsi-row vsi-brand-row"
        onClick={() => onSelectBrand(brand)}
      >
        <span className="vsi-dot" style={{ backgroundColor: offMeta.color }} aria-hidden="true" />
        <span className="vsi-row-body">
          <span className="vsi-row-title">
            {brand.brand_name_std}
            {majorObj && (
              <span className="vsi-brand-cat-tag">
                {majorObj.icon} {majorObj.name}
              </span>
            )}
          </span>
          <span className="vsi-row-sub">
            전국 <strong>{natCount.toLocaleString()}</strong>개소
            {!isNationwide && (
              <>
                {' · '}
                {regionName || '선택 지역'} <strong>{regionCount.toLocaleString()}</strong>개소
              </>
            )}
            {brand.confirmed_franchisee_count > 0 && (
              <> · 확인 가맹점 {Number(brand.confirmed_franchisee_count).toLocaleString()}개</>
            )}
          </span>
        </span>
        <span className={`vsi-badge ${offMeta.className}`}>{offMeta.label}</span>
      </button>
    </li>
  );
});

/**
 * ViewportStoreInspector (통합 점포·전국 5,062개 브랜드 인텔리전스 인스펙터)
 * - [📍 화면 점포] 모드와 [🏷️ 브랜드 분석 (5,062)] 모드를 원클릭 전환
 * - 줌 레벨이 낮을 때(14 미만) 검색어를 입력하거나 좌측 Top 5 브랜드를 클릭해도
 *   "지도를 확대하세요"라는 막다른 안내 대신 해당 브랜드의 전국·시군구 분포와 실제 지점 목록을 즉시 제공
 */
function ViewportStoreInspector({
  stores = [],
  status = 'zoom-required',
  activeStoreId = null,
  onSelectStore,
  filter = 'all',
  onChangeFilter,
  query = '',
  onChangeQuery,
  categoryName = '',
  activeRegionCode = '00',
  selectedRegionName = '전국',
  selectedSido = '00',
  selectedSigungu = '',
  selectedCategoryId = null,
  selectedMidCategoryId = null,
  onNavigateRegion = null,
  inspectedBrandRequest = null
}) {
  const [inspectorMode, setInspectorMode] = useState('stores'); // 'stores' | 'brands'
  const [listOpen, setListOpen] = useState(false);
  const [visibleCount, setVisibleCount] = useState(PAGE_SIZE);

  // 전국 5,062개 브랜드 검색 상태
  const [brandResults, setBrandResults] = useState([]);
  const [brandTotalCount, setBrandTotalCount] = useState(0);
  const [brandLoading, setBrandLoading] = useState(false);

  // 선택된 브랜드 상세 (분포 차트 + 현재 지역 지점 목록)
  const [selectedBrand, setSelectedBrand] = useState(null);
  const [brandSubTab, setBrandSubTab] = useState('stores'); // 'stores' | 'distribution'
  const [distRegionType, setDistRegionType] = useState('SIGUNGU'); // 'SIGUNGU' | 'SIDO'
  const [brandDistData, setBrandDistData] = useState(null);
  const [brandDistLoading, setBrandDistLoading] = useState(false);
  const [brandStores, setBrandStores] = useState([]);
  const [brandStoresTotal, setBrandStoresTotal] = useState(0);
  const [brandStoresLoading, setBrandStoresLoading] = useState(false);

  const brandSearchAbortRef = useRef(null);
  const brandDetailAbortRef = useRef(null);

  const isNationwide = !activeRegionCode || activeRegionCode === '00';
  const trimmedQuery = query.trim().toLowerCase();

  // 검색어가 입력되면 드롭다운 목록을 자동으로 펼침
  useEffect(() => {
    if (query.trim().length > 0) {
      setListOpen(true);
      setVisibleCount(PAGE_SIZE);
    }
  }, [query]);

  // 대분류 또는 중분류 업종이 바뀌면 기존 고정 브랜드 상세창을 즉시 닫고 새 업종을 보여줌
  useEffect(() => {
    setSelectedBrand(null);
    setListOpen(false);
  }, [selectedCategoryId, selectedMidCategoryId]);

  // 외부(좌측 Top 5 브랜드 클릭 또는 지도 점포 팝업 내 '전국·지역 분포 보기' 버튼 클릭)에서 브랜드 분석 요청 시
  useEffect(() => {
    if (!inspectedBrandRequest || !inspectedBrandRequest.nonce) {
      setSelectedBrand(null);
      return;
    }
    setListOpen(true);
    setInspectorMode('brands');
    // 현재 지역이 선택된 경우 바로 지점 목록과 분포를 함께 열람할 수 있도록 세팅
    setBrandSubTab(isNationwide ? 'distribution' : 'stores');

    if (inspectedBrandRequest.internal_brand_id) {
      setSelectedBrand({
        internal_brand_id: inspectedBrandRequest.internal_brand_id,
        brand_name_std: inspectedBrandRequest.brand_name_std,
        brand_officiality: inspectedBrandRequest.brand_officiality || 'FRANCHISE_CONFIRMED',
        category_major_id: inspectedBrandRequest.category_major_id || selectedCategoryId,
        category_mid_id: inspectedBrandRequest.category_mid_id || selectedMidCategoryId,
        nationwide_store_count: inspectedBrandRequest.nationwide_store_count || inspectedBrandRequest.store_count || 0,
        region_store_count: inspectedBrandRequest.store_count || 0
      });
    } else if (inspectedBrandRequest.brand_name_std) {
      // internal_brand_id 없이 이름만 넘어온 경우 검색 API로 즉시 매칭
      searchBrands(
        {
          q: inspectedBrandRequest.brand_name_std,
          regionCode: activeRegionCode,
          limit: 5
        }
      )
        .then((res) => {
          const list = res.data || [];
          const exact = list.find((b) => b.brand_name_std === inspectedBrandRequest.brand_name_std) || list[0];
          if (exact) {
            setSelectedBrand(exact);
          }
        })
        .catch(() => {});
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [inspectedBrandRequest]);

  // 브랜드 검색 API 호출 (검색어 입력 시 또는 브랜드 모드일 때 180ms 디바운스)
  useEffect(() => {
    const shouldFetchBrands =
      inspectorMode === 'brands' ||
      trimmedQuery.length > 0 ||
      (listOpen && status === 'zoom-required');

    if (!shouldFetchBrands) return;

    const timer = setTimeout(() => {
      brandSearchAbortRef.current?.abort();
      const controller = new AbortController();
      brandSearchAbortRef.current = controller;

      setBrandLoading(true);
      const offParam =
        filter === 'franchise'
          ? 'FRANCHISE_CONFIRMED'
          : filter === 'candidate'
            ? 'UNVERIFIED'
            : null;

      searchBrands(
        {
          q: query.trim(),
          regionCode: activeRegionCode,
          categoryMajorId: selectedCategoryId,
          categoryMidId: selectedMidCategoryId,
          officiality: offParam,
          limit: 30
        },
        controller.signal
      )
        .then((res) => {
          if (!controller.signal.aborted) {
            setBrandResults(res.data || []);
            setBrandTotalCount(res.meta?.total_count ?? (res.data || []).length);
          }
        })
        .catch(() => {
          if (!controller.signal.aborted) {
            setBrandResults([]);
            setBrandTotalCount(0);
          }
        })
        .finally(() => {
          if (!controller.signal.aborted) {
            setBrandLoading(false);
          }
        });
    }, 160);

    return () => {
      clearTimeout(timer);
    };
  }, [
    inspectorMode,
    trimmedQuery,
    query,
    listOpen,
    status,
    activeRegionCode,
    selectedCategoryId,
    selectedMidCategoryId,
    filter
  ]);

  // 선택된 브랜드의 지역별 분포 및 현재 지역 내 지점 목록 로드
  useEffect(() => {
    if (!selectedBrand?.internal_brand_id) {
      setBrandDistData(null);
      setBrandStores([]);
      setBrandStoresTotal(0);
      return;
    }

    brandDetailAbortRef.current?.abort();
    const controller = new AbortController();
    brandDetailAbortRef.current = controller;

    setBrandDistLoading(true);
    setBrandStoresLoading(true);

    const storeFilters = {
      sidoCode: selectedSido && selectedSido !== '00' ? selectedSido : undefined,
      sigunguCode: selectedSigungu || undefined,
      limit: 100
    };

    Promise.allSettled([
      fetchBrandDistribution(selectedBrand.internal_brand_id, distRegionType, controller.signal),
      fetchBrandStores(selectedBrand.internal_brand_id, storeFilters, controller.signal)
    ]).then(([distRes, storesRes]) => {
      if (controller.signal.aborted) return;

      if (distRes.status === 'fulfilled') {
        setBrandDistData(distRes.value);
      } else {
        setBrandDistData(null);
      }
      setBrandDistLoading(false);

      if (storesRes.status === 'fulfilled') {
        setBrandStores(storesRes.value.data || []);
        setBrandStoresTotal(storesRes.value.meta?.total_count ?? (storesRes.value.data || []).length);
      } else {
        setBrandStores([]);
        setBrandStoresTotal(0);
      }
      setBrandStoresLoading(false);
    });

    return () => controller.abort();
  }, [selectedBrand, distRegionType, selectedSido, selectedSigungu]);

  // 검색어 기준 매칭 점포 (칩 카운트 계산용)
  const queryMatchedStores = useMemo(() => {
    if (!trimmedQuery) return stores;
    return stores.filter((s) => {
      const hay = `${s.bizes_nm || ''} ${s.brch_nm || ''} ${s.brand_name_std || ''} ${s.category_mid_name || ''}`.toLowerCase();
      return hay.includes(trimmedQuery);
    });
  }, [stores, trimmedQuery]);

  const counts = useMemo(() => {
    const c = { all: queryMatchedStores.length, franchise: 0, candidate: 0, indie: 0 };
    for (let i = 0; i < queryMatchedStores.length; i++) {
      c[getStoreType(queryMatchedStores[i])]++;
    }
    return c;
  }, [queryMatchedStores]);

  const filtered = useMemo(() => {
    const list = filter === 'all'
      ? queryMatchedStores
      : queryMatchedStores.filter((s) => getStoreType(s) === filter);
    const order = { franchise: 0, candidate: 1, indie: 2 };
    return [...list].sort((a, b) => {
      const d = order[getStoreType(a)] - order[getStoreType(b)];
      if (d !== 0) return d;
      return (a.bizes_nm || '').localeCompare(b.bizes_nm || '', 'ko');
    });
  }, [queryMatchedStores, filter]);

  const handleSelectStore = useCallback((store) => {
    if (onSelectStore) onSelectStore(store);
  }, [onSelectStore]);

  const handleSelectBrand = useCallback((brand) => {
    setSelectedBrand(brand);
    setInspectorMode('brands');
    setListOpen(true);
    setBrandSubTab(!isNationwide && (brand.region_store_count ?? 0) > 0 ? 'stores' : 'distribution');
  }, [isNationwide]);

  const handleFilterClick = useCallback((id) => {
    if (onChangeFilter) onChangeFilter(id);
    setVisibleCount(PAGE_SIZE);
  }, [onChangeFilter]);

  const shown = filtered.slice(0, visibleCount);
  const isDropdownVisible = listOpen || trimmedQuery.length > 0 || Boolean(selectedBrand);

  const distList = useMemo(() => {
    return (brandDistData?.distribution || []).slice(0, 12);
  }, [brandDistData]);

  const maxDistCount = useMemo(() => {
    if (distList.length === 0) return 1;
    return Math.max(...distList.map((d) => d.discovered_store_count || 0), 1);
  }, [distList]);

  const brandInfo = brandDistData?.brand_info || selectedBrand;
  const brandOffMeta = brandInfo ? getOfficialityMeta(brandInfo.brand_officiality) : null;

  return (
    <div className="vsi-topbar-wrap desktop-only" role="search" aria-label="지도 점포 및 전국 브랜드 통합 검색">
      {/* 1줄 슬림 컨트롤 바 */}
      <div className="vsi-topbar">
        {/* 좌측 모드 전환 스위치: [📍 화면 점포] ↔ [🏷️ 브랜드 분석] */}
        <div className="vsi-mode-switch" role="tablist" aria-label="탐색 모드 선택">
          <button
            type="button"
            role="tab"
            aria-selected={inspectorMode === 'stores'}
            className={`vsi-mode-btn ${inspectorMode === 'stores' ? 'active' : ''}`}
            onClick={() => {
              setInspectorMode('stores');
              setSelectedBrand(null);
              setListOpen(true);
            }}
            title="현재 지도 화면 안의 개별 점포 탐색"
          >
            화면 점포
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={inspectorMode === 'brands'}
            className={`vsi-mode-btn ${inspectorMode === 'brands' ? 'active' : ''}`}
            onClick={() => {
              setInspectorMode('brands');
              setListOpen(true);
            }}
            title="전국 5,062개 브랜드의 지역별 분포 및 실제 지점 목록 검색"
          >
            브랜드 탐색
          </button>
        </div>

        <div className="vsi-topbar-divider" />

        <div className="vsi-search-wrap">
          <span className="vsi-search-icon" aria-hidden="true">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
          </span>
          <input
            type="text"
            className="vsi-search-input"
            placeholder={
              inspectorMode === 'brands'
                ? '전국 5,062개 브랜드 검색 (예: 스타벅스, 메가, 교촌)'
                : categoryName
                  ? `${categoryName} 상호·브랜드 검색`
                  : '상호·브랜드 검색 (예: 스타벅스)'
            }
            value={query}
            onChange={(e) => {
              if (selectedBrand) setSelectedBrand(null);
              if (onChangeQuery) onChangeQuery(e.target.value);
            }}
            onFocus={() => setListOpen(true)}
            aria-label="점포 상호 또는 브랜드 검색"
          />
          {query && (
            <button
              type="button"
              className="vsi-search-clear"
              onClick={() => {
                setSelectedBrand(null);
                if (onChangeQuery) onChangeQuery('');
              }}
              aria-label="검색어 지우기"
              title="검색어 지우기"
            >
              ✕
            </button>
          )}
        </div>

        <div className="vsi-topbar-divider" />

        <div className="vsi-chips" role="tablist" aria-label="지도 점포 유형 필터">
          {FILTERS.map((f) => {
            const active = filter === f.id;
            const cnt = counts[f.id] ?? 0;
            return (
              <button
                key={f.id}
                type="button"
                role="tab"
                aria-selected={active}
                className={`vsi-chip ${active ? 'active' : ''}`}
                onClick={() => handleFilterClick(f.id)}
                title={`${f.label} 점포만 지도에 표시`}
              >
                {f.dotColor && (
                  <span className="vsi-chip-dot" style={{ backgroundColor: f.dotColor }} />
                )}
                <span>{f.label}</span>
                {status !== 'zoom-required' && status !== 'hidden' && (
                  <strong className="vsi-chip-count">{cnt.toLocaleString()}</strong>
                )}
              </button>
            );
          })}
        </div>

        <div className="vsi-topbar-divider" />

        <button
          type="button"
          className={`vsi-list-toggle ${isDropdownVisible ? 'open' : ''}`}
          onClick={() => setListOpen((prev) => !prev)}
          aria-expanded={isDropdownVisible}
          title={isDropdownVisible ? '탐색 패널 접기' : '점포 및 브랜드 탐색 패널 펼치기'}
        >
          <span>
            {isDropdownVisible
              ? '접기 ▴'
              : inspectorMode === 'brands'
                ? `브랜드 (${brandTotalCount.toLocaleString()}) ▾`
                : `목록 (${filtered.length.toLocaleString()}) ▾`}
          </span>
        </button>
      </div>

      {/* 아래로 펼쳐지는 통합 드롭다운 인스펙터 */}
      {isDropdownVisible && (
        <div className="vsi-dropdown" aria-label="점포 및 브랜드 인텔리전스 패널">
          {/* A. 특정 브랜드가 선택된 경우: 브랜드 세력권 분석 & 지점 바로가기 뷰 */}
          {selectedBrand ? (
            <div className="vsi-brand-detail-view">
              <div className="vsi-dropdown-header vsi-brand-detail-header">
                <button
                  type="button"
                  className="vsi-back-btn"
                  onClick={() => setSelectedBrand(null)}
                >
                  ← 브랜드 목록
                </button>
                <div className="vsi-brand-detail-title-wrap">
                  <strong className="vsi-brand-detail-name">{brandInfo?.brand_name_std}</strong>
                  {brandOffMeta && (
                    <span className={`vsi-badge ${brandOffMeta.className}`}>{brandOffMeta.label}</span>
                  )}
                </div>
                <button
                  type="button"
                  className="vsi-dropdown-close"
                  onClick={() => {
                    setSelectedBrand(null);
                    setListOpen(false);
                    if (trimmedQuery && onChangeQuery) onChangeQuery('');
                  }}
                >
                  닫기 ✕
                </button>
              </div>

              {/* 브랜드 핵심 KPI 요약 배너 */}
              <div className="vsi-brand-kpi-strip">
                <div className="vsi-brand-kpi-item">
                  <span className="vsi-brand-kpi-label">전국 총 점포</span>
                  <strong className="vsi-brand-kpi-val">
                    {Number(brandInfo?.nationwide_store_count || 0).toLocaleString()}개소
                  </strong>
                </div>
                <div className="vsi-brand-kpi-item">
                  <span className="vsi-brand-kpi-label">{selectedRegionName || '현재 지역'} 지점</span>
                  <strong className="vsi-brand-kpi-val highlight">
                    {brandStoresLoading
                      ? '...'
                      : `${Number(brandStoresTotal || 0).toLocaleString()}개소`}
                  </strong>
                </div>
                <div className="vsi-brand-kpi-item">
                  <span className="vsi-brand-kpi-label">확인 가맹점</span>
                  <strong className="vsi-brand-kpi-val">
                    {Number(brandInfo?.confirmed_franchisee_count || 0).toLocaleString()}개소
                  </strong>
                </div>
              </div>

              {/* 서브 탭: [현재 지역 지점 목록] ↔ [전국 지역별 분포 Top 12] */}
              <div className="vsi-brand-subtabs">
                <button
                  type="button"
                  className={`vsi-subtab-btn ${brandSubTab === 'stores' ? 'active' : ''}`}
                  onClick={() => setBrandSubTab('stores')}
                >
                  {selectedRegionName || '전국'} 실제 지점 ({brandStoresTotal.toLocaleString()}개)
                </button>
                <button
                  type="button"
                  className={`vsi-subtab-btn ${brandSubTab === 'distribution' ? 'active' : ''}`}
                  onClick={() => setBrandSubTab('distribution')}
                >
                  전국 시도·시군구 분포 Top 12
                </button>
              </div>

              <div className="vsi-body">
                {brandSubTab === 'stores' ? (
                  brandStoresLoading ? (
                    <div className="vsi-empty">지점 목록을 불러오는 중…</div>
                  ) : brandStores.length === 0 ? (
                    <div className="vsi-empty">
                      현재 선택된 <strong>{selectedRegionName}</strong>에는{' '}
                      <strong>{brandInfo?.brand_name_std}</strong> 지점이 없습니다.
                      <button
                        type="button"
                        className="vsi-reset-inline"
                        onClick={() => setBrandSubTab('distribution')}
                      >
                        전국 최다 분포 지역 보기
                      </button>
                    </div>
                  ) : (
                    <>
                      <div className="vsi-sub-hint">
                        지점을 클릭하면 수동으로 지도를 확대할 필요 없이 해당 매장 위치로 즉시 줌인합니다.
                      </div>
                      <ul className="vsi-list">
                        {brandStores.map((s) => (
                          <StoreRow
                            key={s.bizes_id}
                            store={s}
                            active={s.bizes_id === activeStoreId}
                            onSelect={handleSelectStore}
                          />
                        ))}
                      </ul>
                    </>
                  )
                ) : (
                  <div className="vsi-dist-section">
                    <div className="vsi-dist-toolbar">
                      <span className="vsi-dist-toolbar-title">
                        어느 지역에 가장 많이 입점해 있는가? (클릭 시 지역 이동)
                      </span>
                      <div className="vsi-dist-toggle">
                        <button
                          type="button"
                          className={`vsi-dist-toggle-btn ${distRegionType === 'SIGUNGU' ? 'active' : ''}`}
                          onClick={() => setDistRegionType('SIGUNGU')}
                        >
                          256개 시군구
                        </button>
                        <button
                          type="button"
                          className={`vsi-dist-toggle-btn ${distRegionType === 'SIDO' ? 'active' : ''}`}
                          onClick={() => setDistRegionType('SIDO')}
                        >
                          17개 시도
                        </button>
                      </div>
                    </div>

                    {brandDistLoading ? (
                      <div className="vsi-empty">지역별 브랜드 분포를 분석 중...</div>
                    ) : distList.length === 0 ? (
                      <div className="vsi-empty">분포 데이터가 없습니다.</div>
                    ) : (
                      <div className="vsi-dist-bars">
                        {distList.map((item, idx) => {
                          const widthPct = Math.min(
                            100,
                            Math.max(5, ((item.discovered_store_count || 0) / maxDistCount) * 100)
                          );
                          const isCurrentRegion = item.region_code === activeRegionCode;
                          return (
                            <button
                              type="button"
                              key={item.region_code}
                              className={`vsi-dist-bar-row ${isCurrentRegion ? 'active' : ''}`}
                              onClick={() => {
                                if (onNavigateRegion) {
                                  onNavigateRegion(item.region_code, distRegionType);
                                  setBrandSubTab('stores');
                                }
                              }}
                              title={`${item.region_name} 클릭 시 해당 지역으로 이동하여 지점 확인`}
                            >
                              <div className="vsi-dist-row-top">
                                <span className="vsi-dist-region-name">
                                  <span className="vsi-dist-rank">{idx + 1}</span>
                                  {item.region_name}
                                  {item.rank_in_region ? (
                                    <span className="vsi-dist-inregion-badge">
                                      지역 내 {item.rank_in_region}위
                                    </span>
                                  ) : null}
                                </span>
                                <span className="vsi-dist-region-meta">
                                  <strong>{Number(item.discovered_store_count || 0).toLocaleString()}</strong>개소
                                  <span className="vsi-dist-share">
                                    (업종 내 {item.category_share_in_region ?? 0}%)
                                  </span>
                                </span>
                              </div>
                              <div className="vsi-dist-track">
                                <div
                                  className="vsi-dist-fill"
                                  style={{ width: `${widthPct}%` }}
                                />
                              </div>
                            </button>
                          );
                        })}
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          ) : inspectorMode === 'brands' ? (
            /* B. [🏷️ 브랜드 탐색] 모드: 전국 5,062개 브랜드 검색 및 선택 지역 점포 수 비교 */
            <>
              <div className="vsi-dropdown-header">
                <span>
                  {trimmedQuery ? `'${query.trim()}' 브랜드 검색 ` : `${selectedRegionName} 주요 브랜드 `}
                  <strong>{brandTotalCount.toLocaleString()}</strong>개 브랜드
                  {categoryName ? ` · ${categoryName}` : ''}
                </span>
                <button
                  type="button"
                  className="vsi-dropdown-close"
                  onClick={() => {
                    setListOpen(false);
                    if (trimmedQuery && onChangeQuery) onChangeQuery('');
                  }}
                >
                  닫기 ✕
                </button>
              </div>
              <div className="vsi-body">
                <div className="vsi-sub-hint">
                  브랜드를 클릭하면 <strong>전국 256개 시군구 분포</strong>와{' '}
                  <strong>{selectedRegionName} 실제 지점 목록(도로명주소)</strong>을 즉시 확인할 수 있습니다.
                </div>
                {brandLoading && brandResults.length === 0 ? (
                  <div className="vsi-empty">브랜드를 검색하는 중…</div>
                ) : brandResults.length === 0 ? (
                  <div className="vsi-empty">조건에 맞는 브랜드가 없습니다.</div>
                ) : (
                  <ul className="vsi-list">
                    {brandResults.map((b) => (
                      <BrandRow
                        key={b.internal_brand_id}
                        brand={b}
                        regionName={selectedRegionName}
                        isNationwide={isNationwide}
                        onSelectBrand={handleSelectBrand}
                      />
                    ))}
                  </ul>
                )}
              </div>
            </>
          ) : (
            /* C. [화면 점포] 모드 + 스마트 브랜드 브릿지 (줌 < 14이거나 검색어 입력 시 브랜드 즉시 연결) */
            <>
              <div className="vsi-dropdown-header">
                <span>
                  {trimmedQuery ? `'${query.trim()}' 화면 내 점포 ` : '현재 화면 점포 '}
                  <strong>{filtered.length.toLocaleString()}</strong>개소
                  {categoryName ? ` · ${categoryName}` : ''}
                </span>
                <button
                  type="button"
                  className="vsi-dropdown-close"
                  onClick={() => {
                    setListOpen(false);
                    if (trimmedQuery && onChangeQuery) onChangeQuery('');
                  }}
                >
                  닫기 ✕
                </button>
              </div>

              <div className="vsi-body">
                {/* 줌이 낮거나(< 14) 검색어가 있을 때 일치하는 브랜드가 있으면 상단에 즉시 브랜드 브릿지 노출 */}
                {(status === 'zoom-required' || trimmedQuery.length > 0) && brandResults.length > 0 && (
                  <div className="vsi-smart-brand-bridge">
                    <div className="vsi-bridge-header">
                      <span>
                        <strong>{trimmedQuery ? `'${query.trim()}' 매칭 브랜드` : `${selectedRegionName} 대표 브랜드`}</strong>
                        : 클릭 시 지도를 직접 확대하지 않아도 지점 위치·전국 분포를 바로 봅니다
                      </span>
                    </div>
                    <ul className="vsi-list vsi-bridge-list">
                      {brandResults.slice(0, trimmedQuery ? 5 : 4).map((b) => (
                        <BrandRow
                          key={b.internal_brand_id}
                          brand={b}
                          regionName={selectedRegionName}
                          isNationwide={isNationwide}
                          onSelectBrand={handleSelectBrand}
                        />
                      ))}
                    </ul>
                  </div>
                )}

                {status === 'zoom-required' && (
                  <div className="vsi-empty">
                    개별 골목 점포 전체 핀은 지도를 14단계 이상 확대하면 표시됩니다.
                    <br />
                    위 <strong>브랜드 항목을 클릭</strong>하면 지금 바로 <strong>{selectedRegionName}</strong> 내 실제 지점 목록과 위치로 이동할 수 있습니다.
                  </div>
                )}
                {status === 'hidden' && (
                  <div className="vsi-empty">우측 레일에서 [점포] 레이어가 꺼져 있습니다.</div>
                )}
                {status === 'loading' && stores.length === 0 && (
                  <div className="vsi-empty">점포를 불러오는 중...</div>
                )}
                {status === 'error' && (
                  <div className="vsi-empty">점포를 불러오지 못했습니다.</div>
                )}
                {status !== 'zoom-required' && status !== 'hidden' && status !== 'error' && stores.length === 0 && status !== 'loading' && (
                  <div className="vsi-empty">현재 화면·업종에 해당하는 점포가 없습니다.</div>
                )}
                {stores.length > 0 && filtered.length === 0 && (
                  <div className="vsi-empty">
                    현재 지도 화면 안에는 조건에 맞는 점포가 없습니다.
                    {(filter !== 'all' || trimmedQuery) && (
                      <button
                        type="button"
                        className="vsi-reset-inline"
                        onClick={() => {
                          if (onChangeFilter) onChangeFilter('all');
                          if (onChangeQuery) onChangeQuery('');
                        }}
                      >
                        필터 초기화
                      </button>
                    )}
                  </div>
                )}
                {shown.length > 0 && (
                  <ul className="vsi-list">
                    {shown.map((s) => (
                      <StoreRow
                        key={s.bizes_id}
                        store={s}
                        active={s.bizes_id === activeStoreId}
                        onSelect={handleSelectStore}
                      />
                    ))}
                  </ul>
                )}
                {filtered.length > shown.length && (
                  <button
                    type="button"
                    className="vsi-more"
                    onClick={() => setVisibleCount((c) => c + PAGE_SIZE)}
                  >
                    {(filtered.length - shown.length).toLocaleString()}개 더 보기
                  </button>
                )}
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}

export default memo(ViewportStoreInspector);
