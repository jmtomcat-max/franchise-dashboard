"""
Stage 4D: 외식업 8대 대분류 및 48대 중분류 종합 무결성 검증 및 감사 모듈
프로젝트: D:/Franchise_Dashboard
위치: src/stage4d/validator.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import sqlite3
import json
import time
from typing import Dict, List, Any, Tuple

CATEGORY_MASTER_DB_PATH = Path("d:/Franchise_Dashboard/data/food_category_master_v1.sqlite3")
BRAND_MASTER_DB_PATH = Path("d:/Franchise_Dashboard/data/brand_master_v1.sqlite3")
NATIONWIDE_V2_DB_PATH = Path("d:/Franchise_Dashboard/data/nationwide_food_stores_v2.sqlite3")
VALIDATION_JSON_PATH = Path("d:/Franchise_Dashboard/reports/phase4_stage4d_validation.json")


def run_full_validation() -> Dict[str, Any]:
    """
    Stage 4D 전체 산출물에 대한 전수 데이터 무결성 검증을 수행하고,
    검증 결과 JSON 페이로드를 생성합니다.
    """
    start_time = time.time()
    checks: List[Dict[str, Any]] = []

    # 1. 원본 운영 DB 불변성 확인
    v2_conn = sqlite3.connect(NATIONWIDE_V2_DB_PATH)
    v2_cur = v2_conn.cursor()
    v2_cur.execute("SELECT count(*) FROM stores")
    v2_store_cnt = v2_cur.fetchone()[0]
    v2_conn.close()

    checks.append({
        "check_id": "CHK_01_RAW_DB_IMMUTABILITY",
        "description": "운영 원본 DB(nationwide_food_stores_v2.sqlite3) 점포수 보존 확인",
        "expected": 735185,
        "actual": v2_store_cnt,
        "status": "PASS" if v2_store_cnt == 735185 else "FAIL"
    })

    # 2. 브랜드 마스터 DB(Stage 4C) 불변성 확인
    bm_conn = sqlite3.connect(BRAND_MASTER_DB_PATH)
    bm_cur = bm_conn.cursor()
    bm_cur.execute("SELECT count(*) FROM brands")
    bm_brand_cnt = bm_cur.fetchone()[0]
    bm_cur.execute("SELECT count(*), count(distinct bizes_id) FROM store_brand_links")
    bm_link_cnt, bm_uniq_stores = bm_cur.fetchone()
    bm_conn.close()

    checks.append({
        "check_id": "CHK_02_BRAND_MASTER_IMMUTABILITY",
        "description": "선행 브랜드 마스터(brand_master_v1.sqlite3) 건수 보존 확인",
        "expected": {"brands": 5063, "links": 735208, "unique_stores": 735185},
        "actual": {"brands": bm_brand_cnt, "links": bm_link_cnt, "unique_stores": bm_uniq_stores},
        "status": "PASS" if (bm_brand_cnt == 5063 and bm_link_cnt == 735208 and bm_uniq_stores == 735185) else "FAIL"
    })

    # 3. 신규 카테고리 마스터 DB 무결성 확인
    cat_conn = sqlite3.connect(CATEGORY_MASTER_DB_PATH)
    cat_cur = cat_conn.cursor()

    # 3.1 8대 대분류 확인
    cat_cur.execute("SELECT count(*), count(distinct category_maj_id) FROM major_categories")
    maj_cnt, maj_uniq = cat_cur.fetchone()
    checks.append({
        "check_id": "CHK_03_MAJOR_CATEGORIES_COUNT",
        "description": "확정 8대 대분류 고유성 및 건수 일치 확인",
        "expected": 8,
        "actual": maj_cnt,
        "status": "PASS" if (maj_cnt == 8 and maj_uniq == 8) else "FAIL"
    })

    # 3.2 48대 중분류 확인
    cat_cur.execute("SELECT count(*), count(distinct category_mid_id) FROM mid_categories")
    mid_cnt, mid_uniq = cat_cur.fetchone()
    checks.append({
        "check_id": "CHK_04_MID_CATEGORIES_COUNT",
        "description": "확정 48대 중분류 고유성 및 건수 일치 확인",
        "expected": 48,
        "actual": mid_cnt,
        "status": "PASS" if (mid_cnt == 48 and mid_uniq == 48) else "FAIL"
    })

    # 3.3 대분류별 중분류 슬롯 정합성 (8, 5, 6, 5, 6, 6, 6, 6)
    expected_slots = {
        "CAT_MAJ_01": 8, "CAT_MAJ_02": 5, "CAT_MAJ_03": 6, "CAT_MAJ_04": 5,
        "CAT_MAJ_05": 6, "CAT_MAJ_06": 6, "CAT_MAJ_07": 6, "CAT_MAJ_08": 6
    }
    cat_cur.execute("SELECT category_maj_id, count(*) FROM mid_categories GROUP BY category_maj_id ORDER BY category_maj_id")
    actual_slots = dict(cat_cur.fetchall())
    slots_match = (actual_slots == expected_slots)

    checks.append({
        "check_id": "CHK_05_SLOT_DISTRIBUTION",
        "description": "8대 대분류별 중분류 슬롯(8/5/6/5/6/6/6/6) 일치 확인",
        "expected": expected_slots,
        "actual": actual_slots,
        "status": "PASS" if slots_match else "FAIL"
    })

    # 3.4 소진공 38개 소분류 커버리지
    cat_cur.execute("SELECT count(*) FROM semas_industry_codes")
    semas_cnt = cat_cur.fetchone()[0]
    checks.append({
        "check_id": "CHK_06_SEMAS_COVERAGE",
        "description": "소진공 I2 음식업 38개 소분류 등록 확인",
        "expected": 38,
        "actual": semas_cnt,
        "status": "PASS" if semas_cnt == 38 else "FAIL"
    })

    # 3.5 브랜드 마스터 대표업종 구축 확인 (5,063건)
    cat_cur.execute("SELECT count(*) FROM brand_category_master")
    b_cat_cnt = cat_cur.fetchone()[0]
    checks.append({
        "check_id": "CHK_07_BRAND_CATEGORY_MASTER",
        "description": "브랜드 마스터 대표업종 5,063건 이관 일치 확인",
        "expected": 5063,
        "actual": b_cat_cnt,
        "status": "PASS" if b_cat_cnt == 5063 else "FAIL"
    })

    # 3.6 전국 점포 분류 정합성 (735,185건 고유)
    cat_cur.execute("SELECT count(*), count(distinct bizes_id) FROM store_category_classifications")
    st_cnt, st_uniq = cat_cur.fetchone()
    checks.append({
        "check_id": "CHK_08_STORE_CLASSIFICATION_TOTAL",
        "description": "전국 점포 분류 테이블 고유 점포 수 735,185건 일치 확인",
        "expected": 735185,
        "actual": st_cnt,
        "status": "PASS" if (st_cnt == 735185 and st_uniq == 735185) else "FAIL"
    })

    # 3.7 점포-브랜드-업종 링크 건수 (735,208건)
    cat_cur.execute("SELECT count(*) FROM store_brand_category_links")
    link_cnt = cat_cur.fetchone()[0]
    checks.append({
        "check_id": "CHK_09_CATEGORY_LINKS_TOTAL",
        "description": "점포-브랜드-업종 N:M 링크 735,208건 일치 확인",
        "expected": 735208,
        "actual": link_cnt,
        "status": "PASS" if link_cnt == 735208 else "FAIL"
    })

    # 3.8 23개 복수 브랜드 숍인숍 점포 대사 공식
    cat_cur.execute("""
        SELECT count(*) FROM (
            SELECT bizes_id FROM store_brand_category_links 
            GROUP BY bizes_id HAVING count(*) > 1
        )
    """)
    multi_brand_cnt = cat_cur.fetchone()[0]
    reconciliation_valid = (st_cnt + multi_brand_cnt == link_cnt)

    checks.append({
        "check_id": "CHK_10_MULTI_BRAND_RECONCILIATION",
        "description": "다중 브랜드 숍인숍(23건) 대사 공식 (고유점포 + 복수링크 = 총링크) 검증",
        "expected": {"multi_brand_stores": 23, "formula": "735185 + 23 = 735208"},
        "actual": {"multi_brand_stores": multi_brand_cnt, "reconciliation_passed": reconciliation_valid},
        "status": "PASS" if (multi_brand_cnt == 23 and reconciliation_valid) else "FAIL"
    })

    # 3.9 미분류(UNCLASSIFIED) 점포 수 확인 (0건이어야 함)
    cat_cur.execute("SELECT count(*) FROM store_category_classifications WHERE classification_status = 'UNCLASSIFIED'")
    unclassified_cnt = cat_cur.fetchone()[0]
    checks.append({
        "check_id": "CHK_11_UNCLASSIFIED_STORES",
        "description": "미분류(UNCLASSIFIED) 결측 점포 0건 검증",
        "expected": 0,
        "actual": unclassified_cnt,
        "status": "PASS" if unclassified_cnt == 0 else "FAIL"
    })

    # 3.10 대분류별 점포 분포 요약 집계
    cat_cur.execute("""
        SELECT category_major_id, category_major_name, count(*) 
        FROM store_category_classifications 
        GROUP BY category_major_id, category_major_name
        ORDER BY count(*) DESC
    """)
    major_dist = [
        {"maj_id": r[0], "maj_name": r[1], "store_count": r[2], "share_pct": round(r[2] / 735185 * 100, 2)}
        for r in cat_cur.fetchall()
    ]

    # 3.11 분류 검증 상태 분포
    cat_cur.execute("""
        SELECT classification_status, count(*) 
        FROM store_category_classifications 
        GROUP BY classification_status
    """)
    status_dist = {r[0]: r[1] for r in cat_cur.fetchall()}

    # 3.12 카테고리 불일치(Divergence) 점포 수
    cat_cur.execute("SELECT count(*) FROM store_category_classifications WHERE is_category_divergent = 1")
    divergent_cnt = cat_cur.fetchone()[0]

    cat_conn.close()

    overall_status = "PASS" if all(c["status"] == "PASS" for c in checks) else "FAIL"
    elapsed = time.time() - start_time

    validation_payload = {
        "stage": "Phase 4 Stage 4D",
        "audit_timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "overall_status": overall_status,
        "execution_time_seconds": round(elapsed, 2),
        "check_summary": {
            "total_checks": len(checks),
            "passed": sum(1 for c in checks if c["status"] == "PASS"),
            "failed": sum(1 for c in checks if c["status"] == "FAIL"),
        },
        "checks": checks,
        "nationwide_category_distribution": major_dist,
        "classification_status_distribution": status_dist,
        "category_divergence_metrics": {
            "divergent_store_count": divergent_cnt,
            "divergence_pct": round(divergent_cnt / 735185 * 100, 2)
        }
    }

    # 파일 저장
    VALIDATION_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(VALIDATION_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(validation_payload, f, ensure_ascii=False, indent=2)

    print("=" * 70)
    print(f"Stage 4D Comprehensive Validation Result: [{overall_status}]")
    print(f"  - Checks Passed: {validation_payload['check_summary']['passed']}/{len(checks)}")
    print(f"  - Validation JSON saved: {VALIDATION_JSON_PATH}")
    print("=" * 70)

    return validation_payload


if __name__ == "__main__":
    run_full_validation()
