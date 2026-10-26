# Phase 5D 후속 Step 1 실행 보고서: FTC 전년비 계산 계약 및 단위 검증 보강

- **작성일**: 2026-10-19
- **작업 경로**: `D:\Franchise_Dashboard`
- **상태**: **Step 1 구현 및 단위 검증 완료 (ALL PASS)**
- **근거 계획서**: [`reports/phase5d_ftc_yoy_reassessment_r1.md`](file:///d:/Franchise_Dashboard/reports/phase5d_ftc_yoy_reassessment_r1.md)
- **원시 검증 결과**: [`reports/phase5d_step1_calc_validation.json`](file:///d:/Franchise_Dashboard/reports/phase5d_step1_calc_validation.json)
- **기준선 해시 기록**: [`reports/phase5d_step1_baseline.json`](file:///d:/Franchise_Dashboard/reports/phase5d_step1_baseline.json)

---

## 1. 작업 개요 및 목적

본 작업은 `TASK.md` 및 사용자 승인된 `reports/phase5d_ftc_yoy_reassessment_r1.md`의 Step 1 범위에 따라, 신규 유틸리티나 신규 의존성을 추가하지 않고 **기존 전년비 계산 유틸리티 자산([`frontend/src/utils/ftcYoyComparison.js`](file:///d:/Franchise_Dashboard/frontend/src/utils/ftcYoyComparison.js))을 최소 수정**하여 고정 단위 계약 검증과 엄격한 비수치 예외 방어를 보강하고, 테스트 스크립트([`scratch/test_phase5d_step1_calc.mjs`](file:///d:/Franchise_Dashboard/scratch/test_phase5d_step1_calc.mjs))에 단위 무결성 및 경계 사례(T-09-A ~ T-09-F)를 추가하여 검증하는 것입니다.

---

## 2. 필수 변경 사항 및 구현 상세

### 2.1 고정 단위 계약 매핑 (`KNOWN_METRIC_KEY_UNITS`)
공정위 trends API 응답 스키마(`YearlyTrendItem`)는 별도의 `unit` 필드를 제공하지 않고 필드명 자체에 단위가 고정되어 있습니다. 이를 안전하게 강제하기 위해 다음의 고정 계약을 구축했습니다:
- 매출 3종(`median_sales_thousand_krw`, `trimmed_mean_5pct_thousand_krw`, `store_weighted_avg_thousand_krw`): `thousand_krw`
- 가맹점 수(`total_franchise_stores`): `stores`

```javascript
export const KNOWN_METRIC_KEY_UNITS = {
  median_sales_thousand_krw: 'thousand_krw',
  trimmed_mean_5pct_thousand_krw: 'thousand_krw',
  store_weighted_avg_thousand_krw: 'thousand_krw',
  total_franchise_stores: 'stores'
};
```

### 2.2 엄격한 유한 수치 검증 (`isValidNumeric`)
기존 `isNaN()`이나 단순 형변환이 빈 문자열(`''`), 문자열 숫자(`'100'`), boolean(`true`/`false`)을 통과시키는 위험을 원천 차단하기 위해 `typeof value === 'number' && Number.isFinite(value)`로 검증을 강화했습니다.

```javascript
export function isValidNumeric(value) {
  return typeof value === 'number' && Number.isFinite(value);
}
```

### 2.3 지표별 평가 함수 (`evaluateMetricComparison`)
계약 위반 및 오류 사유를 명확히 구분하여 반환합니다:
1. **단위 불일치 (`reason: '단위 불일치'`)**:
   - 지표 키가 `KNOWN_METRIC_KEY_UNITS`에 없거나, 전달된 `expectedUnit`과 고유 단위가 불일치할 때 (예: `median_sales_thousand_krw`에 `expectedUnit: 'stores'` 설정 시)
   - 레코드에 명시적 `unit` 또는 `unit_type` 메타데이터가 존재하며 고유 단위와 충돌할 때
2. **필드 키 누락 (`reason: '필드 키 누락'`)**:
   - 2024년 또는 2025년 레코드에 대상 `cfg.key` 프로퍼티가 누락되었을 때
3. **비수치 또는 수치 결측 (`reason: '비수치 또는 수치 결측'`)**:
   - 빈 문자열, 문자열 숫자, boolean, `null`, `undefined`, `NaN`, `±Infinity` 입력 시
4. **기준값 0 이하 (`reason: '기준값 0 이하'`)**:
   - 2024년 기준값이 0 또는 음수일 때 (분모 0 나눗셈 및 비정상 음수 차단)

### 2.4 기존 반환 구조 및 포맷터 호환성 유지
기존 `calculateFtcYoyComparison`, `formatMetricValue`, `formatDiffAmount`, `formatDiffRate`의 시그니처와 반환 필드(`diffAmountText`, `diffRateText`, `direction`, `directionSign`, `isCalculable` 등)를 100% 호환되게 유지했습니다.

---

## 3. 단위 테스트 실행 및 검증 결과

실행 스크립트: [`scratch/test_phase5d_step1_calc.mjs`](file:///d:/Franchise_Dashboard/scratch/test_phase5d_step1_calc.mjs)  
원시 결과 파일: [`reports/phase5d_step1_calc_validation.json`](file:///d:/Franchise_Dashboard/reports/phase5d_step1_calc_validation.json)  
실행 결과: **종료 코드 0 (Exit Code 0), `all_passed: true`**

| 테스트 ID | 테스트 명칭 | 대상 조건 | 판정 |
| :--- | :--- | :--- | :---: |
| **T-01** | CAT_MAJ_01 수치 및 포맷팅 일치 검증 | 실제 한식 API 데이터 2024→2025 4개 지표 델타 및 포맷 대조 | **PASS** |
| **T-02** | 8대 전 업종 API 데이터 전년비 계산 성공 | CAT_MAJ_01 ~ CAT_MAJ_08 전수 계산 및 수치 유효성 | **PASS** |
| **T-03** | 기준값 0 / 음수 예외 분기 검증 | 기준값 0인 지표만 `비교 불가`, 정상 지표는 계산 통과 | **PASS** |
| **T-04** | 연도 누락 케이스 검증 | 2024 또는 2025 누락 시 안전한 미표시 분기 (`isAvailable: false`) | **PASS** |
| **T-05** | 빈 데이터 및 비정상 입력 방어 검증 | `null`, `[]`, `undefined` 입력 방어 | **PASS** |
| **T-06** | 2026년 진행형 스냅샷 배제 검증 | 2026년 표본(1858개) 및 수치 완전 배제 확인 | **PASS** |
| **T-07** | 변동 없음 및 감소 케이스 방향성/부호 검증 | `감소 (-)` / `변동 없음 (기호 없음)` / `증가 (+)` 식별성 | **PASS** |
| **T-08** | 보호 파일 3종 무결성 검증 | 보호 파일 3종 SHA-256 기준선 대비 100% 일치 | **PASS** |
| **T-09-A** | 잘못된 expectedUnit 차단 | `median_sales_thousand_krw`에 `expectedUnit: 'stores'` 지정 시 차단 | **PASS** |
| **T-09-B** | 정상 expectedUnit 통과 | `median_sales_thousand_krw`에 `expectedUnit: 'thousand_krw'` 지정 시 통과 | **PASS** |
| **T-09-C** | 레코드 명시적 단위 충돌 차단 | `{ unit: 'thousand_krw', unit_type: 'stores' }` 등 2024·2025 양측 unit/unit_type 충돌 차단 | **PASS** |
| **T-09-D** | 지표 키 누락 차단 | 2024 또는 2025 객체 내 키 누락 시 `필드 키 누락` 차단 | **PASS** |
| **T-09-E** | 비수치 경계값 전수 차단 | `''`, `'100'`, `true`, `false`, `null`, `undefined`, `NaN`, `±Infinity` 차단 | **PASS** |
| **T-09-F** | 기준값 0 및 음수 차단 | `0`, `-1`, `-100`, `-30000` 전달 시 `기준값 0 이하` 차단 | **PASS** |

---

## 4. 보호 대상 파일 무결성 확인

| 대상 파일 | 사전 기준 SHA-256 해시 | 사후 실측 SHA-256 해시 | 무결성 판정 |
| :--- | :--- | :--- | :---: |
| [`collector.py`](file:///d:/Franchise_Dashboard/collector.py) | `341BAC12BB0AF58DCBDEBBA9459033521F27DF9817E35BAD8B21A4D07BA3369C` | `341BAC12BB0AF58DCBDEBBA9459033521F27DF9817E35BAD8B21A4D07BA3369C` | **일치 (PASS)** |
| [`gangnam_food_stores.sqlite3`](file:///d:/Franchise_Dashboard/gangnam_food_stores.sqlite3) | `FEE3B58651CFED5C390C0B95DB02B05EBE92DF18619A06F4E399D429236F3A78` | `FEE3B58651CFED5C390C0B95DB02B05EBE92DF18619A06F4E399D429236F3A78` | **일치 (PASS)** |
| [`run_gangnam.bat`](file:///d:/Franchise_Dashboard/run_gangnam.bat) | `0582C3A1AE53450DDC482E9BF538510780CA2F14D44E987CC753D4E12C816491` | `0582C3A1AE53450DDC482E9BF538510780CA2F14D44E987CC753D4E12C816491` | **일치 (PASS)** |

---

## 5. 범위 준수 및 불필요한 수정 없음 검증

- **신규 패키지/의존성 추가**: 0건
- **신규 유틸리티 파일 생성**: 0건
- **UI 컴포넌트(`FtcBenchmarkPanel.jsx`, `App.jsx` 등) 수정**: **0건 (일체 수정 없음)**
- **CSS 스타일시트 수정**: **0건 (일체 수정 없음)**
- **백엔드 API 및 SQLite DB 수정**: **0건 (일체 수정 없음)**
- **수정 허용 파일만 변경**: `frontend/src/utils/ftcYoyComparison.js`, `scratch/test_phase5d_step1_calc.mjs`
