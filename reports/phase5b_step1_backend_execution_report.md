# Phase 5B Step 1: 공정위 거시통계 백엔드 API 구현 및 /status 안전성 보완 보고서

- **문서 번호**: P5B-STEP1-EXEC-2026-003 (`/status` 안전성 보완 완료)
- **작성 일자**: 2026-10-13T19:50:00+09:00
- **프로젝트 경로**: `D:\Franchise_Dashboard`
- **구현 범위**: Phase 5B Step 1 보완 (`/status` 완료 감사 로그 정합성 확보, 미완료 연도 기본값 제외, 이전 연도 메타 도용 원천 차단 및 12대 종합 테스트)
- **검증 상태**: **전체 12개 테스트 케이스 100% 통과 (PASS: 12, FAIL: 0)**

---

## 1. 개요 및 `/status` 안전성 보완 원칙 준수 내역

운영 DB(`data/ftc_macro_statistics_v1.sqlite3`, `data/franchise_analytics_v1.sqlite3`) 및 UI 코드는 일체 수정하지 않고, Step 2 UI 작업은 시작하지 않은 상태에서 `/status` 엔드포인트의 데이터 정합성과 연도 선택 기준의 일관성을 강화하였습니다.

### `/status` 안전성 및 연도 선택 기준 보완 상세

1. **이전 연도 감사 로그 도용 원천 차단**:
   - 기존 코드에 존재하던 "최신 연도의 `audit` 기록이 없을 경우 최신 `COMPLETED` 로그(이전 연도)로 대체"하는 폴백 로직을 **완전히 삭제**하였습니다.
   - DB상 최신 연도에 `COMPLETED` 수집 기록이 없을 때, 이전 연도의 `post_total_count`와 `completed_at`을 최신 연도 메타데이터로 섞어 표시하거나 위장하는 데이터 왜곡을 원천적으로 불가능하도록 차단하였습니다.

2. **일관된 연도 선택 기준 정립 (`get_ftc_available_years()`)**:
   - `ftc_industry_macro_summary`에 특정 연도(예: 2027)가 부분 적재되었더라도, `ftc_ingestion_audit_logs`에 `status = 'COMPLETED'` 수집 완료 기록이 없는 연도는 수집 미완료(In-progress/Failed) 상태로 규정합니다.
   - `get_ftc_available_years()`가 `ftc_industry_macro_summary`와 `ftc_ingestion_audit_logs`를 조인하여 `status = 'COMPLETED'`인 연도만 유효 기준연도(`jng_biz_crtr_yr DESC`)로 추출하도록 기준을 일관되게 정립했습니다.
   - 따라서 수집이 완료되지 않은 연도는 `/status`, `/benchmark/latest`, `/trends`, `/years`의 기본값 및 서비스 목록에서 원천적으로 제외되고, 완료된 직전 연도(2026년)가 최신 기본값으로 안전하게 선택됩니다.

3. **명확한 미완료/오류 상태 반환 (2차 방어층)**:
   - 만약 모킹이나 비정상 상태로 인해 `available_years[0]`에 지정된 연도에 대해 `COMPLETED` 감사 로그가 존재하지 않는 경우:
   - 다른 연도의 완료 로그를 도용하지 않고, `HTTP 500`과 함께 명확한 에러 코드 `ERR_FTC_STATUS_NO_COMPLETED_AUDIT` 및 미완료 안내 메시지를 반환합니다.

4. **운영 DB 불변 및 모의 테스트 추가 (`test_12`)**:
   - 운영 DB를 일체 수정하지 않고 `monkeypatch`를 통해 두 가지 시나리오(미완료 연도의 기본값 제외, COMPLETED 부재 시 명확한 500 에러 반환)를 검증하는 `test_12`를 추가하였습니다.
   - 기존 11개 테스트 및 신규 `test_12`까지 총 12개 테스트가 전수 통과함을 확인하였습니다.

---

## 2. 변경 파일 및 핵심 코드

### `src/stage4e/api/routers/ftc_macro.py`

