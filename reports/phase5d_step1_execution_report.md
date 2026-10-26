# Phase 5D Step 5D-1 실행 보고서: 공정위 패널 오인 가능성 실측 감사

- **작성일**: 2026-10-16
- **작업 경로**: `D:\Franchise_Dashboard`
- **상태**: **Step 5D-1 감사 완료 / Step 5D-2 수정 승인 대기**
- **근거 계획서**: [`reports/phase5d_ftc_semantic_safety_plan_r2.md`](file:///d:/Franchise_Dashboard/reports/phase5d_ftc_semantic_safety_plan_r2.md)
- **원시 감사 결과**: [`reports/phase5d_step1_semantic_audit.json`](file:///d:/Franchise_Dashboard/reports/phase5d_step1_semantic_audit.json)
- **기준선 해시 기록**: [`reports/phase5d_step1_baseline.json`](file:///d:/Franchise_Dashboard/reports/phase5d_step1_baseline.json)

---

## 1. 감사 개요 및 목적

본 보고서는 `phase5d_ftc_semantic_safety_plan_r2.md`에 명시된 **Step 5D-1(실제 연동 및 오인 가능성 감사)**을 수행한 현장 실측 결과를 기록합니다.  
**코드를 일체 수정하지 않은 원본 상태**에서 Chrome DevTools Protocol(CDP) 자동화를 통해 데스크톱(1440×900)과 모바일(390×844)의 실제 렌더링 화면을 전수 추출하고, **공정위 수치가 선택 브랜드 또는 선택 지역의 실적으로 오인될 가능성**을 집중 점검했습니다.

---

## 2. 보호 대상 자산 및 코드 무수정 무결성 검증

1. **보호 대상 3대 자산 SHA-256 검증 (100% 불변)**:
   - `collector.py`: `341bac12bb0af58dcbdebba9459033521f27df9817e35bad8b21a4d07ba3369c` (일치)
   - `gangnam_food_stores.sqlite3`: `fee3b58651cfed5c390c0b95db02b05ebe92df18619a06f4e399d429236f3a78` (일치)
   - `run_gangnam.bat`: `0582c3a1ae53450ddc482e9bf538510780ca2f14d44e987cc753d4e12c816491` (일치)
2. **코드 무수정 원칙 준수**:
   - 백엔드 API, SQLite DB, 프론트엔드 컴포넌트(`FtcBenchmarkPanel.jsx` 등)에 대한 기능 수정을 일체 진행하지 않고 현 상태 그대로 감사를 진행했습니다.

---

## 3. 경로별 실측 감사 결과 (7개 시나리오)

실측 스크립트: [`scratch/audit_phase5d_step1_semantic_safety.mjs`](file:///d:/Franchise_Dashboard/scratch/audit_phase5d_step1_semantic_safety.mjs)  
원시 데이터: [`reports/phase5d_step1_semantic_audit.json`](file:///d:/Franchise_Dashboard/reports/phase5d_step1_semantic_audit.json)

### 시나리오 1: 데스크톱 (1440×900) 전국 모드 + 카페·음료 업종
- **경로**: 전국(00) 선택, 카페·음료(CAT_MAJ_07), 2024년 기준
- **화면 캡처**: [`reports/phase5d_step1_audit_desktop_nationwide.png`](file:///d:/Franchise_Dashboard/reports/phase5d_step1_audit_desktop_nationwide.png)
- **실측 헤더**: `공정위 공식 가맹사업 거시통계 (전국 가맹본부 기준)`
- **실측 히어로**: `가맹점 연간 대표매출 (중앙값) 16,703만원 (1.67억원)`
- **오인 점검**:
  - `공정위`, `거시통계` 문구는 헤더에 존재하나, 히어로 카드 자체에는 "전국" 또는 "참고 기준" 단어가 빠져 있음.
  - "특정 브랜드 실적 아님" 문구는 첫 화면 및 전체 패널 어디에도 존재하지 않음 (`firstScreenHasNotBrand: false`).

### 시나리오 2: 데스크톱 (1440×900) 시군구 선택 (광진구) + 치킨·패스트푸드
- **경로**: 서울특별시 광진구(11215), 치킨·패스트푸드(CAT_MAJ_05), 2024년 기준
- **화면 캡처**: [`reports/phase5d_step1_audit_desktop_regional_gwangjin.png`](file:///d:/Franchise_Dashboard/reports/phase5d_step1_audit_desktop_regional_gwangjin.png)
- **좌측 패널**: `서울특별시 광진구 분석`
- **우측 FTC 패널**: `가맹점 연간 대표매출 (중앙값) 19,312만원 (1.93억원)`
- **오인 점검**:
  - 좌측 패널과 지도가 '광진구'에 집중된 상태에서 우측 패널의 히어로 카드가 "가맹점 연간 대표매출"로만 표기되어 광진구 점포의 평균 매출로 혼동될 위험이 매우 높음 (`DEF-02`).

### 시나리오 3: 데스크톱 (1440×900) 실제 브랜드 선택 경로 (광진구 카페 Top 1 메가MGC커피)
- **경로**: 서울 광진구(11215), 카페·음료(CAT_MAJ_07), 좌측 상위 브랜드 1위 메가MGC커피(33개소) 선택/포커스
- **화면 캡처**: [`reports/phase5d_step1_audit_desktop_brand_scenario.png`](file:///d:/Franchise_Dashboard/reports/phase5d_step1_audit_desktop_brand_scenario.png)
- **실측 화면 배치**:
  - 좌측 상위 브랜드 카드: `1위 메가MGC커피 33개소 (16.2%)`
  - 우측 FTC 패널 히어로: `가맹점 연간 대표매출 (중앙값) 16,703만원`
- **오인 점검**:
  - 두 카드가 한 화면에 공존하지만, 우측 수치가 **"메가MGC커피의 실적이 아니며 카페 업종 전국 거시 중위값임"**을 설명하는 브릿지 문구가 전혀 없음.
  - 일반 사용자는 1.67억원을 메가MGC커피의 연간 평균 매출로 해석할 위험이 명백함 (`DEF-01`).

### 시나리오 4: 데스크톱 (1440×900) 2026년 진행형 스냅샷 선택 상태
- **경로**: 전국(00), 한식(CAT_MAJ_01), 2026년 연도 막대 선택
- **화면 캡처**: [`reports/phase5d_step1_audit_desktop_snapshot_2026.png`](file:///d:/Franchise_Dashboard/reports/phase5d_step1_audit_desktop_snapshot_2026.png)
- **실측 배지**: `2026년 등록 (2025년 결산)`, `진행형 스냅샷`
- **오인 점검**:
  - '진행형 스냅샷' 배지가 노출되나, 핵심 제한 사항인 **"모집단 30% 미등록 결손으로 전년 직접 비교 불가"** 경고는 마우스 호버(title 툴팁)나 차트 하단 미세 각주에만 기재되어 있어 직관적 식별이 미흡함 (`DEF-05`).

### 시나리오 5: 모바일 (390×844) 바텀시트 축소(피크) 상태
- **경로**: 전국(00), 한식(CAT_MAJ_01), 바텀시트 피크 바
- **화면 캡처**: [`reports/phase5d_step1_audit_mobile_peek.png`](file:///d:/Franchise_Dashboard/reports/phase5d_step1_audit_mobile_peek.png)
- **피크 바 노출 텍스트**: `🍚 한식 중위매출 36,117만원 2026년 스냅샷 (2025년 결산) ▲ 차트/상세 ✕`
- **오인 점검**:
  - **공정위 키워드 누락 (0건)**
  - **전국 키워드 누락 (0건)**
  - **업종 벤치마크 / 참고 기준 누락 (0건)**
  - **특정 브랜드 실적 아님 누락 (0건)**
  - 모바일 지도 하단에 `한식 중위매출 3.61억원`만 표시되어 현재 지도 화면의 점포 실적으로 오인될 가능성이 가장 심각함 (`DEF-03, CRITICAL`).

### 시나리오 6: 모바일 (390×844) 바텀시트 확장 상태
- **경로**: 전국(00), 한식(CAT_MAJ_01), 바텀시트 전체 확장
- **화면 캡처**: [`reports/phase5d_step1_audit_mobile_expanded.png`](file:///d:/Franchise_Dashboard/reports/phase5d_step1_audit_mobile_expanded.png)
- **오인 점검**:
  - 바텀시트 확장 시 첫 844px 내에는 히어로 수치와 비교 바만 보이며, **출처 및 개별 매장 실측치 아님 면책 고지는 742px 아래(스크롤 필요)에 매몰**되어 있음 (`DEF-04`).

### 시나리오 7: 모바일 (390×844) 시군구(광진구) + 카페 업종 화면
- **경로**: 서울 광진구(11215), 카페·음료(CAT_MAJ_07), 모바일 지도 및 바텀시트
- **화면 캡처**: [`reports/phase5d_step1_audit_mobile_brand_scenario.png`](file:///d:/Franchise_Dashboard/reports/phase5d_step1_audit_mobile_brand_scenario.png)
- **오인 점검**:
  - 광진구 지도가 렌더링된 상태에서 하단 피크 바는 `카페·음료 중위매출 16,703만원`으로만 표시되어, 광진구 카페들의 중위매출로 명백히 오인됨.

---

## 4. 노출 위치 및 의미 안전성 전수 대사표

| 정보 항목 | 현재 노출 문구 | DOM 위치 | 첫 화면(스크롤 전) 노출 여부 | 오인 방지 적합성 |
|---|---|---|---|---|
| **패널 대표 제목** | `공정위 공식 가맹사업 거시통계 (전국 가맹본부 기준)` | `.panel-heading` (헤더 h3) | 데스크톱 O / 모바일 X (피크 바에 없음) | **보통** (소제목 형태라 히어로에 밀림) |
| **선택 업종 기준** | `☕ 카페·음료` | `.panel-category-badge` | 데스크톱 O / 모바일 O | **적합** |
| **브랜드 비귀속 고지** | **완전 부재 (0건)** | 없음 | **전 환경 X (미노출)** | **부적합 (심각한 결함)** |
| **전국 모집단 명시** | `(전국 가맹본부 기준)` (괄호 소제목) | `.panel-heading` | 데스크톱 O (작은 폰트) / 모바일 X | **미흡** (히어로 카드에 전국 단어 없음) |
| **데이터 출처** | `출처: 공정거래위원회 가맹사업정보제공시스템` | `.panel-footer-meta` (최하단) | **전 환경 X (스크롤 강제 매몰)** | **미흡** (데스크톱 49px, 모바일 742px 스크롤) |
| **모집단 면책 고지** | `집계단위: 전국 등록 가맹본부 거시 벤치마크 (개별 매장 실측치 아님)` | `.panel-footer-meta` (최하단) | **전 환경 X (스크롤 강제 매몰)** | **미흡** (첫 화면에서 인지 불가) |
| **등록/결산 연도** | `2024년 등록 (2023년 결산)` | `.panel-year-badge` | 데스크톱 O / 모바일 O | **적합** |
| **2026 스냅샷 상태** | `진행형 스냅샷` (배지) | `.badge-snapshot-amber` | 데스크톱 O / 모바일 O | **보통** (결손율 설명은 툴팁에 은폐) |

---

## 5. 결론 및 승인 대기

본 Step 5D-1 감사를 통해, 현재 대시보드는 **공정위 거시 수치가 선택 브랜드(메가커피 등) 또는 선택 지역(광진구 등)의 고유 실적으로 오인될 수 있는 구조적 결함(DEF-01 ~ DEF-04)**을 안고 있음을 실제 화면 캡처와 수치로 입증했습니다.

`AGENTS.md` 및 `phase5d_ftc_semantic_safety_plan_r2.md` 지침에 따라 **Step 5D-2 수정 작업은 착수하지 않고 사용자 승인을 기다립니다.**
