# Phase 8 Step 8-1: 테스트 체계 표준화 보고서 (Test Infrastructure Standardization)

## 1. 개요 및 배경

기존 `scripts/run_tests.py`는 과거 단계(Phase 4, Phase 5B)의 82개 테스트를 `TEST_SUITES` 리스트에 하드코딩된 파일 및 기대 건수로 관리하고 있었으며, 테스트 통과 여부를 콘솔 출력의 마지막 줄에서 정규식(`re.search(r"(\d+)\s+passed", line)`)으로 스크래핑하여 파싱하고 있었습니다.

이로 인해 다음과 같은 심각한 결함이 존재했습니다:
1. **신규 테스트 누락**: Phase 7에서 추가된 회귀 테스트(백업 보존 3개, 런북 정합성 50개 등 53개)가 `run_tests.py`의 기본 실행 대상에 포함되지 못하고 누락됨.
2. **수동 유지보수 비용 발생**: 테스트가 추가되거나 변경될 때마다 기대 건수(`expected_count`)와 파일 목록을 수동으로 수정해야 함.
3. **콘솔 정규식 파싱의 취약성**: 터미널 출력 버퍼링, 경고 메시지 출력 순서 변경, 줄바꿈 등에 따라 테스트 결과를 잘못 파싱할 위험 존재.
4. **단일 프로세스 실행 시 Windows Access Violation (0xC0000005) 발생**: 수많은 C-Extension, SQLite3 핸들, 이벤트루프가 단일 pytest 프로세스에 누적되어 특정 환경(`test_11_views_accessibility`)에서 프로세스가 비정상 종료되는 간섭 현상 발생.

Phase 8 Step 8-1에서는 이러한 문제를 완전히 해결하기 위해 **pytest 자동 테스트 발견(Auto Discovery)**, **파일별 Subprocess 프로세스 완전 격리(Subprocess Isolation)** 및 **표준 JUnit XML 기반 구조화 파싱 및 통합 병합** 체계로 전면 전환하였습니다.

---

## 2. 주요 개선 사항

### 2.1 pytest 자동 테스트 발견 (Auto Discovery) 적용
- **하드코딩 완전 제거**: 파일 목록 및 각 스위트별 기대 건수 하드코딩을 완전히 제거.
- **자동 수집 및 집계**: `tests/` 디렉터리 내의 모든 유효한 테스트 파일(`test_*.py`, `*_test.py`)을 `discover_test_files()`가 자동으로 탐색 및 수집하여 단일 파이프라인으로 실행.
- **확장성 보장**: 향후 신규 테스트 모듈이나 테스트 함수가 추가되더라도 러너 코드 수정 없이 100% 자동 반영.

### 2.2 파일별 Subprocess 완전 격리 (Subprocess Isolation)
- **프로세스 레벨 격리**: 자동 발견된 각 테스트 파일/모듈을 독립된 `python -m pytest` 서브프로세스로 개별 실행.
- **간섭 및 크래시 원천 차단**: 이전 테스트의 SQLite3 데이터베이스 연결 잔재, C-Extension 라이브러리 메모리 누수, 비동기 이벤트 루프 상태 오염을 완벽히 격리하여 Windows `0xC0000005 (STATUS_ACCESS_VIOLATION)` 크래시를 원천 방지.
- **단독 실행과 동일한 안정성 보장**: 전체 10개 모듈 154개 테스트가 단독 실행 시와 완전히 동일한 깨끗한 메모리 환경에서 순차 실행됨.

### 2.3 JUnit XML 기반 구조화 파싱 및 통합 병합 (콘솔 정규식 완전 배제)
- **표준 DOM 파싱**: 각 격리 프로세스에서 pytest가 생성한 JUnit XML(`xunit2`)을 파이썬 표준 라이브러리 `xml.etree.ElementTree`로 전수 파싱.
- **결과 통합 병합 (`merge_junit_xmls`)**: 각 서브프로세스의 개별 JUnit XML들을 하나의 루트 `<testsuites>` DOM 구조로 병합하여 최종 산출물(`reports/phase8_step1_junit.xml`)로 일원화 저장.
- **하위 디렉터리 모듈 고유 분리 집계**: `file` 속성 및 `classname` 경로를 분석하여 서브디렉터리 내 모듈(`tests.unit.test_alpha`, `tests.unit.test_beta` 등)이 단일 디렉터리로 뭉개지지 않고 각각 고유한 모듈과 파일 경로로 정확하게 분리 집계되도록 보장.

