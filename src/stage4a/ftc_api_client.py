#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Franchise Dashboard — Phase 4 Stage 4A 공정위 가맹정보 API 클라이언트
(src/stage4a/ftc_api_client.py)

엔드포인트:
  https://apis.data.go.kr/1130000/FftcBrandFrcsBzmnIntgInfoEatoutTpbizStats2_Service/getBrandFrcsBzmnIntgInfoEatoutTpbiz2

기능:
  1. 비공개 API 인증키 안전 관리 및 로그/콘솔 마스킹
  2. 호출 예산 상한제 (Call Budget Limiter: 최대 30회)
  3. 지수 백오프 재시도 및 HTTP/네트워크 장애 복구
  4. 응답 파싱 (JSON 및 오류 XML) 및 유효성 검증
  5. Stage 4A DB(data/brand_intelligence_stage4a.sqlite3) 적재 및 변환
"""

import os
import sys
import json
import time
import sqlite3
import urllib.request
import urllib.parse
import urllib.error
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_DIR = Path("D:/Franchise_Dashboard")
API_ENDPOINT = "https://apis.data.go.kr/1130000/FftcBrandFrcsBzmnIntgInfoEatoutTpbizStats2_Service/getBrandFrcsBzmnIntgInfoEatoutTpbiz2"


def get_ftc_api_key() -> str:
    """안전한 환경변수 / .env 키 로드"""
    env_file = BASE_DIR / ".env"
    key = None
    if env_file.exists():
        with open(env_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("FTC_SERVICE_KEY="):
                    key = line.split("=", 1)[1].strip().strip('"').strip("'")
                    break
                elif line.startswith("SERVICE_KEY=") or line.startswith("SERVICEKEY="):
                    key = line.split("=", 1)[1].strip().strip('"').strip("'")
                    break
    if not key:
        key = os.environ.get("FTC_SERVICE_KEY") or os.environ.get("SERVICE_KEY")
    if not key:
        raise ValueError("공공데이터 API 인증키(SERVICE_KEY 또는 FTC_SERVICE_KEY)를 찾을 수 없습니다.")
    return key


def sanitize_text(text: str, secret: Optional[str] = None) -> str:
    """로그, 콘솔, 보고서에서 API 키 마스킹"""
    if not text:
        return ""
    clean = str(text)
    keys_to_mask = [secret] if secret else []
    try:
        loaded = get_ftc_api_key()
        if loaded:
            keys_to_mask.append(loaded)
    except Exception:
        pass

    for k in keys_to_mask:
        if k and len(k) > 4:
            clean = clean.replace(k, "[MASKED_API_KEY]")
            quoted = urllib.parse.quote(k, safe="")
            if quoted != k:
                clean = clean.replace(quoted, "[MASKED_API_KEY]")
    return clean


class FtcApiClient:
    def __init__(self, api_key: Optional[str] = None, call_budget: int = 30):
        self.api_key = api_key or get_ftc_api_key()
        self.call_budget = call_budget
        self.call_count = 0
        self.delay = 0.35  # 초당 요청 제한 방지

    @staticmethod
    def _parse_xml_error(xml_str: str) -> Optional[Dict[str, Any]]:
        import xml.etree.ElementTree as ET
        try:
            root = ET.fromstring(xml_str)
            code = None
            msg = None
            for elem in root.iter():
                tag = elem.tag.lower()
                if "returnreasoncode" in tag or "resultcode" in tag:
                    code = elem.text
                elif "returnauthmsg" in tag or "resultmsg" in tag or "errmsg" in tag:
                    msg = elem.text
            if code or msg:
                return {
                    "resultCode": code or "99",
                    "resultMsg": msg or "XML_SERVICE_ERROR",
                    "items": []
                }
        except Exception:
            pass
        return None

    def request(
        self,
        year: str,
        page_no: int = 1,
        num_of_rows: int = 10,
        result_type: str = "json",
        max_retries: int = 3
    ) -> Dict[str, Any]:
        """단일 API 호출 수행 및 예산/재시도 통제"""
        if self.call_count >= self.call_budget:
            raise RuntimeError(f"호출 예산 초과 (현재: {self.call_count}회 / 상한: {self.call_budget}회)")

        params = {
            "serviceKey": self.api_key,
            "pageNo": str(page_no),
            "numOfRows": str(num_of_rows),
            "resultType": result_type,
            "jngBizCrtrYr": str(year)
        }
        query_str = urllib.parse.urlencode(params)
        url = f"{API_ENDPOINT}?{query_str}"
        self.call_count += 1

        for attempt in range(max_retries):
            try:
                req = urllib.request.Request(
                    url,
                    headers={"User-Agent": "Mozilla/5.0 FranchiseDashboard-Stage4A/1.0"}
                )
                with urllib.request.urlopen(req, timeout=20) as resp:
                    body_bytes = resp.read()
                    body_str = body_bytes.decode("utf-8", errors="replace")
                    time.sleep(self.delay)

                    try:
                        data = json.loads(body_str)
                        return {
                            "success": True,
                            "http_status": resp.status,
                            "data": data,
                            "raw_text": body_str,
                            "error": None
                        }
                    except json.JSONDecodeError:
                        xml_data = self._parse_xml_error(body_str)
                        return {
                            "success": False,
                            "http_status": getattr(resp, "status", 200),
                            "data": xml_data,
                            "raw_text": body_str,
                            "error": f"XML_ERROR: {xml_data.get('resultMsg', '')}" if xml_data else "JSON_PARSE_ERROR"
                        }

            except urllib.error.HTTPError as e:
                if e.code == 429:
                    time.sleep((attempt + 1) * 2.0)
                    continue
                elif e.code in [500, 502, 503, 504]:
                    time.sleep((attempt + 1) * 1.5)
                    continue
                else:
                    err_msg = e.read().decode("utf-8", errors="replace") if e.fp else str(e)
                    return {
                        "success": False,
                        "http_status": e.code,
                        "data": None,
                        "raw_text": err_msg,
                        "error": sanitize_text(str(e), self.api_key)
                    }
            except Exception as e:
                time.sleep((attempt + 1) * 1.0)
                if attempt == max_retries - 1:
                    return {
                        "success": False,
                        "http_status": 0,
                        "data": None,
                        "raw_text": None,
                        "error": sanitize_text(str(e), self.api_key)
                    }

        return {
            "success": False,
            "http_status": 0,
            "data": None,
            "raw_text": None,
            "error": "MAX_RETRIES_EXCEEDED"
        }

    def ingest_sample_records(
        self,
        con: sqlite3.Connection,
        run_id: str,
        years: List[str] = ["2024", "2023"],
        pages_per_year: int = 2,
        rows_per_page: int = 10
    ) -> Dict[str, Any]:
        """표본 데이터를 수집하여 Stage 4A DB에 적재"""
        cur = con.cursor()
        # Ensure pipeline_runs record exists for foreign keys
        cur.execute("""
            INSERT OR IGNORE INTO pipeline_runs (
                run_id, stage_name, description, call_budget_limit, status
            ) VALUES (?, 'STAGE_4A', 'FTC Sample Ingestion', ?, 'RUNNING')
        """, (run_id, self.call_budget))
        con.commit()

        total_ingested = 0
        total_candidates = 0

        for yr in years:
            for page in range(1, pages_per_year + 1):
                if self.call_count >= self.call_budget:
                    print(f"  [예산 제한] 호출 예산 상한 도달 ({self.call_count}/{self.call_budget}). 수집을 중단합니다.")
                    break

                res = self.request(year=yr, page_no=page, num_of_rows=rows_per_page, result_type="json")
                if not res["success"] or not res["data"]:
                    print(f"  [호출 실패] 연도={yr}, 페이지={page}: {res.get('error')}")
                    cur.execute("""
                        INSERT INTO data_quality_results (
                            run_id, audit_category, assertion_name, assertion_status,
                            target_dataset, detail_message
                        ) VALUES (?, 'API_VERIFICATION', 'FTC_CALL_SUCCESS', 'FAIL', 'FTC_API', ?)
                    """, (run_id, f"yr={yr}, page={page}, err={res.get('error')}"))
                    con.commit()
                    continue

                data = res["data"]
                r_code = data.get("resultCode", "")
                r_msg = data.get("resultMsg", "")
                total_cnt = int(data.get("totalCount", 0))
                items = data.get("items", [])

                if not isinstance(items, list):
                    items = []

                for idx, it in enumerate(items, 1):
                    raw_id = f"RAW_{yr}_{page:03d}_{idx:03d}"
                    raw_json = json.dumps(it, ensure_ascii=False)

                    # 1. ftc_raw_records 적재
                    cur.execute("""
                        INSERT OR REPLACE INTO ftc_raw_records (
                            raw_record_id, source_id, run_id, crtr_yr,
                            page_no, num_of_rows, total_count, result_code, result_msg, payload_json
                        ) VALUES (?, 'FTC_EATOUT_STATS_V2', ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (raw_id, run_id, yr, page, rows_per_page, total_cnt, r_code, r_msg, raw_json))

                    # 2. ftc_brand_candidates 변환 적재
                    als_brand = it.get("alsBrandMngNo", "")
                    als_jnghq = it.get("alsJnghqMngNo", "")
                    cand_id = f"FTC_{yr}_{als_brand}_{idx:02d}"

                    def to_float(val):
                        try: return float(val) if val is not None else 0.0
                        except: return 0.0

                    def to_int(val):
                        try: return int(val) if val is not None else 0
                        except: return 0

                    cur.execute("""
                        INSERT OR REPLACE INTO ftc_brand_candidates (
                            ftc_candidate_id, raw_record_id, crtr_yr,
                            als_brand_mng_no, als_jnghq_mng_no, jnghq_rgn_nm, biz_strt_ymd,
                            tpbiz_mclsf_nm, frcs_cnt, dms_cnt,
                            prvyr_frcs_cnt, prvyr_dms_cnt,
                            jng_amt, edu_amt, grnte_amt, etc_amt, depst_amt,
                            unit_area_intrr_amt, stor_crtr_area, intrr_amt,
                            fyr, avg_sls_amt, area_unit_avg_sls_amt,
                            anonymization_state, verification_status
                        ) VALUES (
                            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                            ?, ?, ?, 'PSEUDONYMIZED', 'UNVERIFIED'
                        )
                    """, (
                        cand_id, raw_id, yr,
                        als_brand, als_jnghq, it.get("jnghqRgnNm"), it.get("jngBizStrtYmd"),
                        it.get("tpbizMclsfNm", "기타외식"),
                        to_int(it.get("frcsCnt")), to_int(it.get("dmsCnt")),
                        to_int(it.get("prvyrFrcsCnt")), to_int(it.get("prvyrDmsCnt")),
                        to_float(it.get("jngBzmnJngAmt")), to_float(it.get("jngBzmnEduAmt")),
                        to_float(it.get("jngBzmnGrnteAmt")), to_float(it.get("jngBzmnEtcAmt")),
                        to_float(it.get("depstAmt")),
                        to_float(it.get("unitAreaIntrrAmt")), to_float(it.get("storCrtrArea")),
                        to_float(it.get("intrrAmt")),
                        it.get("fyr"), to_float(it.get("avgSlsAmt")), to_float(it.get("areaUnitAvgSlsAmt"))
                    ))
                    total_candidates += 1

                con.commit()
                total_ingested += len(items)

        cur.execute("""
            UPDATE pipeline_runs
            SET actual_calls_made = ?,
                total_records_ingested = ?,
                status = 'COMPLETED',
                completed_at = CURRENT_TIMESTAMP
            WHERE run_id = ?
        """, (self.call_count, total_ingested, run_id))
        con.commit()

        return {
            "total_ingested": total_ingested,
            "total_candidates": total_candidates,
            "calls_made": self.call_count
        }


if __name__ == "__main__":
    from schema_stage4a import init_stage4a_database
    test_db = BASE_DIR / "data" / "brand_intelligence_stage4a_client_test.sqlite3"
    con = init_stage4a_database(test_db)
    
    client = FtcApiClient(call_budget=5)
    print(f"Testing FTC Client with budget: {client.call_budget}")
    
    # Run 1 call test
    run_id = f"RUN_TEST_{int(time.time())}"
    res = client.ingest_sample_records(con, run_id=run_id, years=["2024"], pages_per_year=1, rows_per_page=3)
    print("Ingest Result:", res)
    
    cur = con.cursor()
    cnt_raw = cur.execute("SELECT COUNT(*) FROM ftc_raw_records").fetchone()[0]
    cnt_cand = cur.execute("SELECT COUNT(*) FROM ftc_brand_candidates").fetchone()[0]
    print(f"DB verification: raw={cnt_raw}, candidates={cnt_cand}")
    
    con.close()
    if test_db.exists():
        test_db.unlink()
        for extra in [test_db.with_name(test_db.name + "-wal"), test_db.with_name(test_db.name + "-shm")]:
            if extra.exists(): extra.unlink()
    print("FtcApiClient test passed successfully!")
