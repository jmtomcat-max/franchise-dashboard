# Phase 4F: 공정거래위원회 외식업 거시 가맹통계 다년도(2023~2026) 전수 수집 및 아키텍처 설계서 (R3.1 독립 완결판)

- **문서 번호**: P4F-ARCH-2026-006-R3.1
- **작성 일자**: 2026-10-13 (R3.1 최종 보완일시: 2026-10-13)
- **프로젝트 경로**: `D:\Franchise_Dashboard`
- **설계 상태**: **승인 대기 (Draft R3.1 - Awaiting User Approval)**
- **대상 데이터**: 2023년 ~ 2026년 공정거래위원회 (AI친화)가맹정보 외식업종 현황 4개년 전수 (총 23,537건, 238페이지)
- **엔드포인트**: `https://apis.data.go.kr/1130000/FftcBrandFrcsBzmnIntgInfoEatoutTpbizStats2_Service/getBrandFrcsBzmnIntgInfoEatoutTpbiz2`

---

## 1. 개요 및 수집 범위 확정 (Collection Scope)

본 문서는 실측 조사를 통해 확인된 최신성(2026년 스냅샷 가용) 및 시계열 분석 가치를 반영하여, **2023년부터 2026년까지 4개년 전수 데이터를 안전하게 수집·적재·분석하기 위한 독립 완결형 R3.1 설계서**입니다.

> [!IMPORTANT]
> **실행 보류 원칙**: 사용자 승인 전까지 **실제 23,537건 API 전수 수집 및 DB 적재는 일체 실행하지 않으며**, 본 설계서와 체크리스트만 유지·관리합니다.

### 1.1 연도별 수집 모수 및 페이지 규모 (교차 검증 완료)
각 연도당 `numOfRows = 100` 기준 동적 산출 페이지 수입니다.

| 기준연도 (`jngBizCrtrYr`) | 재무연도 (`fyr`) | 데이터 상태 구분 | 레코드 건수 | 요청 페이지 수 | 산출 공식 (`ceil(cnt/100)`) |
| :---: | :---: | :--- | :---: | :---: | :---: |
| **`2023`** | `2022` | 과거 마감 연도 | **6,151건** | **62페이지** | $\lceil 6,151 / 100 \rceil = 62$ |
| **`2024`** | `2023` | 이전 마감 연도 | **6,346건** | **64페이지** | $\lceil 6,346 / 100 \rceil = 64$ |
| **`2025`** | `2024` | **최신 완결 후보 연도** | **6,519건** | **66페이지** | $\lceil 6,519 / 100 \rceil = 66$ |
| **`2026`** | `2025` | **최신 제공 스냅샷** | **4,521건** | **46페이지** | $\lceil 4,521 / 100 \rceil = 46$ |
| **합계 (4개년)** | - | - | **23,537건** | **238페이지** | $62 + 64 + 66 + 46 = \mathbf{238}$ |

- **모수 및 페이지 일치성 검증**: 마크다운 본문과 메타데이터 JSON 간 건수(23,537) 및 페이지(238) 100% 일치 확인.

---

## 2. 최신자료 표시 및 연도 혼합 금지 정책 (Display & Integrity Contract)

### 2.1 최신 기준연도 기본 설정
1. **대시보드 및 지도의 기본 연도**:
   - 데이터가 존재하는 가장 최신 `jngBizCrtrYr`인 **`2026년`**을 공정위 거시 벤치마크 기본 연도로 설정합니다.
   - 최신연도 데이터가 존재함에도 과거 연도를 임의 기본값으로 사용하지 않습니다.
2. **2026년 공식 UI 표기 표준**:
   > **`2026년 공정위 등록 기준 · 2025 회계연도 실적`**
3. **대체 연도(Fallback) 표시 규칙**:
   - 특정 업종이나 지표에서 2026년 데이터가 부재할 경우에만 직전 연도(2025년)로 대체합니다.
   - 대체 시 UI 배지 및 주석으로 대체 사실을 명시합니다. *(예: "⚠️ 2026년 미등록 업종으로 2025년 등록 실적 대체 표시 중")*

