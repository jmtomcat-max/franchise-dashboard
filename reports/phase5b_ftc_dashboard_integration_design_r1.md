# Phase 5B: 공정거래위원회 외식업 거시통계 지도·대시보드 통합 기술 설계서 (R1 정정본)

- **문서 번호**: P5B-DES-2026-001-R1
- **정정 일자**: 2026-10-13 (R1 전면 정정)
- **프로젝트 경로**: `D:\Franchise_Dashboard`
- **설계 상태**: **설계 완료 (Draft R1 - Awaiting User Approval, 코딩 및 DB 변경 미착수)**
- **대상 원천 DB (읽기 전용)**:
  - 기존 지도·분석 DB: `data/franchise_analytics_v1.sqlite3` (735,185 점포, 16 시도, 256 시군구, 100m 정밀 격자 466개)
  - 공정위 거시통계 DB: `data/ftc_macro_statistics_v1.sqlite3` (23,537 레코드, 4개년 15개 업종, R1 정정 완료)

---

## 1. 개요 및 핵심 제품 원칙 준수 방침 (R1 정정)

본 기술 설계서는 Phase 5A에서 구축된 기본 지도 서비스(광진구 100m 밀집도 격자, 상권 핫스팟, 모바일 390×844 최적화)와 Phase 4F에서 전수 적재·R1 정정된 공정위 2023~2026년 거시 가맹통계 데이터를 안전하고 정직하게 연결하기 위한 통합 아키텍처 R1 정정본입니다.

> [!IMPORTANT]
> **실행 제한 준수 확인**:
> 본 단계에서는 기존 소스코드 수정, 신규 기능 코딩, DB 스키마 변경, API 재수집, 서버 실행 및 패키지 설치를 일체 수행하지 않으며, **오직 본 R1 설계서와 API 계약서, 검증 체크리스트 3개 산출물만을 독립 생성**합니다.
> 모든 예시 수치는 `data/ftc_macro_statistics_v1.sqlite3` 실측 쿼리 결과를 100% 그대로 반영하였습니다.

### 1.1 3대 핵심 제품 원칙 (R1 용어 정정 반영)

```
┌────────────────────────────────────────────────────────────────────────┐
│                      Phase 5B 3대 핵심 제품 원칙 (R1)                   │
├────────────────────┬────────────────────┬──────────────────────────────┤
│   최신자료 원칙    │    역할 분리 원칙  │       데이터 정직성          │
│(Latest & Honest)   │  (Role Separation) │    (Strict Data Integrity)   │
├────────────────────┼────────────────────┼──────────────────────────────┤
│• 기본연도: 2026년  │• 지도: 소진공 점포 │• 한 위젯 내 연도 혼합 금지   │
│• 2026 등록·2025실적│• 공정위: 전국 벤치 │• 명시적 조회시 임의대체 금지 │
│• 스냅샷 버전 명시  │• 본부소재지!=점포  │• 양수/0원/NULL 상태 분리     │
│• 과거연도 조용히   │• 지도마커 연동 금지│• 중앙값/절사평균 우선 채택   │
│  대체 절대 금지    │                    │• 패널 비활성화 유지          │
└────────────────────┴────────────────────┴──────────────────────────────┘
```

1. **최신자료 원칙 (Latest Data First)**
   - 대시보드와 지도의 공정위 벤치마크 기본연도는 데이터가 존재하는 최신 기준연도인 **`2026년`**으로 설정합니다.
   - 표준 표기 문자열:
     > **`2026년 공정위 등록 기준 · 2025 회계연도 실적`**
   - 데이터 버전 및 수집 시각:
     > **`데이터 버전: 2026년 스냅샷 (수집시각: 2026-10-13 08:53:05, 확정모수: 4,521건)`**
   - 2026년은 `수집 시점 기준 최신 제공 스냅샷이며 향후 모수가 변동될 수 있음`을 명시하며, 과거 연도를 기본값으로 조용히 대체하지 않습니다.
   - 2025년 데이터는 `최신 완결 후보 연도이며 공식 마감 여부는 확인되지 않음`으로 엄격히 표기합니다.

2. **역할 분리 원칙 (Strict Role Separation)**
   - **지도(GIS)**: 공간 좌표, 100m 밀집도 격자, 핫스팟, 3D 건물 레이어는 소진공(SEMAS) 73.5만 개 점포 데이터가 전담합니다.
   - **공정위 데이터**: 개별 점포의 위경도 좌표(Lat/Lon)가 없으므로 지도 마커나 건물 익스트루전 높이에 절대 사용하지 않습니다.
   - **본부 소재지(`jnghqRgnNm`) 해석 통제**: 본부 소재지는 법인 본사 주소일 뿐 가맹점 위치가 아니므로, 시도별 가맹점 분포로 해석하거나 지도에 투영하지 않습니다. 공정위는 오직 **전국 거시 벤치마크 패널 및 시계열 추세 비교**에만 사용합니다.

3. **데이터 정직성 원칙 (Data Honesty & Robust Metrics)**
   - **연도 혼합 절대 금지**: 단일 위젯 및 단일 지표 카드 내부에서 서로 다른 연도의 분모·분자 혼합을 금지합니다. 특정 지표 하나가 NULL이라는 이유로 다른 연도 값을 혼합하지 않습니다.
   - **대체 정책 명확화**: 사용자가 특정 연도를 직접 요청한 경우 다른 연도로 자동 대체하지 않고 데이터 부재 시 `NO_DATA_FOR_REQUESTED_YEAR`를 반환합니다. 자동 대체는 기본 최신연도 조회에서 매핑된 업종 전체가 2026년에 부재할 때만 위젯 전체를 2025년으로 원자적 대체하고 `2025년 대체 표시` 배지를 노출합니다.
   - **매출 3분류 엄격 준수**: 매출 데이터를 양수(`> 0`), 0원(`= 0`), 결측(`IS NULL`)으로 분리 표기합니다.
   - **로버스트 벤치마크 우선**: 단순평균 단독 노출을 금지하고, **중앙값(Median)**과 **5% 절사평균(Trimmed Mean)**을 1순위 대표값으로 지정합니다.
   - **패널 비활성화 유지**: 존속 브랜드 균형 패널은 생존편향 위험이 있으므로 비활성 상태를 유지하며, 2026년 미관측 브랜드를 폐업·이탈로 표기하지 않습니다.

---

## 2. 현재 구조 분석 (As-Is Architecture Audit)

기존 Phase 5A 소스코드 및 Phase 4E 백엔드 구조를 분석한 결과입니다.

