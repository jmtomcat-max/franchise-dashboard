import React, { useEffect, useRef, useState, useCallback } from 'react';
import maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import { CATEGORY_MAJOR_LIST } from './CategoryFilterBar';
import SlimMapRail from './SlimMapRail';
import { fetchStoreDetail, fetchStoresByBbox } from '../services/api';

// OpenStreetMap 표준 베이스맵 (토큰 불필요, 100% 무료 무결성 및 한글 지명 완벽 지원)
// MapLibre raster 페인트 필터를 적용하여 촌스러운 채도를 낮추고 차분한 모던 실버 톤으로 정제
const OSM_LIGHT_STYLE = {
  version: 8,
  sources: {
    'osm-tiles': {
      type: 'raster',
      tiles: [
        'https://tile.openstreetmap.org/{z}/{x}/{y}.png'
      ],
      tileSize: 256,
      maxzoom: 19,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap</a> contributors'
    }
  },
  layers: [
    {
      id: 'osm-layer',
      type: 'raster',
      source: 'osm-tiles',
      minzoom: 0,
      maxzoom: 19,
      paint: {
        'raster-saturation': -0.32,  // 촌스러운 노랑/초록 원색을 부드럽고 차분한 모던 톤으로 보정
        'raster-contrast': 0.06,     // 도로망과 한글 지명 텍스트를 또렷하게 유지
        'raster-opacity': 0.95
      }
    }
  ]
};

// 광진구 건대입구 중심 기본 카메라 설정
const DEFAULT_CENTER = [127.0699, 37.5407];

// 8대 외식업 대분류 테마 색상 매핑 상수 (Apple Light Glass 전용 비비드 팔레트)
export const CATEGORY_COLOR_MAP = {
  '한식': '#059669',          // Emerald Green
  '중식': '#e11d48',          // Crimson Rose
  '일식': '#0284c7',          // Electric Blue
  '양식·세계음식': '#d97706',  // Amber Gold
  '치킨·패스트푸드': '#ea580c', // Tangerine Orange
  '분식·간편식': '#db2777',    // Pink Orchid
  '카페·음료': '#8b5cf6',      // Violet Purple
  '베이커리·디저트': '#06b6d4', // Cyan Teal
  '기타': '#64748b'           // Slate Gray
};

// 밀집도 5단계 색상 표현식 (점포 핀의 블루/오렌지/에메랄드 3원색과 겹치지 않는 라벤더→퍼플→딥마젠타 계열)
const DENSITY_COLOR_RAMP = [
  'interpolate', ['linear'], ['get', 'total_stores'],
  3, '#e9d5ff',   // 연라벤더 (저밀도: 3개소)
  15, '#c084fc',  // 라이트 퍼플 (15개소)
  30, '#9333ea',  // 바이올렛 (30개소)
  60, '#db2777',  // 마젠타 핑크 (60개소)
  100, '#9d174d'  // 딥 크림슨 (초고밀도: 100개소 이상)
];

// 8대 업종별 고유 테마 색상 매칭 표현식
const CATEGORY_COLOR_RAMP = [
  'match',
  ['get', 'top_category_name'],
  '한식', '#059669',
  '중식', '#e11d48',
  '일식', '#0284c7',
  '양식·세계음식', '#d97706',
  '치킨·패스트푸드', '#ea580c',
  '분식·간편식', '#db2777',
  '카페·음료', '#8b5cf6',
  '베이커리·디저트', '#06b6d4',
  '#64748b' // 기타 기본값
];

const EMPTY_FEATURE_COLLECTION = { type: 'FeatureCollection', features: [] };
const STORE_MIN_ZOOM = 14;
const STORE_LIMIT = 1200;
// 점포 핀 색상: Okabe-Ito 보색·삼각 대비 원칙 적용 (블루 220° ↔ 오렌지 25° 정보색 + 에메랄드 160° 삼각 대비)
export const STORE_TYPE_META = {
  franchise: { label: '프랜차이즈', color: '#0055ff' },
  candidate: { label: '브랜드 후보', color: '#ff6b00' },
  indie: { label: '개인·독립', color: '#10b981' }
};

export function getStoreType(props) {
  const o = props?.brand_officiality;
  if (o === 'FRANCHISE_CONFIRMED' || o === 'BRAND_CONFIRMED') return 'franchise';
  if (o === 'UNVERIFIED') return 'candidate';
  return 'indie';
}

const STORE_COLOR_RAMP = [
  'match', ['get', 'brand_officiality'],
  'FRANCHISE_CONFIRMED', STORE_TYPE_META.franchise.color,
  'BRAND_CONFIRMED', STORE_TYPE_META.franchise.color,
  'UNVERIFIED', STORE_TYPE_META.candidate.color,
  STORE_TYPE_META.indie.color
];

// 슬림 헥사곤(6각형) 정점 계산 헬퍼 (인접 기둥 간 ~25%의 여백을 두어 크리스탈 타워처럼 입체감 부여)
function createHexagonCoordinates(centerLon, centerLat, radiusMeters = 35) {
  const latRad = (centerLat * Math.PI) / 180.0;
  const metersPerDegLat = 111132.95;
  const metersPerDegLon = 111412.84 * Math.cos(latRad);
  
  const dLat = radiusMeters / metersPerDegLat;
  const dLon = radiusMeters / metersPerDegLon;
  
  const coords = [];
  // 6개 꼭짓점을 계산 (30도 오프셋으로 뾰족탑 크리스탈 형태)
  for (let i = 0; i < 6; i++) {
    const angle = (Math.PI / 3) * i + Math.PI / 6;
    coords.push([
      Number((centerLon + dLon * Math.cos(angle)).toFixed(6)),
      Number((centerLat + dLat * Math.sin(angle)).toFixed(6))
    ]);
  }
  coords.push(coords[0]); // Polygon 닫기
  return coords;
}

// GeoJSON 변환 헬퍼 함수 (슬림 헥사곤 크리스탈 타워 Polygon 생성)
function formatGridToGeoJSON(gridItems) {
  if (!gridItems || gridItems.length === 0) {
    return { type: 'FeatureCollection', features: [] };
  }
  return {
    type: 'FeatureCollection',
    features: gridItems.map((item) => {
      let minLon = item.min_lon;
      let minLat = item.min_lat;
      let maxLon = item.max_lon;
      let maxLat = item.max_lat;

      // 좌표 누락 시 100m 정밀 셀 폭(약 경도 0.00112°, 위도 0.00090°) 안전 폴백
      if (minLon == null || maxLon == null || minLat == null || maxLat == null) {
        const dLon = 0.00056;
        const dLat = 0.00045;
        minLon = item.center_lon - dLon;
        maxLon = item.center_lon + dLon;
        minLat = item.center_lat - dLat;
        maxLat = item.center_lat + dLat;
      }

      // 우아하고 역동적인 높이 스케일링 (최소 14m ~ 점포수에 비례하는 드라마틱한 3D 스카이라인)
      const virtualHeight = Math.max(14.0, Number((Math.pow(item.total_stores, 0.92) * 8.2).toFixed(1)));
      // 인접 셀 간 여백(Gutter)을 남겨 답답한 시멘트 벽 느낌을 없애고 세련된 타워로 렌더링
      const hexCoordinates = createHexagonCoordinates(item.center_lon, item.center_lat, 35);

      return {
        type: 'Feature',
        geometry: {
          type: 'Polygon',
          coordinates: [hexCoordinates]
        },
        properties: {
          grid_id: item.grid_id,
          sigungu_code: item.sigungu_code,
          center_lon: item.center_lon,
          center_lat: item.center_lat,
          min_lon: minLon,
          min_lat: minLat,
          max_lon: maxLon,
          max_lat: maxLat,
          total_stores: item.total_stores,
          brand_stores: item.brand_stores,
          top_category_name: item.top_category_name,
          column_height_m: virtualHeight,
          column_height_raw_m: item.column_height_m || (item.total_stores * 8.5)
        }
      };
    })
  };
}

// GeoJSON 변환 헬퍼 함수 (광역 조망용 정밀 중심점 Point 생성)
function formatGridToPointsGeoJSON(gridItems) {
  if (!gridItems || gridItems.length === 0) {
    return { type: 'FeatureCollection', features: [] };
  }
  return {
    type: 'FeatureCollection',
    features: gridItems.map((item) => {
      const virtualHeight = Number((item.total_stores * 3.0).toFixed(1));
      return {
        type: 'Feature',
        geometry: {
          type: 'Point',
          coordinates: [item.center_lon, item.center_lat]
        },
        properties: {
          grid_id: item.grid_id,
          sigungu_code: item.sigungu_code,
          center_lon: item.center_lon,
          center_lat: item.center_lat,
          min_lon: item.min_lon ?? (item.center_lon - 0.00056),
          min_lat: item.min_lat ?? (item.center_lat - 0.00045),
          max_lon: item.max_lon ?? (item.center_lon + 0.00056),
          max_lat: item.max_lat ?? (item.center_lat + 0.00045),
          total_stores: item.total_stores,
          brand_stores: item.brand_stores,
          top_category_name: item.top_category_name,
          column_height_m: virtualHeight,
          column_height_raw_m: item.column_height_m || (item.total_stores * 8.5)
        }
      };
    })
  };
}

// 2D 바닥 밀집 풋프린트 GeoJSON: 지표면에 붙는 100m 셀 사각형 (3D 기둥과 달리 아무것도 가리지 않음)
function formatGridToFootprintGeoJSON(gridItems) {
  if (!gridItems || gridItems.length === 0) return EMPTY_FEATURE_COLLECTION;
  return {
    type: 'FeatureCollection',
    features: gridItems.map((item) => {
      const dLon = 0.00056;
      const dLat = 0.00045;
      const minLon = item.min_lon ?? (item.center_lon - dLon);
      const maxLon = item.max_lon ?? (item.center_lon + dLon);
      const minLat = item.min_lat ?? (item.center_lat - dLat);
      const maxLat = item.max_lat ?? (item.center_lat + dLat);
      return {
        type: 'Feature',
        geometry: {
          type: 'Polygon',
          coordinates: [[[minLon, minLat], [maxLon, minLat], [maxLon, maxLat], [minLon, maxLat], [minLon, minLat]]]
        },
        properties: {
          grid_id: item.grid_id,
          sigungu_code: item.sigungu_code,
          center_lon: item.center_lon,
          center_lat: item.center_lat,
          total_stores: item.total_stores,
          brand_stores: item.brand_stores,
          top_category_name: item.top_category_name,
          column_height_m: Number((item.total_stores * 3.0).toFixed(1))
        }
      };
    })
  };
}

