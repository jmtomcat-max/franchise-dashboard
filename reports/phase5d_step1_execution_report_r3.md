# Phase 5D Step 5D-1 의미 안전성 감사 실행보고서 (R3)

> **문서 상태**: 완료 (Step 5D-2 승인 대기)  
> **감사 일시**: 2026-10-16 14:53:01 ~ 14:53:30 (KST)  
> **감사 환경**: Node.js Puppeteer (Headless Chrome), Windows 11, Vite Dev Server (`http://127.0.0.1:5173`)  
> **원시 데이터**: [`reports/phase5d_step1_semantic_audit_r3.json`](file:///d:/Franchise_Dashboard/reports/phase5d_step1_semantic_audit_r3.json)  
> **감사 스크립트**: [`scratch/audit_phase5d_step1_semantic_safety_r3.mjs`](file:///d:/Franchise_Dashboard/scratch/audit_phase5d_step1_semantic_safety_r3.mjs)  

---

## 1. 개요 및 R3 감사 목적

본 R3 감사는 **Gravity 전달용 작업지시서 (Phase 5D R2 Step 5D-1 R3)** 및 **재감사 산출물 검증보고서**([`reports/phase5d_step1_semantic_audit_r2_verification.md`](file:///d:/Franchise_Dashboard/reports/phase5d_step1_semantic_audit_r2_verification.md))의 피드백을 엄격히 반영하여 수행되었습니다.

- **R2 감사 검증 결과**: 데스크톱 시나리오 A·B·D는 정상 검증으로 PASS 근거가 보존되었으나, 시나리오 C·E·F·G는 실제 가시성 assertion 취약점(조상 클리핑 미검사 및 뷰포트 밖 판정 오류)이 확인되었습니다.
- **R3 감사 핵심 목표**:
  1. 감사 스크립트의 실제 가시성 판정 함수에 **모든 조상 요소의 overflow 클리핑(`overflow: hidden/auto/scroll/clip`) 계산을 추가**하고 엄격한 assertion을 구축.
  2. 시나리오 **C·E·F·G에 대해 실제 사용자 화면 노출 여부를 정밀 재측정**.
  3. 제품 결함으로 인해 요소가 화면에 보이지 않을 경우 억지로 PASS 처리하지 않고, **원시 사실에 입각하여 FAIL 및 제품 레이아웃/정보구조 결함으로 정직하게 확정**.

감사 전 과정에서 애플리케이션 기능 코드, 스타일, API, DB는 단 1바이트도 수정하지 않았습니다(변경 건수 **0건**).

---

## 2. 보호 대상 파일 무결성 검증

프로젝트 절대 보호 대상 3종 파일에 대해 SHA-256 해시 검증을 수행하였으며, 작업 전 기준선과 100% 동일함을 재확인했습니다.

| 파일명 | 기준선 SHA-256 | R3 감사 후 SHA-256 | 파일 크기 | 무결성 판정 |
| :--- | :--- | :--- | :---: | :---: |
| [`collector.py`](file:///d:/Franchise_Dashboard/collector.py) | `341bac12bb0af58dcbdebba9459033521f27df9817e35bad8b21a4d07ba3369c` | `341bac12bb0af58dcbdebba9459033521f27df9817e35bad8b21a4d07ba3369c` | 3,780 B | **일치 (PASS)** |
| [`gangnam_food_stores.sqlite3`](file:///d:/Franchise_Dashboard/gangnam_food_stores.sqlite3) | `fee3b58651cfed5c390c0b95db02b05ebe92df18619a06f4e399d429236f3a78` | `fee3b58651cfed5c390c0b95db02b05ebe92df18619a06f4e399d429236f3a78` | 15,831,040 B | **일치 (PASS)** |
| [`run_gangnam.bat`](file:///d:/Franchise_Dashboard/run_gangnam.bat) | `0582c3a1ae53450ddc482e9bf538510780ca2f14d44e987cc753d4e12c816491` | `0582c3a1ae53450ddc482e9bf538510780ca2f14d44e987cc753d4e12c816491` | 66 B | **일치 (PASS)** |

---

## 3. 전체 시나리오 감사 결과 총괄표

| ID | 시나리오 명칭 | 해상도 | 요청 조건 | 가시성 측정 결과 | 시나리오 판정 | 비고 및 캡처 |
| :---: | :--- | :---: | :--- | :--- | :---: | :--- |
| **A** | 데스크톱 전국 업종 | 1440×900 | 전국(00) / 카페·음료 / 2024년 | 전국, 카페, 연도배지, 패널 정상 노출 | **PASS** (기존 유지) | [`A 캡처`](file:///d:/Franchise_Dashboard/reports/phase5d_step1_audit_r2_desktop_nationwide.png) |
| **B** | 데스크톱 지역 업종 | 1440×900 | 서울 광진구 / 치킨·패스트푸드 / 2024년 | 광진구, 치킨, 연도배지, 패널 정상 노출 | **PASS** (기존 유지) | [`B 캡처`](file:///d:/Franchise_Dashboard/reports/phase5d_step1_audit_r2_desktop_regional_gwangjin.png) |
| **C** | 지역 Top 5 브랜드와 FTC 패널 동시 노출 | 1440×900 | 서울 광진구 / 카페·음료 / 2024년 / FTC 열림 | FTC 패널은 노출되나, **좌측 메가MGC커피 행이 사이드바 스크롤 아래 매몰** (`isActuallyVisible: false`) | **FAIL (제품 결함)** | **동시 노출 불가**<br>[`C 실패 캡처`](file:///d:/Franchise_Dashboard/reports/phase5d_step1_audit_r3_desktop_brand_coexistence_failure.png) |
| **D** | 데스크톱 2026 스냅샷 | 1440×900 | 전국(00) / 한식 / 2026년 | 2026 등록, 2025 결산, 스냅샷 배지 노출 | **PASS** (기존 유지) | [`D 캡처`](file:///d:/Franchise_Dashboard/reports/phase5d_step1_audit_r2_desktop_snapshot_2026.png) |
| **E** | 모바일 축소 피크 | 390×844 | 전국(00) / 한식 / 2024년 / 축소 | 초기 진입 시 수납 상태(top 844px 밖), **상단 공정위 버튼 클릭 시 top 781px 안착 확인** | **PASS (가시성 확보)** | **의미 결함 확인**<br>[`E 캡처`](file:///d:/Franchise_Dashboard/reports/phase5d_step1_audit_r3_mobile_peek.png) |
| **F** | 모바일 확장 상태 | 390×844 | 전국(00) / 한식 / 2024년 / 확장 | 피크 클릭 시 패널 확장(H: 122px), **대표매출 top 386px 정상 노출 확인** | **PASS (가시성 확보)** | **의미 결함 확인**<br>[`F 캡처`](file:///d:/Franchise_Dashboard/reports/phase5d_step1_audit_r3_mobile_expanded.png) |
| **G** | 모바일 지역·업종 피크 | 390×844 | 서울 광진구 / 카페·음료 / 2024년 / 축소 | 공정위 버튼 클릭 시 **피크 바 top 781px 안착 확인** | **PASS (가시성 확보)** | **의미 결함 확인**<br>[`G 캡처`](file:///d:/Franchise_Dashboard/reports/phase5d_step1_audit_r3_mobile_regional.png) |

---

## 4. C·E·F·G 재실행 정밀 실측 데이터 분석

### 4.1 [시나리오 C] 지역 Top 5 브랜드와 FTC 패널 동시 노출 실측
- **환경**: 1440×900, 서울특별시 광진구(11215), 카페·음료(CAT_MAJ_07), 2024년, FTC 드로어 열림
- **캡처 증빙**: [`phase5d_step1_audit_r3_desktop_brand_coexistence_failure.png`](file:///d:/Franchise_Dashboard/reports/phase5d_step1_audit_r3_desktop_brand_coexistence_failure.png)
- **실측치 대사표**:
  - 좌측 1위 브랜드 행 (`.regional-brands-card .top-brand-row`):
    - `elementRect`: `left: 48, top: 715, right: 270, bottom: 745, width: 222, height: 30`
    - 조상 클리핑 요소: `<aside class="panel summary-panel">` (`overflow: auto/auto`, `rect: top 129, bottom 609, height 480`)
    - 클리핑 계산: `visibleIntersectionRect: width: 222, height: 0` (`top 715 > clipping bottom 609`)
    - `notClippedByAncestor`: **false**
    - `isActuallyVisible`: **false**
  - 우측 FTC 패널 대표 수치 (`heroStat`):
    - `elementRect`: `left: 1343, top: 319, right: 1538, bottom: 343`
    - `visibleIntersectionRect`: `left: 1343, top: 319, right: 1440, bottom: 343, width: 97, height: 24`
    - `isActuallyVisible`: **true**
- **판정 및 결함 확정 (FAIL)**:
  - 데스크톱 기본 화면에서 좌측 요약 패널의 높이가 480px로 고정 클리핑되어 있어, 스크롤을 내리지 않으면 1위 브랜드 카드(메가MGC커피)가 물리적으로 가려져 있습니다.
  - 따라서 **메가MGC커피 행과 우측 FTC 대표 매출을 스크롤 조작 없이 단일 화면에서 동시에 육안 식별하는 것이 불가능함(동시 노출 불가)**을 확인했습니다.
  - 이는 감사 실패가 아닌 **제품 정보구조/레이아웃 결함(`DEF-PRODUCT-LAYOUT-01`)**으로 확정 기록합니다.

### 4.2 [시나리오 E] 모바일 축소 피크 실측
- **환경**: CSS 뷰포트 390×844, DPR 3, 전국(00), 한식(CAT_MAJ_01), 2024년
- **캡처 증빙**: [`phase5d_step1_audit_r3_mobile_peek.png`](file:///d:/Franchise_Dashboard/reports/phase5d_step1_audit_r3_mobile_peek.png)
- **실측치 대사표**:
  - **초기 진입 상태 (공정위 버튼 클릭 전)**:
    - 패널 클래스: `ftc-benchmark-panel drawer-closed mobile-collapsed`
    - 피크 바 rect: `top: 845, bottom: 888` (뷰포트 844px 아래 수납)
    - `isActuallyVisible`: **false**
    - **초기 수납 결함 확인**: 모바일 접속 시 피크 바가 기본 수납되어 상단 공정위 버튼을 누르기 전까지 화면에 나타나지 않음.
  - **사용자 조작 후 (상단 필터바 '공정위 2024' 버튼 클릭 후)**:
    - 패널 클래스: `ftc-benchmark-panel drawer-open mobile-collapsed`
    - 피크 바 rect: `left: 0, top: 781, right: 390, bottom: 824, width: 390, height: 43`
    - 조상 클리핑: `<aside class="ftc-benchmark-panel">` (`top: 780, bottom: 844, height: 64`)
    - `visibleIntersectionRect`: `top: 781, bottom: 824, width: 390, height: 43`
    - `isActuallyVisible`: **true**
  - **피크 바 텍스트 분석**:
    - 노출 문자열: `🍚 한식 중위매출 33,061만원 2024년 등록 (2023년 결산) ▲ 차트/상세 ✕`
    - `공정위`: **미포함 (false)**
    - `전국`: **미포함 (false)**
    - `업종 참고치`: **미포함 (false)**
    - `특정 브랜드 실적 아님`: **미포함 (false)**
- **판정**: 가시성 Assertion **PASS** (버튼 조작 후 뷰포트 내 안착 육안 확인 완료), **의미론적 4대 키워드 결손 결함(DEF-03) 확정**.

### 4.3 [시나리오 F] 모바일 확장 상태 실측
- **환경**: CSS 뷰포트 390×844, 전국(00), 한식(CAT_MAJ_01), 2024년, 확장 상태
- **캡처 증빙**: [`phase5d_step1_audit_r3_mobile_expanded.png`](file:///d:/Franchise_Dashboard/reports/phase5d_step1_audit_r3_mobile_expanded.png)
- **실측치 대사표**:
  - 패널 클래스: `ftc-benchmark-panel drawer-open mobile-expanded`
  - 패널 Bounding Rect: `top: 244, bottom: 844, height: 600` (뷰포트 교차 높이: **600px**)
  - 대표 매출 수치 (`heroStat`):
    - `elementRect`: `left: 23, top: 386, right: 195, bottom: 407, width: 172, height: 21`
    - `visibleIntersectionRect`: `left: 23, top: 386, right: 195, bottom: 407, width: 172, height: 21`
    - `isActuallyVisible`: **true**
  - 푸터 메타/면책 영역 (`footerMeta`):
    - `elementRect`: `top: 1545px` (뷰포트 844px 대비 **701px 아래 매몰**)
    - `isActuallyVisible`: **false** (스크롤 전 첫 화면 비가시)
- **판정**: 가시성 Assertion **PASS** (패널 및 히어로 대표 수치가 뷰포트 상단에 정상 렌더링됨), **출처 및 면책 고지 첫 화면 매몰 결함(DEF-04) 확정**.

### 4.4 [시나리오 G] 모바일 지역·업종 피크 실측
- **환경**: CSS 뷰포트 390×844, 서울특별시 광진구(11215), 카페·음료(CAT_MAJ_07), 2024년
- **캡처 증빙**: [`phase5d_step1_audit_r3_mobile_regional.png`](file:///d:/Franchise_Dashboard/reports/phase5d_step1_audit_r3_mobile_regional.png)
- **실측치 대사표**:
  - 공정위 버튼 클릭 후 피크 바 rect: `left: 0, top: 781, right: 390, bottom: 824, width: 390, height: 43`
  - `isActuallyVisible`: **true**
  - 피크 바 텍스트: `☕ 카페·음료 중위매출 16,149만원 2024년 등록 (2023년 결산) ▲ 차트/상세 ✕`
  - 키워드 포함 여부: `광진구` 미포함, `전국` 미포함, `업종 참고치` 미포함
- **판정**: 가시성 Assertion **PASS**, **광진구 카페 평균 매출로 직관적 오인 가능성 높음(DEF-02 모바일) 확정**.

---

## 5. 모바일 에뮬레이션 정밀 메트릭 대사표

| 메트릭 항목 | CDP 요청값 | 브라우저 런타임 실측값 | 이미지 파일 실제 픽셀 | 배율 일치 여부 |
| :--- | :---: | :---: | :---: | :---: |
| 뷰포트 너비 | 390 px | `window.innerWidth: 390` | 1,170 px (390 × 3) | **정상 일치** |
| 뷰포트 높이 | 844 px | `window.innerHeight: 844` | 2,532 px (844 × 3) | **정상 일치** |
| 디바이스 픽셀 비율 | 3.0 | `window.devicePixelRatio: 3` | - | **정상 일치** |

---

## 6. 애플리케이션 코드 및 환경 무변경 검증

감사 수행 전후 `git status --porcelain` 명령을 통해 소스 코드 무수정 상태를 엄격히 확인하였습니다.

```powershell
git status --porcelain
# 결과: 애플리케이션 기능 코드(frontend/src/**, src/**, package.json 등) 수정 0건 확인
```

---

## 7. R3 감사 결론 및 최종 의견

1. **감사 수행 무결성 완료**: 조상 클리핑 및 뷰포트 가시성을 엄격히 계산하는 R3 감사 스크립트를 통해 모든 수치와 캡처가 100% 원시 사실과 일치함을 입증했습니다.
2. **시나리오 C 결과**: 좌측 1위 브랜드 행이 사이드바 클리핑 아래 매몰되어 데스크톱 기본 화면에서 **동시 노출이 불가함(FAIL)**을 명확한 제품 레이아웃 결함으로 보고합니다.
3. **시나리오 E·F·G 결과**: 상단 공정위 버튼 클릭 시 피크 바와 확장 패널의 실제 가시성(**PASS**)을 확보하였으나, 초기 수납 상태 및 의미론적 키워드 결손 결함(DEF-01~04)이 존재함을 객관적으로 기록했습니다.
4. **Step 5D-2 승인 요청**: Step 5D-1 감사의 모든 사실 확인이 완벽히 종료되었으므로, **Step 5D-2(UI 레이아웃 및 의미 안전성 문구 개선) 작업 착수 승인을 요청**드립니다.