### 2.2 연도 혼합 절대 금지 원칙 (Strict No-Mixing Rule)
- **원칙**: 하나의 통계값을 계산하거나 단일 위젯을 구성할 때 **서로 다른 연도의 데이터를 절대 혼합하지 않습니다.**
- **원자적 대체**: 2026년 특정 지표가 없어 직전 연도로 대체할 경우, 해당 위젯 전체를 2025년 데이터로 일괄 전환하고 `2025년 대체 표시`를 명시합니다.
- **분모·분자 일치성**: 위젯 내부의 분자(매출액 합계), 분모(가맹점수 합계), 표본 수($N$)는 모두 **동일한 단일 기준연도 데이터만 사용**해야 합니다.

---

## 3. 다년도 추세 분석 체계: 전체 모집단 vs 존속 브랜드 균형 패널

왜곡 없는 다년도 통계 분석을 위해 다음 두 가지 분석 축을 엄격히 구분하여 제공합니다.

### 3.1 축 1: 전체 모집단 거시 추세 (Full Population Macro Trend)
- **정의**: 해당 연도에 등록된 외식 프랜차이즈 전체를 대상으로 업종별 평균, 중앙값, 점포수 가중평균 산출.
- **필수 지표**: 단순평균, 중앙값, 가중평균과 함께 **반드시 연도별 유효 표본 수($N$, 브랜드 수 및 가맹점 수)를 병기**합니다.
- **2026년 주의 표기**:
  - `최신 제공 스냅샷` 배지를 부착하고, 현재 시점 스냅샷으로서 추가 등록 가능성이 있음을 명시합니다.
  - 단순 총건수(4,521건 vs 6,519건)나 총점포 수의 단순 합계 비교는 모집단 규모 차이로 왜곡될 수 있으므로 **직접 합계 비교 주의 경고**를 표시합니다.

### 3.2 축 2: 존속 브랜드 균형 패널 (Balanced Panel of Surviving Brands)
- **명칭 정정**: "생존편향 제거" 표현을 삭제하고, **`존속 브랜드 균형 패널`**로 공식 명명합니다.
- **생존편향 한계 명시**:
  - 본 분석은 4개년 연속 관측된 브랜드만 추적하므로, **신규 진입 브랜드 및 폐업·이탈 브랜드가 분석에서 제외되어 생존편향(Survivorship Bias)이 발생할 수 있음**을 보고서와 UI에 명확히 주석 처리합니다.
- **코호트 전이 지표 산출**:
  단순 연속 관측 브랜드 외에 다음 3대 동태적 지표를 별도 산출하여 저장합니다:
  1. **연도별 신규 진입 수 (New Entries)**: $t-1$년에 미존재하고 $t$년에 신규 관측된 브랜드 수
  2. **연도별 이탈 수 (Exits)**: $t-1$년에는 존재했으나 $t$년에 관측되지 않은 브랜드 수
  3. **연도별 연속 관측 수 (Continuous Observation)**: $t-1$년과 $t$년에 연속 관측된 브랜드 수

---

## 4. 가명 ID 연도 안정성 검증 프로토콜 (Pseudonym ID Stability Audit)

가명브랜드관리번호(`alsBrandMngNo`)가 연도 간 동일 브랜드를 지속적으로 식별하는 키인지 실측 검증하기 전까지는 패널 연결키로 확정하지 않습니다.

### 4.1 연도 안정성 실측 검증 항목
수집 완료 후 즉시 다음 쿼리를 통해 ID 안정성을 전수 측정합니다:
1. **인접 연도별 교집합 및 지속률**:
   $$\text{Persistence Rate} = \frac{|\text{Brands}_{t-1} \cap \text{Brands}_t|}{|\text{Brands}_{t-1}|} \times 100\%$$
2. **신규 진입·이탈·재등장(Re-appearance) 규모**:
   $t-2$년에 존재 $\rightarrow$ $t-1$년에 결측 $\rightarrow$ $t$년에 재등장하는 비율 측정.
3. **가맹본부 관리번호(`alsJnghqMngNo`) 변경률**:
   동일 `alsBrandMngNo` 내에서 본부 번호가 변경된 비율 측정.

### 4.2 안정성 판정 및 중단 규칙
- **안정성 기준 충족 시**: `alsBrandMngNo`를 존속 브랜드 균형 패널의 연결키로 승격.
- **안정성 부족 시 (해시 재발급 등으로 연도 간 단절 확인 시)**:
  - **패널 분석을 즉시 중단(Abort)**하고, 축 1의 **`전체 모집단 추세 분석`만 제공**합니다.
  - 평문 브랜드명이 존재하지 않으므로, 텍스트나 수치 기반의 **임의 추정 매칭은 일체 수행하지 않습니다.**

---

