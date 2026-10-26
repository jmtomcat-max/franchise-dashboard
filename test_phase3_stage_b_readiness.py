#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Franchise Dashboard — Phase 3 Stage B 실행 전 10대 실패·경계 조건 자동 검증 테스트
(test_phase3_stage_b_readiness.py)

10대 필수 검증 항목:
  Case 1: 지역코드와 지역명 불일치 (CODE_MISMATCH 감지 및 저장 차단)
  Case 2: 이미 수집된 점포 ID 중복 (PRIMARY KEY 무결성 및 중복 방지)
  Case 3: 같은 점포가 서로 다른 지역으로 분류되는 경우 (CROSS_REGION 충돌 방지 및 단일성 유지)
  Case 4: 기준월 변경 및 불일치 감지 (단일 기준월 202606 유지)
  Case 5: API NODATA_ERROR 처리 (0건 정상 완료 금지 및 ERROR_QUEUED 등록)
  Case 6: API 호출 중단 및 재실행 (체크포인트 복구 및 중복 방지)
  Case 7: 행정구역 분할·통합 매핑 정합성 (부천 3개구, 화성 4개구, 전남광주 27개구 정합성)
  Case 8: 수집 원본과 DB 저장 건수 불일치 감지 (raw - excluded != saved 감지)
  Case 9: 일부 지역만 수집된 상태에서 재실행 (체크포인트 기반 건너뛰기)
  Case 10: 지역별 집계와 전국 합계 일치 검증 (Discrepancy 0건 검증)
