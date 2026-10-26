# Phase 5D Step 2 실행 보고서: FTC 전년비 보조 비교 UI 구현 및 검증 (R4)

- **작성일**: 2026-10-19
- **작업 경로**: `D:\Franchise_Dashboard`
- **회차 (Iteration)**: 4 (Codex Iteration 3 Review 조치 반영: 뷰포트 스크롤 및 카드 내부 잘림 전수 실측)
- **상태**: **Step 2 구현 및 8개 시나리오 전수 검증 완료 (ALL PASS 8/8)**
- **기반 태스크**: [`.agent-workflow/TASK.md`](file:///d:/Franchise_Dashboard/.agent-workflow/TASK.md)
- **검토 결과 기준**: [`.agent-workflow/REVIEW.md`](file:///d:/Franchise_Dashboard/.agent-workflow/REVIEW.md)
- **원시 검증 결과**: [`reports/phase5d_step2_yoy_validation.json`](file:///d:/Franchise_Dashboard/reports/phase5d_step2_yoy_validation.json)
- **검증 스크립트**: [`scratch/verify_phase5d_step2_yoy_ui.mjs`](file:///d:/Franchise_Dashboard/scratch/verify_phase5d_step2_yoy_ui.mjs)

---

## 1. 작업 개요 및 Iteration 4 개선 사항

본 작업은 `TASK.md`의 완료 조건에 따라, Step 1에서 승인된 순수 계산 모듈([`frontend/src/utils/ftcYoyComparison.js`](file:///d:/Franchise_Dashboard/frontend/src/utils/ftcYoyComparison.js))을 재사용하여 공정위 거시 벤치마크 패널([`frontend/src/components/FtcBenchmarkPanel.jsx`](file:///d:/Franchise_Dashboard/frontend/src/components/FtcBenchmarkPanel.jsx))의 다년도 추세 차트 바로 아래에 2024년 대비 2025년(완결 후보) 전년비 보조 비교 UI 블록을 구현하고 반응형·접근성·의미 안전성을 실측 검증하는 것입니다.

### Iteration 3 Review 지적 사항 조치 내역 (R4):
1. **[P2 조치] 비교 블록 뷰포트 중앙 스크롤 및 화면 캡처 정밀화**:
   - `scrollBlockIntoViewAndCheckClipping` 함수를 구현하여 모든 증빙 캡처 직전 비교 블록(`.ftc-yoy-comparison-block`)을 뷰포트 중앙(`block: 'center'`)으로 스크롤한 뒤 캡처하도록 개선.
   - S1/S2 데스크톱 증빙에서 카드 하단 잘림이 발생하던 문제를 해결하고, S6 모바일 증빙에서 바텀시트 확장 및 비교 블록 중앙 배치 후 캡처하여 전체 4개 카드가 선명히 표출됨을 확인.
2. **[P2 조치] 카드 내부 텍스트/요소 잘림(Clipping) 자동 실측 검증**:
   - 각 카드의 `scrollHeight > clientHeight + 1` 또는 `scrollWidth > clientWidth + 1` 여부를 검사하고, 라벨·2024값·2025값·증감액·증감률·방향성 뱃지 각 텍스트 요소의 `scrollWidth > clientWidth + 1`을 검사하여 텍스트 잘림이 0건임을 단언(`ClippingFree: true`).
   - S1, S2(2-A/2-B), S6 전수에서 `isBlockInView: true`, `hasAnyClipping: false` 확인 및 원시 JSON에 기록.

---

## 2. 변경 파일 및 구현 상세

### 2.1 [`frontend/src/components/FtcBenchmarkPanel.jsx`](file:///d:/Franchise_Dashboard/frontend/src/components/FtcBenchmarkPanel.jsx)
1. **계산 재사용 및 파생 메모이제이션 (`useMemo`)**:
   - `calculateFtcYoyComparison`을 import하고 컴포넌트 최상단에서 `yearlySeries` 변경 시에만 파생 계산을 수행하도록 구성.
   ```javascript
   const yearlySeries = trendsData?.data?.yearly_series;
   const yoyComparison = useMemo(() => {
     return calculateFtcYoyComparison(yearlySeries);
   }, [yearlySeries]);
   ```
2. **보조 비교 블록 위치 및 정보구조**:
   - 다년도 추세 섹션(`.visual-trends-section`) 바로 아래, 창업비용 구성 섹션(`.visual-cost-section`) 바로 위에 단일 섹션(`.ftc-yoy-comparison-block`)으로 삽입.
   - 신규 탭이나 분리된 패널을 생성하지 않고 기존 패널 본문 문서 흐름을 유지.
3. **키보드 접근성 및 제어 이벤트 완비**:
   - `.collapse-toggle-btn` 및 `.mini-open-btn`에 Enter 및 Space 키 지원 `onKeyDown` 핸들러 추가.
   - 막대 차트 연도 선택 칼럼(`.chart-bar-column`)의 `onKeyDown` Enter 선택 및 `aria-pressed` 상태 연동.
4. **4대 지표 카드 및 상태 뱃지**:
   - 4대 지표(`중위매출`, `5% 절사평균`, `점포 가중평균 매출`, `가맹점 수`)를 2열(모바일 1열) 그리드로 배치.
   - 각 카드에 2024년 값, 2025년 값, 증감액, 증감률, 방향성 텍스트(`증가/감소/변동 없음/비교 불가`) 및 부호(`▲ +`, `▼ -`, `-`)를 병행 표기.
5. **표본 수 및 의미 안전성 문구 보존**:
   - 2024년 및 2025년 등록 가맹본부 표본 수 표기 (`표본: 2024년 2,340개사 → 2025년 2,532개사`).
   - 상태 라벨: `2025 최신 완결 후보 · 공식 마감 여부 미확인`.
   - 하단 캡션 3줄 보존:
     * `* 2025년은 최신 완결 후보이며 공정위 공식 행정 마감 여부는 미확인 상태입니다.`
     * `* 2026년 진행형 스냅샷은 본 전년비 비교에서 전수 제외되었으며 전년과 직접 비교가 불가합니다.`
     * `* 공정위 전국 등록 가맹본부 거시 통계이며, 특정 브랜드 및 개별 가맹점의 실제 실적·수익률이 아닙니다.`
6. **비교 불가 및 데이터 누락 안전 분기**:
   - 2024 또는 2025 데이터 누락 시 오류 없이 `.yoy-notice-banner`를 통해 비교 불가 안내 배너 표출.
   - 개별 지표의 단위 충돌, 비수치, 기준값 0 이하 발생 시 해당 지표만 `비교 불가 (사유)`로 표시하고 타 지표 정상 렌더링 유지.

### 2.2 [`frontend/src/index.css`](file:///d:/Franchise_Dashboard/frontend/src/index.css)
1. **데스크톱 기본 스타일 (Lines 2950~3177)**:
   - 다크 테마/밝은 아이보리 하모니 유지: `border-radius: 10px`, 카드 `border-radius: 6px`, `gap: 0.4rem`.
   - 2열 그리드: `grid-template-columns: repeat(2, minmax(0, 1fr))`.
   - 방향성 색상 토큰:
     * `.dir-up`: 적색 계열 (`#b91c1c`, `#fef2f2`, `#fecaca`) + 부호 `▲ +`
     * `.dir-down`: 청색 계열 (`#1d4ed8`, `#eff6ff`, `#bfdbfe`) + 부호 `▼ -`
     * `.dir-same`: 중립 회색 계열 (`var(--text-muted)`, `#f1f5f9`) + 부호 `-`
     * `.dir-blocked`: 호박색 계열 (`#b45309`, `#fffbeb`, `#fde68a`)
2. **모바일 반응형 대응 (Lines 2106~2135, `@media (max-width: 900px)`)**:
   - `grid-template-columns: 1fr !important` (1열 세로 스택 전환).
   - 카드 최소 높이 `min-height: 48px !important` (44px 이상 터치 타겟 보장).
   - `box-sizing: border-box !important`, `width: 100% !important`, `max-width: 100% !important`로 390px 뷰포트에서 0px 가로 오버플로 달성.

---

## 3. 자동화 검증 시나리오 및 실행 결과 (R4)

검증 실행 스크립트: [`scratch/verify_phase5d_step2_yoy_ui.mjs`](file:///d:/Franchise_Dashboard/scratch/verify_phase5d_step2_yoy_ui.mjs)  
원시 결과 파일: [`reports/phase5d_step2_yoy_validation.json`](file:///d:/Franchise_Dashboard/reports/phase5d_step2_yoy_validation.json)  
실행 결과: **종료 코드 0 (Exit Code 0), 8개 시나리오 ALL PASS (8/8)**

| 시나리오 ID | 시나리오 명칭 | 실측 항목 및 조건 | 결과 | 증빙 스크린샷 |
| :---: | :--- | :--- | :---: | :--- |
| **S1** | 데스크톱 1440×900 정상 전년비 UI | 비교 블록 뷰포트 중앙 스크롤 및 카드 내부 잘림 없음(`ClippingFree: true`), 한식 4개 지표 및 표본수 대조 | **PASS** | [`phase5d_step2_s1_desktop_yoy.png`](file:///d:/Franchise_Dashboard/reports/phase5d_step2_s1_desktop_yoy.png) |
| **S2** | 지표별 4대 방향성 실측 검증 | (1) 실DB 카페(CAT_MAJ_07) 중위매출/가맹점수 실제 감소 및 무잘림 실측<br>(2) Mock 주입 4종 동시 표출 및 무잘림 실측 | **PASS** | [`phase5d_step2_s2_real_decrease.png`](file:///d:/Franchise_Dashboard/reports/phase5d_step2_s2_real_decrease.png)<br>[`phase5d_step2_s2_variations.png`](file:///d:/Franchise_Dashboard/reports/phase5d_step2_s2_variations.png) |
| **S3** | 데이터 누락 안전 안내 배너 주입 검증 | 스크롤 후 2025 누락 시 안내 배너 및 빈 시계열 배너 표출 실측, 런타임 크래시 0건 | **PASS** | [`phase5d_step2_s3_missing_2025_banner.png`](file:///d:/Franchise_Dashboard/reports/phase5d_step2_s3_missing_2025_banner.png)<br>[`phase5d_step2_s3_empty_series_banner.png`](file:///d:/Franchise_Dashboard/reports/phase5d_step2_s3_empty_series_banner.png) |
| **S4** | 8대 전 외식 업종 전환 기대값 전수 일치성 | `id="tab-CAT_MAJ_*"` 정밀 클릭 및 8개 업종 전수 trends API 기대값(표본수 및 4대 지표) 1:1 대사 통과 | **PASS** | [`phase5d_step2_s4_category_switching.png`](file:///d:/Franchise_Dashboard/reports/phase5d_step2_s4_category_switching.png) |
| **S5** | 데스크톱 및 모바일 가로 오버플로 0 | 데스크톱(1440px): 1440px / 모바일 피크(390px): 390px / 모바일 확장: 390px | **PASS** | [`phase5d_step2_s5_mobile_overflow0.png`](file:///d:/Franchise_Dashboard/reports/phase5d_step2_s5_mobile_overflow0.png) |
| **S6** | 모바일 1열 배치 및 44px 터치 영역, 무잘림 | 바텀시트 확장 후 비교 블록 스크롤, 1열 배치, 카드 실측 높이 74px (≥ 44px), `InView: true`, `ClippingFree: true` | **PASS** | [`phase5d_step2_s6_mobile_touch_targets.png`](file:///d:/Franchise_Dashboard/reports/phase5d_step2_s6_mobile_touch_targets.png) |
| **S7** | 패널 조작 및 키보드 접근성(Enter/Escape) 회귀 없음 | 접기 Enter 토글, 펼치기 Enter 토글, 연도 선택 2025 Enter 입력, Escape 닫기 완비 | **PASS** | [`phase5d_step2_s7_keyboard_interactions.png`](file:///d:/Franchise_Dashboard/reports/phase5d_step2_s7_keyboard_interactions.png) |
| **S8** | 보호 파일 3종 무결성 사후 보존 | `collector.py`, `gangnam_food_stores.sqlite3`, `run_gangnam.bat` 해시 일치 | **PASS** | `reports/phase5d_step2_yoy_validation.json` |

---

## 4. 보호 대상 파일 무결성 대조표

| 대상 파일 | 사전 기준 SHA-256 해시 | 사후 실측 SHA-256 해시 | 무결성 판정 |
| :--- | :--- | :--- | :---: |
| [`collector.py`](file:///d:/Franchise_Dashboard/collector.py) | `341BAC12BB0AF58DCBDEBBA9459033521F27DF9817E35BAD8B21A4D07BA3369C` | `341BAC12BB0AF58DCBDEBBA9459033521F27DF9817E35BAD8B21A4D07BA3369C` | **일치 (PASS)** |
| [`gangnam_food_stores.sqlite3`](file:///d:/Franchise_Dashboard/gangnam_food_stores.sqlite3) | `FEE3B58651CFED5C390C0B95DB02B05EBE92DF18619A06F4E399D429236F3A78` | `FEE3B58651CFED5C390C0B95DB02B05EBE92DF18619A06F4E399D429236F3A78` | **일치 (PASS)** |
| [`run_gangnam.bat`](file:///d:/Franchise_Dashboard/run_gangnam.bat) | `0582C3A1AE53450DDC482E9BF538510780CA2F14D44E987CC753D4E12C816491` | `0582C3A1AE53450DDC482E9BF538510780CA2F14D44E987CC753D4E12C816491` | **일치 (PASS)** |

---

## 5. 빌드 및 런타임 무결성 검증

- **프로덕션 빌드**: `npm.cmd --prefix frontend run build` 수행 결과 **Exit code 0** (정상 완료).
- **의존성 준수**: `package.json` 신규 패키지 추가 0건.
- **백엔드/수집기 보호**: `App.jsx`, 백엔드 API, SQLite DB, 수집기 파일 일체 미수정.
