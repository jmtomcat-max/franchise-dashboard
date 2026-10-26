#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Franchise Dashboard - 표준화된 테스트 러너 자체 검증 테스트 (Test Runner Verification Test)
위치: tests/test_run_tests_runner.py

검증 내용:
  1. parse_junit_xml 함수의 XML 파싱 정확도 (passed, failed, error, skipped, 모듈별 집계)
  2. 하위 디렉터리 모듈(tests.unit.test_alpha, tests.unit.test_beta)의 고유 분리 집계 회귀 검증
  3. 파일 경로, 문자열, 바이트 입력 형식 지원
  4. 비정상 XML 및 에러 핸들링
  5. pytest 종료 코드(0~5) 전수 해석 및 정상 실패 판정/JSON 리포트 검증
  6. run_all_tests 실행 통합 테스트 (정상 성공 시 0 반환, JSON/JUnit XML 출력 보존)
  7. verbose 모드 지정 시 캡처된 상세 pytest 출력 노출 검증
  8. 비정상 대상 실행 시 실패 판정(1 반환) 및 에러 원인 기록
  9. run_tests.py 소스 코드 정적 검증: 82개 하드코딩 제거 및 콘솔 정규식 스크래핑 완전 배제 확인
  10. [회귀 검증 1] 자동 파일 발견 (discover_test_files): 하드코딩 없이 테스트 파일 탐색
  11. [회귀 검증 2] 파일별 Subprocess 격리 실행 (Subprocess Isolation): 파일별 독립 실행 및 JUnit 분리
  12. [회귀 검증 3] 일부 Subprocess 비정상 종료 시 전체 실패 (0xC0000005 Access Violation 등 처리)
  13. [회귀 검증 4] 여러 JUnit XML 결과의 총계 및 실패 상세 병합 (merge_junit_xmls)
"""

import os
import sys
import io
import json
import tempfile
import unittest
import contextlib
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import patch, Mock

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from scripts.run_tests import (
    parse_junit_xml,
    run_all_tests,
    discover_test_files,
    merge_junit_xmls,
    decode_exit_code,
    PYTEST_EXIT_CODES,
    WINDOWS_NTSTATUS_CODES
)


SAMPLE_VALID_JUNIT_XML = """<?xml version="1.0" encoding="utf-8"?>
<testsuites name="pytest tests">
  <testsuite name="pytest" errors="1" failures="1" skipped="1" tests="4" time="1.234" timestamp="2026-10-21T17:00:00+09:00">
    <testcase classname="tests.test_alpha.TestAlpha" name="test_alpha_ok" time="0.100" />
    <testcase classname="tests.test_alpha.TestAlpha" name="test_alpha_fail" time="0.200">
      <failure message="assert 1 == 2">AssertionError: assert 1 == 2</failure>
    </testcase>
    <testcase classname="tests.test_beta.TestBeta" name="test_beta_error" time="0.300">
      <error message="database connection failed">RuntimeError: database connection failed</error>
    </testcase>
    <testcase classname="tests.test_beta.TestBeta" name="test_beta_skip" time="0.050">
      <skipped message="network not available" type="pytest.skip" />
    </testcase>
  </testsuite>
</testsuites>
"""

SAMPLE_ALL_PASSED_XML = """<?xml version="1.0" encoding="utf-8"?>
<testsuite name="pytest" errors="0" failures="0" skipped="0" tests="3" time="0.450">
  <testcase classname="tests.test_gamma.TestGamma" name="test_g1" time="0.150" />
  <testcase classname="tests.test_gamma.TestGamma" name="test_g2" time="0.150" />
  <testcase classname="tests.test_gamma.TestGamma" name="test_g3" time="0.150" />
</testsuite>
"""

SAMPLE_NESTED_SUBDIRECTORIES_XML = """<?xml version="1.0" encoding="utf-8"?>
<testsuites name="pytest tests">
  <testsuite name="pytest" errors="0" failures="0" skipped="0" tests="3" time="0.300">
    <testcase classname="tests.unit.test_alpha.TestAlpha" name="test_a" time="0.100" />
    <testcase classname="tests.unit.test_beta.TestBeta" name="test_b" time="0.100" />
    <testcase classname="tests.integration.deep.test_gamma" name="test_c" time="0.100" />
  </testsuite>