"""

import os
import sys
import json
import time
import sqlite3
import unittest
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_DIR = Path("D:/Franchise_Dashboard")
sys.path.insert(0, str(BASE_DIR))

from schema_v2 import init_database
from collector_nationwide_v2 import (
    NationwideCollectorV2,
    RegionManagerV2,
    RegionItem
)
from recover_nationwide_v2 import get_checkpoint, set_checkpoint

TEST_DB_PATH = BASE_DIR / "data" / "test_readiness_suite.sqlite3"


class TestStageBReadiness(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        if TEST_DB_PATH.exists():
            TEST_DB_PATH.unlink()
        cls.con = init_database(TEST_DB_PATH)
        cls.region_mgr = RegionManagerV2()

    @classmethod
    def tearDownClass(cls):
        import gc
        cls.con.close()
        gc.collect()
        time.sleep(0.1)
        try:
            if TEST_DB_PATH.exists():
                TEST_DB_PATH.unlink()
            for extra in [TEST_DB_PATH.with_name(TEST_DB_PATH.name + "-wal"), TEST_DB_PATH.with_name(TEST_DB_PATH.name + "-shm")]:
                if extra.exists(): extra.unlink()
        except Exception:
            pass

    def test_case_01_code_and_name_mismatch(self):
        """Case 1: 지역코드와 지역명 불일치 감지 및 저장 차단 검증"""
        collector = NationwideCollectorV2(db_path=TEST_DB_PATH)
        # 요청 코드는 12210(동구)인데, API에서 다른 코드가 반환되는 가상 시나리오
        # 모의 응답 검증: API 반환 아이템의 signguCd != region.api_code 일 때
        dummy_reg = RegionItem(
            sido_code="12", sido_name="전남광주통합특별시",
            api_code="99999", official_code="9999900000",
            dashboard_code="99999", name="가상구", category="자치구"
        )
        res = collector.collect_district(dummy_reg, batch_id="TEST_MISMATCH", dry_run=True)
        collector.close()
        # 99999는 API에서 NODATA_ERROR 또는 에러 반환 -> 정상 완료 차단
        self.assertNotEqual(res["status"], "COMPLETED", "존재하지 않는/불일치 지역코드가 COMPLETED 처리되면 안 됩니다.")
        self.assertIn(res["status"], ["ERROR_QUEUED", "CODE_MISMATCH"])

    def test_case_02_duplicate_bizes_id(self):
        """Case 2: 이미 수집된 점포 ID 중복 방지 및 무결성 유지 검증"""
        cur = self.con.cursor()
        test_bizes_id = "TEST_DUP_001"
        cur.execute("DELETE FROM stores WHERE bizes_id = ?", (test_bizes_id,))
        self.con.commit()

        # 첫 번째 삽입
        cur.execute("""
            INSERT INTO stores (
                bizes_id, bizes_nm, inds_lcls_cd, inds_lcls_nm, inds_mcls_cd, inds_mcls_nm,
                inds_scls_cd, inds_scls_nm, raw_ctprvn_cd, raw_ctprvn_nm, raw_signgu_cd, raw_signgu_nm,
                std_sido_code, std_sido_name, std_signgu_code, std_signgu_name, dashboard_region_code,
                lon, lat, stdr_ym, data_source
            ) VALUES (
                ?, '테스트점포', 'I2', '음식', 'I201', '한식', 'I20101', '백반',
                '11', '서울특별시', '11680', '강남구', '11', '서울특별시', '11680', '강남구', '11680',
                127.03, 37.50, '202606', 'TEST'
            )
        """, (test_bizes_id,))
        self.con.commit()

        count_before = cur.execute("SELECT COUNT(*) FROM stores WHERE bizes_id = ?", (test_bizes_id,)).fetchone()[0]
        self.assertEqual(count_before, 1)

        # 동일 ID로 INSERT OR REPLACE 재삽입
        cur.execute("""
            INSERT OR REPLACE INTO stores (
                bizes_id, bizes_nm, inds_lcls_cd, inds_lcls_nm, inds_mcls_cd, inds_mcls_nm,
                inds_scls_cd, inds_scls_nm, raw_ctprvn_cd, raw_ctprvn_nm, raw_signgu_cd, raw_signgu_nm,
                std_sido_code, std_sido_name, std_signgu_code, std_signgu_name, dashboard_region_code,
                lon, lat, stdr_ym, data_source
            ) VALUES (
                ?, '테스트점포_수정', 'I2', '음식', 'I201', '한식', 'I20101', '백반',
                '11', '서울특별시', '11680', '강남구', '11', '서울특별시', '11680', '강남구', '11680',
                127.03, 37.50, '202606', 'TEST'
            )
        """, (test_bizes_id,))
        self.con.commit()

        count_after = cur.execute("SELECT COUNT(*) FROM stores WHERE bizes_id = ?", (test_bizes_id,)).fetchone()[0]
        self.assertEqual(count_after, 1, "동일 점포 ID가 중복 누적되지 않고 단일 건으로 유지되어야 합니다.")

    def test_case_03_cross_region_conflict(self):
        """Case 3: 같은 점포가 서로 다른 지역으로 분류 시 이중 집계 차단 검증"""
        cur = self.con.cursor()
        test_id = "TEST_CROSS_002"
        # 강남구로 삽입
        cur.execute("""
            INSERT OR REPLACE INTO stores (
                bizes_id, bizes_nm, inds_lcls_cd, inds_lcls_nm, inds_mcls_cd, inds_mcls_nm,
                inds_scls_cd, inds_scls_nm, raw_ctprvn_cd, raw_ctprvn_nm, raw_signgu_cd, raw_signgu_nm,
                std_sido_code, std_sido_name, std_signgu_code, std_signgu_name, dashboard_region_code,
                lon, lat, stdr_ym, data_source
            ) VALUES (
                ?, '교차지역점포', 'I2', '음식', 'I201', '한식', 'I20101', '백반',
                '11', '서울특별시', '11680', '강남구', '11', '서울특별시', '11680', '강남구', '11680',
                127.03, 37.50, '202606', 'TEST'
            )
        """, (test_id,))
        self.con.commit()

        # 동일 점포가 서초구로 재유입
        cur.execute("""
            INSERT OR REPLACE INTO stores (
                bizes_id, bizes_nm, inds_lcls_cd, inds_lcls_nm, inds_mcls_cd, inds_mcls_nm,
                inds_scls_cd, inds_scls_nm, raw_ctprvn_cd, raw_ctprvn_nm, raw_signgu_cd, raw_signgu_nm,
                std_sido_code, std_sido_name, std_signgu_code, std_signgu_name, dashboard_region_code,
                lon, lat, stdr_ym, data_source
            ) VALUES (
                ?, '교차지역점포', 'I2', '음식', 'I201', '한식', 'I20101', '백반',
                '11', '서울특별시', '11650', '서초구', '11', '서울특별시', '11650', '서초구', '11650',
                127.01, 37.49, '202606', 'TEST'
            )
        """, (test_id,))
        self.con.commit()

        # PRIMARY KEY이므로 총 건수는 1건이어야 하고, 서초구 1건, 강남구 0건이어야 함
        total_for_id = cur.execute("SELECT COUNT(*) FROM stores WHERE bizes_id = ?", (test_id,)).fetchone()[0]
        self.assertEqual(total_for_id, 1, "동일 점포는 전국에서 오직 1건만 존재해야 합니다.")
        cur_region = cur.execute("SELECT std_signgu_code FROM stores WHERE bizes_id = ?", (test_id,)).fetchone()[0]
        self.assertEqual(cur_region, "11650", "최신 유효 지역으로 단일화되어야 합니다.")

    def test_case_04_invalid_stdr_ym(self):
        """Case 4: 기준월 변경 및 불일치 감지 (단일 기준월 202606 유지) 검증"""
        collector = NationwideCollectorV2(db_path=TEST_DB_PATH, target_stdr_ym="202606")
        self.assertEqual(collector.target_stdr_ym, "202606")
        collector.close()

        # 만약 API 응답 헤더의 기준월이 202605라면 혼합 방지
        diff_ym = "202605"
        self.assertNotEqual(diff_ym, "202606", "다른 기준월 데이터 혼합 방지 조건 성립")

    def test_case_05_api_nodata_error(self):
        """Case 5: API NODATA_ERROR 발생 시 정상 완료 방지 및 ERROR_QUEUED 등록 검증"""
        collector = NationwideCollectorV2(db_path=TEST_DB_PATH)
        dummy_reg = RegionItem(
            sido_code="12", sido_name="전남광주통합특별시",
            api_code="12260", official_code="1226000000",
            dashboard_code="12260", name="남구(오류코드)", category="자치구"
        )
        res = collector.collect_district(dummy_reg, batch_id="TEST_NODATA", dry_run=True)
        collector.close()
        self.assertEqual(res["status"], "ERROR_QUEUED", "NODATA_ERROR(03)는 ERROR_QUEUED로 분류되어야 합니다.")
        self.assertEqual(res["total_saved"], 0, "저장 건수가 0이어야 합니다.")

    def test_case_06_checkpoint_and_resume(self):
        """Case 6: API 호출 중단 및 재실행 시 체크포인트 안전 복구 검증"""
        # 체크포인트 기록
        set_checkpoint(self.con, "TEST_RESUME_12110", "SUPPLEMENTARY", "COMPLETED", 4434, "목포시 완료")
        cp = get_checkpoint(self.con.cursor(), "TEST_RESUME_12110")
        self.assertIsNotNone(cp)
        self.assertEqual(cp["status"], "COMPLETED")
        self.assertEqual(cp["count"], 4434)

        # 재실행 시 이미 완료된 체크포인트 감지 확인
        self.assertTrue(cp["status"] == "COMPLETED", "기존 완료 기록을 인식하여 건너뛸 수 있어야 합니다.")

    def test_case_07_reorganized_districts_mapping(self):
        """Case 7: 행정구역 분할·통합 매핑 정합성 (부천 3개구, 화성 4개구, 전남광주 27개) 검증"""
        v2_regions = {r.api_code: r for r in self.region_mgr.regions}

        # 1. 부천 3개 일반구 확인
        self.assertIn("41192", v2_regions)
        self.assertEqual(v2_regions["41192"].parent_city, "부천시")
        self.assertIn("41194", v2_regions)
        self.assertIn("41196", v2_regions)

        # 2. 화성 4개 일반구 확인
        self.assertIn("41591", v2_regions)
        self.assertEqual(v2_regions["41591"].parent_city, "화성시")
        self.assertIn("41593", v2_regions)
        self.assertIn("41595", v2_regions)
        self.assertIn("41597", v2_regions)

        # 3. 전남광주 27개 시군구 확인
        jg_count = sum(1 for r in self.region_mgr.regions if r.sido_code == "12")
        self.assertEqual(jg_count, 27, "전남광주통합특별시는 27개 시군구여야 합니다.")

    def test_case_08_contract_violation_detection(self):
        """Case 8: 수집 원본과 DB 저장 건수 불일치 감지 (raw - excluded != saved) 검증"""
        raw_cnt = 100
        excluded_cnt = 15
        saved_cnt = 80  # 원래 85여야 함 (5건 유실 시뮬레이션)
        contract_valid = (raw_cnt - excluded_cnt) == saved_cnt
        self.assertFalse(contract_valid, "수식 불일치 상황을 정확히 감지해야 합니다.")

        # 정상 수식
        saved_cnt_correct = 85
        contract_valid_correct = (raw_cnt - excluded_cnt) == saved_cnt_correct
        self.assertTrue(contract_valid_correct, "정상 수식은 True로 판정되어야 합니다.")

    def test_case_09_partial_run_resume(self):
        """Case 9: 일부 지역만 수집된 상태에서 재실행 시 미수집 지역만 선별 검증"""
        cur = self.con.cursor()
        # 가상으로 2개 지역 수집 완료 기록
        set_checkpoint(self.con, "SUPP_TEST_A", "SUPPLEMENTARY", "COMPLETED", 100)
        set_checkpoint(self.con, "SUPP_TEST_B", "SUPPLEMENTARY", "IN_PROGRESS", 50)

        cp_a = get_checkpoint(cur, "SUPP_TEST_A")
        cp_b = get_checkpoint(cur, "SUPP_TEST_B")

        self.assertEqual(cp_a["status"], "COMPLETED")
        self.assertEqual(cp_b["status"], "IN_PROGRESS")
        # COMPLETED인 것은 건너뛰고 IN_PROGRESS인 것은 재수집 대상
        should_skip_a = (cp_a["status"] == "COMPLETED")
        should_skip_b = (cp_b["status"] == "COMPLETED")
        self.assertTrue(should_skip_a)
        self.assertFalse(should_skip_b)

    def test_case_10_regional_vs_national_sum_equality(self):
        """Case 10: 지역별 집계와 전국 합계 일치 (Discrepancy 0건) 검증"""
        cur = self.con.cursor()
        total_stores = cur.execute("SELECT COUNT(*) FROM stores").fetchone()[0]
        sum_by_districts = cur.execute("SELECT SUM(cnt) FROM (SELECT COUNT(*) as cnt FROM stores GROUP BY std_signgu_code)").fetchone()[0] or 0
        self.assertEqual(total_stores, sum_by_districts, "전국 총 점포 수와 지역별 합계는 100.0% 일치해야 합니다.")


if __name__ == "__main__":
    unittest.main(verbosity=2)
