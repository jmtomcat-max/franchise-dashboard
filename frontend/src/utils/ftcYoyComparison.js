/**
 * Phase 5D: 공정위 완결 후보 연도 전년비 보조 비교 유틸리티
 * 
 * 계약 및 규칙:
 * 1. 비교 대상은 2024년(기준) 대비 2025년(완결 후보)으로 한정.
 * 2. 2026년 진행형 스냅샷은 계산식 및 비교 대상에서 완전 제외.
 * 3. 4대 비교 지표:
 *    - median_sales_thousand_krw (중위매출, 단위: thousand_krw)
 *    - trimmed_mean_5pct_thousand_krw (5% 절사평균, 단위: thousand_krw)
 *    - store_weighted_avg_thousand_krw (점포 가중평균 매출, 단위: thousand_krw)
 *    - total_franchise_stores (가맹점 수, 단위: stores)
 * 4. 각 지표 키에 고정된 단위 계약(매출 3종 thousand_krw, 가맹점수 stores)을 둔다.
 * 5. 입력값은 typeof value === 'number' && Number.isFinite(value)일 때만 수치로 인정한다.
 *    빈 문자열, 문자열 숫자, boolean, NaN, ±Infinity, null, undefined는 비교 불가로 처리.
 * 6. 2024 기준값이 0 이하(0 또는 음수)이면 '기준값 0 이하'로 비교 불가 처리.
 * 7. 지표 키 누락('필드 키 누락')과 단위 충돌('단위 불일치')은 각각 구분 가능한 사유로 차단.
 * 8. 상태 투명성: 2025년은 '최신 완결 후보 · 공식 마감 여부 미확인', 2026년은 '진행형 스냅샷 · 전년 직접 비교 불가'.
 */

export const FTC_YOY_NOTICES = {
  STATUS_2025: '최신 완결 후보 · 공식 마감 여부 미확인',
  STATUS_2026: '진행형 스냅샷 · 전년 직접 비교 불가',
  POPULATION_DISCLAIMER: '공정거래위원회 가맹사업정보제공시스템 전국 등록 거시 통계 기준 (소상공인진흥공단 지역 점포 통계와 별개 모집단)'
};

/**
 * 지표 키별 고정 단위 계약 매핑 사전
 */
export const KNOWN_METRIC_KEY_UNITS = {
  median_sales_thousand_krw: 'thousand_krw',
  trimmed_mean_5pct_thousand_krw: 'thousand_krw',
  store_weighted_avg_thousand_krw: 'thousand_krw',
  total_franchise_stores: 'stores'
};

export const FTC_YOY_METRIC_CONFIGS = [
  {
    id: 'median_sales',
    key: 'median_sales_thousand_krw',
    expectedUnit: 'thousand_krw',
    label: '중위매출',
    unitType: 'currency',
    unitLabel: '만원'
  },
  {
    id: 'trimmed_mean_5pct',
    key: 'trimmed_mean_5pct_thousand_krw',
    expectedUnit: 'thousand_krw',
    label: '5% 절사평균',
    unitType: 'currency',
    unitLabel: '만원'
  },
  {
    id: 'store_weighted_avg',
    key: 'store_weighted_avg_thousand_krw',
    expectedUnit: 'thousand_krw',
    label: '점포 가중평균 매출',
    unitType: 'currency',
    unitLabel: '만원'
  },
  {
    id: 'total_franchise_stores',
    key: 'total_franchise_stores',
    expectedUnit: 'stores',
    label: '가맹점 수',
    unitType: 'count',
    unitLabel: '개'
  }
];

/**
 * 엄격한 유한 수치 검증 함수
 * 빈 문자열, 숫자 문자열, boolean, NaN, Infinity, -Infinity, null, undefined를 전수 배제
 * @param {any} value 검증 대상 값
 * @returns {boolean} 유한한 number 타입 여부
 */
export function isValidNumeric(value) {
  return typeof value === 'number' && Number.isFinite(value);
}

/**
 * 수치 단위 포맷터
 * @param {number} val 수치
 * @param {'currency'|'count'} unitType 단위 유형
 * @returns {string} 포맷된 문자열
 */
export function formatMetricValue(val, unitType) {
  if (!isValidNumeric(val)) {
    return '-';
  }
  if (unitType === 'currency') {
    const manwon = Math.round(val / 10);
    return `${manwon.toLocaleString('ko-KR')}만원`;
  }
  return `${Math.round(val).toLocaleString('ko-KR')}개`;
}

/**
 * 증감액 포맷터
 * @param {number|null} diffAmount 증감액
 * @param {'currency'|'count'} unitType 단위 유형
 * @returns {string} 부호 포함 포맷된 증감액 문자열
 */