```mermaid
graph TD
    subgraph Frontend["프런트엔드 (React 18 + MapLibre GL)"]
        App["App.jsx (루트 상태 관리)"]
        Header["Header.jsx (상태/새로고침)"]
        MarketSummary["MarketSummary.jsx (전국 요약)"]
        MapContainer["MapContainer.jsx (MapLibre 2D/3D)"]
        HotspotsPanel["HotspotsPanel.jsx (Top 5 핫스팟)"]
        ApiService["services/api.js (Vite Fetch)"]
    end

    subgraph Backend["백엔드 (FastAPI)"]
        Main["main.py (엔트리포인트)"]
        Database["database.py (SQLite ro Pool)"]
        SummaryRouter["routers/summary.py"]
        CategoriesRouter["routers/categories.py"]
        SpatialRouter["routers/spatial.py"]
    end

    subgraph Storage["SQLite 데이터베이스 (읽기 전용)"]
        AnalyticsDB[("franchise_analytics_v1.sqlite3<br/>73.5만 점포 / 공간 인덱스")]
        FTCDB[("ftc_macro_statistics_v1.sqlite3<br/>23,537 레코드 / 4개년 거시통계")]
    end

    App --> Header
    App --> MarketSummary
    App --> MapContainer
    App --> HotspotsPanel
    App --> ApiService

    ApiService --> Main
    Main --> SummaryRouter
    Main --> CategoriesRouter
    Main --> SpatialRouter

    SummaryRouter --> Database
    CategoriesRouter --> Database
    SpatialRouter --> Database

    Database --> AnalyticsDB
    Database -.->|"신규 연동 필요 (mode=ro)"| FTCDB
```

