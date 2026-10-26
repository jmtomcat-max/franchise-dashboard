# 공정거래위원회 외식업 가맹정보 공식 API 연계 및 데이터 계약서 (FTC API Contract)

- **문서 ID**: `DOC-PHASE4-STAGE4A-FTC-CONTRACT-V1`
- **프로젝트**: 대한민국 외식 프랜차이즈 시장 분석 3D GIS 대시보드 (`D:\Franchise_Dashboard`)
- **작성 단계**: Phase 4 / Stage 4A (API 실증 및 데이터 계약 확정)
- **최종 검증일자**: 2026-10-13
- **계약 상태**: **VERIFIED / CONTRACT FINALIZED (Branch C Strategy)**

---

## 1. 공식 API 서비스 개요 및 메타데이터

| 항목 | 공식 명세 내용 | 검증 상태 |
| :--- | :--- | :--- |
| **서비스명** | (AI친화)가맹정보_브랜드 가맹사업자 통합정보 외식업종 현황 제공 서비스 | VERIFIED |
| **공공데이터포털 ID** | `15165094` | VERIFIED |
| **공식 포털 URL** | [https://www.data.go.kr/data/15165094/openapi.do](https://www.data.go.kr/data/15165094/openapi.do) | VERIFIED |
| **제공 기관** | 공정거래위원회 (FTC, Fair Trade Commission) | VERIFIED |
| **엔드포인트 URL** | `https://apis.data.go.kr/1130000/FftcBrandFrcsBzmnIntgInfoEatoutTpbizStats2_Service/getBrandFrcsBzmnIntgInfoEatoutTpbiz2` | VERIFIED |
| **오퍼레이션명** | `getBrandFrcsBzmnIntgInfoEatoutTpbiz2` | VERIFIED |
| **전송 프로토콜 / 방식** | HTTPS / GET | VERIFIED |
| **인증 방식** | 공공데이터 API 인증키 (`serviceKey` 쿼리 파라미터 URL-encoding 전송) | VERIFIED |
| **데이터 반환 포맷** | JSON (`resultType=json`) 기본, 파라미터 오류 시 XML Fallback | VERIFIED |

---

## 2. 요청 파라미터 (Request Specification)

| 파라미터명 | 국문 파라미터명 | 필수 여부 | 데이터 타입 | 기본값 / 제약조건 | 설명 |
| :--- | :--- | :---: | :--- | :--- | :--- |
| `serviceKey` | 공공데이터 인증키 | **필수** | String | 64자 이상 인코딩 키 | 시스템 환경변수(`.env`의 `SERVICE_KEY`)를 통해 동적 주입 |
| `jngBizCrtrYr` | 가맹사업 기준연도 | **필수** | String(4) | `2017` ~ `2024` | 통계 기준연도 (4자리 연도 YYYY). 미입력 시 에러(Code 11) |
| `pageNo` | 페이지 번호 | 선택 | Integer | `1` (1 이상) | 조회 대상 페이지 번호 |
| `numOfRows` | 페이지당 조회 건수 | 선택 | Integer | `10` (최대 100 권장) | 1회 호출 시 반환 행 수 |
| `resultType` | 반환 포맷 | 선택 | String | `json` (`json`/`xml`) | 응답 데이터 형식 (JSON 권장) |

---

## 3. 응답 구조 및 엔벨로프 (Response Structure)

API 응답은 최상위 JSON 객체에 메타데이터와 결과 리스트(`items`)가 포함된 단일 계층 엔벨로프 구조입니다.

```json
{
  "resultCode": "00",
  "resultMsg": "NORMAL SERVICE",
  "numOfRows": 10,
  "pageNo": 1,
  "totalCount": 6346,
  "items": [
    {
      "jngBizCrtrYr": "2024",
      "alsBrandMngNo": "192408232424576",
      "alsJnghqMngNo": "312418130429576",
      "jnghqRgnNm": "서울",
      "jngBizStrtYmd": "20150312",
      "tpbizMclsfNm": "한식",
      "frcsCnt": 103,
      "dmsCnt": 2,
      "prvyrFrcsCnt": 98,
      "prvyrDmsCnt": 2,
      "jngBzmnJngAmt": 11000.0,
      "jngBzmnEduAmt": 3300.0,
      "jngBzmnGrnteAmt": 5000.0,
      "jngBzmnEtcAmt": 20000.0,
      "depstAmt": 19300.0,
      "unitAreaIntrrAmt": 2200.0,
      "storCrtrArea": 30.0,
      "intrrAmt": 66000.0,
      "fyr": "2023",
      "avgSlsAmt": 115988.0,
      "areaUnitAvgSlsAmt": 3866.0
    }
  ]
}
```

---

## 4. 실측 검증 완료 9대 시나리오 (Empirical Test Results)

본 계약 수립을 위해 실제 공정위 API 서버를 대상으로 총 10회의 실측 테스트를 수행하였으며, 모든 경계 조건이 검증되었습니다.

| 시나리오 번호 | 테스트 유형 | 요청 조건 | 실측 HTTP / 코드 | 결과 건수 | 실증 사실 및 분석 결과 |
| :---: | :--- | :--- | :---: | :---: | :--- |
| **#1** | 최신연도 정상 호출 | `yr=2024, p=1, n=5` | 200 / `00` | 6,346건 | 2024년 전국 외식업 브랜드 총 6,346건 정상 확인 |
| **#2** | 과거연도 정상 호출 | `yr=2023, p=1, n=5` | 200 / `00` | 6,151건 | 2023년 데이터 정상 제공 확인 |
| **#3** | 과거연도 추세 검증 | `yr=2020, p=1, n=5` | 200 / `00` | 4,058건 | 2020년 데이터 정상 제공 확인 (시계열 추적 가능) |
| **#4** | 초기 데이터 검증 | `yr=2017, p=1, n=5` | 200 / `00` | 3,435건 | 2017년부터 연속 시계열 데이터 제공 확인 |
| **#5** | 인증 실패 검증 | 잘못된 인증키 전송 | 403 Forbidden | 0건 | 공공데이터 게이트웨이 레벨 403 차단 확인 |
| **#6** | 미래연도 0건 조회 | `yr=2099, p=1, n=5` | 200 / `00` | 0건 | 데이터 미존재 시 `totalCount: 0, items: []` 정상 처리 |
| **#7** | 필수 파라미터 누락 | `yr` 생략 요청 | 200 / `11` | 0건 | `resultCode: 11` (필수 파라미터 결측 에러) 확인 |
| **#8** | 잘못된 파라미터 전송 | `yr=INVALID` | 200 / `20` | 0건 | 파라미터 오류 시 XML Fallback 메시지 반환 확인 |
| **#9** | 마지막 페이지 경계 | `yr=2024, p=635, n=10` | 200 / `00` | 6건 | 635페이지에서 마지막 잔여 6건 정확 반환 확인 |

---

## 5. 수치 지표 단위 및 정의 규명

실측 결과에 따라 다음 수치 지표의 단위 및 정의를 확정합니다.

1. **금액 지표 (Currency Metrics)**:
   - 가맹비(`jngBzmnJngAmt`), 교육비(`jngBzmnEduAmt`), 보증금(`jngBzmnGrnteAmt`), 기타비용(`jngBzmnEtcAmt`), 예치금(`depstAmt`), 인테리어비용(`intrrAmt`), 가맹점평균매출액(`avgSlsAmt`): **천원 단위 (KRW 1,000)**.
   - 예: `avgSlsAmt = 115988.0` -> **1억 1,598만 8,000원**.
2. **면적 지표 (Area Metrics)**:
   - 점포기준면적(`storCrtrArea`): **평(3.3㎡) 단위**.
   - 예: `storCrtrArea = 30.0` -> **30평 (약 99.17㎡)**.
3. **단위면적당 지표 (Unit Area Metrics)**:
   - 단위면적인테리어비용(`unitAreaIntrrAmt`): **천원/평 단위**.
   - 면적단위평균매출액(`areaUnitAvgSlsAmt`): **천원/평 단위**.
   - 관계식 검증: `intrrAmt ≈ storCrtrArea * unitAreaIntrrAmt` (30평 * 2,200천원 = 66,000천원 성립).

---

## 6. 호출 한도, 속도 제어 및 장애 복구 (SLA & Retry Policy)

- **호출 예산 통제**:
  - Phase 4A 실증 예산: 최대 30회 엄격 제한 (실제 소모 15회, 잔여 15회 보존).
  - 향후 배치 수집 시: 일일 10,000회 공공데이터 기본 쿼터 준수.
- **요청 간 딜레이**:
  - 단일 스레드 기준 요청 간 `0.35초` 슬립 유지 (공공데이터포털 초당 TPS 초과 방지).
- **지수 백오프 (Exponential Backoff)**:
  - HTTP 429(Rate Limit) 또는 5xx 서버 오류 발생 시: 1차(2초) -> 2차(4초) -> 3차(6초) 대기 후 최대 3회 재시도.
  - 최대 재시도 실패 시 해당 호출 건을 `data_quality_results`에 자동 기록 후 정상 재개.

---

## 7. 보안 및 자격증명 보호 계약

- **하드코딩 금지**: 소스코드, 깃 커밋, 테스트 파일 내에 공공데이터 API 키 원문 하드코딩 절대 금지.
- **마스킹 처리 (Masking)**: 모든 로그, 에러 스택, 콘솔 출력 시 인증키 문자열을 `[MASKED_API_KEY]`로 자동 치환.
- **검증 상태**: 기존 소진공 API 키가 공정위 API에서도 정상 승인되어 추가 키 발급 없이 사용 가능함을 실증 완료함.
