#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Franchise Dashboard — Phase 3 Stage A 자동 검증 테스트 스위트 (test_phase3_stage_a.py)

검증 항목:
  Test 1: 기존 3종 DB SHA-256 해시 및 레코드 수 보존 검증 (읽기 전용 보존 계약)
  Test 2: 신규 행정구역 코드 체계(regions_v2.json) 무결성 및 전수 고유성 검증
  Test 3: 신규 DB 스키마(nationwide_food_stores_v2) 테이블, 뷰, 인덱스 무결성 검증
  Test 4: 소진공 API 실측 표본 검증 (전남광주 12, 강원 51, 전북 52, 부천, 화성 등)
  Test 5: 데이터 계약 무결성 검증 (raw - excluded == saved) 및 업종 필터링(주점/구내식당 제외, 뷔페 포함)
  Test 6: 오류 및 경계 조건 처리 검증 (NODATA_ERROR 0건 완료 금지 및 ERROR_QUEUED 확인)
  Test 7: 데이터 복구 범위 산정 무결성 검증 (정상 184개 595,453건 vs 보완 72개)
"""

import os
import sys
import json
import sqlite3
import hashlib
import unittest
from pathlib import Path

# 콘솔 UTF-8 설정
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
    RegionItem,
    get_api_key,
    EXCLUDED_MIDDLE_CODES,
    EXCLUDED_SMALL_CODES
)

# 기준 SHA-256 해시 및 레코드 수
BASELINE = {
    "gangnam": {
        "path": BASE_DIR / "gangnam_food_stores.sqlite3",
        "expected_count": 11296,
        "expected_sha256": "fee3b58651cfed5c390c0b95db02b05ebe92df18619a06f4e399d429236f3a78"
    },
    "seoul": {
        "path": BASE_DIR / "data" / "seoul_food_stores.sqlite3",
        "expected_count": 124104,
        "expected_sha256": "60e561d39aa1fd8a254553a481c5aa93f5144ead2beb8561f8951a9470e66ba5"
    },
    "nationwide": {
        "path": BASE_DIR / "data" / "nationwide_food_stores.sqlite3",
        "expected_count": 595453,
        "expected_sha256": "8294a0fe86ac4e0e4cb3aa5c38aa879675b1a93325da73edcb6e3c875086933d"
    }
}


def compute_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


class TestPhase3StageA(unittest.TestCase):

    def test_01_existing_db_preservation(self):
        """Test 1: 기존 DB 3종 보존 상태 및 SHA-256 해시 일치 검증"""
        for name, spec in BASELINE.items():
            path = spec["path"]
            self.assertTrue(path.exists(), f"기존 DB 파일 부재: {path}")

            actual_sha = compute_sha256(path)
            self.assertEqual(
                actual_sha,
                spec["expected_sha256"],
                f"[{name}] SHA-256 해시 불일치 (기존 파일 변조 감지): {actual_sha} != {spec['expected_sha256']}"
            )

            con = sqlite3.connect(path)
            cur = con.cursor()
            cnt = cur.execute("SELECT COUNT(*) FROM stores").fetchone()[0]
            con.close()
            self.assertEqual(
                cnt,
                spec["expected_count"],
                f"[{name}] 점포 레코드 수 불일치: {cnt} != {spec['expected_count']}"
            )

    def test_02_region_code_system_v2(self):
        """Test 2: 신규 행정구역 코드 체계(regions_v2.json) 무결성 및 전수 고유성 검증"""
        v2_path = BASE_DIR / "config" / "regions_v2.json"
        self.assertTrue(v2_path.exists(), "config/regions_v2.json 파일이 존재하지 않습니다.")

        with open(v2_path, "r", encoding="utf-8") as f:
            v2_data = json.load(f)

        provinces = v2_data.get("provinces", [])
        self.assertEqual(len(provinces), 16, "대한민국 시도 개수는 전남광주 통합 반영 후 16개여야 합니다.")

        all_codes = []
        prov_map = {p["province_code"]: p for p in provinces}

        # 1. 시도별 핵심 개편 반영 여부 확인
        self.assertIn("12", prov_map, "전남광주통합특별시(12)가 누락되었습니다.")
        self.assertEqual(len(prov_map["12"]["districts"]), 27, "전남광주통합특별시 시군구는 27개여야 합니다.")

        self.assertIn("51", prov_map, "강원특별자치도(51)가 누락되었습니다.")
        self.assertEqual(len(prov_map["51"]["districts"]), 18, "강원특별자치도 시군은 18개여야 합니다.")

        self.assertIn("52", prov_map, "전북특별자치도(52)가 누락되었습니다.")
        self.assertEqual(len(prov_map["52"]["districts"]), 15, "전북특별자치도 시군구는 15개여야 합니다.")

        # 부천 3개구, 화성 4개구 확인
        gg_districts = {d["api_code"]: d["name"] for d in prov_map["41"]["districts"]}
        self.assertIn("41192", gg_districts, "부천시 원미구(41192) 누락")
        self.assertIn("41194", gg_districts, "부천시 소사구(41194) 누락")
        self.assertIn("41196", gg_districts, "부천시 오정구(41196) 누락")
        self.assertIn("41591", gg_districts, "화성시 만세구(41591) 누락")
        self.assertIn("41593", gg_districts, "화성시 효행구(41593) 누락")
        self.assertIn("41595", gg_districts, "화성시 병점구(41595) 누락")
        self.assertIn("41597", gg_districts, "화성시 동탄구(41597) 누락")

        # 경북 의성군 47730, 대구 군위군 27720 확인
        gb_districts = {d["api_code"]: d["name"] for d in prov_map["47"]["districts"]}
        self.assertIn("47730", gb_districts, "경북 의성군(47730) 누락")
        self.assertNotIn("47720", gb_districts, "경북에 구 군위군 코드 47720이 남아있습니다.")

        dg_districts = {d["api_code"]: d["name"] for d in prov_map["27"]["districts"]}
        self.assertIn("27720", dg_districts, "대구 군위군(27720) 누락")

        # 2. 전수 코드 고유성 검증 (256개 전체 중복 검사)
        for p in provinces:
            for d in p["districts"]:
                all_codes.append(d["api_code"])

        self.assertEqual(len(all_codes), 256, "전국 시군구 총수는 256개여야 합니다.")
        self.assertEqual(len(all_codes), len(set(all_codes)), "regions_v2.json 내에 중복 코드가 존재합니다.")

    def test_03_db_schema_v2(self):
        """Test 3: 신규 DB 스키마(nationwide_food_stores_v2) 구조 무결성 검증"""
        test_db = BASE_DIR / "data" / "temp_schema_test.sqlite3"
        try:
            con = init_database(test_db)
            cur = con.cursor()

            # 테이블 목록 확인
            tables = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
            required_tables = [
                "stores", "region_master", "collection_logs",
                "category_mappings", "brand_masters", "brand_aliases", "ftc_interfaces"
            ]
            for t in required_tables:
                self.assertIn(t, tables, f"필수 테이블 누락: {t}")

            # stores 테이블 필수 컬럼 확인
            store_cols = [r[1] for r in cur.execute("PRAGMA table_info(stores)").fetchall()]
            req_cols = [
                "bizes_id", "bizes_nm", "raw_ctprvn_cd", "raw_signgu_cd",
                "std_sido_code", "std_signgu_code", "dashboard_region_code",
                "lon", "lat", "stdr_ym", "data_source"
            ]
            for col in req_cols:
                self.assertIn(col, store_cols, f"stores 테이블 컬럼 누락: {col}")

            # 인덱스 목록 확인
            indexes = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='index'").fetchall()]
            self.assertIn("idx_stores_spatial", indexes, "공간 인덱스 누락")
            self.assertIn("idx_stores_sido_signgu", indexes, "시도-시군구 인덱스 누락")

            # 뷰 확인
            views = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='view'").fetchall()]
            self.assertIn("regional_3d_summary", views, "3D GIS 집계 뷰 누락")

            con.close()
        finally:
            if test_db.exists():
                test_db.unlink()
                for extra in [test_db.with_name(test_db.name + "-wal"), test_db.with_name(test_db.name + "-shm")]:
                    if extra.exists(): extra.unlink()

    def test_04_api_probe_verified_samples(self):
        """Test 4: 소진공 API 실측 표본 정상 응답 검증 (강원 51, 전북 52, 전남광주 12 등)"""
        key = get_api_key()
        self.assertTrue(bool(key), "공공데이터포털 API Key가 로드되지 않았습니다.")

        collector = NationwideCollectorV2(api_key=key)

        samples = [
            ("12270", "전남광주통합특별시", "남구"),
            ("51110", "강원특별자치도", "춘천시"),
            ("52111", "전북특별자치도", "전주시 완산구"),
            ("41192", "경기도", "부천시 원미구"),
            ("27720", "대구광역시", "군위군")
        ]

        for code, exp_sido, exp_name in samples:
            res = collector.call_api("signguCd", code, page_no=1, num_of_rows=1)
            self.assertTrue(res["success"], f"API 호출 실패 ({code})")
            body = res["data"].get("body", {})
            cnt = body.get("totalCount", 0)
            self.assertGreater(cnt, 0, f"점포 수 0건 발생 ({code}): {exp_sido} {exp_name}")
            items = body.get("items", [])
            self.assertTrue(len(items) > 0)
            ret_signgu = items[0].get("signguCd")
            self.assertEqual(ret_signgu, code, f"반환 코드 불일치: {ret_signgu} != {code}")

    def test_05_data_contract_and_filters(self):
        """Test 5: 데이터 계약 무결성(raw - excluded == saved) 및 외식업 업종 필터링 규칙 검증"""
        collector = NationwideCollectorV2()

        # 주점(I211) 제외 확인
        self.assertTrue(collector.is_store_excluded({"indsMclsCd": "I211", "indsSclsCd": "I21101"}))
        # 구내식당(I20701) 제외 확인
        self.assertTrue(collector.is_store_excluded({"indsMclsCd": "I207", "indsSclsCd": "I20701"}))
        # 뷔페(I20702) 반드시 포함 확인
        self.assertFalse(collector.is_store_excluded({"indsMclsCd": "I207", "indsSclsCd": "I20702"}))
        # 일반 한식(I20101) 포함 확인
        self.assertFalse(collector.is_store_excluded({"indsMclsCd": "I201", "indsSclsCd": "I20101"}))

        # 단일 시군구 표본 1페이지 dry_run 수식 검증
        reg = collector.region_mgr.get_by_code("12270")
        self.assertIsNotNone(reg)
        res = collector.collect_district(reg, batch_id="TEST_CONTRACT", dry_run=True, max_pages=1)
        self.assertTrue(res["contract_valid"], "데이터 계약 수식(raw - excluded == saved) 위반!")
        self.assertEqual(res["total_raw"] - res["total_excluded"], res["total_saved"])

    def test_06_nodata_error_handling(self):
        """Test 6: NODATA_ERROR 발생 시 0건 완료 처리 금지 및 ERROR_QUEUED 등록 검증"""
        collector = NationwideCollectorV2()
        # 미존재/오류 코드 12260 (구 남구 후보) 테스트
        dummy_reg = RegionItem(
            sido_code="12", sido_name="전남광주통합특별시",
            api_code="12260", official_code="1226000000",
            dashboard_code="12260", name="남구(구후보)", category="자치구"
        )
        res = collector.collect_district(dummy_reg, batch_id="TEST_NODATA", dry_run=True)
        self.assertEqual(res["status"], "ERROR_QUEUED", "NODATA_ERROR는 정상 0건 완료가 아닌 ERROR_QUEUED여야 합니다.")
        self.assertEqual(res["total_saved"], 0)
        self.assertIn("NODATA_ERROR", str(res["error"]))

    def test_07_recovery_scope_breakdown(self):
        """Test 7: 복구 범위 산정 무결성 검증 (정상 184개 지역 vs 보완 72개 지역)"""
        v2_path = BASE_DIR / "config" / "regions_v2.json"
        with open(v2_path, "r", encoding="utf-8") as f:
            v2_data = json.load(f)

        v2_codes = set(d["api_code"] for p in v2_data["provinces"] for d in p["districts"])

        v1_db_path = BASE_DIR / "data" / "nationwide_food_stores.sqlite3"
        con = sqlite3.connect(v1_db_path)
        cur = con.cursor()
        v1_progress = cur.execute("SELECT district_code, SUM(saved_count) FROM progress GROUP BY district_code").fetchall()
        con.close()

        v1_valid_codes = set(r[0] for r in v1_progress if (r[1] or 0) > 0)
        migratable = v2_codes.intersection(v1_valid_codes)
        supplementary = v2_codes - v1_valid_codes

        self.assertEqual(len(migratable), 184, f"v1 정상 이관 대상 시군구는 184개여야 합니다: {len(migratable)}")
        self.assertEqual(len(supplementary), 72, f"보완 수집 대상 시군구는 72개여야 합니다: {len(supplementary)}")
        self.assertEqual(len(migratable) + len(supplementary), 256)


if __name__ == "__main__":
    unittest.main(verbosity=2)
