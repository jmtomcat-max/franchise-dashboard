"""
Unit and Integration Tests for Phase 4 Stage 4D (Category Master Pipeline)
프로젝트: D:/Franchise_Dashboard
위치: tests/test_phase4_stage4d.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import unittest
import sqlite3
import json

from src.stage4d.schema_stage4d import CATEGORY_MASTER_DB_PATH
from src.stage4d.classifier import (
    NATIONWIDE_V2_DB_PATH,
    BRAND_MASTER_DB_PATH
)
from src.stage4d.taxonomy_master import (
    load_taxonomy_config,
    resolve_semas_to_mid
)


class TestPhase4Stage4D(unittest.TestCase):
    """Stage 4D 카테고리 마스터 및 분류 파이프라인 검증 테스트 스위트"""

    @classmethod
    def setUpClass(cls):
        cls.tax_config = load_taxonomy_config()
        cls.cat_conn = sqlite3.connect(CATEGORY_MASTER_DB_PATH)
        cls.cat_cur = cls.cat_conn.cursor()

    @classmethod
    def tearDownClass(cls):
        cls.cat_conn.close()

    def test_01_raw_db_immutability(self):
        """운영 원본 DB(nationwide_food_stores_v2.sqlite3) 점포수 보존 확인 (735,185건)"""
        conn = sqlite3.connect(NATIONWIDE_V2_DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT count(*) FROM stores")
        count = cur.fetchone()[0]
        conn.close()
        self.assertEqual(count, 735185, "운영 DB 전국 점포수가 735,185건이어야 합니다.")

    def test_02_brand_master_immutability(self):
        """선행 브랜드 마스터(brand_master_v1.sqlite3) 보존 확인 (5,063 브랜드, 735,208 링크)"""
        conn = sqlite3.connect(BRAND_MASTER_DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT count(*) FROM brands")
        brand_cnt = cur.fetchone()[0]
        cur.execute("SELECT count(*), count(distinct bizes_id) FROM store_brand_links")
        link_cnt, uniq_stores = cur.fetchone()
        conn.close()

        self.assertEqual(brand_cnt, 5063, "브랜드 마스터 수가 5,063건이어야 합니다.")
        self.assertEqual(link_cnt, 735208, "링크 총수가 735,208건이어야 합니다.")
        self.assertEqual(uniq_stores, 735185, "링크 내 고유 점포수가 735,185건이어야 합니다.")

    def test_03_major_categories_count_and_uniqueness(self):
        """8대 대분류 고유성 및 슬롯 개수 확인"""
        self.cat_cur.execute("SELECT count(*), count(distinct category_maj_id) FROM major_categories")
        cnt, uniq = self.cat_cur.fetchone()
        self.assertEqual(cnt, 8, "확정 대분류는 정확히 8개여야 합니다.")
        self.assertEqual(uniq, 8, "대분류 ID는 고유해야 합니다.")

    def test_04_mid_categories_count_and_distribution(self):
        """48대 중분류 고유성 및 8/5/6/5/6/6/6/6 배분 일치 확인"""
        self.cat_cur.execute("SELECT count(*), count(distinct category_mid_id) FROM mid_categories")
        cnt, uniq = self.cat_cur.fetchone()
        self.assertEqual(cnt, 48, "확정 중분류는 정확히 48개여야 합니다.")
        self.assertEqual(uniq, 48, "중분류 ID는 고유해야 합니다.")

        expected_slots = {
            "CAT_MAJ_01": 8, "CAT_MAJ_02": 5, "CAT_MAJ_03": 6, "CAT_MAJ_04": 5,
            "CAT_MAJ_05": 6, "CAT_MAJ_06": 6, "CAT_MAJ_07": 6, "CAT_MAJ_08": 6
        }
        self.cat_cur.execute("SELECT category_maj_id, count(*) FROM mid_categories GROUP BY category_maj_id")
        actual_slots = dict(self.cat_cur.fetchall())
        self.assertEqual(actual_slots, expected_slots, "대분류별 중분류 슬롯 수가 AGENTS.md 규정과 일치해야 합니다.")

    def test_05_semas_subclasses_coverage(self):
        """소진공 38개 소분류 전수 등록 확인"""
        self.cat_cur.execute("SELECT count(*) FROM semas_industry_codes")
        cnt = self.cat_cur.fetchone()[0]
        self.assertEqual(cnt, 38, "소진공 음식업 소분류는 38개여야 합니다.")

    def test_06_brand_category_master_integrity(self):
        """브랜드 카테고리 마스터 5,063건 전수 구축 및 센티넬 확인"""
        self.cat_cur.execute("SELECT count(*) FROM brand_category_master")
        cnt = self.cat_cur.fetchone()[0]
        self.assertEqual(cnt, 5063, "브랜드 카테고리 마스터 수는 5,063건이어야 합니다.")

        # 센티넬 확인
        self.cat_cur.execute("SELECT classification_status FROM brand_category_master WHERE internal_brand_id = 'BRD_UNMATCHED'")
        sentinel_row = self.cat_cur.fetchone()
        self.assertIsNotNone(sentinel_row)
        self.assertEqual(sentinel_row[0], "UNCLASSIFIED")

    def test_07_store_classification_counts_and_uniqueness(self):
        """전국 점포 분류 테이블 고유 점포 수 735,185건 일치 확인 (중복 0건)"""
        self.cat_cur.execute("SELECT count(*), count(distinct bizes_id) FROM store_category_classifications")
        cnt, uniq = self.cat_cur.fetchone()
        self.assertEqual(cnt, 735185, "전국 점포 분류 수가 735,185건이어야 합니다.")
        self.assertEqual(uniq, 735185, "점포 ID 중복이 없어야 합니다.")

    def test_08_store_brand_category_links_and_reconciliation(self):
        """링크 테이블 735,208건 및 숍인숍 23건 대사 공식 일치 확인"""
        self.cat_cur.execute("SELECT count(*) FROM store_brand_category_links")
        link_cnt = self.cat_cur.fetchone()[0]
        self.assertEqual(link_cnt, 735208, "링크 총수가 735,208건이어야 합니다.")

        self.cat_cur.execute("""
            SELECT count(*) FROM (
                SELECT bizes_id FROM store_brand_category_links 
                GROUP BY bizes_id HAVING count(*) > 1
            )
        """)
        multi_cnt = self.cat_cur.fetchone()[0]
        self.assertEqual(multi_cnt, 23, "복수 브랜드 숍인숍 매장은 23건이어야 합니다.")
        self.assertEqual(735185 + multi_cnt, link_cnt, "735,185 + 23 == 735,208 대사 공식이 성립해야 합니다.")

    def test_09_one_to_n_split_resolution(self):
        """1:N 소분류 키워드 분기 해소 테스트"""
        # I21005 (토스트/샌드위치/샐러드)
        maj_1, mid_1, rule_1, _ = resolve_semas_to_mid("I21005", "이삭토스트 역삼점")
        self.assertEqual(mid_1, "CAT_MID_0504", "이삭토스트는 토스트/샌드위치로 분류되어야 합니다.")

        maj_2, mid_2, rule_2, _ = resolve_semas_to_mid("I21005", "샐러디 선릉점")
        self.assertEqual(mid_2, "CAT_MID_0505", "샐러디는 샐러드/포케로 분류되어야 합니다.")

        # I20302 (일식 카레/돈가스/덮밥)
        maj_3, mid_3, rule_3, _ = resolve_semas_to_mid("I20302", "사보텐 돈카츠")
        self.assertEqual(mid_3, "CAT_MID_0301", "사보텐은 돈가스/카레로 분류되어야 합니다.")

        maj_4, mid_4, rule_4, _ = resolve_semas_to_mid("I20302", "홍대개미 덮밥")
        self.assertEqual(mid_4, "CAT_MID_0304", "홍대개미는 덮밥/가정식으로 분류되어야 합니다.")

    def test_10_no_unclassified_stores(self):
        """미분류(UNCLASSIFIED) 결측 점포 0건 검증"""
        self.cat_cur.execute("SELECT count(*) FROM store_category_classifications WHERE classification_status = 'UNCLASSIFIED'")
        unclassified_cnt = self.cat_cur.fetchone()[0]
        self.assertEqual(unclassified_cnt, 0, "미분류 점포가 0건이어야 합니다.")

    def test_11_views_accessibility(self):
        """지도/통계 연계용 SQL 뷰 접근성 및 건수 확인"""
        with sqlite3.connect(CATEGORY_MASTER_DB_PATH) as conn:
            cur = conn.cursor()
            cur.execute("SELECT count(*) FROM v_store_category_master")
            cnt = cur.fetchone()[0]
            self.assertEqual(cnt, 735185, "v_store_category_master 뷰 조회 건수는 735,185건이어야 합니다.")

            cur.execute("SELECT count(*) FROM v_category_store_aggregates")
            agg_cnt = cur.fetchone()[0]
            self.assertEqual(agg_cnt, 48, "v_category_store_aggregates 뷰는 48개 중분류 전체를 반환해야 합니다.")


if __name__ == "__main__":
    unittest.main()
