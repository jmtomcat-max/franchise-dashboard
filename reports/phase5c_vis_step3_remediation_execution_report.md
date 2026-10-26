# Phase 5C-Vis Step 3 결함 수정(Remediation) 실행 보고서

**문서 경로**: `reports/phase5c_vis_step3_remediation_execution_report.md`  
**작성 일시**: 2026-10-16  
**원시 측정 데이터**: [`reports/phase5c_vis_step3_remediation_metrics.json`](file:///d:/Franchise_Dashboard/reports/phase5c_vis_step3_remediation_metrics.json)  
**수정 전 기준선**: [`reports/phase5c_vis_step3_remediation_baseline.json`](file:///d:/Franchise_Dashboard/reports/phase5c_vis_step3_remediation_baseline.json)  
**검증 브라우저**: Google Chrome 155.0.8059.81 (Headless with CDP, WebGL 2.0 하드웨어 가속)  
**준수 규격**: `AGENTS.md` (보호 대상 3대 파일 절대 보존, 8대 대분류 불변, 단계별 승인 절차)

---

## 1. 개요 및 결함 수정 배경

Phase 5C-Vis Step 3 초기 구현 및 검증 과정에서 도출된 결함(R-01: 모바일 터치 영역 미달, R-02: 모바일 제주시 조망 렌더링 누락, R-03: 업종 테마 전환 시 렌더링 누락, R-04: 배경 픽셀 분석에 의한 허위 PASS 판정 위험)을 해결하기 위해 수립된 **Phase 5C-Vis Step 3 결함 수정 계획서([`reports/phase5c_vis_step3_remediation_plan.md`](file:///d:/Franchise_Dashboard/reports/phase5c_vis_step3_remediation_plan.md))**의 6대 작업 단계(Stage A ~ Stage F)를 전수 수행하고 최종 PASS를 입증하였습니다.

---

## 2. 보호 대상 3대 자산 무결성 검증 (Stage A & Final)

수정 착수 전 baseline 측정치와 작업 완료 후 SHA-256 해시를 비교 대사한 결과, 단 1바이트의 변경 없이 100% 원형 보존되었음을 확인하였습니다.

| 파일명 | 크기 (Bytes) | SHA-256 해시 (Baseline vs Final 대사) | 변경 여부 |
| :--- | :---: | :--- | :---: |
| [`collector.py`](file:///d:/Franchise_Dashboard/collector.py) | 3,780 | `341BAC12BB0AF58DCBDEBBA9459033521F27DF9817E35BAD8B21A4D07BA3369C` | **일치 (보존)** |
| [`gangnam_food_stores.sqlite3`](file:///d:/Franchise_Dashboard/gangnam_food_stores.sqlite3) | 15,831,040 | `FEE3B58651CFED5C390C0B95DB02B05EBE92DF18619A06F4E399D429236F3A78` | **일치 (보존)** |
| [`run_gangnam.bat`](file:///d:/Franchise_Dashboard/run_gangnam.bat) | 66 | `0582C3A1AE53450DDC482E9BF538510780CA2F14D44E987CC753D4E12C816491` | **일치 (보존)** |

---

## 3. 결함 수정 전후 핵심 대비표 (Before vs After)

| 결함 ID | 결함 내용 | 수정 전 (Before) | 수정 후 (After 실측치) | 결과 |
| :---: | :--- | :--- | :--- | :---: |
| **R-01** | 모바일(390×844) 필터바 터치 영역 미달 | 드롭다운 높이 28px, 탭 높이 24px로 44×44px 미달 | 2행 구조 배치, **13개 컨트롤 전수 높이 44px 및 너비 58~138.8px 확보** | **해결** |
| **R-02** | 모바일 제주시 조망 격자 렌더링 누락 | 수신 1,351개이나 BBOX 미재계산으로 화면 렌더링 0개/4개 | `fitGridBounds` 도입, **수신 1,351 = 상태 1,351 = BBOX 1,351 = 렌더링 1,351** | **해결** |
| **R-03** | 업종 테마 전환 시 렌더링 누락 | 테마 전환 시 레이어 렌더링 0개/4개 | 테마 전환 후에도 **1,351개 고유 격자 렌더링 유지**, 8대 업종 범례 표출 | **해결** |
| **R-04** | 배경 픽셀 샘플링 기반 허위 PASS 위험 | 바다 배경색 RGB로 인해 0개 렌더링 시에도 PASS 가능성 | 픽셀 판정 완전 배제, **`queryRenderedFeatures` 고유 grid_id 1,351개 전수 검증 및 Mutation Test 통과** | **해결** |

---

## 4. 세부 실측 검증 데이터

### 4.1 모바일 390×844 필터바 터치 타깃 실측 (Stage B)
`CategoryFilterBar` 내 13개 전체 조작 요소의 `getBoundingClientRect()` 실측 결과, 전 요소가 `width >= 44.0px && height >= 44.0px` 기준을 충족하였습니다.

| 번호 | 요소 식별자 (`id`) | UI 요소 라벨 | 측정 너비 (px) | 측정 높이 (px) | 판정 기준 | 결과 |
| :---: | :--- | :--- | :---: | :---: | :---: | :---: |
| 1 | `sido-select` | 시도 드롭다운 | 58.0 | 44.0 | $\ge 44 \times 44$ | **PASS** |
| 2 | `sigungu-select` | 시군구 드롭다운 | 82.0 | 44.0 | $\ge 44 \times 44$ | **PASS** |
| 3 | `ftc-year-select` | 공정위 연도 드롭다운 | 100.2 | 44.0 | $\ge 44 \times 44$ | **PASS** |
| 4 | `ftc-drawer-btn` | 공정위 통계 패널 버튼 | 112.2 | 44.0 | $\ge 44 \times 44$ | **PASS** |
| 5 | `tab-CAT_MAJ_01` | 🍚 한식 | 76.6 | 44.0 | $\ge 44 \times 44$ | **PASS** |
| 6 | `tab-CAT_MAJ_02` | 🥟 중식 | 71.8 | 44.0 | $\ge 44 \times 44$ | **PASS** |
| 7 | `tab-CAT_MAJ_03` | 🍣 일식 | 71.8 | 44.0 | $\ge 44 \times 44$ | **PASS** |
| 8 | `tab-CAT_MAJ_04` | 🍝 양식·세계음식 | 118.0 | 44.0 | $\ge 44 \times 44$ | **PASS** |
| 9 | `tab-CAT_MAJ_05` | 🍗 치킨·패스트푸드 | 128.6 | 44.0 | $\ge 44 \times 44$ | **PASS** |
| 10 | `tab-CAT_MAJ_06` | 🍢 분식·간편식 | 107.4 | 44.0 | $\ge 44 \times 44$ | **PASS** |
| 11 | `tab-CAT_MAJ_07` | ☕ 카페·음료 | 96.8 | 44.0 | $\ge 44 \times 44$ | **PASS** |
| 12 | `tab-CAT_MAJ_08` | 🥐 베이커리·디저트 | 128.6 | 44.0 | $\ge 44 \times 44$ | **PASS** |
| 13 | `tab-CAT_MAJ_99` | 🔍 기타 외식 (미매핑) | 138.8 | 44.0 | $\ge 44 \times 44$ | **PASS** |

- **가로 오버플로**: `windowInnerWidth: 390px`, `scrollWidth: 390px`, **오버플로: 0px (PASS)**
- **인터랙션/접근성**: 첫 탭(`tab-CAT_MAJ_01`), 중간 탭(`tab-CAT_MAJ_05`), 마지막 탭(`tab-CAT_MAJ_99`) 클릭 및 키보드 포커스 시 `aria-selected="true"` 정상 반영 확인.
- **증빙 캡처**: [`phase5c_vis_step3_remediation_mobile_filter_touch_targets.png`](file:///d:/Franchise_Dashboard/reports/phase5c_vis_step3_remediation_mobile_filter_touch_targets.png)

---

### 4.2 모바일 제주시 조망 1,351개 100% 렌더링 복구 실측 (Stage C)
제주시(`50110`) 선택 시 `fitGridBounds`를 통해 카메라 줌 7.85, 피치 52.0°로 최적화 안착되어 전수 피처가 화면 내에 표출되었습니다.

| 검증 단계 | 측정 지표 | 실측 수량 | 판정 |
| :--- | :--- | :---: | :---: |
| 1. 백엔드 API 응답 | `data.length` | 1,351개 | **일치** |
| 2. 클라이언트 메모리 상태 | `window.__currentGridData.length` | 1,351개 | **일치** |
| 3. 뷰포트 지리 BBOX 내부 | BBOX 내 중심좌표 포함 점포수 | 1,351개 | **일치** |
| 4. MapLibre GPU 렌더링 | `overviewUniqueGridIds` | 1,351개 | **일치** |
| 5. 업종 테마 전환 후 렌더링 | `overviewUniqueGridIds` | 1,351개 | **유지** |
| 6. 범례 동적 전환 | 8대 업종별 색상 범례 표출 | 표출 확인 | **PASS** |

- **증빙 캡처 (기본 조망)**: [`phase5c_vis_step3_remediation_mobile_jeju_overview.png`](file:///d:/Franchise_Dashboard/reports/phase5c_vis_step3_remediation_mobile_jeju_overview.png)
- **증빙 캡처 (업종 테마)**: [`phase5c_vis_step3_remediation_mobile_category_theme.png`](file:///d:/Franchise_Dashboard/reports/phase5c_vis_step3_remediation_mobile_category_theme.png)

---

### 4.3 허위 PASS 차단 Mutation 검증 (Stage D)
단순 픽셀 판정을 배제하고 실제 렌더링 피처 카운트 assertion의 무결성을 입증하기 위해 의도적 변이(Mutation) 검증을 수행하였습니다.
1. **기댓값 불일치 포착**: 실측 1,351개에 대해 의도적 허위 기댓값(9,999) assertion 적용 시 예외 정상 포착 (`caught: PASS`).
2. **비존재 레이어 허위 렌더링 차단**: 비존재 레이어 질의 시 0개가 반환됨을 확인하고 가짜 기댓값(1,351) 검출 시 예외 정상 포착 (`caught: PASS`).

---

### 4.4 데스크톱 1440×900 무회귀 5대 시나리오 검증 (Stage E)

| 시나리오 | 검증 내용 | 실측 결과 | 판정 |
| :---: | :--- | :--- | :---: |
| **D1** | 제주시 전체 조망 | `overviewUniqueGridIds: 1,351개`, BBOX 내부 1,351개 | **PASS** |
| **D2** | 제주시 상세 줌인 | 3D 기둥 고유 수 219개, 팝업 및 호버 정상 | **PASS** |
| **D3** | 광진구 전체 조망 | `overview: 466개`, `columns: 466개` 전수 렌더링 | **PASS** |
| **D4** | 광진구 상세 줌인 | 3D 기둥 고유 수 117개, 팝업 및 호버 정상 | **PASS** |
| **D5** | 전국 빈 상태 | 데이터수 0개, 렌더링 기둥 0개, 빈 상태 안내 배지 표출 | **PASS** |

- **프로덕션 빌드**: `npm run build` 실행 결과 42개 모듈 트랜스파일 완료 및 빌드 성공 (종료코드 0).

---

## 5. 승인 외 기능 동결(Scope Freeze) 현황

사용자 지침에 따라 아래 기능들은 이번 결함 수정(Remediation)에서 확장하거나 임의 삭제하지 않고 **현 상태로 엄격 동결(FROZEN)** 하였습니다.

- **44px 슬림 맵 제어 레일 (`SlimMapRail`)**: `FROZEN`
- **2D 정사영 모드**: `FROZEN`
- **상단 호버 도킹 카드**: `FROZEN`
> ※ 상기 3종 기능의 영구 유지 또는 제거 여부는 향후 사용자 승인 및 피드백 절차를 통해 별도 결정됩니다.

---

## 6. 결론

Phase 5C-Vis Step 3의 4대 핵심 결함(R-01 ~ R-04)이 기술적, 시각적, 데이터 무결성 측면에서 전수 해결되었으며, 보호 대상 3대 파일의 불변성을 유지한 채 프로덕션 빌드 및 전 시나리오 검증을 100% 통과하였습니다.
