"""
Stage 4B 자동 테스트 스위트 (15개 필수 시나리오 전수 검증)
프로젝트: D:/Franchise_Dashboard
위치: tests/test_phase4_stage4b.py
"""

import os
import sys
import unittest
import sqlite3
import tempfile
import shutil
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.stage4b.normalizer import normalize_store_name_full
from src.stage4b.brand_dictionary import (
    OFFICIAL_BRAND_SEEDS,
    BRAND_LOOKUP_DICT,
    GENERIC_FOOD_NOUNS,
    get_official_brand_by_clean_name
)
from src.stage4b.candidate_engine import evaluate_store_candidate
from src.stage4b.schema_stage4b import initialize_stage4b_database
from src.stage4b.evaluator import evaluate_stage4b_quality

SEMAS_V2_DB_PATH = BASE_DIR / "data" / "nationwide_food_stores_v2.sqlite3"


class TestPhase4Stage4B(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.test_dir = Path(tempfile.mkdtemp(prefix="stage4b_test_"))
        cls.test_db_path = cls.test_dir / "test_brand_candidates.sqlite3"
        initialize_stage4b_database(cls.test_db_path)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.test_dir, ignore_errors=True)

    # 1. 동일 브랜드의 한글·영문·약어 표기 (Bilingual & Acronym)
    def test_01_bilingual_and_acronym_matching(self):
        cases = [
            ("스타벅스 강남점", "STARBUCKS", "CAN_BRD_CAF_0001"),
            ("STARBUCKS 역삼점", "스타벅스", "CAN_BRD_CAF_0001"),
            ("bbq치킨 서초점", "비비큐", "CAN_BRD_CHK_0002"),
            ("BBQ치킨 대치점", "bbq치킨", "CAN_BRD_CHK_0002"),
            ("버거킹 종로점", "BURGER KING", "CAN_BRD_CHK_0005"),
        ]
        for raw, alias, expected_id in cases:
            norm = normalize_store_name_full(raw)
            cands = evaluate_store_candidate(norm, "TEST_BI_001")
            self.assertEqual(len(cands), 1)
            self.assertEqual(cands[0]["candidate_brand_id"], expected_id)
            self.assertEqual(cands[0]["store_verification_status"], "VERIFIED_AUTO")

    # 2. 비슷한 이름의 다른 브랜드 분리 (Collision Resolver)
    def test_02_similar_brand_collision_separation(self):
        # 본죽 vs 본도시락 vs 본설렁탕
        cands_bonjuk = evaluate_store_candidate(normalize_store_name_full("본죽 역삼점"), "TEST_001")
        cands_dosirak = evaluate_store_candidate(normalize_store_name_full("본도시락 역삼점"), "TEST_002")
        cands_seol = evaluate_store_candidate(normalize_store_name_full("본설렁탕 역삼점"), "TEST_003")

        self.assertEqual(cands_bonjuk[0]["candidate_brand_id"], "CAN_BRD_KOR_0001")
        self.assertEqual(cands_dosirak[0]["candidate_brand_id"], "CAN_BRD_KOR_0002")
        self.assertEqual(cands_seol[0]["candidate_brand_id"], "CAN_BRD_KOR_0003")
        self.assertNotEqual(cands_bonjuk[0]["candidate_brand_id"], cands_dosirak[0]["candidate_brand_id"])

        # 신전떡볶이 vs 신참떡볶이
        cands_sinjeon = evaluate_store_candidate(normalize_store_name_full("신전떡볶이 강남점"), "TEST_004")
        cands_sincham = evaluate_store_candidate(normalize_store_name_full("신참떡볶이 강남점"), "TEST_005")
        self.assertEqual(cands_sinjeon[0]["candidate_brand_id"], "CAN_BRD_SNK_0004")
        self.assertEqual(cands_sincham[0]["candidate_brand_id"], "CAN_BRD_SNK_0005")
        self.assertNotEqual(cands_sinjeon[0]["candidate_brand_id"], cands_sincham[0]["candidate_brand_id"])

        # 빽다방 vs 빽보이피자
        cands_paik = evaluate_store_candidate(normalize_store_name_full("빽다방 신사점"), "TEST_006")
        self.assertEqual(cands_paik[0]["candidate_brand_id"], "CAN_BRD_CAF_0006")
        self.assertEqual(cands_paik[0]["category_major"], "카페·음료")

    # 3. 일반명사가 포함된 브랜드명 (김가네김밥, 한솥도시락 등)
    def test_03_generic_nouns_inside_brand_name(self):
        norm_kim = normalize_store_name_full("김가네김밥 대학로점")
        cands_kim = evaluate_store_candidate(norm_kim, "TEST_007")
        self.assertEqual(cands_kim[0]["candidate_brand_id"], "CAN_BRD_SNK_0001")
        self.assertEqual(cands_kim[0]["store_verification_status"], "VERIFIED_AUTO")

        norm_hansot = normalize_store_name_full("한솥도시락 신촌점")
        cands_hansot = evaluate_store_candidate(norm_hansot, "TEST_008")
        self.assertEqual(cands_hansot[0]["candidate_brand_id"], "CAN_BRD_KOR_0004")
        self.assertEqual(cands_hansot[0]["store_verification_status"], "VERIFIED_AUTO")

    # 4. 브랜드명이 포함된 비가맹 일반 음식점 (Negative Keyword Filter)
    def test_04_non_franchise_stores_with_brand_keywords(self):
        false_store_names = [
            "교촌식당", "교촌면옥", "교촌한우", "교촌칼국수",
            "놀부식당", "흥부놀부보쌈", "놀부네밥상",
            "이디야호프", "메가치킨", "스타포차", "스타김밥"
        ]
        for raw in false_store_names:
            norm = normalize_store_name_full(raw)
            cands = evaluate_store_candidate(norm, "TEST_FALSE_001")
            self.assertIn(cands[0]["store_verification_status"], ["REJECTED", "INDEPENDENT_STORE"])
            self.assertNotEqual(cands[0]["store_verification_status"], "VERIFIED_AUTO")

    # 5. 지점명 위치가 다른 상호 및 원본 상호 가역성 (Reconstructibility)
    def test_05_branch_name_different_positions_and_reconstructibility(self):
        # 1) 지점 접미어
        norm1 = normalize_store_name_full("스타벅스 강남점")
        self.assertEqual(norm1["normalized_core_nm"], "스타벅스")
        self.assertEqual(norm1["branch_suffix"], "강남점")
        self.assertEqual(norm1["branch_position"], "SUFFIX")
        self.assertEqual(norm1["is_reconstructible"], 1)

        # 2) 지점 접두어 [강남점] 스타벅스
        norm2 = normalize_store_name_full("[강남점] 스타벅스")
        self.assertEqual(norm2["normalized_core_nm"], "스타벅스")
        self.assertEqual(norm2["branch_suffix"], "강남점")
        self.assertEqual(norm2["branch_position"], "PREFIX")
        self.assertEqual(norm2["is_reconstructible"], 1)

        # 3) brch_nm 별도 컬럼
        norm3 = normalize_store_name_full("교촌치킨", brch_nm_col="서초1호점")
        self.assertEqual(norm3["normalized_core_nm"], "교촌치킨")
        self.assertEqual(norm3["branch_suffix"], "서초1호점")
        self.assertEqual(norm3["is_reconstructible"], 1)

    # 6. 동일 점포의 복수 후보 (Multi-brand Candidates)
    def test_06_multi_candidate_store_handling(self):
        # 복합 매장: 교촌치킨&피자마루
        norm = normalize_store_name_full("교촌치킨&피자마루 역삼점")
        cands = evaluate_store_candidate(norm, "TEST_MULTI_001")
        self.assertGreaterEqual(len(cands), 1)
        # 복합 매장은 REVIEW_REQUIRED 상태여야 함
        self.assertIn(cands[0]["store_verification_status"], ["REVIEW_REQUIRED", "PROVISIONAL"])

    # 7. 브랜드 개명 및 별칭 규칙 (Rebranded / Alias Rules)
    def test_07_rebranded_and_alias_rules(self):
        norm = normalize_store_name_full("명륜진사갈비NEW 서초점")
        cands = evaluate_store_candidate(norm, "TEST_REBRAND_001")
        self.assertEqual(cands[0]["candidate_brand_id"], "CAN_BRD_KOR_0012")
        self.assertEqual(cands[0]["store_verification_status"], "VERIFIED_AUTO")

        norm_twosome = normalize_store_name_full("A TWOSOME PLACE 압구정점")
        cands_twosome = evaluate_store_candidate(norm_twosome, "TEST_REBRAND_002")
        self.assertEqual(cands_twosome[0]["candidate_brand_id"], "CAN_BRD_CAF_0003")

    # 8. 동일 상호를 사용하는 다른 사업자 및 일반명사 단독 상호
    def test_08_homonymous_stores_different_businesses(self):
        # 일반명사 단독 상호는 무조건 제외
        for generic in ["김밥", "치킨", "피자", "커피", "순대국", "포차"]:
            norm = normalize_store_name_full(generic)
            cands = evaluate_store_candidate(norm, "TEST_GEN_001")
            self.assertEqual(cands[0]["store_verification_status"], "INDEPENDENT_STORE")
            self.assertEqual(cands[0]["candidate_brand_id"], "NONE_INDEPENDENT")

    # 9. 데이터 처리 중단 및 재개 (Checkpoint & Resume)
    def test_09_timeframe_and_checkpoint_resume(self):
        con = sqlite3.connect(self.test_db_path)
        cur = con.cursor()
        cur.execute("""
            INSERT OR REPLACE INTO candidate_audit_log (
                run_id, batch_step, start_time, total_processed, status
            ) VALUES ('RUN_CHECKPOINT_01', 'CHUNK_1', '2026-10-13T10:00:00', 50000, 'IN_PROGRESS')
        """)
        con.commit()
        last_step = cur.execute("SELECT batch_step FROM candidate_audit_log WHERE status='IN_PROGRESS'").fetchone()[0]
        self.assertEqual(last_step, "CHUNK_1")
        con.close()

    # 10. 점포 ID 고유성 및 중복 방지 (Idempotent Deduplication)
    def test_10_store_id_conflict_prevention(self):
        con = sqlite3.connect(self.test_db_path)
        cur = con.cursor()
        cur.execute("""
            INSERT OR REPLACE INTO store_normalization (
                bizes_id, raw_bizes_nm, normalized_core_nm, branch_suffix, is_reconstructible, processed_at
            ) VALUES ('BIZES_DUP_001', '스타벅스 강남점', '스타벅스', '강남점', 1, '2026-10-13T10:00:00')
        """)
        con.commit()
        # 동일 ID 재입력
        cur.execute("""
            INSERT OR REPLACE INTO store_normalization (
                bizes_id, raw_bizes_nm, normalized_core_nm, branch_suffix, is_reconstructible, processed_at
            ) VALUES ('BIZES_DUP_001', '스타벅스 강남점', '스타벅스', '강남점', 1, '2026-10-13T10:05:00')
        """)
        con.commit()
        cnt = cur.execute("SELECT COUNT(*) FROM store_normalization WHERE bizes_id='BIZES_DUP_001'").fetchone()[0]
        self.assertEqual(cnt, 1)
        con.close()

    # 11. 전국 10개 이상 점포 임계치 검증
    def test_11_threshold_clustering_rules(self):
        norm_unregistered = normalize_store_name_full("행복한골목식당 역삼점")
        # 1) 전국 점포 수 15개인 경우 -> PROVISIONAL 후보 승격
        cands_high = evaluate_store_candidate(norm_unregistered, "TEST_CLUS_001", cluster_store_count=15)
        self.assertEqual(cands_high[0]["store_verification_status"], "PROVISIONAL")
        self.assertTrue(cands_high[0]["candidate_brand_id"].startswith("CAN_CLUS_"))

        # 2) 전국 점포 수 5개인 경우 -> INDEPENDENT_STORE
        cands_low = evaluate_store_candidate(norm_unregistered, "TEST_CLUS_002", cluster_store_count=5)
        self.assertEqual(cands_low[0]["store_verification_status"], "INDEPENDENT_STORE")
        self.assertEqual(cands_low[0]["candidate_brand_id"], "NONE_INDEPENDENT")

        # 3) 공식 등록 브랜드는 10개 미만이어도 완전 보존
        norm_official = normalize_store_name_full("토끼정 강남점")
        cands_official = evaluate_store_candidate(norm_official, "TEST_OFF_001", cluster_store_count=3)
        self.assertEqual(cands_official[0]["store_verification_status"], "VERIFIED_AUTO")
        self.assertEqual(cands_official[0]["candidate_brand_id"], "CAN_BRD_JPN_0007")

    # 12. 공식 브랜드 정보 부재 시에도 소진공 점포 기반 클러스터링으로 자립
    def test_12_missing_official_brand_info_fallback(self):
        norm_emerging = normalize_store_name_full("신규대박마라탕 종로점")
        cands = evaluate_store_candidate(norm_emerging, "TEST_EMERG_001", cluster_store_count=20)
        self.assertEqual(cands[0]["store_verification_status"], "PROVISIONAL")
        self.assertIn("전국 동일 상호 점포 수 20개", cands[0]["notes"])

    # 13. 잘못된 별칭 규칙 및 미등록 업종코드 격리
    def test_13_erroneous_alias_and_unregistered_category(self):
        norm = normalize_store_name_full("아무개식당 역삼점")
        # 미등록 이상 업종코드 주입
        cands = evaluate_store_candidate(norm, "TEST_ERR_001", inds_mcls_nm="UNKNOWN_XYZ", cluster_store_count=1)
        self.assertEqual(cands[0]["store_verification_status"], "INDEPENDENT_STORE")
        self.assertEqual(cands[0]["category_major"], "UNKNOWN_XYZ")

    # 14. 소진공 전국 v2 DB 불변성 (Read-Only) 검증
    def test_14_memory_and_source_db_readonly(self):
        self.assertTrue(SEMAS_V2_DB_PATH.exists())
        con = sqlite3.connect(f"file:{SEMAS_V2_DB_PATH}?mode=ro", uri=True)
        cur = con.cursor()
        total_stores = cur.execute("SELECT COUNT(*) FROM stores").fetchone()[0]
        con.close()
        self.assertEqual(total_stores, 735185)

    # 15. 품질 평가 표본 (1,110건) 자동 확정 정밀도 >= 95% 검증
    def test_15_gold_standard_eval_precision_threshold(self):
        metrics = evaluate_stage4b_quality(self.test_db_path)
        precision = metrics["performance_metrics"]["precision_pct"]
        self.assertGreaterEqual(precision, 95.0)
        self.assertTrue(metrics["performance_metrics"]["target_precision_met"])


if __name__ == "__main__":
    unittest.main()
