"""
Stage 4B: 브랜드 매칭 품질 검증, 골드 스탠다드 평가 및 지표 산출 모듈
프로젝트: D:/Franchise_Dashboard
위치: src/stage4b/evaluator.py
"""

import sys
import json
import sqlite3
import datetime
from pathlib import Path
from typing import Dict, List, Any, Tuple

BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.stage4b.schema_stage4b import DEFAULT_STAGE4B_DB_PATH
from src.stage4b.normalizer import normalize_store_name_full
from src.stage4b.candidate_engine import evaluate_store_candidate
from src.stage4a.brand_matcher_experiment import SAMPLE_BRANDS

STAGE4A_DB_PATH = BASE_DIR / "data" / "brand_intelligence_stage4a.sqlite3"

# 37개 표본 브랜드명 -> 별칭 및 부정 키워드 매핑 딕셔너리
SAMPLE_BRAND_LOOKUP = {b["brand_name"]: b for b in SAMPLE_BRANDS}

def build_gold_standard_eval_dataset(stage4a_db: Path = STAGE4A_DB_PATH) -> List[Dict[str, Any]]:
    """
    Stage 4A의 1,110건 표본을 바탕으로, 실제 사업자 및 상호 구조에 기반한
    검증 가능한 Ground-Truth 평가 표본 데이터셋을 구축한다.
    """
    if not stage4a_db.exists():
        raise FileNotFoundError(f"Stage 4A DB not found at: {stage4a_db}")

    con = sqlite3.connect(stage4a_db)
    cur = con.cursor()
    rows = cur.execute("""
        SELECT bizes_id, target_brand_name, brand_category_major, raw_bizes_nm, semas_mcls_nm
        FROM store_brand_match_samples
    """).fetchall()
    con.close()

    eval_samples = []

    for r in rows:
        bizes_id, target_brand, cat_major, raw_nm, mcls_nm = r
        clean_raw = raw_nm.replace(" ", "").lower()
        brand_def = SAMPLE_BRAND_LOOKUP.get(target_brand, {})
        aliases = [a.replace(" ", "").lower() for a in brand_def.get("aliases", [target_brand])]
        neg_kws = [n.replace(" ", "").lower() for n in brand_def.get("negative_keywords", [])]

        is_false_suspect = False
        rationale = ""

        # 1. 부정 키워드 체크
        matched_neg = None
        for neg in neg_kws:
            if neg in clean_raw:
                matched_neg = neg
                break

        if matched_neg:
            is_false_suspect = True
            rationale = f"공인 부정 키워드('{matched_neg}') 포함 일반 상호"
        else:
            # 2. 일반 식당 키워드 결합 체크 (브랜드 공식 명칭에 포함되지 않은 일반 접미어)
            generic_words = ["식당", "면옥", "한우", "갈비", "밥상", "포차", "주막", "국밥", "마을"]
            has_generic = any(gw in clean_raw for gw in generic_words if gw not in clean_raw[:len(gw)*2])
            
            # 대상 브랜드의 별칭 중 하나라도 접두/포함되는지 검사
            matched_alias = None
            for a in aliases:
                if clean_raw == a or clean_raw.startswith(a) or a in clean_raw:
                    matched_alias = a
                    break

            if not matched_alias:
                is_false_suspect = True
                rationale = f"브랜드 공식 별칭 미일치 단순 키워드 검색 상호 ('{raw_nm}')"
            elif has_generic and target_brand not in ["하남돼지집", "새마을식당"]:
                is_false_suspect = True
                rationale = f"브랜드명 포함되나 일반식당 접미어 결합 ('{raw_nm}')"
            else:
                is_false_suspect = False
                rationale = f"공식 브랜드/별칭('{matched_alias}') 및 지점 구조 정합 ('{raw_nm}')"

        ground_truth_label = 0 if is_false_suspect else 1

        eval_samples.append({
            "bizes_id": bizes_id,
            "raw_bizes_nm": raw_nm,
            "target_brand_name": target_brand,
            "category_major": cat_major,
            "semas_mcls_nm": mcls_nm,
            "ground_truth_label": ground_truth_label,
            "ground_truth_rationale": rationale
        })

    return eval_samples


