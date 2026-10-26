/**
 * Franchise Dashboard Phase 5A: API 통신 서비스
 * 환경변수 VITE_API_URL을 단일 진입점으로 사용하여 백엔드와 통신합니다.
 */

// API 통신 기준 주소 (BASE_URL) 결정:
// 1. 프로덕션 모드(import.meta.env.PROD)에서는 방문자 브라우저가 사용자 로컬 PC로 향하는 것을 방지하기 위해,
//    루프백 주소(127.0.0.1/localhost)이거나 빈 값인 경우 동일 출처 상대 경로('')를 강제합니다.
// 2. 프로덕션에서 명시적인 외부 HTTPS 도메인이 지정된 경우에만 해당 도메인을 사용합니다.
// 3. 로컬 개발 모드(import.meta.env.DEV)에서는 VITE_API_URL 또는 'http://127.0.0.1:8000'으로 fallback합니다.
const rawApiUrl = (import.meta.env?.VITE_API_URL || '').trim();
const isLoopback = rawApiUrl.includes('127.0.0.1') || rawApiUrl.includes('localhost');

// 외부 LAN IP(예: 팀원 PC/노트북)에서 접근한 경우 루프백 대신 동일 출처 상대 경로('')를 사용하여 Vite 프록시 경유
const isExternalClient = typeof window !== 'undefined' && 
  window.location.hostname !== 'localhost' && 
  window.location.hostname !== '127.0.0.1';

const BASE_URL = (import.meta.env.PROD || isExternalClient)
  ? (isLoopback || !rawApiUrl ? '' : rawApiUrl.replace(/\/+$/, ''))
  : (rawApiUrl || 'http://127.0.0.1:8000');

/**
 * 전국 외식업 총괄 요약 통계를 조회합니다.
 * @param {AbortSignal} [signal] 
 */
export async function fetchSummary(signal) {
  const res = await fetch(`${BASE_URL}/api/v1/analytics/summary`, { signal });
  if (!res.ok) {
    throw new Error(`요약 통계 조회 실패 (HTTP ${res.status})`);
  }
  return res.json();
}

/**
 * 특정 시군구(기본: 11215 광진구)의 100m 정밀 밀집도 격자 데이터를 조회합니다.
 * @param {string} [sigunguCode='11215'] 
 * @param {AbortSignal} [signal] 
 * @param {number} [limit=1500] 반환 격자 상한 (제주시 1,351개 포함 전수 커버)
 * @param {string|null} [categoryMajorId=null] 8대 대분류 코드 ('CAT_MAJ_01'~'08')
 * @param {string|null} [categoryMidId=null] 48대 중분류 코드 ('CAT_MID_0101'~'0806')
 */
export async function fetchGridDensity(
  sigunguCode = '11215',
  signal,
  limit = 1500,
  categoryMajorId = null,
  categoryMidId = null
) {
  const params = new URLSearchParams({
    sigungu_code: String(sigunguCode),
    limit: String(limit)
  });
  if (categoryMajorId && categoryMajorId !== 'ALL') {
    params.set('category_major_id', categoryMajorId);
  }
  if (categoryMidId && categoryMidId !== 'ALL') {
    params.set('category_mid_id', categoryMidId);
  }
  const res = await fetch(`${BASE_URL}/api/v1/spatial/density/grid?${params.toString()}`, { signal });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `밀집도 격자 조회 실패 (HTTP ${res.status})`);
  }
  return res.json();
}

/**
 * 현재 지도 뷰포트의 개별 점포를 GeoJSON으로 조회합니다.
 */
export async function fetchStoresByBbox(bounds, categoryMajorId, signal, limit = 500, categoryMidId = null) {
  const params = new URLSearchParams({
    min_lon: String(bounds.minLon),
    min_lat: String(bounds.minLat),
    max_lon: String(bounds.maxLon),
    max_lat: String(bounds.maxLat),
    exact_count: 'false',
    limit: String(limit),
    format: 'geojson'
  });
  if (categoryMajorId && categoryMajorId !== 'ALL') params.set('category_major_id', categoryMajorId);
  if (categoryMidId && categoryMidId !== 'ALL') params.set('category_mid_id', categoryMidId);

  const res = await fetch(`${BASE_URL}/api/v1/spatial/stores/bbox?${params}`, { signal });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data.detail || `개별 점포 조회 실패 (HTTP ${res.status})`);
  }
  return data;
}

/** 개별 점포의 4축 상태와 팝업 표시 정보를 조회합니다. */
export async function fetchStoreDetail(bizesId, signal) {
  const res = await fetch(`${BASE_URL}/api/v1/spatial/stores/${encodeURIComponent(bizesId)}`, { signal });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data.detail || `점포 상세 조회 실패 (HTTP ${res.status})`);
  }
  return data;
}

/**
 * 상위 상권 핫스팟 목록 및 3D 카메라 앵글을 조회합니다.
 * @param {AbortSignal} [signal] 
 * @param {{ sidoCode?: string, sigunguCode?: string, categoryMajorId?: string }} [filters]
 */