### 2.4 오류 보고서 집계 및 필터 실행 정합성 (Codex 검토 반영)
- **일반 assertion 실패와 Crash의 정밀 분리**: 일반 assertion 실패(exit 1)는 정상적인 테스트 실패(failures)로만 처리하고 `crashes`에 오분류되지 않도록 분리.
- **단일 소스 기반 XML/JSON 집계 일치**: 정상 XML 생성 후 프로세스 크래시 시 JSON과 JUnit XML 모두에 동일하게 process_crash 에러 노드를 반영하며, 손상된 XML 파싱 실패 시에도 중복 집계 없이 단일 에러로 정확하게 집계.
- **필터(-k/-m) 실행 시 exit 5 정상 처리**: 필터링으로 인해 특정 파일에서 매칭 테스트가 없는 것(exit 5)을 정상적인 필터 제외로 처리하여 `-x` (fail-fast) 시 오탐 중단을 방지하고, 전체 0건일 때만 정상적으로 미발견 실패 처리.
- **테스트 미발견 시 에러 JUnit XML 생성**: 테스트 미발견 시 이전 실행의 잔재 XML이 남아 오인되지 않도록, 오류를 나타내는 표준 JUnit XML(`tests="1" errors="1"`)을 즉시 덮어써 생성.

### 2.5 표준 구조화 리포트 생성 및 Verbose 출력 지원
- `--json <path>`: 타임스탬프, 실행 환경, 격리 모드(`subprocess_per_file`), pytest 종료 상태, 종합 통계, 서브프로세스 실행 목록(`subprocess_runs`), 크래시 기록(`crashes`), 모듈별 집계, 실패 케이스 상세 정보를 담은 구조화된 JSON 리포트 저장.
- `--junitxml <path>`: 병합된 표준 JUnit XML 아티팩트 보존.
- 유연한 CLI 옵션: `-k` (키워드 필터), `-m` (마커 필터), `-x` (첫 실패 시 중단), `-v` / `--verbose` (캡처된 상세 pytest 출력을 콘솔에 온전히 노출), `--target` (특정 모듈/경로 지정) 지원.

---

## 3. 전체 테스트 스위트 실행 결과 요약 (2회 연속 전수 통과)

표준화된 격리 러너 `scripts/run_tests.py`를 통해 `tests/` 디렉터리 내 10개 모듈 총 154개 테스트를 2회 연속 실행하였으며, 두 번 모두 결함이나 크래시 없이 100% 통과했습니다.

### 3.1 1회차 전체 실행 결과
- **실행 명령**: `.venv/Scripts/python.exe scripts/run_tests.py --target tests --json reports/phase8_step1_test_summary.json --junitxml reports/phase8_step1_junit.xml`
- **전체 결과**: **154 / 154 PASS (100% 통과, 0 Failures, 0 Errors, 0 Skipped, 0 Crashes)**
- **총 실행 시간**: 56.42초 (총 경과 시간: 56.45초)
- **종료 코드**: `0` (성공)

### 3.2 2회차 전체 실행 결과 (연속 재검증)
- **실행 명령**: `.venv/Scripts/python.exe scripts/run_tests.py --target tests --json reports/phase8_step1_test_summary.json --junitxml reports/phase8_step1_junit.xml`
- **전체 결과**: **154 / 154 PASS (100% 통과, 0 Failures, 0 Errors, 0 Skipped, 0 Crashes)**
- **총 실행 시간**: 55.40초 (총 경과 시간: 55.42초)
- **종료 코드**: `0` (성공)

### 3.3 모듈별 상세 실행 통계 (2회차 기준)