const COLUMN_LAYER_IDS = ['density-grid-3d-columns', 'density-grid-3d-base-line', 'density-grid-3d-highlight'];
const FOOTPRINT_LAYER_IDS = ['density-grid-2d-fill', 'density-grid-2d-line'];

// 격자 레이어 가시성 일괄 동기화: 3D 렌즈가 꺼져 있으면 기둥 대신 2D 풋프린트만 표시
function syncGridLayerVisibility(map, { hasData, gridVisible, extrusion }) {
  if (!map) return;
  const show = hasData && gridVisible;
  const setVis = (id, visible) => {
    if (map.getLayer(id)) map.setLayoutProperty(id, 'visibility', visible ? 'visible' : 'none');
  };
  COLUMN_LAYER_IDS.forEach((id) => setVis(id, show && extrusion));
  FOOTPRINT_LAYER_IDS.forEach((id) => setVis(id, show && !extrusion));
  setVis('density-grid-overview-points', show);
}

// 격자 데이터 기반 반응형 fitBounds 공통 헬퍼
function fitGridBounds(map, items, is3D = null, customZoom = null) {
  if (!map || !items || items.length === 0) return;
  let minLon = Infinity, minLat = Infinity, maxLon = -Infinity, maxLat = -Infinity;
  for (let i = 0; i < items.length; i++) {
    const item = items[i];
    if (item.center_lon < minLon) minLon = item.center_lon;
    if (item.center_lon > maxLon) maxLon = item.center_lon;
    if (item.center_lat < minLat) minLat = item.center_lat;
    if (item.center_lat > maxLat) maxLat = item.center_lat;
  }
  if (minLon === Infinity || maxLon === -Infinity) return;

  const lonSpan = maxLon - minLon;
  const latSpan = maxLat - minLat;
  const targetMaxZoom = lonSpan > 0.3 || latSpan > 0.3 ? 11.8 : (lonSpan > 0.1 ? 13.2 : 14.0);

  const isMobile = typeof window !== 'undefined' && window.innerWidth <= 768;
  const fitPadding = isMobile
    ? { top: 75, bottom: 45, left: 20, right: 20 }
    : { top: 75, bottom: 65, left: 65, right: 65 };

  const currentPitch = map.getPitch ? map.getPitch() : 0.0;
  const shouldUse3D = is3D !== null ? is3D : (currentPitch > 10.0);
  const prefersReducedMotion = typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  map.fitBounds(
    [[minLon, minLat], [maxLon, maxLat]],
    {
      padding: fitPadding,
      pitch: shouldUse3D ? 52.0 : 0.0,
      bearing: shouldUse3D ? -25.0 : 0.0,
      maxZoom: customZoom !== null ? customZoom : targetMaxZoom,
      duration: prefersReducedMotion ? 0 : 800,
      essential: true
    }
  );
}

// 안전한 DOM 팝업 노드 생성 함수 (XSS 방지)
function createPopupElement(props, regionName = '선택 지역', sedaReferenceMonth = null, categoryName = null) {
  const popupEl = document.createElement('div');
  popupEl.className = 'map-popup-card';

  const headerEl = document.createElement('div');
  headerEl.className = 'popup-header';
  const gridTag = props.grid_id ? ` [${props.grid_id}]` : '';
  const catPrefix = categoryName && categoryName !== '전체' ? ` · ${categoryName}` : '';
  headerEl.textContent = `${regionName}${catPrefix} 100m 격자 분석${gridTag}`;
  popupEl.appendChild(headerEl);

  // 외식업 점포수 (업종 선택 시 해당 업종 점포수)
  const item1 = document.createElement('div');
  item1.className = 'popup-item';
  const k1 = document.createElement('span');
  k1.className = 'popup-key';
  k1.textContent = categoryName && categoryName !== '전체' ? `${categoryName} 점포:` : '총 외식업 점포:';
  const v1 = document.createElement('span');
  v1.className = 'popup-val highlight';
  v1.textContent = `${props.total_stores}개소`;
  item1.append(k1, v1);
  popupEl.appendChild(item1);

  // 브랜드 점포수
  const item2 = document.createElement('div');
  item2.className = 'popup-item';
  const k2 = document.createElement('span');
  k2.className = 'popup-key';
  k2.textContent = '브랜드 연결 점포:';
  const v2 = document.createElement('span');
  v2.className = 'popup-val';
  v2.textContent = `${props.brand_stores}개소`;
  item2.append(k2, v2);
  popupEl.appendChild(item2);

  // 주요 업종 (해당 격자 최다 점포 업종)
  const item3 = document.createElement('div');
  item3.className = 'popup-item';
  const k3 = document.createElement('span');
  k3.className = 'popup-key';
  k3.textContent = '최다 점포 업종:';
  const v3 = document.createElement('span');
  v3.className = 'popup-val';
  v3.textContent = props.top_category_name || '-';
  item3.append(k3, v3);
  popupEl.appendChild(item3);

  // 데이터 성격 명시 안내 (통계 왜곡 방지)
  const subEl = document.createElement('div');
  subEl.className = 'popup-sub';
  const monthTag = sedaReferenceMonth ? `소진공 ${sedaReferenceMonth}` : '소진공 기준월 확인 불가';
  subEl.textContent = `* 본 격자는 ${monthTag} ${regionName} 외식업 전체 점포 공간 수치입니다. 지도를 확대하면 격자 안의 개별 점포를 확인할 수 있습니다.`;
  popupEl.appendChild(subEl);

  return popupEl;
}

function appendPopupRow(parent, label, value, className = '') {
  const row = document.createElement('div');
  row.className = 'popup-item';
  const key = document.createElement('span');
  key.className = 'popup-key';
  key.textContent = label;
  const val = document.createElement('span');
  val.className = `popup-val ${className}`.trim();
  val.textContent = value || '-';
  row.append(key, val);
  parent.appendChild(row);
}

// 점포 내부 코드(BRAND_LINKED 등)를 사용자 친화적 한글 설명으로 변환
function formatStoreVerificationText(store, ui) {
  const off = store.brand_officiality;
  const op = store.operation_type;
  const opText =
    op === 'FRANCHISED'
      ? '가맹점'
      : op === 'COMPANY_OPERATED'
        ? '직영·본점 추정'
        : ui?.operation_badge?.label || (off === 'INDEPENDENT' ? '단독 운영 매장' : '일반 매장');

  if (off === 'FRANCHISE_CONFIRMED') {
    return `공정위 정보공개서 대조 완료 · ${opText}`;
  }
  if (off === 'BRAND_CONFIRMED') {
    return `다점포 브랜드 확인 · ${opText}`;
  }
  if (off === 'UNVERIFIED') {
    return `전국 10개 이상 동일상호 군집 후보 · ${opText}`;
  }
  return '프랜차이즈 미소속 개인·독립 외식점포';
}

// 개별 점포 상세 팝업도 textContent만 사용해 API 문자열을 HTML로 해석하지 않는다.
function createStorePopupElement(detail, loadingText = null, onInspectBrand = null) {
  const popupEl = document.createElement('div');
  popupEl.className = 'map-popup-card store-popup-card';

  const store = detail?.store || {};
  const ui = detail?.ui_presentation || {};

  // 상단 배지 바 (점포 유형 컬러 배지 + 업종 대/중분류 태그)
  if (!loadingText && store.category_major_name) {
    const badgeBar = document.createElement('div');
    badgeBar.className = 'store-popup-badge-bar';

    const storeType = getStoreType(store);
    const typeMeta = STORE_TYPE_META[storeType] || STORE_TYPE_META.indie;
    const typeBadge = document.createElement('span');
    typeBadge.className = `store-popup-type-badge ${storeType}`;
    typeBadge.textContent =
      store.brand_officiality === 'FRANCHISE_CONFIRMED'
        ? '공식 가맹 브랜드'
        : typeMeta.label;

    const catBadge = document.createElement('span');
    catBadge.className = 'store-popup-cat-badge';
    catBadge.textContent = store.category_mid_name
      ? `${store.category_major_name} › ${store.category_mid_name}`
      : store.category_major_name;

    badgeBar.append(typeBadge, catBadge);
    popupEl.appendChild(badgeBar);
  }

  const header = document.createElement('div');
  header.className = 'popup-header';
  const fullTitle = store.brch_nm ? `${store.bizes_nm || ''} ${store.brch_nm}` : (store.bizes_nm || '개별 점포 상세');
  header.textContent = fullTitle;
  popupEl.appendChild(header);

  if (loadingText) {
    const status = document.createElement('div');
    status.className = 'popup-sub';
    status.textContent = loadingText;
    popupEl.appendChild(status);
    return popupEl;
  }

  const isBrandStore = Boolean(
    store.brand_name_std &&
    store.primary_brand_id &&
    ['FRANCHISE_CONFIRMED', 'BRAND_CONFIRMED', 'UNVERIFIED'].includes(store.brand_officiality)
  );

  appendPopupRow(popupEl, '소속 브랜드:', isBrandStore ? store.brand_name_std : '개인·독립 점포 (비프랜차이즈)', isBrandStore ? 'highlight' : '');
  if (store.brch_nm) {
    appendPopupRow(popupEl, '지점명:', store.brch_nm);
  }
  const addrText = store.rdnm_adr || store.lno_adr || '주소 미확인';
  appendPopupRow(popupEl, '소재지 주소:', addrText);
  appendPopupRow(popupEl, '운영·검증:', formatStoreVerificationText(store, ui), 'store-axis-value');

  [ui.divergent_alert, ui.multi_brand_alert].filter(Boolean).forEach((message) => {
    const alert = document.createElement('div');
    alert.className = 'store-popup-alert';
    alert.textContent = message;
    popupEl.appendChild(alert);
  });

  // 하단 사용자 액션 버튼 영역 (도로명주소 복사 + 브랜드 전국/지역 분포 바로가기)
  const actionsWrap = document.createElement('div');
  actionsWrap.className = 'store-popup-actions';

  if (store.rdnm_adr || store.lno_adr) {
    const copyBtn = document.createElement('button');
    copyBtn.type = 'button';
    copyBtn.className = 'store-popup-action-btn secondary';
    copyBtn.textContent = '📋 주소 복사';
    copyBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      const targetText = store.rdnm_adr || store.lno_adr || '';
      if (navigator.clipboard?.writeText) {
        navigator.clipboard.writeText(targetText).then(() => {
          copyBtn.textContent = '✓ 주소 복사됨';
          setTimeout(() => {
            copyBtn.textContent = '📋 주소 복사';
          }, 1800);
        }).catch(() => {});
      }
    });
    actionsWrap.appendChild(copyBtn);
  }

  if (isBrandStore && typeof onInspectBrand === 'function') {
    const brandBtn = document.createElement('button');
    brandBtn.type = 'button';
    brandBtn.className = 'store-popup-action-btn primary';
    brandBtn.textContent = `📊 '${store.brand_name_std}' 전국·지역 분포`;
    brandBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      onInspectBrand({
        internal_brand_id: store.primary_brand_id,
        brand_name_std: store.brand_name_std,
        brand_officiality: store.brand_officiality,
        category_major_id: store.category_major_id,
        category_mid_id: store.category_mid_id
      });
    });
    actionsWrap.appendChild(brandBtn);
  }

  if (actionsWrap.childNodes.length > 0) {
    popupEl.appendChild(actionsWrap);
  }

  return popupEl;
}

