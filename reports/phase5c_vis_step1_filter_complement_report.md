# Phase 5C-Vis Step 1 모바일 상단 필터 보완 및 실제 좌표 클릭 검증 보고서

**문서 경로**: `reports/phase5c_vis_step1_filter_complement_report.md`  
**작성 일시**: 2026-10-15  
**검증 환경**: Google Chrome 390×844 (iPhone 12/13/14 Pro 규격, Device Scale Factor 3, 모바일 터치 에뮬레이션)  
**적용 대상**: 모바일 상단 필터바 (`CategoryFilterBar` 및 `frontend/src/index.css`)  
**보존 규칙 준수**: 데스크톱 레이아웃, 백엔드 API, SQLite DB, 데이터 파이프라인 무변경 보존. 기존 캡처/보고서 일체 덮어쓰기 금지 및 신규 파일명(`phase5c_vis_step1_filter_comp_*`) 격리 적용. 3D 기둥(Step 2) 미착수.

---

## 1. 개요 및 요구사항 이행 요약

사용자의 모바일 상단 필터 보완 요청사항을 충족하기 위해 다음 3가지 핵심 작업을 완수하고 실제 브라우저 좌표 클릭(손가락 탭)으로 동작을 실측 검증했습니다.

1. **390px 화면 내 연도 선택 및 공정위 버튼 완전 안착 & 터치 가능 보장**:
   - 불필요한 라벨(`region-section-label`)을 모바일에서 완전히 숨겨 시도(58px) + 시군구(72px) 선택기를 140px 이내에 안착시켰습니다.
   - 연도 선택기(`#ftc-year-select`, 68px)와 공정위 패널 열기 버튼(`.ftc-drawer-btn`, 154.81px)이 `0 <= left < right <= 390` 범위 내에 정확히 배치되어 요소 간 겹침(0px) 및 가로 넘침(0px)을 완벽히 해소했습니다.
2. **긴 업종 목록만 독자적 가로 스크롤 분리**:
   - 1행(지역·연도·공정위 버튼)은 고정 그리드로 위치를 완벽히 고정하고, 2행의 8대 외식업 대분류 탭 목록(`.category-tabs-scroll`)만 독립적으로 가로 스크롤되도록 분리했습니다.
   - 탭 목록을 140px 스크롤해도 1행의 컨트롤러 좌표는 단 1px도 이동하지 않음을 실측 증명했습니다.
3. **실제 손가락 탭(CDP 마우스/터치 좌표 클릭) 검증**:
   - 단순 자바스크립트 이벤트 호출(`el.click()`)이 아닌 브라우저 CDP의 실제 화면 중심 좌표 $(X, Y)$ 클릭(`mousePressed` + `mouseReleased`)으로 공정위 바텀시트 열기/닫기 및 연도 선택 동작을 실측 검증했습니다.
4. **증거 파일 독립 격리 (과거 캡처 보존)**:
   - 과거 실행 시각 변경 문제를 원천 차단하기 위해 이전 `phase5c_vis_step1_*` 파일들을 일체 건드리지 않고, 모든 신규 캡처와 측정 데이터를 `phase5c_vis_step1_filter_comp_*`라는 완전히 새로운 파일명으로 생성·보존했습니다.

---

## 2. 390px 모바일 레이아웃 실측 바운딩 박스 (Element Bounding Rects)

`reports/phase5c_vis_step1_filter_comp_metrics.json`에서 추출한 모바일 390×844 환경의 실제 렌더링 좌표 측정값입니다.

| UI 컨트롤러 | 선택자 (Selector) | Left (px) | Right (px) | Top (px) | Bottom (px) | Width (px) | Height (px) | 390px 내부 여부 | 터치 가능성 |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **전체 필터바** | `.category-filter-bar` | 0.00 | 390.00 | 42.00 | 105.95 | 390.00 | 63.95 | **완전 안착** | - |
| **1행: 시도 선택기** | `#sido-select` | 8.00 | 66.00 | 45.19 | 69.19 | 58.00 | 24.00 | **완전 안착** | 양호 (58×24px) |
| **1행: 시군구 선택기** | `#sigungu-select` | 68.39 | 140.39 | 45.19 | 69.19 | 72.00 | 24.00 | **완전 안착** | 양호 (72×24px) |
| **1행: 기준연도 선택** | `#ftc-year-select` | 145.59 | 213.59 | 45.19 | 69.19 | 68.00 | 24.00 | **완전 안착** | 양호 (68×24px) |
| **1행: 공정위 열기 버튼** | `.ftc-drawer-btn` | 227.19 | 382.00 | 45.19 | 69.19 | 154.81 | 24.00 | **완전 안착** | **우수 (154.8×24px)** |
| **2행: 업종 탭 스크롤** | `.category-tabs-scroll` | 8.00 | 382.00 | 75.77 | 101.77 | 374.00 | 26.00 | **완전 안착** | 가로 스크롤 가능 |

