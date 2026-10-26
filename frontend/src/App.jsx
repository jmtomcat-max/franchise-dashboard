import React, { useState, useEffect, useCallback, useRef } from 'react';
import Header from './components/Header';
import CategoryFilterBar, { CATEGORY_MAJOR_LIST } from './components/CategoryFilterBar';
import MarketSummary from './components/MarketSummary';
import MapContainer from './components/MapContainer';
import HotspotsPanel from './components/HotspotsPanel';
import ViewportStoreInspector from './components/ViewportStoreInspector';
import FtcBenchmarkPanel from './components/FtcBenchmarkPanel';
import DashboardHome from './components/DashboardHome';
import CinematicIntro from './components/CinematicIntro';
import UserGuideModal from './components/UserGuideModal';
import { 
  fetchSummary, 
  fetchGridDensity, 
  fetchHotspots, 
  fetchFtcStatus, 
  fetchFtcBenchmark, 
  fetchFtcTrends, 
  fetchFtcYears, 
  fetchRegions,
  fetchRegionDetail,
  fetchMajorCategoryDetail,
  BASE_URL 
} from './services/api';

export default function App() {
  // 1. 전국 총괄 요약 통계 상태 관리
  const [summaryData, setSummaryData] = useState(null);
  const [summaryMeta, setSummaryMeta] = useState(null);
  const [summaryLoading, setSummaryLoading] = useState(true);
  const [summaryError, setSummaryError] = useState(null);

  // 2. 지역 선택 및 드릴다운 상태 관리 (시도 / 시군구)
  const [sidoList, setSidoList] = useState([]);
  const [sigunguList, setSigunguList] = useState([]);
  const [selectedSido, setSelectedSido] = useState('00'); // 기본: 대한민국 전국 (735,185건 총괄)
  const [selectedSigungu, setSelectedSigungu] = useState(''); // 기본: 시군구 미지정
  const [regionsLoading, setRegionsLoading] = useState(false);

  const [regionDetail, setRegionDetail] = useState(null);
  const [nationalRegionDetail, setNationalRegionDetail] = useState(null);
  const [regionLoading, setRegionLoading] = useState(true);
  const [regionError, setRegionError] = useState(null);

  // 현재 활성 분석 지역 코드 (시군구 지정 시 시군구, 아니면 시도, '00'이면 전국)
  const activeRegionCode = selectedSigungu || (selectedSido !== '00' ? selectedSido : '00');
  const isNationwide = activeRegionCode === '00';

  // 3. 지도 격자, 광역 버블 마커 및 핫스팟 상태 관리
  const [gridData, setGridData] = useState([]);
  const [gridLoading, setGridLoading] = useState(true);
  const [gridError, setGridError] = useState(null);
  const [macroBubbles, setMacroBubbles] = useState([]);
  const [macroBubblesLoading, setMacroBubblesLoading] = useState(false);

  const [hotspots, setHotspots] = useState([]);
  const [hotspotsLoading, setHotspotsLoading] = useState(true);
  const [hotspotsError, setHotspotsError] = useState(null);

  const [selectedHotspot, setSelectedHotspot] = useState(null);
  const [isRefreshing, setIsRefreshing] = useState(false);

  // 0. 화면 모드 관리: 'dashboard' (기본 홈 대시보드) vs 'map' (3D GIS 상권 지도)
  const urlParams = typeof window !== 'undefined' ? new URLSearchParams(window.location.search) : null;
  const initialViewMode = (urlParams && urlParams.get('view')) === 'map' ? 'map' : 'dashboard';
  const [viewMode, setViewMode] = useState(initialViewMode);

  // 0-1. 대문 시네마틱 인트로 영상 상태 관리 (당일 숨김 localStorage 및 intro URL 파라미터 연동)
  const [showIntro, setShowIntro] = useState(() => {
    if (typeof window !== 'undefined') {
      const p = new URLSearchParams(window.location.search);
      if (p.get('intro') === 'true') return true;
      if (p.get('intro') === 'false') return false;
      try {
        const hideDate = localStorage.getItem('hide_cinematic_intro_date');
        const todayStr = new Date().toISOString().slice(0, 10);
        if (hideDate === todayStr) {
          return false;
        }
      } catch (e) {
        // localStorage 예외 무시
      }
    }
    return true; // 첫 접속 시 대문 영상 기본 노출
  });

  const handleCloseIntro = useCallback(() => {
    setShowIntro(false);
  }, []);

  const handleExploreDashboardFromIntro = useCallback(() => {
    setViewMode('dashboard');
    setShowIntro(false);
  }, []);

  const handleExplore3DMapFromIntro = useCallback(() => {
    setViewMode('map');
    setShowIntro(false);
  }, []);

  const handleOpenIntro = useCallback(() => {
    setShowIntro(true);
  }, []);

  // 사용자 가이드 및 용어 사전 모달 팝업 상태 관리 (중앙 모달)
  const [showGuideModal, setShowGuideModal] = useState(false);
  const handleOpenGuideModal = useCallback(() => {
    setShowGuideModal(true);
  }, []);
  const handleCloseGuideModal = useCallback(() => {
    setShowGuideModal(false);
  }, []);

  // 4. 공정위 거시통계 상태 관리 (업종·연도 필터 연동) 및 48개 중분류 드릴다운 상태
  const initialCategory = (urlParams && urlParams.get('category')) || 'ALL';
  const [selectedCategory, setSelectedCategory] = useState(initialCategory); // 기본: 전체 업종
  const [selectedMidCategory, setSelectedMidCategory] = useState(null); // 48개 중분류 필터 (null = 대분류 전체)
  const [midCategories, setMidCategories] = useState([]);
  const [nationalMidCategories, setNationalMidCategories] = useState([]);
  const [midCategoriesLoading, setMidCategoriesLoading] = useState(false);

  const isAllCategory = selectedCategory === 'ALL';
  const categoryFilterId = isAllCategory ? null : selectedCategory; // API/지도 필터용 (전체=필터 없음)

  const handleSelectCategory = useCallback((catId) => {
    setSelectedCategory(catId);
    setSelectedMidCategory(null);
    setStoreSearchQuery('');
    setInspectedBrandRequest(null);
  }, []);

  const handleSelectMidCategory = useCallback((midId) => {
    setSelectedMidCategory(midId);
    setStoreSearchQuery('');
    setInspectedBrandRequest(null);
  }, []);

  // 상위 브랜드: 업종 필터와 연동 (지역 격자/통계 로딩과 분리해 업종 전환 시 지도가 초기화되지 않도록 함)
  const [topBrandsState, setTopBrandsState] = useState({ list: [], loading: false, error: null });
  const [selectedYear, setSelectedYear] = useState(null); // 기본: null (DB 최신연도 자동 조회)
  
  const [ftcStatusMeta, setFtcStatusMeta] = useState(null);
  const [yearsList, setYearsList] = useState([]);
  const [yearsLoading, setYearsLoading] = useState(true);

  const [benchmarkData, setBenchmarkData] = useState(null);
  const [trendsData, setTrendsData] = useState(null);
  const [ftcLoading, setFtcLoading] = useState(true);
  const [ftcError, setFtcError] = useState(null);

  // 5. 공정위 전국 벤치마크 드로어 및 핫스팟 팝오버 상태 (기본: 닫힘 상태로 지도를 가리지 않음)
  const initialFtcOpen = urlParams && urlParams.get('ftc_open') === 'true';
  const [isFtcDrawerOpen, setIsFtcDrawerOpen] = useState(initialFtcOpen);
  const [isHotspotsVisible, setIsHotspotsVisible] = useState(false);

  // 6. 현재 지도 화면 점포 검색·필터 바 상태
  const [visibleStores, setVisibleStores] = useState([]);
  const [storeStatus, setStoreStatus] = useState('zoom-required');
  const [activeStoreId, setActiveStoreId] = useState(null);
  const [focusStoreRequest, setFocusStoreRequest] = useState(null);
  const [storeTypeFilter, setStoreTypeFilter] = useState('all');
  const [storeSearchQuery, setStoreSearchQuery] = useState('');
  const [inspectedBrandRequest, setInspectedBrandRequest] = useState(null);
  const focusNonceRef = useRef(0);
  const brandNonceRef = useRef(0);

  // 요청 취소 컨트롤러 Refs 및 요청 순번 추적 (Race Condition 방지)
  const abortControllerRef = useRef(null);
  const ftcAbortRef = useRef(null);
  const regionAbortRef = useRef(null);
  const regionReqIdRef = useRef(0);
  const sidoAbortRef = useRef(null);
  const sidoReqIdRef = useRef(0);
  const [gridRetryKey, setGridRetryKey] = useState(0);

  // 시도 및 초기 시군구 목록 로드 (1회 실행)
  useEffect(() => {
    let isMounted = true;
    async function loadSidosAndInitialSigungus() {
      setRegionsLoading(true);
      try {
        const [sidoRes, sggRes] = await Promise.all([
          fetchRegions('SIDO'),
          fetchRegions('SIGUNGU', '11')
        ]);
        if (isMounted) {
          setSidoList(sidoRes.data || []);
          setSigunguList(sggRes.data || []);
        }
      } catch (e) {
        // 무시
      } finally {
        if (isMounted) {
          setRegionsLoading(false);
        }
      }
    }
    loadSidosAndInitialSigungus();
    return () => {
      isMounted = false;
    };
  }, []);

  // 시도 선택 핸들러 (연속 선택 경쟁 상태 방지 및 시군구 목록 즉시 분리)
  const handleSelectSido = useCallback((sidoCode) => {
    if (sidoAbortRef.current) {
      sidoAbortRef.current.abort();
    }
    const controller = new AbortController();
    sidoAbortRef.current = controller;
    const signal = controller.signal;
    const reqId = ++sidoReqIdRef.current;

    setSelectedSido(sidoCode);
    setSelectedSigungu(''); // 시군구 선택 리셋
    setSigunguList([]); // 이전 시도의 시군구 목록 즉시 비우기 (화면 분리)

    if (sidoCode === '00') {
      setRegionsLoading(false);
      return;
    }

    setRegionsLoading(true);

    async function loadSigungus() {
      try {
        const res = await fetchRegions('SIGUNGU', sidoCode, signal);
        if (reqId === sidoReqIdRef.current) {
          setSigunguList(res.data || []);
        }
      } catch (e) {
        if (reqId === sidoReqIdRef.current && e?.name !== 'AbortError') {
          setSigunguList([]);
        }
      } finally {
        if (reqId === sidoReqIdRef.current) {
          setRegionsLoading(false);
        }
      }
    }
    loadSigungus();
  }, []);

  // 시군구 선택 핸들러
  const handleSelectSigungu = useCallback((sigunguCode) => {
    setSelectedSigungu(sigunguCode);
  }, []);

  // 활성 지역 변경 시 지역 상세 및 격자 데이터 로드 (지역 선택 즉시 화면 분리 및 응답 확정 후 반영)
  useEffect(() => {
    if (regionAbortRef.current) {
      regionAbortRef.current.abort();
    }
    const controller = new AbortController();
    regionAbortRef.current = controller;
    const signal = controller.signal;

    // 순차 요청 카운터 증가 (오래된 비동기 응답이 새 지역 지도를 덮어쓰지 않도록 차단)
    const reqId = ++regionReqIdRef.current;

    // [핵심 보완 원칙 1: 지역 선택 즉시 이전 지역의 격자·상세 정보 화면 분리]
    setRegionDetail(null);
    setGridData([]);
    setRegionError(null);
    setGridError(null);
    setSelectedHotspot((prev) => {
      if (prev && (prev.sigungu_code === activeRegionCode || prev.sido_code === activeRegionCode)) {
        return prev;
      }
      return null;
    });

    // 1) 전국('00') 단위인 경우: 100m 정밀 격자는 미제공하되 전국 8대 업종 구성 및 상위 브랜드 상세 로드
    if (activeRegionCode === '00') {
      setGridLoading(false);
      setRegionLoading(true);
      fetchRegionDetail('00', signal)
        .then((detail) => {
          if (reqId === regionReqIdRef.current) {
            setRegionDetail(detail);
          }
        })
        .catch(() => {})
        .finally(() => {
          if (reqId === regionReqIdRef.current) {
            setRegionLoading(false);
          }
        });
      return;
    }

    // 2) 시도(길이 2) 단위인 경우: 시군구 드릴다운 안내 표기 (수만 개 격자 과부하 방지)
    const isSido = activeRegionCode.length === 2;

    setRegionLoading(true);
    setGridLoading(false);

    if (isSido) {
      async function loadSidoDetail() {
        try {
          const detail = await fetchRegionDetail(activeRegionCode, signal);
          if (reqId === regionReqIdRef.current) {
            setRegionDetail(detail);
          }
        } catch (e) {
          if (reqId === regionReqIdRef.current && e?.name !== 'AbortError') {
            setRegionError(`지역 통계 로드 실패: ${e?.message || '응답 오류'}`);
          }
        } finally {
          if (reqId === regionReqIdRef.current) {
            setRegionLoading(false);
          }
        }
      }
      loadSidoDetail();
      return;
    }

    // 3) 시군구(길이 5) 단위인 경우: 실제 100m 정밀 밀집도 격자 조회 (제주시 1,351개 등 전수 수용 limit=1500)
    setRegionLoading(true);
    setGridLoading(true);

    async function loadSigunguData() {
      try {
        const [detailRes, gridRes] = await Promise.allSettled([
          fetchRegionDetail(activeRegionCode, signal),
          fetchGridDensity(activeRegionCode, signal, 1500, categoryFilterId)
        ]);

        // 다른 지역이 이미 선택된 경우 이전 지연 응답 엄격 폐기
        if (reqId !== regionReqIdRef.current) return;

        // 지역 종합 통계 처리
        if (detailRes.status === 'fulfilled') {
          setRegionDetail(detailRes.value);
        } else if (detailRes.reason?.name !== 'AbortError') {
          setRegionError(`지역 통계 로드 실패: ${detailRes.reason?.message || '응답 오류'}`);
        }

        // 100m 정밀 밀집도 격자 처리 (새 지역 응답이 확정된 뒤에만 gridData 반영)
        if (gridRes.status === 'fulfilled') {
          const items = gridRes.value.data || [];
          setGridData(items);
          setGridError(null);
        } else if (gridRes.reason?.name !== 'AbortError') {
          setGridData([]);
          setGridError(gridRes.reason?.message || '격자 데이터 조회 실패');
        }
      } catch (e) {
        // 무시
      } finally {
        if (reqId === regionReqIdRef.current) {
          setRegionLoading(false);
          setGridLoading(false);
        }
      }
    }

    loadSigunguData();

    return () => {
      controller.abort();
    };
  }, [activeRegionCode, gridRetryKey]);

  // 기본 소상공인 요약 및 핫스팟 데이터 로드
  const loadMapData = useCallback(async () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    const controller = new AbortController();
    abortControllerRef.current = controller;
    const signal = controller.signal;

    setIsRefreshing(true);
    setSummaryLoading(true);
    setHotspotsLoading(true);

    try {
      const results = await Promise.allSettled([
        fetchSummary(signal),
        fetchHotspots(signal),
        fetchRegionDetail('00', signal)
      ]);

      const [summaryRes, hotspotsRes, natDetailRes] = results;

      if (natDetailRes.status === 'fulfilled') {
        setNationalRegionDetail(natDetailRes.value);
      }

      if (summaryRes.status === 'fulfilled') {
        setSummaryData(summaryRes.value.data);
        setSummaryMeta(summaryRes.value.meta);
        setSummaryError(null);
      } else if (summaryRes.reason?.name !== 'AbortError') {
        setSummaryError(`요약 API 연결 실패: ${summaryRes.reason?.message || '응답 오류'}`);
      }

      if (hotspotsRes.status === 'fulfilled') {
        const list = hotspotsRes.value.data || [];
        setHotspots(list);
        setHotspotsError(null);
        setSelectedHotspot((prev) => {
          if (!prev && list.length > 0) {
            return list.find((h) => h.sigungu_code === '11215') || list[0];
          }
          return prev;
        });
      } else if (hotspotsRes.reason?.name !== 'AbortError') {
        setHotspotsError(`핫스팟 API 연결 실패: ${hotspotsRes.reason?.message || '응답 오류'}`);
      }
    } catch (err) {
      // AbortError 무시
    } finally {
      setIsRefreshing(false);
      setSummaryLoading(false);
      setHotspotsLoading(false);
    }
  }, []);

  // 공정위 재시도 트리거 키 (네트워크 실제 재호출 보장)
  const [ftcRetryKey, setFtcRetryKey] = useState(0);
  const handleRetryFtc = useCallback(() => {
    setFtcRetryKey((prev) => prev + 1);
  }, []);

  // 공정위 연도 메타 및 상태 초기 로드 (1회 실행)
  useEffect(() => {
    let isMounted = true;
    async function loadFtcMetadata() {
      setYearsLoading(true);
      try {
        const [yearsRes, statusRes] = await Promise.allSettled([
          fetchFtcYears(),
          fetchFtcStatus()
        ]);
        if (isMounted) {
          if (yearsRes.status === 'fulfilled') {
            const list = yearsRes.value.data || [];
            setYearsList(list);
          }
          if (statusRes.status === 'fulfilled') {
            setFtcStatusMeta(statusRes.value.data);
          }
        }
      } catch (e) {
        // 무시
      } finally {
        if (isMounted) {
          setYearsLoading(false);
        }
      }
    }
    loadFtcMetadata();
    return () => {
      isMounted = false;
    };
  }, []);

  // 공정위 벤치마크 및 시계열 추세 페칭 (업종·연도·재시도 키 변경 시에만 격리 호출 - ALL 전체 외식업 포함)
  useEffect(() => {
    if (ftcAbortRef.current) {
      ftcAbortRef.current.abort();
    }
    const controller = new AbortController();
    ftcAbortRef.current = controller;
    const signal = controller.signal;

    setFtcLoading(true);
    setFtcError(null);

    async function loadBenchmarkAndTrends() {
      try {
        const [benchRes, trendsRes] = await Promise.all([
          fetchFtcBenchmark(selectedCategory, selectedYear, signal, selectedSido),
          fetchFtcTrends(selectedCategory, signal, selectedSido).catch(() => null)
        ]);

        setBenchmarkData(benchRes);
        setTrendsData(trendsRes);
        setFtcError(null);
      } catch (err) {
        if (err.name !== 'AbortError') {
          setFtcError(err);
        }
      } finally {
        setFtcLoading(false);
      }
    }

    loadBenchmarkAndTrends();

    return () => {
      controller.abort();
    };
  }, [selectedCategory, selectedYear, selectedSido, ftcRetryKey]);

  // 48개 중분류 하위 목록 로드 (지역 또는 8대 대분류 변경 시, 전국 중분류 기준치 동시 확보)
  useEffect(() => {
    if (!categoryFilterId || categoryFilterId === 'CAT_MAJ_99') {
      setMidCategories([]);
      setNationalMidCategories([]);
      setMidCategoriesLoading(false);
      return;
    }
    const controller = new AbortController();
    setMidCategoriesLoading(true);
    Promise.allSettled([
      fetchMajorCategoryDetail(categoryFilterId, activeRegionCode, controller.signal),
      activeRegionCode === '00'
        ? Promise.resolve(null)
        : fetchMajorCategoryDetail(categoryFilterId, '00', controller.signal)
    ])
      .then(([regRes, natRes]) => {
        if (controller.signal.aborted) return;
        const regList = regRes.status === 'fulfilled' ? (regRes.value?.mid_categories || []) : [];
        const natList =
          activeRegionCode === '00'
            ? regList
            : natRes.status === 'fulfilled'
              ? (natRes.value?.mid_categories || [])
              : [];
        setMidCategories(regList);
        setNationalMidCategories(natList);
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setMidCategoriesLoading(false);
        }
      });
    return () => controller.abort();
  }, [activeRegionCode, categoryFilterId]);

  // 상위 브랜드 및 업종·중분류별 100m 밀집도 격자·동적 핫스팟 로드 (지역·업종·중분류 변경 시)
  useEffect(() => {
    const controller = new AbortController();
    const signal = controller.signal;

    // 1. 지역×업종 맞춤 핫스팟 동적 갱신 (전 시군구 Top 5 보장)
    setHotspotsLoading(true);
    fetchHotspots(signal, {
      sidoCode: selectedSido,
      sigunguCode: selectedSigungu,
      categoryMajorId: categoryFilterId
    })
      .then((res) => {
        setHotspots(res.data || []);
        setHotspotsError(null);
      })
      .catch((e) => {
        if (e?.name !== 'AbortError') {
          setHotspotsError(e?.message || '핫스팟 조회 실패');
        }
      })
      .finally(() => {
        if (!signal.aborted) setHotspotsLoading(false);
      });

    // 2. 선택 지역(전국 '00' 포함) 내 대분류·중분류별 상위 브랜드 갱신
    setTopBrandsState((prev) => ({ ...prev, loading: true, error: null }));
    fetchRegionDetail(activeRegionCode, signal, categoryFilterId, selectedMidCategory)
      .then((res) => {
        setTopBrandsState({ list: res.top_brands || [], loading: false, error: null });
      })
      .catch((e) => {
        if (e?.name === 'AbortError') return;
        setTopBrandsState({ list: [], loading: false, error: e?.message || '상위 브랜드 조회 실패' });
      });

    // 3. 시군구 단위(5자리)인 경우 선택된 대분류·중분류에 맞춰 100m 정밀 밀집도 격자 실시간 재계산
    //    전국('00') 또는 시도(2자리)인 경우 하위 지역(17개 시도 / 산하 시군구) 버블 마커 데이터 로드
    if (activeRegionCode.length === 5) {
      setMacroBubbles([]);
      setMacroBubblesLoading(false);
      fetchGridDensity(activeRegionCode, signal, 1500, categoryFilterId, selectedMidCategory)
        .then((res) => {
          if (!signal.aborted) {
            setGridData(res.data || []);
            setGridError(null);
          }
        })
        .catch((e) => {
          if (e?.name !== 'AbortError') {
            setGridError(e?.message || '업종별 격자 조회 실패');
          }
        });
    } else {
      setMacroBubblesLoading(true);
      const targetType = activeRegionCode === '00' ? 'SIDO' : 'SIGUNGU';
      const targetSido = activeRegionCode === '00' ? null : activeRegionCode;
      fetchRegions(targetType, targetSido, signal, categoryFilterId, selectedMidCategory)
        .then((res) => {
          if (!signal.aborted) {
            setMacroBubbles(res.data || []);
          }
        })
        .catch(() => {
          if (!signal.aborted) {
            setMacroBubbles([]);
          }
        })
        .finally(() => {
          if (!signal.aborted) {
            setMacroBubblesLoading(false);
          }
        });
    }

    return () => controller.abort();
  }, [activeRegionCode, selectedSido, selectedSigungu, categoryFilterId, selectedMidCategory]);

  // 마운트 시 최초 전국 요약 및 핫스팟 데이터 로드
  useEffect(() => {
    loadMapData();
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, [loadMapData]);

  // 화면 내 점포 목록 (MapContainer ↔ ViewportStoreInspector 연동)
  const handleVisibleStoresChange = useCallback((stores, status) => {
    setVisibleStores(stores);
    setStoreStatus(status);
  }, []);

  const handleSelectStoreFromInspector = useCallback((store) => {
    setActiveStoreId(store.bizes_id);
    focusNonceRef.current += 1;
    setFocusStoreRequest({
      bizes_id: store.bizes_id,
      bizes_nm: store.bizes_nm,
      lon: Number(store.lon),
      lat: Number(store.lat),
      nonce: focusNonceRef.current
    });
  }, []);

  // 브랜드 상세 분석 호출 (좌측 Top 5 브랜드 클릭 또는 지도 점포 팝업 내 브랜드 분석 버튼 클릭)
  const handleInspectBrand = useCallback((brandObjOrName) => {
    if (!brandObjOrName) return;
    brandNonceRef.current += 1;
    if (typeof brandObjOrName === 'string') {
      setStoreSearchQuery(brandObjOrName);
      setInspectedBrandRequest({
        brand_name_std: brandObjOrName,
        nonce: brandNonceRef.current
      });
    } else {
      setStoreSearchQuery(brandObjOrName.brand_name_std || '');
      setInspectedBrandRequest({
        ...brandObjOrName,
        nonce: brandNonceRef.current
      });
    }
  }, []);

  // 브랜드 분포 차트 또는 지도 위 광역 버블 마커에서 특정 지역(전국/시도/시군구) 클릭 시 대시보드 전체 지역 동기화 이동
  const handleNavigateRegionFromBrand = useCallback((regionCode, regionType) => {
    if (!regionCode) return;
    setSelectedHotspot(null);
    if (regionCode === '00' || regionType === 'NATIONWIDE') {
      handleSelectSido('00');
    } else if (regionType === 'SIDO' || regionCode.length === 2) {
      handleSelectSido(regionCode);
    } else if (regionCode.length === 5) {
      const targetSido = regionCode.slice(0, 2);
      if (targetSido !== selectedSido) {
        setSelectedSido(targetSido);
        setRegionsLoading(true);
        fetchRegions('SIGUNGU', targetSido)
          .then((res) => setSigunguList(res.data || []))
          .catch(() => {})
          .finally(() => setRegionsLoading(false));
      }
      setSelectedSigungu(regionCode);
    }
  }, [selectedSido, handleSelectSido]);

  // 핫스팟 선택 핸들러 (지도 카메라 이동과 동시에 상단·좌측·우측 패널의 시도/시군구 상태를 100% 동기화)
  const handleSelectHotspot = useCallback((item) => {
    if (!item) return;
    setSelectedHotspot(item);
    if (item.sido_code && item.sido_code !== selectedSido) {
      setSelectedSido(item.sido_code);
      setRegionsLoading(true);
      fetchRegions('SIGUNGU', item.sido_code)
        .then((res) => {
          setSigunguList(res.data || []);
        })
        .catch(() => {})
        .finally(() => setRegionsLoading(false));
    }
    if (item.sigungu_code && item.sigungu_code !== selectedSigungu) {
      setSelectedSigungu(item.sigungu_code);
    }
  }, [selectedSido, selectedSigungu]);

  // 대시보드 홈 ↔ 3D 지도 모드 상호 전환 핸들러
  const handleOpenMap = useCallback(() => {
    setViewMode('map');
  }, []);

  const handleBackToDashboard = useCallback(() => {
    setViewMode('dashboard');
  }, []);

  const handleOpenMapWithHotspot = useCallback((item) => {
    handleSelectHotspot(item);
    setViewMode('map');
  }, [handleSelectHotspot]);

  const handleOpenMapWithBrand = useCallback((brand) => {
    handleInspectBrand(brand);
    setViewMode('map');
  }, [handleInspectBrand]);

  const handleOpenMapWithRegion = useCallback((sidoCode, sigunguCode) => {
    if (sidoCode) handleSelectSido(sidoCode);
    if (sigunguCode) handleSelectSigungu(sigunguCode);
    setViewMode('map');
  }, [handleSelectSido, handleSelectSigungu]);

  // 현재 선택된 업종 및 중분류 객체
  const currentCategoryInfo = CATEGORY_MAJOR_LIST.find((c) => c.id === selectedCategory) || {
    id: selectedCategory,
    name: selectedCategory
  };
  const currentMidCategoryObj = selectedMidCategory
    ? midCategories.find((m) => m.category_mid_id === selectedMidCategory)
    : null;
  const currentMidCategoryLabel = currentMidCategoryObj?.category_mid_name || '';

  // 선택된 지역 정보 객체 계산
  const selectedRegionInfo = isNationwide
    ? { region_code: '00', region_name: '전국', region_type: 'NATIONWIDE', center_lon: 127.7669, center_lat: 35.9078 }
    : (regionDetail?.region_stats || {
        region_code: activeRegionCode,
        region_name: sigunguList.find(s => s.region_code === activeRegionCode)?.region_name 
          || sidoList.find(s => s.region_code === activeRegionCode)?.region_name 
          || '선택 지역'
      });

  // 소진공 데이터 기준월 및 출처 텍스트 계산
  // 전국(00)은 summaryMeta, 지역은 regionDetail.meta를 직접 참조하며 지역 기준월 부재 시 전국값 대리 표출 엄격 차단
  const sedaReferenceMonth = (activeRegionCode === '00'
    ? summaryMeta?.data_reference_month
    : regionDetail?.meta?.data_reference_month) || null;

  const sedaProvenanceText = sedaReferenceMonth
    ? `소진공 ${sedaReferenceMonth} 공간 전수`
    : '소진공 기준월 확인 불가';

  const apiStatus = {
    summary: !summaryError && !!summaryData,
    grid: gridData.length > 0,
    hotspots: !hotspotsError && hotspots.length > 0,
    ftc: !ftcError && !!benchmarkData
  };

  const hasAnyError = summaryError || hotspotsError;

  // 1. 기본 진입 화면: Finora 스타일의 외식 프랜차이즈 데이터 대시보드 홈
  if (viewMode === 'dashboard') {
    return (
      <>
        <CinematicIntro
          isOpen={showIntro}
          onClose={handleCloseIntro}
          onExploreDashboard={handleExploreDashboardFromIntro}
          onExplore3DMap={handleExplore3DMapFromIntro}
        />
        <DashboardHome
          summaryData={summaryData}
          summaryMeta={summaryMeta}
          nationalRegionDetail={nationalRegionDetail}
          regionDetail={regionDetail}
          selectedRegionInfo={selectedRegionInfo}
          isNationwide={isNationwide}
          sidoList={sidoList}
          sigunguList={sigunguList}
          selectedSido={selectedSido}
          selectedSigungu={selectedSigungu}
          onSelectSido={handleSelectSido}
          onSelectSigungu={handleSelectSigungu}
          regionsLoading={regionsLoading}
          selectedCategory={selectedCategory}
          onSelectCategory={handleSelectCategory}
          midCategories={midCategories}
          selectedMidCategory={selectedMidCategory}
          onSelectMidCategory={handleSelectMidCategory}
          topBrandsState={topBrandsState}
          benchmarkData={benchmarkData}
          trendsData={trendsData}
          ftcLoading={ftcLoading}
          selectedYear={selectedYear}
          onSelectYear={setSelectedYear}
          yearsList={yearsList}
          hotspots={hotspots}
          hotspotsLoading={hotspotsLoading}
          onOpenMap={handleOpenMap}
          onOpenMapWithHotspot={handleOpenMapWithHotspot}
          onOpenMapWithBrand={handleOpenMapWithBrand}
          onOpenMapWithRegion={handleOpenMapWithRegion}
          onOpenIntro={handleOpenIntro}
          onOpenGuideModal={handleOpenGuideModal}
          onRefresh={loadMapData}
          isRefreshing={isRefreshing}
          apiStatus={apiStatus}
        />
        <UserGuideModal
          isOpen={showGuideModal}
          onClose={handleCloseGuideModal}
        />
      </>
    );
  }

  // 2. 3D GIS 상권 공간 지도 모드 (특정 버튼/핫스팟/브랜드 클릭 시 전환)
  return (
    <div className="app-layout">
      <CinematicIntro
        isOpen={showIntro}
        onClose={handleCloseIntro}
        onExploreDashboard={handleExploreDashboardFromIntro}
        onExplore3DMap={handleExplore3DMapFromIntro}
      />

      {/* 1. 상단 글로벌 헤더 (대시보드 홈 복귀 버튼 연동) */}
      <Header 
        apiStatus={apiStatus} 
        onRefresh={loadMapData} 
        isRefreshing={isRefreshing}
        onBackToDashboard={handleBackToDashboard}
        onOpenIntro={handleOpenIntro}
        onOpenGuideModal={handleOpenGuideModal}
      />

      {/* 2. 지역, 업종 및 기준연도 선택 바 (CategoryFilterBar) */}
      <CategoryFilterBar 
        selectedCategory={selectedCategory}
        onSelectCategory={handleSelectCategory}
        midCategories={midCategories}
        selectedMidCategory={selectedMidCategory}
        onSelectMidCategory={handleSelectMidCategory}
        midCategoriesLoading={midCategoriesLoading}
        yearsList={yearsList}
        selectedYear={selectedYear}
        onSelectYear={setSelectedYear}
        yearsLoading={yearsLoading}
        statusMeta={ftcStatusMeta}
        benchmarkData={benchmarkData}
        sedaReferenceMonth={sedaReferenceMonth}
        sedaProvenanceText={sedaProvenanceText}
        sidoList={sidoList}
        selectedSido={selectedSido}
        onSelectSido={handleSelectSido}
        sigunguList={sigunguList}
        selectedSigungu={selectedSigungu}
        onSelectSigungu={handleSelectSigungu}
        regionsLoading={regionsLoading}
        isFtcDrawerOpen={isFtcDrawerOpen}
        onToggleFtcDrawer={() => setIsFtcDrawerOpen((prev) => !prev)}
      />

      {/* API 연결 지연 배너 */}
      {hasAnyError && (
        <div className="api-warning-banner" role="alert">
          <div className="warning-content">
            <span className="warning-icon">⚠️</span>
            <span>
              일부 백엔드 API 연결에 실패했습니다 (대상: <code>{BASE_URL}</code>). 성공한 데이터는 계속 유지되며, 서버 실행 후 재시도하세요.
            </span>
          </div>
          <button className="banner-retry-btn" onClick={loadMapData}>재연결 시도</button>
        </div>
      )}

      {/* 3. 대시보드 메인 본문 (지도 전면 캔버스 및 플로팅 패널 구조) */}
      <main className="dashboard-body">
        {/* 전면 배경: 3D GIS 지도 뷰포트 (MapContainer) */}
        <MapContainer 
          gridData={gridData} 
          macroBubbles={macroBubbles}
          macroBubblesLoading={macroBubblesLoading}
          onSelectRegionBubble={handleNavigateRegionFromBrand}
          selectedHotspot={selectedHotspot} 
          selectedCategory={categoryFilterId}
          selectedMidCategory={selectedMidCategory}
          selectedMidCategoryLabel={currentMidCategoryLabel}
          selectedRegionInfo={selectedRegionInfo}
          gridLoading={gridLoading}
          gridError={gridError}
          regionLoading={regionLoading}
          onRetryGrid={() => setGridRetryKey((prev) => prev + 1)}
          sedaReferenceMonth={sedaReferenceMonth}
          isFtcDrawerOpen={isFtcDrawerOpen}
          onToggleFtcDrawer={() => {
            setIsFtcDrawerOpen((prev) => {
              const next = !prev;
              if (next) setIsHotspotsVisible(false);
              return next;
            });
          }}
          isHotspotsVisible={isHotspotsVisible}
          onToggleHotspots={() => {
            setIsHotspotsVisible((prev) => {
              const next = !prev;
              if (next) setIsFtcDrawerOpen(false);
              return next;
            });
          }}
          onVisibleStoresChange={handleVisibleStoresChange}
          onActiveStoreChange={setActiveStoreId}
          focusStoreRequest={focusStoreRequest}
          storeTypeFilter={storeTypeFilter}
          storeSearchQuery={storeSearchQuery}
          onInspectBrand={handleInspectBrand}
          onOpenGuideModal={handleOpenGuideModal}
        />

        {/* 지도 상단 중앙: 1줄 슬림 점포·브랜드 통합 검색 및 인텔리전스 바 */}
        <ViewportStoreInspector
          stores={visibleStores}
          status={storeStatus}
          activeStoreId={activeStoreId}
          onSelectStore={handleSelectStoreFromInspector}
          filter={storeTypeFilter}
          onChangeFilter={setStoreTypeFilter}
          query={storeSearchQuery}
          onChangeQuery={setStoreSearchQuery}
          categoryName={
            currentMidCategoryLabel
              ? `${currentCategoryInfo.name} › ${currentMidCategoryLabel}`
              : isAllCategory
                ? ''
                : currentCategoryInfo.name
          }
          activeRegionCode={activeRegionCode}
          selectedRegionName={selectedRegionInfo?.region_name || '전국'}
          selectedSido={selectedSido}
          selectedSigungu={selectedSigungu}
          selectedCategoryId={categoryFilterId}
          selectedMidCategoryId={selectedMidCategory}
          onNavigateRegion={handleNavigateRegionFromBrand}
          inspectedBrandRequest={inspectedBrandRequest}
        />

        {/* 좌측 플로팅: 지역 및 전국 소상공인 점포·브랜드 실측 분석 패널 */}
        <MarketSummary 
          data={isNationwide ? summaryData : regionDetail?.region_stats} 
          meta={isNationwide ? summaryMeta : regionDetail?.meta} 
          nationalSummaryData={summaryData}
          nationalSummaryMeta={summaryMeta}
          nationalRegionDetail={nationalRegionDetail}
          nationalMidCategories={nationalMidCategories}
          regionDetail={regionDetail}
          selectedRegionInfo={selectedRegionInfo}
          isNationwide={isNationwide}
          loading={isNationwide ? summaryLoading : regionLoading} 
          error={isNationwide ? summaryError : regionError} 
          onRetry={() => {
            if (isNationwide) loadMapData();
            else setSelectedSigungu(selectedSigungu);
          }} 
          sedaReferenceMonth={sedaReferenceMonth}
          sedaProvenanceText={sedaProvenanceText}
          topBrandsState={topBrandsState}
          selectedCategoryId={categoryFilterId}
          categoryLabel={isAllCategory ? '' : currentCategoryInfo.name}
          midCategories={midCategories}
          selectedMidCategory={selectedMidCategory}
          midCategoryLabel={currentMidCategoryLabel}
          onSelectCategory={handleSelectCategory}
          onSelectMidCategory={handleSelectMidCategory}
          activeBrandName={storeSearchQuery.trim()}
          onSelectBrand={(brandName, brandObj) => {
            handleInspectBrand(brandObj || brandName);
          }}
        />

        {/* 우측 독(Dock) 연동 팝오버: 🔥 핫스팟 버튼 클릭 시 튀어나오는 상권 핫스팟 메뉴 */}
        {isHotspotsVisible && (
          <HotspotsPanel 
            hotspots={hotspots} 
            activeHotspotId={selectedHotspot?.hotspot_id} 
            onSelectHotspot={(item) => {
              handleSelectHotspot(item);
            }} 
            onClose={() => setIsHotspotsVisible(false)}
            loading={hotspotsLoading} 
            error={hotspotsError} 
            onRetry={loadMapData}
            selectedRegionInfo={selectedRegionInfo}
            activeRegionCode={activeRegionCode}
          />
        )}

        {/* 우측 독(Dock) '💰 매출' 버튼 연동: 시도 지역×업종별 매출·창업비용 & 8대 업종 비교 패널 */}
        <FtcBenchmarkPanel 
          categoryInfo={currentCategoryInfo}
          isAllCategory={isAllCategory}
          onSelectCategory={handleSelectCategory}
          selectedSido={selectedSido}
          selectedRegionInfo={selectedRegionInfo}
          benchmarkData={benchmarkData}
          trendsData={trendsData}
          loading={ftcLoading}
          error={ftcError}
          onRetry={handleRetryFtc}
          selectedYear={selectedYear}
          onSelectYear={setSelectedYear}
          yearsList={yearsList}
          statusMeta={ftcStatusMeta}
          isDrawerOpen={isFtcDrawerOpen}
          onCloseDrawer={() => setIsFtcDrawerOpen(false)}
          onToggleDrawer={() => setIsFtcDrawerOpen((prev) => !prev)}
        />
      </main>

      <UserGuideModal
        isOpen={showGuideModal}
        onClose={handleCloseGuideModal}
      />
    </div>
  );
}

