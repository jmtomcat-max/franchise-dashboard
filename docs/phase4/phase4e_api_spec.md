# Phase 4 Stage 4E: 외식 프랜차이즈 분석 및 3D GIS API 명세서 (API Specification)

본 문서는 **대한민국 외식 프랜차이즈 시장 분석 3D GIS 대시보드** 백엔드 API 서비스(Phase 4 Stage 4E)의 엔드포인트 명세, 요청/응답 스키마, 필터 매개변수 및 에러 처리 표준을 정의합니다.

- **기본 URL**: `http://localhost:8000` (개발 환경)
- **API 버전**: `v1.0.0`
- **인터랙티브 문서**: `/docs` (Swagger UI), `/redoc` (ReDoc)
- **응답 기본 포맷**: JSON 및 GeoJSON (`application/json`)

---

## 1. 공통 규약 및 메타데이터

모든 API 응답은 `meta` 객체를 포함하여 데이터의 기준 시점, 적용된 필터, 페이징 정보 및 4축 분리 메타데이터를 클라이언트에 제공합니다.

### 1.1 메타데이터 스키마 (`ResponseMeta`)
```json
{
  "timestamp": "2026-10-13T14:15:50.123456",
  "data_reference_month": "2026-07",
  "universe_definition": "전국 외식업 총 고유 점포 735,185건 전수 대사 완료 (소상공인진흥공단 공공데이터 API)",
  "decoupled_axes": {
    "brand_officiality": "브랜드의 법적 가맹사업 실체성 (FRANCHISE_CONFIRMED, BRAND_CONFIRMED, UNVERIFIED, UNMATCHED)",
    "store_match_status": "점포 상호명 정규화 매칭 확신도 (MATCH_VERIFIED, MATCH_AUTO_HIGH_CONFIDENCE, MATCH_PROVISIONAL, REVIEW_REQUIRED, UNMATCHED)",
    "operation_type": "점포 운영 형태 (COMPANY_OPERATED, FRANCHISED, UNKNOWN)",
    "classification_status": "8대 대분류/48대 중분류 매핑 신뢰도 (CATEGORY_CONFIRMED, CATEGORY_PROVISIONAL, AMBIGUOUS_REVIEW)"
  },
  "applied_filters": {},
  "page": 1,
  "page_size": 100,
  "total_count": 256
}
```

---

## 2. 핵심 엔드포인트 상세 명세

### 2.1 총괄 대시보드 요약 (`Summary Analytics`)
- **엔드포인트**: `GET /api/v1/analytics/summary`
- **설명**: 전국 외식업 총괄 통계 요약 및 735,185건 대사 검증 결과를 반환합니다.
- **응답 예시**:
```json
{
  "data": {
    "reference_date": "2026-07",
    "total_food_stores": 735185,
    "brand_linked_stores": 168295,
    "independent_stores": 566890,
    "brand_penetration_rate": 22.89,
    "franchise_confirmed_stores": 48002,
    "confirmed_franchisees": 45202,
    "franchise_penetration_rate": 6.53,
    "total_brand_candidates": 5062,
    "franchise_confirmed_brands": 72,
    "shop_in_shop_stores": 23,
    "ambiguous_category_stores": 104060,
    "provinces_count": 16,
    "districts_count": 256,
    "taxonomy_majors": 8,
    "taxonomy_mids": 48,
    "data_integrity_status": "100% RECONCILED (ZERO DISCREPANCY)"
  },
  "meta": { ... }
}
```

---

### 2.2 지역별 외식업 통계 (`Regional Analytics`)

#### 2.2.1 지역 목록 조회
- **엔드포인트**: `GET /api/v1/analytics/regions`
- **쿼리 매개변수**:
  - `region_type` (Optional, string): `'SIDO'` 또는 `'SIGUNGU'`
  - `sido_code` (Optional, string): 상위 시도코드 (예: `'11'` 서울특별시 내 25개 구 조회)
  - `sort_by` (Optional, string, default `'total_stores'`): `'total_stores'`, `'franchise_confirmed_stores'`, `'brand_linked_stores'`, `'franchise_penetration_rate'`, `'brand_penetration_rate'`, `'region_name'` (화이트리스트 검증)
  - `order` (Optional, string, default `'desc'`): `'asc'` 또는 `'desc'`
  - `limit` (Optional, integer, default 100, max 300)
  - `offset` (Optional, integer, default 0)