| 모듈명 | 대상 파일 | 테스트 수 | 결과 | 소요시간 | 설명 |
|:---|:---|:---:|:---:|:---:|:---|
| `tests.test_phase4_stage4a` | `tests/test_phase4_stage4a.py` | 14 | **PASS** | 2.30s | 공공데이터 수집기 및 API 계약 테스트 |
| `tests.test_phase4_stage4b` | `tests/test_phase4_stage4b.py` | 15 | **PASS** | 1.79s | 브랜드 정규화 및 클러스터링 평가 테스트 |
| `tests.test_phase4_stage4c` | `tests/test_phase4_stage4c.py` | 11 | **PASS** | 2.20s | 80대 공인 브랜드 마스터 및 검증 테스트 |
| `tests.test_phase4_stage4d` | `tests/test_phase4_stage4d.py` | 11 | **PASS** | 7.70s | 8대 대분류/48대 중분류 매핑 무결성 테스트 (0xC0000005 완전 해결) |
| `tests.test_phase4_stage4e` | `tests/test_phase4_stage4e.py` | 15 | **PASS** | 3.90s | 73.5만 점포 다차원 공간 집계 및 API 테스트 |
| `tests.test_phase5b_step1` | `tests/test_phase5b_step1.py` | 12 | **PASS** | 2.64s | 공정위 거시통계 및 벤치마크 API 테스트 |
| `tests.test_phase5b_step2_supplement` | `tests/test_phase5b_step2_supplement.py` | 4 | **PASS** | 2.24s | 연도 자동/수동 선택 및 원자적 폴백 보완 테스트 |
| `tests.test_phase7_backup_retention` | `tests/test_phase7_backup_retention.py` | 3 | **PASS** | 1.52s | SQLite 온라인 백업 보존 주기 회귀 테스트 |
| `tests.test_phase7_runbook_consistency` | `tests/test_phase7_runbook_consistency.py` | 50 | **PASS** | 26.96s | 런북-체크리스트 1:1 정합성 및 bash 구문 검증 |
| `tests.test_run_tests_runner` | `tests/test_run_tests_runner.py` | 19 | **PASS** | 4.14s | **(신규/회귀보강)** 표준화 격리 테스트 러너 자체 검증 (19개 테스트) |
| **합계 (Total)** | **10개 모듈** | **154** | **PASS** | **55.40s** | **전체 154개 테스트 결함 없이 100% 통과 (0 Crashes)** |

---

## 4. 테스트 러너 자체 검증 (`tests/test_run_tests_runner.py` - 19/19 PASS)

보강된 `tests/test_run_tests_runner.py`를 통해 러너의 모든 핵심 동작과 예외 상황, 프로세스 격리, 크래시 판정 및 필터링 동작을 엄격히 검증했습니다 (19/19 PASS):