</testsuites>
"""


class TestRunTestsRunner(unittest.TestCase):
    """표준화된 테스트 러너 및 JUnit XML 파서 검증 테스트 스위트"""

    def test_parse_junit_xml_multi_status(self):
        """passed, failed, error, skipped가 혼합된 JUnit XML 파싱 검증"""
        results = parse_junit_xml(SAMPLE_VALID_JUNIT_XML)

        self.assertEqual(results["total_tests"], 4)
        self.assertEqual(results["passed"], 1)
        self.assertEqual(results["failures"], 1)
        self.assertEqual(results["errors"], 1)
        self.assertEqual(results["skipped"], 1)
        self.assertAlmostEqual(results["time"], 0.650, places=3)

        # 모듈 집계 검증
        modules = {m["module"]: m for m in results["modules"]}
        self.assertIn("tests.test_alpha", modules)
        self.assertIn("tests.test_beta", modules)

        alpha = modules["tests.test_alpha"]
        self.assertEqual(alpha["total"], 2)
        self.assertEqual(alpha["passed"], 1)
        self.assertEqual(alpha["failures"], 1)
        self.assertEqual(alpha["errors"], 0)

        beta = modules["tests.test_beta"]
        self.assertEqual(beta["total"], 2)
        self.assertEqual(beta["passed"], 0)
        self.assertEqual(beta["failures"], 0)
        self.assertEqual(beta["errors"], 1)
        self.assertEqual(beta["skipped"], 1)

        # 실패 상세 메시지 검증
        failed_tc = [tc for tc in results["testcases"] if tc["status"] == "failed"][0]
        self.assertEqual(failed_tc["name"], "test_alpha_fail")
        self.assertEqual(failed_tc["message"], "assert 1 == 2")

        error_tc = [tc for tc in results["testcases"] if tc["status"] == "error"][0]
        self.assertEqual(error_tc["name"], "test_beta_error")
        self.assertEqual(error_tc["message"], "database connection failed")

    def test_parse_junit_xml_nested_subdirectories(self):
        """하위 디렉터리 내 서로 다른 테스트 파일들이 별도의 고유 모듈로 정확히 분리 집계되는지 검증"""
        results = parse_junit_xml(SAMPLE_NESTED_SUBDIRECTORIES_XML)
        self.assertEqual(results["total_tests"], 3)
        self.assertEqual(len(results["modules"]), 3)

        modules_map = {m["module"]: m for m in results["modules"]}
        self.assertIn("tests.unit.test_alpha", modules_map)
        self.assertIn("tests.unit.test_beta", modules_map)
        self.assertIn("tests.integration.deep.test_gamma", modules_map)

        # 파일 경로 매핑 검증
        self.assertEqual(modules_map["tests.unit.test_alpha"]["file"], "tests/unit/test_alpha.py")
        self.assertEqual(modules_map["tests.unit.test_beta"]["file"], "tests/unit/test_beta.py")
        self.assertEqual(modules_map["tests.integration.deep.test_gamma"]["file"], "tests/integration/deep/test_gamma.py")

        self.assertEqual(modules_map["tests.unit.test_alpha"]["total"], 1)
        self.assertEqual(modules_map["tests.unit.test_beta"]["total"], 1)
        self.assertEqual(modules_map["tests.integration.deep.test_gamma"]["total"], 1)

    def test_parse_junit_xml_all_passed(self):
        """루트가 <testsuite>이고 전원 통과인 경우의 파싱 검증"""
        results = parse_junit_xml(SAMPLE_ALL_PASSED_XML)
        self.assertEqual(results["total_tests"], 3)
        self.assertEqual(results["passed"], 3)
        self.assertEqual(results["failures"], 0)
        self.assertEqual(results["errors"], 0)
        self.assertEqual(results["skipped"], 0)
        self.assertEqual(len(results["modules"]), 1)
        self.assertEqual(results["modules"][0]["module"], "tests.test_gamma")

    def test_parse_junit_xml_input_formats(self):
        """파일 경로(Path, str) 및 바이트(bytes) 입력 지원 검증"""
        res_bytes = parse_junit_xml(SAMPLE_ALL_PASSED_XML.encode("utf-8"))
        self.assertEqual(res_bytes["total_tests"], 3)

        with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".xml", delete=False) as f:
            f.write(SAMPLE_ALL_PASSED_XML)
            f_path = f.name

        try:
            res_file_str = parse_junit_xml(f_path)
            self.assertEqual(res_file_str["total_tests"], 3)

            res_file_path = parse_junit_xml(Path(f_path))
            self.assertEqual(res_file_path["total_tests"], 3)
        finally:
            if os.path.exists(f_path):
                os.remove(f_path)

    def test_parse_junit_xml_invalid_sources(self):
        """유효하지 않은 입력 및 파싱 오류 처리 검증"""
        with self.assertRaises(Exception):
            parse_junit_xml("<invalid xml not closed")

        with self.assertRaises(ValueError):
            parse_junit_xml(12345)

    def test_pytest_exit_code_table_and_descriptions(self):
        """pytest 0~5 종료 코드 매핑 테이블 및 설명 검증"""
        for code in (0, 1, 2, 3, 4, 5):
            self.assertIn(code, PYTEST_EXIT_CODES)
            self.assertTrue(len(PYTEST_EXIT_CODES[code]) > 0)

    def test_exit_code_interpretation_and_json_handling(self):
        """pytest 종료 코드 0~5 전수에 대한 러너 판정(0은 성공, 1~5는 실패) 및 JSON 기록 검증"""
        sample_pass_xml = parse_junit_xml(SAMPLE_ALL_PASSED_XML)

        for code in range(6):
            with tempfile.TemporaryDirectory() as temp_dir:
                json_file = Path(temp_dir) / f"exit_{code}.json"

                mock_proc = Mock(returncode=code, stdout="mock pytest stdout", stderr="mock pytest stderr")
                with patch("scripts.run_tests.discover_test_files", return_value=[Path("tests/test_mock.py")]), \
                     patch("scripts.run_tests.subprocess.run", return_value=mock_proc), \
                     patch("scripts.run_tests.Path.exists", return_value=True), \
                     patch("scripts.run_tests.parse_junit_xml", return_value=sample_pass_xml):

                    ret = run_all_tests(
                        test_target="mock_tests",
                        json_output_path=str(json_file)
                    )

                    if code == 0:
                        self.assertEqual(ret, 0, "종료 코드 0은 정상 통과(0)로 판정되어야 함")
                    else:
                        self.assertEqual(ret, 1, f"종료 코드 {code}는 비정상 실패(1)로 판정되어야 함")

                    self.assertTrue(json_file.exists())
                    with open(json_file, "r", encoding="utf-8") as f:
                        data = json.load(f)

                    self.assertEqual(data["pytest_exit_code"], code)
                    self.assertIn("pytest_exit_description", data)
                    if code == 0:
                        self.assertTrue(data["all_passed"])
                    else:
                        self.assertFalse(data["all_passed"])

    def test_run_all_tests_verbose_mode(self):
        """--verbose 옵션 활성화 시 캡처된 pytest 상세 출력이 콘솔에 노출되는지 검증"""
        sample_pass_xml = parse_junit_xml(SAMPLE_ALL_PASSED_XML)
        mock_proc = Mock(returncode=0, stdout="=== DETAILED PYTEST VERBOSE OUTPUT ===", stderr="")

        with tempfile.TemporaryDirectory() as temp_dir:
            json_file = Path(temp_dir) / "verbose_out.json"

            with patch("scripts.run_tests.discover_test_files", return_value=[Path("tests/test_mock.py")]), \
                 patch("scripts.run_tests.subprocess.run", return_value=mock_proc), \
                 patch("scripts.run_tests.Path.exists", return_value=True), \
                 patch("scripts.run_tests.parse_junit_xml", return_value=sample_pass_xml):

                stdout_capture = io.StringIO()
                with contextlib.redirect_stdout(stdout_capture):
                    ret = run_all_tests(
                        test_target="mock_tests",
                        json_output_path=str(json_file),
                        verbose=True
                    )

                self.assertEqual(ret, 0)
                captured_text = stdout_capture.getvalue()
                self.assertIn("DETAILED PYTEST VERBOSE OUTPUT", captured_text, "verbose 모드에서는 상세 출력이 노출되어야 함")

    def test_run_all_tests_integration_success(self):
        """실제 소규모 테스트 대상 러너 실행 통합 테스트 (종료코드 0, JSON/XML 검증)"""
        with tempfile.TemporaryDirectory() as temp_dir:
            json_file = Path(temp_dir) / "test_out.json"
            xml_file = Path(temp_dir) / "test_out.xml"

            ret = run_all_tests(
                test_target="tests/test_phase7_backup_retention.py",
                json_output_path=str(json_file),
                junit_output_path=str(xml_file)
            )

            self.assertEqual(ret, 0, "소규모 테스트 실행은 반드시 종료 코드 0이어야 함")
            self.assertTrue(json_file.exists(), "결과 JSON 파일이 생성되어야 함")
            self.assertTrue(xml_file.exists(), "결과 XML 파일이 생성되어야 함")

            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            self.assertTrue(data["all_passed"])
            self.assertEqual(data["pytest_exit_code"], 0)
            self.assertEqual(data["summary"]["total_tests"], 3)
            self.assertEqual(data["summary"]["passed"], 3)
            self.assertEqual(data["summary"]["failures"], 0)
            self.assertEqual(data["summary"]["errors"], 0)
            self.assertEqual(len(data["modules"]), 1)

    def test_run_all_tests_failure_on_nonexistent_target(self):
        """존재하지 않는 타겟 실행 시 exit code 1 및 all_passed False 검증"""
        with tempfile.TemporaryDirectory() as temp_dir:
            json_file = Path(temp_dir) / "fail_out.json"

            ret = run_all_tests(
                test_target="nonexistent_test_path_12345",
                json_output_path=str(json_file)
            )

            self.assertEqual(ret, 1, "존재하지 않는 타겟은 종료 코드 1이어야 함")
            self.assertTrue(json_file.exists())

            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            self.assertFalse(data["all_passed"])
            self.assertNotEqual(data["pytest_exit_code"], 0)

    def test_source_code_no_hardcoded_82_and_no_regex_console_parsing(self):
        """scripts/run_tests.py 소스 코드 정적 검증 (82 하드코딩 제거 및 콘솔 정규식 스크래핑 완전 배제 확인)"""
        runner_source = (BASE_DIR / "scripts" / "run_tests.py").read_text(encoding="utf-8")

        # 1. 고정된 82 기대값 하드코딩 배열 부재 확인
        self.assertNotIn("TEST_SUITES = [", runner_source, "TEST_SUITES 하드코딩 배열이 제거되어야 함")
        self.assertNotIn('"expected_count": 40', runner_source)
        self.assertNotIn('"expected_count": 11', runner_source)
        self.assertNotIn('"expected_count": 15', runner_source)
        self.assertNotIn('"expected_count": 16', runner_source)
        self.assertNotIn("total_expected = 82", runner_source)

        # 2. 콘솔 텍스트 정규식 파싱(parse_pytest_summary / re.search r'(\d+)\s+passed') 부재 확인
        self.assertNotIn("def parse_pytest_summary", runner_source, "콘솔 텍스트 정규식 파서 함수가 제거되어야 함")
        self.assertNotIn(r're.search(r"(\d+)\s+passed"', runner_source)

        # 3. JUnit XML 파싱 라이브러리 및 함수 존재 확인
        self.assertIn("xml.etree.ElementTree", runner_source)
        self.assertIn("def parse_junit_xml", runner_source)
        self.assertIn("junit_family=xunit2", runner_source)

    # =========================================================================
    # Phase 8 Step 8-1 회귀 검증 테스트 (추가 요구사항)
    # =========================================================================

    def test_regression_discover_test_files(self):
        """[회귀검증 1] 자동 파일 발견: 하드코딩 없이 테스트 파일 목록 탐색 및 필터링 검증"""
        # 1. 실제 tests 디렉터리 자동 탐색
        files = discover_test_files("tests")
        self.assertGreaterEqual(len(files), 10, "tests 디렉터리 내 최소 10개 이상의 테스트 파일이 발견되어야 함")
        file_names = [f.name for f in files]
        self.assertIn("test_phase4_stage4a.py", file_names)
        self.assertIn("test_phase4_stage4d.py", file_names)
        self.assertIn("test_run_tests_runner.py", file_names)

        # 2. 단일 파일 지정 시 단일 파일 리스트 반환
        single = discover_test_files("tests/test_phase4_stage4a.py")
        self.assertEqual(len(single), 1)
        self.assertEqual(single[0].name, "test_phase4_stage4a.py")

        # 3. 존재하지 않는 경로 지정 시 빈 리스트 반환
        non_existent = discover_test_files("invalid/non_existent_dir_999")
        self.assertEqual(non_existent, [])

        # 4. 임시 디렉터리 생성 후 __pycache__ 및 일반 py 파일 필터링 검증
        with tempfile.TemporaryDirectory() as temp_d:
            td = Path(temp_d)
            (td / "test_one.py").write_text("#", encoding="utf-8")
            (td / "another_test.py").write_text("#", encoding="utf-8")
            (td / "helper.py").write_text("# not a test", encoding="utf-8")
            cache_dir = td / "__pycache__"
            cache_dir.mkdir()
            (cache_dir / "test_cached.py").write_text("# cached", encoding="utf-8")

            discovered = discover_test_files(td)
            d_names = [p.name for p in discovered]
            self.assertEqual(d_names, ["another_test.py", "test_one.py"])
            self.assertNotIn("helper.py", d_names)
            self.assertNotIn("test_cached.py", d_names)

    def test_regression_subprocess_isolation_file_by_file(self):
        """[회귀검증 2] 파일별 Subprocess 격리: 파일마다 독립 subprocess.run 호출 및 파라미터 격리 검증"""
        mock_files = [
            Path(BASE_DIR / "tests" / "test_mod_a.py"),
            Path(BASE_DIR / "tests" / "test_mod_b.py")
        ]
        sample_pass_xml = parse_junit_xml(SAMPLE_ALL_PASSED_XML)

        call_commands = []

        def mock_subprocess_run(cmd, *args, **kwargs):
            call_commands.append(cmd)
            # cmd 내의 --junitxml 파일 경로 찾아서 XML 작성
            for arg in cmd:
                if arg.startswith("--junitxml="):
                    xml_p = arg.split("=", 1)[1]
                    Path(xml_p).write_text(SAMPLE_ALL_PASSED_XML, encoding="utf-8")
            return Mock(returncode=0, stdout="mock pass", stderr="")

        with patch("scripts.run_tests.discover_test_files", return_value=mock_files), \
             patch("scripts.run_tests.subprocess.run", side_effect=mock_subprocess_run):

            ret = run_all_tests(test_target="mock_tests")
            self.assertEqual(ret, 0)
            self.assertEqual(len(call_commands), 2, "2개 파일에 대해 정확히 2번의 격리된 subprocess.run이 호출되어야 함")

            # 첫 번째 호출 검증
            cmd1 = call_commands[0]
            self.assertIn(str(mock_files[0]), cmd1)
            self.assertNotIn(str(mock_files[1]), cmd1, "첫 번째 subprocess에는 두 번째 파일이 포함되지 않아야 함 (격리)")

            # 두 번째 호출 검증
            cmd2 = call_commands[1]
            self.assertIn(str(mock_files[1]), cmd2)
            self.assertNotIn(str(mock_files[0]), cmd2, "두 번째 subprocess에는 첫 번째 파일이 포함되지 않아야 함 (격리)")

    def test_regression_partial_subprocess_crash_failure(self):
        """[회귀검증 3] 일부 Subprocess 비정상 종료 (0xC0000005 등) 시 전체 실패 및 세부 원인 기록 검증"""
        mock_files = [
            Path(BASE_DIR / "tests" / "test_normal.py"),
            Path(BASE_DIR / "tests" / "test_crasher.py")
        ]

        # 0xC0000005 (STATUS_ACCESS_VIOLATION): Windows에서 부호 있는 -1073741819 또는 부호 없는 3221225477로 전달됨
        win_access_violation_code = -1073741819

        # decode_exit_code 디코딩 기능 검증
        decoded_msg = decode_exit_code(win_access_violation_code)
        self.assertIn("STATUS_ACCESS_VIOLATION", decoded_msg)
        self.assertIn("0xC0000005", decoded_msg)

        def mock_subprocess_run(cmd, *args, **kwargs):
            is_crasher = any("test_crasher.py" in str(c) for c in cmd)
            for arg in cmd:
                if arg.startswith("--junitxml="):
                    xml_p = arg.split("=", 1)[1]
                    if not is_crasher:
                        Path(xml_p).write_text(SAMPLE_ALL_PASSED_XML, encoding="utf-8")
            if is_crasher:
                return Mock(returncode=win_access_violation_code, stdout="", stderr="Windows crash dump 0xC0000005")
            return Mock(returncode=0, stdout="passed", stderr="")

        with tempfile.TemporaryDirectory() as temp_dir:
            json_file = Path(temp_dir) / "crash_result.json"

            with patch("scripts.run_tests.discover_test_files", return_value=mock_files), \
                 patch("scripts.run_tests.subprocess.run", side_effect=mock_subprocess_run):

                ret = run_all_tests(
                    test_target="mock_tests",
                    json_output_path=str(json_file)
                )

                # 한 subprocess가 크래시 났으므로 전체 종료 코드는 반드시 1이어야 함
                self.assertEqual(ret, 1, "한 subprocess 비정상 종료 시 전체 결과는 반드시 실패(1)여야 함")
                self.assertTrue(json_file.exists())

                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                self.assertFalse(data["all_passed"], "all_passed는 False여야 함")
                self.assertEqual(data["summary"]["crashes"], 1, "crash 건수가 1로 집계되어야 함")
                self.assertGreater(len(data["crashes"]), 0)

                crash_info = data["crashes"][0]
                self.assertIn("test_crasher", crash_info["module"])
                self.assertEqual(crash_info["exit_code"], win_access_violation_code)
                self.assertIn("0xC0000005", crash_info["exit_description"])

    def test_regression_merge_junit_xmls_totals_and_failures(self):
        """[회귀검증 4] 여러 JUnit XML 결과의 총계 및 실패 상세 병합 (merge_junit_xmls) 검증"""
        with tempfile.TemporaryDirectory() as temp_dir:
            td = Path(temp_dir)
            xml1 = td / "sub1.xml"
            xml2 = td / "sub2.xml"
            merged_out = td / "merged.xml"

            # sub1: 3 통과 (0.45s)
            xml1.write_text(SAMPLE_ALL_PASSED_XML, encoding="utf-8")
            # sub2: 4개 (1 pass, 1 fail, 1 error, 1 skip) (1.234s)
            xml2.write_text(SAMPLE_VALID_JUNIT_XML, encoding="utf-8")

            crash_items = [{
                "module": "tests.test_crash_mod",
                "time": 0.500,
                "message": "STATUS_ACCESS_VIOLATION (0xC0000005)",
                "details": "Access violation occurred at 0x7FFF"
            }]

            merged_tree = merge_junit_xmls(
                xml_sources=[xml1, xml2],
                output_path=merged_out,
                crash_items=crash_items,
                total_elapsed=2.184
            )

            root = merged_tree.getroot()
            self.assertEqual(root.tag, "testsuites")

            # 총계 검증: sub1(3) + sub2(4) + crash(1) = 8
            self.assertEqual(root.get("tests"), "8")
            self.assertEqual(root.get("failures"), "1")
            # errors: sub2(1) + crash(1) = 2
            self.assertEqual(root.get("errors"), "2")
            self.assertEqual(root.get("skipped"), "1")

            # 저장된 파일 파싱 재검증
            self.assertTrue(merged_out.exists())
            re_tree = ET.parse(str(merged_out))
            re_root = re_tree.getroot()
            self.assertEqual(re_root.get("tests"), "8")
            self.assertEqual(re_root.get("failures"), "1")
            self.assertEqual(re_root.get("errors"), "2")

            # crash testsuite가 추가되었는지 확인
            crash_suite = re_root.find(".//testsuite[@name='tests.test_crash_mod']")
            self.assertIsNotNone(crash_suite)
            tc = crash_suite.find("testcase")
            self.assertIsNotNone(tc)
            err = tc.find("error")
            self.assertIsNotNone(err)
            self.assertIn("0xC0000005", err.get("message"))

    def test_regression_assertion_failure_does_not_count_as_crash(self):
        """[회귀검증 5] 일반 assertion 실패(exit 1) 주입 시 crash로 오분류되지 않고 JSON/XML 집계가 1:1 일치하는지 검증"""
        fail_xml_content = """<?xml version="1.0" encoding="utf-8"?>