// 광역(전국 시도 / 시도 내 시군구) 버블 마커용 지역명 축약 헬퍼
function formatShortRegionLabel(regionName = '', regionType = 'SIDO') {
  const raw = String(regionName || '').trim();
  if (!raw) return '지역';
  if (regionType === 'SIDO') {
    if (raw.startsWith('충청북')) return '충북';
    if (raw.startsWith('충청남')) return '충남';
    if (raw.startsWith('전라북') || raw.startsWith('전북')) return '전북';
    if (raw.startsWith('전라남')) return '전남';
    if (raw.startsWith('경상북')) return '경북';
    if (raw.startsWith('경상남')) return '경남';
    return raw
      .replace(/특별자치도|특별자치시|특별시|광역시|자치도|도$/g, '')
      .trim() || raw;
  }
  const parts = raw.split(/\s+/);
  if (parts.length >= 2) {
    return parts.slice(1).join(' ');
  }
  return raw;
}

export default function MapContainer({ 
  gridData, 
  macroBubbles = [],
  macroBubblesLoading = false,
  onSelectRegionBubble = null,
  selectedHotspot, 
  selectedCategory = 'CAT_MAJ_01', 
  selectedMidCategory = null,
  selectedMidCategoryLabel = '',
  selectedRegionInfo = null,
  gridLoading = false,
  gridError = null,
  regionLoading = false,
  onRetryGrid,
  onMapReady,
  sedaReferenceMonth = null,
  isFtcDrawerOpen = false,
  onToggleFtcDrawer = null,
  isHotspotsVisible = true,
  onToggleHotspots = null,
  onVisibleStoresChange = null,
  onActiveStoreChange = null,
  focusStoreRequest = null,
  storeTypeFilter = 'all',
  storeSearchQuery = '',
  onInspectBrand = null
}) {
  const mapContainerRef = useRef(null);
  const mapInstanceRef = useRef(null);
  const activePopupRef = useRef(null);
  const hoverTipRef = useRef(null);
  const openStoreDetailRef = useRef(null);
  const onVisibleStoresChangeRef = useRef(onVisibleStoresChange);
  const onActiveStoreChangeRef = useRef(onActiveStoreChange);
  const onInspectBrandRef = useRef(onInspectBrand);
  const onSelectRegionBubbleRef = useRef(onSelectRegionBubble);
  const macroBubbleMarkersRef = useRef([]);
  const rawStoreFeaturesRef = useRef([]);
  const storeTypeFilterRef = useRef(storeTypeFilter);
  const storeSearchQueryRef = useRef(storeSearchQuery);
  const hotspotMarkerRef = useRef(null);
  const isMapLoadedRef = useRef(false);
  const gridDataRef = useRef(gridData);
  const selectedRegionInfoRef = useRef(selectedRegionInfo);
  const selectedHotspotRef = useRef(selectedHotspot);
  const sedaReferenceMonthRef = useRef(sedaReferenceMonth);
  const selectedCategoryRef = useRef(selectedCategory);
  const selectedMidCategoryRef = useRef(selectedMidCategory);
  const storeAbortRef = useRef(null);
  const storeDetailAbortRef = useRef(null);
  const storeRequestIdRef = useRef(0);
  const isStoreLayerVisibleRef = useRef(true);

  // Phase 5C-Vis Step 3 인터랙티브 상태 관리
  // 기본은 2D 탑뷰: 3D 기둥이 뒤편 점포를 가리지 않도록, 3D는 사용자가 켜는 선택 렌즈로만 제공
  const [is3DMode, setIs3DMode] = useState(false);
  const is3DModeRef = useRef(false);
  const [isExtrusionEnabled, setIsExtrusionEnabled] = useState(false);
  const isExtrusionEnabledRef = useRef(false);
  const [isGridVisible, setIsGridVisible] = useState(true);
  const [isStoreLayerVisible, setIsStoreLayerVisible] = useState(true);
  const [colorMode, setColorMode] = useState('density'); // 'density' | 'category'
  const [hoveredGrid, setHoveredGrid] = useState(null);
  const [storeLayerStatus, setStoreLayerStatus] = useState({ state: 'zoom-required', count: 0, limited: false, error: null });

  useEffect(() => {
    sedaReferenceMonthRef.current = sedaReferenceMonth;
  }, [sedaReferenceMonth]);

  useEffect(() => {
    onVisibleStoresChangeRef.current = onVisibleStoresChange;
    onActiveStoreChangeRef.current = onActiveStoreChange;
    onInspectBrandRef.current = onInspectBrand;
    onSelectRegionBubbleRef.current = onSelectRegionBubble;
  }, [onVisibleStoresChange, onActiveStoreChange, onInspectBrand, onSelectRegionBubble]);

  useEffect(() => {
    isExtrusionEnabledRef.current = isExtrusionEnabled;
  }, [isExtrusionEnabled]);

  useEffect(() => {
    selectedCategoryRef.current = selectedCategory;
    selectedMidCategoryRef.current = selectedMidCategory;
  }, [selectedCategory, selectedMidCategory]);

  // 현재 선택된 업종 정보 (상단 HUD 안내용)
  const currentCategory = CATEGORY_MAJOR_LIST.find((c) => c.id === selectedCategory) || CATEGORY_MAJOR_LIST[0];

  // URL 쿼리 파라미터 기반 검증 모드 읽기
  const urlParams = typeof window !== 'undefined' ? new URLSearchParams(window.location.search) : null;
  const customZoom = urlParams && urlParams.get('zoom') ? parseFloat(urlParams.get('zoom')) : null;
  const shouldOpenPopup = urlParams && urlParams.get('open_popup') === 'true';

  useEffect(() => {
    gridDataRef.current = gridData;
    if (typeof window !== 'undefined') {
      window.__currentGridCount = gridData ? gridData.length : 0;
      window.__currentGridData = gridData || [];
    }
  }, [gridData]);

  useEffect(() => {
    selectedHotspotRef.current = selectedHotspot;
  }, [selectedHotspot]);

  // 글로벌 상태 동기화 (CDP 테스트 및 자동화 검증용)
  useEffect(() => {
    is3DModeRef.current = is3DMode;
    if (typeof window !== 'undefined') {
      window.__is3DMode = is3DMode;
      window.__isExtrusionEnabled = isExtrusionEnabled;
      window.__isGridVisible = isGridVisible;
      window.__isStoreLayerVisible = isStoreLayerVisible;
      window.__colorMode = colorMode;
      window.__hoveredGrid = hoveredGrid;
    }
  }, [is3DMode, isExtrusionEnabled, isGridVisible, isStoreLayerVisible, colorMode, hoveredGrid]);

  useEffect(() => {
    isStoreLayerVisibleRef.current = isStoreLayerVisible;
  }, [isStoreLayerVisible]);

  // 공정위 드로어 열림/닫힘 전환 시 MapLibre 캔버스 리사이즈
  useEffect(() => {
    if (mapInstanceRef.current) {
      const timer = setTimeout(() => {
        mapInstanceRef.current?.resize();
      }, 320);
      return () => clearTimeout(timer);
    }
  }, [isFtcDrawerOpen]);

  // 안전한 팝업 표출 헬퍼 함수
  const displayPopup = useCallback((map, coords, props) => {
    if (activePopupRef.current) {
      activePopupRef.current.remove();
    }
    const regionName = selectedRegionInfoRef.current?.region_name || '선택 지역';
    const catObj = CATEGORY_MAJOR_LIST.find((c) => c.id === selectedCategoryRef.current);
    const catName = catObj && catObj.id !== 'ALL' ? catObj.name : null;
    const popupEl = createPopupElement(props, regionName, sedaReferenceMonthRef.current, catName);
    const popup = new maplibregl.Popup({ offset: 12, closeButton: true })
      .setLngLat(coords)
      .setDOMContent(popupEl)
      .addTo(map);

    activePopupRef.current = popup;
    window.__activePopup = popup;
  }, []);

  // 밀집도 소스 데이터 갱신 (3D 기둥 폴리곤 및 개요 포인트)
  const updateGridSource = useCallback((items) => {
    const map = mapInstanceRef.current;
    if (!map || !isMapLoadedRef.current) return;
    const polySource = map.getSource('density-grid-source');
    if (polySource) {
      polySource.setData(formatGridToGeoJSON(items));
    }
    const ptSource = map.getSource('density-grid-overview-source');
    if (ptSource) {
      ptSource.setData(formatGridToPointsGeoJSON(items));
    }
    const footprintSource = map.getSource('density-grid-2d-source');
    if (footprintSource) {
      footprintSource.setData(formatGridToFootprintGeoJSON(items));
    }
  }, []);

  // 현재 화면 점포 목록을 상위(점포 탐색기)로 전달
  const emitStores = useCallback((features, status) => {
    if (!onVisibleStoresChangeRef.current) return;
    onVisibleStoresChangeRef.current(features.map((f) => f.properties || {}), status);
  }, []);

  const clearStoreSource = useCallback((map) => {
    rawStoreFeaturesRef.current = [];
    const source = map?.getSource('store-points-source');
    if (source) source.setData(EMPTY_FEATURE_COLLECTION);
    if (typeof window !== 'undefined') {
      window.__currentStoreFeatures = [];
      window.__storeSourceData = EMPTY_FEATURE_COLLECTION;
    }
  }, []);

  // 유형 필터(전체/프랜차이즈/후보/독립) 및 검색어를 지도 위의 점포 핀에 즉시 반영
  const syncStoreSourceWithFilter = useCallback((map) => {
    const raw = rawStoreFeaturesRef.current || [];
    const tf = storeTypeFilterRef.current || 'all';
    const q = (storeSearchQueryRef.current || '').trim().toLowerCase();
    const filtered = raw.filter((f) => {
      const p = f.properties || {};
      if (tf !== 'all' && getStoreType(p) !== tf) return false;
      if (q) {
        const hay = `${p.bizes_nm || ''} ${p.brch_nm || ''} ${p.brand_name_std || ''} ${p.category_mid_name || ''}`.toLowerCase();
        if (!hay.includes(q)) return false;
      }
      return true;
    });
    map?.getSource('store-points-source')?.setData({ type: 'FeatureCollection', features: filtered });
    if (typeof window !== 'undefined') {
      window.__currentStoreFeatures = filtered;
      window.__storeSourceData = { type: 'FeatureCollection', features: filtered };
    }
    return filtered;
  }, []);

  const loadVisibleStores = useCallback(async (
    map,
    category = selectedCategoryRef.current,
    midCategory = selectedMidCategoryRef.current
  ) => {
    if (!map || !isMapLoadedRef.current) return;
    storeAbortRef.current?.abort();
    const requestId = ++storeRequestIdRef.current;

    if (!isStoreLayerVisibleRef.current) {
      clearStoreSource(map);
      setStoreLayerStatus({ state: 'hidden', count: 0, limited: false, error: null });
      emitStores([], 'hidden');
      return;
    }

    if (map.getZoom() < STORE_MIN_ZOOM) {
      clearStoreSource(map);
      setStoreLayerStatus({ state: 'zoom-required', count: 0, limited: false, error: null });
      emitStores([], 'zoom-required');
      return;
    }

    const controller = new AbortController();
    storeAbortRef.current = controller;
    const bounds = map.getBounds();
    const reqEntry = {
      requestId,
      category,
      bbox: [bounds.getWest(), bounds.getSouth(), bounds.getEast(), bounds.getNorth()],
      requestedAt: performance.now(),
      discarded: false,
      applied: false,
      featureCount: 0
    };
    if (typeof window !== 'undefined') {
      window.__storeRequestHistory = window.__storeRequestHistory || [];
      window.__storeRequestHistory.push(reqEntry);
    }
    setStoreLayerStatus((current) => ({ ...current, state: 'loading', error: null }));

    try {
      const geojson = await fetchStoresByBbox({
        minLon: bounds.getWest(),
        minLat: bounds.getSouth(),
        maxLon: bounds.getEast(),
        maxLat: bounds.getNorth()
      }, category, controller.signal, STORE_LIMIT, midCategory);

      if (requestId !== storeRequestIdRef.current) {
        reqEntry.discarded = true;
        reqEntry.discardedReason = 'superseded_by_newer_request';
        if (typeof window !== 'undefined') {
          window.__storeDiscardedCount = (window.__storeDiscardedCount || 0) + 1;
        }
        return;
      }
      const features = Array.isArray(geojson.features) ? geojson.features : [];
      rawStoreFeaturesRef.current = features;
      const filtered = syncStoreSourceWithFilter(map);
      reqEntry.applied = true;
      reqEntry.appliedAtLatestRequestId = storeRequestIdRef.current;
      reqEntry.wasStale = (requestId !== storeRequestIdRef.current);
      reqEntry.featureCount = features.length;
      setStoreLayerStatus({
        state: filtered.length ? 'ready' : 'empty',
        count: filtered.length,
        totalCount: features.length,
        limited: features.length === STORE_LIMIT,
        error: null
      });
      emitStores(features, features.length ? 'ready' : 'empty');
    } catch (error) {
      if (error?.name === 'AbortError' || requestId !== storeRequestIdRef.current) {
        reqEntry.discarded = true;
        if (typeof window !== 'undefined') {
          window.__storeDiscardedCount = (window.__storeDiscardedCount || 0) + 1;
        }
        return;
      }
      clearStoreSource(map);
      setStoreLayerStatus({ state: 'error', count: 0, limited: false, error: error.message });
      emitStores([], 'error');
    }
  }, [clearStoreSource, emitStores, syncStoreSourceWithFilter]);

  // 검색어 또는 점포 유형 필터 변경 시 지도 위 핀을 즉시 재필터링 (줌 14 미만에서 검색 시 자동 확대)
  useEffect(() => {
    storeTypeFilterRef.current = storeTypeFilter;
    storeSearchQueryRef.current = storeSearchQuery;
    const map = mapInstanceRef.current;
    if (!map || !isMapLoadedRef.current) return;
    if (storeSearchQuery.trim() && map.getZoom() < STORE_MIN_ZOOM) {
      map.easeTo({ zoom: 14.5, duration: 500, essential: true });
      return;
    }
    if (map.getZoom() >= STORE_MIN_ZOOM && isStoreLayerVisibleRef.current) {
      const filtered = syncStoreSourceWithFilter(map);
      setStoreLayerStatus((prev) => ({
        ...prev,
        state: filtered.length ? 'ready' : 'empty',
        count: filtered.length
      }));
    }
  }, [storeTypeFilter, storeSearchQuery, syncStoreSourceWithFilter]);

  const handleToggleGrid = useCallback(() => {
    const map = mapInstanceRef.current;
    if (!map) return;
    const nextVisible = !isGridVisible;
    setIsGridVisible(nextVisible);
    syncGridLayerVisibility(map, {
      hasData: Boolean(gridDataRef.current && gridDataRef.current.length > 0),
      gridVisible: nextVisible,
      extrusion: isExtrusionEnabledRef.current
    });
    if (!nextVisible) setHoveredGrid(null);
  }, [isGridVisible]);

  const handleToggleStores = useCallback(() => {
    const map = mapInstanceRef.current;
    if (!map) return;
    const nextVisible = !isStoreLayerVisible;
    isStoreLayerVisibleRef.current = nextVisible;
    setIsStoreLayerVisible(nextVisible);
    if (map.getLayer('store-points')) {
      map.setLayoutProperty('store-points', 'visibility', nextVisible ? 'visible' : 'none');
    }
    if (nextVisible) {
      loadVisibleStores(map);
    } else {
      storeAbortRef.current?.abort();
      storeRequestIdRef.current += 1;
      clearStoreSource(map);
      setStoreLayerStatus({ state: 'hidden', count: 0, limited: false, error: null });
      emitStores([], 'hidden');
    }
  }, [clearStoreSource, emitStores, isStoreLayerVisible, loadVisibleStores]);

  // 1. 3D / 2D 시점 전환 핸들러
  const handleToggle3D = useCallback(() => {
    const map = mapInstanceRef.current;
    if (!map) return;
    const next3D = !is3DMode;
    const prefersReducedMotion = typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (prefersReducedMotion) {
      map.jumpTo({
        pitch: next3D ? 52.0 : 0.0,
        bearing: next3D ? -25.0 : 0.0
      });
    } else if (next3D) {
      map.easeTo({
        pitch: 52.0,
        bearing: -25.0,
        duration: 800,
        essential: true
      });
    } else {
      map.easeTo({
        pitch: 0.0,
        bearing: 0.0,
        duration: 800,
        essential: true
      });
    }
  }, [is3DMode]);

  // 2. 3D 기둥 렌즈 켜기/끄기 핸들러 (켜면 경사 시점으로, 끄면 2D 탑뷰 + 바닥 풋프린트로 복귀)
  const handleToggleExtrusion = useCallback(() => {
    const map = mapInstanceRef.current;
    if (!map) return;
    const nextExtrusion = !isExtrusionEnabled;
    isExtrusionEnabledRef.current = nextExtrusion;
    setIsExtrusionEnabled(nextExtrusion);
    syncGridLayerVisibility(map, {
      hasData: Boolean(gridDataRef.current && gridDataRef.current.length > 0),
      gridVisible: isGridVisible,
      extrusion: nextExtrusion
    });
    const prefersReducedMotion = typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const camera = nextExtrusion
      ? { pitch: 52.0, bearing: -25.0 }
      : { pitch: 0.0, bearing: 0.0 };
    if (prefersReducedMotion) map.jumpTo(camera);
    else map.easeTo({ ...camera, duration: 800, essential: true });
  }, [isExtrusionEnabled, isGridVisible]);

  // 3. 색상 테마 전환 핸들러 (밀집도 ↔ 8대 업종별 고유 색상)
  const handleToggleColorMode = useCallback(() => {
    const map = mapInstanceRef.current;
    if (!map) return;
    const nextColorMode = colorMode === 'density' ? 'category' : 'density';
    setColorMode(nextColorMode);

    const activeRamp = nextColorMode === 'category' ? CATEGORY_COLOR_RAMP : DENSITY_COLOR_RAMP;

    if (map.getLayer('density-grid-3d-columns')) {
      map.setPaintProperty('density-grid-3d-columns', 'fill-extrusion-color', activeRamp);
    }
    if (map.getLayer('density-grid-2d-fill')) {
      map.setPaintProperty('density-grid-2d-fill', 'fill-color', activeRamp);
    }
    if (map.getLayer('density-grid-overview-points')) {
      map.setPaintProperty('density-grid-overview-points', 'circle-color', activeRamp);
    }
  }, [colorMode]);

  // 4. 선택 지역 전체 조망 시점 복귀 핸들러
  const handleResetView = useCallback(() => {
    const map = mapInstanceRef.current;
    if (!map) return;
    if (gridDataRef.current && gridDataRef.current.length > 0) {
      fitGridBounds(map, gridDataRef.current, is3DModeRef.current);
    }
  }, []);

  // 핫스팟 카메라 이동 및 마커 반영 함수
  const applySelectedHotspot = useCallback((hotspot, isInitial = false, skipCamera = false) => {
    const map = mapInstanceRef.current;
    if (!map || !hotspot) return;

    const { center_lon, center_lat, pitch, bearing, zoom, hotspot_name } = hotspot;
    const targetZoom = customZoom !== null ? customZoom : (zoom !== undefined ? zoom : 15.0);
    // 2D 탑뷰가 기본: 3D 렌즈가 켜져 있을 때만 핫스팟의 경사 카메라 값을 사용
    const use3D = is3DModeRef.current;
    const targetPitch = use3D ? (isInitial ? 52.0 : (pitch !== undefined ? pitch : 52.0)) : 0.0;
    const targetBearing = use3D ? (isInitial ? -25.0 : (bearing !== undefined ? bearing : -25.0)) : 0.0;

    const prefersReducedMotion = typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    if (!skipCamera) {
      if (prefersReducedMotion || isInitial) {
        map.jumpTo({
          center: [center_lon, center_lat],
          pitch: targetPitch,
          bearing: targetBearing,
          zoom: targetZoom
        });
      } else {
        // 시네마틱 드론 선회 비행: 카메라가 포물선을 그리며 상권 중심을 향해 부드럽게 회전 하강
        const currentB = typeof map.getBearing === 'function' ? map.getBearing() : -25.0;
        const targetB = use3D ? (bearing !== undefined ? bearing : (currentB - 35.0)) : 0.0;
        map.flyTo({
          center: [center_lon, center_lat],
          pitch: targetPitch,
          bearing: targetB,
          zoom: targetZoom,
          speed: 0.85,
          curve: 1.5,
          essential: true,
          easing: (t) => t * (2 - t)
        });
      }
    }

    if (hotspotMarkerRef.current) {
      hotspotMarkerRef.current.remove();
    }

    const markerEl = document.createElement('div');
    markerEl.className = 'hotspot-map-marker';

    const pinEl = document.createElement('div');
    pinEl.className = 'marker-pin';

    const labelEl = document.createElement('div');
    labelEl.className = 'marker-label';
    labelEl.textContent = hotspot_name;

    markerEl.appendChild(pinEl);
    markerEl.appendChild(labelEl);

    const marker = new maplibregl.Marker({ element: markerEl })
      .setLngLat([center_lon, center_lat])
      .addTo(map);

    hotspotMarkerRef.current = marker;
  }, [customZoom]);

  // 지도 인스턴스 초기화
  useEffect(() => {
    if (!mapContainerRef.current) return;

    const initialCenter = selectedRegionInfoRef.current?.center_lon && selectedRegionInfoRef.current?.center_lat
      ? [selectedRegionInfoRef.current.center_lon, selectedRegionInfoRef.current.center_lat]
      : (selectedHotspotRef.current 
          ? [selectedHotspotRef.current.center_lon, selectedHotspotRef.current.center_lat]
          : DEFAULT_CENTER);
    const initialZoom = customZoom !== null ? customZoom : 14.0;

    const map = new maplibregl.Map({
      container: mapContainerRef.current,
      style: OSM_LIGHT_STYLE,
      center: initialCenter,
      zoom: initialZoom,
      pitch: 0.0,
      bearing: 0.0,
      attributionControl: true
    });

    map.addControl(new maplibregl.NavigationControl({ visualizePitch: true }), 'top-right');

    // 사용자가 직접 기울이거나 레일 버튼으로 전환해도 3D 상태 표시가 실제 pitch와 일치하도록 동기화
    map.on('pitchend', () => {
      const tilted = map.getPitch() > 10.0;
      is3DModeRef.current = tilted;
      setIs3DMode(tilted);
    });

    let lastIsMobile = typeof window !== 'undefined' ? (window.innerWidth <= 768) : false;
    const handleResize = () => {
      if (!map) return;
      map.resize();
      const currentIsMobile = window.innerWidth <= 768;
      if (currentIsMobile !== lastIsMobile) {
        lastIsMobile = currentIsMobile;
        if (gridDataRef.current && gridDataRef.current.length > 0) {
          fitGridBounds(map, gridDataRef.current, is3DModeRef.current);
        }
      }
    };
    window.addEventListener('resize', handleResize);

    let resizeObserver = null;
    if (typeof ResizeObserver !== 'undefined' && mapContainerRef.current) {
      let lastObservedWidth = 0;
      resizeObserver = new ResizeObserver((entries) => {
        if (!map) return;
        map.resize();
        for (const entry of entries) {
          const w = entry.contentRect.width;
          if (lastObservedWidth && Math.abs(w - lastObservedWidth) > 200) {
            if (gridDataRef.current && gridDataRef.current.length > 0) {
              fitGridBounds(map, gridDataRef.current, is3DModeRef.current);
            }
          }
          lastObservedWidth = w;
        }
      });
      resizeObserver.observe(mapContainerRef.current);
    }

    map.on('load', () => {
      mapInstanceRef.current = map;
      isMapLoadedRef.current = true;
      map.resize();
      if (onMapReady) onMapReady(map);

      // 글로벌 디버깅 & FPS 실측 헬퍼 바인딩
      window.__map = map;
      window.__displayPopup = displayPopup;
      window.__displayStorePopup = (coords, detail) => {
        if (activePopupRef.current) activePopupRef.current.remove();
        const popup = new maplibregl.Popup({ offset: 12, closeButton: true, maxWidth: '320px' })
          .setLngLat(coords)
          .setDOMContent(createStorePopupElement(detail))
          .addTo(map);
        activePopupRef.current = popup;
        window.__activePopup = popup;
        return popup;
      };
      window.__fitCurrentGridBounds = () => fitGridBounds(map, gridDataRef.current, is3DModeRef.current);
      window.__applySelectedHotspot = applySelectedHotspot;
      window.__columnHeightFor = (stores) => stores * 3.0;
      window.__getGridFeatures = () => map.querySourceFeatures('density-grid-source');
      window.__getRenderedFeatures = () => map.queryRenderedFeatures({ layers: ['density-grid-3d-columns'] });
      window.__getOverviewFeatures = () => (map.getLayer('density-grid-overview-points') ? map.queryRenderedFeatures({ layers: ['density-grid-overview-points'] }) : []);
      window.__getStoreFeatures = () => {
        const raw = map.querySourceFeatures('store-points-source') || [];
        const seen = new Set();
        const unique = [];
        for (let i = 0; i < raw.length; i++) {
          const id = raw[i].properties?.bizes_id;
          if (id && !seen.has(id)) {
            seen.add(id);
            unique.push(raw[i]);
          }
        }
        return unique;
      };
      window.__getStoreSourceFeatures = () => map.querySourceFeatures('store-points-source');
      window.__getRenderedStoreFeatures = () => map.queryRenderedFeatures({ layers: ['store-points'] });
      window.__areTilesLoaded = () => (map.areTilesLoaded ? map.areTilesLoaded() : true);
      window.__loadVisibleStores = () => loadVisibleStores(map);
      window.__getStoreRequestId = () => storeRequestIdRef.current;
      
      // Step 3 렌더링 성능 실측 헬퍼 (MapLibre 실제 WebGL render 이벤트 기반 실측)
      window.__measureFPS = (durationMs = 2000, withMotion = true) => {
        return new Promise((resolve) => {
          let renderCount = 0;
          let minDelta = Infinity;
          let lastTime = performance.now();
          const startTime = lastTime;

          const onRender = () => {
            renderCount++;
            const now = performance.now();
            const delta = now - lastTime;
            if (delta > 0 && delta < minDelta) minDelta = delta;
            lastTime = now;
          };

          map.on('render', onRender);
          if (withMotion && map.panBy) {
            map.panBy([35, 35], { duration: durationMs, essential: true });
          }

          setTimeout(() => {
            map.off('render', onRender);
            const totalElapsed = (performance.now() - startTime) / 1000;
            const avgFps = Number((renderCount / totalElapsed).toFixed(1));
            const minFps = minDelta !== Infinity && minDelta > 0 ? Number((1000 / minDelta).toFixed(1)) : avgFps;
            resolve({
              renderFrames: renderCount,
              durationMs: Number((totalElapsed * 1000).toFixed(1)),
              avgFps,
              minFps,
              passedDesktop: avgFps >= 45,
              passedMobile: avgFps >= 30,
              measuredViaMapRenderEvent: true,
              testedWithMotion: Boolean(withMotion)
            });
          }, durationMs);
        });
      };
      window.__measureRenderFPS = window.__measureFPS;

      // 45도 방향 광원 설정 (3D 입체감 강화)
      if (map.setLight) {
        map.setLight({
          anchor: 'viewport',
          color: '#ffffff',
          intensity: 0.65,
          position: [1.3, 210, 50]
        });
      }

      // 밀집도 소스 등록 (3D 기둥 폴리곤 및 개요 포인트)
      const initialGeoJSON = formatGridToGeoJSON(gridDataRef.current);
      map.addSource('density-grid-source', {
        type: 'geojson',
        data: initialGeoJSON,
        tolerance: 0
      });

      const initialPointsGeoJSON = formatGridToPointsGeoJSON(gridDataRef.current);
      map.addSource('density-grid-overview-source', {
        type: 'geojson',
        data: initialPointsGeoJSON,
        tolerance: 0
      });

      // 1. 광역 조망 시각화 개요 레이어 (Circle, zoom 6~14.5)
      map.addLayer({
        id: 'density-grid-overview-points',
        type: 'circle',
        source: 'density-grid-overview-source',
        maxzoom: 14.5,
        layout: {
          visibility: (gridDataRef.current && gridDataRef.current.length > 0) ? 'visible' : 'none'
        },
        paint: {
          'circle-radius': [
            'interpolate', ['linear'], ['zoom'],
            6, 2.0,
            7, 2.5,
            8, 3.2,
            10, 4.5,
            13, 6.0,
            14.5, 7.5
          ],
          'circle-color': DENSITY_COLOR_RAMP,
          'circle-opacity': [
            'interpolate', ['linear'], ['zoom'],
            6, 0.90,
            8, 0.88,
            12, 0.85,
            13.5, 0.50,
            14.5, 0.0
          ],
          'circle-stroke-width': 1.5,
          'circle-stroke-color': '#ffffff',
          'circle-stroke-opacity': [
            'interpolate', ['linear'], ['zoom'],
            6, 0.90,
            8, 0.90,
            13, 0.75,
            14.5, 0.0
          ]
        }
      });

      // 2D 바닥 풋프린트 소스 및 레이어 (기본 표시: 지표면에 붙어 도로·점포를 가리지 않음)
      map.addSource('density-grid-2d-source', {
        type: 'geojson',
        data: formatGridToFootprintGeoJSON(gridDataRef.current),
        tolerance: 0
      });
      map.addLayer({
        id: 'density-grid-2d-fill',
        type: 'fill',
        source: 'density-grid-2d-source',
        minzoom: 10.5,
        layout: { visibility: 'none' },
        paint: {
          'fill-color': DENSITY_COLOR_RAMP,
          'fill-opacity': [
            'interpolate', ['linear'], ['zoom'],
            10.5, 0.38,
            13.8, 0.26,
            14.2, 0.12,
            17, 0.08
          ]
        }
      });
      map.addLayer({
        id: 'density-grid-2d-line',
        type: 'line',
        source: 'density-grid-2d-source',
        minzoom: 12,
        layout: { visibility: 'none' },
        paint: {
          'line-color': '#ffffff',
          'line-width': 0.8,
          'line-opacity': 0.55
        }
      });

      // 2. 소진공 100m 정밀 격자 MapLibre fill-extrusion 3D 슬림 헥사곤 기둥 레이어 (선택 렌즈: 기본 숨김)
      map.addLayer({
        id: 'density-grid-3d-columns',
        type: 'fill-extrusion',
        source: 'density-grid-source',
        minzoom: 10.5,
        layout: {
          visibility: 'none'
        },
        paint: {
          'fill-extrusion-height': ['get', 'column_height_m'],
          'fill-extrusion-base': 0,
          'fill-extrusion-color': DENSITY_COLOR_RAMP,
          'fill-extrusion-opacity': 0.86,
          'fill-extrusion-vertical-gradient': true
        }
      });

      // 2-B. 헥사곤 기둥 하단 건축 베이스 윤곽선 레이어 (크리스탈 받침대 효과)
      map.addLayer({
        id: 'density-grid-3d-base-line',
        type: 'line',
        source: 'density-grid-source',
        minzoom: 10.5,
        layout: {
          visibility: 'none'
        },
        paint: {
          'line-color': '#0ea5e9',
          'line-width': 1.2,
          'line-opacity': 0.35
        }
      });

      // 3. [Step 3] 호버 하이라이트 레이어 (선택된 기둥 상단에 밝은 일렉트릭 시안/화이트 캡 발광 효과)
      map.addLayer({
        id: 'density-grid-3d-highlight',
        type: 'fill-extrusion',
        source: 'density-grid-source',
        minzoom: 10.5,
        layout: { visibility: 'none' },
        filter: ['==', ['get', 'grid_id'], ''],
        paint: {
          'fill-extrusion-height': ['+', ['get', 'column_height_m'], 6.0],
          'fill-extrusion-base': ['get', 'column_height_m'],
          'fill-extrusion-color': '#38bdf8',
          'fill-extrusion-opacity': 0.98
        }
      });

      syncGridLayerVisibility(map, {
        hasData: Boolean(gridDataRef.current && gridDataRef.current.length > 0),
        gridVisible: true,
        extrusion: false
      });

      // 개별 점포는 격자 위에 가장 선명하게 그려 클릭 우선순위를 보장한다.
      map.addSource('store-points-source', {
        type: 'geojson',
        data: EMPTY_FEATURE_COLLECTION
      });
      // 선택된 점포 강조 링
      map.addLayer({
        id: 'store-points-selected',
        type: 'circle',
        source: 'store-points-source',
        minzoom: STORE_MIN_ZOOM,
        filter: ['==', ['get', 'bizes_id'], ''],
        paint: {
          'circle-radius': ['interpolate', ['linear'], ['zoom'], 14, 11, 17, 18],
          'circle-color': 'rgba(2, 132, 199, 0.16)',
          'circle-stroke-width': 2.5,
          'circle-stroke-color': '#0284c7'
        }
      });
      map.addLayer({
        id: 'store-points',
        type: 'circle',
        source: 'store-points-source',
        minzoom: STORE_MIN_ZOOM,
        layout: { visibility: 'visible' },
        paint: {
          'circle-radius': [
            'interpolate', ['linear'], ['zoom'],
            14, ['match', ['get', 'brand_officiality'], 'FRANCHISE_CONFIRMED', 6.5, 'BRAND_CONFIRMED', 6.5, 'UNVERIFIED', 6.0, 5.0],
            16, ['match', ['get', 'brand_officiality'], 'FRANCHISE_CONFIRMED', 8.5, 'BRAND_CONFIRMED', 8.5, 'UNVERIFIED', 7.8, 6.5],
            18, ['match', ['get', 'brand_officiality'], 'FRANCHISE_CONFIRMED', 11.0, 'BRAND_CONFIRMED', 11.0, 'UNVERIFIED', 10.0, 8.5]
          ],
          'circle-color': STORE_COLOR_RAMP,
          'circle-opacity': 1,
          'circle-stroke-width': 2.2,
          'circle-stroke-color': '#ffffff'
        }
      });

      // 초기 핫스팟 반영
      if (selectedHotspotRef.current) {
        applySelectedHotspot(selectedHotspotRef.current, true, true);
      }

      // 팝업 자동 열림 모드 지원
      if (shouldOpenPopup && gridDataRef.current && gridDataRef.current.length > 0) {
        const topCell = [...gridDataRef.current].sort((a, b) => b.total_stores - a.total_stores)[0];
        if (topCell) {
          displayPopup(map, [topCell.center_lon, topCell.center_lat], topCell);
        }
      }

      // 팝업 클릭 이벤트
      const handleGridClick = (e) => {
        if (!e.features || e.features.length === 0) return;
        if (map.queryRenderedFeatures(e.point, { layers: ['store-points'] }).length) return;
        const feature = e.features[0];
        const props = feature.properties || {};
        const coords = (props.center_lon && props.center_lat)
          ? [Number(props.center_lon), Number(props.center_lat)]
          : [e.lngLat.lng, e.lngLat.lat];
        displayPopup(map, coords, props);
      };

      map.on('click', 'density-grid-3d-columns', handleGridClick);
      map.on('click', 'density-grid-2d-fill', handleGridClick);
      map.on('click', 'density-grid-overview-points', handleGridClick);

      // 점포 상세 팝업 (지도 핀 클릭과 점포 탐색기 목록 클릭이 공유)
      const openStoreDetail = async (bizesId, bizesName, coords) => {
        if (!bizesId) return;
        storeDetailAbortRef.current?.abort();
        const controller = new AbortController();
        storeDetailAbortRef.current = controller;
        hoverTipRef.current?.remove();
        if (activePopupRef.current) activePopupRef.current.remove();
        const popup = new maplibregl.Popup({ offset: 14, closeButton: true, maxWidth: '320px' })
          .setLngLat(coords)
          .setDOMContent(createStorePopupElement({ store: { bizes_nm: bizesName } }, '점포 상세를 불러오는 중...'))
          .addTo(map);
        activePopupRef.current = popup;
        window.__activePopup = popup;
        if (map.getLayer('store-points-selected')) {
          map.setFilter('store-points-selected', ['==', ['get', 'bizes_id'], bizesId]);
        }
        if (onActiveStoreChangeRef.current) onActiveStoreChangeRef.current(bizesId);
        popup.on('close', () => {
          if (activePopupRef.current !== popup) return;
          if (map.getLayer('store-points-selected')) {
            map.setFilter('store-points-selected', ['==', ['get', 'bizes_id'], '']);
          }
          if (onActiveStoreChangeRef.current) onActiveStoreChangeRef.current(null);
        });
        try {
          const detail = await fetchStoreDetail(bizesId, controller.signal);
          if (activePopupRef.current === popup) {
            popup.setDOMContent(createStorePopupElement(detail, null, onInspectBrandRef.current));
          }
        } catch (error) {
          if (error?.name !== 'AbortError' && activePopupRef.current === popup) {
            popup.setDOMContent(createStorePopupElement({ store: { bizes_nm: bizesName } }, error.message));
          }
        }
      };
      openStoreDetailRef.current = openStoreDetail;

      const handleStoreClick = (e) => {
        const feature = (e.features && e.features.length > 1)
          ? (e.features.find((f) => Number(f.properties?.is_multi_brand_store) === 1) || e.features[0])
          : e.features?.[0];
        if (!feature) return;
        openStoreDetail(feature.properties?.bizes_id, feature.properties?.bizes_nm, feature.geometry.coordinates.slice());
      };
      map.on('click', 'store-points', handleStoreClick);

      // 점포 핀 호버: 상호명 즉시 표시 (클릭 전에 어떤 점포인지 확인)
      map.on('mousemove', 'store-points', (e) => {
        const feature = e.features?.[0];
        if (!feature) return;
        map.getCanvas().style.cursor = 'pointer';
        // 점포/격자 팝업이 열려 있으면 호버 툴팁을 띄우지 않아 겹침 방지
        if (activePopupRef.current?.isOpen?.()) {
          hoverTipRef.current?.remove();
          return;
        }
        const p = feature.properties || {};
        const baseName = p.brch_nm ? `${p.bizes_nm} ${p.brch_nm}` : p.bizes_nm;
        const typeLabel = STORE_TYPE_META[getStoreType(p)].label;
        const name = `${baseName || ''} · ${typeLabel}`;
        if (!hoverTipRef.current) {
          hoverTipRef.current = new maplibregl.Popup({
            closeButton: false,
            closeOnClick: false,
            offset: 12,
            className: 'store-hover-tip'
          });
        }
        hoverTipRef.current
          .setLngLat(feature.geometry.coordinates.slice())
          .setText(name || '')
          .addTo(map);
      });
      map.on('mouseleave', 'store-points', () => {
        map.getCanvas().style.cursor = '';
        hoverTipRef.current?.remove();
      });
      map.on('moveend', () => loadVisibleStores(map));
      loadVisibleStores(map);

      // [Step 3] 마우스 호버 하이라이트 & 도킹 카드 이벤트
      const handleGridHover = (e) => {
        if (!e.features || e.features.length === 0) return;
        const feature = e.features[0];
        const props = feature.properties || {};
        map.getCanvas().style.cursor = 'pointer';
        // 팝업이 열려 있으면 격자 호버 카드를 띄우지 않음 (점포 정보 우선)
        if (activePopupRef.current?.isOpen?.()) {
          setHoveredGrid(null);
        } else {
          setHoveredGrid(props);
        }
        if (props.grid_id && map.getLayer('density-grid-3d-highlight')) {
          map.setFilter('density-grid-3d-highlight', ['==', ['get', 'grid_id'], props.grid_id]);
        }
      };

      const handleGridLeave = () => {
        map.getCanvas().style.cursor = '';
        setHoveredGrid(null);
        if (map.getLayer('density-grid-3d-highlight')) {
          map.setFilter('density-grid-3d-highlight', ['==', ['get', 'grid_id'], '']);
        }
      };

      map.on('mousemove', 'density-grid-3d-columns', handleGridHover);
      map.on('mouseleave', 'density-grid-3d-columns', handleGridLeave);
      map.on('mousemove', 'density-grid-2d-fill', handleGridHover);
      map.on('mouseleave', 'density-grid-2d-fill', handleGridLeave);
      map.on('mousemove', 'density-grid-overview-points', handleGridHover);
      map.on('mouseleave', 'density-grid-overview-points', handleGridLeave);
    });

    return () => {
      window.removeEventListener('resize', handleResize);
      if (resizeObserver) resizeObserver.disconnect();
      isMapLoadedRef.current = false;
      if (activePopupRef.current) activePopupRef.current.remove();
      if (hoverTipRef.current) hoverTipRef.current.remove();
      if (hotspotMarkerRef.current) hotspotMarkerRef.current.remove();

      storeAbortRef.current?.abort();
      storeDetailAbortRef.current?.abort();
      map.remove();
      mapInstanceRef.current = null;
      window.__map = null;
    };
  }, [displayPopup, applySelectedHotspot, shouldOpenPopup, loadVisibleStores]);

  useEffect(() => {
    const map = mapInstanceRef.current;
    if (map && isMapLoadedRef.current) loadVisibleStores(map, selectedCategory, selectedMidCategory);
  }, [selectedCategory, selectedMidCategory, loadVisibleStores]);

  useEffect(() => {
    if (typeof window !== 'undefined') window.__storeLayerStatus = storeLayerStatus;
  }, [storeLayerStatus]);

  const hasGridData = Boolean(gridData && gridData.length > 0);

  // gridData 변경 시 데이터 갱신 및 레이어 가시성 토글
  useEffect(() => {
    if (isMapLoadedRef.current && mapInstanceRef.current) {
      const map = mapInstanceRef.current;
      syncGridLayerVisibility(map, {
        hasData: hasGridData,
        gridVisible: isGridVisible,
        extrusion: isExtrusionEnabled
      });
      if (hasGridData) {
        updateGridSource(gridData);
        if (shouldOpenPopup && !activePopupRef.current) {
          const topCell = [...gridData].sort((a, b) => b.total_stores - a.total_stores)[0];
          if (topCell) {
            displayPopup(map, [topCell.center_lon, topCell.center_lat], topCell);
          }
        }
      } else {
        if (map.getLayer('density-grid-3d-highlight')) {
          map.setFilter('density-grid-3d-highlight', ['==', ['get', 'grid_id'], '']);
        }
        updateGridSource([]);
        setHoveredGrid(null);
        if (activePopupRef.current) {
          activePopupRef.current.remove();
          activePopupRef.current = null;
        }
        if (window.__activePopup) {
          try { window.__activePopup.remove(); } catch (e) {}
          window.__activePopup = null;
        }
      }
    }
  }, [gridData, hasGridData, isGridVisible, isExtrusionEnabled, updateGridSource, displayPopup, shouldOpenPopup]);

  // 점포 탐색기에서 점포를 선택하면 지도를 해당 점포로 이동하고 상세 팝업을 연다.
  useEffect(() => {
    const map = mapInstanceRef.current;
    if (!focusStoreRequest || !map || !isMapLoadedRef.current) return;
    const { bizes_id, bizes_nm, lon, lat } = focusStoreRequest;
    if (!Number.isFinite(lon) || !Number.isFinite(lat)) return;
    const prefersReducedMotion = typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const target = { center: [lon, lat], zoom: Math.max(map.getZoom(), 16.5) };
    if (prefersReducedMotion) map.jumpTo(target);
    else map.easeTo({ ...target, duration: 600, essential: true });
    if (openStoreDetailRef.current) openStoreDetailRef.current(bizes_id, bizes_nm, [lon, lat]);
  }, [focusStoreRequest]);

  // 새 지역 응답이 확정된 뒤에만 지도 범위 적용 (동일 지역 내 업종 탭 변경 시에는 현재 줌/시점 유지)
  const lastFittedRegionKeyRef = useRef(null);
  useEffect(() => {
    selectedRegionInfoRef.current = selectedRegionInfo;
    const map = mapInstanceRef.current;
    if (!map || !isMapLoadedRef.current) return;

    if (gridLoading) return;

    const isSido = selectedRegionInfo?.region_type === 'SIDO';
    if (isSido && regionLoading) return;

    const regionKey = `${selectedRegionInfo?.region_code || '00'}_${is3DMode}`;
    if (lastFittedRegionKeyRef.current === regionKey) {
      return;
    }

    if (hasGridData && gridData.length > 0) {
      lastFittedRegionKeyRef.current = regionKey;
      fitGridBounds(map, gridData, is3DMode, customZoom);
    } else if (selectedRegionInfo) {
      lastFittedRegionKeyRef.current = regionKey;
      const { center_lon, center_lat, region_code, region_type } = selectedRegionInfo;
      if (center_lon && center_lat) {
        let targetZoom = 13.5;
        let targetPitch = is3DMode ? 40.0 : 0.0;
        if (region_code === '00' || region_type === 'NATIONWIDE') {
          targetZoom = 7.0;
          targetPitch = is3DMode ? 20.0 : 0.0;
        } else if (region_type === 'SIDO') {
          targetZoom = 10.5;
          targetPitch = is3DMode ? 30.0 : 0.0;
        }

        const prefersReducedMotion = typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
        if (prefersReducedMotion) {
          map.jumpTo({
            center: [center_lon, center_lat],
            pitch: targetPitch,
            bearing: is3DMode ? -20.0 : 0.0,
            zoom: customZoom !== null ? customZoom : targetZoom
          });
        } else {
          map.flyTo({
            center: [center_lon, center_lat],
            pitch: targetPitch,
            bearing: is3DMode ? -20.0 : 0.0,
            zoom: customZoom !== null ? customZoom : targetZoom,
            speed: 1.1,
            curve: 1.42,
            essential: true
          });
        }
      }
    }
  }, [gridData, hasGridData, selectedRegionInfo, gridLoading, regionLoading, is3DMode, customZoom]);

  // 광역 뷰(전국 17개 시도 / 시도 내 시군구) 인터랙티브 버블 마커 렌더링 및 드릴다운 연동
  useEffect(() => {
    const map = mapInstanceRef.current;
    // 기존 광역 버블 마커 일괄 정리
    if (macroBubbleMarkersRef.current.length > 0) {
      macroBubbleMarkersRef.current.forEach((m) => m.remove());
      macroBubbleMarkersRef.current = [];
    }

    if (!map || !isMapLoadedRef.current || hasGridData || !macroBubbles || macroBubbles.length === 0) {
      return;
    }

    const sorted = [...macroBubbles].sort((a, b) => (b.total_stores || 0) - (a.total_stores || 0));
    const maxStores = Math.max(...sorted.map((d) => d.total_stores || 0), 1);
    const catAccent =
      selectedCategory && selectedCategory !== 'ALL'
        ? currentCategory.color || '#0055ff'
        : '#0055ff';

    const createdMarkers = [];
    sorted.forEach((item, idx) => {
      if (item.center_lon == null || item.center_lat == null) return;
      const rank = idx + 1;
      const ratio = (item.total_stores || 0) / maxStores;
      const tierClass =
        ratio >= 0.65
          ? 'tier-xl'
          : ratio >= 0.35
            ? 'tier-lg'
            : ratio >= 0.15
              ? 'tier-md'
              : 'tier-sm';

      const shortName = formatShortRegionLabel(item.region_name, item.region_type);
      const storesCount = Number(item.total_stores || 0);
      const franRate = Number(item.franchise_penetration_rate || 0).toFixed(1);

      const el = document.createElement('button');
      el.type = 'button';
      el.className = `macro-region-bubble ${tierClass} ${rank <= 3 ? `top-rank-${rank}` : ''}`.trim();
      el.style.setProperty('--bubble-accent', catAccent);
      el.title = `${item.region_name} · 점포 ${storesCount.toLocaleString()}개소 · 가맹침투율 ${franRate}% (클릭 시 상권 진입)`;

      const topRow = document.createElement('span');
      topRow.className = 'macro-bubble-top';
      if (rank <= 3) {
        const rankBadge = document.createElement('span');
        rankBadge.className = `macro-bubble-rank r-${rank}`;
        rankBadge.textContent = `#${rank}`;
        topRow.appendChild(rankBadge);
      }
      const nameSpan = document.createElement('span');
      nameSpan.className = 'macro-bubble-name';
      nameSpan.textContent = shortName;
      topRow.appendChild(nameSpan);

      const countRow = document.createElement('strong');
      countRow.className = 'macro-bubble-count';
      countRow.textContent =
        storesCount >= 10000
          ? `${(storesCount / 10000).toFixed(1)}만`
          : `${storesCount.toLocaleString()}개`;

      const rateRow = document.createElement('span');
      rateRow.className = 'macro-bubble-rate';
      rateRow.textContent = `가맹 ${franRate}%`;

      el.append(topRow, countRow, rateRow);

      el.addEventListener('click', (e) => {
        e.stopPropagation();
        if (onSelectRegionBubbleRef.current) {
          onSelectRegionBubbleRef.current(item.region_code, item.region_type);
        }
      });

      const marker = new maplibregl.Marker({ element: el, anchor: 'center' })
        .setLngLat([Number(item.center_lon), Number(item.center_lat)])
        .addTo(map);

      createdMarkers.push(marker);
    });

    macroBubbleMarkersRef.current = createdMarkers;

    return () => {
      createdMarkers.forEach((m) => m.remove());
    };
  }, [macroBubbles, hasGridData, selectedCategory, currentCategory]);

  // selectedHotspot 변경 시 카메라 이동 및 마커 생성
  const initialHotspotHandledRef = useRef(false);
  useEffect(() => {
    if (isMapLoadedRef.current) {
      if (selectedHotspot) {
        const isFirstAuto = !initialHotspotHandledRef.current;
        initialHotspotHandledRef.current = true;
        if (typeof window !== 'undefined') {
          window.__lastAppliedHotspot = selectedHotspot;
          window.__applyHotspotCalls = (window.__applyHotspotCalls || 0) + 1;
        }
        applySelectedHotspot(selectedHotspot, false, isFirstAuto);
      } else if (hotspotMarkerRef.current) {
        hotspotMarkerRef.current.remove();
        hotspotMarkerRef.current = null;
      }
    }
  }, [selectedHotspot, applySelectedHotspot]);

  const currentRegionName = selectedRegionInfo?.region_name || '선택 지역';
  const isNationwide = selectedRegionInfo?.region_code === '00' || selectedRegionInfo?.region_type === 'NATIONWIDE';
  const isSido = selectedRegionInfo?.region_type === 'SIDO';

  return (
    <div className="map-wrapper" aria-label="3D 지도 뷰포트">
      <div ref={mapContainerRef} className="map-container" />

      <div id="store-hud-status" className={`store-layer-status ${storeLayerStatus.state}`} role="status" aria-live="polite">
        {storeLayerStatus.state === 'zoom-required' && '줌 14 이상에서 개별 점포 표시'}
        {storeLayerStatus.state === 'hidden' && '개별 점포 레이어 숨김'}
        {storeLayerStatus.state === 'loading' && '현재 화면의 점포를 불러오는 중...'}
        {storeLayerStatus.state === 'ready' && `표시 점포 ${storeLayerStatus.count.toLocaleString()}개${storeLayerStatus.limited ? ` (최대 ${STORE_LIMIT.toLocaleString()}개)` : ''}`}
        {storeLayerStatus.state === 'empty' && '현재 화면·업종에 해당하는 점포 없음'}
        {storeLayerStatus.state === 'error' && `개별 점포 조회 실패: ${storeLayerStatus.error}`}
      </div>

      {/* 우측 슬림 맵 제어 레일 (Phase 5C-Vis Step 3 핵심 UI) */}
      <SlimMapRail
        is3DMode={is3DMode}
        onToggle3D={handleToggle3D}
        isExtrusionEnabled={isExtrusionEnabled}
        onToggleExtrusion={handleToggleExtrusion}
        colorMode={colorMode}
        onToggleColorMode={handleToggleColorMode}
        isGridVisible={isGridVisible}
        onToggleGrid={handleToggleGrid}
        isStoreLayerVisible={isStoreLayerVisible}
        onToggleStores={handleToggleStores}
        isHotspotsVisible={isHotspotsVisible}
        onToggleHotspots={onToggleHotspots}
        isFtcDrawerOpen={isFtcDrawerOpen}
        onToggleFtcDrawer={onToggleFtcDrawer}
        onResetView={handleResetView}
        hasGridData={hasGridData}
      />

      {/* 100m 격자 호버 카드: 좌측 하단 1줄 (점포 팝업이 열려 있으면 표시하지 않음) */}
      {hoveredGrid && (
        <div className="map-hover-dock-card" role="tooltip" aria-live="polite">
          <span className="hover-metric-k">📍 이 100m</span>
          <span className="hover-metric-v highlight">
            {selectedCategory && selectedCategory !== 'ALL' ? currentCategory.name : '외식'} {hoveredGrid.total_stores}개소
          </span>
          <span className="hover-metric-k">브랜드</span>
          <span className="hover-metric-v">{hoveredGrid.brand_stores}개소</span>
          <span className="hover-metric-k">최다</span>
          <span className="hover-metric-v" style={{ color: CATEGORY_COLOR_MAP[hoveredGrid.top_category_name] || '#38bdf8' }}>
            {hoveredGrid.top_category_name || '-'}
          </span>
          <span className="hover-card-sub">{sedaReferenceMonth ? '소진공 ' + sedaReferenceMonth : ''}</span>
        </div>
      )}

      {/* 지도 상단 HUD: 공간 계층 브레드크럼(전국 ↔ 시도 버블 ↔ 시군구 100m 격자) 및 상태 안내 */}
      {gridLoading || macroBubblesLoading ? (
        <div className="map-overlay-badge loading-state" role="status" aria-live="polite">
          <span className="badge-loading-spinner" />
          <span className="badge-text">
            📍 {currentRegionName} {hasGridData || (!isNationwide && !isSido) ? '100m 정밀 격자' : '광역 상권 버블'} 로딩 중...
          </span>
        </div>
      ) : gridError ? (
        <div className="map-overlay-badge error-state" role="alert">
          <span className="badge-error-icon">⚠️</span>
          <span className="badge-text">📍 {currentRegionName} 격자 로드 실패: {gridError}</span>
          {onRetryGrid && (
            <button className="hud-retry-btn" onClick={onRetryGrid} title="격자 재시도">
              재시도
            </button>
          )}
        </div>
      ) : hasGridData ? (
        <div className="map-overlay-badge spatial-breadcrumb-badge" aria-label="공간 계층 이동 바">
          <button
            type="button"
            className="spatial-crumb-btn"
            onClick={() => onSelectRegionBubble && onSelectRegionBubble('00', 'NATIONWIDE')}
            title="전국 17개 시도 버블 지도로 전환"
          >
            🗺️ 전국
          </button>
          <span className="spatial-crumb-sep">›</span>
          {selectedRegionInfo?.region_code?.length === 5 && (
            <>
              <button
                type="button"
                className="spatial-crumb-btn"
                onClick={() =>
                  onSelectRegionBubble &&
                  onSelectRegionBubble(selectedRegionInfo.region_code.slice(0, 2), 'SIDO')
                }
                title="상위 시도 전체 시군구 버블 지도로 한 단계 축소"
              >
                ↩ 시군구 전체 버블
              </button>
              <span className="spatial-crumb-sep">›</span>
            </>
          )}
          <span className="spatial-crumb-current">
            📍 {currentRegionName} 100m 정밀 격자 ({gridData.length.toLocaleString()}개 셀)
          </span>
        </div>
      ) : (
        <div className="map-overlay-badge spatial-breadcrumb-badge" aria-label="광역 버블 드릴다운 안내">
          {isNationwide ? (
            <>
              <span className="badge-empty-icon">🗺️</span>
              <span className="badge-empty-text">
                <strong>전국 17개 시도 상권 버블</strong>
                {selectedMidCategoryLabel
                  ? ` (${currentCategory.name} › ${selectedMidCategoryLabel})`
                  : selectedCategory && selectedCategory !== 'ALL'
                    ? ` (${currentCategory.name})`
                    : ''}
                {' '}— 지도 위의 시도 버블을 클릭하면 해당 시군구 상권으로 진입합니다
              </span>
            </>
          ) : isSido ? (
            <>
              <button
                type="button"
                className="spatial-crumb-btn"
                onClick={() => onSelectRegionBubble && onSelectRegionBubble('00', 'NATIONWIDE')}
                title="전국 17개 시도 버블 지도로 복귀"
              >
                ↩ 전국 17개 시도
              </button>
              <span className="spatial-crumb-sep">›</span>
              <span className="badge-empty-text">
                <strong>{currentRegionName} ({macroBubbles.length}개 시군구 버블)</strong> — 지도에서 구·군 버블을 클릭하면 100m 정밀 격자로 진입합니다
              </span>
            </>
          ) : (
            <>
              <span className="badge-empty-icon">ℹ️</span>
              <span className="badge-empty-text">📍 {currentRegionName} — 선택된 업종에 해당하는 100m 밀집도 격자 없음 (0건)</span>
            </>
          )}
        </div>
      )}

      {/* 지도 우측 하단: 방안 C — 1줄 초슬림 밀집도 미니 캡슐 (점포 핀 색상은 상단 검색바·좌측 패널에 통합) */}
      {hasGridData && isGridVisible && !gridLoading && !gridError && (
        <div className="map-density-mini-pill" aria-label="100m 격자 밀집도 미니 범례">
          <span className="mini-pill-label">
            {colorMode === 'category' ? '100m 최다업종' : '100m 밀집도'}
          </span>
          <span className="mini-pill-divider" aria-hidden="true" />
          {colorMode === 'category' ? (
            <div className="mini-pill-cats">
              <span className="mini-cat"><i style={{ backgroundColor: '#059669' }} />한식</span>
              <span className="mini-cat"><i style={{ backgroundColor: '#dc2626' }} />중식</span>
              <span className="mini-cat"><i style={{ backgroundColor: '#2563eb' }} />일식</span>
              <span className="mini-cat"><i style={{ backgroundColor: '#d97706' }} />양식</span>
              <span className="mini-cat"><i style={{ backgroundColor: '#ea580c' }} />치킨</span>
              <span className="mini-cat"><i style={{ backgroundColor: '#e11d48' }} />분식</span>
              <span className="mini-cat"><i style={{ backgroundColor: '#9333ea' }} />카페</span>
              <span className="mini-cat"><i style={{ backgroundColor: '#0891b2' }} />베이커리</span>
            </div>
          ) : (
            <div className="mini-pill-scale" title="100m 격자 내 외식 점포 수">
              <span className="scale-num">3</span>
              <span className="scale-bar" aria-hidden="true">
                <i style={{ backgroundColor: '#e9d5ff' }} />
                <i style={{ backgroundColor: '#c084fc' }} />
                <i style={{ backgroundColor: '#9333ea' }} />
                <i style={{ backgroundColor: '#db2777' }} />
                <i style={{ backgroundColor: '#9d174d' }} />
              </span>
              <span className="scale-num">100+</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