### 2.1 프런트엔드 구조 및 상태 전파 경로
- **진입점**: [App.jsx](file:///d:/Franchise_Dashboard/frontend/src/App.jsx)
  - `loadAllData()` 함수에서 `Promise.allSettled`로 3대 엔드포인트(`/summary`, `/spatial/density/grid`, `/spatial/hotspots`)를 병렬 호출.
  - 현재 상태 변수: `summaryData`, `gridData`, `hotspots`, `selectedHotspot`, `isRefreshing`.
- **업종 선택 상태의 부재 (Gap)**:
  - 현재 화면에는 업종(8대 대분류/48대 중분류)을 선택하고 전파하는 전역 상태가 없음.
  - 백엔드(`/api/v1/analytics/categories`, `/api/v1/spatial/stores/bbox`)에는 `category_major_id`, `category_mid_id` 필터 파라미터가 이미 존재하므로, 프런트엔드에 `selectedCategoryMajor`, `selectedCategoryMid` 상태를 신설해야 함.
- **컴포넌트 레이아웃**:
  - 데스크톱: 좌측 [MarketSummary.jsx](file:///d:/Franchise_Dashboard/frontend/src/components/MarketSummary.jsx) (360px), 중앙 [MapContainer.jsx](file:///d:/Franchise_Dashboard/frontend/src/components/MapContainer.jsx) (flex: 1), 우측 [HotspotsPanel.jsx](file:///d:/Franchise_Dashboard/frontend/src/components/HotspotsPanel.jsx) (380px).
  - 모바일(390×844): [index.css](file:///d:/Franchise_Dashboard/frontend/src/index.css)에서 `.app-layout`이 flex-direction: column으로 전환. 상단 지도(42vh), 하단 패널 스택.
- **지도 및 팝업**:
  - `MapContainer.jsx` 내 MapLibre GL JS 인스턴스가 `OSM_LIGHT_STYLE` 래스터 타일 및 `density-grid-circles` 원형 서클을 렌더링.
  - 팝업은 DOM 노드를 직접 생성(`createPopupElement`)하여 `textContent`로 텍스트를 주입함으로써 XSS를 원천 차단함.

### 2.2 백엔드 API 및 DB 접근 계층 구조
- **백엔드 메인**: [main.py](file:///d:/Franchise_Dashboard/src/stage4e/api/main.py)
  - CORS 미들웨어 허용, 5대 라우터(`summary`, `regions`, `categories`, `brands`, `spatial`) 마운트.
- **DB 접근 계층**: [database.py](file:///d:/Franchise_Dashboard/src/stage4e/api/database.py)
  - 스레드 로컬 `_thread_local.conn` 기반 `get_cached_connection()`.
  - SQLite 연결 문자열: `file:data/franchise_analytics_v1.sqlite3?mode=ro`.
  - 256MB mmap (`PRAGMA mmap_size = 268435456`), 64MB 캐시 (`PRAGMA cache_size = -64000`).
  - `validate_whitelist()`를 통한 SQL 인젝션 차단.
- **기존 분석 DB와 공정위 DB의 격리 현황**:
  - `franchise_analytics_v1.sqlite3`에는 소상공인 공간·점포 분석 테이블만 존재.
  - 공정위 데이터는 `ftc_macro_statistics_v1.sqlite3`에 독립 보존되어 있음.
  - 두 DB 간 런타임 JOIN은 절대 수행하지 않으며, 백엔드에서 공정위 전용 DB 핸들러(`get_ftc_connection()`)를 분리 생성하여 읽기 전용으로 안전하게 접근해야 함.

### 2.3 수정 대상 예상 파일 목록 및 역할 정의

| 구분 | 파일 경로 | 현재 역할 | 향후 Phase 5B 구현 단계 역할 |
| :--- | :--- | :--- | :--- |
| **신규** | `config/category_ftc_mapping_v1.json` | - | 8대 대분류 ↔ 공정위 15개 업종 매핑 설계안 (`PROPOSED_FOR_APPROVAL`) |
| **수정** | `src/stage4e/api/database.py` | 분석 DB 읽기 전용 풀 | 공정위 DB 전용 읽기 풀 `get_ftc_connection()` 추가 (`mode=ro`) |
| **신규** | `src/stage4e/api/routers/ftc_macro.py` | - | 공정위 최신 상태, 벤치마크, 4개년 추세 읽기 API 라우터 |
| **수정** | `src/stage4e/api/main.py` | FastAPI 앱 및 라우터 등록 | `/api/v1/ftc` 신규 라우터 등록 |
| **수정** | `src/stage4e/api/schemas.py` | Pydantic v2 스키마 | 공정위 벤치마크 및 추세 응답 스키마 정의 |
| **수정** | `frontend/src/services/api.js` | API 통신 함수 | `fetchFtcStatus`, `fetchFtcBenchmark`, `fetchFtcTrends` 추가 |
| **신규** | `frontend/src/components/FtcBenchmarkPanel.jsx` | - | 공정위 거시 벤치마크 요약 카드 및 툴팁 위젯 (UI 비침범) |
| **신규** | `frontend/src/components/CategoryFilterBar.jsx` | - | 8대 대분류 탭/셀렉터 및 연도 선택 UI |
| **수정** | `frontend/src/App.jsx` | 전역 상태 및 레이아웃 | 업종 선택 전역 상태 신설, FTC API 연동, 패널 배치 |
| **수정** | `frontend/src/index.css` | 스타일시트 | FTC 카드, 배지, 반응형 모바일 그리드 CSS 추가 |

---

## 3. 업종 매핑 설계 (Category Mapping Architecture - R1 정정)

> [!NOTE]
> **거버넌스 정정**: `config/food_category_taxonomy_v1.json`에 정의된 8대 대분류·48개 중분류 표준 분류체계를 기반으로 하되, 공정위 15개 업종과의 연결은 기술적 통합을 위한 **`대분류 수준의 승인 대기 제안(PROPOSED_FOR_APPROVAL)`**이며 공식 기관 매핑이 아닙니다. 사용자 최종 검토 및 승인 전까지 본 매핑 설정을 확정 상태로 표시하지 않습니다.

### 3.1 공정위 15개 업종 2026년 실측표 (DB 쿼리 전수 검증)

`data/ftc_macro_statistics_v1.sqlite3`의 `ftc_industry_macro_summary` 테이블에서 실측한 2026년 15개 업종의 공식 데이터 전수입니다.

| 순번 | 공정위 업종명 (`tpbizMclsfNm`) | 전체 레코드 (`record_count`) | 총 가맹점 (`sum_frcs_cnt`) | 총 직영점 (`sum_dms_cnt`) | 양수 매출 (`sls_pos`) | 0원 매출 (`sls_zero`) | 결측치 (`sls_null`) | 중위 매출 (`median_sls`) | 5% 절사평균 (`trimmed_5pct`) | 가중평균 (`weighted_avg`) | 가중평균 분모 (`denom_stores`) | 자동 대사 ($\Delta$) |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| 1 | **기타 외국식** | 102 | 1,340 | 87 | 69 | 30 | 3 | 328,623.0 | 371,856.29 | 357,052.66 | 1,200 | $\Delta = 0$ (일치) |
| 2 | **기타 외식** | 520 | 10,396 | 453 | 399 | 112 | 9 | 278,128.0 | 304,572.40 | 333,782.35 | 9,961 | $\Delta = 0$ (일치) |
| 3 | **분식** | 220 | 7,179 | 230 | 147 | 70 | 3 | 247,174.0 | 264,102.71 | 263,666.82 | 6,675 | $\Delta = 0$ (일치) |
| 4 | **서양식** | 119 | 1,316 | 136 | 81 | 34 | 4 | 322,232.0 | 370,411.22 | 334,949.92 | 1,231 | $\Delta = 0$ (일치) |
| 5 | **아이스크림/빙수** | 29 | 448 | 29 | 23 | 4 | 2 | 167,404.0 | 160,650.90 | 162,714.27 | 416 | $\Delta = 0$ (일치) |
| 6 | **음료 (커피 외)** | 35 | 1,481 | 88 | 25 | 9 | 1 | 190,221.0 | 190,679.39 | 241,171.08 | 1,452 | $\Delta = 0$ (일치) |
| 7 | **일식** | 258 | 3,317 | 281 | 178 | 71 | 9 | 323,361.5 | 402,962.93 | 642,682.71 | 3,129 | $\Delta = 0$ (일치) |
| 8 | **제과제빵** | 142 | 2,332 | 208 | 96 | 44 | 2 | 177,646.0 | 257,220.64 | 226,086.79 | 2,238 | $\Delta = 0$ (일치) |
| 9 | **주점** | 242 | 4,863 | 165 | 149 | 84 | 9 | 285,020.0 | 318,659.92 | 282,646.92 | 4,524 | $\Delta = 0$ (일치) |
| 10 | **중식** | 143 | 1,791 | 108 | 89 | 50 | 4 | 412,334.0 | 445,207.74 | 415,843.22 | 1,644 | $\Delta = 0$ (일치) |
| 11 | **치킨** | 274 | 14,637 | 109 | 216 | 49 | 9 | 172,284.0 | 197,993.61 | 305,794.14 | 14,418 | $\Delta = 0$ (일치) |
| 12 | **커피** | 403 | 12,192 | 755 | 276 | 112 | 15 | 166,491.0 | 188,420.09 | 270,138.88 | 11,958 | $\Delta = 0$ (일치) |
| 13 | **패스트푸드** | 59 | 2,635 | 337 | 38 | 21 | 0 | 228,807.5 | 283,143.97 | 516,130.76 | 2,570 | $\Delta = 0$ (일치) |
| 14 | **피자** | 117 | 4,143 | 83 | 85 | 25 | 7 | 238,550.0 | 265,197.62 | 257,327.21 | 4,017 | $\Delta = 0$ (일치) |
| 15 | **한식** | 1,858 | 29,557 | 1,248 | 1,204 | 584 | 70 | 361,174.5 | 394,210.78 | 395,702.93 | 27,187 | $\Delta = 0$ (일치) |
| **합계** | **전체 15개 업종** | **4,521** | **97,627** | **4,317** | **3,075** | **1,299** | **147** | - | - | - | **92,520** | **$\Delta = 0$ (100% 완전 대사)** |

*(단위: 건, 개소, 천원 / 대사 공식: $\text{sls\_pos} + \text{sls\_zero} + \text{sls\_null} == \text{record\_count}$, 전 행 오차 0건 검증 완료)*

### 3.2 지도 8대 대분류 → 공정위 매핑 제안표 및 분류 상태 명세

```
[지도 8대 대분류]                              [공정위 15대 업종]
 CAT_MAJ_01 (한식)              ──( 제안 1:1 )─>  한식
 CAT_MAJ_02 (중식)              ──( 제안 1:1 )─>  중식
 CAT_MAJ_03 (일식)              ──( 제안 1:1 )─>  일식
 CAT_MAJ_04 (양식·세계음식)     ──( 제안 N:1 )─>  서양식 + 기타 외국식
 CAT_MAJ_05 (치킨·패스트푸드)   ──( 제안 N:1 )─>  치킨 + 패스트푸드 + 피자
 CAT_MAJ_06 (분식·간편식)       ──( 제안 1:1 )─>  분식
 CAT_MAJ_07 (카페·음료)         ──( 제안 N:1 )─>  커피 + 음료 (커피 외)
 CAT_MAJ_08 (베이커리·디저트)   ──( 제안 N:1 )─>  제과제빵 + 아이스크림/빙수
                                             [미매핑 격리 항목]
 (프로젝트 제외 정책)          ───────────>  주점 (EXCLUDED_BY_PROJECT_POLICY)
 (배타적 분류 불가)            ───────────>  기타 외식 (UNMAPPED_REVIEW)
```

1. **일대일 제안 매핑 (`ONE_TO_ONE`)**:
   - `CAT_MAJ_01` (한식) $\leftrightarrow$ `한식` (상태: `PROPOSED_FOR_APPROVAL`)
   - `CAT_MAJ_02` (중식) $\leftrightarrow$ `중식` (상태: `PROPOSED_FOR_APPROVAL`)
   - `CAT_MAJ_03` (일식) $\leftrightarrow$ `일식` (상태: `PROPOSED_FOR_APPROVAL`)
   - `CAT_MAJ_06` (분식·간편식) $\leftrightarrow$ `분식` (상태: `PROPOSED_FOR_APPROVAL`)
2. **다대일 합산 제안 매핑 (`MANY_TO_ONE_AGGREGATED`)**:
   - `CAT_MAJ_04` (양식·세계음식) $\leftarrow$ `서양식` (119건) + `기타 외국식` (102건) = **221건** (상태: `PROPOSED_FOR_APPROVAL`)
   - `CAT_MAJ_05` (치킨·패스트푸드) $\leftarrow$ `치킨` (274건) + `패스트푸드` (59건) + `피자` (117건) = **450건** (상태: `PROPOSED_FOR_APPROVAL`)
   - `CAT_MAJ_07` (카페·음료) $\leftarrow$ `커피` (403건) + `음료 (커피 외)` (35건) = **438건** (상태: `PROPOSED_FOR_APPROVAL`)
   - `CAT_MAJ_08` (베이커리·디저트) $\leftarrow$ `제과제빵` (142건) + `아이스크림/빙수` (29건) = **171건** (상태: `PROPOSED_FOR_APPROVAL`)
3. **매핑 제외 및 미매핑 격리 항목**:
   - `주점` (242건): AGENTS.md 제3.1조에 따라 지도 DB 수집 시 `I211(주점)`이 전면 제외되었으므로 `EXCLUDED_BY_PROJECT_POLICY`로 격리.
   - `기타 외식` (520건): 공정위 내 복합·기타 업종으로 특정 대분류에 임의 추정 매핑하는 것을 엄격히 금지하고 `UNMAPPED_REVIEW`로 격리.

### 3.3 복수 공정위 업종 합산 시 '평균의 단순 평균' 절대 금지 원칙 및 재산출 수식

두 개 이상의 공정위 업종을 하나의 대분류로 합산할 때, 각 업종의 평균을 단순 산술평균하면 표본 크기 차이로 인해 심각한 왜곡이 발생합니다.

$$\text{잘못된 방식 (금지):} \quad \frac{\text{Avg}(\text{치킨}) + \text{Avg}(\text{패스트푸드}) + \text{Avg}(\text{피자})}{3} \quad (\times)$$

**올바른 분자·분모 원자적 합산 재산식 (Mandatory Formula)**:
사전 집계 테이블 `ftc_industry_macro_summary`에 저장된 분자와 분모를 원시 합산하여 재계산합니다.

1. **브랜드 단순평균 (양수 매출 기준)**:
   $$\text{SimpleAvg}_{\text{Agg}} = \frac{\sum_{k \in \text{Mapped}} \text{sum\_sls\_amount}_k}{\sum_{k \in \text{Mapped}} \text{sls\_positive\_record\_count}_k}$$
2. **점포수 가중평균**:
   $$\text{WeightedAvg}_{\text{Agg}} = \frac{\sum_{k \in \text{Mapped}} \text{sum\_weighted\_sls\_amount}_k}{\sum_{k \in \text{Mapped}} \text{denom\_store\_weighted\_sls}_k}$$
3. **합산 중앙값 및 절사평균 처리**:
   - 중앙값과 절사평균은 비선형 통계량이므로 요약 테이블의 값들을 합산할 수 없습니다.
   - 따라서 대분류 합산 요청 시에는 원본 레코드 테이블(`ftc_brand_macro_records`)에서 매핑된 업종들의 `avg_sls_amt > 0` 레코드 세트를 직접 조회하여 통합 정렬 후 중앙값 및 절사평균을 정확히 산출합니다.

### 3.4 하드코딩 방지를 위한 매핑 설정 파일 구조 (`config/category_ftc_mapping_v1.json`)

```json
{
  "mapping_version": "v1.0.0-draft-r1",
  "source_standard": "FTC Eatout Statistics 15 Categories",
  "target_standard": "Franchise Dashboard 8 Major Categories (AGENTS.md)",
  "governance_note": "config/food_category_taxonomy_v1.json의 8대 대분류·48개 중분류 체계를 준용하며, 공정위 15개 업종과의 연계는 대분류 수준의 승인 대기 제안(PROPOSED_FOR_APPROVAL) 상태입니다.",
  "rules": {
    "allow_estimation": false,
    "prevent_average_of_averages": true
  },
  "mappings": [
    {
      "category_major_id": "CAT_MAJ_01",
      "category_major_name": "한식",
      "ftc_tpbiz_list": ["한식"],
      "mapping_type": "ONE_TO_ONE",
      "status": "PROPOSED_FOR_APPROVAL"
    },
    {
      "category_major_id": "CAT_MAJ_04",
      "category_major_name": "양식·세계음식",
      "ftc_tpbiz_list": ["서양식", "기타 외국식"],
      "mapping_type": "MANY_TO_ONE_AGGREGATED",
      "status": "PROPOSED_FOR_APPROVAL"
    },
    {
      "category_major_id": "CAT_MAJ_05",
      "category_major_name": "치킨·패스트푸드",
      "ftc_tpbiz_list": ["치킨", "패스트푸드", "피자"],
      "mapping_type": "MANY_TO_ONE_AGGREGATED",
      "status": "PROPOSED_FOR_APPROVAL"
    }
  ],
  "unmapped_ftc_categories": [
    {
      "ftc_tpbiz_name": "주점",
      "reason": "EXCLUDED_BY_PROJECT_POLICY",
      "status": "ISOLATED_EXCLUDED"
    },
    {
      "ftc_tpbiz_name": "기타 외식",
      "reason": "INDETERMINATE_CROSS_CATEGORY",
      "status": "UNMAPPED_REVIEW"
    }
  ]
}
```

---

## 4. 백엔드 읽기 전용 API 계약 (Backend Read-Only API Contracts - R1 정정)

백엔드 라우터 경로: `/api/v1/ftc`
모든 시간대는 ISO-8601 한국 표준시(`+09:00`)를 엄격히 준수합니다.

### 4.1 엔드포인트 1: 최신 데이터 상태 조회 (`GET /api/v1/ftc/status`)
- **목적**: 대시보드 헤더 및 벤치마크 패널에 공정위 데이터의 최신 기준연도, 회계연도, 데이터 버전, 수집 시각, 스냅샷 상태 메타데이터 제공.
- **파라미터**: 없음
- **응답 JSON 예시 (DB 실측 반영)**:
```json
{
  "status": "SUCCESS",
  "data": {
    "latest_benchmark_year": "2026",
    "financial_year": "2025",
    "display_label": "2026년 공정위 등록 기준 · 2025 회계연도 실적",
    "snapshot_status": "LATEST_PROVIDED_SNAPSHOT",
    "is_snapshot": true,
    "collected_at": "2026-10-13 08:53:05",
    "total_records": 4521,
    "total_brands": 4515,
    "total_franchise_stores": 97627,
    "total_direct_stores": 4317,
    "available_years": ["2026", "2025", "2024", "2023"],
    "version_string": "2026년 공정위 등록 기준 스냅샷 (수집시각: 2026-10-13 08:53:05, 확정모수: 4521건)",
    "macro_notice": "수집 시점 기준 최신 제공 스냅샷이며 향후 모수가 변동될 수 있습니다."
  },
  "meta": {
    "cached": true,
    "cache_ttl_sec": 3600,
    "timestamp": "2026-10-13T18:56:00+09:00"
  }
}
```

### 4.2 엔드포인트 2: 업종별 최신 벤치마크 조회 (`GET /api/v1/ftc/benchmark/latest`)
- **목적**: 8대 대분류에 대응하는 공정위 거시 벤치마크 반환.
- **파라미터**:
  - `category_major_id` (string, 필수): 예: `CAT_MAJ_01` (한식)
  - `year` (string, 선택, 기본값: `2026`): 특정 연도 수동 선택 시 사용
- **대체 정책**:
  - 사용자가 특정 연도(`year=2024` 등)를 명시한 경우 다른 연도로 자동 대체하지 않으며, 데이터가 없으면 `NO_DATA_FOR_REQUESTED_YEAR`를 반환합니다.
  - 자동 대체는 기본 최신연도 조회에서 매핑된 업종 전체가 2026년에 부재할 때만 위젯 전체를 2025년으로 일괄 대체합니다.
- **응답 JSON 예시 (2026년 한식 정상 응답 - DB 실측치 100% 반영)**:
```json
{
  "status": "SUCCESS",
  "data": {
    "benchmark_year": "2026",
    "financial_year": "2025",
    "display_label": "2026년 공정위 등록 기준 · 2025 회계연도 실적",
    "is_fallback_applied": false,
    "fallback_reason": null,
    "category_major_id": "CAT_MAJ_01",
    "category_major_name": "한식",
    "mapped_ftc_categories": ["한식"],
    "mapping_type": "ONE_TO_ONE",
    "mapping_status": "PROPOSED_FOR_APPROVAL",
    "sample_metrics": {
      "total_brand_records": 1858,
      "sales_positive_records": 1204,
      "sales_zero_records": 584,
      "sales_null_records": 70,
      "total_franchise_stores": 29557,
      "total_direct_stores": 1248
    },
    "sales_benchmarks": {
      "median_sales_thousand_krw": 361174.5,
      "trimmed_mean_5pct_thousand_krw": 394210.78,
      "store_weighted_avg_thousand_krw": 395702.93,
      "simple_avg_positive_thousand_krw": 437251.23,
      "all_records_avg_thousand_krw": 294435.39,
      "recommended_primary_metric": "median_sales_thousand_krw",
      "recommended_secondary_metric": "trimmed_mean_5pct_thousand_krw",
      "weighted_avg_denominator_stores": 27187
    },
    "startup_cost_components": {
      "reported_deposit_amount": {
        "median_thousand_krw": 13800.0,
        "mean_thousand_krw": 15592.25,
        "valid_count": 1855,
        "field_note": "공정위 원본 depstAmt 값이며 구성항목 합계와 항상 일치하지 않습니다."
      },
      "franchise_fee_jng_amt": {
        "median_thousand_krw": 5500.0,
        "mean_thousand_krw": 8191.43,
        "valid_count": 1855
      },
      "education_fee_edu_amt": {
        "median_thousand_krw": 3300.0,
        "mean_thousand_krw": 4464.25,
        "valid_count": 1855
      },
      "guarantee_fee_grnte_amt": {
        "median_thousand_krw": 2000.0,
        "mean_thousand_krw": 3211.46,
        "valid_count": 1855
      },
      "interior_cost_intrr_amt": {
        "median_thousand_krw": 44000.0,
        "mean_thousand_krw": 48542.13,
        "valid_count": 1856
      },
      "interior_cost_per_pyeong_3_3sqm": {
        "median_thousand_krw": 1760.0,
        "mean_thousand_krw": 1761.3,
        "valid_count": 1856
      },
      "tentative_derived_sum": {
        "median_thousand_krw": 133400.0,
        "mean_thousand_krw": 147690.85,
        "valid_count": 1858,
        "is_official_stat": false,
        "disclaimer": "본 합계는 공정위 공인 공식 총창업비용이 아니며 원본 항목(예치금+기타+인테리어)을 합산한 잠정 파생 지표입니다."
      }
    },
    "quality_notices": [
      {
        "type": "SNAPSHOT_NOTICE",
        "badge": "최신 제공 스냅샷",
        "message": "수집 시점 기준 최신 제공 스냅샷이며 향후 모수가 변동될 수 있습니다."
      },
      {
        "type": "ZERO_SALES_NOTICE",
        "badge": "매출 0원 공시 31.4%",
        "message": "전체 브랜드 중 584개(31.4%)가 매출 0원으로 공시되어 있어 단순평균 대신 중앙값(Median) 지표를 확인하십시오."
      }
    ]
  },
  "meta": {
    "calculation_method": "Actual DB values from ftc_industry_macro_summary and ftc_brand_macro_records",
    "timestamp": "2026-10-13T18:56:00+09:00"
  }
}
```

- **대체 연도 응답 예시 (2026년 데이터 부재 시 2025 대체 - DB 실측 반영)**:
```json
{
  "status": "SUCCESS",
  "data": {
    "benchmark_year": "2025",
    "financial_year": "2024",
    "display_label": "2025년 공정위 등록 기준 · 2024 회계연도 실적",
    "is_fallback_applied": true,
    "fallback_reason": "2026년 등록 데이터 부재로 최신 완결 후보 연도인 2025년 실적으로 원자적 대체 표출 중",
    "category_major_id": "CAT_MAJ_01",
    "category_major_name": "한식",
    "sample_metrics": {
      "total_brand_records": 2532,
      "sales_positive_records": 1493,
      "sales_zero_records": 967,
      "sales_null_records": 72,
      "total_franchise_stores": 43566,
      "total_direct_stores": 1899
    },
    "sales_benchmarks": {
      "median_sales_thousand_krw": 347197.0,
      "trimmed_mean_5pct_thousand_krw": 382823.8,
      "store_weighted_avg_thousand_krw": 399445.82,
      "simple_avg_positive_thousand_krw": 450832.77,
      "all_records_avg_thousand_krw": 273615.17,
      "weighted_avg_denominator_stores": 39537
    },
    "quality_notices": [
      {
        "type": "FALLBACK_NOTICE",
        "badge": "2025년 대체 표시",
        "message": "2026년 스냅샷 미등록으로 2025년 실적으로 일괄 전환되었습니다 (최신 완결 후보 연도이며 공식 마감 여부는 확인되지 않음)."
      }
    ]
  },
  "meta": {
    "timestamp": "2026-10-13T18:56:00+09:00"
  }
}
```

- **명시적 연도 조회 시 데이터 부재 응답 (`NO_DATA_FOR_REQUESTED_YEAR`)**:
```json
{
  "status": "NO_DATA",
  "error_code": "NO_DATA_FOR_REQUESTED_YEAR",
  "message": "요청하신 연도(2027)에 해당하는 공정위 등록 데이터가 존재하지 않습니다. 사용자가 지정한 연도는 다른 연도로 자동 대체되지 않습니다.",
  "requested_year": "2027"
}
```

### 4.3 엔드포인트 3: 업종별 4개년 다년도 추세 조회 (`GET /api/v1/ftc/trends`)
- **목적**: 2023년부터 2026년까지 4개년 거시 추세 차트(전체 모집단 기준 횡단면 추세) 데이터 제공.
- **응답 JSON 예시 (한식 4개년 DB 실측치 100% 반영)**:
```json
{
  "status": "SUCCESS",
  "data": {
    "category_major_id": "CAT_MAJ_01",
    "category_major_name": "한식",
    "trend_mode": "FULL_POPULATION_CROSS_SECTIONAL",
    "balanced_panel_active": false,
    "panel_inactive_reason": "존속 브랜드 균형 패널은 생존편향 위험으로 인해 비활성화 상태 유지",
    "yearly_series": [
      {
        "benchmark_year": "2023",
        "financial_year": "2022",
        "is_snapshot": false,
        "sample_count": 2148,
        "total_franchise_stores": 37977,
        "total_direct_stores": 1660,
        "median_sales_thousand_krw": 298016.0,
        "trimmed_mean_5pct_thousand_krw": 330650.4,
        "store_weighted_avg_thousand_krw": 324602.19,
        "simple_avg_thousand_krw": 375513.78,
        "denom_stores": 34406
      },
      {
        "benchmark_year": "2024",
        "financial_year": "2023",
        "is_snapshot": false,
        "sample_count": 2340,
        "total_franchise_stores": 41914,
        "total_direct_stores": 1798,
        "median_sales_thousand_krw": 330611.0,
        "trimmed_mean_5pct_thousand_krw": 371714.33,
        "store_weighted_avg_thousand_krw": 360391.18,
        "simple_avg_thousand_krw": 414718.22,
        "denom_stores": 37789
      },
      {
        "benchmark_year": "2025",
        "financial_year": "2024",
        "is_snapshot": false,
        "sample_count": 2532,
        "total_franchise_stores": 43566,
        "total_direct_stores": 1899,
        "median_sales_thousand_krw": 347197.0,
        "trimmed_mean_5pct_thousand_krw": 382823.8,
        "store_weighted_avg_thousand_krw": 399445.82,
        "simple_avg_thousand_krw": 450832.77,
        "denom_stores": 39537
      },
      {
        "benchmark_year": "2026",
        "financial_year": "2025",
        "is_snapshot": true,
        "snapshot_badge": "최신 제공 스냅샷",
        "sample_count": 1858,
        "total_franchise_stores": 29557,
        "total_direct_stores": 1248,
        "median_sales_thousand_krw": 361174.5,
        "trimmed_mean_5pct_thousand_krw": 394210.78,
        "store_weighted_avg_thousand_krw": 395702.93,
        "simple_avg_thousand_krw": 437251.23,
        "denom_stores": 27187
      }
    ],
    "macro_guidance": "금액 지표는 물가변동 미반영 명목금액이며, 2026년은 수집 시점의 최신 제공 스냅샷으로 이전 연도와 모집단이 달라, 점포 수 차이를 산업 성장·감소로 직접 해석할 수 없습니다."
  },
  "meta": {
    "timestamp": "2026-10-13T18:56:00+09:00"
  }
}
```

### 4.4 엔드포인트 4: 연도 목록 메타 조회 (`GET /api/v1/ftc/years`)
```json
{
  "status": "SUCCESS",
  "data": [
    {
      "benchmark_year": "2026",
      "financial_year": "2025",
      "is_default": true,
      "is_snapshot": true,
      "label": "2026년 공정위 등록 (최신 스냅샷)"
    },
    {
      "benchmark_year": "2025",
      "financial_year": "2024",
      "is_default": false,
      "is_snapshot": false,
      "label": "2025년 공정위 등록 (최신 완결 후보)"
    },
    {
      "benchmark_year": "2024",
      "financial_year": "2023",
      "is_default": false,
      "is_snapshot": false,
      "label": "2024년 공정위 등록 (2023 실적)"
    },
    {
      "benchmark_year": "2023",
      "financial_year": "2022",
      "is_default": false,
      "is_snapshot": false,
      "label": "2023년 공정위 등록 (2022 실적)"
    }
  ],
  "meta": {
    "timestamp": "2026-10-13T18:56:00+09:00"
  }
}
```

---

## 5. 화면 정보구조 및 비침범 UI 설계 (Information Architecture)

```
┌────────────────────────────────────────────────────────────────────────┐
│ [Header] 외식 프랜차이즈 3D GIS 상황실 | 2026-07 기준 | API 정상 [새로고침] │
├────────────────────────────────────────────────────────────────────────┤
│ [CategoryFilterBar] [전체] [한식] [중식] [일식] [양식] [치킨·패스트] ...│
├───────────────┬────────────────────────────────────────┬───────────────┤
│ [좌측 패널]   │ [중앙 3D GIS 지도 뷰포트]              │ [우측 패널]   │
│ MarketSummary │ (MapLibre OSM 래스터 타일 +            │ HotspotsPanel │
│ 73.5만 점포   │  광진구 건대입구 100m 밀집도 서클 +    │ Top 5 상권    │
│ 침투율 22.89% │  핫스팟 핀)                            │               │
│               ├────────────────────────────────────────┤               │
│               │ [지도 하단 플로팅 오버레이 (Collapsible)]│               │
│               │ 📊 공정위 2026 거시 벤치마크 요약 카드 │               │
│               │ (2026 등록·2025 실적 | 중위매출: 3.6억)│               │
└───────────────┴────────────────────────────────────────┴───────────────┘
```

### 5.1 데스크톱 정보구조 (1920×1080)
1. **상단 서브 바 (`CategoryFilterBar`)**:
   - 8대 대분류 필터 탭과 기준연도 선택기(`2026 (최신 스냅샷)` 기본 선택)를 슬림하게 배치(높이 44px).
2. **공정위 벤치마크 카드 (`FtcBenchmarkCard`)**:
   - 지도를 가리지 않도록 지도 뷰포트 우측 상단 플로팅 오버레이(너비 340px) 또는 좌측 `MarketSummary` 패널 내 탭 전환/하단 카드 형태로 배치.
   - 접기/펼치기 토글(Chevron) 기본 탑재로 사용자가 언제든지 지도를 100% 넓게 볼 수 있도록 보장.
3. **카드 내부 구성요소**:
   - **배지 영역**: `2026년 등록 · 2025 실적` (녹색 고대비 배지), `최신 제공 스냅샷` (오렌지 배지).
   - **핵심 지표 (Hero KPI)**:
     - 대표 매출: **`36,117 만원` (중앙값)** / 보조: `39,421 만원 (5% 절사평균)`
     - 점포 규모: 가맹점 `29,557 개소`, 직영점 `1,248 개소`
   - **창업비용 아코디언**:
     - 가맹비 550만원 · 교육비 330만원 · 보증금 200만원 · 인테리어(평당 176만원)
     - 툴팁: *"공정위 등록 정보공개서 제출 기준이며, 잠정 합계는 참고용입니다."*
   - **4개년 미니 스파크라인 차트**:
     - 2023 ~ 2026년 중앙값 추세선 (2026년 포인트는 점선 원으로 스냅샷 구분).

### 5.2 모바일 정보구조 (390×844)
1. **바텀 시트 (Bottom Sheet) 3단계 제어**:
   - **Collapsed (높이 64px)**: 지도 하단에 `한식 벤치마크: 중위매출 3.6억 (2026 스냅샷)` 한 줄 앵커만 노출 $\rightarrow$ 지도가 뷰포트의 70% 이상 유지됨.
   - **Half (높이 380px)**: 스와이프 업 시 대표 매출, 표본수, 창업비용 요약 노출.
   - **Expanded (높이 700px)**: 4개년 추세 차트 및 데이터 품질 안내 전수 노출.
2. **모바일 가로 스크롤 완전 차단 (0px)**:
   - 모든 벤치마크 카드는 `width: 100%`, `box-sizing: border-box`, `min-width: 0`을 준수하여 390px 뷰포트 내에 안전 패딩(16px)을 유지.

### 5.3 9대 UI 상태별 와이어프레임 텍스트 명세 (R1 정정)

```
[1. 정상 상태 (Normal - 2026 Snapshot)]
┌─────────────────────────────────────────────────────────────┐
│ [한식] 2026년 공정위 등록 기준 · 2025 회계연도 실적         │
│ [배지: 최신 제공 스냅샷] [수집: 2026-10-13 08:53, N=1,858]  │
│ ─────────────────────────────────────────────────────────── │
│ • 대표 중위 매출 : 36,117 만원 (중앙값, N_pos=1,204)       │
│ • 보조 절사 평균 : 39,421 만원 (상하위 5% 절사평균)        │
│ • 점포 가중 평균 : 39,570 만원 (가맹점수 27,187개 가중)     │
│ ─────────────────────────────────────────────────────────── │
│ 창업비용 구성 (중위): 가맹 550만 / 교육 330만 / 보증 200만   │
│ 인테리어: 4,400만원 (평당 176만원)                         │
└─────────────────────────────────────────────────────────────┘

[2. 2025년 대체 상태 (Fallback - 2025)]
┌─────────────────────────────────────────────────────────────┐
│ ⚠️ [배지: 2025년 대체 표시] [2024 회계연도 실적 후보본]      │
│ "2026년 스냅샷 미등록 업종으로 2025년 실적 일괄 대체"        │
│ ─────────────────────────────────────────────────────────── │
│ (위젯 내부의 모든 분모·분자·표본이 2025년 단일연도로 일괄 전환)│
└─────────────────────────────────────────────────────────────┘

[3. 업종 매핑 불가 상태 (Unmapped Review)]
┌─────────────────────────────────────────────────────────────┐
│ ℹ️ [배지: 거시 벤치마크 미제공]                              │
│ "선택하신 업종(기타 외식)은 공정위 분류와 배타적 매핑이      │
│  불가하여 거시 벤치마크를 제공하지 않습니다."              │
│ (추정 매핑 금지 원칙 준수)                                   │
└─────────────────────────────────────────────────────────────┘

[4. 0원·결측치 비율 경고 (High Zero/Null Ratio)]
┌─────────────────────────────────────────────────────────────┐
│ ⚠️ [배지: 매출 0원 공시 31.4%] (양수 1,204 / 0원 584개)     │
│ "매출 0원 공시 브랜드 비중이 높으므로 단순평균 대신          │
│  중앙값(Median) 지표를 확인하십시오."                       │
└─────────────────────────────────────────────────────────────┘

[5. 극단 이상치 감지 상태 (Extreme Outlier Notice)]
┌─────────────────────────────────────────────────────────────┐
│ 🚨 [배지: 이상치 왜곡 주의] (2024년 중식 단순평균 53.7억)   │
│ "원천 공시 오류 추정 6,296억 이상치가 포함되어 단순평균이   │
│  심각하게 왜곡되었습니다. 5% 절사평균(4.4억)을 참조하세요."  │
└─────────────────────────────────────────────────────────────┘

[6. 로딩 상태] -> 스켈레톤 UI (높이 24px, 40px 쉬머 애니메이션)
[7. 데이터 없음 상태] -> "해당 조건의 공정위 등록 데이터가 존재하지 않습니다."
[8. API/DB 연결 오류] -> "공정위 거시통계 서버 연결 지연 (재시도 버튼 노출)"
[9. 모바일 축소 상태] -> 한 줄 요약 칩 노출 (높이 64px 탭 바)
```

---

## 6. 대표지표 결정 및 통계적 근거 (Metric Decision Framework - R1 정정)

### 6.1 매출 대표지표 비교 분석 및 권장 우선순위

공정위 원본 데이터(23,537건) 실측 결과, 프랜차이즈 매출 데이터는 극단적인 우측 꼬리 분포(Right-skewed)와 0원 공시(33.7%)가 혼재되어 있습니다.

| 지표 후보 | 산출 수식 | 장점 | 단점 및 위험 | 권장 우선순위 |
| :--- | :--- | :--- | :--- | :---: |
| **중앙값 (Median)** | 정렬 후 50% 지점 수치 (`avg_sls_amt > 0`) | 이상치(6,296억 등)에 100% 불변, 전형적인 가맹점 수준 정확 대변 | 표본이 10개 미만으로 적을 때 계단식 불연속 발생 | **1순위 (대표 벤치마크)** |
| **5% 절사평균 (Trimmed Mean)** | 상·하위 5% 제외 후 산술평균 (`avg_sls_amt > 0`) | 이상치 왜곡 완화 + 통계적 유효성 보존 (중식 53.7억 $\rightarrow$ 4.4억 정상화) | 양 끝단 10% 표본 배제에 대한 사용자 설명 필요 | **2순위 (보조 벤치마크)** |
| **점포수 가중평균 (Weighted Avg)** | $\frac{\sum (\text{avgSlsAmt} \times \text{frcsCnt})}{\sum \text{frcsCnt}}$ | 대형 프랜차이즈의 시장 파급력 반영, 소비자가 실제 체감하는 평균에 근접 | 대형 브랜드 1~2개의 실적에 휘둘림, 신규 창업자 기준 괴리 | **3순위 (시장 규모 비교용)** |
| **단순평균 (Simple Mean)** | $\frac{1}{N_{pos}}\sum \text{avgSlsAmt}$ | 계산이 직관적 | **극단 이상치에 치명적 왜곡** (2024년 중식 단순평균 53.7억은 허구) | **단독 노출 절대 금지** |
| **0원 포함 전체평균 (All Mean)** | $\frac{1}{N}\sum \text{avgSlsAmt}$ | 전체 정보공개서 모수 포괄 | 0원(33.7%)으로 인해 실질 영업 매장 매출이 심각하게 과소평가됨 | **참고용 (0원 영향도 비교)** |

> **최종 결정**:
> - **화면 대표값 (Hero KPI)**: **`중앙값 (Median)`**
> - **화면 보조값 (Secondary KPI)**: **`5% 절사평균`** 및 **`점포수 가중평균`** (표본수 병기)
> - **단순평균**: 보조 지표 목록 하단에 배치하되, 5% 절사평균과의 괴리율이 20% 이상일 경우 `이상치 영향 경고` 툴팁을 강제 부착합니다.

### 6.2 창업비용 구성 및 `depstAmt` 명칭 거버넌스 (R1 정정)
공정위 원본 필드는 다음과 같이 분리 제공되며, **`공식 총창업비용`이라는 단일 항목은 API에 존재하지 않습니다.**

1. `reported_deposit_amount` (`depst_amt`):
   - 공정위 API의 원본 depstAmt 값입니다. 세부 구성항목의 합계와 항상 일치하지 않으며, 정확한 법적·회계적 정의는 별도 근거 확인 전까지 단정하지 않습니다.
   - 구성 항목 합계(`jng + edu + grnte`)와 100% 일치하지 않으므로(실측 일치율 95~97%), **`공식` 표현을 사용하지 않습니다.**
2. 개별 구성 항목:
   - 가맹비 (`jng_bzmn_jng_amt`)
   - 교육비 (`jng_bzmn_edu_amt`)
   - 보증금 (`jng_bzmn_grnte_amt`)
   - 기타비용 (`jng_bzmn_etc_amt`)
   - 인테리어 비용 (`intrr_amt`) 및 평당 인테리어 비용 (`unit_area_intrr_amt`)
3. **잠정 파생 합계 (`tentative_startup_cost_thousand`)의 거버넌스**:
   - 수식: `(depst_amt or 0) + (jng_bzmn_etc_amt or 0) + (intrr_amt or 0)`
   - 본 수치는 **절대 "공정위 공식 총창업비용"으로 표기할 수 없으며**, 반드시 **`항목 합산 잠정 창업비용 (참고용)`**으로 명시하고 개별 항목 내역을 함께 펼쳐서 보여주어야 합니다.

---

## 7. 다년도 비교 및 시계열 분석 원칙 (Multi-Year Principles - R1 정정)

1. **전체 모집단 횡단면 추세 (Cross-Sectional Trend) 기본 제공**:
   - 2023, 2024, 2025, 2026년 각 연도별 등록된 전체 외식 프랜차이즈 모집단을 대상으로 한 추세선만 기본 활성화합니다.
2. **존속 브랜드 균형 패널 (Balanced Panel) 비활성화 유지**:
   - 4개년 연속 관측 브랜드(2,504개)만을 묶는 패널 분석은 **생존편향(Survivorship Bias)**을 내포하므로, Phase 5B UI에서는 기본 비활성화(Toggle Off) 상태를 유지합니다.
3. **2026년 스냅샷의 직접 성장률 비교 제한**:
   - 2026년 총브랜드수(4,521건)와 총가맹점수(97,627개)는 2025년(6,519건 / 17.7만개)보다 물리적으로 적습니다.
   - 2026년은 수집 시점의 최신 제공 스냅샷으로 이전 연도와 모집단이 달라, 점포 수 차이를 산업 성장·감소로 직접 해석할 수 없으므로, **2025 $\rightarrow$ 2026년 단순 성장률(CAGR, 증감률) 계산은 비활성화하거나 `최신 제공 스냅샷 주의` 안내를 강제**합니다.
4. **명목금액 표기 원칙**:
   - 모든 금액은 한국은행 소비자물가지수(CPI) 조정 전의 **명목금액**임을 툴팁으로 명시합니다.

---

## 8. 성능 및 운영 아키텍처 설계 (Performance & Operations - R1 정정)

> [!NOTE]
> **성능 표현 정정**: 측정 전인 수치에 대해 단정적 사전 보장 표현을 배제하고, **`엔지니어링 성능 목표(Performance Targets)`**로 정정합니다. 실제 수치는 구현 후 실측 벤치마크를 통해 검증합니다.

```
[클라이언트 (브라우저)]
   │
   ├── 1. 지도 이동/줌/드래그 (BBOX 이벤트) ──> 지도 전용 API (소진공 점포 BBOX)
   │                                            (공정위 API 호출 0건!)
   │
   └── 2. 업종 탭 클릭 / 연도 변경         ──> 공정위 API (/api/v1/ftc/benchmark)
                                                │
                                                ▼
                                      [FastAPI In-Memory 캐시]
                                      (TTL: 3600초, 8대 업종 x 4개년 = 32개 엔트리)
                                                │
                                                ▼ (Cache Miss 시에만)
                                      [ftc_macro_statistics_v1.sqlite3]
                                      (mode=ro, mmap, 사전집계 테이블 조회)
```

### 8.1 4대 성능 엔지니어링 목표 (Performance Targets)
1. **API 응답 레이턴시 목표**:
   - 캐시 적중 시: **p95 50ms 이하**
   - 캐시 미적중 시: **p95 200ms 이하**
2. **네트워크 페이로드 크기 목표**:
   - 벤치마크 단일 응답: **Gzip 10KB 이하**
3. **지도 프레임레이트 및 회귀 방지 목표**:
   - 벤치마크 패널 마운트 상태에서도 지도 조작 시 **기존 지도 FPS(평균 55~60fps) 대비 유의미한 저하 없음**
   - 지도 조작(pan/zoom) 중 공정위 API 네트워크 요청 **0건 유지**
4. **캐시 무효화 정책**:
   - 불변 배치 파일이므로 TTL 3600초 적용. 2026년 스냅샷 재수집 발생 시 서버 캐시 즉시 무효화.

---

## 9. 결론 및 향후 구현 단계 로드맵 (Roadmap)

### 9.1 향후 구현 3단계 분할 제안
- **Step 1: 백엔드 API 및 DB 연결 계층 구축**
  - `database.py` 내 FTC DB 읽기 전용 풀 구성 (`mode=ro`)
  - `config/category_ftc_mapping_v1.json` 생성 및 매핑 로직 구현
  - `schemas.py` 및 `routers/ftc_macro.py` 엔드포인트 4종 구현 및 단위 테스트
- **Step 2: 프론트엔드 연동 및 벤치마크 위젯 제작**
  - `services/api.js` 통신 함수 확장
  - `CategoryFilterBar.jsx` 및 `FtcBenchmarkPanel.jsx` 제작 (와이어프레임 준수)
  - `App.jsx` 전역 상태 연결 및 390×844 모바일 바텀시트 반응형 CSS 튜닝
- **Step 3: 전수 검증 및 회귀 테스트**
  - 8대 업종 매핑 전수 대사
  - 2026 스냅샷 $\rightarrow$ 2025 대체 시나리오 E2E 테스트
  - 브라우저 레이턴시 및 가로 스크롤(0px) 최종 실측 검증
