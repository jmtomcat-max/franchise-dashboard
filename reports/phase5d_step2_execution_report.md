# Phase 5D Step 5D-2 의미 안전성 보완 구현 실행보고서 (증빙 정정 R1)

> **문서 상태**: 증빙 정정 및 8대 시나리오 전수 재검증 완료 (ALL PASS)  
> **수행 일시**: 2026-10-16 15:30:00 ~ 15:35:00 (KST)  
> **기준 지침**: [`gravity_handoff_phase5d_step2_evidence_correction_r1.md`](file:///d:/Franchise_Dashboard/gravity_handoff_phase5d_step2_evidence_correction_r1.md)  
> **구현 계획**: [`reports/phase5d_step2_semantic_safety_remediation_plan_r1.md`](file:///d:/Franchise_Dashboard/reports/phase5d_step2_semantic_safety_remediation_plan_r1.md)  
> **원시 검증 데이터**: [`reports/phase5d_step2_validation.json`](file:///d:/Franchise_Dashboard/reports/phase5d_step2_validation.json)  
> **검증 스크립트**: [`scratch/verify_phase5d_step2_semantic_safety.mjs`](file:///d:/Franchise_Dashboard/scratch/verify_phase5d_step2_semantic_safety.mjs)  

---

## 1. 개요 및 증빙 정정 목적

본 보고서는 **Phase 5D Step 5D-2 증빙 정정 지침 R1**에 따라, 기존 검증 스크립트에서 초기 지역 상태(기본값 서울특별시 광진구)로 인해 전국 시나리오의 실제 선택 상태가 광진구로 실행되었던 결함을 교정하고, 8대 시나리오를 전수 새로 실행하여 **원시 JSON, 화면 캡처, 실행보고서, 품질보고서 간의 조건과 실측 결과를 100% 일치**시킨 증빙 정정 보고서입니다.

- **수정 범위 엄격 제한**:
  - `frontend/src/**`, 백엔드 API, DB, 수집 로직, 기존 보호 파일은 일체 수정하지 않았습니다(제품 코드 변경 0건).
  - `scratch/verify_phase5d_step2_semantic_safety.mjs`의 지역 선택 대기 및 단언 로직만 교정하여 신규 검증 및 캡처를 생성했습니다.
  - 감정적이거나 과장된 절대 표현(`완벽히 차단`, `원천 차단` 등)을 배제하고, 실측된 수치와 사실만 기술했습니다.

---

## 2. 보호 대상 파일 무결성 검증

프로젝트 절대 보호 대상 3종 파일에 대해 SHA-256 해시를 대조하였으며, 작업 전 기준선과 100% 동일함을 확인했습니다.

| 대상 파일 | 기준선 SHA-256 | 사후 측정 SHA-256 | 파일 크기 | 무결성 판정 |
| :--- | :--- | :--- | :---: | :---: |
| [`collector.py`](file:///d:/Franchise_Dashboard/collector.py) | `341BAC12BB0AF58DCBDEBBA9459033521F27DF9817E35BAD8B21A4D07BA3369C` | `341BAC12BB0AF58DCBDEBBA9459033521F27DF9817E35BAD8B21A4D07BA3369C` | 3,780 B | **일치 (PASS)** |
| [`gangnam_food_stores.sqlite3`](file:///d:/Franchise_Dashboard/gangnam_food_stores.sqlite3) | `FEE3B58651CFED5C390C0B95DB02B05EBE92DF18619A06F4E399D429236F3A78` | `FEE3B58651CFED5C390C0B95DB02B05EBE92DF18619A06F4E399D429236F3A78` | 15,831,040 B | **일치 (PASS)** |
| [`run_gangnam.bat`](file:///d:/Franchise_Dashboard/run_gangnam.bat) | `0582C3A1AE53450DDC482E9BF538510780CA2F14D44E987CC753D4E12C816491` | `0582C3A1AE53450DDC482E9BF538510780CA2F14D44E987CC753D4E12C816491` | 66 B | **일치 (PASS)** |

---

## 3. 검증 스크립트 정정 내역

[`scratch/verify_phase5d_step2_semantic_safety.mjs`](file:///d:/Franchise_Dashboard/scratch/verify_phase5d_step2_semantic_safety.mjs):
1. **명시적 지역 선택 강제**:
   - S1, S3, S4, S8에서 화면 초기화 직후 `await selectRegion('00', '')`를 명시적으로 실행하여 전국 상태를 확립했습니다.
   - S5는 S4에서 이어지는 실제 전국 상태(`sidoValue: '00'`)임을 재확인했습니다.
   - S2, S6에서는 `await selectRegion('11', '11215')`를 실행하여 서울특별시 광진구 상태를 확립했습니다.
2. **비동기 옵션 로드 및 반영 대기**:
   - `fetchRegions` API 응답 대기: 시도 선택 전 `#sido-select option[value="${sidoVal}"]`가 DOM에 렌더링될 때까지 대기(최대 8초).
   - 전국('00') 선택 시: `#sigungu-select`가 `disabled || value === ''`가 될 때까지 대기(최대 5초).
   - 특정 시군구('11215') 선택 시: 해당 option이 로드된 후 선택하고, value 반영이 완료될 때까지 대기(최대 5초).
3. **지역 상태 정밀 단언 및 원시 JSON 기록**:
   - 각 시나리오의 측정 블록에 `sidoValue`, `sidoText`, `sigunguValue`, `sigunguText`, `actualRegion`을 수집하여 기록했습니다.
   - 전국 시나리오는 `sidoValue === '00'` 및 `(!sigunguValue || sigunguDisabled)`일 때만 PASS로 판정했습니다.
   - 광진구 시나리오는 `sidoValue === '11'` 및 `sigunguValue === '11215'`일 때만 PASS로 판정했습니다.
   - 지역 상태 단언 실패 시 해당 시나리오와 `overallPass`가 false가 되도록 처리했습니다.

---

## 4. 8대 필수 시나리오 정정 검증 결과 총괄표

| ID | 시나리오 명칭 | 해상도 | 요청 조건 | 기대 지역 상태 | 실제 지역 상태 (실측) | 의미 안전성 / 가시성 판정 | 최종 판정 | 증빙 캡처 |
| :---: | :--- | :---: | :--- | :---: | :---: | :--- | :---: | :--- |
| **1** | 데스크톱 전국·카페·2024 | 1440×900 | 전국 / 카페·음료 / 2024 | 전국 (`00`) | **전국 (`00`)** | 전국 중앙값 라벨 & 비귀속 상시 안내 가시 | **PASS** | [`S1 캡처`](file:///d:/Franchise_Dashboard/reports/phase5d_step2_s1_desktop_cafe_2024.png) |
| **2** | 데스크톱 광진구·치킨·2024 | 1440×900 | 광진구 / 치킨 / 2024 | 광진구 (`11215`) | **서울 광진구 (`11`/`11215`)** | 지역 모드에서 전국 거시 라벨 및 비귀속 고지 | **PASS** | [`S2 캡처`](file:///d:/Franchise_Dashboard/reports/phase5d_step2_s2_desktop_gwangjin_chicken.png) |
| **3** | 데스크톱 전국·한식·2026 | 1440×900 | 전국 / 한식 / 2026 | 전국 (`00`) | **전국 (`00`)** | 호버 없는 2026 스냅샷 상시 인라인 경고 | **PASS** | [`S3 캡처`](file:///d:/Franchise_Dashboard/reports/phase5d_step2_s3_desktop_korean_2026_snapshot.png) |
| **4** | 모바일 전국·한식·2024 피크 | 390×844 | 전국 / 한식 / 2024 (피크) | 전국 (`00`) | **전국 (`00`)** | `공정위 전국`, `중위 3.31억`, `(업종 참고치)`, H: 64px | **PASS** | [`S4 캡처`](file:///d:/Franchise_Dashboard/reports/phase5d_step2_s4_mobile_korean_2024_peek.png) |
| **5** | 모바일 전국·한식·2024 확장 | 390×844 | 전국 / 한식 / 2024 (확장) | 전국 (`00`) | **전국 (`00`)** | 첫 844px 내 콤팩트 공지 배너 + 대표 수치 가시 | **PASS** | [`S5 캡처`](file:///d:/Franchise_Dashboard/reports/phase5d_step2_s5_mobile_korean_2024_expanded.png) |
| **6** | 모바일 광진구·카페·2024 피크 | 390×844 | 광진구 / 카페 / 2024 (피크) | 광진구 (`11215`) | **서울 광진구 (`11`/`11215`)** | 지역 모드 피크 바 `공정위 전국` 및 참고치 고지 | **PASS** | [`S6 캡처`](file:///d:/Franchise_Dashboard/reports/phase5d_step2_s6_mobile_gwangjin_cafe_peek.png) |
| **7** | 키보드 상호작용 검증 | 데스크톱/모바일 | 공정위 버튼, 피크 바 | - | - | Enter 열기, ESC 닫기, 바텀시트 Enter 토글 | **PASS** | [`S7 캡처`](file:///d:/Franchise_Dashboard/reports/phase5d_step2_s7_keyboard_interaction.png) |
| **8** | 모바일 가로 오버플로 0 | 390×844 | 전국 / 한식 / 2024 | 전국 (`00`) | **전국 (`00`)** | 피크 & 확장 `docScrollWidth = 390px`, 오버플로 0 | **PASS** | 원시 JSON 기록 |

---

## 5. 시나리오별 상세 실측 데이터

### 5.1 [시나리오 1] 데스크톱 전국·카페·2024
- **실제 지역 상태**: `sidoValue: "00"`, `sidoText: "전국"`, `sigunguValue: ""`, `sigunguDisabled: true`, `actualRegion: "전국"` (일치)
- **히어로 대표 라벨 (`.hero-label`)**:
  - 텍스트: `"전국 가맹본부 대표매출 (중앙값)"`
  - `elementRect`: `left: 1036, top: 298, right: 1205, bottom: 314, width: 169, height: 16`
  - `isActuallyVisible`: `true`
- **히어로 비귀속 안내 (`.hero-scope-disclaimer`)**:
  - 텍스트: `"* 공정위 정기공시 전국 카페·음료 가맹본부 기준 거시 통계이며, 특정 브랜드나 개별 점포의 실적이 아닙니다."`
  - `elementRect`: `left: 1036, top: 352, right: 1395, bottom: 388, width: 360, height: 36`
  - `isActuallyVisible`: `true`
- **화면 캡처 대조**: 좌측 상단 지역 선택기가 `전국`으로 정확히 표시됨을 확인.

### 5.2 [시나리오 2] 데스크톱 광진구·치킨·2024
- **실제 지역 상태**: `sidoValue: "11"`, `sidoText: "서울"`, `sigunguValue: "11215"`, `sigunguText: "광진구"`, `actualRegion: "서울 서울특별시 광진구"` (일치)
- **히어로 대표 라벨 (`.hero-label`)**:
  - 텍스트: `"전국 가맹본부 대표매출 (중앙값)"` (지역 선택 상태에서도 전국 거시 모집단임을 명시)
  - `isActuallyVisible`: `true`
- **히어로 비귀속 안내 (`.hero-scope-disclaimer`)**:
  - 텍스트: `"* 공정위 정기공시 전국 치킨·패스트푸드 가맹본부 기준 거시 통계이며, 특정 브랜드나 개별 점포의 실적이 아닙니다."`
  - `isActuallyVisible`: `true`
- **화면 캡처 대조**: 좌측 상단 지역 선택기가 `서울 / 광진구`로 정확히 표시됨을 확인.

### 5.3 [시나리오 3] 데스크톱 전국·한식·2026
- **실제 지역 상태**: `sidoValue: "00"`, `sigunguValue: ""`, `actualRegion: "전국"` (일치)
- **인라인 경고 박스 (`.snapshot-inline-alert`)**:
  - 텍스트: `"⚠️ 진행형 스냅샷: 2026년은 정기공시 진행 중(약 30% 미등록 결손)으로 2025년과 직접 비교가 불가합니다."`
  - `elementRect`: `left: 1024, top: 254, right: 1408, bottom: 289, width: 384, height: 35`
  - `isActuallyVisible`: `true` (호버 조작 없이 초기 화면에 즉시 노출)
- **화면 캡처 대조**: 지역 선택기 `전국` 표시 및 패널 상단 앰버 경고 박스 상시 노출 확인.

### 5.4 [시나리오 4] 모바일 전국·한식·2024 피크 바 (390×844)
- **실제 지역 상태**: `sidoValue: "00"`, `actualRegion: "전국"` (일치)
- **태그 (`.mobile-summary-tag`)**: 텍스트 `"공정위 전국"`, `isActuallyVisible: true`
- **수치 (`.mobile-summary-kpi`)**: 텍스트 `"중위 3.31억"`, `isActuallyVisible: true`
- **참고치 라벨 (`.mobile-summary-sub`)**: 텍스트 `"(업종 참고치)"`, `isActuallyVisible: true`
- **피크 바 패널 높이**: `elementRect.height = 64px` (기존 높이 유지)
- **문서 스크롤 너비**: `scrollWidth = 390px` (가로 오버플로 0)

### 5.5 [시나리오 5] 모바일 전국·한식·2024 확장 상태 (390×844)
- **실제 지역 상태**: S4에서 이어진 `sidoValue: "00"`, `actualRegion: "전국"` 상태 확인
- **최상단 콤팩트 공지 배너 (`.mobile-first-screen-notice`)**:
  - 텍스트: `"📌 공정위 정기공시 전국 가맹본부 거시 벤치마크 (개별 점포·특정 브랜드 실적 아님)"`
  - `elementRect`: `left: 10, top: 405, right: 380, bottom: 437, width: 370, height: 32`
  - `isActuallyVisible`: `true` (스크롤 전 첫 844px 뷰포트 내 안착)
- **대표 매출 수치 (`.hero-stat-number`)**:
  - `elementRect`: `left: 23, top: 494, right: 280, bottom: 521, width: 257, height: 27`
  - `isActuallyVisible`: `true` (공지 배너 추가에도 첫 화면에서 화면 밖으로 밀리지 않음)

### 5.6 [시나리오 6] 모바일 광진구·카페·2024 피크 바 (390×844)
- **실제 지역 상태**: `sidoValue: "11"`, `sigunguValue: "11215"`, `actualRegion: "서울 서울특별시 광진구"` (일치)
- 지역(광진구) 선택 상태에서도 피크 바에 `[공정위 전국]` 태그와 `(업종 참고치)` 라벨이 노출되어 전국 거시 수치임을 전달 (`isActuallyVisible: true`).
- **화면 캡처 대조**: 상단 필터바에 `서울 / 광진구` 표시 및 하단 피크 바 정상 안착 확인.

### 5.7 [시나리오 7] 키보드 상호작용 검증
- 데스크톱 공정위 버튼 `Enter` 입력: `drawer-open` 전환 확인.
- `Escape` 입력: `drawer-closed` 전환 확인.
- 모바일 피크 바 핸들 `Enter` 입력: `mobile-expanded` 확장 확인.
- 다시 `Enter` 입력: `mobile-collapsed` 축소 확인.

### 5.8 [시나리오 8] 390×844 문서 가로 오버플로 0 종합 측정
- **실제 지역 상태**: `sidoValue: "00"`, `actualRegion: "전국"` (일치)
- 피크 바 상태: `docScrollWidth = 390px`, `bodyScrollWidth = 390px`, 패널 가로 초과 0건.
- 확장 패널 상태: `docScrollWidth = 390px`, `bodyScrollWidth = 390px`, 패널 가로 초과 0건.

---

## 6. 재검증 명령 실행 결과

지침에 명시된 재검증 명령 3종을 순차 실행했습니다.

```powershell
# 1. JSON 검증
node -e "const fs=require('fs');const j=JSON.parse(fs.readFileSync('reports/phase5d_step2_validation.json','utf8'));if(!j.overallPass||j.scenarios.length!==8)process.exit(1);console.log('JSON PASS',j.scenarios.length)"
# 출력: JSON PASS 8

# 2. 프론트엔드 빌드 검증
npm.cmd --prefix frontend run build
# 출력: vite v5.4.21 building for production... ✓ built in 20.52s (오류 0건)

# 3. 보호 파일 해시 검증
Get-FileHash -Algorithm SHA256 collector.py,gangnam_food_stores.sqlite3,run_gangnam.bat
# 출력: collector.py (341BAC12...), gangnam_food_stores.sqlite3 (FEE3B586...), run_gangnam.bat (0582C3A1...) 전원 일치
```

---

## 7. 결론

Phase 5D Step 5D-2 증빙 정정 작업을 완료하였으며, S1·S3·S4·S5·S8의 전국 지역 상태와 S2·S6의 광진구 지역 상태가 원시 JSON, 화면 캡처, 실행보고서 간에 오차 없이 일치함을 검증했습니다.