<testsuites>
  <testsuite name="test_fail" tests="1" failures="1" errors="0" skipped="0" time="0.050">
    <testcase classname="tests.test_fail" name="test_bad_assertion" time="0.050">
      <failure message="assert 1 == 2">AssertionError: assert 1 == 2</failure>
    </testcase>
  </testsuite>
</testsuites>
"""
        mock_files = [Path(BASE_DIR / "tests" / "test_fail.py")]

        def mock_subprocess_run(cmd, *args, **kwargs):
            for arg in cmd:
                if arg.startswith("--junitxml="):
                    xml_p = arg.split("=", 1)[1]
                    Path(xml_p).write_text(fail_xml_content, encoding="utf-8")
            return Mock(returncode=1, stdout="1 failed", stderr="")

        with tempfile.TemporaryDirectory() as temp_dir:
            json_file = Path(temp_dir) / "fail_result.json"
            xml_file = Path(temp_dir) / "fail_result.xml"

            with patch("scripts.run_tests.discover_test_files", return_value=mock_files), \
                 patch("scripts.run_tests.subprocess.run", side_effect=mock_subprocess_run):

                ret = run_all_tests(
                    test_target="mock_tests",
                    json_output_path=str(json_file),
                    junit_output_path=str(xml_file)
                )

                self.assertEqual(ret, 1, "테스트 실패 시 러너 종료 코드는 1이어야 함")
                self.assertTrue(json_file.exists())
                self.assertTrue(xml_file.exists())

                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                # JSON 집계 검증: 일반 assertion failure는 crash가 아니어야 함!
                self.assertFalse(data["all_passed"])
                self.assertEqual(data["summary"]["total_tests"], 1)
                self.assertEqual(data["summary"]["failures"], 1)
                self.assertEqual(data["summary"]["errors"], 0)
                self.assertEqual(data["summary"]["crashes"], 0, "일반 assertion 실패는 crash 건수가 0이어야 함")
                self.assertEqual(len(data["crashes"]), 0)

                # JUnit XML 집계 검증: tests=1, failures=1, errors=0
                tree = ET.parse(str(xml_file))
                root = tree.getroot()
                self.assertEqual(root.get("tests"), "1", "JUnit XML tests는 1이어야 함 (중복 합성 suite 방지)")
                self.assertEqual(root.get("failures"), "1")
                self.assertEqual(root.get("errors"), "0", "일반 assertion 실패 시 errors는 0이어야 함")

    def test_regression_no_discovery_generates_error_junit_xml(self):
        """[회귀검증 6] 테스트 미발견 시 이전 성공 XML을 덮어쓰고 오류를 나타내는 JUnit XML 생성 검증"""
        with tempfile.TemporaryDirectory() as temp_dir:
            xml_file = Path(temp_dir) / "legacy_result.xml"
            json_file = Path(temp_dir) / "legacy_result.json"

            # 이전에 성공했던 잔재 XML 미리 생성
            xml_file.write_text(SAMPLE_ALL_PASSED_XML, encoding="utf-8")

            with patch("scripts.run_tests.discover_test_files", return_value=[]):
                ret = run_all_tests(
                    test_target="non_existent_path",
                    json_output_path=str(json_file),
                    junit_output_path=str(xml_file)
                )

                self.assertEqual(ret, 1, "테스트 미발견 시 종료 코드는 1이어야 함")
                self.assertTrue(xml_file.exists())

                # XML이 이전 성공 잔재가 아니라 최신 오류 XML로 덮어써졌는지 검증
                tree = ET.parse(str(xml_file))
                root = tree.getroot()
                self.assertEqual(root.get("tests"), "1")
                self.assertEqual(root.get("errors"), "1")
                self.assertEqual(root.get("failures"), "0")

                suite = root.find(".//testsuite[@name='discovery']")
                self.assertIsNotNone(suite)
                tc = suite.find("testcase")
                self.assertIsNotNone(tc)
                err = tc.find("error")
                self.assertIsNotNone(err)
                self.assertIn("No test files found", err.get("message"))

    def test_regression_crash_with_valid_xml_and_corrupt_xml_single_counting(self):
        """[회귀검증 7] 정상 XML 후 크래시 시 JSON/XML 동일 집계 및 손상 XML 단일 집계(중복 방지) 검증"""
        valid_xml_content = """<?xml version="1.0" encoding="utf-8"?>