## 5. 수집 안정성 및 2026년 변동 스냅샷 양방향 검증

### 5.1 연도별 수집 시작/종료 양방향 모수 대사 (Pre & Post Audit)
1. **시작 시점 (`Pre-Ingestion`)**:
   - 수집 시작 직전 `pageNo=1, numOfRows=1`을 선행 호출하여 시작 시점 `pre_total_count`를 확인합니다.
   - $\lceil \text{pre\_total\_count} / 100 \rceil$로 페이지 수를 동적 계산합니다.
2. **수집 실행 (`Atomic Ingestion`)**:
   - 페이지 단위 원자적 트랜잭션으로 적재를 수행합니다.
3. **종료 시점 (`Post-Ingestion`)**:
   - 모든 페이지 적재 직후 `post_total_count`를 재조회합니다.
   - **완료 판정 조건**:
     $$\text{pre\_total\_count} == \text{post\_total\_count} == \text{total\_saved\_records} == \sum \text{items\_fetched}$$
4. **변동 스냅샷 예외 처리 (`UNSTABLE_SNAPSHOT`)**:
   - 수집 도중 공정위 포털에 새 데이터가 등록되어 `pre_total_count != post_total_count`가 발생할 경우:
     - 해당 연도를 임의 완료 처리하지 않고 **`UNSTABLE_SNAPSHOT`**으로 플래그 지정하고 파이프라인을 일시 중단 후 사용자에게 보고합니다.
5. **2026년 스냅샷 UI 데이터 버전 연결**:
   - 2026년 데이터는 수집 시작·종료 시각 및 확정 `totalCount`를 UI 데이터 버전에 바인딩합니다:
     *(예: `데이터 버전: 2026년 스냅샷 (2026-10-13 18:00 기준, 4,521건)`)*

---

## 6. 지도 적용 범위 및 공간 데이터 경계 (Map Integration Boundaries)

1. **개별 점포 위치 매핑 금지**:
   - 공정위 API에는 매장 위경도 좌표(Lat/Lon)가 없으므로 지도상의 점(마커)이나 3D 건물 레이어에 절대 사용하지 않습니다.
2. **역할 분담 원칙**:
   - **공간 좌표/밀집도/3D 건물**: 기존 소상공인진흥공단(SEMAS) 73.5만 개 점포 데이터가 전담.
   - **공정위 데이터의 역할**: 지도에서 특정 행정구역 및 8대 외식업종을 선택했을 때 표출되는 **거시 벤치마크 위젯, 사이드 패널, 팝업, 비교 지표**에만 사용.
3. **본부 소재지 (`jnghqRgnNm`) 해석 통제**:
   - 본부 소재지는 법인 본사 위치이며 점포 소재지가 아니므로, 시도별 가맹점 분포로 해석하거나 지도에 표현하지 않습니다.

---

## 7. 완전 병합 데이터베이스 스키마 및 안전장치 DDL (`data/ftc_macro_statistics_v1.sqlite3`)

### 7.1 원본 응답 보존 테이블 (`ftc_raw_api_responses`)
```sql
CREATE TABLE IF NOT EXISTS ftc_raw_api_responses (
    response_id INTEGER PRIMARY KEY AUTOINCREMENT,
    jng_biz_crtr_yr TEXT NOT NULL,          -- '2023', '2024', '2025', '2026'
    page_no INTEGER NOT NULL,               -- 요청 페이지 번호
    num_of_rows INTEGER NOT NULL DEFAULT 100,
    http_status INTEGER NOT NULL,           -- HTTP 상태 코드 (200)
    result_code TEXT NOT NULL,              -- API 결과 코드 ('00')
    total_count INTEGER NOT NULL,           -- API 전체 건수
    item_count INTEGER NOT NULL,            -- 실제 수신 항목 수
    payload_json TEXT NOT NULL,             -- 응답 JSON 원문 (인증키 제외)
    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_raw_page UNIQUE (jng_biz_crtr_yr, page_no)
);
```

