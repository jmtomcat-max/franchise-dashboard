# Phase 5C Step 2 보완 보고서 (Complement Report)
**데이터 결손 처리 엄격화, 동일 응답 기반 결산연도 고립 및 실 브라우저 7대 전수 검증**

- **문서 버전**: v1.2 (2025년 결산연도 고립 및 실 브라우저 테스트 추가 완료)
- **작성 일자**: 2026-10-14
- **작업 디렉터리**: `D:\Franchise_Dashboard`
- **준수 규격**: `AGENTS.md` (보호 규칙 및 단계별 승인 절차 준수), Phase 5C Step 2 사용자 보완 지시문

---

## 1. 개요 및 사용자 보완 지시 사항

Phase 5C 2단계 검토 후 제시된 **데이터 결손 처리 및 연도 고립 지시**를 엄격히 이행하였습니다.

1. **선택 연도의 결산연도 고립 (동일 응답 필드만 사용)**:
   - 사용자가 특정 연도(예: 2025년)를 선택했을 때, **해당 벤치마크 응답(`benchmarkData.data`)의 `financial_year` 필드만 단독으로 사용**.
   - 최신 상태 메타(`statusMeta`, 2026년 등록/2025년 결산)의 필드가 선택 연도 화면으로 교차 유입(Pollution)되는 폴백을 원천 차단.
   - 해당 응답에 `financial_year`가 없으면 임의 계산(`- 1`)이나 타 응답 참조 없이 **모든 화면(필터 태그, 패널 헤더, 모바일 뱃지, 경고 배너)에서 일관되게 `결산연도 확인 불가`로 표시**.
2. **전국 비교 기준 동적 연동 및 고정값 완전 제거**:
   - `MarketSummary.jsx`에 하드코딩되어 있던 전국 기준값(6.53%, 22.89% 및 48,002 / 735,185, 168,295 / 735,185)을 제거하고, 요약 API(`/api/v1/analytics/summary`)의 실제 응답값으로 실시간 계산되도록 수정.
   - 전국 데이터가 없거나 기준시점이 맞지 않으면 침투율 비교를 즉시 보류(`[전국 비교 보류]`).
3. **선택 지역 기준월 누락 시 전국 요약 기준월 대리 표출 차단**:
   - `App.jsx`에서 `regionDetail.meta.data_reference_month` 부재 시 `summaryMeta`를 대신 표시하던 폴백을 제거하고, 지역 데이터의 기준월을 확인하지 못했다면 엄격히 `소진공 기준월 확인 불가`로 표시.
4. **2025년 선택 상태 결산연도 부재 브라우저 CDP 테스트 추가 (TEST 7)**:
   - 2025년 선택 상태에서 `financial_year` 필드만 제거한 런타임 네트워크 인터셉트 환경을 구성하고, 실제 브라우저(CDP)에서 모든 화면 요소의 `결산연도 확인 불가` 표출과 오염 배제를 실측 검증.

---

## 2. 보완 구현 상세 내역

### 2.1 `CategoryFilterBar.jsx` & `FtcBenchmarkPanel.jsx` 동일 응답 결산연도 고립
- **동일 응답 단독 바인딩 로직**:
  ```javascript
  // frontend/src/components/CategoryFilterBar.jsx
  const bData = benchmarkData?.data;
  const ftcBenchmarkYear = bData ? bData.benchmark_year : (statusMeta?.latest_benchmark_year || null);
  
  // bData가 존재하면 오직 bData.financial_year만 사용하고, statusMeta.financial_year로 폴백하지 않음
  const ftcFinancialYear = bData ? (bData.financial_year || null) : (statusMeta?.financial_year || null);
  const finYearText = ftcFinancialYear ? `${ftcFinancialYear}년 결산` : '결산연도 확인 불가';
  ```
- **FtcBenchmarkPanel.jsx 전 화면 일관 적용**:
  - 패널 상단 데스크톱 헤더 배지: `{data.benchmark_year}년 등록 ({finYearText})`
  - 모바일 요약 바 배지: `{data.benchmark_year}년 등록 ({finYearText})`
  - 결산 부재/스냅샷 안내 배너: `{finYearText}` 적용 완료 (기존 `{data.financial_year}년 결산` 하드코딩 교체)
  - 2025년 선택 시 `bData.financial_year`가 없으면 모든 화면에서 예외 없이 `2025년 등록 (결산연도 확인 불가)`로 표출.