<testsuites>
  <testsuite name="test_valid_crash" tests="1" failures="0" errors="0" skipped="0" time="0.050">
    <testcase classname="tests.test_valid_crash" name="test_ok" time="0.050" />
  </testsuite>
</testsuites>
"""
        corrupt_xml_content = "<testsuites><unclosed_tag"

        # 1. 정상 XML 작성 후 프로세스가 0xC0000005 크래시 발생
        with tempfile.TemporaryDirectory() as temp_dir:
            jf = Path(temp_dir) / "crash_valid.json"
            xf = Path(temp_dir) / "crash_valid.xml"

            def mock_run_valid_crash(cmd, *a, **k):
                for arg in cmd:
                    if arg.startswith("--junitxml="):
                        Path(arg.split("=", 1)[1]).write_text(valid_xml_content, encoding="utf-8")
                return Mock(returncode=-1073741819, stdout="", stderr="Crash 0xC0000005")

            with patch("scripts.run_tests.discover_test_files", return_value=[Path(BASE_DIR / "tests" / "test_valid_crash.py")]), \
                 patch("scripts.run_tests.subprocess.run", side_effect=mock_run_valid_crash):

                ret = run_all_tests(json_output_path=str(jf), junit_output_path=str(xf))
                self.assertEqual(ret, 1)

                with open(jf, encoding="utf-8") as f:
                    jdata = json.load(f)
                xroot = ET.parse(str(xf)).getroot()

                # 원래 테스트 1개 + 크래시 1개 = 총 2개 테스트, errors 1개로 양쪽 완벽 일치!
                self.assertEqual(jdata["summary"]["total_tests"], 2)
                self.assertEqual(jdata["summary"]["passed"], 1)
                self.assertEqual(jdata["summary"]["errors"], 1)
                self.assertEqual(jdata["summary"]["crashes"], 1)

                # 모듈별 집계에서도 total=2, errors=1 갱신 검증
                self.assertEqual(len(jdata["modules"]), 1)
                self.assertEqual(jdata["modules"][0]["total"], 2)
                self.assertEqual(jdata["modules"][0]["errors"], 1)

                self.assertEqual(xroot.get("tests"), "2")
                self.assertEqual(xroot.get("errors"), "1")
                self.assertEqual(xroot.get("failures"), "0")

        # 2. 빈 testsuite (<testsuite tests="0"/>) 작성 후 치명적 오류 (exit 4) 발생
        empty_suite_xml = """<?xml version="1.0" encoding="utf-8"?>