- **요소 간 간격 및 겹침 분석**:
  - 시도 $\rightarrow$ 시군구: 간격 2.39px (겹침 없음)
  - 시군구 $\rightarrow$ 연도 선택: 간격 5.20px (겹침 없음)
  - 연도 선택 $\rightarrow$ 공정위 버튼: 간격 13.60px (겹침 없음)
  - 공정위 버튼 우측 여백: $390.00 - 382.00 = 8.00\text{px}$ (안전 마진 확보)
- **가로 넘침(Horizontal Overflow)**: `document.documentElement.scrollWidth: 390px` (뷰포트 너비 390px와 100% 일치, 가로 스크롤바 발생 0)

---

## 3. 실제 좌표 클릭(손가락 탭) 동작 검증 결과

### 3.1 공정위 패널 열기 버튼 좌표 클릭 검증
- **클릭 목표**: 공정위 패널 열기 버튼(`.ftc-drawer-btn`)의 물리적 중심 좌표
- **클릭 좌표**: $(X: 304.59, Y: 57.19)$
- **동작 결과**:
  - `Input.dispatchMouseEvent` 발송 즉시 바텀시트 열림 (`.ftc-benchmark-panel.drawer-open` 활성화)
  - 바텀시트 닫기 버튼(`.mobile-drawer-close-btn`, 중심 좌표 $X: 375.08, Y: 806.39$) 좌표 클릭 시 바텀시트가 즉시 정상 수납됨 확인
  - `drawerOpenedSuccessfully: true`, `drawerClosedSuccessfully: true`

### 3.2 연도 선택기 좌표 클릭 및 선택 검증
- **클릭 목표**: 기준연도 선택 드롭다운(`#ftc-year-select`)의 물리적 중심 좌표
- **클릭 좌표**: $(X: 179.59, Y: 57.19)$
- **동작 결과**:
  - 2025년 선택 (`selectedYear: "2025"`) 적용 완료
  - 공정위 버튼 텍스트가 `공정위 2025년 등록 (2024년 결산) · 최신 완결 후보`로 즉시 동적 갱신됨 확인
  - 드롭다운 내부 옵션: 2026년(최신 스냅샷), 2025년(최신 완결 후보), 2024년, 2023년 정상 유지

### 3.3 긴 업종 목록 가로 스크롤 분리 및 상단 고정 검증
- **검증 방법**: `.category-tabs-scroll` 요소의 `scrollLeft`를 140px로 스크롤한 후 상단 툴바 컨트롤러들의 좌표 변동 여부 측정

| 항목 | 스크롤 전 (Pre-scroll) | 스크롤 후 (Post-scroll) | 변동량 (Delta) | 판정 |
| :--- | :---: | :---: | :---: | :---: |
| **업종 탭 스크롤 위치 (`tabsScrollLeft`)** | 0.00px | 140.00px | +140.00px | **정상 가로 스크롤** |
| **필터바 전체 스크롤 (`filterBarScrollLeft`)** | 0.00px | 0.00px | 0.00px | **고정 유지 (불변)** |
| **윈도우 가로 스크롤 (`windowScrollX`)** | 0.00px | 0.00px | 0.00px | **고정 유지 (불변)** |
| **시도 선택기 X좌표 (`sidoLeft`)** | 8.00px | 8.00px | 0.00px | **완전 고정** |
| **시군구 선택기 X좌표 (`sigunguLeft`)** | 68.39px | 68.39px | 0.00px | **완전 고정** |
| **연도 선택기 X좌표 (`yearLeft`)** | 145.59px | 145.59px | 0.00px | **완전 고정** |
| **공정위 버튼 X좌표 (`ftcLeft`)** | 227.19px | 227.19px | 0.00px | **완전 고정** |

- **결론**: 긴 업종 목록만 독자적으로 부드럽게 가로 스크롤되며, 상단의 지역/연도/공정위 버튼은 흔들림 없이 화면 상단에 완벽히 고정됩니다.

---

## 4. 실측 화면 캡처 증빙 (신규 파일명 격리 저장)

모든 캡처는 기존 증거 파일을 재사용하지 않고 신규 파일명으로 생성되었습니다.