export async function fetchHotspots(signal, filters = {}) {
  const params = new URLSearchParams();
  if (filters.sidoCode && filters.sidoCode !== '00') {
    params.set('sido_code', filters.sidoCode);
  }
  if (filters.sigunguCode) {
    params.set('sigungu_code', filters.sigunguCode);
  }
  if (filters.categoryMajorId && filters.categoryMajorId !== 'ALL') {
    params.set('category_major_id', filters.categoryMajorId);
  }
  const qs = params.toString();
  const url = `${BASE_URL}/api/v1/spatial/hotspots${qs ? `?${qs}` : ''}`;
  const res = await fetch(url, { signal });
  if (!res.ok) {
    throw new Error(`상권 핫스팟 목록 조회 실패 (HTTP ${res.status})`);
  }
  return res.json();
}

/**
 * 공정위 거시통계 최신 적재 상태 및 메타데이터를 조회합니다.
 * @param {AbortSignal} [signal]
 */
export async function fetchFtcStatus(signal) {
  const res = await fetch(`${BASE_URL}/api/v1/ftc/status`, { signal });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail?.message || `공정위 상태 조회 실패 (HTTP ${res.status})`);
  }
  return res.json();
}

/**
 * 업종별 공정위 거시 벤치마크 데이터를 조회합니다.
 * @param {string} categoryMajorId 8대 대분류 코드 (CAT_MAJ_01 ~ CAT_MAJ_08)
 * @param {string} [year] 기준연도 (미지정 시 DB 최신연도 자동 조회)
 * @param {AbortSignal} [signal]
 */
export async function fetchFtcBenchmark(categoryMajorId, year = null, signal, sidoCode = null) {
  let url = `${BASE_URL}/api/v1/ftc/benchmark/latest?category_major_id=${encodeURIComponent(categoryMajorId)}&v=rgn2`;
  if (year) {
    url += `&year=${encodeURIComponent(year)}`;
  }
  const effectiveSido = sidoCode || '00';
  url += `&sido_code=${encodeURIComponent(effectiveSido)}`;
  const res = await fetch(url, { signal, cache: 'no-store' });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    // 400 (매핑 불가) 또는 404 (해당 연도 데이터 없음) 등 상태를 본문 객체와 함께 에러에 보존
    const error = new Error(data.message || `공정위 벤치마크 조회 실패 (HTTP ${res.status})`);
    error.status = res.status;
    error.data = data;
    throw error;
  }
  return data;
}

/**
 * 업종별 다년도 횡단면 거시 시계열 추세를 조회합니다.
 * @param {string} categoryMajorId 8대 대분류 코드
 * @param {AbortSignal} [signal]
 * @param {string} [sidoCode] 시도 코드
 */
export async function fetchFtcTrends(categoryMajorId, signal, sidoCode = null) {
  const effectiveSido = sidoCode || '00';
  const url = `${BASE_URL}/api/v1/ftc/trends?category_major_id=${encodeURIComponent(categoryMajorId)}&sido_code=${encodeURIComponent(effectiveSido)}&v=rgn2`;
  const res = await fetch(url, { signal, cache: 'no-store' });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const error = new Error(data.message || `공정위 시계열 추세 조회 실패 (HTTP ${res.status})`);
    error.status = res.status;
    error.data = data;
    throw error;
  }
  return data;
}

/**
 * 수동 연도 선택용 연도 메타 목록을 조회합니다.
 * @param {AbortSignal} [signal]
 */
export async function fetchFtcYears(signal) {
  const res = await fetch(`${BASE_URL}/api/v1/ftc/years`, { signal });
  if (!res.ok) {
    throw new Error(`공정위 연도 메타 조회 실패 (HTTP ${res.status})`);
  }
  return res.json();
}

/**
 * 시도 및 시군구 지역 목록을 조회합니다.
 * @param {string} [regionType] 'SIDO' | 'SIGUNGU'
 * @param {string} [sidoCode] 상위 시도코드 (예: '11')
 * @param {AbortSignal} [signal]
 */
export async function fetchRegions(
  regionType = null,
  sidoCode = null,
  signal,
  categoryMajorId = null,
  categoryMidId = null
) {
  const params = new URLSearchParams({ limit: '300' });
  if (regionType) params.set('region_type', regionType);
  if (sidoCode) params.set('sido_code', sidoCode);
  if (categoryMajorId && categoryMajorId !== 'ALL') params.set('category_major_id', categoryMajorId);
  if (categoryMidId && categoryMidId !== 'ALL') params.set('category_mid_id', categoryMidId);
  const res = await fetch(`${BASE_URL}/api/v1/analytics/regions?${params.toString()}`, { signal });
  if (!res.ok) {
    throw new Error(`지역 목록 조회 실패 (HTTP ${res.status})`);
  }
  return res.json();
}