### 7.2 정제 레코드 테이블 (`ftc_brand_macro_records`)
```sql
CREATE TABLE IF NOT EXISTS ftc_brand_macro_records (
    record_id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- [원본 수집 위치 메타데이터 - 중복 방지 및 멱등성 보장]
    source_page_no INTEGER NOT NULL,
    source_row_index INTEGER NOT NULL,
    row_fingerprint TEXT NOT NULL,
    
    -- [실제 36개 응답 필드 전수]
    als_brand_mng_no TEXT NOT NULL,
    als_jnghq_mng_no TEXT NOT NULL,
    jng_biz_crtr_yr TEXT NOT NULL,
    jnghq_rgn_nm TEXT,
    jng_biz_strt_ymd TEXT,
    tpbiz_mclsf_nm TEXT NOT NULL,
    frcs_cnt INTEGER NOT NULL DEFAULT 0,
    dms_cnt INTEGER NOT NULL DEFAULT 0,
    prvyr_frcs_cnt INTEGER DEFAULT 0,
    prvyr_dms_cnt INTEGER DEFAULT 0,
    jng_bzmn_jng_amt REAL,
    jng_bzmn_edu_amt REAL,
    jng_bzmn_grnte_amt REAL,
    jng_bzmn_etc_amt REAL,
    depst_amt REAL,
    unit_area_intrr_amt REAL,
    intrr_amt REAL,
    prvyr_jng_bzmn_jng_amt REAL,
    prvyr_jng_bzmn_edu_amt REAL,
    prvyr_jng_bzmn_grnte_amt REAL,
    prvyr_jng_bzmn_etc_amt REAL,
    prvyr_depst_amt REAL,
    prvyr_unit_area_intrr_amt REAL,
    prvyr_intrr_amt REAL,
    frst_ctrt_yycnt REAL,
    prlg_ctrt_yycnt REAL,
    stor_crtr_area REAL,
    prvyr_frst_ctrt_yycnt REAL,
    prvyr_prlg_ctrt_yycnt REAL,
    prvyr_stor_crtr_area REAL,
    fyr TEXT,
    avg_sls_amt REAL,
    area_unit_avg_sls_amt REAL,
    prvyr_fyr TEXT,
    prvyr_avg_sls_amt REAL,
    prvyr_area_unit_avg_sls_amt REAL,
    
    -- [창업비용 잠정 파생지표 (공식 표기 금지)]
    calc_depst_diff REAL,
    calc_depst_is_matched INTEGER,
    tentative_startup_cost_thousand REAL,
    startup_cost_calc_method TEXT,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_source_position UNIQUE (jng_biz_crtr_yr, source_page_no, source_row_index)
);

CREATE INDEX IF NOT EXISTS idx_ftc_records_year_tpbiz ON ftc_brand_macro_records (jng_biz_crtr_yr, tpbiz_mclsf_nm);
CREATE INDEX IF NOT EXISTS idx_ftc_records_brand_year ON ftc_brand_macro_records (als_brand_mng_no, jng_biz_crtr_yr);
CREATE INDEX IF NOT EXISTS idx_ftc_records_fingerprint ON ftc_brand_macro_records (row_fingerprint);
```

### 7.3 체크포인트 테이블 (`ftc_ingestion_checkpoints`)
```sql
CREATE TABLE IF NOT EXISTS ftc_ingestion_checkpoints (
    checkpoint_id INTEGER PRIMARY KEY AUTOINCREMENT,
    jng_biz_crtr_yr TEXT NOT NULL,
    page_no INTEGER NOT NULL,
    num_of_rows INTEGER NOT NULL DEFAULT 100,
    status TEXT NOT NULL CHECK (status IN ('PENDING', 'SUCCESS', 'FAILED', 'RETRY')),
    items_fetched INTEGER DEFAULT 0,
    items_saved INTEGER DEFAULT 0,
    latency_ms INTEGER,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_checkpoint_page UNIQUE (jng_biz_crtr_yr, page_no)
);
```

### 7.4 수집 감사 로그 테이블 (`ftc_ingestion_audit_logs`)
```sql
CREATE TABLE IF NOT EXISTS ftc_ingestion_audit_logs (
    audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
    jng_biz_crtr_yr TEXT NOT NULL,
    pre_total_count INTEGER NOT NULL,           -- 수집 전 조회 건수
    post_total_count INTEGER,                   -- 수집 완료 후 조회 건수
    total_pages_expected INTEGER NOT NULL,      -- 예상 페이지 수
    total_pages_succeeded INTEGER NOT NULL,     -- 성공 페이지 수
    total_records_saved INTEGER NOT NULL,       -- 실제 적재 건수
    discrepancy_count INTEGER NOT NULL,         -- 오차 건수 (0이어야 정상)
    status TEXT NOT NULL CHECK (status IN ('IN_PROGRESS', 'COMPLETED', 'FAILED', 'UNSTABLE_SNAPSHOT')),
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);
```