export function formatDiffAmount(diffAmount, unitType) {
  if (!isValidNumeric(diffAmount)) {
    return '비교 불가';
  }
  const rounded = Math.round(unitType === 'currency' ? diffAmount / 10 : diffAmount);
  const sign = rounded > 0 ? '+' : (rounded < 0 ? '-' : '');
  const absVal = Math.abs(rounded).toLocaleString('ko-KR');
  const unit = unitType === 'currency' ? '만원' : '개';
  return `${sign}${absVal}${unit}`;
}

/**
 * 증감률 포맷터
 * @param {number|null} diffRatePct 증감률 (%)
 * @returns {string} 부호 포함 포맷된 증감률 문자열
 */
export function formatDiffRate(diffRatePct) {
  if (!isValidNumeric(diffRatePct)) {
    return '비교 불가';
  }
  const sign = diffRatePct > 0 ? '+' : '';
  return `${sign}${diffRatePct.toFixed(1)}%`;
}

/**
 * 개별 지표 전년비 비교 및 단위·비수치·기준값 안전성 평가 함수
 * 
 * @param {Object} item2024 2024년 기준 레코드
 * @param {Object} item2025 2025년 비교 레코드
 * @param {Object} cfg 지표 설정 객체 ({ key, expectedUnit, unitType, ... })
 * @returns {Object} 계산 및 판정 결과 객체
 */
export function evaluateMetricComparison(item2024, item2025, cfg) {
  // 1. 고정 필드별 고유 단위 매핑 및 설정된 expectedUnit 검증
  const intrinsicUnit = KNOWN_METRIC_KEY_UNITS[cfg?.key];
  if (!intrinsicUnit || (cfg?.expectedUnit && cfg.expectedUnit !== intrinsicUnit)) {
    return {
      isCalculable: false,
      reason: '단위 불일치',
      diffAmount: null,
      diffRatePct: null,
      diffAmountText: '비교 불가',
      diffRateText: '비교 불가',
      direction: '비교 불가',
      directionSign: ''
    };
  }

  // 2. 필드 키 존재 여부 검증 (2024 또는 2025 객체에 프로퍼티 미존재 시 차단)
  if (!item2024 || !item2025 || !(cfg.key in item2024) || !(cfg.key in item2025)) {
    return {
      isCalculable: false,
      reason: '필드 키 누락',
      diffAmount: null,
      diffRatePct: null,
      diffAmountText: '비교 불가',
      diffRateText: '비교 불가',
      direction: '비교 불가',
      directionSign: ''
    };
  }

  // 3. 레코드에 명시적 단위 메타데이터(unit 및 unit_type)가 제공될 경우 고유 단위와의 불일치 차단
  // unit과 unit_type이 동시에 제공되더라도 둘 중 어느 하나라도 intrinsicUnit과 다르면 즉시 차단
  if (
    (item2024.unit && item2024.unit !== intrinsicUnit) ||
    (item2024.unit_type && item2024.unit_type !== intrinsicUnit) ||
    (item2025.unit && item2025.unit !== intrinsicUnit) ||
    (item2025.unit_type && item2025.unit_type !== intrinsicUnit)
  ) {
    return {
      isCalculable: false,
      reason: '단위 불일치',
      diffAmount: null,
      diffRatePct: null,
      diffAmountText: '비교 불가',
      diffRateText: '비교 불가',
      direction: '비교 불가',
      directionSign: ''
    };
  }

  const v24 = item2024[cfg.key];
  const v25 = item2025[cfg.key];

  // 4. 비수치 차단 (빈 문자열, 숫자 문자열, boolean, null, undefined, NaN, ±Infinity 전수 차단)
  if (!isValidNumeric(v24) || !isValidNumeric(v25)) {
    return {
      isCalculable: false,
      reason: '비수치 또는 수치 결측',
      diffAmount: null,
      diffRatePct: null,
      diffAmountText: '비교 불가',
      diffRateText: '비교 불가',
      direction: '비교 불가',
      directionSign: ''
    };
  }

  // 5. 기준값 0 이하 차단 (0 나눗셈 및 비즈니스 음수 차단)
  if (v24 <= 0) {
    return {
      isCalculable: false,
      reason: '기준값 0 이하',
      diffAmount: null,
      diffRatePct: null,
      diffAmountText: '비교 불가',
      diffRateText: '비교 불가',
      direction: '비교 불가',
      directionSign: ''
    };
  }

  // 6. 정상 델타 및 증감률 산출
  const diffAmount = v25 - v24;
  const diffRatePct = ((v25 - v24) / v24) * 100;

  let direction = '변동 없음';
  let directionSign = '';
  if (Math.abs(diffAmount) < 0.0001 || Math.abs(diffRatePct) < 0.001) {
    direction = '변동 없음';
    directionSign = '';
  } else if (diffAmount > 0) {
    direction = '증가';
    directionSign = '+';
  } else {
    direction = '감소';
    directionSign = '-';
  }

  return {
    isCalculable: true,
    reason: null,
    diffAmount,
    diffRatePct,
    diffAmountText: formatDiffAmount(diffAmount, cfg.unitType),
    diffRateText: formatDiffRate(diffRatePct),
    direction,
    directionSign
  };
}

