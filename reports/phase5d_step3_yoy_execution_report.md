# Phase 5D Step 3 실행 보고서: FTC 전년비 전체 회귀 및 품질 검증 (Iteration 6)

- **작성일**: 2026-10-19
- **작업 경로**: `D:\Franchise_Dashboard`
- **회차 (Iteration)**: 6 (Codex Iteration 5 Review 조치: 순수 Tab/Shift+Tab 기반 내부 초점 이동 실측, S4~S8 원시 JSON requested/actual DOM 선택값 및 selectionMatch 판정 결합)
- **상태**: **Step 3 전체 회귀 및 품질 종합 검증 완료 (ALL PASS 9/9)**
- **기반 태스크**: [`.agent-workflow/TASK.md`](file:///d:/Franchise_Dashboard/.agent-workflow/TASK.md)
- **검토 결과 기준**: [`.agent-workflow/REVIEW.md`](file:///d:/Franchise_Dashboard/.agent-workflow/REVIEW.md)
- **원시 검증 데이터**: [`reports/phase5d_step3_yoy_validation.json`](file:///d:/Franchise_Dashboard/reports/phase5d_step3_yoy_validation.json)
- **종합 검증 스크립트**: [`scratch/verify_phase5d_step3_yoy_suite.mjs`](file:///d:/Franchise_Dashboard/scratch/verify_phase5d_step3_yoy_suite.mjs)
- **연계 검증 스크립트**: [`scratch/test_phase5d_step1_calc.mjs`](file:///d:/Franchise_Dashboard/scratch/test_phase5d_step1_calc.mjs), [`scratch/verify_phase5d_step2_yoy_ui.mjs`](file:///d:/Franchise_Dashboard/scratch/verify_phase5d_step2_yoy_ui.mjs)

---

## 1. 개요 및 Codex Iteration 5 Review 지적 사항 조치 내역

Iteration 5 검토에서 제시된 두 P2 조치 사항([`.agent-workflow/TASK.md`](file:///d:/Franchise_Dashboard/.agent-workflow/TASK.md))을 충족하고 실제 브라우저 환경에서 재검증을 완료하였습니다.

### 조치 내역 상세:
1. **[P2 조치 1] S8 순수 Tab/Shift+Tab 이동 및 내부 직접 `.focus()` 점프 완전 배제**:
   - 패널 외부 최초 진입점 설정(필터바) 이후, 패널 내부의 대상(닫기 버튼, 접기 버튼, 펼치기 미니 버튼, 2025년 선택 컬럼, 지표 카드)으로의 이동 시 일체의 임의 `.focus()` 호출 없이 **순수 Tab 및 Shift+Tab 키보드 이벤트 디스패치만으로 이동**하도록 구현.
   - 11단계 전체 DOM 탐색 순서 일치(`allStepsFollowDomOrder: true`), 모든 요소 Focus Ring 노출(`allFocusRingsVisible: true`), 순수 Enter/Space/Escape 키 조작(`clickFallbacksUsed: false`) 실측 완료.
2. **[P2 조치 2] S4~S8 원시 JSON `requestedSelection`, `actualSelection`, `selectionMatch` 기록 및 판정 연결**:
   - S4, S5, S6, S7, S8 (및 S1~S3) 각 시나리오의 요청 시도/시군구/업종/연도 상태와 실제 렌더링된 DOM의 셀렉트박스 값, 활성 탭 ID, 선택된 연도 컬럼 값을 추출하여 대조.
   - 지역·업종·연도의 실제 DOM 값이 요청값과 불일치할 경우 해당 시나리오가 즉시 **FAIL** 되도록 불리언 조건 연결.
   - S4의 8개 전 업종 순회(`categoriesTested`) 및 S4~S8 상위 시나리오 레벨에서 전수 `selectionMatch: true` 확인.

---

## 2. 9대 시나리오 전수 검증 결과 (ALL PASS 9/9)

| 시나리오 ID | 시나리오 명칭 | 핵심 검증 조건 및 실측 결과 | 선택값 일치 (selectionMatch) | 결과 | 증빙 캡처 |
| :--- | :--- | :--- | :---: | :---: | :--- |
| **S1** | 전국 요약 및 거시 통계 의미 안전성 | 전국 + 한식(`CAT_MAJ_01`) + 2025년 기준<br>- 4개 카드 지표(중위 34,720만원, 절사 38,282만원, 가중 39,945만원, 점포 43,566개) 일치<br>- 3줄 캡션 및 완결후보 뱃지 보존, 2026 스냅샷 배제 확인<br>- 카드 내부 텍스트 잘림 0건 (`ClippingFree: true`) | `true`<br>(00 / / CAT_MAJ_01 / 2025) | **PASS** | [`reports/phase5d_step3_yoy_s1_desktop_national_korean.png`](file:///d:/Franchise_Dashboard/reports/phase5d_step3_yoy_s1_desktop_national_korean.png) |
| **S2** | 지역 선택 + 카페 실제 감소치 실측 | 서울 강남구(`11680`) + 카페(`CAT_MAJ_07`) + 2025년<br>- 중위매출: -351만원 (-2.2%) 감소 실측<br>- 가맹점수: -1,703개 (-5.3%) 감소 실측<br>- 부호 `▼ -` 및 텍스트 `감소` 병행 표기<br>- 지역 점포와 공정위 전국 거시 통계 분리 확인 | `true`<br>(11 / 11680 / CAT_MAJ_07 / 2025) | **PASS** | [`reports/phase5d_step3_yoy_s2_desktop_regional_gangnam_cafe.png`](file:///d:/Franchise_Dashboard/reports/phase5d_step3_yoy_s2_desktop_regional_gangnam_cafe.png) |
| **S3** | 원격 도서 지역 + 치킨 벤치마크 분리 | 제주특별자치도(`50`) + 치킨(`CAT_MAJ_05`) + 2025년<br>- 지역 점포수와 전국 가맹본부 거시 통계 분리 안내문 확인<br>- 중위 20,171만원 (+515만원, +2.6%), 가맹점 41,139개 (-2,165개, -5.0%)<br>- 카드 내부 텍스트 잘림 0건 | `true`<br>(50 / / CAT_MAJ_05 / 2025) | **PASS** | [`reports/phase5d_step3_yoy_s3_desktop_regional_jeju_chicken.png`](file:///d:/Franchise_Dashboard/reports/phase5d_step3_yoy_s3_desktop_regional_jeju_chicken.png) |
| **S4** | 8대 외식 업종 전수 수치 1:1 대사 | 8대 업종 순차 전환(`CAT_MAJ_01` ~ `CAT_MAJ_08`)<br>- 백엔드 `/api/v1/ftc/trends` 원시 API 응답 기반 독립 수학 함수 대사<br>- 8개 업종 전수 4개 지표(총 32개 카드) '24값, '25값, 증감액, 증감률, 방향 텍스트 1:1 일치<br>- 8개 업종 전수 개별 DOM 선택값 일치 검증 통과 | `true`<br>(00 / / CAT_MAJ_08 / 2025 & 전수 일치) | **PASS** | [`reports/phase5d_step3_yoy_s4_all_8_categories_context.png`](file:///d:/Franchise_Dashboard/reports/phase5d_step3_yoy_s4_all_8_categories_context.png) |
| **S5** | 엣지 케이스 및 연도 결손 방어 | React 실제 런타임 6개 배치 주입 검증<br>- Batch 1A(기준값 0, 키 결측, 비수치), Batch 1B(단위 충돌 actual 정상 기록), Batch 2(음수 기준값), Batch 3(null 결측), Batch 4(정상 3종 방향), Batch 5(2025 누락 배너), Batch 6(빈 시계열 배너)<br>- 방어 카드 상태 복원 후 스크린샷 및 DOM 상태 일치 확인 | `true`<br>(00 / / CAT_MAJ_02 / 2025) | **PASS** | [`reports/phase5d_step3_yoy_s5_edge_cases_and_missing_years.png`](file:///d:/Franchise_Dashboard/reports/phase5d_step3_yoy_s5_edge_cases_and_missing_years.png) |
| **S6** | 대시보드 기존 핵심 기능 회귀 검증 | - MapLibre WebGL 캔버스 정상 렌더링<br>- 강남구 상권 요약 패널 브랜드 Top 5 추출<br>- 제주도로 지역 변경 시 브랜드 Top 5 동적 갱신 실측<br>- 연도 차트 2024/2025 선택 시 `aria-pressed="true"` 전이<br>- 패널 접기/펼치기/닫기/열기 상태 전이 실측 | `true`<br>(00 / / CAT_MAJ_01 / 2025) | **PASS** | [`reports/phase5d_step3_yoy_s6_map_filters_top5_regression.png`](file:///d:/Franchise_Dashboard/reports/phase5d_step3_yoy_s6_map_filters_top5_regression.png) |
| **S7** | 데스크톱·모바일 뷰포트 레이아웃 핏 | - 데스크톱 (1440×900): 가로 오버플로 0px, 2열 카드 그리드, 카드 내부 잘림 0건<br>- 모바일 (390×844) Peek: 가로 오버플로 0px<br>- 모바일 (390×844) Expanded: 가로 오버플로 0px, 1열 레이아웃, 터치 타깃 74px (≥ 44px) | `true`<br>(00 / / CAT_MAJ_01 / 2025) | **PASS** | [`reports/phase5d_step3_yoy_s7_desktop_and_mobile_no_overflow.png`](file:///d:/Franchise_Dashboard/reports/phase5d_step3_yoy_s7_desktop_and_mobile_no_overflow.png) |
| **S8** | 키보드 탐색 및 접근성 (A11y) 실측 | - 키보드만으로 패널 열기 성공 (`keyboardOpenSuccess: true`)<br>- 외부 진입점 이후 내부 순수 Tab 11단계 초점 순서 DOM 완전 일치 (`allStepsFollowDomOrder: true`)<br>- 직접 `.focus()` 점프 배제 및 순수 Tab/Shift+Tab 기반 조작<br>- 전 요소 Focus Ring computed style 검증 (`allFocusRingsVisible: true`)<br>- Enter(접기)/Space(펼치기)/Enter(연도선택)/Escape(닫기) 완벽 동작<br>- `clickFallbacksUsed: false`, ARIA 트리 및 부호+색상+텍스트 3중 정보 전달 확인 | `true`<br>(00 / / CAT_MAJ_01 / 2025) | **PASS** | [`reports/phase5d_step3_yoy_s8_keyboard_navigation_and_a11y.png`](file:///d:/Franchise_Dashboard/reports/phase5d_step3_yoy_s8_keyboard_navigation_and_a11y.png) |
| **S9** | 보호 대상 핵심 파일 무결성 검증 | `collector.py`, `gangnam_food_stores.sqlite3`, `run_gangnam.bat`<br>- 사전(Pre) 및 사후(Post) SHA-256 해시 100% 일치<br>- 파일 크기 및 수정 시각 불변 확인 | N/A (무결성 검증) | **PASS** | (원시 JSON 기록) |

---

## 3. 세부 실측 데이터 요약

### 3.1 DOM 선택 상태 일치 실측 (`requestedSelection` vs `actualSelection`)
- **S1**: 요청 `{sidoCode: '00', sigunguCode: '', categoryId: 'CAT_MAJ_01', year: '2025'}` == 실제 DOM 일치 (`selectionMatch: true`).
- **S2**: 요청 `{sidoCode: '11', sigunguCode: '11680', categoryId: 'CAT_MAJ_07', year: '2025'}` == 실제 DOM 일치 (`selectionMatch: true`).
- **S3**: 요청 `{sidoCode: '50', sigunguCode: '', categoryId: 'CAT_MAJ_05', year: '2025'}` == 실제 DOM 일치 (`selectionMatch: true`).
- **S4**: 8개 업종 전수 (`CAT_MAJ_01` ~ `CAT_MAJ_08`) 개별 탭 및 상위 요약 전수 일치 (`selectionMatch: true`).
- **S5**: 요청 `{sidoCode: '00', sigunguCode: '', categoryId: 'CAT_MAJ_02', year: '2025'}` == 실제 DOM 일치 (`selectionMatch: true`).
- **S6**: 요청 `{sidoCode: '00', sigunguCode: '', categoryId: 'CAT_MAJ_01', year: '2025'}` == 실제 DOM 일치 (`selectionMatch: true`).
- **S7**: 요청 `{sidoCode: '00', sigunguCode: '', categoryId: 'CAT_MAJ_01', year: '2025'}` == 실제 DOM 일치 (`selectionMatch: true`).
- **S8**: 요청 `{sidoCode: '00', sigunguCode: '', categoryId: 'CAT_MAJ_01', year: '2025'}` == 실제 DOM 일치 (`selectionMatch: true`).

### 3.2 S8 순수 키보드 조작 및 접근성 실측 결과
- **키보드 조작 결과 (`keyboardOnlyOperations`)**:
  * `openViaKeyboard`: true (필터바 -> Tab -> `.ftc-drawer-btn` -> Enter)
  * `reachedDrawerButtonViaTab`: true
  * `reachedCollapseViaShiftTab`: true (순수 Shift+Tab 탐색 도달)
  * `reachedMiniOpenViaTab`: true (순수 Tab 탐색 도달)
  * `reachedYear2025ViaTab`: true (순수 Tab 탐색 도달)
  * `collapseViaKeyboard`: true (Enter)
  * `expandViaKeyboard`: true (Space)
  * `selectYearViaKeyboard`: true (Enter)
  * `closeViaKeyboard`: true (Escape 키 입력)
  * `clickFallbacksUsed`: **false** (대체 클릭 0건)
- **DOM 초점 순환 및 Focus Ring 실측 (`automatedDomFocusOrderAudit`)**:
  * 11단계 전 요소 `DOCUMENT_POSITION_FOLLOWING` (4) 완전 일치 (`allStepsFollowDomOrder: true`).
  * 11단계 전 요소 computed outline/box-shadow 실측 통과 (`allFocusRingsVisible: true`).
  * 순회 대상: `drawer-close-btn` -> `collapse-toggle-btn` -> `chart-bar-column` (2023, 2024, 2025, 2026) -> `yoy-metric-card` (4종) -> `cost-detail-toggle`.
- **접근성 트리 실측 (`automatedAccessibilityAudit`)**:
  * `panelAriaLabel`: "공정위 거시 벤치마크 패널"
  * `blockAriaLabel`: "2024년 대비 2025년 거시 전년비 보조 비교"
  * `allMetricCardsHaveDetailedAria`: true (4개 카드 모두 2024년 값, 2025년 값, 증감액, 증감률 상세 안내 포함)
  * `yearButtonsHaveRoleAndAria`: true (`role="button"`, `aria-label`, `aria-pressed`)
  * `hasSignAndText`: true (▲ + 증가, ▼ - 감소, - 변동 없음, 비교 불가)
  * `decorativeArrowsHidden`: true (`aria-hidden="true"`)

---

## 4. 연계 검증 및 프로덕션 빌드 결과

1. **Step 1 순수 계산 단위 검증 (`scratch/test_phase5d_step1_calc.mjs`)**:
   - `ALL PASS` (Exit Code 0, T-01 ~ T-09-F 전수 통과)
2. **Step 2 화면 UI 검증 (`scratch/verify_phase5d_step2_yoy_ui.mjs`)**:
   - `ALL PASS 8/8` (Exit Code 0)
3. **Step 3 종합 회귀 스위트 (`scratch/verify_phase5d_step3_yoy_suite.mjs`)**:
   - `ALL PASS 9/9` (Exit Code 0)
4. **프론트엔드 프로덕션 빌드 (`npm.cmd --prefix frontend run build`)**:
   - `Exit Code 0` (`vite v5.4.21 built in 3.29s`, dist 생성 완료)
5. **보호 대상 파일 3종 무결성**:
   - `collector.py`: `341BAC12BB0AF58DCBDEBBA9459033521F27DF9817E35BAD8B21A4D07BA3369C`
   - `gangnam_food_stores.sqlite3`: `FEE3B58651CFED5C390C0B95DB02B05EBE92DF18619A06F4E399D429236F3A78`
   - `run_gangnam.bat`: `0582C3A1AE53450DDC482E9BF538510780CA2F14D44E987CC753D4E12C816491`
   - 100% 해시 일치.

---

## 5. 결론

TASK.md에 명시된 두 가지 P2 조치(S8 순수 Tab/Shift+Tab 기반 초점 도달 및 focus 점프 배제, S4~S8 실제 DOM 선택값과 요청값 대조 및 일치 판정 연결)가 완벽히 실측 검증되었으며, 제품 코드 및 보호 대상 파일 변경 없이 검증 스위트 및 보고서의 정합성이 100% 확보되었습니다.