### 7.5 재실행 가능한 업종 도메인 실측 조사 테이블 (`ftc_tpbiz_domain_survey`)
```sql
CREATE TABLE IF NOT EXISTS ftc_tpbiz_domain_survey (
    survey_id INTEGER PRIMARY KEY AUTOINCREMENT,
    jng_biz_crtr_yr TEXT NOT NULL,
    tpbiz_mclsf_nm TEXT NOT NULL,
    record_count INTEGER NOT NULL,
    total_franchise_stores INTEGER NOT NULL,
    total_direct_stores INTEGER NOT NULL,
    record_percentage REAL NOT NULL,
    surveyed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_domain_survey UNIQUE (jng_biz_crtr_yr, tpbiz_mclsf_nm)
);
```

### 7.6 업종별 통계 요약 테이블 (`ftc_industry_macro_summary`)
단순평균, 중앙값, 가중평균 및 **정확한 분자·분모·표본수**를 함께 저장하여 8대 대분류 롤업 시 재계산이 가능하도록 합니다.

```sql
CREATE TABLE IF NOT EXISTS ftc_industry_macro_summary (
    summary_id INTEGER PRIMARY KEY AUTOINCREMENT,
    jng_biz_crtr_yr TEXT NOT NULL,
    tpbiz_mclsf_nm TEXT NOT NULL,
    
    -- 표본 모수
    record_count INTEGER NOT NULL,              -- 총 브랜드 수 (N)
    sum_frcs_cnt INTEGER NOT NULL,              -- 총 가맹점 수
    sum_dms_cnt INTEGER NOT NULL,               -- 총 직영점 수
    
    -- 매출 지표 및 분모 (단위: 천원)
    brand_simple_avg_sls_amt REAL,              -- 브랜드 단순 평균매출
    store_weighted_avg_sls_amt REAL,            -- 점포수 가중 평균매출
    median_sls_amt REAL,                        -- 중위 매출
    sls_valid_record_count INTEGER NOT NULL,    -- 매출 유효 레코드 수 (단순평균 분모)
    sls_null_record_count INTEGER NOT NULL,     -- 매출 결측 레코드 수
    sum_sls_amount REAL,                        -- SUM(avgSlsAmt) (단순평균 분자)
    sum_weighted_sls_amount REAL,               -- SUM(avgSlsAmt * frcsCnt) (가중평균 분자)
    denom_store_weighted_sls INTEGER,           -- 매출 유효 가맹점수 합계 (가중평균 분모)
    
    -- 면적단위(3.3㎡) 매출 지표
    brand_simple_avg_area_sls REAL,
    store_weighted_avg_area_sls REAL,
    median_area_sls REAL,
    area_sls_valid_count INTEGER,
    
    -- 창업비용 지표 (단순평균 및 중앙값, 단위: 천원)
    avg_jng_amt REAL,       median_jng_amt REAL,       valid_jng_cnt INTEGER,
    avg_edu_amt REAL,       median_edu_amt REAL,       valid_edu_cnt INTEGER,
    avg_grnte_amt REAL,     median_grnte_amt REAL,     valid_grnte_cnt INTEGER,
    avg_etc_amt REAL,       median_etc_amt REAL,       valid_etc_cnt INTEGER,
    avg_intrr_amt REAL,     median_intrr_amt REAL,     valid_intrr_cnt INTEGER,
    avg_unit_intrr REAL,    median_unit_intrr REAL,    valid_unit_intrr_cnt INTEGER,
    avg_total_startup REAL, median_total_startup REAL, valid_total_startup_cnt INTEGER,
    
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_ind_summary UNIQUE (jng_biz_crtr_yr, tpbiz_mclsf_nm)
);
```

---

## 8. 수집 파이프라인 안전장치 처리 규칙 (Operational Safeguards)

1. **페이지 단위 단일 원자적 트랜잭션**:
   - `ftc_raw_api_responses` + `ftc_brand_macro_records` + `ftc_ingestion_checkpoints` 갱신을 단일 `BEGIN IMMEDIATE ... COMMIT`으로 실행.
   - 예외 발생 시 즉시 `ROLLBACK`하여 부분 레코드 잔류 차단.
2. **시작 시 `PENDING` 자동 복구**:
   - 수집 기동 시 `status = 'PENDING'`으로 방치된 레코드를 `RETRY`로 일괄 전환 후 재개 우선순위에 포함.