/**
 * 2024년 대비 2025년(완결 후보) 공정위 전년비 보조 비교 계산 함수.
 * 2026년 진행형 스냅샷은 계산식 및 대상에서 완전 제외한다.
 * 
 * @param {Array} yearlySeries trendsData.data.yearly_series 시계열 배열
 * @returns {Object} 전년비 계산 결과 객체
 */
export function calculateFtcYoyComparison(yearlySeries) {
  if (!Array.isArray(yearlySeries) || yearlySeries.length === 0) {
    return {
      isAvailable: false,
      reason: '시계열 데이터 없음',
      baseYear: '2024',
      targetYear: '2025',
      baseYearRecord: null,
      targetYearRecord: null,
      baseYearSampleCount: null,
      targetYearSampleCount: null,
      statusNotice2025: FTC_YOY_NOTICES.STATUS_2025,
      statusNotice2026: FTC_YOY_NOTICES.STATUS_2026,
      disclaimer: FTC_YOY_NOTICES.POPULATION_DISCLAIMER,
      metrics: []
    };
  }

  // 2024년 및 2025년 레코드만 엄격 탐색 (2026년 등 타 연도 배제)
  const item2024 = yearlySeries.find((item) => String(item?.benchmark_year) === '2024') || null;
  const item2025 = yearlySeries.find((item) => String(item?.benchmark_year) === '2025') || null;

  if (!item2024 || !item2025) {
    let missingReason = '2024년 및 2025년 데이터 누락';
    if (!item2024 && item2025) missingReason = '2024년 기준 데이터 누락';
    if (item2024 && !item2025) missingReason = '2025년 비교 데이터 누락';

    return {
      isAvailable: false,
      reason: missingReason,
      baseYear: '2024',
      targetYear: '2025',
      baseYearRecord: item2024,
      targetYearRecord: item2025,
      baseYearSampleCount: item2024?.sample_count ?? null,
      targetYearSampleCount: item2025?.sample_count ?? null,
      statusNotice2025: FTC_YOY_NOTICES.STATUS_2025,
      statusNotice2026: FTC_YOY_NOTICES.STATUS_2026,
      disclaimer: FTC_YOY_NOTICES.POPULATION_DISCLAIMER,
      metrics: []
    };
  }

  const calculatedMetrics = FTC_YOY_METRIC_CONFIGS.map((cfg) => {
    const val2024 = item2024[cfg.key];
    const val2025 = item2025[cfg.key];
    const isNum24 = isValidNumeric(val2024);
    const isNum25 = isValidNumeric(val2025);

    const evalResult = evaluateMetricComparison(item2024, item2025, cfg);

    return {
      id: cfg.id,
      key: cfg.key,
      expectedUnit: cfg.expectedUnit || KNOWN_METRIC_KEY_UNITS[cfg.key],
      label: cfg.label,
      unitType: cfg.unitType,
      unitLabel: cfg.unitLabel,
      val2024: isNum24 ? val2024 : null,
      val2025: isNum25 ? val2025 : null,
      formatted2024: isNum24 ? formatMetricValue(val2024, cfg.unitType) : '-',
      formatted2025: isNum25 ? formatMetricValue(val2025, cfg.unitType) : '-',
      diffAmount: evalResult.diffAmount,
      diffRatePct: evalResult.diffRatePct,
      diffAmountText: evalResult.diffAmountText,
      diffRateText: evalResult.diffRateText,
      direction: evalResult.direction,
      directionSign: evalResult.directionSign,
      isCalculable: evalResult.isCalculable,
      reason: evalResult.reason
    };
  });

  return {
    isAvailable: true,
    reason: null,
    baseYear: '2024',
    targetYear: '2025',
    baseYearRecord: item2024,
    targetYearRecord: item2025,
    baseYearSampleCount: item2024.sample_count,
    targetYearSampleCount: item2025.sample_count,
    statusNotice2025: FTC_YOY_NOTICES.STATUS_2025,
    statusNotice2026: FTC_YOY_NOTICES.STATUS_2026,
    disclaimer: FTC_YOY_NOTICES.POPULATION_DISCLAIMER,
    metrics: calculatedMetrics
  };
}