/**
 * 특정 지역(시도/시군구/전국)의 상세 통계, 상위 10개 브랜드, 업종 구성을 조회합니다.
 * @param {string} regionCode (예: '11680', '11215', '11', '00')
 * @param {AbortSignal} [signal]
 * @param {string|null} [categoryMajorId] 지정 시 상위 브랜드를 해당 업종 내 순위로 조회 (미지정 시 전 업종)
 * @param {string|null} [categoryMidId] 지정 시 상위 브랜드를 해당 48대 중분류 내 순위로 조회
 */
export async function fetchRegionDetail(regionCode, signal, categoryMajorId = null, categoryMidId = null) {
  const params = new URLSearchParams();
  if (categoryMajorId && categoryMajorId !== 'ALL') {
    params.set('category_major_id', categoryMajorId);
  }
  if (categoryMidId && categoryMidId !== 'ALL') {
    params.set('category_mid_id', categoryMidId);
  }
  const qs = params.toString();
  const res = await fetch(`${BASE_URL}/api/v1/analytics/regions/${encodeURIComponent(regionCode)}${qs ? `?${qs}` : ''}`, { signal });
  if (!res.ok) {
    throw new Error(`지역 상세 조회 실패 (HTTP ${res.status})`);
  }
  return res.json();
}

/**
 * 특정 8대 대분류의 하위 중분류(48대 중분류) 통계 및 점유율을 조회합니다.
 * @param {string} categoryMajorId ('CAT_MAJ_01' ~ 'CAT_MAJ_08')
 * @param {string} [regionCode='00'] ('00' 전국, '11' 시도, '11215' 시군구)
 * @param {AbortSignal} [signal]
 */
export async function fetchMajorCategoryDetail(categoryMajorId, regionCode = '00', signal) {
  const res = await fetch(
    `${BASE_URL}/api/v1/analytics/categories/${encodeURIComponent(categoryMajorId)}?region_code=${encodeURIComponent(regionCode || '00')}`,
    { signal }
  );
  if (!res.ok) {
    throw new Error(`중분류 통계 조회 실패 (HTTP ${res.status})`);
  }
  return res.json();
}

/**
 * 전국 5,062개 브랜드 후보를 검색 및 자동완성합니다 (선택 지역 점포 수 동시 반환).
 * @param {object} [options]
 * @param {AbortSignal} [signal]
 */
export async function searchBrands(options = {}, signal) {
  const {
    q = '',
    regionCode = '00',
    categoryMajorId = null,
    categoryMidId = null,
    officiality = null,
    limit = 25
  } = options;
  const params = new URLSearchParams({
    region_code: String(regionCode || '00'),
    limit: String(limit)
  });
  if (q && q.trim()) params.set('q', q.trim());
  if (categoryMajorId && categoryMajorId !== 'ALL') params.set('category_major_id', categoryMajorId);
  if (categoryMidId && categoryMidId !== 'ALL') params.set('category_mid_id', categoryMidId);
  if (officiality && officiality !== 'all') params.set('officiality', officiality);

  const res = await fetch(`${BASE_URL}/api/v1/analytics/brands/search?${params.toString()}`, { signal });
  if (!res.ok) {
    throw new Error(`브랜드 검색 실패 (HTTP ${res.status})`);
  }
  return res.json();
}

/**
 * 특정 브랜드의 전국 17개 시도('SIDO') 또는 256개 시군구('SIGUNGU') 분포를 조회합니다.
 * @param {string} brandId
 * @param {'SIDO'|'SIGUNGU'} [regionType='SIGUNGU']
 * @param {AbortSignal} [signal]
 */
export async function fetchBrandDistribution(brandId, regionType = 'SIGUNGU', signal) {
  const params = new URLSearchParams({ region_type: regionType });
  const res = await fetch(
    `${BASE_URL}/api/v1/analytics/brands/${encodeURIComponent(brandId)}/distribution?${params.toString()}`,
    { signal }
  );
  if (!res.ok) {
    throw new Error(`브랜드 지역별 분포 조회 실패 (HTTP ${res.status})`);
  }
  return res.json();
}

/**
 * 특정 브랜드의 개별 지점 목록(도로명주소·좌표 포함)을 조회합니다.
 * @param {string} brandId
 * @param {{ sidoCode?: string, sigunguCode?: string, limit?: number }} [filters]
 * @param {AbortSignal} [signal]
 */
export async function fetchBrandStores(brandId, filters = {}, signal) {
  const params = new URLSearchParams({
    limit: String(filters.limit || 80)
  });
  if (filters.sidoCode && filters.sidoCode !== '00') {
    params.set('sido_code', filters.sidoCode);
  }
  if (filters.sigunguCode) {
    params.set('sigungu_code', filters.sigunguCode);
  }
  const res = await fetch(
    `${BASE_URL}/api/v1/analytics/brands/${encodeURIComponent(brandId)}/stores?${params.toString()}`,
    { signal }
  );
  if (!res.ok) {
    throw new Error(`브랜드 지점 목록 조회 실패 (HTTP ${res.status})`);
  }
  return res.json();
}

export { BASE_URL };

