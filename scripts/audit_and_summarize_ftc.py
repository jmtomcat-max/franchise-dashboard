import os
import sys
import json
import sqlite3
import statistics
from pathlib import Path

BASE_DIR = Path("D:/Franchise_Dashboard")
DB_PATH = BASE_DIR / "data" / "ftc_macro_statistics_v1.sqlite3"
YEARS = ["2023", "2024", "2025", "2026"]

def run_audit():
    if not DB_PATH.exists():
        print(f"[ERROR] DB not found at {DB_PATH}")
        sys.exit(1)
        
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("PRAGMA busy_timeout = 30000;")
    
    audit_results = {
        "database_info": {
            "path": str(DB_PATH),
            "size_bytes": os.path.getsize(DB_PATH),
            "size_mb": round(os.path.getsize(DB_PATH) / (1024 * 1024), 2)
        },
        "year_execution_summary": {},
        "candidate_key_audit": {},
        "fingerprint_audit": {},
        "field_quality_audit": {},
        "startup_cost_audit": {},
        "tpbiz_distribution": {},
        "rgn_distribution": {},
        "id_stability_audit": {},
        "industry_macro_summary": {},
        "version_string_2026": None
    }
    
    print("\n=======================================================")
    print("[1] Verifying Ingestion Checkpoints & Audit Logs")
    print("=======================================================")
    for yr in YEARS:
        cur.execute("SELECT * FROM ftc_ingestion_audit_logs WHERE jng_biz_crtr_yr = ? ORDER BY audit_id DESC LIMIT 1", (yr,))
        alog = cur.fetchone()
        
        cur.execute("SELECT COUNT(*), SUM(items_fetched), SUM(items_saved) FROM ftc_ingestion_checkpoints WHERE jng_biz_crtr_yr = ? AND status = 'SUCCESS'", (yr,))
        chk_success = cur.fetchone()
        
        cur.execute("SELECT COUNT(*) FROM ftc_ingestion_checkpoints WHERE jng_biz_crtr_yr = ? AND status != 'SUCCESS'", (yr,))
        chk_failed = cur.fetchone()[0]
        
        cur.execute("SELECT COUNT(*) FROM ftc_brand_macro_records WHERE jng_biz_crtr_yr = ?", (yr,))
        clean_count = cur.fetchone()[0]
        
        cur.execute("SELECT COUNT(*) FROM ftc_raw_api_responses WHERE jng_biz_crtr_yr = ?", (yr,))
        raw_pages = cur.fetchone()[0]
        
        # Last page items
        cur.execute("SELECT page_no, items_saved FROM ftc_ingestion_checkpoints WHERE jng_biz_crtr_yr = ? ORDER BY page_no DESC LIMIT 1", (yr,))
        last_page_info = cur.fetchone()
        
        yr_summary = {
            "pre_total_count": alog[2] if alog else None,
            "post_total_count": alog[3] if alog else None,
            "total_pages_expected": alog[4] if alog else None,
            "total_pages_succeeded": chk_success[0] if chk_success else 0,
            "total_pages_failed_or_retry": chk_failed,
            "raw_pages_saved": raw_pages,
            "clean_records_saved": clean_count,
            "last_page_no": last_page_info[0] if last_page_info else None,
            "last_page_items": last_page_info[1] if last_page_info else None,
            "audit_status": alog[8] if alog else None,
            "started_at": alog[9] if alog else None,
            "completed_at": alog[10] if alog else None
        }
        audit_results["year_execution_summary"][yr] = yr_summary
        print(f"  [{yr}] Status: {yr_summary['audit_status']}, Pages: {yr_summary['total_pages_succeeded']}/{yr_summary['total_pages_expected']}, Saved: {clean_count}, LastPage: {yr_summary['last_page_items']} items")

    # 2026 version string
    summary_2026 = audit_results["year_execution_summary"].get("2026", {})
    audit_results["version_string_2026"] = f"2026년 공정위 등록 기준 스냅샷 (수집시각: {summary_2026.get('completed_at')}, 확정모수: {summary_2026.get('clean_records_saved')}건)"

    print("\n=======================================================")
    print("[2] Auditing 4-Step Candidate Keys & Fingerprints")
    print("=======================================================")
    cur.execute("DELETE FROM ftc_key_validation_log;")
    candidate_definitions = [
        ("후보 1 (연도+브랜드)", "jng_biz_crtr_yr, als_brand_mng_no", ["jng_biz_crtr_yr", "als_brand_mng_no"]),
        ("후보 2 (연도+브랜드+본부)", "jng_biz_crtr_yr, als_brand_mng_no, als_jnghq_mng_no", ["jng_biz_crtr_yr", "als_brand_mng_no", "als_jnghq_mng_no"]),
        ("후보 3 (연도+브랜드+업종)", "jng_biz_crtr_yr, als_brand_mng_no, tpbiz_mclsf_nm", ["jng_biz_crtr_yr", "als_brand_mng_no", "tpbiz_mclsf_nm"]),
        ("후보 4 (연도+브랜드+본부+업종)", "jng_biz_crtr_yr, als_brand_mng_no, als_jnghq_mng_no, tpbiz_mclsf_nm", ["jng_biz_crtr_yr", "als_brand_mng_no", "als_jnghq_mng_no", "tpbiz_mclsf_nm"])
    ]
    
    for yr in YEARS:
        audit_results["candidate_key_audit"][yr] = {}
        cur.execute("SELECT COUNT(*) FROM ftc_brand_macro_records WHERE jng_biz_crtr_yr = ?", (yr,))
        total_rec = cur.fetchone()[0]
        
        for name, fields_str, fields_list in candidate_definitions:
            cur.execute(f"""
                SELECT COUNT(*) FROM (
                    SELECT {fields_str}, COUNT(*) AS cnt
                    FROM ftc_brand_macro_records
                    WHERE jng_biz_crtr_yr = ?
                    GROUP BY {fields_str}
                    HAVING cnt > 1
                )
            """, (yr,))
            dup_keys = cur.fetchone()[0]
            
            cur.execute(f"""
                SELECT COALESCE(SUM(cnt), 0) FROM (
                    SELECT {fields_str}, COUNT(*) AS cnt
                    FROM ftc_brand_macro_records
                    WHERE jng_biz_crtr_yr = ?
                    GROUP BY {fields_str}
                    HAVING cnt > 1
                )
            """, (yr,))
            dup_records = cur.fetchone()[0]
            
            cur.execute(f"SELECT COUNT(*) FROM (SELECT DISTINCT {fields_str} FROM ftc_brand_macro_records WHERE jng_biz_crtr_yr = ?)", (yr,))
            distinct_k = cur.fetchone()[0]
            
            is_uniq = 1 if dup_keys == 0 else 0
            cur.execute("""
                INSERT INTO ftc_key_validation_log (
                    jng_biz_crtr_yr, candidate_key_name, key_fields, total_records,
                    distinct_keys, duplicate_keys_count, duplicate_records_count, is_unique
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (yr, name, fields_str, total_rec, distinct_k, dup_keys, dup_records, is_uniq))
            
            audit_results["candidate_key_audit"][yr][name] = {
                "fields": fields_str,
                "total_records": total_rec,
                "distinct_keys": distinct_k,
                "duplicate_keys": dup_keys,
                "duplicate_records": dup_records,
                "is_unique": bool(is_uniq)
            }
            if is_uniq:
                print(f"  [{yr}] {name}: UNIQUE PASS (0 Duplicates)")
            else:
                print(f"  [{yr}] {name}: COLLISION ({dup_keys} dup keys, {dup_records} recs)")

        # Fingerprint duplicate audit
        cur.execute("""
            SELECT COUNT(*) FROM (
                SELECT row_fingerprint, COUNT(*) AS cnt
                FROM ftc_brand_macro_records
                WHERE jng_biz_crtr_yr = ?
                GROUP BY row_fingerprint
                HAVING cnt > 1
            )
        """, (yr,))
        fp_dup_keys = cur.fetchone()[0]
        cur.execute(f"SELECT COUNT(DISTINCT row_fingerprint) FROM ftc_brand_macro_records WHERE jng_biz_crtr_yr = ?", (yr,))
        fp_distinct = cur.fetchone()[0]
        audit_results["fingerprint_audit"][yr] = {
            "total_records": total_rec,
            "distinct_fingerprints": fp_distinct,
            "duplicate_fingerprints": fp_dup_keys,
            "is_unique": (fp_dup_keys == 0)
        }
        print(f"  [{yr}] Fingerprint Uniqueness: {'PASS (0 Dup)' if fp_dup_keys == 0 else f'COLLISION ({fp_dup_keys})'}")
    conn.commit()

    print("\n=======================================================")
    print("[3] Auditing Field Quality, NULLs, & Outliers")
    print("=======================================================")
    for yr in YEARS:
        cur.execute("""
            SELECT 
                COUNT(*) AS total,
                SUM(CASE WHEN als_brand_mng_no IS NULL OR als_brand_mng_no = '' THEN 1 ELSE 0 END) AS null_brand,
                SUM(CASE WHEN als_jnghq_mng_no IS NULL OR als_jnghq_mng_no = '' THEN 1 ELSE 0 END) AS null_hq,
                SUM(CASE WHEN tpbiz_mclsf_nm IS NULL OR tpbiz_mclsf_nm = '' THEN 1 ELSE 0 END) AS null_tpbiz,
                SUM(CASE WHEN frcs_cnt < 0 THEN 1 ELSE 0 END) AS negative_frcs,
                SUM(CASE WHEN dms_cnt < 0 THEN 1 ELSE 0 END) AS negative_dms,
                SUM(CASE WHEN avg_sls_amt IS NULL THEN 1 ELSE 0 END) AS null_sls,
                SUM(CASE WHEN avg_sls_amt < 0 THEN 1 ELSE 0 END) AS negative_sls,
                SUM(CASE WHEN avg_sls_amt == 0 THEN 1 ELSE 0 END) AS zero_sls,
                SUM(CASE WHEN avg_sls_amt > 0 THEN 1 ELSE 0 END) AS valid_positive_sls,
                MIN(avg_sls_amt) AS min_sls,
                MAX(avg_sls_amt) AS max_sls
            FROM ftc_brand_macro_records
            WHERE jng_biz_crtr_yr = ?
        """, (yr,))
        row = cur.fetchone()
        audit_results["field_quality_audit"][yr] = {
            "total_records": row[0],
            "null_brand_id": row[1],
            "null_hq_id": row[2],
            "null_tpbiz": row[3],
            "negative_frcs_cnt": row[4],
            "negative_dms_cnt": row[5],
            "null_avg_sls_amt": row[6],
            "negative_avg_sls_amt": row[7],
            "zero_avg_sls_amt": row[8],
            "valid_positive_sls_amt": row[9],
            "min_avg_sls_amt": row[10],
            "max_avg_sls_amt": row[11]
        }
        print(f"  [{yr}] Sales Quality: Valid Positive={row[9]}, Null={row[6]}, Zero={row[8]}, Neg={row[7]}, Min={row[10]}, Max={row[11]}")

    print("\n=======================================================")
    print("[4] Auditing Startup Cost Tentative Formula")
    print("=======================================================")
    for yr in YEARS:
        cur.execute("""
            SELECT 
                COUNT(*) AS total,
                SUM(CASE WHEN calc_depst_diff IS NOT NULL AND abs(calc_depst_diff) < 0.001 THEN 1 ELSE 0 END) AS exact_matches,
                SUM(CASE WHEN calc_depst_diff IS NOT NULL AND abs(calc_depst_diff) >= 0.001 THEN 1 ELSE 0 END) AS mismatches,
                SUM(CASE WHEN calc_depst_diff IS NULL THEN 1 ELSE 0 END) AS null_diffs,
                MIN(calc_depst_diff) AS min_diff,
                MAX(calc_depst_diff) AS max_diff
            FROM ftc_brand_macro_records
            WHERE jng_biz_crtr_yr = ?
        """, (yr,))
        c_row = cur.fetchone()
        total_eval = c_row[1] + c_row[2]
        match_rate = round((c_row[1] / total_eval * 100.0), 2) if total_eval > 0 else 0.0
        audit_results["startup_cost_audit"][yr] = {
            "total_records": c_row[0],
            "exact_matches": c_row[1],
            "mismatches": c_row[2],
            "null_diffs": c_row[3],
            "match_rate_pct": match_rate,
            "min_diff": c_row[4],
            "max_diff": c_row[5],
            "is_empirically_verified": (c_row[2] == 0)
        }
        print(f"  [{yr}] depstAmt == jng+edu+grnte: Match={c_row[1]}, Mismatch={c_row[2]}, Rate={match_rate}%, Null={c_row[3]}")

    print("\n=======================================================")
    print("[5] Generating Idempotent Domain Survey & Industry Summaries")
    print("=======================================================")
    cur.execute("DELETE FROM ftc_tpbiz_domain_survey;")
    cur.execute("DELETE FROM ftc_industry_macro_summary;")
    
    for yr in YEARS:
        # Domain survey
        cur.execute("""
            INSERT INTO ftc_tpbiz_domain_survey (
                jng_biz_crtr_yr, tpbiz_mclsf_nm, record_count,
                total_franchise_stores, total_direct_stores, record_percentage
            )
            SELECT 
                jng_biz_crtr_yr, tpbiz_mclsf_nm,
                COUNT(*) AS record_count,
                SUM(frcs_cnt) AS total_franchise_stores,
                SUM(dms_cnt) AS total_direct_stores,
                ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM ftc_brand_macro_records WHERE jng_biz_crtr_yr=?), 2) AS record_percentage
            FROM ftc_brand_macro_records
            WHERE jng_biz_crtr_yr = ?
            GROUP BY jng_biz_crtr_yr, tpbiz_mclsf_nm
            ORDER BY record_count DESC;
        """, (yr, yr))
        
        cur.execute("SELECT tpbiz_mclsf_nm, record_count, total_franchise_stores, record_percentage FROM ftc_tpbiz_domain_survey WHERE jng_biz_crtr_yr = ? ORDER BY record_count DESC", (yr,))
        audit_results["tpbiz_distribution"][yr] = [
            {"tpbiz": r[0], "records": r[1], "franchise_stores": r[2], "pct": r[3]}
            for r in cur.fetchall()
        ]
        
        # Region survey
        cur.execute("""
            SELECT COALESCE(jnghq_rgn_nm, '미기재') AS rgn, COUNT(*) AS cnt, ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM ftc_brand_macro_records WHERE jng_biz_crtr_yr=?), 2)
            FROM ftc_brand_macro_records WHERE jng_biz_crtr_yr = ?
            GROUP BY rgn ORDER BY cnt DESC;
        """, (yr, yr))
        audit_results["rgn_distribution"][yr] = [
            {"region": r[0], "records": r[1], "pct": r[2]} for r in cur.fetchall()
        ]
        
        # Industry Macro Summary Aggregation
        cur.execute("SELECT DISTINCT tpbiz_mclsf_nm FROM ftc_brand_macro_records WHERE jng_biz_crtr_yr = ?", (yr,))
        tpbiz_list = [r[0] for r in cur.fetchall()]
        
        audit_results["industry_macro_summary"][yr] = []
        for tp in tpbiz_list:
            cur.execute("""
                SELECT 
                    COUNT(*) AS rec_cnt,
                    SUM(frcs_cnt) AS sum_frcs,
                    SUM(dms_cnt) AS sum_dms,
                    SUM(CASE WHEN avg_sls_amt > 0 THEN avg_sls_amt ELSE 0 END) AS sum_sls,
                    SUM(CASE WHEN avg_sls_amt > 0 THEN avg_sls_amt * frcs_cnt ELSE 0 END) AS sum_weighted_sls,
                    SUM(CASE WHEN avg_sls_amt > 0 THEN frcs_cnt ELSE 0 END) AS denom_weighted_sls,
                    SUM(CASE WHEN avg_sls_amt > 0 THEN 1 ELSE 0 END) AS valid_sls_cnt,
                    SUM(CASE WHEN avg_sls_amt IS NULL OR avg_sls_amt = 0 THEN 1 ELSE 0 END) AS null_sls_cnt,
                    SUM(CASE WHEN area_unit_avg_sls_amt > 0 THEN area_unit_avg_sls_amt ELSE 0 END) AS sum_area_sls,
                    SUM(CASE WHEN area_unit_avg_sls_amt > 0 THEN area_unit_avg_sls_amt * frcs_cnt ELSE 0 END) AS sum_weighted_area_sls,
                    SUM(CASE WHEN area_unit_avg_sls_amt > 0 THEN 1 ELSE 0 END) AS valid_area_cnt,
                    AVG(jng_bzmn_jng_amt) AS avg_jng,
                    AVG(jng_bzmn_edu_amt) AS avg_edu,
                    AVG(jng_bzmn_grnte_amt) AS avg_grnte,
                    AVG(jng_bzmn_etc_amt) AS avg_etc,
                    AVG(intrr_amt) AS avg_intrr,
                    AVG(unit_area_intrr_amt) AS avg_unit_intrr,
                    AVG(tentative_startup_cost_thousand) AS avg_startup
                FROM ftc_brand_macro_records
                WHERE jng_biz_crtr_yr = ? AND tpbiz_mclsf_nm = ?
            """, (yr, tp))
            ag = cur.fetchone()
            
            # Median sales
            cur.execute("SELECT avg_sls_amt FROM ftc_brand_macro_records WHERE jng_biz_crtr_yr = ? AND tpbiz_mclsf_nm = ? AND avg_sls_amt > 0 ORDER BY avg_sls_amt", (yr, tp))
            sls_vals = [r[0] for r in cur.fetchall()]
            med_sls = round(statistics.median(sls_vals), 2) if sls_vals else None
            
            # Median area sales
            cur.execute("SELECT area_unit_avg_sls_amt FROM ftc_brand_macro_records WHERE jng_biz_crtr_yr = ? AND tpbiz_mclsf_nm = ? AND area_unit_avg_sls_amt > 0 ORDER BY area_unit_avg_sls_amt", (yr, tp))
            area_vals = [r[0] for r in cur.fetchall()]
            med_area = round(statistics.median(area_vals), 2) if area_vals else None
            
            # Startup costs medians
            cur.execute("SELECT jng_bzmn_jng_amt FROM ftc_brand_macro_records WHERE jng_biz_crtr_yr = ? AND tpbiz_mclsf_nm = ? AND jng_bzmn_jng_amt IS NOT NULL", (yr, tp))
            jng_vals = [r[0] for r in cur.fetchall()]
            med_jng = round(statistics.median(jng_vals), 2) if jng_vals else None
            
            cur.execute("SELECT jng_bzmn_edu_amt FROM ftc_brand_macro_records WHERE jng_biz_crtr_yr = ? AND tpbiz_mclsf_nm = ? AND jng_bzmn_edu_amt IS NOT NULL", (yr, tp))
            edu_vals = [r[0] for r in cur.fetchall()]
            med_edu = round(statistics.median(edu_vals), 2) if edu_vals else None
            
            cur.execute("SELECT jng_bzmn_grnte_amt FROM ftc_brand_macro_records WHERE jng_biz_crtr_yr = ? AND tpbiz_mclsf_nm = ? AND jng_bzmn_grnte_amt IS NOT NULL", (yr, tp))
            grnte_vals = [r[0] for r in cur.fetchall()]
            med_grnte = round(statistics.median(grnte_vals), 2) if grnte_vals else None
            
            cur.execute("SELECT jng_bzmn_etc_amt FROM ftc_brand_macro_records WHERE jng_biz_crtr_yr = ? AND tpbiz_mclsf_nm = ? AND jng_bzmn_etc_amt IS NOT NULL", (yr, tp))
            etc_vals = [r[0] for r in cur.fetchall()]
            med_etc = round(statistics.median(etc_vals), 2) if etc_vals else None
            
            cur.execute("SELECT intrr_amt FROM ftc_brand_macro_records WHERE jng_biz_crtr_yr = ? AND tpbiz_mclsf_nm = ? AND intrr_amt IS NOT NULL", (yr, tp))
            intrr_vals = [r[0] for r in cur.fetchall()]
            med_intrr = round(statistics.median(intrr_vals), 2) if intrr_vals else None
            
            cur.execute("SELECT unit_area_intrr_amt FROM ftc_brand_macro_records WHERE jng_biz_crtr_yr = ? AND tpbiz_mclsf_nm = ? AND unit_area_intrr_amt IS NOT NULL", (yr, tp))
            u_intrr_vals = [r[0] for r in cur.fetchall()]
            med_uintrr = round(statistics.median(u_intrr_vals), 2) if u_intrr_vals else None
            
            cur.execute("SELECT tentative_startup_cost_thousand FROM ftc_brand_macro_records WHERE jng_biz_crtr_yr = ? AND tpbiz_mclsf_nm = ? AND tentative_startup_cost_thousand IS NOT NULL", (yr, tp))
            start_vals = [r[0] for r in cur.fetchall()]
            med_start = round(statistics.median(start_vals), 2) if start_vals else None
            
            rec_cnt = ag[0]
            sum_frcs = ag[1] or 0
            sum_dms = ag[2] or 0
            sum_sls = ag[3] or 0.0
            sum_weighted_sls = ag[4] or 0.0
            denom_weighted_sls = ag[5] or 0
            valid_sls_cnt = ag[6]
            null_sls_cnt = ag[7]
            
            brand_simple_avg_sls = round(sum_sls / valid_sls_cnt, 2) if valid_sls_cnt > 0 else None
            store_weighted_avg_sls = round(sum_weighted_sls / denom_weighted_sls, 2) if denom_weighted_sls > 0 else None
            
            valid_area_cnt = ag[10]
            sum_area_sls = ag[8] or 0.0
            sum_weighted_area_sls = ag[9] or 0.0
            brand_simple_avg_area = round(sum_area_sls / valid_area_cnt, 2) if valid_area_cnt > 0 else None
            store_weighted_avg_area = round(sum_weighted_area_sls / denom_weighted_sls, 2) if denom_weighted_sls > 0 else None
            
            cur.execute("""
                INSERT INTO ftc_industry_macro_summary (
                    jng_biz_crtr_yr, tpbiz_mclsf_nm, record_count, sum_frcs_cnt, sum_dms_cnt,
                    brand_simple_avg_sls_amt, store_weighted_avg_sls_amt, median_sls_amt,
                    sls_valid_record_count, sls_null_record_count, sum_sls_amount,
                    sum_weighted_sls_amount, denom_store_weighted_sls,
                    brand_simple_avg_area_sls, store_weighted_avg_area_sls, median_area_sls,
                    area_sls_valid_count,
                    avg_jng_amt, median_jng_amt, valid_jng_cnt,
                    avg_edu_amt, median_edu_amt, valid_edu_cnt,
                    avg_grnte_amt, median_grnte_amt, valid_grnte_cnt,
                    avg_etc_amt, median_etc_amt, valid_etc_cnt,
                    avg_intrr_amt, median_intrr_amt, valid_intrr_cnt,
                    avg_unit_intrr, median_unit_intrr, valid_unit_intrr_cnt,
                    avg_total_startup, median_total_startup, valid_total_startup_cnt
                ) VALUES (
                    ?, ?, ?, ?, ?,
                    ?, ?, ?,
                    ?, ?, ?,
                    ?, ?,
                    ?, ?, ?,
                    ?,
                    ?, ?, ?,
                    ?, ?, ?,
                    ?, ?, ?,
                    ?, ?, ?,
                    ?, ?, ?,
                    ?, ?, ?,
                    ?, ?, ?
                )
            """, (
                yr, tp, rec_cnt, sum_frcs, sum_dms,
                brand_simple_avg_sls, store_weighted_avg_sls, med_sls,
                valid_sls_cnt, null_sls_cnt, round(sum_sls, 2),
                round(sum_weighted_sls, 2), denom_weighted_sls,
                brand_simple_avg_area, store_weighted_avg_area, med_area,
                valid_area_cnt,
                round(ag[11], 2) if ag[11] else None, med_jng, len(jng_vals),
                round(ag[12], 2) if ag[12] else None, med_edu, len(edu_vals),
                round(ag[13], 2) if ag[13] else None, med_grnte, len(grnte_vals),
                round(ag[14], 2) if ag[14] else None, med_etc, len(etc_vals),
                round(ag[15], 2) if ag[15] else None, med_intrr, len(intrr_vals),
                round(ag[16], 2) if ag[16] else None, med_uintrr, len(u_intrr_vals),
                round(ag[17], 2) if ag[17] else None, med_start, len(start_vals)
            ))
            
            audit_results["industry_macro_summary"][yr].append({
                "tpbiz": tp,
                "records": rec_cnt,
                "frcs_cnt": sum_frcs,
                "brand_simple_avg_sls": brand_simple_avg_sls,
                "store_weighted_avg_sls": store_weighted_avg_sls,
                "median_sls": med_sls,
                "valid_sls_count": valid_sls_cnt,
                "denom_weighted_sls": denom_weighted_sls
            })
            
    conn.commit()

    print("\n=======================================================")
    print("[6] Auditing Pseudonym ID Temporal Stability Across Years")
    print("=======================================================")
    cur.execute("DELETE FROM ftc_id_stability_metrics;")
    
    # Extract distinct brand IDs and HQ IDs per year
    brands_by_yr = {}
    brand_hq_map_by_yr = {}
    for yr in YEARS:
        cur.execute("SELECT als_brand_mng_no, als_jnghq_mng_no FROM ftc_brand_macro_records WHERE jng_biz_crtr_yr = ?", (yr,))
        rows = cur.fetchall()
        brands_by_yr[yr] = set(r[0] for r in rows)
        brand_hq_map_by_yr[yr] = {r[0]: r[1] for r in rows}

    transitions = [("2023", "2024"), ("2024", "2025"), ("2025", "2026"), ("2023", "2026")]
    for y1, y2 in transitions:
        b1 = brands_by_yr[y1]
        b2 = brands_by_yr[y2]
        common = b1.intersection(b2)
        new_entries = b2 - b1
        exits = b1 - b2
        
        persistence_rate = round(len(common) / len(b1) * 100.0, 2) if len(b1) > 0 else 0.0
        
        # HQ change rate among surviving brands
        hq_changes = 0
        for b in common:
            if brand_hq_map_by_yr[y1].get(b) != brand_hq_map_by_yr[y2].get(b):
                hq_changes += 1
        hq_change_rate = round(hq_changes / len(common) * 100.0, 2) if len(common) > 0 else 0.0
        
        # Re-appearance: in y0, not in y1, in y2
        reappearing = 0
        if y1 == "2024" and y2 == "2025": # 2023 in, 2024 out, 2025 in
            reappearing = len((brands_by_yr["2023"] - brands_by_yr["2024"]).intersection(brands_by_yr["2025"]))
        elif y1 == "2025" and y2 == "2026": # 2024 in, 2025 out, 2026 in
            reappearing = len((brands_by_yr["2024"] - brands_by_yr["2025"]).intersection(brands_by_yr["2026"]))
            
        period_label = f"{y1}->{y2}" if y1 != "2023" or y2 != "2026" else "2023->2026 (4-Year Panel)"
        
        cur.execute("""
            INSERT INTO ftc_id_stability_metrics (
                transition_period, prior_year, current_year,
                prior_year_total_brands, current_year_total_brands,
                common_surviving_brands, persistence_rate_pct,
                new_entry_brands, exit_brands, reappearing_brands,
                hq_changed_brands, hq_change_rate_pct
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            period_label, y1, y2, len(b1), len(b2),
            len(common), persistence_rate, len(new_entries), len(exits),
            reappearing, hq_changes, hq_change_rate
        ))
        
        audit_results["id_stability_audit"][period_label] = {
            "prior_year": y1,
            "current_year": y2,
            "prior_total": len(b1),
            "current_total": len(b2),
            "common_surviving": len(common),
            "persistence_rate_pct": persistence_rate,
            "new_entries": len(new_entries),
            "exits": len(exits),
            "reappearing": reappearing,
            "hq_changed": hq_changes,
            "hq_change_rate_pct": hq_change_rate
        }
        print(f"  [{period_label}] Common: {len(common)}/{len(b1)} ({persistence_rate}%), New: {len(new_entries)}, Exit: {len(exits)}, HQ Changed: {hq_changes} ({hq_change_rate}%)")
        
    # 4-Year intersection (in all 2023, 2024, 2025, 2026)
    all_4_surviving = brands_by_yr["2023"].intersection(brands_by_yr["2024"]).intersection(brands_by_yr["2025"]).intersection(brands_by_yr["2026"])
    audit_results["id_stability_audit"]["balanced_4_year_panel"] = {
        "surviving_all_4_years": len(all_4_surviving),
        "pct_of_2023_cohort": round(len(all_4_surviving) / len(brands_by_yr["2023"]) * 100.0, 2),
        "pct_of_2026_cohort": round(len(all_4_surviving) / len(brands_by_yr["2026"]) * 100.0, 2)
    }
    print(f"  [Balanced 4-Year Panel] Brands present in all 4 years: {len(all_4_surviving)} ({audit_results['id_stability_audit']['balanced_4_year_panel']['pct_of_2023_cohort']}% of 2023)")
    conn.commit()

    # Table row counts
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [r[0] for r in cur.fetchall()]
    table_counts = {}
    for t in tables:
        cur.execute(f"SELECT COUNT(*) FROM '{t}'")
        table_counts[t] = cur.fetchone()[0]
    audit_results["table_row_counts"] = table_counts

    conn.close()

    # Save to JSON
    out_json = BASE_DIR / "reports" / "phase4f_ftc_multi_year_validation.json"
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(audit_results, f, ensure_ascii=False, indent=2)
    print(f"\n[DONE] Full audit results saved to {out_json}")

if __name__ == "__main__":
    run_audit()
