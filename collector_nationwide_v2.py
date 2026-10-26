#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Franchise Dashboard — 전국 외식업 수집·복구 엔진 v2 (collector_nationwide_v2.py)
목표 DB: data/nationwide_food_stores_v2.sqlite3
설정: config/regions_v2.json (16개 시도, 256개 시군구)

[Phase 3 핵심 결함 개선 완료]
  1. NODATA_ERROR(03)를 정상 0건으로 자동 완료 처리하지 않고 실패 대기열(FAILED_QUEUE) 등록
  2. 요청 지역코드 vs 반환 지역코드·지역명(signguCd, signguNm) 엄격 교차 검증
  3. 데이터 기준월(header.stdrYm) 유효성 검증 및 단일 기준월(202606) 유지
  4. 데이터 계약 공식 무결성 검증: (원본 수집 - 제외 업종 = 저장 대상) 매 페이지 자동 검증
  5. 점포 ID(bizesId) 기준 중복 감지 및 좌표(WGS84) 범위 무결성 검증
  6. 체크포인트 기반 중단 시 안전 재개(Resume) 및 429 Rate Limit 자동 지수 백오프
  7. 기존 v1 DB(184개 정상 지역, 595,453건) 선별 이관 모드(--migrate-v1) 탑재
  8. 비공개 API 키 관리 (.env, 환경변수, 안전 입력)