### 2.2 `MarketSummary.jsx` 동적 전국 벤치마크 및 비교 보류 로직
- **Props 확장**: `nationalSummaryData`, `nationalSummaryMeta`를 상위 `App.jsx`로부터 주입받아 전국 벤치마크를 동적으로 산출.
- **비교 가능 여부 판정 및 보류 상태**:
  - `hasNationalBenchmark`: 전국 요약 데이터 및 분자/분모 유효성 검증.
  - `isPeriodMatched`: 지역 기준월(`localRefMonth`)과 전국 기준월(`nationalRefMonth`) 일치 검증.
  - `!isComparisonAvailable` 시:
    - 격차 뱃지(`.diff-pill`)에 `+0.64%p` 대신 `비교 보류` 표출.
    - 게이지 바의 전국 기준선 핀(`.gauge-target-pin`) 자동 숨김.
    - 수식 영역에 `[전국 비교 보류: {사유}]` 명시 (사유: `기준시점 미확인`, `기준시점 불일치`, 또는 `전국 벤치마크 데이터 미수신`).
    - 카드 상단 뱃지에 `.tag-hold` 스타일로 보류 사유 고지.

### 2.3 `App.jsx` 지역 기준월 대리 표출 완전 차단
- 기존의 전국 메타 폴백 삼항 연산자 제거:
  ```javascript
  const sedaReferenceMonth = (activeRegionCode === '00'
    ? summaryMeta?.data_reference_month
    : regionDetail?.meta?.data_reference_month) || null;
  ```

---

## 3. 실 브라우저 CDP 종합 전수 검증 결과 (7대 시나리오 100% 통과)

실제 구동 중인 Chrome 환경에서 브라우저 `window.fetch` 런타임 단계에 진입하는 API 응답을 제어하여, 실제 화면 렌더링 및 상태 전이를 전수 검증하였습니다.

| 테스트 번호 | 시나리오 및 조건 | 검증 항목 | 실측 화면 결과 | 판정 |
| :---: | :--- | :--- | :--- | :---: |
| **T1** | **정상 광진구(`11215`) + 2026 스냅샷** | 동적 전국 벤치마크 연동, 분자/분모 일치, 격차 계산 | - SEDA: `소진공 2026-07 공간 전수`<br>- FTC: `2026년 등록 (2025년 결산) · 진행형 스냅샷`<br>- 수식: `지역: 323개 / 4,507개 (전국 기준 6.53%: 48,002 / 735,185)`<br>- 격차: `+0.64%p`, 기준선 핀: `6.53%` 표출 | **PASS** |
| **T2** | **정상 제주시(`50110`) 실측** | 점포 11,711개 대사 및 전국 6.53% / 22.89% 동적 연동 | - 점포수: `11,711 개소`<br>- 가맹수식: `지역: 535개 / 11,711개 (전국 기준 6.53%: 48,002 / 735,185)`<br>- 브랜드수식: `지역: 1,244개 / 11,711개 (전국 기준 22.89%: 168,295 / 735,185)`<br>- 격차: `-1.96%p`, `-12.27%p` | **PASS** |
| **T3** | **결손 흐름 A: 지역 기준월 누락**<br>(`meta.data_reference_month = null`) | 전국값 대리 표출 차단, `기준월 확인 불가`, 침투율 비교 보류 | - SEDA 뱃지: `소진공 기준월 확인 불가`<br>- 카드 태그: `비교 보류 (기준시점 미확인 (지역: 미확인, 전국: 2026-07))`<br>- 수식: `[전국 비교 보류: 기준시점 미확인 ...]`<br>- 격차 뱃지: `비교 보류`<br>- 기준선 핀: 숨김 | **PASS** |
| **T4** | **결손 흐름 B: 기준시점 불일치**<br>(지역: `2025-12`, 전국: `2026-07`) | 시점 불일치 감지 및 침투율 비교 보류 고지 | - SEDA 뱃지: `소진공 2025-12 공간 전수`<br>- 카드 태그: `비교 보류 (기준시점 불일치 (지역: 2025-12, 전국: 2026-07))`<br>- 수식: `[전국 비교 보류: 기준시점 불일치 (지역: 2025-12, 전국: 2026-07)]`<br>- 격차 뱃지: `비교 보류` | **PASS** |
| **T5** | **결손 흐름 C: 2026년 결산연도 필드 부재**<br>(`financial_year` 누락) | 임의 -1 계산 차단, `결산연도 확인 불가` 표기 | - FTC 필터 태그: `공정위 2026년 등록 (결산연도 확인 불가) · 진행형 스냅샷`<br>- 데스크톱 헤더: `2026년 등록 (결산연도 확인 불가)`<br>- 모바일 배지: `2026년 스냅샷 (결산연도 확인 불가)`<br>- `2025년 결산` 임의 계산 0건 확인 | **PASS** |
| **T6** | **결손 흐름 D: 전국 벤치마크 미수신**<br>(전국 요약 API 500 오류) | 전국 분모/분자 부재 시 비교 보류 | - 카드 태그: `비교 보류 (전국 벤치마크 데이터 미수신)`<br>- 수식: `[전국 비교 보류: 전국 벤치마크 데이터 미수신]`<br>- 푸터 기준선: `전국 벤치마크 데이터 미수신` | **PASS** |
| **T7** | **결손 흐름 E: 2025년 결산연도 필드 부재**<br>(2025 응답의 `financial_year`만 누락, `statusMeta` 유지) | **동일 응답 고립 및 statusMeta 폴백 차단, 임의 -1 추측 차단** | - FTC 필터 태그: `공정위 2025년 등록 (결산연도 확인 불가) · 최신 완결 후보`<br>- 데스크톱 헤더: `2025년 등록 (결산연도 확인 불가)`<br>- 모바일 배지: `2025년 등록 (결산연도 확인 불가)`<br>- 후보 배지: `최신 완결 후보 (공식마감 미확인)`<br>- `2024년 결산` 추측 및 `2025년 결산` 오염 0건 확인 | **PASS** |