3. **재수집 중복 방지 (선제 삭제)**:
   - 동일 페이지 재수집 시 트랜잭션 내에서 `DELETE FROM ftc_brand_macro_records WHERE jng_biz_crtr_yr = ? AND source_page_no = ?`를 선행 실행.
4. **최대 5회 재시도 및 치명적 실패 중단**:
   - 페이지별 재시도 한도 초과 시 파이프라인 전체를 즉시 중단(Abort)하고 에러 보고.
5. **4단계 고유키 순차 검증 및 중복 무손실 보존**:
   - ① (연도+브랜드) $\rightarrow$ ② (연도+브랜드+본부) $\rightarrow$ ③ (연도+브랜드+업종) $\rightarrow$ ④ (연도+브랜드+본부+업종) 검증.
   - 4단계 모두 중복 발생 시 **행 삭제/덮어쓰기 절대 금지**, 원본 위치 및 SHA-256 `row_fingerprint`를 온전히 보존하고 격리 테이블 적재 후 사용자 보고.
6. **창업비용 잠정 산식 실측 검증**:
   - 전수 데이터에서 `calc_depst_diff = depst_amt - (jng + edu + grnte)` 오차를 전수 실측하되, 100% 일치하더라도 "공식 산식"이 아닌 **`전수 데이터에서 검증된 파생 산식`**으로 표기.
7. **8대 대분류 롤업 시 '평균의 단순 평균' 절대 금지**:
   - `ftc_industry_macro_summary`에 저장된 분자(`sum_sls_amount`, `sum_weighted_sls_amount`)와 분모(`sls_valid_record_count`, `denom_store_weighted_sls`)를 합산하여 재계산.

---

## 9. R3.1 종합 검증 체크리스트

| 번호 | 점검 항목 | 세부 검증 기준 | 상태 |
| :---: | :--- | :--- | :---: |
| **1** | **4개년 수집 규모** | 2023(62p), 2024(64p), 2025(66p), 2026(46p) 총 238p/23,537건 일치 확인 | **PASS** (설계 반영) |
| **2** | **패널 분석 정정** | "생존편향 제거" 삭제, `존속 브랜드 균형 패널` 명명 및 생존편향 한계 명시 | **PASS** (설계 반영) |
| **3** | **동태적 전이 지표** | 신규 진입 수, 이탈 수, 연속 관측 수 별도 산출 설계 | **PASS** (설계 반영) |
| **4** | **가명 ID 안정성 검증** | 인접연도 교집합/변경률 실측 전 패널 연결키 확정 금지, 부족 시 패널 중단 | **PASS** (설계 반영) |
| **5** | **양방향 모수 대사** | 시작 전/후 totalCount 대사, 불일치 시 `UNSTABLE_SNAPSHOT` 표시 및 중단 | **PASS** (설계 반영) |
| **6** | **2026 스냅샷 버전** | 수집 시각 및 확정 모수를 UI 데이터 버전 문자열에 연결 | **PASS** (설계 반영) |
| **7** | **연도 혼합 금지** | 단일 위젯 내 연도 혼합 금지, 2026 부재 시 위젯 전체 2025 대체 및 배지 안내 | **PASS** (설계 반영) |
| **8** | **용어 거버넌스 준수** | 2025년 `최신 완결 후보 연도`, 2026년 `최신 제공 스냅샷` 단정 표현 배제 | **PASS** (설계 반영) |
| **9** | **지도 경계 준수** | 공정위 데이터를 점포 좌표로 지도에 렌더링하지 않고 거시 벤치마크 패널로 분리 | **PASS** (설계 반영) |
| **10** | **R2-Final 완전 병합** | 원자적 트랜잭션, 롤백, PENDING 복구, 선삭제, 4단계 PK, DDL 전수 수록 | **PASS** (설계 반영) |
| **11** | **수집 실행 보류** | **사용자의 R3.1 최종 검토 및 승인 전까지 실제 23,537건 수집 실행 보류** | **대기 중 (HOLD)** |

---

## 10. 현재 상태 및 사용자 최종 승인 대기

현재 **R3.1 독립 완결 설계서 작성만 완료**되었으며, 실제 API 호출 및 DB 적재는 일체 착수하지 않고 대기 중입니다.
본 R3.1 설계서를 확인하시고 최종 실행을 승인해 주시면, 즉시 안전하게 4개년 전수 수집(23,537건) 및 분석 데이터베이스 구축을 착수하겠습니다.