- **응답**: `RegionListResponse`

#### 2.2.2 특정 지역 상세 조회
- **엔드포인트**: `GET /api/v1/analytics/regions/{region_code}`
- **경로 매개변수**: `region_code` (예: `'11680'` 강남구, `'11215'` 광진구, `'00'` 전국)
- **응답**: 지역 통계 및 상위 5개 업종 분포, 브랜드 침투율 상세.

---

### 2.3 업종별 분류 및 시장 점유율 (`Category Analytics`)

#### 2.3.1 업종별 점유율 및 모호 분류 분리 조회
- **엔드포인트**: `GET /api/v1/analytics/categories`
- **쿼리 매개변수**:
  - `region_code` (Optional, string, default `'00'`): 조회할 지역코드
  - `category_major_id` (Optional, string): 특정 8대 대분류 필터 (`CAT_MAJ_01` ~ `CAT_MAJ_08`)
  - `include_ambiguous` (Optional, boolean, default `true`):
    - `true`: 모호 분류(104,060건) 포함 전국 735,185건 기준 집계
    - `false`: 모호 분류를 제외한 확정 631,125건 기준 순수 점유율 산출

#### 2.3.2 특정 대분류 상세 및 하위 중분류 목록
- **엔드포인트**: `GET /api/v1/analytics/categories/{category_major_id}`
- **경로 매개변수**: `category_major_id` (`CAT_MAJ_01` ~ `CAT_MAJ_08`)

---

### 2.4 브랜드 분석 및 검색 (`Brand Analytics`)

#### 2.4.1 브랜드 검색 및 자동완성
- **엔드포인트**: `GET /api/v1/analytics/brands/search`
- **쿼리 매개변수**:
  - `q` (Optional, string): 검색어 (예: `'메가'`, `'스타벅스'`)
  - `officiality` (Optional, string): `'FRANCHISE_CONFIRMED'`, `'BRAND_CONFIRMED'`, `'UNVERIFIED'`
  - `category_major_id` (Optional, string): 대분류 필터
  - `limit` (Optional, integer, default 20)

#### 2.4.2 브랜드 전국/지역 분포 및 점유율
- **엔드포인트**: `GET /api/v1/analytics/brands/{brand_id}/distribution`
- **경로 매개변수**: `brand_id` (`BRD_xxxx`)
- **쿼리 매개변수**:
  - `region_type` (Optional, string, default `'SIDO'`): `'SIDO'` 또는 `'SIGUNGU'`

---

### 2.5 3D GIS 및 공간 검색 (`Spatial & 3D Map Service`)

#### 2.5.1 지도 화면 BBOX 점포 검색 (MapLibre / deck.gl 표준)
- **엔드포인트**: `GET /api/v1/spatial/stores/bbox`
- **쿼리 매개변수**:
  - `min_lon`, `min_lat`, `max_lon`, `max_lat` (Required, float): 바운딩 박스 WGS84 좌표
  - `zoom` (Optional, float): 현재 지도 줌레벨
  - `category_major_id` (Optional, string): 8대 대분류 필터
  - `category_mid_id` (Optional, string): 48대 중분류 필터
  - `brand_id` (Optional, string): 특정 브랜드 필터
  - `officiality` (Optional, string): 브랜드 공식성 필터
  - `classification_status` (Optional, string): 업종분류 상태 필터
  - `format` (Optional, string, default `'geojson'`): `'geojson'` 또는 `'json'`
  - `exact_count` (Optional, boolean, default `false`): 고속 뷰포트 렌더링 시 `false` 권장
  - `limit` (Optional, integer, default 500, max 2000)
  - `offset` (Optional, integer, default 0)