### 3.1 실 브라우저 캡처 화면 링크

1. **광진구 정상 연동 화면**:
   - [phase5c_step2_gwangjin_2026.png](file:///D:/Franchise_Dashboard/reports/phase5c_step2_gwangjin_2026.png)
2. **제주시 실측 대사 화면**:
   - [phase5c_step2_jeju_2025.png](file:///D:/Franchise_Dashboard/reports/phase5c_step2_jeju_2025.png)
3. **결손 흐름 A (지역 기준월 누락 시 대리 표출 차단 및 비교 보류)**:
   - [phase5c_step2_defect_region_month_missing.png](file:///D:/Franchise_Dashboard/reports/phase5c_step2_defect_region_month_missing.png)
4. **결손 흐름 B (지역 2025-12 vs 전국 2026-07 기준시점 불일치 시 비교 보류)**:
   - [phase5c_step2_defect_period_mismatch.png](file:///D:/Franchise_Dashboard/reports/phase5c_step2_defect_period_mismatch.png)
5. **결손 흐름 C (공정위 2026년 결산연도 부재 시 임의 -1 계산 차단)**:
   - [phase5c_step2_defect_ftc_finyear_missing.png](file:///D:/Franchise_Dashboard/reports/phase5c_step2_defect_ftc_finyear_missing.png)
6. **결손 흐름 D (전국 벤치마크 미수신 시 비교 보류)**:
   - [phase5c_step2_defect_national_missing.png](file:///D:/Franchise_Dashboard/reports/phase5c_step2_defect_national_missing.png)
7. **결손 흐름 E (공정위 2025년 선택 상태에서 결산연도 부재 시 동일 응답 고립 및 확인 불가 표출)**:
   - [phase5c_step2_defect_2025_finyear_missing.png](file:///D:/Franchise_Dashboard/reports/phase5c_step2_defect_2025_finyear_missing.png)

---

## 4. 수정 파일 및 자산 보존 검증

### 4.1 보완 수정된 프런트엔드 파일 (5개)
1. `frontend/src/App.jsx`:
   - 선택 지역 기준월 누락 시 전국 요약 기준월 대리 표출 제거
   - `MarketSummary`에 `nationalSummaryData`, `nationalSummaryMeta` 전달
2. `frontend/src/components/MarketSummary.jsx`:
   - 전국 벤치마크 분자/분모/비율 하드코딩 완전 제거 및 요약 API 동적 연동
   - 기준시점 불일치/부재 시 비교 보류 로직 구현
3. `frontend/src/components/CategoryFilterBar.jsx`:
   - 결산연도 필드를 동일 응답(`bData.financial_year`)으로만 고립
   - 타 응답(`statusMeta`) 폴백 및 `Number() - 1` 임의 추측 완전 제거, 부재 시 `결산연도 확인 불가` 표기
4. `frontend/src/components/FtcBenchmarkPanel.jsx`:
   - 결산연도 부재 시 임의 추측 차단 및 전체 영역 `finYearText` 적용
5. `frontend/src/index.css`:
   - `.diff-hold`, `.benchmark-formula-hold`, `.comparison-rule-tag.tag-hold` 디자인 토큰 추가

### 4.2 자산 불변성 확인
- **SQLite DB (16개 전체)**: 파일 수정 시각 및 데이터 무변경 유지.
- **Python 백엔드**: API 라우터, 스키마, 파이프라인 일체 무변경 유지.
- **8대·48개 업종 분류 체계**: 100% 무변경 유지.

---

## 5. 결론 및 단계 완료 승인 요청

Phase 5C Step 2의 모든 보완 지시 사항이 완벽히 해결되었으며, 특히 **선택 연도의 결산연도를 동일 응답 필드만으로 격리하고, 부재 시 전 화면에서 `결산연도 확인 불가`로 표시하는 로직**과 **2025년 결산연도 제거 상태 실 브라우저 CDP 테스트(TEST 7)**가 100% 성공하였습니다.

**`AGENTS.md` 지침에 따라, 사용자의 공식 확인 및 승인 전까지 다음 단계(Phase 5C Step 3)로 임의 진행하지 않고 현 상태에서 작업을 중단하고 대기합니다.**
