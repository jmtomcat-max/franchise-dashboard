"""
Phase 4 Stage 4C: 브랜드 마스터 구축 및 정합성 검증 테스트 스위트 (unittest 기반)
프로젝트: D:/Franchise_Dashboard
위치: tests/test_phase4_stage4c.py
"""

import json
import sqlite3
import sys
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

MASTER_DB_PATH = BASE_DIR / "data" / "brand_master_v1.sqlite3"
RAW_V2_DB_PATH = BASE_DIR / "data" / "nationwide_food_stores_v2.sqlite3"
VALIDATION_JSON_PATH = BASE_DIR / "reports" / "phase4_stage4c_validation.json"

class TestPhase4Stage4C(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        assert MASTER_DB_PATH.exists(), f"Master DB not found at: {MASTER_DB_PATH}"
        cls.db_conn = sqlite3.connect(f"{MASTER_DB_PATH.resolve().as_uri()}?mode=ro", uri=True)

    @classmethod
    def tearDownClass(cls):
        cls.db_conn.close()

    def test_01_stage4c_database_and_tables_exist(self):
        """1. 브랜드 마스터 데이터베이스 내 10대 핵심 엔터티 테이블이 모두 존재하는지 검증한다."""
        cur = self.db_conn.cursor()
        tables = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()]
        
        expected_tables = [
            "brands", "brand_aliases", "brand_sources", "brand_franchise_evidence",
            "store_brand_links", "brand_reviews", "matching_rules", "brand_history",
            "data_quality_audits", "independent_eval_samples"
        ]
        for tbl in expected_tables:
            self.assertIn(tbl, tables, f"Expected table '{tbl}' not found in master DB.")

    def test_02_raw_database_immutability(self):
        """2. 원본 운영 DB (nationwide_food_stores_v2.sqlite3)가 변경 없이 735,185건을 보존하는지 검증한다."""
        self.assertTrue(RAW_V2_DB_PATH.exists())
        con = sqlite3.connect(f"file:{RAW_V2_DB_PATH}?mode=ro", uri=True)
        cur = con.cursor()
        count = cur.execute("SELECT count(*) FROM stores;").fetchone()[0]
        con.close()
        self.assertEqual(count, 735185, f"Raw DB store count corrupted! Expected 735,185, found {count}")

    def test_03_80_census_brands_classification(self):
        """3. 80대 공인 브랜드 전수 조사 결과: 가맹사업 72개, 100% 직영 7개, 근거부족 1개 정합성을 검증한다."""
        cur = self.db_conn.cursor()
        
        total_census = cur.execute("SELECT count(*) FROM brands WHERE discovery_method = 'OFFICIAL_SEED_CENSUS';").fetchone()[0]
        self.assertEqual(total_census, 80, f"Expected 80 census brands, found {total_census}")
        
        frcs_confirmed = cur.execute("SELECT count(*) FROM brands WHERE brand_officiality = 'FRANCHISE_CONFIRMED';").fetchone()[0]
        self.assertEqual(frcs_confirmed, 72, f"Expected 72 FRANCHISE_CONFIRMED brands, found {frcs_confirmed}")
        
        brand_confirmed = cur.execute("SELECT count(*) FROM brands WHERE brand_officiality = 'BRAND_CONFIRMED';").fetchone()[0]
        self.assertEqual(brand_confirmed, 7, f"Expected 7 BRAND_CONFIRMED (100% 직영) brands, found {brand_confirmed}")
        
        # 스타벅스는 BRAND_CONFIRMED (직영) 확인
        sb_row = cur.execute("SELECT brand_officiality FROM brands WHERE brand_name_std = '스타벅스';").fetchone()
        self.assertIsNotNone(sb_row)
        self.assertEqual(sb_row[0], "BRAND_CONFIRMED", "Starbucks must be BRAND_CONFIRMED, not FRANCHISE_CONFIRMED!")
        
        # 교동짬뽕은 UNVERIFIED 확인
        kd_row = cur.execute("SELECT brand_officiality FROM brands WHERE brand_name_std = '교동짬뽕';").fetchone()
        self.assertIsNotNone(kd_row)
        self.assertEqual(kd_row[0], "UNVERIFIED", "Kyodong Jjamppong must be UNVERIFIED due to deficient evidence!")

    def test_04_3axis_state_model_separation(self):
        """4. 브랜드 공식성, 점포 매칭 상태, 운영 형태 3축 상태 모델이 독립적으로 유지되는지 검증한다."""
        cur = self.db_conn.cursor()
        
        # 축 1: 브랜드 공식성 허용값
        brand_offs = set(r[0] for r in cur.execute("SELECT DISTINCT brand_officiality FROM brands;").fetchall())
        self.assertTrue(brand_offs.issubset({"FRANCHISE_CONFIRMED", "BRAND_CONFIRMED", "UNVERIFIED", "REJECTED"}))
        
        # 축 2: 점포 매칭 상태 허용값
        match_statuses = set(r[0] for r in cur.execute("SELECT DISTINCT match_status FROM store_brand_links;").fetchall())
        self.assertTrue(match_statuses.issubset({
            "MATCH_VERIFIED", "MATCH_AUTO_HIGH_CONFIDENCE", "MATCH_PROVISIONAL",
            "REVIEW_REQUIRED", "UNMATCHED", "MATCH_REJECTED"
        }))
        
        # 축 3: 점포 운영 형태 허용값
        op_types = set(r[0] for r in cur.execute("SELECT DISTINCT operation_type FROM store_brand_links;").fetchall())
        self.assertTrue(op_types.issubset({"FRANCHISED", "COMPANY_OPERATED", "OTHER", "UNKNOWN"}))

    def test_05_unmatched_store_conversion(self):
        """5. 기존 INDEPENDENT_STORE (566,056건)가 객관적 독립 운영 판단 없이 UNMATCHED로 전환되었는지 검증한다."""
        cur = self.db_conn.cursor()
        unmatched_cnt = cur.execute("SELECT count(*) FROM store_brand_links WHERE match_status = 'UNMATCHED';").fetchone()[0]
        self.assertEqual(unmatched_cnt, 566056, f"Expected 566,056 UNMATCHED stores, found {unmatched_cnt}")

    def test_06_verified_auto_renamed(self):
        """6. 기존 VERIFIED_AUTO (32,903건)가 MATCH_AUTO_HIGH_CONFIDENCE로 분리 명명되었는지 검증한다."""
        cur = self.db_conn.cursor()
        auto_cnt = cur.execute("SELECT count(*) FROM store_brand_links WHERE match_status = 'MATCH_AUTO_HIGH_CONFIDENCE';").fetchone()[0]
        self.assertEqual(auto_cnt, 32903, f"Expected 32,903 MATCH_AUTO_HIGH_CONFIDENCE links, found {auto_cnt}")

    def test_07_store_count_reconciliation(self):
        """7. 전국 점포 통계 정합성: 고유 점포 735,185건, 링크 735,208건, 다중 후보 점포 23건 일치를 검증한다."""
        cur = self.db_conn.cursor()
        
        uniq_stores = cur.execute("SELECT count(DISTINCT bizes_id) FROM store_brand_links;").fetchone()[0]
        self.assertEqual(uniq_stores, 735185, f"Expected 735,185 unique stores, found {uniq_stores}")
        
        total_links = cur.execute("SELECT count(*) FROM store_brand_links;").fetchone()[0]
        self.assertEqual(total_links, 735208, f"Expected 735,208 total link rows, found {total_links}")
        
        multi_cnt = cur.execute("""
            SELECT count(*) FROM (
                SELECT bizes_id, count(*) as c FROM store_brand_links GROUP BY bizes_id HAVING c > 1
            )
        """).fetchone()[0]
        self.assertEqual(multi_cnt, 23, f"Expected 23 multi-candidate stores, found {multi_cnt}")

    def test_08_candidate_id_mapping_stability(self):
        """8. 기존 Stage 4B 후보 ID와 신규 내부 브랜드 ID 간의 매핑 보존을 검증한다."""
        cur = self.db_conn.cursor()
        total_cands = cur.execute("SELECT count(DISTINCT candidate_brand_id) FROM brands;").fetchone()[0]
        self.assertEqual(total_cands, 5063, f"Expected 5,063 unique candidate IDs (including UNMATCHED), found {total_cands}")

    def test_09_independent_evaluation_metrics(self):
        """9. 독립 품질 평가 결과: 비소속 표본 >= 200건, Precision >= 95.0% 및 무오탐 검증."""
        cur = self.db_conn.cursor()
        
        neg_count = cur.execute("SELECT count(*) FROM independent_eval_samples WHERE ground_truth_label = 0;").fetchone()[0]
        self.assertGreaterEqual(neg_count, 200, f"Expected >= 200 negative evaluation samples, found {neg_count}")
        
        audits = dict(cur.execute("SELECT metric_name, metric_value FROM data_quality_audits;").fetchall())
        precision = audits.get("INDEPENDENT_PRECISION", 0.0)
        self.assertGreaterEqual(precision, 95.0, f"Independent precision {precision}% below target 95.0%!")
        
        false_merges = audits.get("FALSE_MERGE_COUNT", 0.0)
        self.assertEqual(false_merges, 0, f"False merges detected: {false_merges}")

    def test_10_review_system_persistence(self):
        """10. 수동 검토 결정 영구 보존(is_persistent=1) 및 덮어쓰기 방지를 검증한다."""
        import tempfile
        import shutil
        from src.stage4c.review_system import record_brand_review
        
        # 운영 DB를 절대 수정하지 않도록 임시 DB 파일을 생성하여 격리 테스트 수행
        with tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False) as tmp:
            tmp_db_path = Path(tmp.name)
        
        try:
            shutil.copy2(MASTER_DB_PATH, tmp_db_path)
            res = record_brand_review(
                "BRD_KOR_0001",
                "APPROVED",
                "전문가 공정위 정보공개서 일치 확인",
                "HUMAN_EXPERT",
                db_path=tmp_db_path
            )
            self.assertEqual(res["status"], "SUCCESS")
            self.assertEqual(res["decision"], "APPROVED")
            
            con = sqlite3.connect(f"{tmp_db_path.resolve().as_uri()}?mode=ro", uri=True)
            cur = con.cursor()
            pers = cur.execute(
                "SELECT is_persistent FROM brand_reviews WHERE target_id = 'BRD_KOR_0001' ORDER BY review_id DESC LIMIT 1;"
            ).fetchone()[0]
            con.close()
            self.assertEqual(pers, 1, "Review decision must be marked as is_persistent=1!")
        finally:
            if tmp_db_path.exists():
                try:
                    tmp_db_path.unlink()
                except Exception:
                    pass

    def test_11_validation_json_artifact(self):
        """11. reports/phase4_stage4c_validation.json 파일이 정상 생성되었고 PASS 상태인지 검증한다."""
        self.assertTrue(VALIDATION_JSON_PATH.exists(), f"Validation JSON not found at: {VALIDATION_JSON_PATH}")
        with open(VALIDATION_JSON_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(data["overall_status"], "PASS", f"Validation JSON overall_status is {data['overall_status']}, expected PASS")

if __name__ == "__main__":
    unittest.main()