```python
def get_ftc_available_years() -> List[str]:
    """
    DB에서 수집 완료(status = 'COMPLETED') 감사 기록이 존재하며
    실제 업종 요약(ftc_industry_macro_summary) 데이터가 존재하는 유효 기준연도 목록을
    최신순(내림차순)으로 동적 추출합니다.
    수집 미완료(IN_PROGRESS / FAILED) 상태이거나 완료 기록이 없는 연도는
    기본값 및 제공 연도 목록에서 원천적으로 제외됩니다.
    """
    rows = ftc_query_all("""
        SELECT DISTINCT s.jng_biz_crtr_yr
        FROM ftc_industry_macro_summary s
        INNER JOIN ftc_ingestion_audit_logs a 
            ON s.jng_biz_crtr_yr = a.jng_biz_crtr_yr
        WHERE a.status = 'COMPLETED'
        ORDER BY s.jng_biz_crtr_yr DESC
    """)
    if rows:
        return [r["jng_biz_crtr_yr"] for r in rows]

    audit_rows = ftc_query_all("""
        SELECT DISTINCT jng_biz_crtr_yr
        FROM ftc_ingestion_audit_logs
        WHERE status = 'COMPLETED'
        ORDER BY jng_biz_crtr_yr DESC
    """)
    if audit_rows:
        return [r["jng_biz_crtr_yr"] for r in audit_rows]

    fallback_rows = ftc_query_all("""
        SELECT DISTINCT jng_biz_crtr_yr
        FROM ftc_industry_macro_summary
        ORDER BY jng_biz_crtr_yr DESC
    """)
    return [r["jng_biz_crtr_yr"] for r in fallback_rows]
```

```python
    # GET /api/v1/ftc/status 내부
    audit = ftc_query_one("""
        SELECT jng_biz_crtr_yr, post_total_count, completed_at
        FROM ftc_ingestion_audit_logs
        WHERE status = 'COMPLETED' AND jng_biz_crtr_yr = ?
        ORDER BY audit_id DESC
        LIMIT 1
    """, (latest_year,))
    
    if not audit:
        # 최신 연도에 COMPLETED 수집 기록이 없을 때:
        # 이전 연도의 post_total_count와 completed_at을 최신 연도 메타데이터로 섞어 표시하는 것을 엄격히 차단합니다.
        raise HTTPException(
            status_code=500,
            detail={
                "status": "ERROR",
                "error_code": "ERR_FTC_STATUS_NO_COMPLETED_AUDIT",
                "message": f"최신 기준연도({latest_year})에 대한 수집 완료(COMPLETED) 기록이 존재하지 않아 메타데이터를 제공할 수 없습니다.",
                "latest_year": latest_year
            }
        )
```

---

## 3. 종합 테스트 결과 요약 (`tests/test_phase5b_step1.py`)

- **테스트 환경**: Python 3.14.7, pytest-9.1.1, FastAPI TestClient
- **결과**: **12 PASSED, 0 FAILED**

```
tests/test_phase5b_step1.py::test_01_ftc_status PASSED                   [  8%]
tests/test_phase5b_step1.py::test_02_ftc_benchmark_hansik_2026 PASSED    [ 16%]
tests/test_phase5b_step1.py::test_03_all_8_major_categories PASSED       [ 25%]
tests/test_phase5b_step1.py::test_04_unmapped_category_handling PASSED   [ 33%]
tests/test_phase5b_step1.py::test_05_explicit_year_and_no_fallback PASSED [ 41%]
tests/test_phase5b_step1.py::test_06_fallback_scenario_simulation PASSED [ 50%]
tests/test_phase5b_step1.py::test_07_ftc_trends PASSED                   [ 58%]
tests/test_phase5b_step1.py::test_08_ftc_years PASSED                    [ 66%]
tests/test_phase5b_step1.py::test_09_existing_apis_regression PASSED     [ 75%]
tests/test_phase5b_step1.py::test_10_dynamic_new_year_addition PASSED    [ 83%]
tests/test_phase5b_step1.py::test_11_utc_to_kst_conversion PASSED        [ 91%]
tests/test_phase5b_step1.py::test_12_status_safety_when_latest_year_has_no_completed_audit PASSED [100%]
```