def evaluate_stage4b_quality(
    target_db_path: Path = DEFAULT_STAGE4B_DB_PATH
) -> Dict[str, Any]:
    """
    Stage 4B 알고리즘을 평가 데이터셋(1,110건)에 적용하여
    정밀도(Precision), 재현율(Recall), F1-Score 및 세부 품질 지표를 산출하고 DB에 기록한다.
    """
    eval_samples = build_gold_standard_eval_dataset()
    print(f"[*] 평가 데이터셋 로드 완료: 총 {len(eval_samples)}건")

    tp_count = 0 # 실제 참(1)인데 참(VERIFIED_AUTO)으로 맞춤
    fp_count = 0 # 실제 거짓(0)인데 참(VERIFIED_AUTO)으로 잘못 확정함
    fn_count = 0 # 실제 참(1)인데 참으로 확정하지 못함
    tn_count = 0 # 실제 거짓(0)인데 REJECTED 또는 INDEPENDENT로 잘 걸러냄

    auto_confirmed_count = 0
    review_required_count = 0
    rejected_count = 0

    category_stats: Dict[str, Dict[str, int]] = {}
    brand_stats: Dict[str, Dict[str, int]] = {}

    db_con = sqlite3.connect(target_db_path)
    cur = db_con.cursor()
    cur.execute("DELETE FROM labeled_evaluation_samples;")

    now_iso = datetime.datetime.now().isoformat()

    for sample in eval_samples:
        bizes_id = sample["bizes_id"]
        raw_nm = sample["raw_bizes_nm"]
        gt_label = sample["ground_truth_label"]
        cat_major = sample["category_major"]
        target_brand = sample["target_brand_name"]

        if cat_major not in category_stats:
            category_stats[cat_major] = {"total": 0, "tp": 0, "fp": 0, "auto": 0, "review": 0}
        if target_brand not in brand_stats:
            brand_stats[target_brand] = {"total": 0, "tp": 0, "fp": 0, "auto": 0}

        category_stats[cat_major]["total"] += 1
        brand_stats[target_brand]["total"] += 1

        # 4B 엔진 실행
        norm_res = normalize_store_name_full(raw_nm)
        cand_results = evaluate_store_candidate(
            store_norm=norm_res,
            bizes_id=bizes_id,
            inds_mcls_nm=sample.get("semas_mcls_nm"),
            cluster_store_count=15
        )

        primary_cand = cand_results[0]
        pred_status = primary_cand["store_verification_status"]
        pred_brand_id = primary_cand["candidate_brand_id"]

        is_pred_positive = (pred_status == "VERIFIED_AUTO")
        if is_pred_positive:
            auto_confirmed_count += 1
            category_stats[cat_major]["auto"] += 1
            brand_stats[target_brand]["auto"] += 1
        elif pred_status == "REVIEW_REQUIRED":
            review_required_count += 1
            category_stats[cat_major]["review"] += 1
        else:
            rejected_count += 1

        # 정답 비교
        is_correct = 0
        if gt_label == 1:
            if is_pred_positive:
                tp_count += 1
                category_stats[cat_major]["tp"] += 1
                brand_stats[target_brand]["tp"] += 1
                is_correct = 1
            else:
                fn_count += 1
        else: # gt_label == 0
            if is_pred_positive:
                fp_count += 1
                category_stats[cat_major]["fp"] += 1
                brand_stats[target_brand]["fp"] += 1
                is_correct = 0
            else:
                tn_count += 1
                is_correct = 1

        cur.execute("""
            INSERT INTO labeled_evaluation_samples (
                bizes_id, raw_bizes_nm, normalized_bizes_nm, target_brand_name,
                category_major, ground_truth_label, ground_truth_brand_id,
                ground_truth_rationale, predicted_candidate_id, predicted_status,
                is_correct, evaluated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            bizes_id, raw_nm, norm_res["normalized_core_nm"], target_brand,
            cat_major, gt_label, target_brand, sample["ground_truth_rationale"],
            pred_brand_id, pred_status, is_correct, now_iso
        ))

    # 메트릭 계산
    precision = (tp_count / (tp_count + fp_count) * 100.0) if (tp_count + fp_count) > 0 else 0.0
    total_true_positives = tp_count + fn_count
    recall = (tp_count / total_true_positives * 100.0) if total_true_positives > 0 else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0
    auto_ratio = (auto_confirmed_count / len(eval_samples) * 100.0)
    review_ratio = (review_required_count / len(eval_samples) * 100.0)

    run_id = f"EVAL_4B_{int(datetime.datetime.now().timestamp())}"

    # 품질 지표 저장
    metrics_to_record = [
        ("PRECISION_AUTO_CONFIRMED", precision, 95.0, "PASS" if precision >= 95.0 else "FAIL", len(eval_samples), f"TP={tp_count}, FP={fp_count}"),
        ("RECALL_TRUE_BRANDS", recall, 80.0, "PASS" if recall >= 80.0 else "CONDITIONAL", len(eval_samples), f"TP={tp_count}, FN={fn_count}"),
        ("F1_SCORE", f1, 85.0, "PASS" if f1 >= 85.0 else "CONDITIONAL", len(eval_samples), f"Harmonic mean of P and R"),
        ("AUTO_LINK_RATIO", auto_ratio, None, "MEASURED", len(eval_samples), f"Auto confirmed {auto_confirmed_count} / {len(eval_samples)}"),
        ("REVIEW_REQUIRED_RATIO", review_ratio, None, "MEASURED", len(eval_samples), f"Review required {review_required_count} / {len(eval_samples)}")
    ]

    for m_name, m_val, th_val, stat, s_size, notes in metrics_to_record:
        cur.execute("""
            INSERT INTO quality_metrics (
                run_id, metric_name, metric_value, threshold_value, status, sample_size, notes, measured_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (run_id, m_name, round(m_val, 2), th_val, stat, s_size, notes, now_iso))

    db_con.commit()
    db_con.close()

    result_summary = {
        "run_id": run_id,
        "total_samples": len(eval_samples),
        "ground_truth_breakdown": {
            "true_franchise_stores": total_true_positives,
            "non_franchise_false_positives": tn_count + fp_count
        },
        "confusion_matrix": {
            "tp": tp_count,
            "fp": fp_count,
            "tn": tn_count,
            "fn": fn_count
        },
        "performance_metrics": {
            "precision_pct": round(precision, 2),
            "recall_pct": round(recall, 2),
            "f1_score": round(f1, 2),
            "auto_confirmed_ratio_pct": round(auto_ratio, 2),
            "review_required_ratio_pct": round(review_ratio, 2),
            "target_precision_threshold_pct": 95.0,
            "target_precision_met": precision >= 95.0
        },
        "category_metrics": category_stats,
        "brand_metrics": brand_stats
    }

    return result_summary

if __name__ == "__main__":
    from src.stage4b.schema_stage4b import initialize_stage4b_database
    initialize_stage4b_database()
    res = evaluate_stage4b_quality()
    print("\n================ 품질 평가 결과 ================")
    print(f"정밀도 (Precision): {res['performance_metrics']['precision_pct']}% (목표 95.0% 대비: {res['performance_metrics']['target_precision_met']})")
    print(f"재현율 (Recall): {res['performance_metrics']['recall_pct']}%")
    print(f"F1-Score: {res['performance_metrics']['f1_score']}")
    print(f"자동 확정 비율: {res['performance_metrics']['auto_confirmed_ratio_pct']}%")
    print(f"수동 검토 필요 비율: {res['performance_metrics']['review_required_ratio_pct']}%")
    print(f"혼동 행렬: TP={res['confusion_matrix']['tp']}, FP={res['confusion_matrix']['fp']}, TN={res['confusion_matrix']['tn']}, FN={res['confusion_matrix']['fn']}")
