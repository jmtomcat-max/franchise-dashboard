# Phase 5D 후속 Step 1 품질 검증 보고서: 전년비 계산 계약 품질 및 무결성 감사

- **작성일**: 2026-10-19
- **검증 환경**: Node.js (v22.14.0), Windows
- **대상 파일**: [`frontend/src/utils/ftcYoyComparison.js`](file:///d:/Franchise_Dashboard/frontend/src/utils/ftcYoyComparison.js)
- **원시 검증 데이터**: [`reports/phase5d_step1_calc_validation.json`](file:///d:/Franchise_Dashboard/reports/phase5d_step1_calc_validation.json)
- **종합 판정**: **품질 기준 100% 충족 (QUALITY PASS)**

---

## 1. 품질 감사 개요

본 보고서는 `TASK.md`의 완료 조건에 따라 Phase 5D Step 1 계산 유틸리티의 계약 준수, 비수치 방어, 단위 무결성 및 보호 자산의 안전성을 독립적으로 검증한 결과를 기술합니다.

---

## 2. 세부 품질 감사 항목 및 결과

### 2.1 고정 단위 계약 검증 품질 (Unit Integrity)
- **감사 기준**:
  - API 필드명에 내재된 고유 단위(매출 3종: `thousand_krw`, 가맹점수: `stores`)가 코드 레벨에서 사전(`KNOWN_METRIC_KEY_UNITS`)으로 관리되는가?
  - 호출부에서 임의의 잘못된 `expectedUnit`(예: 매출에 `stores` 지정)을 설정했을 때 즉시 차단되는가?
  - 레코드 내 명시적 메타데이터(`unit`, `unit_type`)가 존재할 때 불일치 시 차단되는가?
- **실측 결과**:
  - T-09-A: `median_sales_thousand_krw`에 `expectedUnit: 'stores'` 지정 시 `isCalculable: false, reason: '단위 불일치'` 정상 차단 (**PASS**).
  - T-09-B: 정상 expectedUnit 지정 시 `isCalculable: true, diffAmount: 2000, diffRatePct: 6.7%` 정상 산출 (**PASS**).
  - T-09-C: 레코드의 `{ unit: 'thousand_krw', unit_type: 'stores' }` 등 unit과 unit_type 개별/동시 명시 시 2024·2025 양측 불일치 전수 차단 (`isCalculable: false, reason: '단위 불일치'`, **PASS**).

### 2.2 엄격한 비수치 및 결측치 방어 품질 (Type & Range Safety)
- **감사 기준**:
  - `isNaN()`의 묵시적 형변환 취약점(빈 문자열 `''`, 문자열 숫자 `'100'`, boolean `true`/`false`)이 완전히 차단되는가?
  - `null`, `undefined`, `NaN`, `Infinity`, `-Infinity`가 모두 `비수치 또는 수치 결측`으로 처리되는가?
- **실측 결과**:
  - T-09-E: 11개 비수치 패턴에 대해 2024년 및 2025년 양측 총 22회 테스트 전수 `isCalculable: false, reason: '비수치 또는 수치 결측'` 차단 (**PASS**).

### 2.3 0 나눗셈 및 비즈니스 경계값 품질 (Zero Division Prevention)
- **감사 기준**:
  - 2024년 기준값이 0 또는 음수일 때 분모 0 나눗셈 및 왜곡된 음수 델타가 방지되는가?
- **실측 결과**:
  - T-03 & T-09-F: `0`, `-1`, `-100`, `-30000` 등 2024년 기준값 0 이하 입력 시 `isCalculable: false, reason: '기준값 0 이하'` 정상 차단 (**PASS**).

### 2.4 실 API 데이터 전수 수치 정확도 (Production Data Accuracy)
- **감사 기준**:
  - 로컬 FTC trends API의 8대 대분류(`CAT_MAJ_01` ~ `CAT_MAJ_08`) 전수에서 4대 지표 델타 및 증감률이 정상 계산되는가?
  - 2026년 진행형 스냅샷 데이터가 계산 및 표본에서 100% 배제되는가?
- **실측 결과**:
  - T-01: CAT_MAJ_01(한식) 중위매출(+1,659만원 / +5.0%), 5% 절사평균(+1,111만원 / +3.0%), 가중평균(+3,905만원 / +10.8%), 가맹점수(+1,652개 / +3.9%) 수동 검증값과 100% 일치 (**PASS**).
  - T-02: 8개 업종 전수 HTTP 200 수신 및 4개 지표 전수 `isCalculable: true` 확인 (**PASS**).
  - T-06: 2026년 스냅샷 표본(1,858개) 및 수치가 `baseYearSampleCount`, `targetYearSampleCount`, `metrics` 어디에도 유입되지 않음 확인 (**PASS**).

---

## 3. 보호 대상 자산 100% 불변 검증

| 대상 파일 | 사전 SHA-256 기준값 | 사후 실측 SHA-256 | 일치 여부 |
| :--- | :--- | :--- | :---: |
| [`collector.py`](file:///d:/Franchise_Dashboard/collector.py) | `341BAC12BB0AF58DCBDEBBA9459033521F27DF9817E35BAD8B21A4D07BA3369C` | `341BAC12BB0AF58DCBDEBBA9459033521F27DF9817E35BAD8B21A4D07BA3369C` | **100% 일치** |
| [`gangnam_food_stores.sqlite3`](file:///d:/Franchise_Dashboard/gangnam_food_stores.sqlite3) | `FEE3B58651CFED5C390C0B95DB02B05EBE92DF18619A06F4E399D429236F3A78` | `FEE3B58651CFED5C390C0B95DB02B05EBE92DF18619A06F4E399D429236F3A78` | **100% 일치** |
| [`run_gangnam.bat`](file:///d:/Franchise_Dashboard/run_gangnam.bat) | `0582C3A1AE53450DDC482E9BF538510780CA2F14D44E987CC753D4E12C816491` | `0582C3A1AE53450DDC482E9BF538510780CA2F14D44E987CC753D4E12C816491` | **100% 일치** |

---

## 4. 종합 품질 평가 결론

본 Step 1 작업은 UI/CSS/API/DB 수정 0건 원칙을 철저히 준수하였으며, 단위 무결성·비수치 방어 계약을 완벽히 만족하였습니다. 모든 테스트가 성공(Exit Code 0, `all_passed: true`)하여 **다음 개발 단계(Step 2 UI 연동) 진입 준비가 완료**되었습니다.