### 세부 검증 항목별 판정
1. **`test_01_ftc_status`**: 동적 최신 연도 판정(`2026`), KST 시각(`2026-10-13T17:53:05+09:00`), `version_string` 내 일관된 KST 시각 반영, `Cache-Control` 헤더 검증 완료.
2. **`test_02_ftc_benchmark_hansik_2026`**: 한식 2026년 실제 DB 18개 핵심 통계 지표와 소수점 둘째 자리까지 100.00% 일치 검증 완료.
3. **`test_03_all_8_major_categories`**: 단일 매핑 4개 및 복수 매핑 4개 전수 정상 응답 및 합산 무결성 검증 완료.
4. **`test_04_unmapped_category_handling`**: 미매핑 업종 요청 시 HTTP 400 + `ERR_CATEGORY_UNMAPPED` 정상 처리.
5. **`test_05_explicit_year_and_no_fallback`**: 사용자가 `year=2024` 요청 시 2024년 고정 반환, `year=2027` 부재 연도 요청 시 타 연도로 자동 대체하지 않고 HTTP 404 + `NO_DATA_FOR_REQUESTED_YEAR` 정상 차단.
6. **`test_06_fallback_scenario_simulation`**: 운영 DB를 일체 변경하지 않고, 모의 환경에서 최신 연도 데이터 부재 시 실제 이용 가능한 이전 연도(2025년)로 원자적 대체 및 `FALLBACK_NOTICE` 배지 정상 표출 확인.
7. **`test_07_ftc_trends`**: 동적 연도 기반 시계열 정렬, 최신 스냅샷 배지, 거시 가이드 문구 동적 반영 검증 완료.
8. **`test_08_ftc_years`**: DB 실제 연도 기반 메타 목록, 최신 연도 기본값(`is_default=True`, 최신 스냅샷), 차상위 연도(`최신 완결 후보`) 동적 라벨링 검증 완료.
9. **`test_09_existing_apis_regression`**: 기존 5대 분석 API(`summary`, `regions`, `categories`, `brands`, `spatial`)가 100% 정상 작동 유지 확인.
10. **`test_10_dynamic_new_year_addition`**: 운영 DB 미수정 상태에서 2027년이 DB에 신규 추가된 상황을 모킹하여 `/status`, `/years`, `/trends`, `/benchmark/latest`가 2027년을 기본 최신 연도로 인식하고, 데이터 부재 시 직전 이용 가능 연도(2026년)로 원자적 대체하는 전체 라이프사이클 검증 완료.
11. **`test_11_utc_to_kst_conversion`**: SQLite `CURRENT_TIMESTAMP`(UTC, `2026-10-13 08:53:05`)가 한국 표준시(`2026-10-13T17:53:05+09:00`, +09:00 명시)로 오차 없이 변환되며, `version_string` 문구에도 일관되게 적용됨을 검증 완료.
12. **`test_12_status_safety_when_latest_year_has_no_completed_audit`**: DB상 최신 연도(2027)에 `COMPLETED` 수집 기록이 없을 때:
    - (시나리오 1) `get_ftc_available_years()`가 2027년을 기본값에서 자동 제외하고 완료된 2026년을 최신으로 선택하여 정상 서비스 유지.
    - (시나리오 2) 최신 연도에 `COMPLETED` 기록이 없는 상태로 `/status`에 도달 시, 이전 연도의 모수와 시각을 도용하지 않고 `HTTP 500 ERR_FTC_STATUS_NO_COMPLETED_AUDIT` 명확한 에러를 반환함을 완벽 검증.
13. **기존 Stage 4E 테스트 15종**: `tests/test_phase4_stage4e.py` 15개 테스트 전수 통과 (**15 PASSED, 100%**).

---

## 4. 결론

- `/status` 엔드포인트의 데이터 정합성 보완이 완료되었습니다.
- 최신 연도에 `COMPLETED` 완료 기록이 없을 때 이전 연도의 `post_total_count`와 `completed_at`을 혼합 표시하는 위험 로직이 완전히 제거되었습니다.
- 연도 선택 기준이 `COMPLETED` 완료 기록 기반으로 통일되어 미완료 연도는 기본값에서 자동으로 제외되며, 감사 로그 부재 시 명확한 오류 상태를 반환합니다.
- 운영 DB와 UI 코드는 전혀 변경되지 않았으며, Step 2 UI 작업은 시작하지 않고 대기 중입니다.
