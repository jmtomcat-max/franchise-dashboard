# Phase 5B Step 2: 공정위 거시 벤치마크 UI 연동 및 정합성·반응형 완결 보고서

**문서 승인 상태**: `STEP 2 SUPPLEMENT COMPLETED (FOR USER REVIEW)`  
**작업 일시**: 2026-10-14  
**작업자**: AI Pair Programmer (Antigravity)  
**기준 설계서**: [phase5b_ftc_dashboard_integration_design_r1.md](file:///d:/Franchise_Dashboard/reports/phase5b_ftc_dashboard_integration_design_r1.md)  
**관련 산출물**:
- UI 컴포넌트: [CategoryFilterBar.jsx](file:///d:/Franchise_Dashboard/frontend/src/components/CategoryFilterBar.jsx), [FtcBenchmarkPanel.jsx](file:///d:/Franchise_Dashboard/frontend/src/components/FtcBenchmarkPanel.jsx), [MapContainer.jsx](file:///d:/Franchise_Dashboard/frontend/src/components/MapContainer.jsx), [App.jsx](file:///d:/Franchise_Dashboard/frontend/src/App.jsx)
- API 서비스: [api.js](file:///d:/Franchise_Dashboard/frontend/src/services/api.js)
- 스타일 시트: [index.css](file:///d:/Franchise_Dashboard/frontend/src/index.css)
- 테스트 스위트: [test_phase5b_step1.py](file:///d:/Franchise_Dashboard/tests/test_phase5b_step1.py), [test_phase5b_step2_supplement.py](file:///d:/Franchise_Dashboard/tests/test_phase5b_step2_supplement.py)

---

## 1. 보완 요구사항 및 해결 요약

| 사용자 보완 지시문 | 문제점 및 원인 | 조치 및 구현 내역 | 검증 결과 |
| :--- | :--- | :--- | :--- |
| **1. 최신 연도 자동 선택 vs 직접 지정 분리** | 클라이언트 초기화 시 특정 연도를 지정하여 백엔드의 DB 기반 최신 연도 자동 판정 및 단일 이전 연도 원자적 대체 로직이 무력화될 위험 존재. | 초기 `selectedYear`를 `null`로 유지하고 백엔드 호출 시 `year` 파라미터를 제외. 사용자가 드롭다운에서 명시적으로 연도를 선택한 경우에만 `year` 파라미터 전송. 선택 모드 뱃지(`.year-mode-pill`) 추가. | `test_phase5b_step2_supplement.py` 4종 테스트 전수 통과 (자동 선택, 직접 지정, 404 차단, 원자적 대체 배너) |
| **2. 지도 밀집도 서클 데이터 정합성 교정** | 광진구 전체 점포 격자 밀집도 원을 업종 선택 시 색상을 바꾸어 마치 업종별 밀집도인 것처럼 오해 유발. | 업종 선택 시 서클 색상을 바꾸던 임의 recoloring 연출 완전 제거. 서클 색상을 광진구 전체 점포 밀집도 램프로 고정. 지도 상단 HUD에 `📍 광진구 전체 외식업 밀집도 (100m 격자) \| 벤치마크 대상: 🍚 한식 (전국 공정위)`로 성격 명확히 분리. 우측 하단에 전체 밀집도 범례(3, 15, 30, 60, 100+) 추가 및 팝업 안내 보강. | 데스크톱 기본/치킨 캡처에서 지도 서클 색상 고정 및 HUD/범례 분리 표기 검증 완료 |
| **3. 390×844 모바일 요소 잘림 방지 및 바텀시트 제스처** | `100vw` 사용으로 인한 윈도우 스크롤바 폭 오버플로우와 가로 텍스트로 인해 4번째 막대(2026 스냅샷), 대표 수치, 비교 막대 수치가 잘림. 바텀시트 터치 제스처 부재. | `100vw`를 `width: 100%`, `max-width: 100%`, `box-sizing: border-box`로 전면 교체. 4개년 차트 컬럼을 `flex: 1 1 0`, 막대 최대폭 20px, 하단 연도/스냅샷 라벨을 2열 스택(`flex-direction: column`)으로 최적화하여 390px 폭 안에 100% 안착. 바텀시트에 실제 터치 스와이프(`onTouchStart`, `onTouchEnd`) 및 탭 클릭 듀얼 인터랙션 구현. | 390×844 모바일 에뮬레이션 캡처에서 2026 스냅샷, 대표 수치, 3대 비교 막대 수치 100% 온스크린 확인 |
| **4. 공정위 오류 재시도 및 키보드 접근성** | 오류 카드 재시도 버튼이 기존 상태를 다시 설정하는 것에 그쳐 네트워크 재요청을 유발하지 않을 수 있음. 차트 막대의 키보드 선택 불가. | `App.jsx`에 `ftcRetryKey` 상태를 도입하고 `onRetry` 시 키를 증가시켜 `useEffect` 네트워크 재호출 보장. 차트 막대 컬럼에 `role="button"`, `tabIndex={0}`, `aria-pressed`, `onKeyDown` (Enter/Space 키 핸들러) 완비. | 네트워크 재호출 및 키보드 선택 인터랙션 코드 검증 완료 |
| **5. 실측 화면 캡처 및 빌드·테스트 보고** | 모바일 및 데스크톱 실측 캡처 제출, 빌드 및 무회귀 보고 필요. | 데스크톱 기본(1920×1080), 데스크톱 치킨(1920×1080), 모바일 피크(390×844), 모바일 확장(390×844) 실제 캡처 완료. Vite 빌드 0 Errors, 백엔드 테스트 16개 전수 통과. 운영 DB 무변경 유지. | 하단 3~5절 상세 수록 |

---

## 2. 세부 구현 아키텍처 및 정합성 원칙

### 2.1 최신 연도 자동 선택과 사용자 직접 지정 상태 분리
- **API 전송 규칙**:
  - `selectedYear === null` (기본값):
    - `GET /api/v1/ftc/benchmark/latest?category_major_id=CAT_MAJ_01` (쿼리 스트링에 `year` 누락).
    - 백엔드가 DB의 최신 수집 연도(2026)를 동적으로 판정하며, 해당 업종 데이터 부재 시 직전 이용 가능 연도(2025)로 원자적 단일 대체를 수행함.
    - 대체 발생 시 응답의 `is_fallback_applied: true`, `fallback_reason`을 수신하여 패널 상단에 주황색 경고 배너(`.fallback-alert-banner`)와 헤더 배지(`⚠️ 2025년 대체 표출`)를 자동 표출.
  - `selectedYear !== null` (사용자가 드롭다운 또는 차트 막대를 클릭/엔터하여 직접 선택):
    - `GET /api/v1/ftc/benchmark/latest?category_major_id=CAT_MAJ_01&year=2024` (쿼리 스트링에 `year` 명시).
    - 사용자의 선택을 엄격히 존중하여 백엔드는 절대 다른 연도로 대체하지 않으며, 데이터가 없을 경우 명확한 404(`NO_DATA_FOR_REQUESTED_YEAR`)를 반환함.
- **UI 모드 인디케이터**:
  - `CategoryFilterBar` 우측에 `.year-mode-pill` 뱃지를 배치하여 현재 상태가 `자동 판정`(초록색)인지 `직접 지정`(파란색)인지 사용자가 즉시 인지 가능.

### 2.2 지리 공간 데이터 정합성 (GIS Data Governance)
- **데이터 성격 명확 분리**:
  - **지도 100m 격자 원**: 소상공인진흥공단 공공데이터 기반 **"광진구 전체 외식업 점포 밀집도"** (고정 램프: 3개 미만 Sky Blue $\rightarrow$ 15개 Royal Blue $\rightarrow$ 30개 Violet $\rightarrow$ 60개 Orange $\rightarrow$ 100개 이상 Crimson Red).
  - **플로팅 패널**: 공정거래위원회 정보공개서 기반 **"전국 프랜차이즈 거시 벤치마크"**.
- **오해 유발 연출 원천 제거**:
  - 업종을 한식 $\rightarrow$ 치킨 $\rightarrow$ 일식 등으로 변경하더라도 지도 상의 점포 격자 색상은 전혀 변경되지 않음 (임의 데이터 창작 및 거짓 상관관계 차단).
  - 지도 상단 중앙에 고정된 HUD 배지(`.map-overlay-badge`)를 통해:
    `📍 광진구 전체 외식업 밀집도 (100m 격자) | 벤치마크 대상: 🍚 한식 (전국 공정위)`
    두 데이터의 출처와 공간적 범위를 1초 만에 분리 인식할 수 있도록 안내.
  - 지도 우측 하단에 `.map-density-legend` 범례 카드를 신설하여 전체 점포 밀집도 색상 램프를 상시 표출.
  - 격자 서클 클릭 시 나타나는 MapLibre 팝업에 "※ 본 격자는 광진구 전체 외식업 점포 기준 밀집도이며, 공정위 전국 거시 통계와 독립적인 지표입니다." 안내문 명시.

### 2.3 390×844 모바일 뷰포트 최적화 및 제스처 인터랙션
- **`overflow-x: hidden` 감춤 배제 및 100% 온스크린 배치**:
  - 기존 코드의 `100vw`가 윈도우 스크롤바 폭(16px)을 포함하여 우측 요소를 물리적으로 밀어내던 문제를 근본 해결하기 위해 모든 컨테이너 폭을 `width: 100%`, `max-width: 100%`, `box-sizing: border-box`로 전환.
  - 4개년 차트의 4번째 컬럼(2026 최신 스냅샷)이 잘리지 않도록:
    - 막대 너비를 최대 20px로 슬림화.
    - 상단 수치 배지(`3.61억`)를 `left: 50%; transform: translateX(-50%)`로 막대 중심 정렬.
    - 하단 라벨을 상하 2줄(`flex-direction: column; align-items: center`)로 배치하여 `2026`과 `스냅샷`이 가로 폭을 침범하지 않도록 설계.
  - 대표 중위 매출(`36,117만원 (3.61억원)`)과 3대 비교 막대(중앙값, 5% 절사평균, 점포수 가중평균)의 우측 수치 라벨이 화면 우측 여백 안에 100% 안착.
- **바텀시트 터치 스와이프 제스처 및 탭 듀얼 인터랙션**:
  - 바텀시트 상단 핸들 바(`.mobile-bottom-sheet-handle`)에 `onTouchStart`, `onTouchEnd` 리스너를 결합하여 Y축 30px 이상의 드래그 동작 시 부드럽게 펼쳐짐/접힘이 전환되는 실제 모바일 스와이프 제스처 구현.
  - 단순 클릭(탭) 및 키보드 Enter/Space 조작으로도 토글 가능하도록 듀얼 접근성 보장.

---

## 3. 실제 화면 캡처 검증

데스크톱(1920×1080)과 모바일(390×844)의 실제 브라우저 렌더링 화면을 캡처하여 검증했습니다.

### 3.1 데스크톱 기본 화면 (1920×1080): 자동 선택 연도 & 전체 밀집도 범례/분리 HUD
> 상단 기준연도에 `최신 연도 (자동 선택)` 및 `자동 판정` 뱃지가 적용되어 있고, 지도의 서클 색상은 전체 밀집도 고유 램프(우측 하단 범례와 1:1 일치)를 유지합니다. 지도 상단 중앙의 HUD 배지가 데이터 성격을 명확히 분리하고, 좌측 벤치마크 패널의 대표 매출과 4개년 차트가 완벽하게 공존합니다.

![데스크톱 기본 화면](/C:/Users/jongmin98/.gemini/antigravity-ide/brain/e277a09d-d309-4b21-aaae-1fe31ab1fdc4/phase5b_step2_desktop.png)

### 3.2 데스크톱 치킨 업종 전환 화면 (1920×1080): 지도 밀집도 고정 유지 확인
> 상단 필터에서 '치킨·패스트푸드'를 선택했을 때 지도 서클의 색상은 전체 점포 밀집도 기준 그대로 유지되며, 지도 상단 HUD가 `📍 광진구 전체 외식업 밀집도 (100m 격자) | 벤치마크 대상: 🍗 치킨·패스트푸드 (전국 공정위)`로 갱신되고 좌측 패널의 벤치마크 지표(중위매출 1.93억, 4개년 차트, 창업비용)만 치킨 업종 통계로 동기화됩니다.

![데스크톱 치킨 업종 화면](/C:/Users/jongmin98/.gemini/antigravity-ide/brain/e277a09d-d309-4b21-aaae-1fe31ab1fdc4/phase5b_step2_desktop_chicken.png)

### 3.3 모바일 피크 뷰 (390×844): 지도 중심 + 바텀시트 요약
> 390×844 모바일 뷰포트에서 상단 헤더의 API 상태와 데이터 갱신 버튼, 지도 HUD 배지와 점포 밀집도 범례가 겹침 없이 깔끔하게 배치되며, 하단 바텀시트에 한식 중위매출(36,117만원)과 2026년 배지가 피크 형태로 지도 시야를 60% 이상 확보합니다.

![모바일 피크 뷰](/C:/Users/jongmin98/.gemini/antigravity-ide/brain/e277a09d-d309-4b21-aaae-1fe31ab1fdc4/phase5b_step2_mobile_peek.png)

### 3.4 모바일 확장 뷰 (390×844): 4개년 차트 및 대표 수치 100% 온스크린
> 바텀시트를 상향 스와이프 또는 탭하여 전개했을 때, 대표 매출(`36,117만원 (3.61억원)`), 3대 지표 수평 비교 바, 그리고 4개년 차트의 마지막 연도인 **2026년 최신 스냅샷 막대(주황 빗금)와 `3.61억` 수치 배지, `2026 / 스냅샷` 라벨이 화면 우측 경계선 안쪽에 100% 온전히 표출**됩니다 (`overflow-x: hidden` 감춤 없이 여백 내 안착).

![모바일 확장 뷰](/C:/Users/jongmin98/.gemini/antigravity-ide/brain/e277a09d-d309-4b21-aaae-1fe31ab1fdc4/phase5b_step2_mobile_expanded.png)

---

## 4. 테스트 및 빌드 무회귀 검증 결과

### 4.1 백엔드 API 종합 단위 테스트 스위트 (16/16 통과, 100%)
Step 2 보완 사항(자동 연도 선택 vs 직접 지정 분리, 부재 연도 strict 404, 단일 이전 연도 원자적 대체 및 품질 배너 근거 검증)을 위한 전용 테스트 [test_phase5b_step2_supplement.py](file:///d:/Franchise_Dashboard/tests/test_phase5b_step2_supplement.py)를 신설하고 기존 Step 1 테스트와 통합 실행했습니다.

```bash
$ python -m pytest tests/test_phase5b_step1.py tests/test_phase5b_step2_supplement.py -v
============================= test session starts =============================
tests/test_phase5b_step1.py::test_01_ftc_status PASSED                   [  6%]
tests/test_phase5b_step1.py::test_02_ftc_benchmark_hansik_2026 PASSED    [ 12%]
tests/test_phase5b_step1.py::test_03_all_8_major_categories PASSED       [ 18%]
tests/test_phase5b_step1.py::test_04_unmapped_category_handling PASSED   [ 25%]
tests/test_phase5b_step1.py::test_05_explicit_year_and_no_fallback PASSED [ 31%]
tests/test_phase5b_step1.py::test_06_fallback_scenario_simulation PASSED [ 37%]
tests/test_phase5b_step1.py::test_07_ftc_trends PASSED                   [ 43%]
tests/test_phase5b_step1.py::test_08_ftc_years PASSED                    [ 50%]
tests/test_phase5b_step1.py::test_09_existing_apis_regression PASSED     [ 56%]
tests/test_phase5b_step1.py::test_10_dynamic_new_year_addition PASSED    [ 62%]
tests/test_phase5b_step1.py::test_11_utc_to_kst_conversion PASSED        [ 68%]
tests/test_phase5b_step1.py::test_12_status_safety_when_latest_year_has_no_completed_audit PASSED [ 75%]
tests/test_phase5b_step2_supplement.py::test_auto_year_selection_without_year_param PASSED [ 81%]
tests/test_phase5b_step2_supplement.py::test_manual_year_selection_with_explicit_year_param PASSED [ 87%]
tests/test_phase5b_step2_supplement.py::test_manual_year_selection_nonexistent_year_strictly_no_fallback PASSED [ 93%]
tests/test_phase5b_step2_supplement.py::test_auto_year_selection_atomic_fallback_when_latest_year_missing PASSED [100%]
======================== 16 passed, 1 warning in 1.27s ========================
```

### 4.2 프런트엔드 프로덕션 빌드 무결성 (0 Errors)
```bash
$ cd frontend && npm.cmd run build
> franchise-dashboard-frontend@0.1.0 build
> vite build

vite v5.4.21 building for production...
transforming...
✓ 41 modules transformed.
rendering chunks...
computing gzip size...
dist/index.html                   0.61 kB │ gzip:   0.46 kB
dist/assets/index-BwFlle_W.css   96.76 kB │ gzip:  15.20 kB
dist/assets/index-BPC6uT_i.js   987.30 kB │ gzip: 277.99 kB
✓ built in 5.71s
```

### 4.3 운영 데이터베이스 및 기존 지도 API 불변성 준수
- **운영 DB 무변경**: `data/gangnam_food_stores.sqlite3`, `data/ftc_macro_statistics_v1.sqlite3` 등 모든 데이터베이스 파일은 읽기 전용으로만 조회되었으며 스키마나 레코드가 변경되지 않았습니다.
- **기존 지도 API 무손실**: 기존 `/api/v1/analytics/summary`, `/regions`, `/grid`, `/hotspots` 엔드포인트의 응답 구조와 정합성이 100% 온전히 유지되었습니다.

---

## 5. 최종 결론

사용자의 Phase 5B Step 2 보완 지침 5개 항목이 모두 완벽하게 이행되었습니다:
1. 연도 자동 선택(null 미전송 $\rightarrow$ 원자적 단일 대체 보장)과 직접 지정(`year` 전송 $\rightarrow$ strict no-fallback)의 상태 분리 및 배지 연동 완료.
2. 광진구 전체 점포 밀집도 격자 서클 색상 고정 및 지도 HUD·우측 하단 범례·팝업 분리 표기로 데이터 왜곡 원천 차단.
3. 390×844 실제 모바일 뷰포트에서 대표 수치, 비교 막대 수치, 4개년 차트 마지막 연도(2026 스냅샷) 및 라벨이 100% 들어오도록 반응형 구조 최적화 및 바텀시트 터치 스와이프 제스처 구현.
4. 오류 상태 재시도 버튼의 실제 네트워크 재요청 보장(`ftcRetryKey`) 및 차트 연도 막대 키보드 접근성 완비.
5. 빌드 0 Errors 통과, 단위 테스트 16종 전수 통과, 데스크톱/모바일 실측 캡처 4종 제출.

**작업 수칙 준수**: 지침에 따라 **Step 3(전수 검증 및 성능 최적화)로 넘어가지 않고 Step 2 보완 완료 시점에서 멈추어 사용자의 최종 확인 및 승인을 대기**합니다.
