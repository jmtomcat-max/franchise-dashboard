# Phase 5D Step 3 품질 보고서: FTC 전년비 전체 회귀 및 품질 평가 (Iteration 6)

- **평가일**: 2026-10-19
- **작업 경로**: `D:\Franchise_Dashboard`
- **회차 (Iteration)**: 6 (Codex Iteration 5 Review 조치 반영)
- **평가 대상**: `FTC 전년비 보조 비교 기능 종합 체계` ([`frontend/src/utils/ftcYoyComparison.js`](file:///d:/Franchise_Dashboard/frontend/src/utils/ftcYoyComparison.js), [`frontend/src/components/FtcBenchmarkPanel.jsx`](file:///d:/Franchise_Dashboard/frontend/src/components/FtcBenchmarkPanel.jsx), [`frontend/src/index.css`](file:///d:/Franchise_Dashboard/frontend/src/index.css))
- **품질 판정**: **최종 승인 적격 (VERDICT: PASS)**
- **검증 근거**: [`reports/phase5d_step3_yoy_validation.json`](file:///d:/Franchise_Dashboard/reports/phase5d_step3_yoy_validation.json)
- **종합 검증 스크립트**: [`scratch/verify_phase5d_step3_yoy_suite.mjs`](file:///d:/Franchise_Dashboard/scratch/verify_phase5d_step3_yoy_suite.mjs)

---

## 1. 품질 평가 요약

| 평가 차원 | 기준 사양 | 실측치 및 검증 결과 (Iteration 6) | 평가 |
| :--- | :--- | :--- | :---: |
| **연도 범위 엄밀성** | 2024→2025만 비교 계산, 2026 진행형 스냅샷 전수 배제 | S1~S8 전수에서 2024→2025만 산출, 2026년 선택 시에도 전년비 비교는 2024 대비 2025로 고정 유지 및 안내 캡션 확인 | **PASS** |
| **독립 수학 산출 정확도** | 4대 지표(중위매출, 5%절사평균, 가중평균, 가맹점수)의 원시값, 증감액, 증감률 독립 수동 계산 1:1 일치 | S4 8대 외식 업종 32개 카드 전수 '24값, '25값, 증감액, 증감률, 방향 텍스트를 독립 수학 함수와 1:1 대사하여 100% 일치 (`allMetricsMatch: true`) | **PASS** |
| **선택값 상태 일관성 (P2)** | 요청 지역·업종·연도와 실제 렌더링된 DOM 선택값 일치 및 불일치 시 FAIL 판정 | S1~S8 전 시나리오 및 S4 8개 업종 전수에서 `requestedSelection` vs `actualSelection` 100% 일치 (`selectionMatch: true`) | **PASS** |
| **거시 벤치마크 분리** | 전국 및 시군구 선택 시 공정위 통계가 전국 가맹본부 거시 데이터이며 개별 점포 실적이 아님을 고지 | 패널 상단 및 비교 블록 하단 3줄 캡션에 `공정위 전국 등록 가맹본부 거시 통계이며, 특정 브랜드 및 개별 가맹점의 실제 실적·수익률이 아닙니다.` 명시 보존 | **PASS** |
| **예외 6대 배치 방어** | 0, 음수, 결측, 비수치, 단위 충돌, 연도 누락 시 런타임 에러 0건 및 안내 배너/비교 불가 처리 | React 런타임 실제 파이프라인 6대 배치 주입 및 방어 카드 상태 정상 복원 검증 | **PASS** |
| **기존 기능 회귀 방지** | MapLibre 지도, 시도/시군구 필터, 상권 요약, 브랜드 Top 5, 연도 선택, 접기/닫기 회귀 0건 | WebGL 캔버스 유지, 강남구/제주도 브랜드 Top 5 동적 갱신 실측, 연도 선택 `aria-pressed="true"`, 접기/닫기 상태 전이 통과 | **PASS** |
| **반응형 핏 & 무잘림** | 1440×900 및 390×844 뷰포트에서 가로 오버플로 0px 및 카드 내부 텍스트/요소 잘림 0건 | 데스크톱 1440px / 모바일 390px 가로 스크롤 0px, 4개 카드 내부 텍스트 잘림 0건 (`hasAnyClipping: false`) | **PASS** |
| **모바일 사용성** | 모바일 바텀시트 전개 시 1열 배치, 최소 터치 타깃 44px 이상 준수 | 바텀시트 확장 시 1열 레이아웃 적용, 카드 실측 높이 74px (≥ 44px) 확인 | **PASS** |
| **순수 키보드 조작 & A11y (P2)** | 내부 직접 `.focus()` 점프 배제, Tab·Shift+Tab 경로 이동, 닫기/접기/펼치기/선택 순수 키보드 조작, 초점 링 실측 | `clickFallbacksUsed: false`, 순수 Tab/Shift+Tab 기반 조작 전수 통과, 11단계 Tab 이동 DOM 완전 일치(`allStepsFollowDomOrder: true`), Focus Ring computed outline/shadow 실측(`allFocusRingsVisible: true`), ARIA 트리 완비 | **PASS** |
| **시각 다중 단서 제공** | 색상에 의존하지 않고 부호와 텍스트를 병행하여 정보 전달 | 증가(`▲ + 증가`), 감소(`▼ - 감소`), 변동 없음(`- 변동 없음`), 비교 불가(`비교 불가`)로 3중 단서 제공 | **PASS** |
| **단위/회귀 테스트 연계** | Step 1 계산 단위 테스트 및 Step 2 화면 검증 재통과 | `test_phase5d_step1_calc.mjs` (ALL PASS), `verify_phase5d_step2_yoy_ui.mjs` (8/8 PASS) 재통과 | **PASS** |
| **프로덕션 빌드 무결성** | `npm run build` 오류 없이 완료 | `vite build` 3.29초 성공 (dist 생성 완료) | **PASS** |
| **보호 자산 불변성** | 보호 대상 3개 파일 SHA-256 해시 100% 불변 | `collector.py`, `gangnam_food_stores.sqlite3`, `run_gangnam.bat` 해시 일치 | **PASS** |

---

## 2. Codex Iteration 5 Review 지적 사항 조치 평가

### 2.1 [P2] S8 내부 직접 `.focus()` 점프 배제 및 순수 Tab·Shift+Tab 경로 이동
- **지적 내용**: 패널 내부 요소를 탐색하거나 조작할 때 직접 `.focus()`를 호출하여 대상을 건너뛰지 않고 순수 Tab·Shift+Tab으로 닫기, 접기, 펼치기, 2025년 선택, 지표 카드에 도달해야 함.
- **조치 결과**:
  * 외부 진입점(필터바) 이후, 패널 내부 탐색 시 순수 Tab 키 이벤트를 통해 패널에 자연스럽게 진입.
  * `drawer-close-btn`부터 11개 대상 요소까지 순수 Tab으로만 이동하며 DOM 선행 순서(`followsDomOrder: true`) 및 Focus Ring 표출(`focusRingPresent: true`)을 전수 실측.
  * 접기 버튼 도달은 순수 Shift+Tab, 펼치기 버튼 및 2025년 선택 컬럼, 지표 카드 도달은 순수 Tab 키 입력으로만 찾아가도록 구현.
  * Enter(접기), Space(펼치기), Enter(연도선택), Escape(패널닫기) 조작 시 마우스 클릭 대체 없이(`clickFallbacksUsed: false`) 순수 키보드로만 조작 완료.
- **판정**: **PASS (완전 충족)**

### 2.2 [P2] S4~S8 원시 JSON DOM 선택값(`requestedSelection`, `actualSelection`, `selectionMatch`) 기록 및 판정 연결
- **지적 내용**: S4~S8 원시 JSON에 요청값, 실제 DOM 값, 일치 여부가 기록되어야 하며, 불일치 시 해당 시나리오는 FAIL이어야 함.
- **조치 결과**:
  * `getDomSelectionState()` 헬퍼를 통해 실제 렌더링된 시도코드, 시군구코드, 활성 카테고리 탭 ID, 선택된 연도 컬럼을 측정.
  * S4의 8개 전 업종 순회 및 S4, S5, S6, S7, S8 상위 시나리오 레벨에서 `requestedSelection`, `actualSelection`, `selectionMatch`를 원시 JSON에 기록.
  * 각 시나리오의 PASS 조건에 `selectionMatch`를 필수 결합하여 불일치 시 즉시 FAIL 처리되도록 설계.
  * 실측 결과: S1~S8 전 시나리오에서 `selectionMatch: true` 확인.
- **판정**: **PASS (완전 충족)**

---

## 3. 최종 품질 종합 판정

- **완료 판정**: **적격 (PASS)**
- **결론**: Codex Review의 2대 P2 조치 사항이 브라우저 실제 환경에서 검증되었으며, 제품 코드 수정 없이 회귀 스위트 및 보고서 정합성이 100% 확보되었습니다. 최종 승인을 건의합니다.