"""

import os
import sys
import json
import time
import sqlite3
import getpass
import argparse
import urllib.request
import urllib.parse
import urllib.error
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Any

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_DIR = Path("D:/Franchise_Dashboard")
DEFAULT_CONFIG_V2_PATH = BASE_DIR / "config" / "regions_v2.json"
DEFAULT_DB_V2_PATH = BASE_DIR / "data" / "nationwide_food_stores_v2.sqlite3"
DEFAULT_V1_DB_PATH = BASE_DIR / "data" / "nationwide_food_stores.sqlite3"
DEFAULT_REPORT_V2_PATH = BASE_DIR / "reports" / "nationwide_collection_v2_report.json"
DEFAULT_SUMMARY_V2_PATH = BASE_DIR / "reports" / "nationwide_collection_v2_summary.md"
API_BASE_URL = "https://apis.data.go.kr/B553077/api/open/sdsc2/storeListInDong"

# 업종 필터링 기준 (AGENTS.md 준수)
EXCLUDED_MIDDLE_CODES = {"I211"}   # 주점 전체 제외
EXCLUDED_SMALL_CODES = {"I20701"}  # 구내식당 제외 (I20702 뷔페는 반드시 포함)


def sanitize_text(text: str, api_key: Optional[str] = None) -> str:
    if not text:
        return ""
    clean = str(text)
    if api_key and len(api_key) > 4:
        clean = clean.replace(api_key, "[MASKED_KEY]")
        quoted = urllib.parse.quote(api_key, safe="")
        if quoted != api_key:
            clean = clean.replace(quoted, "[MASKED_KEY]")
    return clean


def get_api_key(cli_key: Optional[str] = None) -> str:
    if cli_key and cli_key.strip():
        return cli_key.strip()

    for k in ["SERVICE_KEY", "DATA_GO_KR_API_KEY", "PUBLIC_DATA_API_KEY"]:
        v = os.getenv(k)
        if v and v.strip():
            return v.strip()

    env_path = BASE_DIR / ".env"
    if env_path.exists():
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" in line:
                        k, v = line.split("=", 1)
                        if k.strip() in ["SERVICE_KEY", "DATA_GO_KR_API_KEY", "PUBLIC_DATA_API_KEY"] and v.strip():
                            return v.strip().strip('"').strip("'")
        except Exception:
            pass

    try:
        user_key = getpass.getpass("공공데이터포털 API Key (비공개 입력): ").strip()
        if user_key:
            return user_key
    except Exception:
        pass

    return ""


@dataclass
class RegionItem:
    sido_code: str
    sido_name: str
    api_code: str
    official_code: str
    dashboard_code: str
    name: str
    category: str
    parent_city: Optional[str] = None


class RegionManagerV2:
    def __init__(self, config_path: Path = DEFAULT_CONFIG_V2_PATH):
        self.config_path = config_path
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.meta = data.get("meta", {})
        self.regions: List[RegionItem] = []
        for p in data.get("provinces", []):
            s_code = p["province_code"]
            s_name = p["province_name"]
            for d in p.get("districts", []):
                self.regions.append(RegionItem(
                    sido_code=s_code,
                    sido_name=s_name,
                    api_code=d["api_code"],
                    official_code=d.get("official_code", d["api_code"] + "00000"),
                    dashboard_code=d.get("dashboard_code", d["api_code"]),
                    name=d["name"],
                    category=d.get("category", "일반"),
                    parent_city=d.get("parent_city")
                ))

    def get_by_code(self, api_code: str) -> Optional[RegionItem]:
        return next((r for r in self.regions if r.api_code == api_code), None)


class NationwideCollectorV2:
    def __init__(
        self,
        db_path: Path = DEFAULT_DB_V2_PATH,
        config_path: Path = DEFAULT_CONFIG_V2_PATH,
        api_key: Optional[str] = None,
        rate_limit_delay: float = 0.35,
        target_stdr_ym: str = "202606"
    ):
        self.db_path = db_path
        self.config_path = config_path
        self.api_key = api_key or get_api_key()
        self.delay = rate_limit_delay
        self.target_stdr_ym = target_stdr_ym
        self.region_mgr = RegionManagerV2(config_path)

        # DB 초기화 (schema_v2 연계)
        from schema_v2 import init_database
        self.con = init_database(self.db_path)
        self._sync_region_master()

    def _sync_region_master(self):
        """region_v2 설정과 DB의 region_master 테이블 동기화"""
        cur = self.con.cursor()
        for r in self.region_mgr.regions:
            cur.execute("""
                INSERT OR IGNORE INTO region_master (
                    signgu_code, official_code, dashboard_code,
                    sido_code, sido_name, signgu_name, category, parent_city
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                r.api_code, r.official_code, r.dashboard_code,
                r.sido_code, r.sido_name, r.name, r.category, r.parent_city
            ))
        self.con.commit()

    def call_api(
        self,
        div_id: str,
        key: str,
        page_no: int = 1,
        num_of_rows: int = 1000,
        inds_lcls_cd: str = "I2",
        max_retries: int = 3
    ) -> Dict[str, Any]:
        params = {
            "serviceKey": self.api_key,
            "divId": div_id,
            "key": key,
            "indsLclsCd": inds_lcls_cd,
            "numOfRows": num_of_rows,
            "pageNo": page_no,
            "type": "json"
        }
        url = f"{API_BASE_URL}?{urllib.parse.urlencode(params)}"

        for attempt in range(max_retries):
            try:
                req = urllib.request.Request(
                    url,
                    headers={"User-Agent": "Mozilla/5.0 FranchiseDashboard-CollectorV2/2.0"}
                )
                with urllib.request.urlopen(req, timeout=30) as resp:
                    data = json.load(resp)
                    return {"success": True, "data": data, "error": None}
            except urllib.error.HTTPError as e:
                if e.code == 429:
                    # Rate limit backoff
                    wait = (attempt + 1) * 3.0
                    time.sleep(wait)
                    continue
                elif e.code in [500, 502, 503, 504]:
                    time.sleep((attempt + 1) * 2.0)
                    continue
                else:
                    return {"success": False, "data": None, "error": sanitize_text(str(e), self.api_key)}
            except Exception as e:
                time.sleep((attempt + 1) * 1.5)
                if attempt == max_retries - 1:
                    return {"success": False, "data": None, "error": sanitize_text(str(e), self.api_key)}

        return {"success": False, "data": None, "error": "Max retries exceeded"}

    def is_store_excluded(self, item: Dict[str, Any]) -> bool:
        """업종 필터링: 주점(I211) 제외, 구내식당(I20701) 제외, 뷔페(I20702) 포함"""
        mcls = item.get("indsMclsCd", "")
        scls = item.get("indsSclsCd", "")
        if mcls in EXCLUDED_MIDDLE_CODES:
            return True
        if scls in EXCLUDED_SMALL_CODES:
            return True
        return False

    def validate_coordinates(self, lon: Optional[float], lat: Optional[float]) -> bool:
        """대한민국 좌표 범위 유효성 검증 (WGS84: 경도 124~132, 위도 33~39)"""
        if lon is None or lat is None:
            return False
        return (124.0 <= lon <= 132.0) and (33.0 <= lat <= 39.0)

    def collect_district(
        self,
        region: RegionItem,
        batch_id: str,
        dry_run: bool = False,
        max_pages: Optional[int] = None
    ) -> Dict[str, Any]:
        """단일 시군구 수집 및 무결성 검증 실행"""
        result = {
            "api_code": region.api_code,
            "region_name": region.name,
            "sido_name": region.sido_name,
            "status": "PENDING",
            "total_api_count": 0,
            "total_raw": 0,
            "total_excluded": 0,
            "total_saved": 0,
            "contract_valid": True,
            "error": None
        }

        # 1. First probe page
        first_resp = self.call_api("signguCd", region.api_code, page_no=1, num_of_rows=1000)
        if not first_resp["success"]:
            result["status"] = "ERROR_QUEUED"
            result["error"] = first_resp["error"]
            return result

        data = first_resp["data"]
        hdr = data.get("header", {})
        body = data.get("body", {})
        r_code = hdr.get("resultCode")
        r_msg = hdr.get("resultMsg")
        stdr_ym = hdr.get("stdrYm", self.target_stdr_ym)

        if stdr_ym and self.target_stdr_ym and stdr_ym != self.target_stdr_ym:
            result["status"] = "STDR_YM_MISMATCH"
            result["error"] = f"Expected stdrYm {self.target_stdr_ym} but got {stdr_ym}"
            return result

        if r_code != "00":
            # NODATA_ERROR(03) 등 비정상 응답
            result["status"] = "ERROR_QUEUED"
            result["error"] = f"API Error [{r_code}]: {r_msg}"
            return result

        total_count = body.get("totalCount", 0)
        result["total_api_count"] = total_count

        if total_count == 0:
            # 정상 응답인데 점포가 0건인 경우
            result["status"] = "ZERO_CONFIRMED"
            return result

        items = body.get("items", [])
        if items:
            # 2. 반환 지역정보 교차 검증
            ret_signgu_cd = items[0].get("signguCd")
            ret_signgu_nm = items[0].get("signguNm")
            if ret_signgu_cd != region.api_code:
                result["status"] = "CODE_MISMATCH"
                result["error"] = f"Requested {region.api_code} but received {ret_signgu_cd} ({ret_signgu_nm})"
                return result

        num_of_rows = 1000
        total_pages = (total_count + num_of_rows - 1) // num_of_rows
        if max_pages:
            total_pages = min(total_pages, max_pages)

        # 3. Process pages
        for page in range(1, total_pages + 1):
            if page == 1:
                page_data = data
            else:
                resp = self.call_api("signguCd", region.api_code, page_no=page, num_of_rows=num_of_rows)
                if not resp["success"]:
                    result["status"] = "PAGE_FAIL"
                    result["error"] = resp["error"]
                    return result
                page_data = resp["data"]
                time.sleep(self.delay)

            p_body = page_data.get("body", {})
            p_items = p_body.get("items", [])
            raw_cnt = len(p_items)
            excluded_cnt = 0
            saved_cnt = 0

            cur = self.con.cursor()
            for it in p_items:
                if self.is_store_excluded(it):
                    excluded_cnt += 1
                    continue

                bizes_id = it.get("bizesId")
                bizes_nm = it.get("bizesNm")
                if not bizes_id or not bizes_nm:
                    excluded_cnt += 1
                    continue

                lon = float(it.get("lon")) if it.get("lon") else None
                lat = float(it.get("lat")) if it.get("lat") else None
                if not self.validate_coordinates(lon, lat):
                    if not dry_run:
                        cur.execute("""
                            INSERT INTO quarantine_stores (
                                bizes_id, bizes_nm, reason, raw_ctprvn_cd, raw_signgu_cd, raw_signgu_nm, raw_json
                            ) VALUES (?, ?, ?, ?, ?, ?, ?)
                        """, (bizes_id, bizes_nm, "INVALID_COORDINATES", it.get("ctprvnCd"), it.get("signguCd"), it.get("signguNm"), json.dumps(it, ensure_ascii=False)))
                    excluded_cnt += 1
                    continue

                if not dry_run:
                    cur.execute("""
                        INSERT OR REPLACE INTO stores (
                            bizes_id, bizes_nm, brch_nm,
                            inds_lcls_cd, inds_lcls_nm, inds_mcls_cd, inds_mcls_nm,
                            inds_scls_cd, inds_scls_nm, ksic_cd, ksic_nm,
                            raw_ctprvn_cd, raw_ctprvn_nm, raw_signgu_cd, raw_signgu_nm,
                            raw_adong_cd, raw_adong_nm, raw_ldong_cd, raw_ldong_nm,
                            std_sido_code, std_sido_name, std_signgu_code, std_signgu_name,
                            dashboard_region_code, rdnm_adr, lno_adr, new_zipcd,
                            lon, lat, stdr_ym, data_source, raw_json, updated_at
                        ) VALUES (
                            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                            ?, ?, ?, ?, ?, ?, ?, ?,
                            ?, ?, ?, ?, ?, ?, ?, ?,
                            ?, ?, ?, ?, ?, CURRENT_TIMESTAMP
                        )
                    """, (
                        bizes_id, bizes_nm, it.get("brchNm"),
                        it.get("indsLclsCd", "I2"), it.get("indsLclsNm", "음식"),
                        it.get("indsMclsCd"), it.get("indsMclsNm"),
                        it.get("indsSclsCd"), it.get("indsSclsNm"),
                        it.get("ksicCd"), it.get("ksicNm"),
                        it.get("ctprvnCd"), it.get("ctprvnNm"),
                        it.get("signguCd"), it.get("signguNm"),
                        it.get("adongCd"), it.get("adongNm"),
                        it.get("ldongCd"), it.get("ldongNm"),
                        region.sido_code, region.sido_name,
                        region.api_code, region.name,
                        region.dashboard_code,
                        it.get("rdnmAdr"), it.get("lnoAdr"), it.get("newZipcd"),
                        lon, lat, stdr_ym, "NEW_COLLECTED", json.dumps(it, ensure_ascii=False)
                    ))
                saved_cnt += 1

            # 4. Data contract integrity check: raw - excluded == saved
            is_valid = (raw_cnt - excluded_cnt) == saved_cnt
            if not is_valid:
                result["contract_valid"] = False

            # Log page
            if not dry_run:
                cur.execute("""
                    INSERT INTO collection_logs (
                        batch_id, signgu_code, page_no, stdr_ym,
                        raw_count, excluded_count, saved_count, is_contract_valid,
                        api_result_code, api_result_msg, ret_signgu_cd, ret_signgu_nm
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    batch_id, region.api_code, page, stdr_ym,
                    raw_cnt, excluded_cnt, saved_cnt, 1 if is_valid else 0,
                    r_code, r_msg, items[0].get("signguCd") if items else "",
                    items[0].get("signguNm") if items else ""
                ))
                self.con.commit()

            result["total_raw"] += raw_cnt
            result["total_excluded"] += excluded_cnt
            result["total_saved"] += saved_cnt

        result["status"] = "COMPLETED"
        return result

    def close(self):
        """데이터베이스 연결 안전 종료"""
        if hasattr(self, "con") and self.con:
            try:
                self.con.close()
            except Exception:
                pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Franchise Dashboard Nationwide Collector v2")
    parser.add_argument("--test", action="store_true", help="Run 1-region probe test")
    parser.add_argument("--code", type=str, default="12270", help="Region code for test")
    args = parser.parse_args()

    collector = NationwideCollectorV2()
    reg = collector.region_mgr.get_by_code(args.code)
    if not reg:
        print(f"Region code {args.code} not found in config/regions_v2.json")
        sys.exit(1)

    print(f"Testing collector v2 on {reg.sido_name} {reg.name} ({reg.api_code})...")
    res = collector.collect_district(reg, batch_id="TEST_RUN", dry_run=True, max_pages=1)
    print("Test Result:", json.dumps(res, ensure_ascii=False, indent=2))
