import os
import sys
import json
import time
import math
import hashlib
import random
import urllib.parse
import urllib.request
import urllib.error
import sqlite3
from pathlib import Path

BASE_DIR = Path("D:/Franchise_Dashboard")
DB_PATH = BASE_DIR / "data" / "ftc_macro_statistics_v1.sqlite3"
ENDPOINT = "https://apis.data.go.kr/1130000/FftcBrandFrcsBzmnIntgInfoEatoutTpbizStats2_Service/getBrandFrcsBzmnIntgInfoEatoutTpbiz2"
TARGET_YEARS = ["2023", "2024", "2025", "2026"]
MAX_PAGE_RETRIES = 5
BASE_RETRY_DELAY = 2.0
RATE_LIMIT_DELAY = 0.25

# 1. API Key Loading (Strictly honoring FTC_SERVICE_KEY without logging)
api_key = os.environ.get("FTC_SERVICE_KEY")
if not api_key:
    env_file = BASE_DIR / ".env"
    if env_file.exists():
        with open(env_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("FTC_SERVICE_KEY="):
                    api_key = line.split("=", 1)[1].strip().strip('"').strip("'")
                    break
                elif line.startswith("SERVICE_KEY=") or line.startswith("SERVICEKEY="):
                    api_key = line.split("=", 1)[1].strip().strip('"').strip("'")
                    break

if not api_key:
    print("[ERROR] FTC API Key could not be resolved from FTC_SERVICE_KEY or .env")
    sys.exit(1)

def mask_text(text: str) -> str:
    if not text or not api_key:
        return text
    m = text.replace(api_key, "[MASKED_FTC_KEY]")
    quoted = urllib.parse.quote(api_key)
    if quoted in m:
        m = m.replace(quoted, "[MASKED_FTC_KEY]")
    return m

def init_db(db_path: Path):
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("PRAGMA journal_mode = WAL;")
    cur.execute("PRAGMA synchronous = NORMAL;")
    cur.execute("PRAGMA busy_timeout = 30000;")
    
    cur.execute("""
    CREATE TABLE IF NOT EXISTS ftc_raw_api_responses (
        response_id INTEGER PRIMARY KEY AUTOINCREMENT,
        jng_biz_crtr_yr TEXT NOT NULL,
        page_no INTEGER NOT NULL,
        num_of_rows INTEGER NOT NULL DEFAULT 100,
        http_status INTEGER NOT NULL,
        result_code TEXT NOT NULL,
        total_count INTEGER NOT NULL,
        item_count INTEGER NOT NULL,
        payload_json TEXT NOT NULL,
        fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        CONSTRAINT uq_raw_page UNIQUE (jng_biz_crtr_yr, page_no)
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS ftc_brand_macro_records (
        record_id INTEGER PRIMARY KEY AUTOINCREMENT,
        source_page_no INTEGER NOT NULL,
        source_row_index INTEGER NOT NULL,
        row_fingerprint TEXT NOT NULL,
        als_brand_mng_no TEXT NOT NULL,
        als_jnghq_mng_no TEXT NOT NULL,
        jng_biz_crtr_yr TEXT NOT NULL,
        jnghq_rgn_nm TEXT,
        jng_biz_strt_ymd TEXT,
        tpbiz_mclsf_nm TEXT NOT NULL,
        frcs_cnt INTEGER NOT NULL DEFAULT 0,
        dms_cnt INTEGER NOT NULL DEFAULT 0,
        prvyr_frcs_cnt INTEGER DEFAULT 0,
        prvyr_dms_cnt INTEGER DEFAULT 0,
        jng_bzmn_jng_amt REAL,
        jng_bzmn_edu_amt REAL,
        jng_bzmn_grnte_amt REAL,
        jng_bzmn_etc_amt REAL,
        depst_amt REAL,
        unit_area_intrr_amt REAL,
        intrr_amt REAL,
        prvyr_jng_bzmn_jng_amt REAL,
        prvyr_jng_bzmn_edu_amt REAL,
        prvyr_jng_bzmn_grnte_amt REAL,
        prvyr_jng_bzmn_etc_amt REAL,
        prvyr_depst_amt REAL,
        prvyr_unit_area_intrr_amt REAL,
        prvyr_intrr_amt REAL,
        frst_ctrt_yycnt REAL,
        prlg_ctrt_yycnt REAL,
        stor_crtr_area REAL,
        prvyr_frst_ctrt_yycnt REAL,
        prvyr_prlg_ctrt_yycnt REAL,
        prvyr_stor_crtr_area REAL,
        fyr TEXT,
        avg_sls_amt REAL,
        area_unit_avg_sls_amt REAL,
        prvyr_fyr TEXT,
        prvyr_avg_sls_amt REAL,
        prvyr_area_unit_avg_sls_amt REAL,
        calc_depst_diff REAL,
        calc_depst_is_matched INTEGER,
        tentative_startup_cost_thousand REAL,
        startup_cost_calc_method TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        CONSTRAINT uq_source_position UNIQUE (jng_biz_crtr_yr, source_page_no, source_row_index)
    );
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_ftc_records_year_tpbiz ON ftc_brand_macro_records (jng_biz_crtr_yr, tpbiz_mclsf_nm);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_ftc_records_brand_year ON ftc_brand_macro_records (als_brand_mng_no, jng_biz_crtr_yr);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_ftc_records_fingerprint ON ftc_brand_macro_records (row_fingerprint);")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS ftc_ingestion_checkpoints (
        checkpoint_id INTEGER PRIMARY KEY AUTOINCREMENT,
        jng_biz_crtr_yr TEXT NOT NULL,
        page_no INTEGER NOT NULL,
        num_of_rows INTEGER NOT NULL DEFAULT 100,
        status TEXT NOT NULL CHECK (status IN ('PENDING', 'SUCCESS', 'FAILED', 'RETRY')),
        items_fetched INTEGER DEFAULT 0,
        items_saved INTEGER DEFAULT 0,
        latency_ms INTEGER,
        error_message TEXT,
        retry_count INTEGER DEFAULT 0,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        CONSTRAINT uq_checkpoint_page UNIQUE (jng_biz_crtr_yr, page_no)
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS ftc_ingestion_audit_logs (
        audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
        jng_biz_crtr_yr TEXT NOT NULL,
        pre_total_count INTEGER NOT NULL,
        post_total_count INTEGER,
        total_pages_expected INTEGER NOT NULL,
        total_pages_succeeded INTEGER NOT NULL DEFAULT 0,
        total_records_saved INTEGER NOT NULL DEFAULT 0,
        discrepancy_count INTEGER NOT NULL DEFAULT 0,
        status TEXT NOT NULL CHECK (status IN ('IN_PROGRESS', 'COMPLETED', 'FAILED', 'UNSTABLE_SNAPSHOT')),
        started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        completed_at TIMESTAMP
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS ftc_tpbiz_domain_survey (
        survey_id INTEGER PRIMARY KEY AUTOINCREMENT,
        jng_biz_crtr_yr TEXT NOT NULL,
        tpbiz_mclsf_nm TEXT NOT NULL,
        record_count INTEGER NOT NULL,
        total_franchise_stores INTEGER NOT NULL,
        total_direct_stores INTEGER NOT NULL,
        record_percentage REAL NOT NULL,
        surveyed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        CONSTRAINT uq_domain_survey UNIQUE (jng_biz_crtr_yr, tpbiz_mclsf_nm)
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS ftc_industry_macro_summary (
        summary_id INTEGER PRIMARY KEY AUTOINCREMENT,
        jng_biz_crtr_yr TEXT NOT NULL,
        tpbiz_mclsf_nm TEXT NOT NULL,
        record_count INTEGER NOT NULL,
        sum_frcs_cnt INTEGER NOT NULL,
        sum_dms_cnt INTEGER NOT NULL,
        brand_simple_avg_sls_amt REAL,
        store_weighted_avg_sls_amt REAL,
        median_sls_amt REAL,
        sls_valid_record_count INTEGER NOT NULL,
        sls_null_record_count INTEGER NOT NULL,
        sum_sls_amount REAL,
        sum_weighted_sls_amount REAL,
        denom_store_weighted_sls INTEGER,
        brand_simple_avg_area_sls REAL,
        store_weighted_avg_area_sls REAL,
        median_area_sls REAL,
        area_sls_valid_count INTEGER,
        avg_jng_amt REAL,       median_jng_amt REAL,       valid_jng_cnt INTEGER,
        avg_edu_amt REAL,       median_edu_amt REAL,       valid_edu_cnt INTEGER,
        avg_grnte_amt REAL,     median_grnte_amt REAL,     valid_grnte_cnt INTEGER,
        avg_etc_amt REAL,       median_etc_amt REAL,       valid_etc_cnt INTEGER,
        avg_intrr_amt REAL,     median_intrr_amt REAL,     valid_intrr_cnt INTEGER,
        avg_unit_intrr REAL,    median_unit_intrr REAL,    valid_unit_intrr_cnt INTEGER,
        avg_total_startup REAL, median_total_startup REAL, valid_total_startup_cnt INTEGER,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        CONSTRAINT uq_ind_summary UNIQUE (jng_biz_crtr_yr, tpbiz_mclsf_nm)
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS ftc_key_validation_log (
        log_id INTEGER PRIMARY KEY AUTOINCREMENT,
        jng_biz_crtr_yr TEXT NOT NULL,
        candidate_key_name TEXT NOT NULL,
        key_fields TEXT NOT NULL,
        total_records INTEGER NOT NULL,
        distinct_keys INTEGER NOT NULL,
        duplicate_keys_count INTEGER NOT NULL,
        duplicate_records_count INTEGER NOT NULL,
        is_unique INTEGER NOT NULL,
        tested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS ftc_id_stability_metrics (
        metric_id INTEGER PRIMARY KEY AUTOINCREMENT,
        transition_period TEXT NOT NULL,
        prior_year TEXT NOT NULL,
        current_year TEXT NOT NULL,
        prior_year_total_brands INTEGER NOT NULL,
        current_year_total_brands INTEGER NOT NULL,
        common_surviving_brands INTEGER NOT NULL,
        persistence_rate_pct REAL NOT NULL,
        new_entry_brands INTEGER NOT NULL,
        exit_brands INTEGER NOT NULL,
        reappearing_brands INTEGER DEFAULT 0,
        hq_changed_brands INTEGER NOT NULL,
        hq_change_rate_pct REAL NOT NULL,
        calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    conn.commit()
    conn.close()

def fetch_api(year: str, page_no: int, num_of_rows: int = 100):
    params = {
        "serviceKey": api_key,
        "pageNo": str(page_no),
        "numOfRows": str(num_of_rows),
        "resultType": "json",
        "jngBizCrtrYr": str(year)
    }
    encoded = urllib.parse.urlencode(params)
    url = f"{ENDPOINT}?{encoded}"
    
    t0 = time.time()
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        latency_ms = int((time.time() - t0) * 1000)
        status_code = resp.getcode()
        raw_text = resp.read().decode("utf-8", errors="replace")
        
    body = json.loads(raw_text)
    return body, status_code, latency_ms

def extract_items(body):
    items = body.get("items", [])
    if isinstance(items, dict):
        items = items.get("item", [])
    if isinstance(items, dict):
        items = [items]
    if not isinstance(items, list):
        items = []
    return items

def to_int(val, default=0):
    if val is None or val == "":
        return default
    try:
        return int(float(str(val).replace(",", "").strip()))
    except Exception:
        return default

def to_float(val, default=None):
    if val is None or val == "":
        return default
    try:
        return float(str(val).replace(",", "").strip())
    except Exception:
        return default

def get_live_total_count(year: str):
    body, status_code, _ = fetch_api(year, 1, 1)
    if status_code != 200:
        raise RuntimeError(f"HTTP status {status_code} when querying totalCount for {year}")
    total_count = int(body.get("totalCount", 0))
    return total_count

def process_year(year: str, db_path: Path):
    print(f"\n=======================================================")
    print(f"[*] Starting ingestion for Reference Year: {year}")
    print(f"=======================================================")
    
    # 1. Pre-ingestion Live totalCount query
    pre_total_count = get_live_total_count(year)
    total_pages = math.ceil(pre_total_count / 100)
    print(f"[*] [PRE-CHECK] Live totalCount for {year}: {pre_total_count} records ({total_pages} pages expected)")
    
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("PRAGMA busy_timeout = 30000;")
    
    # Record initial audit log
    cur.execute("""
        INSERT INTO ftc_ingestion_audit_logs (
            jng_biz_crtr_yr, pre_total_count, total_pages_expected, status
        ) VALUES (?, ?, ?, 'IN_PROGRESS')
    """, (year, pre_total_count, total_pages))
    audit_id = cur.lastrowid
    conn.commit()

    # Recovery: Set any dangling PENDING from previous run to RETRY
    cur.execute("""
        UPDATE ftc_ingestion_checkpoints
        SET status = 'RETRY', error_message = 'Interrupted: Recovered from dangling PENDING state', updated_at = CURRENT_TIMESTAMP
        WHERE jng_biz_crtr_yr = ? AND status = 'PENDING'
    """, (year,))
    recovered = cur.rowcount
    if recovered > 0:
        print(f"[*] Recovered {recovered} dangling PENDING pages to RETRY for {year}")
    conn.commit()

    # Page ingestion loop with priority queue
    completed_pages = 0
    while True:
        # Priority 1: FAILED or RETRY with retry_count < MAX_PAGE_RETRIES
        cur.execute("""
            SELECT page_no, retry_count FROM ftc_ingestion_checkpoints
            WHERE jng_biz_crtr_yr = ? AND status IN ('FAILED', 'RETRY') AND retry_count < ?
            ORDER BY page_no ASC LIMIT 1
        """, (year, MAX_PAGE_RETRIES))
        row = cur.fetchone()
        
        target_page = None
        current_retry = 0
        if row:
            target_page, current_retry = row[0], row[1]
        else:
            # Priority 2: Unattempted pages (1 to total_pages)
            cur.execute("SELECT page_no FROM ftc_ingestion_checkpoints WHERE jng_biz_crtr_yr = ?", (year,))
            attempted = set(r[0] for r in cur.fetchall())
            for p in range(1, total_pages + 1):
                if p not in attempted:
                    target_page = p
                    current_retry = 0
                    break
                    
        if target_page is None:
            # Check if all pages are SUCCESS
            cur.execute("""
                SELECT COUNT(*) FROM ftc_ingestion_checkpoints
                WHERE jng_biz_crtr_yr = ? AND status = 'SUCCESS' AND page_no BETWEEN 1 AND ?
            """, (year, total_pages))
            success_count = cur.fetchone()[0]
            if success_count == total_pages:
                print(f"[+] All {total_pages} pages succeeded for {year}!")
                break
            else:
                # Fatal retry limit check
                cur.execute("""
                    SELECT page_no, error_message FROM ftc_ingestion_checkpoints
                    WHERE jng_biz_crtr_yr = ? AND status IN ('FAILED', 'RETRY') AND retry_count >= ?
                """, (year, MAX_PAGE_RETRIES))
                failed_rows = cur.fetchall()
                if failed_rows:
                    cur.execute("UPDATE ftc_ingestion_audit_logs SET status = 'FAILED' WHERE audit_id = ?", (audit_id,))
                    conn.commit()
                    conn.close()
                    raise RuntimeError(f"Pages exceeded max retries {MAX_PAGE_RETRIES}: {failed_rows}")

        # Mark checkpoint as PENDING
        cur.execute("""
            INSERT INTO ftc_ingestion_checkpoints (
                jng_biz_crtr_yr, page_no, num_of_rows, status, retry_count
            ) VALUES (?, ?, 100, 'PENDING', ?)
            ON CONFLICT(jng_biz_crtr_yr, page_no) DO UPDATE SET
                status = 'PENDING', retry_count = ?, updated_at = CURRENT_TIMESTAMP
        """, (year, target_page, current_retry, current_retry))
        conn.commit()

        # Fetch page with exponential backoff on transient errors
        fetch_success = False
        body = None
        status_code = None
        latency_ms = 0
        
        for attempt in range(MAX_PAGE_RETRIES):
            try:
                body, status_code, latency_ms = fetch_api(year, target_page, 100)
                if status_code == 200 and (body.get("resultCode") == "00" or body.get("header", {}).get("resultCode") == "00"):
                    fetch_success = True
                    break
                else:
                    err_msg = f"API error HTTP {status_code}, code {body.get('resultCode')}"
            except Exception as e:
                err_msg = mask_text(str(e))
                
            delay = BASE_RETRY_DELAY * (2 ** attempt) + random.uniform(0.1, 0.5)
            print(f"    [!] Page {target_page} attempt {attempt+1} failed ({err_msg}). Retrying in {delay:.2f}s...")
            time.sleep(delay)
            
        if not fetch_success:
            # Update checkpoint to RETRY or FAILED
            new_retry = current_retry + 1
            new_status = 'FAILED' if new_retry >= MAX_PAGE_RETRIES else 'RETRY'
            cur.execute("""
                UPDATE ftc_ingestion_checkpoints
                SET status = ?, retry_count = ?, error_message = ?, updated_at = CURRENT_TIMESTAMP
                WHERE jng_biz_crtr_yr = ? AND page_no = ?
            """, (new_status, new_retry, err_msg, year, target_page))
            conn.commit()
            if new_status == 'FAILED':
                cur.execute("UPDATE ftc_ingestion_audit_logs SET status = 'FAILED' WHERE audit_id = ?", (audit_id,))
                conn.commit()
                conn.close()
                raise RuntimeError(f"Fatal: Page {target_page} failed after {MAX_PAGE_RETRIES} attempts.")
            continue

        # Page atomic database transaction
        items = extract_items(body)
        try:
            cur.execute("BEGIN IMMEDIATE;")
            
            # 1. Delete-before-insert for idempotency
            cur.execute("DELETE FROM ftc_brand_macro_records WHERE jng_biz_crtr_yr = ? AND source_page_no = ?", (year, target_page))
            
            # 2. Raw response preservation
            cur.execute("""
                INSERT INTO ftc_raw_api_responses (
                    jng_biz_crtr_yr, page_no, num_of_rows, http_status,
                    result_code, total_count, item_count, payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(jng_biz_crtr_yr, page_no) DO UPDATE SET
                    http_status = excluded.http_status,
                    payload_json = excluded.payload_json,
                    item_count = excluded.item_count,
                    fetched_at = CURRENT_TIMESTAMP
            """, (year, target_page, 100, status_code, body.get("resultCode", "00"),
                  int(body.get("totalCount", 0)), len(items), json.dumps(body, ensure_ascii=False)))
                  
            # 3. Clean records batch insertion
            for row_idx, it in enumerate(items):
                canonical_str = json.dumps(it, sort_keys=True, ensure_ascii=False)
                fingerprint = hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()
                
                jng_amt = to_float(it.get("jngBzmnJngAmt"))
                edu_amt = to_float(it.get("jngBzmnEduAmt"))
                grnte_amt = to_float(it.get("jngBzmnGrnteAmt"))
                etc_amt = to_float(it.get("jngBzmnEtcAmt"))
                depst_amt = to_float(it.get("depstAmt"))
                intrr_amt = to_float(it.get("intrrAmt"))
                
                calc_diff = None
                calc_matched = 0
                if depst_amt is not None and jng_amt is not None and edu_amt is not None and grnte_amt is not None:
                    calc_diff = round(depst_amt - (jng_amt + edu_amt + grnte_amt), 2)
                    calc_matched = 1 if abs(calc_diff) < 0.001 else 0
                    
                tentative_cost = (depst_amt or 0.0) + (etc_amt or 0.0) + (intrr_amt or 0.0)
                
                cur.execute("""
                    INSERT INTO ftc_brand_macro_records (
                        source_page_no, source_row_index, row_fingerprint,
                        als_brand_mng_no, als_jnghq_mng_no, jng_biz_crtr_yr,
                        jnghq_rgn_nm, jng_biz_strt_ymd, tpbiz_mclsf_nm,
                        frcs_cnt, dms_cnt, prvyr_frcs_cnt, prvyr_dms_cnt,
                        jng_bzmn_jng_amt, jng_bzmn_edu_amt, jng_bzmn_grnte_amt, jng_bzmn_etc_amt,
                        depst_amt, unit_area_intrr_amt, intrr_amt,
                        prvyr_jng_bzmn_jng_amt, prvyr_jng_bzmn_edu_amt, prvyr_jng_bzmn_grnte_amt, prvyr_jng_bzmn_etc_amt,
                        prvyr_depst_amt, prvyr_unit_area_intrr_amt, prvyr_intrr_amt,
                        frst_ctrt_yycnt, prlg_ctrt_yycnt, stor_crtr_area,
                        prvyr_frst_ctrt_yycnt, prvyr_prlg_ctrt_yycnt, prvyr_stor_crtr_area,
                        fyr, avg_sls_amt, area_unit_avg_sls_amt,
                        prvyr_fyr, prvyr_avg_sls_amt, prvyr_area_unit_avg_sls_amt,
                        calc_depst_diff, calc_depst_is_matched, tentative_startup_cost_thousand,
                        startup_cost_calc_method
                    ) VALUES (
                        ?, ?, ?,
                        ?, ?, ?,
                        ?, ?, ?,
                        ?, ?, ?, ?,
                        ?, ?, ?, ?,
                        ?, ?, ?,
                        ?, ?, ?, ?,
                        ?, ?, ?,
                        ?, ?, ?,
                        ?, ?, ?,
                        ?, ?, ?,
                        ?, ?, ?,
                        ?, ?, ?,
                        ?
                    )
                """, (
                    target_page, row_idx, fingerprint,
                    str(it.get("alsBrandMngNo", "")), str(it.get("alsJnghqMngNo", "")), str(it.get("jngBizCrtrYr", year)),
                    it.get("jnghqRgnNm"), it.get("jngBizStrtYmd"), str(it.get("tpbizMclsfNm", "")),
                    to_int(it.get("frcsCnt")), to_int(it.get("dmsCnt")), to_int(it.get("prvyrFrcsCnt")), to_int(it.get("prvyrDmsCnt")),
                    jng_amt, edu_amt, grnte_amt, etc_amt,
                    depst_amt, to_float(it.get("unitAreaIntrrAmt")), intrr_amt,
                    to_float(it.get("prvyrJngBzmnJngAmt")), to_float(it.get("prvyrJngBzmnEduAmt")), to_float(it.get("prvyrJngBzmnGrnteAmt")), to_float(it.get("prvyrJngBzmnEtcAmt")),
                    to_float(it.get("prvyrDepstAmt")), to_float(it.get("prvyrUnitAreaIntrrAmt")), to_float(it.get("prvyrIntrrAmt")),
                    to_float(it.get("frstCtrtYycnt")), to_float(it.get("prlgCtrtYycnt")), to_float(it.get("storCrtrArea")),
                    to_float(it.get("prvyrFrstCtrtYycnt")), to_float(it.get("prvyrPrlgCtrtYycnt")), to_float(it.get("prvyrStorCrtrArea")),
                    it.get("fyr"), to_float(it.get("avgSlsAmt")), to_float(it.get("areaUnitAvgSlsAmt")),
                    it.get("prvyrFyr"), to_float(it.get("prvyrAvgSlsAmt")), to_float(it.get("prvyrAreaUnitAvgSlsAmt")),
                    calc_diff, calc_matched, tentative_cost,
                    "DEPST_SUM"
                ))

            # 4. Checkpoint success update in same transaction
            cur.execute("""
                INSERT INTO ftc_ingestion_checkpoints (
                    jng_biz_crtr_yr, page_no, num_of_rows, status,
                    items_fetched, items_saved, latency_ms, error_message
                ) VALUES (?, ?, 100, 'SUCCESS', ?, ?, ?, NULL)
                ON CONFLICT(jng_biz_crtr_yr, page_no) DO UPDATE SET
                    status = 'SUCCESS',
                    items_fetched = excluded.items_fetched,
                    items_saved = excluded.items_saved,
                    latency_ms = excluded.latency_ms,
                    error_message = NULL,
                    updated_at = CURRENT_TIMESTAMP
            """, (year, target_page, len(items), len(items), latency_ms))
            
            cur.execute("COMMIT;")
            completed_pages += 1
            if completed_pages % 10 == 0 or target_page == total_pages:
                print(f"    [P.{target_page:02d}/{total_pages:02d}] Saved {len(items)} items ({latency_ms}ms)")
                
        except Exception as db_err:
            cur.execute("ROLLBACK;")
            err_text = mask_text(str(db_err))
            print(f"    [!] DB Error on page {target_page}: {err_text}")
            cur.execute("""
                UPDATE ftc_ingestion_checkpoints
                SET status = 'RETRY', retry_count = retry_count + 1, error_message = ?, updated_at = CURRENT_TIMESTAMP
                WHERE jng_biz_crtr_yr = ? AND page_no = ?
            """, (err_text, year, target_page))
            conn.commit()
            
        time.sleep(RATE_LIMIT_DELAY)

    # 3. Post-ingestion Live totalCount query & Audit Verification
    post_total_count = get_live_total_count(year)
    cur.execute("SELECT COUNT(*) FROM ftc_brand_macro_records WHERE jng_biz_crtr_yr = ?", (year,))
    saved_records = cur.fetchone()[0]
    cur.execute("SELECT SUM(items_fetched), COUNT(*) FROM ftc_ingestion_checkpoints WHERE jng_biz_crtr_yr = ? AND status = 'SUCCESS'", (year,))
    row = cur.fetchone()
    fetched_records = row[0]
    success_pages = row[1]
    
    print(f"\n[*] [POST-AUDIT] Year {year}:")
    print(f"    Pre totalCount:   {pre_total_count}")
    print(f"    Post totalCount:  {post_total_count}")
    print(f"    Fetched Records:  {fetched_records}")
    print(f"    Saved Records:    {saved_records}")
    print(f"    Success Pages:    {success_pages}/{total_pages}")
    
    discrepancy = abs(saved_records - pre_total_count)
    if pre_total_count != post_total_count:
        print(f"    [!] WARNING: UNSTABLE_SNAPSHOT detected! (Pre: {pre_total_count} != Post: {post_total_count})")
        cur.execute("""
            UPDATE ftc_ingestion_audit_logs
            SET post_total_count = ?, total_pages_succeeded = ?, total_records_saved = ?,
                discrepancy_count = ?, status = 'UNSTABLE_SNAPSHOT', completed_at = CURRENT_TIMESTAMP
            WHERE audit_id = ?
        """, (post_total_count, success_pages, saved_records, discrepancy, audit_id))
        conn.commit()
        conn.close()
        raise RuntimeError(f"Snapshot unstable for year {year}: pre {pre_total_count} != post {post_total_count}")
        
    if saved_records != pre_total_count or success_pages != total_pages:
        print(f"    [!] ERROR: Discrepancy detected! (Saved: {saved_records}, Expected: {pre_total_count})")
        cur.execute("""
            UPDATE ftc_ingestion_audit_logs
            SET post_total_count = ?, total_pages_succeeded = ?, total_records_saved = ?,
                discrepancy_count = ?, status = 'FAILED', completed_at = CURRENT_TIMESTAMP
            WHERE audit_id = ?
        """, (post_total_count, success_pages, saved_records, discrepancy, audit_id))
        conn.commit()
        conn.close()
        raise RuntimeError(f"Audit reconciliation failed for {year}: saved {saved_records} != {pre_total_count}")
        
    cur.execute("""
        UPDATE ftc_ingestion_audit_logs
        SET post_total_count = ?, total_pages_succeeded = ?, total_records_saved = ?,
            discrepancy_count = 0, status = 'COMPLETED', completed_at = CURRENT_TIMESTAMP
        WHERE audit_id = ?
    """, (post_total_count, success_pages, saved_records, audit_id))
    conn.commit()
    conn.close()
    print(f"[+] Year {year} completed successfully with 100% audit match!\n")

def run_all():
    t_start = time.time()
    print(f"[*] Starting Phase 4F Multi-Year Ingestion Pipeline (2023 ~ 2026)")
    print(f"[*] Target DB: {DB_PATH}")
    init_db(DB_PATH)
    
    for yr in TARGET_YEARS:
        process_year(yr, DB_PATH)
        
    t_end = time.time()
    elapsed_sec = int(t_end - t_start)
    print(f"\n=======================================================")
    print(f"[+] All 4 Years Ingested Successfully in {elapsed_sec // 60}m {elapsed_sec % 60}s!")
    print(f"=======================================================\n")

if __name__ == "__main__":
    run_all()