<testsuites>
  <testsuite name="pytest" tests="0" failures="0" errors="0" skipped="0" time="0.0">
  </testsuite>
</testsuites>
"""
        with tempfile.TemporaryDirectory() as temp_dir:
            jf = Path(temp_dir) / "empty_crash.json"
            xf = Path(temp_dir) / "empty_crash.xml"

            def mock_run_empty_crash(cmd, *a, **k):
                for arg in cmd:
                    if arg.startswith("--junitxml="):
                        Path(arg.split("=", 1)[1]).write_text(empty_suite_xml, encoding="utf-8")
                return Mock(returncode=4, stdout="", stderr="Fatal exit 4")

            with patch("scripts.run_tests.discover_test_files", return_value=[Path(BASE_DIR / "tests" / "test_empty_crash.py")]), \
                 patch("scripts.run_tests.subprocess.run", side_effect=mock_run_empty_crash):

                ret = run_all_tests(json_output_path=str(jf), junit_output_path=str(xf))
                self.assertEqual(ret, 1)

                with open(jf, encoding="utf-8") as f:
                    jdata = json.load(f)
                xroot = ET.parse(str(xf)).getroot()

                # 빈 suite 크래시 시 JSON: tests=1, errors=1, 모듈: total=1, errors=1, XML: tests=1, errors=1 완벽 일치!
                self.assertEqual(jdata["summary"]["total_tests"], 1)
                self.assertEqual(jdata["summary"]["errors"], 1)
                self.assertEqual(len(jdata["modules"]), 1)
                self.assertEqual(jdata["modules"][0]["total"], 1)
                self.assertEqual(jdata["modules"][0]["errors"], 1)

                self.assertEqual(xroot.get("tests"), "1")
                self.assertEqual(xroot.get("errors"), "1")

        # 2. 손상된 XML 작성 시 중복 집계 없이 단 1회만 집계
        with tempfile.TemporaryDirectory() as temp_dir:
            jf = Path(temp_dir) / "corrupt.json"
            xf = Path(temp_dir) / "corrupt.xml"

            def mock_run_corrupt(cmd, *a, **k):
                for arg in cmd:
                    if arg.startswith("--junitxml="):
                        Path(arg.split("=", 1)[1]).write_text(corrupt_xml_content, encoding="utf-8")
                return Mock(returncode=1, stdout="", stderr="Corrupted XML")

            with patch("scripts.run_tests.discover_test_files", return_value=[Path(BASE_DIR / "tests" / "test_corrupt.py")]), \
                 patch("scripts.run_tests.subprocess.run", side_effect=mock_run_corrupt):

                ret = run_all_tests(json_output_path=str(jf), junit_output_path=str(xf))
                self.assertEqual(ret, 1)

                with open(jf, encoding="utf-8") as f:
                    jdata = json.load(f)
                xroot = ET.parse(str(xf)).getroot()

                # 손상된 XML은 단일 에러로 한 번만 집계 (중복 방지: tests=1, errors=1)
                self.assertEqual(jdata["summary"]["total_tests"], 1)
                self.assertEqual(jdata["summary"]["errors"], 1)
                self.assertEqual(xroot.get("tests"), "1")
                self.assertEqual(xroot.get("errors"), "1")

    def test_regression_keyword_and_marker_filter_exit_5_handling(self):
        """[회귀검증 8] 필터(-k/-m) 적용 시 exit 5 파일 건너뜀 및 -x 중단 방지, 전체 0건 시 정상 실패 검증"""
        file_a = Path(BASE_DIR / "tests" / "test_mod_empty.py")
        file_b = Path(BASE_DIR / "tests" / "test_mod_match.py")
        match_xml = SAMPLE_ALL_PASSED_XML

        # 1. 파일 A는 필터 제외(exit 5), 파일 B는 매칭 통과(exit 0) 시 성공
        def mock_run_filter(cmd, *a, **k):
            if "test_mod_empty.py" in str(cmd):
                return Mock(returncode=5, stdout="no tests collected", stderr="")
            for arg in cmd:
                if arg.startswith("--junitxml="):
                    Path(arg.split("=", 1)[1]).write_text(match_xml, encoding="utf-8")
            return Mock(returncode=0, stdout="3 passed", stderr="")

        with tempfile.TemporaryDirectory() as temp_dir:
            jf = Path(temp_dir) / "filter_pass.json"
            with patch("scripts.run_tests.discover_test_files", return_value=[file_a, file_b]), \
                 patch("scripts.run_tests.subprocess.run", side_effect=mock_run_filter):

                # fail-fast(-x)가 켜져 있어도 파일 A의 exit 5로 인해 중단되지 않고 파일 B까지 실행되어 성공해야 함
                ret = run_all_tests(
                    keyword="match_only",
                    fail_fast=True,
                    json_output_path=str(jf)
                )

                self.assertEqual(ret, 0, "필터 매칭된 테스트가 통과하면 전체 결과는 0이어야 함")
                with open(jf, encoding="utf-8") as f:
                    data = json.load(f)
                self.assertTrue(data["all_passed"])
                self.assertEqual(data["summary"]["total_tests"], 3)
                self.assertEqual(data["summary"]["passed"], 3)
                self.assertEqual(data["summary"]["failures"], 0)
                self.assertEqual(data["summary"]["errors"], 0)

        # 2. 전체 파일에서 필터 매칭 결과가 0건일 때 정상 실패 판정
        def mock_run_all_empty(cmd, *a, **k):
            return Mock(returncode=5, stdout="no tests collected", stderr="")

        with tempfile.TemporaryDirectory() as temp_dir:
            jf = Path(temp_dir) / "filter_zero.json"
            with patch("scripts.run_tests.discover_test_files", return_value=[file_a, file_b]), \
                 patch("scripts.run_tests.subprocess.run", side_effect=mock_run_all_empty):

                ret = run_all_tests(
                    keyword="matches_nothing_at_all",
                    json_output_path=str(jf)
                )

                self.assertEqual(ret, 1, "필터 결과 전체 매칭 0건이면 실패(1)여야 함")
                with open(jf, encoding="utf-8") as f:
                    data = json.load(f)
                self.assertFalse(data["all_passed"])
                self.assertEqual(data["summary"]["total_tests"], 0)


if __name__ == "__main__":
    unittest.main()


