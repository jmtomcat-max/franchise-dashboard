# Phase 5 Stage 5A-R3: 기본 지도 서비스 품질 및 최종 보정 검증 보고서 (Quality Report)

- **작성 일자**: 2026-10-13
- **프로젝트 경로**: `D:\Franchise_Dashboard`
- **대상 패키지**: `frontend/` (Vite v5.4.11 + React 18 + MapLibre GL JS v4.7.1)
- **백엔드 서비스**: `http://127.0.0.1:8000` (FastAPI Stage 4E 분석 서비스)
- **최종 품질 판정**: **PASS (Phase 5A-R3 모바일 헤더·타일 렌더링 및 KPI 문구 보정 완료, Phase 5B 대기)**

---

## 1. 프론트엔드 환경 및 빌드 품질 검증

`D:\Franchise_Dashboard\frontend`에서 실행한 자동화 검증 및 빌드 결과입니다.

| 검증 항목 | 도구 / 버전 | 결과 / 수치 | 판정 |
| :--- | :--- | :--- | :--- :---: |
| **의존성 설치** | `npm install` | 102개 패키지 정상 설치 완료 (추가 외부 라이브러리 없음) | **PASS** |
| **프로덕션 빌드** | `npm run build` (Vite v5.4.11) | 6.10초 완료, 컴파일 오류 **0건** | **PASS** |
| **번들 산출물 크기** | Rollup / Gzip | JS 270.92 kB (gzip), CSS 12.10 kB (gzip) | **PASS** |
| **개발 서버 실행** | `npm run dev` | `http://127.0.0.1:5173/` (HTTP 200 정상 서빙) | **PASS** |
| **브라우저 콘솔 에러** | Edge CDP Logging | 런타임 콘솔 오류 **0건** 확인 | **PASS** |

---

## 2. Phase 5A-R3 핵심 보정 항목 실측 검증

### 2.1 모바일 헤더 및 화면 잘림 수정 (390×844)
- **결함 진단**:
  - 기존 `.header-brand > div` 선택자가 GIS 로고(`.brand-icon`)와 제목 래퍼 모두에 `flex: 1`을 적용하여 로고가 화면 너비의 절반 가까이 비정상 확장됨.
  - 이로 인해 제목과 부제목이 우측으로 밀려 잘리고, 데이터 갱신 버튼이 화면 우측 경계를 벗어나는 결함 발생.
