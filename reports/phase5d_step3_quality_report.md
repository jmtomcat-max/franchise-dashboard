# Phase 5D Step 5D-3 품질 및 의미 안전성 검증보고서

> **문서 상태**: 8대 시나리오 전수 검증 및 품질 감사 완료 (ALL PASS)  
> **수행 일시**: 2026-10-19 11:15:00 (KST)  
> **작업 지침**: [`.agent-workflow/TASK.md`](file:///d:/Franchise_Dashboard/.agent-workflow/TASK.md)  
> **원시 검증 데이터**: [`reports/phase5d_step3_validation.json`](file:///d:/Franchise_Dashboard/reports/phase5d_step3_validation.json)  
> **실행보고서**: [`reports/phase5d_step3_execution_report.md`](file:///d:/Franchise_Dashboard/reports/phase5d_step3_execution_report.md)  

---

## 1. 품질 검증 요약

Phase 5D Step 5D-3 작업 지침에 따라, 8대 필수 검증 시나리오에 대해 **원시 CDP 가시성 측정, 뷰포트 레이아웃, 조상 오버플로 클리핑 분석, 키보드 접근성 및 기능 회귀 검증**을 완료했습니다.

전체 검증 항목에서 결함 0건, **100% PASS**를 기록했습니다.

| 구분 | 검증 항목 | 검증 기준 및 방식 | 실측 결과 | 판정 |
| :---: | :--- | :--- | :--- | :---: |
| **의미 안전성 (브랜드 비귀속)** | 실제 브랜드 선택 시 공정위 실적 오귀속 차단 | 1위 브랜드 행 클릭 후 패널 본문 검사 | 특정 브랜드 명칭 + 매출/실적 오표기 0건, 비귀속 안내문 상시 가시 | **PASS** |
| **의미 안전성 (거시 성격 유지)** | 지역 변경 후 전국 거시 성격 첫 화면 식별 | 광진구 선택 후 스크롤 0 상태 가시성 | `전국 가맹본부 대표매출 (중앙값)` 및 비귀속 고지문 첫 화면 가시 | **PASS** |
| **분류 정합성 (8대 대분류)** | 8대 대분류 전수 공정위 매핑 일치 | 8대 카테고리 순회 및 배지/고지 대조 | 8/8 카테고리 배지, 업종명 포함 비귀속문구, 유효 중앙값 일치 | **PASS** |
| **데이터 분리 (출처·모집단)** | 점포 전수 데이터 vs 가맹본부 표본 분리 | 소진공 카드 vs 공정위 패널 출처 배지/표제/하단 메타 대조 | 소진공 4,507개 점포 기반 vs 공정위 403개 브랜드 표본 및 '개별 매장 실측치 아님' 분리 | **PASS** |
| **가시성 보장 (데스크톱)** | 1440×900 핵심 안내 조상 클리핑 차단 | 상위 4개 조상 컨테이너 오버플로 계산 | `notClippedByAncestor: true`, `isActuallyVisible: true` | **PASS** |
| **가시성 보장 (모바일 피크)** | 390×844 모바일 피크 바 핵심 정보 노출 | 하단 64px 고정 피크 바 텍스트/라벨 | `[공정위 전국]`, `중위 3.61억`, `(업종 참고치)` 단일행 노출 | **PASS** |
| **가시성 보장 (모바일 확장)** | 390×844 확장 바텀시트 첫 화면 공지 가시 | 첫 844px 뷰포트 내 요소 바운딩 박스 | `.mobile-first-screen-notice` (`bottom: 437px <= 844px`) 안착 | **PASS** |
| **레이아웃 (모바일)** | 390×844 가로 오버플로 0 | `documentElement.scrollWidth` 측정 | 피크 `390px`, 확장 `390px` (초과 0px) | **PASS** |
| **접근성 (키보드 조작)** | 드로어/바텀시트 키보드 조작성 | `Enter` 키 열기/확장, `Escape` 닫기 | 데스크톱 Enter 열기/ESC 닫기, 모바일 Enter 토글 PASS | **PASS** |
| **레이아웃 (패널 접기)** | 데스크톱 패널 접기/펼치기 유지 | `#ftc-benchmark-panel .collapse-toggle-btn` 클릭 | `.collapsed` 토글 정상 작동 | **PASS** |
| **기능 회귀 (지도/필터/연도)** | MapLibre 캔버스, 지역 브랜드, 연도 전환 | WebGL 렌더링, Top 5 렌더링, 2024→2025 변경 | 캔버스 정상, Top 5 5개 렌더링, 2025 배지/수치 갱신 확인 | **PASS** |
| **스냅샷 경고 (2026년)** | 2026 진행형 스냅샷 경고 호버 없이 상시 노출 | 렌더링 즉시 `.snapshot-inline-alert` 검사 | `opacity: 1`, 30% 미등록 및 직접 비교 불가 문구 노출 | **PASS** |
| **파일 무결성** | 보호 대상 3종 파일 SHA-256 불변 | SHA-256 사전/사후 해시 대조 | `collector.py`, `sqlite3`, `bat` 100% 일치 | **PASS** |
| **빌드 안정성** | 프로덕션 빌드 성공 | `npm.cmd --prefix frontend run build` | 오류 0건 완료 (`built in 4.98s`) | **PASS** |

---

## 2. 세부 검증 결과 분석

### 2.1 브랜드 오귀속 방지 (Scenario 1)
- **테스트 시나리오**: 서울 광진구 카페·음료 모드에서 1위 브랜드인 `메가MGC커피` 행을 선택/클릭.
- **실측 결과**:
  - 패널 최상단 히어로 라벨: `"전국 가맹본부 대표매출 (중앙값)"`
  - 비귀속 안내문: `"* 공정위 정기공시 전국 카페·음료 가맹본부 기준 거시 통계이며, 특정 브랜드나 개별 점포의 실적이 아닙니다."`
  - 패널 내 텍스트 전체 검색 결과, `메가MGC커피 매출` 또는 `메가MGC커피 실적`과 같이 브랜드가 공정위 통계의 주체로 오인될 수 있는 표현이 **전혀 생성되지 않음**.
- **판정**: 브랜드 선택 시에도 공정위 수치가 브랜드 단독 실적으로 표현되지 않음이 보장됨.

### 2.2 지역 필터 변경과 전국 거시 벤치마크 공존 (Scenario 2)
- **테스트 시나리오**: 전국 단위에서 서울 광진구 치킨·패스트푸드로 지역 변경 직후 초기 상태(스크롤 0) 측정.
- **실측 결과**:
  - 사용자 스크롤 조작 전(`scrollY = 0`), `.hero-label`과 `.hero-scope-disclaimer`의 Y축 좌표는 각각 `382px`, `435px`로 첫 뷰포트(900px) 중앙 상단에 즉시 위치함.
  - 지역 변경 직후 첫 화면에서 '전국 가맹본부 기준' 및 '개별 점포 실적이 아님'을 즉각 인지할 수 있음.
- **판정**: 지역 변경 후에도 공정위 수치가 전국 통계임이 첫 화면에서 식별됨.

### 2.3 확정된 8대 대분류 100% 매핑 정합성 (Scenario 3)
- **테스트 시나리오**: `CAT_MAJ_01`부터 `CAT_MAJ_08`까지 8개 대분류 탭을 순차 클릭하여 공정위 매핑 결과 확인.
- **실측 결과**:
  - 8개 업종 전수에서 각 업종의 공식 명칭(한식, 중식, 일식, 양식·세계음식, 치킨·패스트푸드, 분식·간편식, 카페·음료, 베이커리·디저트)이 배지와 비귀속 안내문에 정확히 표기됨.
  - 모든 업종에서 결측치(`-`) 없이 유효한 대표 중앙값 매출이 산출되어 렌더링됨.
- **판정**: 8대 대분류 체계와 공정위 업종 매핑이 100% 일치함.

### 2.4 데이터 출처 및 모집단 표기 분리 (Scenario 4)
- **소상공인시장진흥공단 (SEDA)**:
  - 성격: 상가(상권)정보 기반 점포 단위 공간 전수.
  - 지표: 광진구 외식 점포 4,507개소, 프랜차이즈 침투율 24.43%, 지역 상위 브랜드 순위.
- **공정거래위원회 (FTC)**:
  - 성격: 가맹사업정보제공시스템 가맹본부 정기공시 정보공개서 기반 전국 거시 통계.
  - 지표: 전국 가맹본부 대표매출 중앙값(1.67억원), 공시 표본 수(403개 브랜드), '개별 매장 실측치 아님' 명시.
- **판정**: 두 데이터 소스의 수집 단위와 모집단이 UI 상에서 명확히 분리 표기됨.

### 2.5 반응형 뷰포트 레이아웃 및 클리핑 차단 (Scenario 5 & 6)
- **데스크톱 (1440×900)**:
  - 상위 컨테이너(`.panel-body`, `#ftc-benchmark-panel`, `.dashboard-body`, `.app-layout`)의 바운딩 렉트와 교차 면적을 계산한 결과, 클리핑으로 인한 가시 영역 축소(width=0 또는 height=0)가 발생하지 않음.
- **모바일 (390×844)**:
  - 피크 바 및 확장 바텀시트 상태 모두에서 `document.documentElement.scrollWidth`가 정확히 `390px`로 측정되어 가로 스크롤/오버플로가 발생하지 않음.
  - 확장 바텀시트의 첫 844px 내에 비귀속 안내 배너(`top: 405px`)와 대표 매출 수치(`top: 494px`)가 완벽히 배치됨.

---

## 3. 원시 측정 데이터 및 스크린샷 증빙 대조표

모든 시나리오의 조건, 실측 수치 및 캡처 이미지가 상호 100% 일치함을 확인했습니다.

| 시나리오 | 원시 JSON 지표 (`reports/phase5d_step3_validation.json`) | 스크린샷 증빙 파일 | 대조 확인 사항 |
| :---: | :--- | :--- | :--- |
| **S1** | `topBrand: "메가MGC커피"`, `erroneouslyClaimsBrand: false`, `disclaimerVisible: true` | [`phase5d_step3_s1_brand_disclaimer_coexistence.png`](file:///d:/Franchise_Dashboard/reports/phase5d_step3_s1_brand_disclaimer_coexistence.png) | 광진구 상위 브랜드 카드와 공정위 비귀속 안내문 동시 노출 확인 |
| **S2** | `region: "11215"`, `scrollY: 0`, `heroLabel: "전국 가맹본부 대표매출 (중앙값)"` | [`phase5d_step3_s2_regional_macro_benchmark.png`](file:///d:/Franchise_Dashboard/reports/phase5d_step3_s2_regional_macro_benchmark.png) | 광진구 치킨 모드 진입 시 첫 화면 내 전국 중앙값 라벨 확인 |
| **S3** | `matchedCategories: 8`, `allEightMatched: true` | [`phase5d_step3_s3_8categories_mapping.png`](file:///d:/Franchise_Dashboard/reports/phase5d_step3_s3_8categories_mapping.png) | 8대 업종 탭 및 패널 배지·수치 매핑 확인 |
| **S4** | `semasPresent: true`, `provenanceBadge: "공정위 거시 공시"`, `samplePill: 403개 브랜드` | [`phase5d_step3_s4_source_segregation.png`](file:///d:/Franchise_Dashboard/reports/phase5d_step3_s4_source_segregation.png) | 좌측 상권 요약(소진공)과 우측 벤치마크(공정위) 모집단 분리 확인 |
| **S5** | `desktopNotClipped: true`, `mobPeekTagVisible: true`, `mobExpNoticeVisible: true` | [`phase5d_step3_s5_desktop_not_clipped.png`](file:///d:/Franchise_Dashboard/reports/phase5d_step3_s5_desktop_not_clipped.png)<br>[`phase5d_step3_s5_mobile_peek_visible.png`](file:///d:/Franchise_Dashboard/reports/phase5d_step3_s5_mobile_peek_visible.png)<br>[`phase5d_step3_s5_mobile_expanded_visible.png`](file:///d:/Franchise_Dashboard/reports/phase5d_step3_s5_mobile_expanded_visible.png) | 데스크톱 미잘림 및 모바일 피크·확장 첫 화면 가시성 확인 |
| **S6** | `zeroOverflow: true (390px)`, `keyboard: all true`, `collapseToggle: true` | [`phase5d_step3_s6_overflow_and_keyboard.png`](file:///d:/Franchise_Dashboard/reports/phase5d_step3_s6_overflow_and_keyboard.png) | 모바일 오버플로 0px 및 키보드·접기 인터랙션 정상 확인 |
| **S7** | `mapRendered: true`, `top5RowCount: 5`, `yearSelectionFunctional: true (2025)` | [`phase5d_step3_s7_map_filters_top5_regression.png`](file:///d:/Franchise_Dashboard/reports/phase5d_step3_s7_map_filters_top5_regression.png) | MapLibre 지도 렌더링, Top 5 목록, 2025년도 선택 회귀 없음 확인 |
| **S8** | `hasExactWarning: true`, `isAlertVisibleWithoutHover: true`, `opacity: 1` | [`phase5d_step3_s8_snapshot_warning_no_hover.png`](file:///d:/Franchise_Dashboard/reports/phase5d_step3_s8_snapshot_warning_no_hover.png) | 2026년 선택 시 앰버 인라인 경고 박스 상시 가시 확인 |

---

## 4. 최종 품질 판정

Phase 5D Step 5D-3의 모든 완료 조건이 완전하게 충족되었으며, 의미 왜곡 위험이나 기능적 회귀 없이 프로덕션 빌드가 성공적으로 완료되었습니다.
