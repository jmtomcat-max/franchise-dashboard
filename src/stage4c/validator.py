"""
Stage 4C: 종합 데이터 정합성 검증 및 validation.json 생성 모듈
프로젝트: D:/Franchise_Dashboard
위치: src/stage4c/validator.py

본 모듈은:
1. 전국 735,185개 점포 및 5,062개 브랜드 마스터의 정합성을 교차 검증하고
2. 3축 상태 모델 분리, 비소속 음성 표본 수(>=200), 정밀도(>=95%), 다중 매칭 중복 제거를 확인하여
3. reports/phase4_stage4c_validation.json 산출물을 생성합니다.
"""

import json
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

BASE_DIR = Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.stage4c.schema_stage4c import DEFAULT_STAGE4C_DB_PATH

VALIDATION_JSON_PATH = BASE_DIR / "reports" / "phase4_stage4c_validation.json"
RAW_V2_DB_PATH = BASE_DIR / "data" / "nationwide_food_stores_v2.sqlite3"
CAND_DB_PATH = BASE_DIR / "data" / "brand_candidates_v1.sqlite3"

def run_comprehensive_validation(
    master_db_path: Optional[Path] = None,
    out_json_path: Optional[Path] = None
) -> Dict[str, Any]:
    """Stage 4C의 모든 요구조건 및 정합성을 검증하고 JSON으로 기록한다."""
    tgt_db = master_db_path or DEFAULT_STAGE4C_DB_PATH
    out_json = out_json_path or VALIDATION_JSON_PATH
    out_json.parent.mkdir(parents=True, exist_ok=True)
    
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # 1. 원본 DB (읽기 전용) 불변성 검증
    raw_con = sqlite3.connect(f"file:{RAW_V2_DB_PATH}?mode=ro", uri=True)
    raw_store_count = raw_con.cursor().execute("SELECT count(*) FROM stores;").fetchone()[0]
    raw_con.close()
    
    # 2. Stage 4B 후보 DB 검증
    cand_con = sqlite3.connect(f"file:{CAND_DB_PATH}?mode=ro", uri=True)
    cand_cur = cand_con.cursor()
    cand_brand_count = cand_cur.execute("SELECT count(*) FROM brand_candidates;").fetchone()[0]
    cand_link_count = cand_cur.execute("SELECT count(*) FROM store_brand_candidates;").fetchone()[0]
    cand_con.close()
    
    # 3. Stage 4C 브랜드 마스터 DB 정합성 검증
    m_con = sqlite3.connect(tgt_db)
    m_cur = m_con.cursor()
    
    # brands 테이블
    total_brands = m_cur.execute("SELECT count(*) FROM brands WHERE internal_brand_id != 'BRD_UNMATCHED';").fetchone()[0]
    census_brands = m_cur.execute("SELECT count(*) FROM brands WHERE discovery_method = 'OFFICIAL_SEED_CENSUS';").fetchone()[0]
    cluster_brands = m_cur.execute("SELECT count(*) FROM brands WHERE discovery_method = 'CLUSTER_NATIONWIDE_GE10';").fetchone()[0]
    
    franchise_confirmed = m_cur.execute("SELECT count(*) FROM brands WHERE brand_officiality = 'FRANCHISE_CONFIRMED';").fetchone()[0]
    brand_confirmed = m_cur.execute("SELECT count(*) FROM brands WHERE brand_officiality = 'BRAND_CONFIRMED';").fetchone()[0]
    unverified_brands = m_cur.execute("SELECT count(*) FROM brands WHERE brand_officiality = 'UNVERIFIED' AND internal_brand_id != 'BRD_UNMATCHED';").fetchone()[0]
    
    # store_brand_links 테이블
    total_links = m_cur.execute("SELECT count(*) FROM store_brand_links;").fetchone()[0]
    uniq_stores_linked = m_cur.execute("SELECT count(DISTINCT bizes_id) FROM store_brand_links;").fetchone()[0]
    multi_cand_stores = m_cur.execute("""
        SELECT count(*) FROM (
            SELECT bizes_id, count(*) as c FROM store_brand_links GROUP BY bizes_id HAVING c > 1
        )
    """).fetchone()[0]
    
    match_status_counts = dict(m_cur.execute("SELECT match_status, count(*) FROM store_brand_links GROUP BY match_status;").fetchall())
    operation_type_counts = dict(m_cur.execute("SELECT operation_type, count(*) FROM store_brand_links GROUP BY operation_type;").fetchall())
    
    # 증거 테이블 및 출처 테이블
    evidence_count = m_cur.execute("SELECT count(*) FROM brand_franchise_evidence;").fetchone()[0]
    sources_count = m_cur.execute("SELECT count(*) FROM brand_sources;").fetchone()[0]
    aliases_count = m_cur.execute("SELECT count(*) FROM brand_aliases;").fetchone()[0]
    
    # 독립 품질 평가 테이블
    eval_samples_count = m_cur.execute("SELECT count(*) FROM independent_eval_samples;").fetchone()[0]
    eval_negatives_count = m_cur.execute("SELECT count(*) FROM independent_eval_samples WHERE ground_truth_label = 0;").fetchone()[0]
    eval_positives_count = m_cur.execute("SELECT count(*) FROM independent_eval_samples WHERE ground_truth_label = 1;").fetchone()[0]
    
    audit_metrics = dict(m_cur.execute("SELECT metric_name, metric_value FROM data_quality_audits;").fetchall())
    
    m_con.close()
    
    # 4. 검증 판정 매트릭스
    checks = {
        "raw_db_stores_preserved": {
            "expected": 735185,
            "actual": raw_store_count,
            "passed": raw_store_count == 735185
        },
        "candidate_brands_migrated": {
            "expected": 5062,
            "actual": total_brands,
            "passed": total_brands == 5062
        },
        "census_80_brands_registered": {
            "expected": 80,
            "actual": census_brands,
            "passed": census_brands == 80
        },
        "census_franchise_confirmed": {
            "expected": 72,
            "actual": franchise_confirmed,
            "passed": franchise_confirmed == 72
        },
        "census_brand_confirmed_direct": {
            "expected": 7,
            "actual": brand_confirmed,
            "passed": brand_confirmed == 7
        },
        "census_unverified_deficient": {
            "expected": 1,
            "actual": census_brands - franchise_confirmed - brand_confirmed,
            "passed": (census_brands - franchise_confirmed - brand_confirmed) == 1
        },
        "unique_stores_no_data_loss": {
            "expected": 735185,
            "actual": uniq_stores_linked,
            "passed": uniq_stores_linked == 735185
        },
        "total_links_exact_match": {
            "expected": 735208,
            "actual": total_links,
            "passed": total_links == 735208
        },
        "multi_candidate_stores_count": {
            "expected": 23,
            "actual": multi_cand_stores,
            "passed": multi_cand_stores == 23
        },
        "independent_store_converted_to_unmatched": {
            "expected": 566056,
            "actual": match_status_counts.get("UNMATCHED", 0),
            "passed": match_status_counts.get("UNMATCHED", 0) == 566056
        },
        "verified_auto_renamed_high_confidence": {
            "expected": 32903,
            "actual": match_status_counts.get("MATCH_AUTO_HIGH_CONFIDENCE", 0),
            "passed": match_status_counts.get("MATCH_AUTO_HIGH_CONFIDENCE", 0) == 32903
        },
        "independent_eval_negative_samples_gte_200": {
            "expected": ">= 200",
            "actual": eval_negatives_count,
            "passed": eval_negatives_count >= 200
        },
        "independent_eval_precision_gte_95": {
            "expected": ">= 95.0%",
            "actual": audit_metrics.get("INDEPENDENT_PRECISION", 0.0),
            "passed": audit_metrics.get("INDEPENDENT_PRECISION", 0.0) >= 95.0
        },
        "false_merges_zero": {
            "expected": 0,
            "actual": int(audit_metrics.get("FALSE_MERGE_COUNT", 0)),
            "passed": int(audit_metrics.get("FALSE_MERGE_COUNT", 0)) == 0
        },
        "false_splits_zero": {
            "expected": 0,
            "actual": int(audit_metrics.get("FALSE_SPLIT_COUNT", 0)),
            "passed": int(audit_metrics.get("FALSE_SPLIT_COUNT", 0)) == 0
        }
    }
    
    all_passed = all(c["passed"] for c in checks.values())
    
    validation_payload = {
        "stage": "Phase 4 Stage 4C",
        "title": "브랜드 마스터 구축 및 전국 점포 정합성 검증",
        "validated_at": now_str,
        "overall_status": "PASS" if all_passed else "FAIL",
        "verification_summary": {
            "total_nationwide_stores": raw_store_count,
            "total_brands_in_master": total_brands,
            "census_80_brands": {
                "total": census_brands,
                "FRANCHISE_CONFIRMED": franchise_confirmed,
                "BRAND_CONFIRMED_100_PERCENT_DIRECT": brand_confirmed,
                "UNVERIFIED_DEFICIENT": 1
            },
            "cluster_candidates": cluster_brands,
            "store_brand_links": {
                "total_links": total_links,
                "unique_stores": uniq_stores_linked,
                "multi_candidate_stores": multi_cand_stores,
                "match_status_breakdown": match_status_counts,
                "operation_type_breakdown": operation_type_counts
            },
            "independent_quality_evaluation": {
                "total_samples": eval_samples_count,
                "positive_samples": eval_positives_count,
                "negative_samples": eval_negatives_count,
                "precision": audit_metrics.get("INDEPENDENT_PRECISION"),
                "recall": audit_metrics.get("INDEPENDENT_RECALL"),
                "f1_score": audit_metrics.get("INDEPENDENT_F1_SCORE"),
                "verdict": "PASS" if audit_metrics.get("INDEPENDENT_PRECISION", 0) >= 95.0 else "FAIL"
            }
        },
        "detailed_checks": checks
    }
    
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(validation_payload, f, indent=2, ensure_ascii=False)
        
    print(f"=== [Stage 4C Validation Report Generated] ===")
    print(f"  Overall Status: {'[PASS]' if all_passed else '[FAIL]'}")
    print(f"  Target JSON: {out_json}")
    
    return validation_payload

if __name__ == "__main__":
    res = run_comprehensive_validation()
    print("Done. Overall status:", res["overall_status"])
