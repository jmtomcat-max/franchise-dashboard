# Phase 5D Step 5D-2 품질 및 의미 안전성 검증보고서 (증빙 정정 R1)

> **문서 상태**: 증빙 정정 및 전수 재검증 완료 (사용자 승인 대기)  
> **기준 지침**: [`gravity_handoff_phase5d_step2_evidence_correction_r1.md`](file:///d:/Franchise_Dashboard/gravity_handoff_phase5d_step2_evidence_correction_r1.md)  
> **검증 기준 문서**: [`reports/phase5d_step2_semantic_safety_remediation_plan_r1.md`](file:///d:/Franchise_Dashboard/reports/phase5d_step2_semantic_safety_remediation_plan_r1.md)  
> **원시 검증 데이터**: [`reports/phase5d_step2_validation.json`](file:///d:/Franchise_Dashboard/reports/phase5d_step2_validation.json)  
> **실행보고서**: [`reports/phase5d_step2_execution_report.md`](file:///d:/Franchise_Dashboard/reports/phase5d_step2_execution_report.md)  

---

## 1. 품질 검증 요약

Phase 5D Step 5D-2 증빙 정정 지침 R1에 따라 8개 시나리오를 전수 재실행하고 12개 인수 기준에 대해 정밀 검증을 완료했습니다. **전 항목에서 100% PASS**를 기록했습니다.

| 구분 | 인수 기준 항목 | 검증 방식 | 실측 결과 | 판정 |
| :---: | :--- | :--- | :--- | :---: |
| **지역 상태 일치** | S1·S3·S4·S5·S8 실제 전국 상태 | DOM value 및 text 대조 | `sidoValue: '00'`, `sigunguValue: ''`, `actualRegion: '전국'` | **PASS** |
| **지역 상태 일치** | S2·S6 실제 광진구 상태 | DOM value 및 text 대조 | `sidoValue: '11'`, `sigunguValue: '11215'`, `actualRegion: '서울 광진구'` | **PASS** |
| **의미 안전성** | 데스크톱 히어로 `전국` 문구 노출 | CDP element text & rect | `"전국 가맹본부 대표매출 (중앙값)"` 실제 노출 (`top: 298px`) | **PASS** |
| **의미 안전성** | 비귀속 안내문 첫 화면 상시 노출 | 조상 클리핑 가시성 검사 | `.hero-scope-disclaimer` 상시 가시 (`top: 352px`) | **PASS** |
| **의미 안전성** | 2026 경고 호버 없이 상시 노출 | 렌더링 즉시 DOM & style | `.snapshot-inline-alert` 호버 불필요 노출 (`#fffbeb`, `top: 254px`) | **PASS** |
| **모바일 안전성** | 피크 바 `공정위`, `전국`, `업종 참고치` 노출 | 390px 뷰포트 CDP 가시성 | `[공정위 전국]`, `(업종 참고치)` 실제 가시 | **PASS** |
| **모바일 안전성** | 모바일 피크 수치 억 단위 축약 | textContent 검증 | `중위 3.31억` (`formatEokShort`) 적용 확인 | **PASS** |
| **모바일 안전성** | 모바일 확장 첫 화면 비귀속 배너 노출 | 첫 844px 뷰포트 안착 | `.mobile-first-screen-notice` (`top: 405px`, H: 32px) | **PASS** |
| **레이아웃** | 모바일 390×844 가로 오버플로 0 | `scrollWidth` 정밀 측정 | 피크 `390px`, 확장 `390px` (초과 0px) | **PASS** |
| **레이아웃** | 모바일 초기 수납 및 지도 비차폐 유지 | 초기 진입 translateY 검증 | `drawer-closed` 시 `translateY(100%)` (0px 차폐 유지) | **PASS** |
| **접근성** | 키보드 조작 회귀 없음 | 순차 키 이벤트 발송 | Enter 열기, ESC 닫기, 바텀시트 Enter 토글 PASS | **PASS** |
| **무결성** | 보호 대상 파일 3종 SHA-256 불변 | SHA-256 전후 대조 | `collector.py`, `sqlite3`, `bat` 100% 일치 | **PASS** |

---

## 2. 지역 상태 추적 및 증빙 정합성 분석

### 2.1 결함 원인 분석 및 교정
- **기존 결함**: React 앱 초기 상태(`selectedSido: '11'`, `selectedSigungu: '11215'`)에서 전국 시나리오 실행 시 `selectRegion('00', '')`를 명시적으로 호출하지 않았거나, 비동기 옵션 로드 지연으로 인해 실제 렌더링 상태가 광진구로 유지된 상태에서 캡처가 기록되었음.
- **교정 조치**:
  1. 각 시나리오 시작 시 `selectRegion`을 명시적으로 실행.
  2. 시도 및 시군구 옵션이 API로부터 로드될 때까지 비동기 대기(`while (Date.now() - start < 8000)`)를 적용.
  3. 시도 및 시군구 DOM의 `selectedOptions[0].text`와 `value`를 직접 읽어 `sidoValue`, `sidoText`, `sigunguValue`, `sigunguText`, `actualRegion`을 추출하고 원시 JSON에 기록.
  4. 단언 조건에 지역 상태를 포함하여 불일치 시 즉시 실패하도록 강제.

### 2.2 시나리오별 기대 상태 vs 실제 상태 대조

| 시나리오 | 기대 지역 | 실제 시도코드 (`sidoValue`) | 실제 시군구코드 (`sigunguValue`) | 실제 지역 표기 (`actualRegion`) | 일치 여부 |
| :---: | :---: | :---: | :---: | :---: | :---: |
| **S1 (데스크톱 전국 카페)** | 전국 | `00` | `""` (disabled) | 전국 | **일치** |
| **S2 (데스크톱 광진구 치킨)** | 광진구 | `11` | `11215` | 서울 서울특별시 광진구 | **일치** |
| **S3 (데스크톱 전국 한식)** | 전국 | `00` | `""` (disabled) | 전국 | **일치** |
| **S4 (모바일 피크 전국 한식)** | 전국 | `00` | `""` (disabled) | 전국 | **일치** |
| **S5 (모바일 확장 전국 한식)** | 전국 | `00` | `""` (disabled) | 전국 | **일치** |
| **S6 (모바일 피크 광진구 카페)** | 광진구 | `11` | `11215` | 서울 서울특별시 광진구 | **일치** |
| **S7 (키보드 상호작용)** | - | - | - | - | - |
| **S8 (모바일 가로 오버플로 0)** | 전국 | `00` | `""` (disabled) | 전국 | **일치** |

모든 시나리오의 기대 조건과 실제 DOM 상태, 캡처된 화면상의 선택기 표시가 100% 일치함을 확인했습니다.

---

## 3. 의미 안전성(Semantic Safety) 실측 결과

### 3.1 데스크톱 환경 실측
- **전국 범위 모집단 명시**:
  - 히어로 카드 라벨이 `"전국 가맹본부 대표매출 (중앙값)"`으로 노출되어 전국 거시 수치임을 알림 (`isActuallyVisible: true`, S1: `top 298px`, S2: `top 298px`).
  - S2(지역 선택 모드)에서도 히어로 라벨이 `전국`으로 유지되어 선택 지역 매장의 실적이 아님을 나타냄.
- **비귀속 상시 안내문 (`.hero-scope-disclaimer`)**:
  - 문구: `"* 공정위 정기공시 전국 {업종명} 가맹본부 기준 거시 통계이며, 특정 브랜드나 개별 점포의 실적이 아닙니다."`
  - S1(카페) 및 S2(치킨) 모두에서 `top: 352px`에 상시 가시됨을 실측 확인 (`isActuallyVisible: true`).
- **2026 진행형 스냅샷 경고 (`.snapshot-inline-alert`)**:
  - 문구: `"⚠️ 진행형 스냅샷: 2026년은 정기공시 진행 중(약 30% 미등록 결손)으로 2025년과 직접 비교가 불가합니다."`
  - S3에서 마우스 호버 없이 렌더링 즉시 표출됨을 확인 (`top: 254px`, H: 35px, `isActuallyVisible: true`).

### 3.2 모바일 환경 실측 (390×844)
- **모바일 피크 바 (S4, S6)**:
  - `[공정위 전국]` 태그와 `(업종 참고치)` 보조 라벨이 실제 노출됨 (`isActuallyVisible: true`).
  - `중위 3.31억` (`formatEokShort`) 억 단위 축약이 적용되어 390px 뷰포트에서 줄바꿈 없이 단일 행(높이 64px)을 유지함.
  - S4 및 S6의 문서 스크롤 너비는 모두 `390px`로 가로 오버플로 0px를 기록함.
- **모바일 확장 패널 첫 화면 (S5)**:
  - 패널 최상단에 32px 슬림 배너(`.mobile-first-screen-notice`)가 배치되어 스크롤 전 첫 화면(`top: 405px`) 내에서 가시성 확보 (`isActuallyVisible: true`).
  - 대표 매출 수치(`top: 494px`)와 3대 지표 비교 바 역시 첫 화면 내에 유지됨.

---

## 4. 재검증 명령 검증 증빙

```powershell
# 1. JSON 검증
node -e "const fs=require('fs');const j=JSON.parse(fs.readFileSync('reports/phase5d_step2_validation.json','utf8'));if(!j.overallPass||j.scenarios.length!==8)process.exit(1);console.log('JSON PASS',j.scenarios.length)"
# 결과: JSON PASS 8

# 2. 프로덕션 빌드 검증
npm.cmd --prefix frontend run build
# 결과: vite v5.4.21 building for production... ✓ built in 20.52s (오류 0건)

# 3. 보호 파일 해시 검증
Get-FileHash -Algorithm SHA256 collector.py,gangnam_food_stores.sqlite3,run_gangnam.bat
# 결과:
# collector.py                : 341BAC12BB0AF58DCBDEBBA9459033521F27DF9817E35BAD8B21A4D07BA3369C
# gangnam_food_stores.sqlite3 : FEE3B58651CFED5C390C0B95DB02B05EBE92DF18619A06F4E399D429236F3A78
# run_gangnam.bat             : 0582C3A1AE53450DDC482E9BF538510780CA2F14D44E987CC753D4E12C816491
```

---

## 5. 최종 판정

- **종합 판정**: **최종 적격 (ALL PASS)**
- **정합성 확인**: 원시 JSON(`phase5d_step2_validation.json`), 캡처 PNG 7종(`phase5d_step2_s1~s7_*.png`), 실행보고서 및 본 품질보고서의 시나리오별 지역 조건과 실측 결과가 **100% 일치**함을 확인했습니다.
- **사용자 승인 대기**: 후속 단계인 Step 5D-3에 임의 착수하지 않고, 본 증빙 정정 보고에 대한 사용자 승인을 대기합니다.
