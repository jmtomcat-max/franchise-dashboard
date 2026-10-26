#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Franchise Dashboard - 표준화된 격리 실행 테스트 스위트 러너 (Subprocess-Isolated Test Runner)
프로젝트: D:/Franchise_Dashboard
위치: scripts/run_tests.py

핵심 설계 및 개선 사항 (Phase 8 Step 8-1):
  1. 자동 테스트 파일 발견 (Auto Discovery):
     - 테스트 파일 목록 및 기대 건수 하드코딩 완전 배제
     - 디렉터리 내 test_*.py, *_test.py 파일을 자동 발견하여 실행 대상 산출
  2. 파일별 Subprocess 프로세스 완전 격리 (Subprocess Isolation):
     - 테스트 간 메모리 누수, C 확장/SQLite3 연결 잔재, 이벤트루프 간섭 원천 차단
     - Windows 0xC0000005 (Access Violation) 등 장시간 단일 프로세스 누적으로 인한 비정상 종료 방지
  3. 구조화된 JUnit XML 파싱 및 통합 병합:
     - 콘솔 텍스트 정규식 파싱(regex scraping) 배제
     - 각 격리 프로세스의 JUnit XML을 파싱하여 통합 JSON 리포트 생성
     - 복수 JUnit XML을 단일 표준 루트 <testsuites> XML 파일로 안전하게 병합
  4. 엄격한 비정상 종료(Crash) 및 종료 코드 판정:
     - subprocess 하나라도 exit code != 0 또는 XML 누락 시 전체 실패(exit code 1) 판정
     - 일반 assertion 실패(exit 1)와 실제 OS 비정상 종료(Crash)를 정밀 구분하여 리포트 정합성 유지
     - 정상 XML 후 프로세스 크래시 시 JSON과 JUnit XML 모두에 크래시 오류를 1:1로 동일하게 반영
     - 손상된 XML 파싱 실패 시 중복 집계 없이 단일 에러로 정확하게 집계
     - 필터(-k/-m) 적용 시 개별 파일의 exit 5(매칭 없음)를 정상 필터 제외로 처리하고 전체 0건일 때만 실패 판정