### 4.1 모바일 기본 개요 화면 (Overview)
- **파일명**: `reports/phase5c_vis_step1_filter_comp_overview.png`
- **화면 설명**: 390×844 모바일 화면에서 상단 1행에 시도/시군구/연도선택/공정위버튼이 잘림 없이 깔끔하게 표시되며, 지도가 첫 화면의 80% 이상을 차지합니다.
- **이미지**:
  ![모바일 상단 필터 개요 화면](file:///d:/Franchise_Dashboard/reports/phase5c_vis_step1_filter_comp_overview.png)

### 4.2 공정위 버튼 실제 좌표 클릭 후 바텀시트 오픈 화면
- **파일명**: `reports/phase5c_vis_step1_filter_comp_drawer_click.png`
- **화면 설명**: 공정위 버튼 중심 좌표 $(X: 304.59, Y: 57.19)$ 클릭으로 바텀시트가 열리고 닫기 버튼(✕)이 활성화된 상태입니다.
- **이미지**:
  ![공정위 바텀시트 열림 화면](file:///d:/Franchise_Dashboard/reports/phase5c_vis_step1_filter_comp_drawer_click.png)

### 4.3 연도 선택기 좌표 클릭 및 2025년 선택 화면
- **파일명**: `reports/phase5c_vis_step1_filter_comp_year_click.png`
- **화면 설명**: 연도 선택기 중심 좌표 $(X: 179.59, Y: 57.19)$ 클릭으로 2025년을 선택한 후 공정위 출처 태그 문구가 2025년으로 즉시 갱신된 모습입니다.
- **이미지**:
  ![연도 선택 2025년 반영 화면](file:///d:/Franchise_Dashboard/reports/phase5c_vis_step1_filter_comp_year_click.png)

### 4.4 업종 목록 독립 가로 스크롤 검증 화면
- **파일명**: `reports/phase5c_vis_step1_filter_comp_category_scroll.png`
- **화면 설명**: 상단 컨트롤러(지역·연도·공정위 버튼)는 정확히 고정된 채, 2행의 탭 목록만 스크롤되어 `일식`, `양식·세계음식`, `치킨·패스트푸드`, `분식·간편식`이 화면 안으로 이동한 모습입니다.
- **이미지**:
  ![업종 목록 독자 가로 스크롤 화면](file:///d:/Franchise_Dashboard/reports/phase5c_vis_step1_filter_comp_category_scroll.png)

---

## 5. 생성 및 보존 파일 목록

1. **테스트 스크립트**:
   - [scratch/test_phase5c_vis_step1_filter_complement.mjs](file:///d:/Franchise_Dashboard/scratch/test_phase5c_vis_step1_filter_complement.mjs)
2. **원시 측정 데이터 (JSON)**:
   - [reports/phase5c_vis_step1_filter_comp_metrics.json](file:///d:/Franchise_Dashboard/reports/phase5c_vis_step1_filter_comp_metrics.json)
3. **신규 캡처 파일 (PNG)**:
   - [reports/phase5c_vis_step1_filter_comp_overview.png](file:///d:/Franchise_Dashboard/reports/phase5c_vis_step1_filter_comp_overview.png)
   - [reports/phase5c_vis_step1_filter_comp_drawer_click.png](file:///d:/Franchise_Dashboard/reports/phase5c_vis_step1_filter_comp_drawer_click.png)
   - [reports/phase5c_vis_step1_filter_comp_year_click.png](file:///d:/Franchise_Dashboard/reports/phase5c_vis_step1_filter_comp_year_click.png)
   - [reports/phase5c_vis_step1_filter_comp_category_scroll.png](file:///d:/Franchise_Dashboard/reports/phase5c_vis_step1_filter_comp_category_scroll.png)
4. **본 보고서**:
   - [reports/phase5c_vis_step1_filter_complement_report.md](file:///d:/Franchise_Dashboard/reports/phase5c_vis_step1_filter_complement_report.md)

---

## 6. 결론 및 다음 단계 착수 대기

- 모바일 390px 화면에서 상단 필터바의 연도 선택 및 공정위 패널 열기 버튼이 완전하게 노출되고 실제 손가락 탭으로 원활하게 조작 가능함을 실측 검증했습니다.
- 긴 업종 목록만 독자적으로 가로 스크롤되며 상단 툴바는 안정적으로 고정됨을 확인했습니다.
- 기존 증거 파일 재사용 및 덮어쓰기 없이 모든 산출물을 신규 파일명으로 안전하게 격리 저장했습니다.
- **AGENTS.md 보호 규칙 및 사용자 지침에 따라 3D 기둥(`fill-extrusion`) 구현(Step 2)은 일체 착수하지 않고 본 보고서 제출 후 작업을 중단합니다.**