- **응답 (GeoJSON FeatureCollection)**:
```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": {
        "type": "Point",
        "coordinates": [127.0276, 37.4979]
      },
      "properties": {
        "bizes_id": "MA010120220805432100",
        "bizes_nm": "스타벅스 강남역점",
        "brch_nm": "강남역점",
        "category_major_name": "카페·음료",
        "category_mid_name": "커피전문점",
        "brand_name_std": "스타벅스",
        "brand_officiality": "BRAND_CONFIRMED",
        "match_status": "MATCH_VERIFIED",
        "operation_type": "COMPANY_OPERATED",
        "classification_status": "CATEGORY_CONFIRMED",
        "is_multi_brand_store": 0
      }
    }
  ],
  "meta": { ... }
}
```

#### 2.5.2 개별 점포 3D 팝업 상세 조회
- **엔드포인트**: `GET /api/v1/spatial/stores/{bizes_id}`
- **설명**: 3D 지도에서 특정 점포 클릭 시 4차원 독립 배지 및 복수 브랜드(샵인샵) 알림이 포함된 팝업 데이터를 반환합니다.
- **응답 구조**:
```json
{
  "store": { ... },
  "ui_presentation": {
    "badges": {
      "officiality_badge": { "code": "FRANCHISE_CONFIRMED", "label": "공인 가맹 프랜차이즈", "color": "#10B981" },
      "match_badge": { "code": "MATCH_VERIFIED", "label": "매칭 검증 완료", "color": "#3B82F6" },
      "operation_badge": { "code": "FRANCHISED", "label": "확인된 가맹점", "color": "#8B5CF6" },
      "category_badge": { "code": "CATEGORY_CONFIRMED", "label": "표준 업종 확정", "color": "#059669" }
    },
    "multi_brand_alert": null
  }
}
```

#### 2.5.3 3D 밀집도 100m 격자 기둥 (deck.gl ColumnLayer 연동)
- **엔드포인트**: `GET /api/v1/spatial/density/grid`
- **쿼리 매개변수**:
  - `sigungu_code` (Optional, string): 시군구 필터 (예: `'11215'` 광진구)
  - `min_lon`, `min_lat`, `max_lon`, `max_lat` (Optional, float): BBOX 공간 필터
  - `limit` (Optional, integer, default 500, max 2000)
- **응답 아이템**:
```json
{
  "grid_id": "GRID_11215_127071_37542",
  "sigungu_code": "11215",
  "center_lon": 127.071,
  "center_lat": 37.542,
  "total_stores": 28,
  "brand_stores": 12,
  "top_category_name": "카페·음료",
  "column_height_m": 238.0
}
```

#### 2.5.4 3D 상권 핫스팟 및 드론 비행 카메라 투어
- **엔드포인트**: `GET /api/v1/spatial/hotspots`
- **설명**: 전국 10대 대표 외식 상권(광진구 건대입구 등)의 3D 시점 카메라 파라미터(`pitch`, `bearing`, `zoom`) 및 비행 순서를 제공합니다.

---

## 3. 에러 처리 및 상태 코드 표준

| HTTP 상태 코드 | 상황 | 응답 포맷 |
| :--- | :--- | :--- |
| **400 Bad Request** | 잘못된 BBOX 좌표 범위 (`min > max`) 또는 화이트리스트 외 정렬 파라미터 입력 | `{"detail": "에러 원인", "status": 400}` |
| **404 Not Found** | 존재하지 않는 지역코드 (`99999`) 또는 점포 ID | `{"detail": "해당 리소스를 찾을 수 없습니다."}` |
| **422 Unprocessable Entity** | Pydantic 타입 유효성 검사 실패 (문자열이 입력되어야 할 곳에 객체 등) | FastAPI 기본 422 JSON |
| **500 Internal Server Error** | 서버 내부 예외 발생 | `{"detail": "서버 내부 처리 중 오류가 발생했습니다."}` |