"""

import sys
import os
import time
import json
import argparse
import tempfile
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Any, List, Optional, Union

# Windows 콘솔 UTF-8 출력 보장
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent.parent

# Python 실행 경로 결정: .venv 우선
venv_python = BASE_DIR / ".venv" / "Scripts" / "python.exe"
if venv_python.exists():
    PYTHON_EXE = str(venv_python)
else:
    PYTHON_EXE = sys.executable

PYTEST_EXIT_CODES = {
    0: "전체 테스트 성공 (All tests collected and passed successfully)",
    1: "테스트 실패 (Tests were collected and run but some of the tests failed)",
    2: "실행 중단 (Test execution was interrupted by the user or system)",
    3: "내부 실행 오류 (Internal error happened while executing tests)",
    4: "명령줄 사용 오류 (pytest command line usage error)",
    5: "수집된 테스트 없음 (No tests were collected)"
}

WINDOWS_NTSTATUS_CODES = {
    0xC0000005: "STATUS_ACCESS_VIOLATION (0xC0000005) - 메모리 접근 위반",
    0xC00000FD: "STATUS_STACK_OVERFLOW (0xC00000FD) - 스택 오버플로우",
    0xC0000409: "STATUS_STACK_BUFFER_OVERRUN (0xC0000409) - 스택 버퍼 오버런",
    0xC000013A: "STATUS_CONTROL_C_EXIT (0xC000013A) - 사용자 중단",
    0xC0000025: "STATUS_NONCONTINUABLE_EXCEPTION (0xC0000025) - 처리 불가 예외",
}


def decode_exit_code(code: int) -> str:
    """
    pytest 종료 코드 또는 OS 레벨 비정상 종료(NTSTATUS, Signal) 코드를 사람이 읽을 수 있는 설명으로 디코딩합니다.
    """
    if code in PYTEST_EXIT_CODES:
        return f"pytest exit {code}: {PYTEST_EXIT_CODES[code]}"

    unsigned_code = (code & 0xFFFFFFFF) if code < 0 else code
    if unsigned_code in WINDOWS_NTSTATUS_CODES:
        return f"OS 비정상 종료 (Crash): {WINDOWS_NTSTATUS_CODES[unsigned_code]}"
    if unsigned_code >= 0x80000000:
        return f"OS 비정상 종료 코드: 0x{unsigned_code:08X}"
    if code < 0:
        return f"프로세스 시그널 중단: Signal {-code}"
    return f"알 수 없는 종료 코드 ({code})"


def discover_test_files(target: Union[str, Path]) -> List[Path]:
    """
    테스트 대상 경로에서 실행할 테스트 파일들을 자동으로 탐색하여 정렬된 리스트로 반환합니다.
    하드코딩을 전혀 사용하지 않고 pytest 기본 규칙(test_*.py, *_test.py)을 따릅니다.
    """
    target_path = Path(target)
    if not target_path.is_absolute():
        target_path = (BASE_DIR / target_path).resolve()

    if not target_path.exists():
        return []

    if target_path.is_file():
        return [target_path]

    discovered: List[Path] = []
    for item in target_path.rglob("*.py"):
        if any(part.startswith(".") or part == "__pycache__" for part in item.parts):
            continue
        if item.name.startswith("test_") or item.name.endswith("_test.py"):
            discovered.append(item.resolve())

    return sorted(discovered, key=lambda p: str(p).replace("\\", "/"))


def parse_junit_xml(xml_source: Union[str, Path, bytes]) -> Dict[str, Any]:
    """
    JUnit XML 소스(파일 경로, XML 문자열 또는 바이트)를 파싱하여 구조화된 딕셔너리를 반환합니다.
    정규식 콘솔 스크래핑을 배제하고 표준 XML DOM 엘리먼트 트리를 전수 검사합니다.
    하위 디렉터리 모듈(예: tests.unit.test_alpha, tests.unit.test_beta)을 각각 고유 모듈로 올바르게 분리 집계합니다.
    """
    if isinstance(xml_source, Path) or (isinstance(xml_source, str) and os.path.exists(str(xml_source))):
        tree = ET.parse(str(xml_source))
        root = tree.getroot()
    elif isinstance(xml_source, str):
        root = ET.fromstring(xml_source)
    elif isinstance(xml_source, bytes):
        root = ET.fromstring(xml_source.decode("utf-8", errors="replace"))
    else:
        raise ValueError(f"유효하지 않은 XML 소스 형식: {type(xml_source)}")

    testsuites = root.findall(".//testsuite")
    if not testsuites and root.tag == "testsuite":
        testsuites = [root]

    testcases: List[Dict[str, Any]] = []
    modules: Dict[str, Dict[str, Any]] = {}

    for suite in testsuites:
        for tc in suite.findall("testcase"):
            classname = tc.get("classname", "")
            name = tc.get("name", "")
            try:
                time_val = float(tc.get("time", "0.0") or 0.0)
            except (ValueError, TypeError):
                time_val = 0.0

            file_attr = (tc.get("file") or "").strip()
            if file_attr:
                file_rel = file_attr.replace("\\", "/")
                if file_rel.endswith(".py"):
                    module_name = file_rel[:-3].replace("/", ".")
                else:
                    module_name = file_rel.replace("/", ".")
            else:
                parts = classname.split(".")
                if len(parts) >= 2 and (parts[-1][:1].isupper() or parts[-1].startswith("Test")):
                    module_parts = parts[:-1]
                else:
                    module_parts = parts

                module_name = ".".join(module_parts) if module_parts else "unknown"
                file_rel = module_name.replace(".", "/") + ".py"

            failure_el = tc.find("failure")
            error_el = tc.find("error")
            skipped_el = tc.find("skipped")

            status = "passed"
            message = ""
            details = ""

            if failure_el is not None:
                status = "failed"
                message = failure_el.get("message", "")
                details = failure_el.text or ""
            elif error_el is not None:
                status = "error"
                message = error_el.get("message", "")
                details = error_el.text or ""
            elif skipped_el is not None:
                status = "skipped"
                message = skipped_el.get("message", "")
                details = skipped_el.text or ""

            tc_data = {
                "classname": classname,
                "name": name,
                "module": module_name,
                "file": file_rel,
                "time": round(time_val, 4),
                "status": status,
                "message": message.strip() if message else "",
                "details": details.strip() if details else ""
            }
            testcases.append(tc_data)

            if module_name not in modules:
                modules[module_name] = {
                    "module": module_name,
                    "file": file_rel,
                    "total": 0,
                    "passed": 0,
                    "failures": 0,
                    "errors": 0,
                    "skipped": 0,
                    "time": 0.0,
                    "testcases": []
                }

            mod = modules[module_name]
            mod["total"] += 1
            mod["time"] += time_val
            if status == "passed":
                mod["passed"] += 1
            elif status == "failed":
                mod["failures"] += 1
            elif status == "error":
                mod["errors"] += 1
            elif status == "skipped":
                mod["skipped"] += 1
            mod["testcases"].append(tc_data)

    total_tests = len(testcases)
    total_passed = sum(1 for tc in testcases if tc["status"] == "passed")
    total_failures = sum(1 for tc in testcases if tc["status"] == "failed")
    total_errors = sum(1 for tc in testcases if tc["status"] == "error")
    total_skipped = sum(1 for tc in testcases if tc["status"] == "skipped")
    total_time = sum(tc["time"] for tc in testcases)

    for mod in modules.values():
        mod["time"] = round(mod["time"], 4)

    return {
        "total_tests": total_tests,
        "passed": total_passed,
        "failures": total_failures,
        "errors": total_errors,
        "skipped": total_skipped,
        "time": round(total_time, 4),
        "modules": list(modules.values()),
        "testcases": testcases
    }


def merge_junit_xmls(
    xml_sources: List[Union[str, Path]],
    output_path: Optional[Union[str, Path]] = None,
    unrepresented_crashes: Optional[List[Dict[str, Any]]] = None,
    crash_items: Optional[List[Dict[str, Any]]] = None,
    total_elapsed: float = 0.0
) -> ET.ElementTree:
    """
    여러 격리 실행의 JUnit XML 파일들을 하나의 종합 <testsuites> XML DOM 구조로 병합합니다.
    unrepresented_crashes(XML 파일 자체가 없거나 손상되어 XML 목록에 포함되지 못한 항목)에 대해서만 에러 suite를 합성합니다.
    (crash_items는 하위 호환성을 위해 지원합니다)
    """
    if unrepresented_crashes is None and crash_items is not None:
        unrepresented_crashes = crash_items
    root = ET.Element("testsuites", {
        "name": "Franchise Dashboard Standardized Test Suite",
        "time": f"{round(total_elapsed, 4)}"
    })

    total_tests = 0
    total_failures = 0
    total_errors = 0
    total_skipped = 0

    for src in xml_sources:
        src_path = Path(src)
        if not src_path.exists():
            continue
        try:
            tree = ET.parse(str(src_path))
            src_root = tree.getroot()
            suites = src_root.findall(".//testsuite")
            if not suites and src_root.tag == "testsuite":
                suites = [src_root]

            for suite in suites:
                suite_tests = int(suite.get("tests", "0") or 0)
                suite_failures = int(suite.get("failures", "0") or 0)
                suite_errors = int(suite.get("errors", "0") or 0)
                suite_skipped = int(suite.get("skipped", "0") or 0)

                total_tests += suite_tests
                total_failures += suite_failures
                total_errors += suite_errors
                total_skipped += suite_skipped

                root.append(suite)
        except Exception as e:
            # 파싱 실패한 XML은 에러 스위트로 변환 (단일 집계)
            err_suite = ET.SubElement(root, "testsuite", {
                "name": src_path.stem,
                "tests": "1",
                "failures": "0",
                "errors": "1",
                "skipped": "0",
                "time": "0.0"
            })
            err_tc = ET.SubElement(err_suite, "testcase", {
                "classname": src_path.stem,
                "name": "xml_parsing",
                "time": "0.0"
            })
            err_el = ET.SubElement(err_tc, "error", {"message": f"JUnit XML parse failed: {e}"})
            err_el.text = str(e)
            total_tests += 1
            total_errors += 1

    # XML에 아직 반영되지 못한 실제 비정상 종료(XML 미생성 또는 파싱 실패) 항목만 추가
    if unrepresented_crashes:
        for c in unrepresented_crashes:
            mod_name = c.get("module", "unknown")
            crash_suite = ET.SubElement(root, "testsuite", {
                "name": mod_name,
                "tests": "1",
                "failures": "0",
                "errors": "1",
                "skipped": "0",
                "time": f"{round(c.get('time', 0.0), 4)}"
            })
            crash_tc = ET.SubElement(crash_suite, "testcase", {
                "classname": mod_name,
                "name": "process_execution",
                "time": f"{round(c.get('time', 0.0), 4)}"
            })
            crash_el = ET.SubElement(crash_tc, "error", {
                "message": c.get("message", "Subprocess execution crash")
            })
            crash_el.text = c.get("details", "")
            total_tests += 1
            total_errors += 1

    root.set("tests", str(total_tests))
    root.set("failures", str(total_failures))
    root.set("errors", str(total_errors))
    root.set("skipped", str(total_skipped))

    merged_tree = ET.ElementTree(root)
    if output_path:
        out_p = Path(output_path).resolve()
        out_p.parent.mkdir(parents=True, exist_ok=True)
        merged_tree.write(str(out_p), encoding="utf-8", xml_declaration=True)

    return merged_tree


def run_all_tests(
    test_target: str = "tests",
    json_output_path: Optional[str] = None,
    junit_output_path: Optional[str] = None,
    keyword: Optional[str] = None,
    marker: Optional[str] = None,
    fail_fast: bool = False,
    verbose: bool = False
) -> int:
    """
    pytest 테스트를 파일 단위 Subprocess로 완전히 격리하여 실행합니다.
    1. test_target 내 테스트 파일 목록을 자동 발견
    2. 각 파일을 별도의 pytest 서브프로세스로 실행하여 메모리 오염 및 프로세스 간 간섭 배제
    3. 각 실행의 JUnit XML을 수집 및 파싱하여 단일 JSON 및 종합 JUnit XML로 병합
    4. 하나라도 비정상 종료(0xC0000005 등), exit code != 0, XML 누락 발생 시 즉시 실패 판정
    """
    print("=" * 80)
    print("  Franchise Dashboard - 표준화된 격리 실행 테스트 러너 (Subprocess Isolation)")
    print(f"  사용 Python    : {PYTHON_EXE}")
    print(f"  테스트 대상 경로: {test_target}")
    if keyword:
        print(f"  키워드 필터 (-k): {keyword}")
    if marker:
        print(f"  마커 필터 (-m)  : {marker}")
    if fail_fast:
        print("  Fast Fail (-x) : 활성화 (첫 실패 시 즉시 중단)")
    if verbose:
        print("  상세 모드 (-v) : 활성화")
    print("=" * 80)

    start_total = time.perf_counter()

    # 1. 테스트 파일 자동 발견
    test_files = discover_test_files(test_target)
    if not test_files:
        print(f"\n[오류] '{test_target}' 경로에서 발견된 테스트 파일이 없습니다.")
        total_elapsed = time.perf_counter() - start_total
        if json_output_path:
            out_file = Path(json_output_path).resolve()
            out_file.parent.mkdir(parents=True, exist_ok=True)
            report_data = {
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                "python_executable": PYTHON_EXE,
                "test_target": test_target,
                "pytest_exit_code": 5,
                "pytest_exit_description": PYTEST_EXIT_CODES[5],
                "all_passed": False,
                "summary": {
                    "total_modules": 0,
                    "total_tests": 1,
                    "passed": 0,
                    "failures": 0,
                    "errors": 1,
                    "skipped": 0,
                    "crashes": 0,
                    "execution_time_seconds": 0.0,
                    "total_elapsed_seconds": round(total_elapsed, 4)
                },
                "subprocess_runs": [],
                "crashes": [],
                "modules": [],
                "failures_details": [{"message": f"No test files found in target: {test_target}"}]
            }
            with open(out_file, "w", encoding="utf-8") as f:
                json.dump(report_data, f, ensure_ascii=False, indent=2)

        # 테스트 미발견 시에도 오류를 나타내는 표준 JUnit XML 생성 (이전 잔재 덮어쓰기)
        if junit_output_path:
            out_xml = Path(junit_output_path).resolve()
            out_xml.parent.mkdir(parents=True, exist_ok=True)
            root = ET.Element("testsuites", {
                "name": "Franchise Dashboard Standardized Test Suite",
                "time": "0.0",
                "tests": "1",
                "failures": "0",
                "errors": "1",
                "skipped": "0"
            })
            suite = ET.SubElement(root, "testsuite", {
                "name": "discovery",
                "tests": "1",
                "failures": "0",
                "errors": "1",
                "skipped": "0",
                "time": "0.0"
            })
            tc = ET.SubElement(suite, "testcase", {
                "classname": "discovery",
                "name": "test_discovery",
                "time": "0.0"
            })
            err = ET.SubElement(tc, "error", {"message": f"No test files found in target: {test_target}"})
            err.text = f"No test files discovered in path '{test_target}'"
            tree = ET.ElementTree(root)
            tree.write(str(out_xml), encoding="utf-8", xml_declaration=True)

        return 1

    print(f"\n[*] 자동 발견된 테스트 파일: 총 {len(test_files)}개 파일")
    for idx, f in enumerate(test_files, 1):
        rel_f = f.relative_to(BASE_DIR) if f.is_relative_to(BASE_DIR) else f
        print(f"    [{idx:02d}/{len(test_files):02d}] {rel_f}")

    all_modules: List[Dict[str, Any]] = []
    all_testcases: List[Dict[str, Any]] = []
    generated_xml_paths: List[Path] = []
    crash_items: List[Dict[str, Any]] = []
    unrepresented_crashes: List[Dict[str, Any]] = []
    subprocess_runs: List[Dict[str, Any]] = []

    total_exec_time = 0.0
    any_subprocess_failed = False
    first_non_zero_exit_code = 0
    has_active_filter = bool(keyword or marker)

    with tempfile.TemporaryDirectory(prefix="franchise_isolated_test_") as temp_dir:
        temp_dir_path = Path(temp_dir)

        print("\n" + "-" * 80)
        print("  격리된 Subprocess 단위 테스트 실행 시작 (Process Isolation)")
        print("-" * 80)

        for idx, test_file in enumerate(test_files, 1):
            rel_path = test_file.relative_to(BASE_DIR) if test_file.is_relative_to(BASE_DIR) else test_file
            mod_display_name = str(rel_path).replace("\\", "/").replace(".py", "").replace("/", ".")
            file_xml = temp_dir_path / f"junit_sub_{idx:03d}.xml"

            cmd = [
                PYTHON_EXE,
                "-m",
                "pytest",
                str(test_file),
                f"--junitxml={str(file_xml)}",
                "-o",
                "junit_family=xunit2"
            ]

            if not verbose:
                cmd.append("-q")
            else:
                cmd.append("-v")

            if keyword:
                cmd.extend(["-k", keyword])
            if marker:
                cmd.extend(["-m", marker])
            if fail_fast:
                cmd.append("-x")

            file_start = time.perf_counter()
            proc = subprocess.run(
                cmd,
                cwd=BASE_DIR,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace"
            )
            file_elapsed = time.perf_counter() - file_start
            total_exec_time += file_elapsed
            exit_code = proc.returncode

            # 비정상 종료(Access Violation 등) 여부 디코딩
            exit_desc = decode_exit_code(exit_code)
            is_os_crash = (exit_code < 0) or ((exit_code & 0xFFFFFFFF) >= 0x80000000)
            is_pytest_fatal = exit_code in (2, 3, 4)

            # 필터(-k, -m) 적용 시 특정 파일에서 매칭 테스트가 없는 것(exit 5)은 정상적인 필터 제외로 취급
            is_filtered_empty = (exit_code == 5 and has_active_filter)

            if verbose and proc.stdout:
                print(f"\n--- [Subprocess {idx}: {rel_path} 상세 출력] ---")
                print(proc.stdout.strip())
                print("-" * 60)

            if is_filtered_empty:
                # 필터 제외 파일: 크래시나 실패로 판정하지 않고 건너뜀
                print(f"  [FILTERED] {mod_display_name:<38} | 필터 매칭 테스트 없음 (건너뜀) | {file_elapsed:>6.2f}s")
                subprocess_runs.append({
                    "index": idx,
                    "file": str(rel_path).replace("\\", "/"),
                    "module": mod_display_name,
                    "exit_code": 5,
                    "exit_description": "필터 매칭 테스트 없음 (Filtered out)",
                    "elapsed_seconds": round(file_elapsed, 4),
                    "is_crash": False
                })
                continue

            # XML 파싱 시도 (오직 파싱에 성공한 유효 XML만 처리)
            file_parse_error = None
            parsed_file_result: Optional[Dict[str, Any]] = None

            if file_xml.exists():
                try:
                    parsed_file_result = parse_junit_xml(file_xml)
                except Exception as e:
                    file_parse_error = f"XML 파싱 에러: {e}"
            else:
                file_parse_error = f"JUnit XML 파일 미생성 (exit_code={exit_code})"

            # 실제 비정상 종료(Crash) 여부 판정
            is_actual_crash = is_os_crash or is_pytest_fatal or (file_parse_error is not None)

            run_record = {
                "index": idx,
                "file": str(rel_path).replace("\\", "/"),
                "module": mod_display_name,
                "exit_code": exit_code,
                "exit_description": exit_desc,
                "elapsed_seconds": round(file_elapsed, 4),
                "is_crash": is_actual_crash
            }
            subprocess_runs.append(run_record)

            # 실패 및 크래시 처리
            if exit_code != 0 or file_parse_error is not None:
                any_subprocess_failed = True
                if first_non_zero_exit_code == 0:
                    first_non_zero_exit_code = exit_code if exit_code != 0 else 1

                if is_actual_crash:
                    crash_entry = {
                        "file": str(rel_path).replace("\\", "/"),
                        "module": mod_display_name,
                        "exit_code": exit_code,
                        "exit_description": exit_desc,
                        "time": round(file_elapsed, 4),
                        "message": f"Subprocess 비정상 종료: {exit_desc}" if (is_os_crash or is_pytest_fatal) else (file_parse_error or exit_desc),
                        "details": (proc.stderr or proc.stdout or "").strip()
                    }
                    crash_items.append(crash_entry)
                    print(f"  [CRASH] {mod_display_name:<40} | {exit_desc} | {file_elapsed:>6.2f}s")
                    if proc.stderr:
                        err_snippet = proc.stderr.strip().splitlines()[-1]
                        print(f"          stderr: {err_snippet}")

                    if parsed_file_result is not None:
                        # 케이스 1: 정상 XML이 생성되었으나 프로세스가 크래시한 경우
                        # 원래 테스트 결과들을 유지하면서 크래시 에러 테스트케이스 1개를 JSON과 file_xml 모두에 일치하여 반영
                        synthetic_crash_tc = {
                            "classname": mod_display_name,
                            "name": "process_crash",
                            "module": mod_display_name,
                            "file": str(rel_path).replace("\\", "/"),
                            "time": round(file_elapsed, 4),
                            "status": "error",
                            "message": f"Subprocess 크래시: {exit_desc}",
                            "details": (proc.stderr or proc.stdout or "").strip()
                        }
                        parsed_file_result["testcases"].append(synthetic_crash_tc)
                        parsed_file_result["total_tests"] += 1
                        parsed_file_result["errors"] += 1

                        # 모듈 집계 및 testcases도 함께 갱신
                        mod = next((m for m in parsed_file_result["modules"] if m["module"] == mod_display_name), None)
                        if mod is not None:
                            mod["total"] += 1
                            mod["errors"] += 1
                            mod["testcases"].append(synthetic_crash_tc)
                        else:
                            parsed_file_result["modules"].append({
                                "module": mod_display_name,
                                "file": str(rel_path).replace("\\", "/"),
                                "total": 1,
                                "passed": 0,
                                "failures": 0,
                                "errors": 1,
                                "skipped": 0,
                                "time": round(file_elapsed, 4),
                                "testcases": [synthetic_crash_tc]
                            })

                        # XML 파일에도 process_crash testcase를 추가하고 저장하여 단일 소스 일치 보장
                        try:
                            tree = ET.parse(str(file_xml))
                            root_el = tree.getroot()
                            found_suite = root_el.find(".//testsuite")
                            if found_suite is not None:
                                target_suite = found_suite
                            elif root_el.tag == "testsuite":
                                target_suite = root_el
                            else:
                                target_suite = ET.SubElement(root_el, "testsuite", {
                                    "name": mod_display_name,
                                    "tests": "0",
                                    "failures": "0",
                                    "errors": "0",
                                    "skipped": "0",
                                    "time": "0.0"
                                })

                            tc_el = ET.SubElement(target_suite, "testcase", {
                                "classname": mod_display_name,
                                "name": "process_crash",
                                "time": f"{round(file_elapsed, 4)}"
                            })
                            err_el = ET.SubElement(tc_el, "error", {"message": f"Subprocess 크래시: {exit_desc}"})
                            err_el.text = (proc.stderr or proc.stdout or "").strip()

                            s_tests = int(target_suite.get("tests", "0") or 0) + 1
                            s_errors = int(target_suite.get("errors", "0") or 0) + 1
                            target_suite.set("tests", str(s_tests))
                            target_suite.set("errors", str(s_errors))
                            tree.write(str(file_xml), encoding="utf-8", xml_declaration=True)
                        except Exception:
                            pass

                        generated_xml_paths.append(file_xml)
                        all_testcases.extend(parsed_file_result["testcases"])
                        all_modules.extend(parsed_file_result["modules"])
                    else:
                        # 케이스 2: XML이 없거나 파싱 실패한 경우 (손상된 XML)
                        # generated_xml_paths에 넣지 않고 unrepresented_crashes를 통해 단 한 번만 합성
                        synthetic_tc = {
                            "classname": mod_display_name,
                            "name": "subprocess_execution",
                            "module": mod_display_name,
                            "file": str(rel_path).replace("\\", "/"),
                            "time": round(file_elapsed, 4),
                            "status": "error",
                            "message": exit_desc if exit_code != 0 else (file_parse_error or "Unknown error"),
                            "details": (proc.stderr or proc.stdout or "").strip()
                        }
                        all_testcases.append(synthetic_tc)
                        all_modules.append({
                            "module": mod_display_name,
                            "file": str(rel_path).replace("\\", "/"),
                            "total": 1,
                            "passed": 0,
                            "failures": 0,
                            "errors": 1,
                            "skipped": 0,
                            "time": round(file_elapsed, 4),
                            "testcases": [synthetic_tc]
                        })
                        unrepresented_crashes.append(crash_entry)
                else:
                    # 케이스 3: 일반 assertion 또는 테스트 실패 (exit 1, XML 정상)
                    m_total = parsed_file_result["total_tests"] if parsed_file_result else 0
                    m_passed = parsed_file_result["passed"] if parsed_file_result else 0
                    m_failed = parsed_file_result["failures"] if parsed_file_result else 0
                    m_errors = parsed_file_result["errors"] if parsed_file_result else 0
                    print(f"  [FAIL]  {mod_display_name:<40} | {m_passed}/{m_total} 통과, {m_failed} 실패, {m_errors} 오류 | {file_elapsed:>6.2f}s")
                    generated_xml_paths.append(file_xml)
                    all_testcases.extend(parsed_file_result["testcases"])
                    all_modules.extend(parsed_file_result["modules"])
            else:
                # 정상 통과
                m_total = parsed_file_result["total_tests"] if parsed_file_result else 0
                m_passed = parsed_file_result["passed"] if parsed_file_result else 0
                m_skipped = parsed_file_result["skipped"] if parsed_file_result else 0
                badge = "[PASS]"
                detail_str = f"{m_passed}/{m_total} 통과"
                if m_skipped > 0:
                    detail_str += f" ({m_skipped} 건너뜀)"
                print(f"  {badge}  {mod_display_name:<40} | {detail_str:<22} | {file_elapsed:>6.2f}s")
                generated_xml_paths.append(file_xml)
                all_testcases.extend(parsed_file_result["testcases"])
                all_modules.extend(parsed_file_result["modules"])

            if fail_fast and (exit_code != 0 or file_parse_error is not None) and not is_filtered_empty:
                print(f"\n[중단] -x (Fail Fast) 옵션으로 인해 실패 발견 즉시 실행을 중단합니다.")
                break

        total_elapsed = time.perf_counter() - start_total

        total_tests = len(all_testcases)
        total_passed = sum(1 for tc in all_testcases if tc["status"] == "passed")
        total_failures = sum(1 for tc in all_testcases if tc["status"] == "failed")
        total_errors = sum(1 for tc in all_testcases if tc["status"] == "error")
        total_skipped = sum(1 for tc in all_testcases if tc["status"] == "skipped")

        failed_cases = [tc for tc in all_testcases if tc["status"] in ("failed", "error")]

        # 엄격 합격 판정:
        all_passed = (
            not any_subprocess_failed
            and total_failures == 0
            and total_errors == 0
            and len(crash_items) == 0
            and total_tests > 0
        )

        # 종합 JUnit XML 병합 저장
        if junit_output_path:
            merge_junit_xmls(
                xml_sources=generated_xml_paths,
                output_path=junit_output_path,
                unrepresented_crashes=unrepresented_crashes,
                total_elapsed=total_exec_time
            )

        print("\n" + "=" * 80)
        print("  종합 테스트 실행 결과 요약 (Consolidated Summary)")
        print("=" * 80)

        if failed_cases:
            print(f"\n[실패/오류 세부 내역] 총 {len(failed_cases)}개 항목:")
            for idx, fc in enumerate(failed_cases, 1):
                print(f"  [{idx}] {fc['classname']}.{fc['name']} ({fc['status'].upper()})")
                if fc.get("message"):
                    print(f"      원인: {fc['message']}")
                if fc.get("details"):
                    first_trace = fc["details"].strip().splitlines()[-1]
                    print(f"      상세: {first_trace}")

        if crash_items:
            print(f"\n[비정상 프로세스 종료 (Crashes)] 총 {len(crash_items)}개:")
            for c in crash_items:
                print(f"  - 모듈: {c['module']} (종료코드 {c['exit_code']}: {c['exit_description']})")

        print("\n" + "-" * 80)
        if all_passed:
            print(f"  [성공] 자동 발견된 {len(test_files)}개 모듈, 총 {total_tests}개 테스트가 모두 통과했습니다!")
            print(f"         (통과: {total_passed}/{total_tests}, 건너뜀: {total_skipped}, 실행시간: {total_exec_time:.2f}s, 총시간: {total_elapsed:.2f}s)")
            overall_status_code = 0
        else:
            reasons = []
            if any_subprocess_failed:
                reasons.append("일부 서브프로세스 실패/오류")
            if total_failures > 0:
                reasons.append(f"{total_failures}개 테스트 실패")
            if total_errors > 0:
                reasons.append(f"{total_errors}개 오류")
            if len(crash_items) > 0:
                reasons.append(f"{len(crash_items)}개 비정상 종료")
            if total_tests == 0:
                reasons.append("수집된 테스트 없음 (0 tests collected)")

            print(f"  [실패] 테스트 실행 중 결함이 발견되었습니다! ({', '.join(reasons)})")
            print(f"         (수집: {total_tests}, 통과: {total_passed}, 실패: {total_failures}, 오류: {total_errors}, 건너뜀: {total_skipped})")
            overall_status_code = 1
        print("=" * 80)

        # JSON 리포트 저장
        if json_output_path:
            out_file = Path(json_output_path).resolve()
            out_file.parent.mkdir(parents=True, exist_ok=True)
            report_data = {
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                "python_executable": PYTHON_EXE,
                "test_target": test_target,
                "isolation_mode": "subprocess_per_file",
                "pytest_exit_code": first_non_zero_exit_code if any_subprocess_failed else (5 if total_tests == 0 else 0),
                "pytest_exit_description": decode_exit_code(first_non_zero_exit_code if any_subprocess_failed else (5 if total_tests == 0 else 0)),
                "all_passed": all_passed,
                "summary": {
                    "total_modules": len(test_files),
                    "total_tests": total_tests,
                    "passed": total_passed,
                    "failures": total_failures,
                    "errors": total_errors,
                    "skipped": total_skipped,
                    "crashes": len(crash_items),
                    "execution_time_seconds": round(total_exec_time, 4),
                    "total_elapsed_seconds": round(total_elapsed, 4)
                },
                "subprocess_runs": subprocess_runs,
                "crashes": crash_items,
                "modules": all_modules,
                "failures_details": failed_cases
            }
            with open(out_file, "w", encoding="utf-8") as f:
                json.dump(report_data, f, ensure_ascii=False, indent=2)
            print(f"[*] 구조화된 테스트 결과 JSON 저장 완료: {out_file}")

        if junit_output_path:
            print(f"[*] 병합된 종합 JUnit XML 리포트 저장 완료: {junit_output_path}")

        return overall_status_code


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Franchise Dashboard Standardized Isolated Test Runner (Subprocess per file & JUnit XML)"
    )
    parser.add_argument(
        "--target",
        type=str,
        default="tests",
        help="테스트 대상 디렉터리 또는 파일 경로 (기본값: tests)"
    )
    parser.add_argument(
        "--json",
        type=str,
        default=None,
        help="구조화된 테스트 결과 JSON 저장 경로 (예: reports/test_results.json)"
    )
    parser.add_argument(
        "--junitxml",
        type=str,
        default=None,
        help="병합된 종합 JUnit XML 결과 파일 보존 경로 (예: reports/junit.xml)"
    )
    parser.add_argument(
        "-k",
        "--keyword",
        type=str,
        default=None,
        help="pytest -k 키워드 필터링 표현식"
    )
    parser.add_argument(
        "-m",
        "--marker",
        type=str,
        default=None,
        help="pytest -m 마커 필터링 표현식"
    )
    parser.add_argument(
        "-x",
        "--fail-fast",
        action="store_true",
        help="첫 번째 실패 발생 시 즉시 중단"
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="pytest 상세 출력 모드 활성화"
    )

    args = parser.parse_args()

    exit_code = run_all_tests(
        test_target=args.target,
        json_output_path=args.json,
        junit_output_path=args.junitxml,
        keyword=args.keyword,
        marker=args.marker,
        fail_fast=args.fail_fast,
        verbose=args.verbose
    )
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
