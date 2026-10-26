# Phase 5D Step 5D-3 의미 안전성 및 회귀 검증 실행보고서

> **문서 상태**: 8대 필수 시나리오 전수 실측 검증 완료 (ALL PASS)  
> **수행 일시**: 2026-10-19 11:10:00 ~ 11:15:00 (KST)  
> **작업 지침**: [`.agent-workflow/TASK.md`](file:///d:/Franchise_Dashboard/.agent-workflow/TASK.md)  
> **원시 검증 데이터**: [`reports/phase5d_step3_validation.json`](file:///d:/Franchise_Dashboard/reports/phase5d_step3_validation.json)  
> **검증 스크립트**: [`scratch/verify_phase5d_step3_semantic_safety.mjs`](file:///d:/Franchise_Dashboard/scratch/verify_phase5d_step3_semantic_safety.mjs)  

---

## 1. 개요 및 검증 목적

본 보고서는 **Phase 5D Step 5D-3** 지침에 따라, Phase 5D Step 5D-2에서 구현된 공정거래위원회 전국 업종 벤치마크 패널의 **의미 안전성(Semantic Safety)**을 실제 브랜드·지역·8대 업종 조합에서 엄격하게 실측 검증하고, 기존 지도·필터·접근성·반응형 동작의 회귀 여부를 전수 확인한 결과를 기록합니다.

- **범위 준수**:
  - `collector.py`, `gangnam_food_stores.sqlite3`, `run_gangnam.bat` 보호 파일 3종은 일체 수정하지 않고 SHA-256 불변성을 확인했습니다.
  - 백엔드 API, SQLite 스키마, 수집기, 브랜드 매칭 알고리즘은 수정하지 않았습니다.
  - 검증 과정 중 비동기 카테고리 전환 시 DOM 렌더링 대기 결함(S3 타이밍 이슈)을 `scratch/verify_phase5d_step3_semantic_safety.mjs` 내에서 최소 수정하여 재현 및 100% 정상 통과를 확인했습니다.
  - 실측된 수치, 가시성 좌표, DOM 속성 및 화면 캡처 간의 사실 관계를 왜곡 없이 기록했습니다.

---

## 2. 보호 대상 파일 무결성 검증

프로젝트 핵심 보호 파일 3종에 대해 사전·사후 SHA-256 해시를 대조하였으며, 작업 전후 100% 일치함을 확인했습니다.

| 대상 파일 | 사전/사후 SHA-256 해시 | 파일 크기 (Bytes) | 무결성 판정 |
| :--- | :--- | :---: | :---: |
| [`collector.py`](file:///d:/Franchise_Dashboard/collector.py) | `341BAC12BB0AF58DCBDEBBA9459033521F27DF9817E35BAD8B21A4D07BA3369C` | 3,780 B | **일치 (PASS)** |
| [`gangnam_food_stores.sqlite3`](file:///d:/Franchise_Dashboard/gangnam_food_stores.sqlite3) | `FEE3B58651CFED5C390C0B95DB02B05EBE92DF18619A06F4E399D429236F3A78` | 15,831,040 B | **일치 (PASS)** |
| [`run_gangnam.bat`](file:///d:/Franchise_Dashboard/run_gangnam.bat) | `0582C3A1AE53450DDC482E9BF538510780CA2F14D44E987CC753D4E12C816491` | 66 B | **일치 (PASS)** |

---

## 3. 검증 환경 및 실행 방식

- **프론트엔드 환경**: `http://127.0.0.1:5173` (Vite v5.4.21 Dev Server)
- **백엔드 API 환경**: `http://127.0.0.1:8000` (FastAPI / Uvicorn Daemon)
- **자동화 드라이버**: Chrome DevTools Protocol (CDP, Headless Chrome, 1440×900 데스크톱 및 390×844 모바일 뷰포트)
- **가시성 측정 방식**: DOM 속성(`display`, `visibility`, `opacity`), 바운딩 박스 크기(`width > 0`, `height > 0`), 뷰포트 교차(`intersectsViewport`), 모든 상위 조상 컨테이너의 오버플로 클리핑(`notClippedByAncestor`), 닫힌 드로어 및 축소 시트 차폐 여부를 정밀 계산하는 `inspectVisibility` 헬퍼 적용.

---

## 4. 8대 필수 시나리오 검증 결과 총괄표

| ID | 필수 검증 시나리오 | 뷰포트 | 실제 지역/업종 조건 | 핵심 단언 및 실측 지표 | 판정 | 증빙 캡처 파일 |
| :---: | :--- | :---: | :--- | :--- | :---: | :--- |
| **S1** | 실제 브랜드 선택 시 공정위 수치가 해당 브랜드 실적으로 표현되지 않음 | 1440×900 | 서울 광진구 (`11215`) / 카페·음료 (`CAT_MAJ_07`) | 1위 브랜드(메가MGC커피) 행 클릭 후에도 `.hero-scope-disclaimer` 상시 가시, 브랜드 단독 실적 왜곡 문구 0건 | **PASS** | [`S1 증빙`](file:///d:/Franchise_Dashboard/reports/phase5d_step3_s1_brand_disclaimer_coexistence.png) |
| **S2** | 지역 변경 후에도 공정위 수치가 전국 통계임을 첫 화면에서 확인 가능 | 1440×900 | 서울 광진구 (`11215`) / 치킨·패스트푸드 (`CAT_MAJ_05`) | 첫 화면(스크롤 0)에서 `전국 가맹본부 대표매출 (중앙값)` 및 비귀속 고지 상시 가시 | **PASS** | [`S2 증빙`](file:///d:/Franchise_Dashboard/reports/phase5d_step3_s2_regional_macro_benchmark.png) |
| **S3** | 확정된 8대 대분류 각각에서 공정위 업종 매핑과 표시 제목 일치 | 1440×900 | 전국 (`00`) / 8대 대분류 전수 순회 | 8대 대분류 전수 배지 텍스트 일치, 비귀속문구 업종명 포함, 유효 중앙값 노출 (8/8) | **PASS** | [`S3 증빙`](file:///d:/Franchise_Dashboard/reports/phase5d_step3_s3_8categories_mapping.png) |
| **S4** | 전국·지역·브랜드·업종 선택 조합에서 데이터 출처와 모집단 분리 | 1440×900 | 서울 광진구 (`11215`) / 카페·음료 (`CAT_MAJ_07`) / 2024 | 소진공 4,507개소 점포 기반 vs 공정위 가맹본부 표본(403개 브랜드) 및 '개별 매장 실측치 아님' 명시 | **PASS** | [`S4 증빙`](file:///d:/Franchise_Dashboard/reports/phase5d_step3_s4_source_segregation.png) |
| **S5** | 데스크톱 1440×900 및 모바일 390×844에서 핵심 안내 미잘림·미숨김 보장 | 1440×900<br>390×844 | 전국 (`00`) / 한식 (`CAT_MAJ_01`) | 데스크톱 조상 클리핑 0건, 모바일 피크 바 `공정위 전국`·`(업종 참고치)` 노출, 확장 시 첫 844px 내 공지 배너 가시 | **PASS** | [`S5 Desk`](file:///d:/Franchise_Dashboard/reports/phase5d_step3_s5_desktop_not_clipped.png)<br>[`S5 Peek`](file:///d:/Franchise_Dashboard/reports/phase5d_step3_s5_mobile_peek_visible.png)<br>[`S5 Exp`](file:///d:/Franchise_Dashboard/reports/phase5d_step3_s5_mobile_expanded_visible.png) |
| **S6** | 모바일 가로 오버플로 0 및 키보드 접근성·패널 접기 유지 | 390×844<br>1440×900 | 전국 (`00`) / 한식 (`CAT_MAJ_01`) | 모바일 피크·확장 `scrollWidth = 390px`(초과 0px), Enter 열기/ESC 닫기, 모바일 Enter 토글, 데스크톱 접기/펼치기 정상 | **PASS** | [`S6 증빙`](file:///d:/Franchise_Dashboard/reports/phase5d_step3_s6_overflow_and_keyboard.png) |
| **S7** | 지도, 필터, 지역 브랜드 Top 5, 공정위 연도 선택 회귀 없음 확인 | 1440×900 | 서울 광진구 (`11215`) / 치킨·패스트푸드 (`CAT_MAJ_05`) | MapLibre WebGL 캔버스 렌더링 정상, 광진구 Top 5 브랜드 5건 표출, 2024→2025 연도 전환 정상 | **PASS** | [`S7 증빙`](file:///d:/Franchise_Dashboard/reports/phase5d_step3_s7_map_filters_top5_regression.png) |
| **S8** | 2026 진행형 스냅샷 경고가 호버 없이 유지됨 | 1440×900 | 전국 (`00`) / 한식 (`CAT_MAJ_01`) / 2026 | `.snapshot-inline-alert` 호버 없이 즉시 가시 (`top: 254px`, `opacity: 1`), 30% 미등록 및 직접 비교 불가 문구 일치 | **PASS** | [`S8 증빙`](file:///d:/Franchise_Dashboard/reports/phase5d_step3_s8_snapshot_warning_no_hover.png) |

---

## 5. 시나리오별 상세 실측 데이터

### 5.1 [시나리오 1] 실제 브랜드 선택 시 공정위 수치가 해당 브랜드 실적으로 표현되지 않음
- **지역/업종 상태**: `sidoValue: "11"`, `sigunguValue: "11215"`, `actualRegion: "서울 서울특별시 광진구"`, `category: "CAT_MAJ_07"`
- **광진구 상위 브랜드 카드**:
  - `brandCardExists`: `true`, `brandRowCount`: 5개
  - 1위 브랜드 식별: `메가MGC커피` (점포수 23개소, 침투율 2.45%)
- **브랜드 상호작용 후 공정위 패널 평가**:
  - 히어로 라벨: `"전국 가맹본부 대표매출 (중앙값)"` (`heroLabelIsNationwideMedian: true`)
  - 히어로 수치: `"16,703만원 (1.67억원)"`
  - 비귀속 안내문 (`.hero-scope-disclaimer`):
    - 텍스트: `"* 공정위 정기공시 전국 카페·음료 가맹본부 기준 거시 통계이며, 특정 브랜드나 개별 점포의 실적이 아닙니다."`
    - 좌표: `left: 1036, top: 435, width: 360, height: 36`
    - 가시성: `isActuallyVisible: true`, `notClippedByAncestor: true`
  - 패널 내 텍스트 검색 결과: `메가MGC커피 매출`, `메가MGC커피 실적`, `메가MGC커피 대표매출` 등 단독 귀속 문구 **0건** (`erroneouslyClaimsBrand: false`).

### 5.2 [시나리오 2] 지역 변경 후에도 공정위 수치가 전국 통계임을 첫 화면에서 확인 가능
- **지역/업종 상태**: `sidoValue: "11"`, `sigunguValue: "11215"` (서울 광진구), `category: "CAT_MAJ_05"` (치킨·패스트푸드)
- **첫 화면 가시성 (스크롤 위치: `scrollY = 0`)**:
  - `.hero-label`: 텍스트 `"전국 가맹본부 대표매출 (중앙값)"`, `top: 382px`, `isActuallyVisible: true`
  - `.hero-stat-number`: `"19,312만원 (1.93억원)"`, `top: 402px`, `isActuallyVisible: true`
  - `.hero-scope-disclaimer`: `top: 435px`, `isActuallyVisible: true`
  - 판정: 광진구 지역 모드 진입 직후 스크롤 없이도 공정위 수치가 전국 단위 통계이며 개별 점포 실적이 아님이 첫 화면에서 즉시 확인됨.

### 5.3 [시나리오 3] 확정된 8대 대분류 각각에서 공정위 업종 매핑과 표시 제목 일치
8대 대분류 전수를 순회하며 공정위 거시 벤치마크 패널 매핑을 실측했습니다.

| 분류 ID | 업종 대분류명 | 패널 배지 텍스트 | 비귀속 고지문 내 업종명 포함 | 대표 매출 수치 (중앙값) | 판정 |
| :---: | :--- | :--- | :---: | :---: | :---: |
| `CAT_MAJ_01` | 한식 | `🍚 한식` | 포함 | 36,117만원 (3.61억원) | **PASS** |
| `CAT_MAJ_02` | 중식 | `🥟 중식` | 포함 | 41,233만원 (4.12억원) | **PASS** |
| `CAT_MAJ_03` | 일식 | `🍣 일식` | 포함 | 32,336만원 (3.23억원) | **PASS** |
| `CAT_MAJ_04` | 양식·세계음식 | `🍝 양식·세계음식` | 포함 | 32,603만원 (3.26억원) | **PASS** |
| `CAT_MAJ_05` | 치킨·패스트푸드 | `🍗 치킨·패스트푸드` | 포함 | 19,312만원 (1.93억원) | **PASS** |
| `CAT_MAJ_06` | 분식·간편식 | `🍢 분식·간편식` | 포함 | 24,717만원 (2.47억원) | **PASS** |
| `CAT_MAJ_07` | 카페·음료 | `☕ 카페·음료` | 포함 | 16,703만원 (1.67억원) | **PASS** |
| `CAT_MAJ_08` | 베이커리·디저트 | `🥐 베이커리·디저트` | 포함 | 17,499만원 (1.75억원) | **PASS** |

- 8대 대분류 전수에서 배지 명칭, 비귀속 고지문 표기, 중앙값 수치가 누락 없이 일치했습니다.

### 5.4 [시나리오 4] 전국·지역·브랜드·업종 선택 조합에서 데이터 출처와 모집단 분리
- **소상공인진흥공단 상가데이터 (점포 기반)**:
  - 총 외식 점포수: `4,507 개소`
  - 프랜차이즈 침투율: `24.43%`
  - 광진구 상위 브랜드: 5개 행 표출
- **공정위 거시 공시 데이터 (가맹본부 표본 기반)**:
  - 출처 배지: `"공정위 거시 공시"` (`.provenance-badge-ftc`)
  - 패널 표제: `"공정위 공식 가맹사업 거시통계 (전국 가맹본부 기준)"`
  - 표본 안내: `"공시 표본 403개 브랜드 (유효 매출 기준)"` (`.pill-sample`)
  - 모집단 세부: `"전국 가맹사업망 가맹 32,011개 · 직영 1,354개 / 총 635개 브랜드 (매출 0원: 204개)"`
  - 하단 고지: `"출처: 공정거래위원회 가맹사업정보제공시스템 / 집계단위: 전국 등록 가맹본부 거시 벤치마크 (개별 매장 실측치 아님)"`
- 판정: 소진공의 '개별 점포 전수'와 공정위의 '전국 가맹본부 등록 표본'이 완전히 분리되어 표현됨.

### 5.5 [시나리오 5] 데스크톱 1440×900 및 모바일 390×844에서 핵심 안내 미잘림·미숨김 보장
- **데스크톱 (1440×900)**:
  - `.hero-label`: `top: 382px, height: 16px`, 조상 클리핑 0건, `isActuallyVisible: true`
  - `.hero-scope-disclaimer`: `top: 435px, height: 36px`, 조상 클리핑 0건, `isActuallyVisible: true`
- **모바일 피크 바 (390×844)**:
  - 태그 (`.mobile-summary-tag`): `"공정위 전국"` (`isActuallyVisible: true`)
  - KPI (`.mobile-summary-kpi`): `"중위 3.61억"` (`isActuallyVisible: true`)
  - 참고치 문구 (`.mobile-summary-sub`): `"(업종 참고치)"` (`isActuallyVisible: true`)
  - 피크 바 높이: 64px, 하단 고정 유지
- **모바일 확장 바텀시트 (390×844)**:
  - 첫 화면 공지 (`.mobile-first-screen-notice`): `bottom: 437px <= 844px` (`isActuallyVisible: true`)
  - 대표 수치 (`.hero-stat-number`): `bottom: 518px <= 844px` (`isActuallyVisible: true`)
  - 판정: 모바일 첫 화면 844px 내에서 핵심 비귀속 고지와 대표 매출 수치가 잘림 없이 가시됨.

### 5.6 [시나리오 6] 모바일 가로 오버플로 0 및 키보드 접근성·패널 접기 유지
- **모바일 가로 오버플로 실측**:
  - 피크 바 상태: `docScrollWidth = 390px`, `bodyScrollWidth = 390px`, `panelRight = 390px` (초과 0px)
  - 확장 시트 상태: `docScrollWidth = 390px`, `bodyScrollWidth = 390px`, `panelRight = 390px` (초과 0px)
- **키보드 접근성 실측**:
  - 데스크톱 공정위 버튼(`.ftc-drawer-btn`) 포커스 후 `Enter` 키 입력: 드로어 오픈 확인 (`.drawer-open`)
  - `Escape` 키 입력: 드로어 닫힘 확인 (`.drawer-closed`)
  - 모바일 피크 핸들(`.mobile-bottom-sheet-handle`) 포커스 후 `Enter` 키 입력: 시트 확장 (`.mobile-expanded`)
  - 다시 `Enter` 키 입력: 시트 축소 (`.mobile-collapsed`)
- **데스크톱 패널 접기/펼치기**:
  - 접기 버튼(`#ftc-benchmark-panel .collapse-toggle-btn`) 클릭 시: `.collapsed` 클래스 추가 및 본문 축소
  - 재클릭 시: `.collapsed` 제거 및 본문 원상 복구 확인.

### 5.7 [시나리오 7] 지도, 필터, 지역 브랜드 Top 5, 공정위 연도 선택 회귀 없음 확인
- **지도 WebGL 캔버스**:
  - `maplibregl-canvas` 요소 존재 확인, 렌더링 폭 `1440px`, 높이 `785px` (`rendered: true`)
- **지역 브랜드 Top 5 카드**:
  - 광진구 치킨·패스트푸드 5개 브랜드 정상 렌더링 (`rowCount: 5`)
  - 1위 맘스터치, 2위 교촌치킨, 3위 BHC 등 정상 표출
- **공정위 연도 선택기**:
  - `#ftc-year-select` 값을 `2024`에서 `2025`로 변경 시, 패널 연도 배지가 `2025`로 즉시 갱신 (`updatedTo2025: true`).

### 5.8 [시나리오 8] 2026 진행형 스냅샷 경고가 호버 없이 유지됨
- **2026 연도 선택 상태 (`sidoValue: "00"`, `year: "2026"`)**:
  - 인라인 경고 박스 (`.snapshot-inline-alert`):
    - 문구: `"⚠️ 진행형 스냅샷: 2026년은 정기공시 진행 중(약 30% 미등록 결손)으로 2025년과 직접 비교가 불가합니다."`
    - 좌표: `left: 1024, top: 254, width: 384, height: 35`
    - 가시성: `isActuallyVisible: true`, `opacity: 1`, 조상 클리핑 0건
    - 마우스 호버 등 사용자 개입 없이 패널 최상단에 상시 노출됨을 확인.

---

## 6. 프로덕션 빌드 검증

```powershell
npm.cmd --prefix frontend run build
```
- 결과:
  ```text
  vite v5.4.21 building for production...
  transforming...
  ✓ 42 modules transformed.
  rendering chunks...
  computing gzip size...
  dist/index.html                     0.61 kB │ gzip:   0.47 kB
  dist/assets/index-BYUUe7lR.css    125.16 kB │ gzip:  19.73 kB
  dist/assets/index-D8mLa6NY.js   1,021.07 kB │ gzip: 287.99 kB
  ✓ built in 4.98s
  ```
- 오류 0건, 성공 종료.

---

## 7. 결론

Phase 5D Step 5D-3에서 요구된 **8대 필수 검증 시나리오가 모두 PASS**되었으며, 보호 대상 파일 3종 무결성 불변, 프로덕션 빌드 성공, 원시 JSON 및 스크린샷 증빙과의 100% 정합성을 확인하였습니다.