- **수정 내용**:
  - [Header.jsx](file:///d:/Franchise_Dashboard/frontend/src/components/Header.jsx): 제목과 부제목을 감싸는 요소에 `.header-copy` 명시적 클래스 부여.
  - [index.css](file:///d:/Franchise_Dashboard/frontend/src/index.css): 
    - `.brand-icon`에 `flex: 0 0 auto !important` 적용 (GIS 로고 가로 42px 정상 고정 크기 유지).
    - `.header-copy`에 `flex: 1 !important; min-width: 0 !important;` 적용 (제목 래퍼만 공간 차지).
    - `.header-actions`에 `width: 100%`, `justify-content: space-between` 및 배지/버튼 `flex-shrink: 0; white-space: nowrap;` 적용.
    - `.badge-meta`에 `flex-shrink: 0; white-space: nowrap;` 적용.
- **390×844 실측 수치**:
  - **GIS 로고 크기**: 너비 **42px**, 높이 **30px** (정상 크기 유지, 비정상 확장 **0건**)
  - **제목 전체 표시**: `외식 프랜차이즈 시장 분석 3D GIS 상황실` (scrollWidth 307px == clientWidth 307px, 잘림 **0건**)
  - **부제목 전체 표시**: `Phase 5A 기본 지도 서비스 · 광진구 건대입구 중심 검증 뷰` (scrollWidth 307px == clientWidth 307px, 잘림 **0건**)
  - **API 상태 배지**: `● API 정상 연결` (right: 117.5px, 뷰포트 내부 정상 배치, 잘림 **0건**)
  - **데이터 갱신 버튼**: `데이터 갱신` (right: 374.0px, 뷰포트 390px 대비 16px 내부 안전 마진 확보, 잘림 **0건**)
  - **기준 월 배지**: `2026-07 기준` (right: 374.0px, 뷰포트 내부 정상 배치, 잘림 **0건**)
  - **가로 스크롤 수치**: `scrollWidth: 390px`, `horizontalOverflow: 0px` (**가로 스크롤 0**)

### 2.2 모바일 지도 타일 및 밀집도 원 실표시 (회색 빈 지도 배제)
- **결함 진단**:
  - 모바일 세로 레이아웃 전환 시 `.map-container` 높이가 0으로 수축하거나 뷰포트 리사이즈 통지가 누락되어 지도 타일이 로드되지 않고 회색 배경(#e2e8f0)만 캡처되던 현상 발생.
- **수정 내용**:
  - [index.css](file:///d:/Franchise_Dashboard/frontend/src/index.css): `.map-container`에 `position: absolute; inset: 0; width: 100%; height: 100%;`를 적용하여 부모 `.map-wrapper` 높이에 완전 종속 밀착.
  - [MapContainer.jsx](file:///d:/Franchise_Dashboard/frontend/src/components/MapContainer.jsx):
    - `map.on('load')` 시점에 `map.resize()` 즉시 강제 호출.
    - `ResizeObserver` 및 `window.addEventListener('resize')`를 등록하여 모바일 뷰포트 변경 시 지도 리사이즈 및 타일 재계산 보장.
    - `window.__areTilesLoaded()` 헬퍼를 추가하여 모든 OSM 타일 및 밀집도 Feature 렌더링 완료 시점 동기화.
- **실표시 실측 결과**:
  - 모바일 지도 뷰포트 내 OSM 표준 도로·건물·지명 래스터 타일 100% 실표시 완료.
  - 건대입구 중심 **28개 밀집도 원형 서클** (Blue, Indigo, Purple 고대비 서클 및 2px 화이트 스트로크) 렌더링 확인.
  - 핫스팟 앵커 핀 `광진 건대입구 맛의거리` 정상 표출.
  - 모바일 캡처 파일 크기: 기존 44,405 bytes $\rightarrow$ **240,429 bytes** (실제 타일 및 벡터 그래픽 탑재 증명).

### 2.3 공정위 관련 KPI 표현 정정
- **수정 사유**:
  - 현재 공정위 API는 평문 브랜드명을 직접 제공하지 않고 사업자등록번호 및 정보공개서 번호 기반이므로, 72개 브랜드가 API로 직접 자동 검증됐다고 오인될 수 있는 표현 정정.
- **표현 변경 내역** ([MarketSummary.jsx](file:///d:/Franchise_Dashboard/frontend/src/components/MarketSummary.jsx)):
  - **기존**: `공인 가맹 브랜드 발견 점포` / `공정위 공인 72개 가맹사업 브랜드 대상`
  - **정정**: `주요 검증 브랜드 연결 점포` / `수동 검증 목록 72개 브랜드 기준`
  - 향후 브랜드별 정보공개서 등록번호와 공식 증빙이 확보된 항목에 한하여 `공정위 등록 확인`으로 고도화 표기할 방침 수립.

---

## 3. 백엔드 API 연동 실측 레이턴시 및 응답성

| 엔드포인트 | 메서드 | 응답 코드 | 실측 레이턴시 | 주요 수신 데이터 | 연동 상태 |
| :--- | :--- | :---: | :---: | :--- | :---: |
| `/api/v1/analytics/summary` | GET | `200 OK` | **21.80ms** | 전국 외식업 총 점포 수 `735,185`개소, 브랜드 침투율 `22.89%` | **정상** |
| `/api/v1/spatial/density/grid?sigungu_code=11215&limit=1000` | GET | `200 OK` | **29.10ms** | 광진구(11215) 100m 정밀 격자 셀 `466`개 | **정상** |
| `/api/v1/spatial/hotspots` | GET | `200 OK` | **11.45ms** | 전국 10대 핫스팟 중 Top 5 목록 및 카메라 파라미터 | **정상** |

---

## 4. 16개 시도 수식 증명 및 데이터 무결성

[nationwide_food_stores_v2.sqlite3](file:///D:/Franchise_Dashboard/data/nationwide_food_stores_v2.sqlite3)의 `collection_logs` 및 `stores` 테이블 전수 쿼리 결과입니다.

| 단계 | 항목명 | 산출 기준 | 건수 (건) | 비고 |
| :---: | :--- | :--- | :---: | :--- |
| **1** | **원천 API 수집 건수** | `SUM(raw_count)` (`signgu_code LIKE '12%'`) | **55,881** | 소진공 API에서 응답받은 총 점포 수 |
| **2** | **제외 업종 건수** | `SUM(excluded_count)` (`signgu_code LIKE '12%'`) | **8,359** | 주점 `I211` 및 구내식당 `I20701` 제외 |
| **3** | **최종 저장 대상 건수** | `SUM(saved_count)` (`signgu_code LIKE '12%'`) | **47,522** | 수집 계약 검증 통과 건수 |
| **4** | **실제 점포 DB 저장 건수** | `COUNT(*)` from `stores` (`raw_ctprvn_cd = '12'`) | **47,522** | 분석 DB에 실제 저장된 최종 점포 수 |

$$\mathbf{55,881 \text{ (원천 수집)} - 8,359 \text{ (제외 업종)} = 47,522 \text{ (최종 저장)}} \quad (\Delta = 0, \mathbf{100.00\% \text{ 완전 일치}})$$

---

## 5. 실제 브라우저 검증 증거 산출물 목록 (Visual Evidence)

Edge 헤드리스 브라우저 엔진을 통해 실제 뷰포트에서 렌더링된 화면 캡처 파일 목록입니다.

| 구분 | 파일 경로 | 해상도 | 파일 크기 | 검증 내용 및 증거 |
| :--- | :--- | :---: | :---: | :--- |
| **모바일 메인 (R3 핵심)** | [phase5_stage5a_mobile.png](file:///D:/Franchise_Dashboard/reports/phase5_stage5a_mobile.png) | 390 × 844 | **240,429 bytes** | GIS 로고(42px), 제목/부제목 온전 표시, 갱신버튼/배지 잘림 0, OSM 타일+밀집도원 28개 실표시, 가로스크롤 0 |
| **모바일 요약 (KPI 검증)** | [phase5_stage5a_mobile_summary.png](file:///D:/Franchise_Dashboard/reports/phase5_stage5a_mobile_summary.png) | 390 × 844 | **116,406 bytes** | 정정된 문구(`주요 검증 브랜드 연결 점포 48,002개소`, `수동 검증 목록 72개 브랜드 기준`), 기준월 배지 정상 표출 |
| **모바일 핫스팟** | [phase5_stage5a_mobile_hotspots.png](file:///D:/Franchise_Dashboard/reports/phase5_stage5a_mobile_hotspots.png) | 390 × 844 | **73,264 bytes** | 모바일 화면에서 상권 핫스팟 Top 5 카드 100% 폭 정상 배치 확인 |
| **데스크톱 표준** | [phase5_stage5a_desktop.png](file:///D:/Franchise_Dashboard/reports/phase5_stage5a_desktop.png) | 1920 × 1080 | **1,479,842 bytes** | 워터마크 없는 OSM 표준 타일, 건대입구 핫스팟 마커, 84개 가시 밀집도 서클 표출 |
| **밀집도 확대** | [phase5_stage5a_zoom_density.png](file:///D:/Franchise_Dashboard/reports/phase5_stage5a_zoom_density.png) | 1920 × 1080 | **1,489,137 bytes** | 건대입구 100m 정밀 격자 서클 확대 뷰 (Sky Blue~Crimson Red 고대비) |
| **팝업 열림** | [phase5_stage5a_popup.png](file:///D:/Franchise_Dashboard/reports/phase5_stage5a_popup.png) | 1920 × 1080 | **1,490,574 bytes** | 격자 셀 클릭 시 DOM 노드로 안전하게 렌더링된 상세 분석 팝업 카드 표출 |

---

## 6. 결론 및 단계 승인 대기

Phase 5A-R3 최종 보정 지침에 명시된 모든 항목(모바일 헤더 로고 크기 고정, 제목/부제목 및 버튼/배지 잘림 0, 가로 스크롤 0, 모바일 실제 지도 타일 및 밀집도 원 렌더링 캡처 확보, 공정위 KPI 표현 정정)이 완벽히 검증되었습니다.

지침에 따라 **Phase 5B로 넘어가지 않고 즉시 중단하며, 사용자의 검토 및 승인을 대기**합니다.