1. `test_parse_junit_xml_multi_status`: passed, failed, error, skipped가 혼합된 XML DOM 파싱 시 정확한 통계 집계 및 실패 사유 추출 검증 (PASS).
2. `test_parse_junit_xml_nested_subdirectories`: 하위 디렉터리 내 서로 다른 테스트 파일들이 단일 디렉터리로 뭉개지지 않고 고유 모듈 및 파일 경로로 분리 집계되는지 검증 (PASS).
3. `test_parse_junit_xml_all_passed`: 단일 `<testsuite>` 루트 및 전원 통과 케이스 파싱 검증 (PASS).
4. `test_parse_junit_xml_input_formats`: 파일 경로(str, Path) 및 바이트(bytes) 입력 지원 검증 (PASS).
5. `test_parse_junit_xml_invalid_sources`: 비정상 XML 문법 및 미지원 타입 전달 시 예외 발생 검증 (PASS).
6. `test_pytest_exit_code_table_and_descriptions`: pytest 0~5 종료 코드 매핑 테이블 및 설명 검증 (PASS).
7. `test_exit_code_interpretation_and_json_handling`: pytest 종료 코드 0~5 전수에 대한 러너 판정(0은 성공, 1~5는 실패) 및 JSON 리포트 일치 전수 검증 (PASS).
8. `test_run_all_tests_verbose_mode`: `--verbose` 옵션 활성화 시 캡처된 pytest 상세 출력이 콘솔에 노출되는지 검증 (PASS).
9. `test_run_all_tests_integration_success`: 소규모 테스트 대상 러너 실행 시 종료 코드 0 반환 및 JSON/XML 생성 통합 검증 (PASS).
10. `test_run_all_tests_failure_on_nonexistent_target`: 존재하지 않는 타겟 실행 시 종료 코드 1 반환 및 all_passed=False 판정 검증 (PASS).
11. `test_source_code_no_hardcoded_82_and_no_regex_console_parsing`: 소스 코드 내 하드코딩된 기대값 및 정규식 콘솔 스크래핑 부재 정적 검증 (PASS).
12. `test_regression_discover_test_files` (회귀 1): 하드코딩 없이 테스트 디렉터리 내 10개 이상 테스트 파일 자동 발견 및 `__pycache__` 필터링 검증 (PASS).
13. `test_regression_subprocess_isolation_file_by_file` (회귀 2): 파일마다 독립된 서브프로세스 호출 및 개별 JUnit XML 생성 파라미터 격리 검증 (PASS).
14. `test_regression_partial_subprocess_crash_failure` (회귀 3): 일부 subprocess가 `0xC0000005 (STATUS_ACCESS_VIOLATION)`로 비정상 종료 시 전체 실패(Exit Code 1) 판정 및 크래시 원인 정확한 디코딩/기록 검증 (PASS).
15. `test_regression_merge_junit_xmls_totals_and_failures` (회귀 4): 복수 JUnit XML 결과와 크래시 에러 케이스의 총계(tests, failures, errors, skipped) 및 세부 엘리먼트 병합 무결성 검증 (PASS).
16. `test_regression_assertion_failure_does_not_count_as_crash` (회귀 5): 일반 assertion 실패(exit 1) 주입 시 crash로 오분류되지 않고 JSON(tests=1, failures=1, errors=0, crashes=0)과 JUnit XML(tests=1, failures=1, errors=0) 집계가 1:1 완벽 일치함을 검증 (PASS).
17. `test_regression_no_discovery_generates_error_junit_xml` (회귀 6): 테스트 미발견 시 이전 잔재 XML을 덮어쓰고 오류를 나타내는 표준 JUnit XML(`tests="1" errors="1"`)이 정상 생성됨을 검증 (PASS).
18. **`test_regression_crash_with_valid_xml_and_corrupt_xml_single_counting` (회귀 7 - 신규)**: 정상 XML 후 크래시 시 JSON과 XML 모두 process_crash가 반영되어 1:1 동일 집계(tests=2, errors=1)되고, 손상된 XML 파싱 실패 시에도 중복 없이 단 1회만 에러로 집계(tests=1, errors=1)됨을 검증 (PASS).
19. **`test_regression_keyword_and_marker_filter_exit_5_handling` (회귀 8 - 신규)**: 필터(-k/-m) 적용 시 개별 파일의 exit 5(매칭 없음)를 정상 필터 제외로 처리하여 `-x` 시 오탐 중단을 방지하고, 전체 0건일 때만 정상적으로 미발견 실패(exit 1)로 판정됨을 검증 (PASS).

---

## 5. 생성된 산출물 및 보존 검증

1. **테스트 러너 스크립트**:
   - `scripts/run_tests.py`: pytest 자동 발견, 파일별 서브프로세스 격리 실행, JUnit XML 병합 및 크래시 감지 표준 러너
2. **러너 자체 검증 테스트**:
   - `tests/test_run_tests_runner.py`: 19개 단위/통합/회귀 테스트 스위트
3. **구조화된 리포트 아티팩트**:
   - `reports/phase8_step1_test_summary.json`: 154개 테스트 실행 상세 결과 JSON (모듈별 실행시간, subprocess_runs 전수 보존)
   - `reports/phase8_step1_junit.xml`: 병합된 종합 JUnit XML 결과 파일 (154개 testcase 일치)
4. **보호 자산 및 무결성 불변 확인**:
   - `collector.py`: SHA-256 일치 (`341BAC12BB...`)
   - `gangnam_food_stores.sqlite3`: SHA-256 일치 (`FEE3B58651...`)
   - `run_gangnam.bat`: SHA-256 일치 (`0582C3A1AE...`)
   - 운영 DB 3종 무결성 및 레코드(브랜드 5,063개, 점포 링크 735,208개) 100% 불변
