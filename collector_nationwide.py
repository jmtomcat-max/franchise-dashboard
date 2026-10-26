#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
collector_nationwide.py
Franchise Dashboard - 대한민국 전국 17개 시도 외식업 데이터 자동 수집 프로그램

[주요 기능]
1. config/regions.json 기반 전국 17개 시도 250개 시군구 순차 수집
   (시도 -> 시군구 -> 페이지 계층 순회)
2. API 오류 시 지수 백오프(Exponential Backoff) 최대 3회 재시도 및 안전 마스킹
3. 페이지별 SQLite 트랜잭션 저장 및 중단 시 마지막 완료 페이지부터 재개(Resume)
4. 점포 고유번호(bizesId) 기준 중복 방지 및 이상치(좌표 누락, 중복 점포) 별도 기록
5. API 데이터 기준월(stdrYm)별 배치 분리 관리
6. 시군구별 무결성 자동 검증 (공식: 원본 수집 건수 - 제외 업종 건수 = 최종 저장 대상 건수)
7. 수집 진행률(%), 처리 시군구 수, 예상 잔여 호출량 실시간 표시
8. 최종 JSON 및 Markdown 종합 보고서 자동 생성
   (reports/nationwide_collection_report.json, reports/nationwide_collection_summary.md)
9. API Key 보안 관리: 환경변수 / .env / 콘솔 비공개 입력 (CLI 인자 노출 금지)
"""

import os
import sys
import json
import time
import sqlite3
import getpass
import argparse
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Any
import urllib.parse
import urllib.request
import urllib.error

# 콘솔 출력 UTF-8 인코딩 설정
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# 기본 경로 설정
BASE_DIR = Path(r"D:\Franchise_Dashboard")
DEFAULT_CONFIG_PATH = BASE_DIR / "config" / "regions.json"
DEFAULT_DB_PATH = BASE_DIR / "data" / "nationwide_food_stores.sqlite3"
DEFAULT_REPORT_PATH = BASE_DIR / "reports" / "nationwide_collection_report.json"
DEFAULT_SUMMARY_PATH = BASE_DIR / "reports" / "nationwide_collection_summary.md"
BASE_API_URL = "https://apis.data.go.kr/B553077/api/open/sdsc2"


# ==============================================================================
# 1. 보안 유틸리티
# ==============================================================================

def sanitize_text(text: str, secret_key: Optional[str] = None) -> str:
    """로그, 에러 메시지, 보고서에서 API 인증키가 노출되지 않도록 마스킹합니다."""
    if not text:
        return ""
    cleaned = str(text)
    if secret_key and len(secret_key) > 4:
        cleaned = cleaned.replace(secret_key, "[MASKED_KEY]")
        encoded_key = urllib.parse.quote(secret_key)
        if encoded_key != secret_key:
            cleaned = cleaned.replace(encoded_key, "[MASKED_KEY]")
    return cleaned


# ==============================================================================
# 2. 전국 행정구역 모델 및 매니저
# ==============================================================================

@dataclass
class DistrictInfo:
    code: str
    name: str

@dataclass
class ProvinceInfo:
    code: str
    name: str
    districts: List[DistrictInfo] = field(default_factory=list)

class NationwideRegionManager:
    """config/regions.json 파일을 로드하고 전국 17개 시도·시군구 구조를 관리합니다."""

    def __init__(self, config_path: Path = DEFAULT_CONFIG_PATH):
        self.config_path = Path(config_path)
        self.meta: Dict[str, Any] = {}
        self.provinces: List[ProvinceInfo] = []
        self._load_regions()

    def _load_regions(self):
        if not self.config_path.exists():
            raise FileNotFoundError(f"행정구역 설정 파일을 찾을 수 없습니다: {self.config_path}")

        with open(self.config_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.meta = data.get("meta", {})
        self.provinces = []
        for p in data.get("provinces", []):
            districts = [DistrictInfo(d["code"], d["name"]) for d in p.get("districts", [])]
            self.provinces.append(ProvinceInfo(p["province_code"], p["province_name"], districts))

    def get_all_districts(self) -> List[Tuple[ProvinceInfo, DistrictInfo]]:
        """전국 모든 시도-시군구 쌍 목록을 반환합니다."""
        res = []
        for p in self.provinces:
            for d in p.districts:
                res.append((p, d))
        return res

    def get_province(self, province_code: str) -> Optional[ProvinceInfo]:
        for p in self.provinces:
            if p.code == province_code:
                return p
        return None

    def find_district(self, district_code: str) -> Optional[Tuple[ProvinceInfo, DistrictInfo]]:
        for p in self.provinces:
            for d in p.districts:
                if d.code == district_code:
                    return (p, d)
        return None


# ==============================================================================
# 3. 데이터베이스 매니저 (SQLite Database Manager)
# ==============================================================================

class DatabaseManager:
    """SQLite3 전국 데이터베이스 연결, 스키마 관리, 트랜잭션 및 인덱스를 담당합니다."""

    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_tables()

    def get_connection(self, timeout: float = 30.0) -> sqlite3.Connection:
        con = sqlite3.connect(self.db_path, timeout=timeout)
        con.execute("PRAGMA journal_mode = WAL")
        con.execute("PRAGMA foreign_keys = ON")
        return con

    def _init_tables(self):
        with self.get_connection() as con:
            # 전국 점포 마스터 테이블
            con.execute("""CREATE TABLE IF NOT EXISTS stores (
                bizes_id TEXT PRIMARY KEY,
                name TEXT,
                middle_code TEXT,
                small_code TEXT,
                province TEXT,
                district TEXT,
                dong TEXT,
                address TEXT,
                lat REAL,
                lon REAL,
                raw_json TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )""")

            # 고속 검색 및 3D GIS 렌더링 최적화 인덱스
            con.execute("CREATE INDEX IF NOT EXISTS idx_stores_prov_dist ON stores(province, district)")
            con.execute("CREATE INDEX IF NOT EXISTS idx_stores_dist_dong ON stores(district, dong)")
            con.execute("CREATE INDEX IF NOT EXISTS idx_stores_codes ON stores(middle_code, small_code)")
            con.execute("CREATE INDEX IF NOT EXISTS idx_stores_coords ON stores(lat, lon)")

            # 수집 진행 상태 테이블 (시군구코드 + 페이지 + 기준년월 복합 식별)
            con.execute("""CREATE TABLE IF NOT EXISTS progress (
                district_code TEXT,
                page INTEGER,
                source_month TEXT,
                total_api_count INTEGER,
                raw_count INTEGER,
                excluded_count INTEGER,
                saved_count INTEGER,
                status TEXT,
                collected_at TEXT DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (district_code, page, source_month)
            )""")

            # 수집 배치 관리 테이블 (기준월 변경 시 별도 관리)
            con.execute("""CREATE TABLE IF NOT EXISTS collection_batches (
                batch_id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_month TEXT UNIQUE,
                started_at TEXT DEFAULT CURRENT_TIMESTAMP,
                completed_at TEXT,
                status TEXT
            )""")

            # 무결성 이상치 및 오류 기록 테이블 (좌표 누락, 중복 점포, API 오류 기록)
            con.execute("""CREATE TABLE IF NOT EXISTS integrity_issues (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                district_code TEXT,
                page INTEGER,
                bizes_id TEXT,
                issue_type TEXT,
                details TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )""")

    def get_last_completed_page(self, district_code: str, source_month: str) -> int:
        """해당 시군구 및 기준월에서 마지막으로 성공한 페이지 번호를 반환합니다."""
        with self.get_connection() as con:
            row = con.execute("""
                SELECT MAX(page) FROM progress 
                WHERE district_code = ? AND source_month = ? AND status = 'COMPLETED'
            """, (district_code, source_month)).fetchone()
            return row[0] if (row and row[0] is not None) else 0

    def is_district_completed(self, district_code: str, source_month: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """해당 시군구의 모든 페이지가 이미 수집 완료되었는지 확인합니다."""
        with self.get_connection() as con:
            row = con.execute("""
                SELECT MAX(page), MAX(total_api_count), SUM(raw_count), SUM(excluded_count), SUM(saved_count)
                FROM progress 
                WHERE district_code = ? AND source_month = ? AND status = 'COMPLETED'
            """, (district_code, source_month)).fetchone()
            if row and row[0] is not None and row[1] is not None and row[1] >= 0:
                max_page, total_api, sum_raw, sum_excluded, sum_saved = row
                if max_page * 1000 >= total_api or total_api == 0:
                    missing_coords = con.execute("""
                        SELECT COUNT(*) FROM integrity_issues
                        WHERE district_code = ? AND issue_type = 'MISSING_COORDINATES'
                    """, (district_code,)).fetchone()[0]
                    duplicates = con.execute("""
                        SELECT COUNT(*) FROM integrity_issues
                        WHERE district_code = ? AND issue_type = 'DUPLICATE_STORE'
                    """, (district_code,)).fetchone()[0]
                    return True, {
                        "district_code": district_code,
                        "total_api_count": total_api,
                        "collected_pages": max_page,
                        "raw_collected_count": sum_raw or 0,
                        "excluded_count": sum_excluded or 0,
                        "target_save_count": (sum_raw or 0) - (sum_excluded or 0),
                        "actual_new_saved": sum_saved or 0,
                        "duplicate_count": duplicates,
                        "missing_coords_count": missing_coords,
                        "validation_passed": ((sum_raw or 0) - (sum_excluded or 0)) == (sum_saved or 0),
                        "total_count_match": total_api == (sum_raw or 0)
                    }
        return False, None

    def get_known_source_month(self) -> Optional[str]:
        """기존 DB에 기록된 최신 기준년월을 확인합니다."""
        with self.get_connection() as con:
            row = con.execute("SELECT source_month FROM collection_batches ORDER BY batch_id DESC LIMIT 1").fetchone()
            return row[0] if row else None

    def register_batch_if_new(self, source_month: str):
        with self.get_connection() as con:
            con.execute("""
                INSERT OR IGNORE INTO collection_batches(source_month, status)
                VALUES(?, 'IN_PROGRESS')
            """, (source_month,))

    def log_issue(self, district_code: str, page: int, bizes_id: Optional[str], issue_type: str, details: str, con: Optional[sqlite3.Connection] = None):
        sql = """
            INSERT INTO integrity_issues(district_code, page, bizes_id, issue_type, details)
            VALUES(?, ?, ?, ?, ?)
        """
        params = (district_code, page, bizes_id, issue_type, details)
        if con is not None:
            con.execute(sql, params)
        else:
            with self.get_connection() as local_con:
                local_con.execute(sql, params)


# ==============================================================================
# 4. 전국 수집 엔진 코어 (Nationwide Store Collector Engine)
# ==============================================================================

class NationwideStoreCollectorEngine:
    """전국 17개 시도 250개 시군구 외식업 데이터 자동 수집 및 무결성 검증 엔진"""

    def __init__(self, api_key: str, db_manager: DatabaseManager):
        self.api_key = api_key
        self.db = db_manager
        self.source_month: Optional[str] = None
        # 외식업 확정 필터링 체계
        self.target_industry_large = "I2"            # 음식업
        self.excluded_middle_codes = ["I211"]        # 주점 전체 제외
        self.excluded_small_codes = ["I20701"]       # 구내식당 제외
        self.included_small_codes = ["I20702"]       # 뷔페 포함

    def _fetch_page_with_retry(self, district_code: str, page: int, max_retries: int = 3) -> Dict[str, Any]:
        """
        지수 백오프(Exponential Backoff) 방식으로 최대 max_retries회 재시도하며 API를 호출합니다.
        (인증키는 로그에 노출되지 않도록 자동 마스킹 처리)
        """
        params = {
            "serviceKey": self.api_key,
            "divId": "signguCd",
            "key": district_code,
            "indsLclsCd": self.target_industry_large,
            "numOfRows": 1000,
            "pageNo": page,
            "type": "json"
        }
        url = f"{BASE_API_URL}/storeListInDong?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})

        last_error = None
        effective_max_retries = max(max_retries, 5)

        for attempt in range(1, effective_max_retries + 1):
            try:
                with urllib.request.urlopen(req, timeout=45) as resp:
                    data = json.load(resp)
                header = data.get("header", {})
                res_code = str(header.get("resultCode", ""))

                # 소진공 API 특성: 조건에 부합하는 데이터가 0건일 때 resultCode='03', resultMsg='NODATA_ERROR' 반환
                if res_code == "03":
                    return {
                        "header": header,
                        "body": {
                            "items": [],
                            "numOfRows": 0,
                            "pageNo": page,
                            "totalCount": 0
                        }
                    }

                if res_code != "00":
                    msg = header.get("resultMsg", str(header))
                    raise RuntimeError(f"API Error [{res_code}]: {msg}")
                return data
            except Exception as ex:
                last_error = ex
                safe_err = sanitize_text(str(ex), self.api_key)

                # HTTP 429 (Too Many Requests / Rate Limit) 특화 처리
                is_rate_limit = False
                retry_after_sec = None
                if isinstance(ex, urllib.error.HTTPError) and ex.code == 429:
                    is_rate_limit = True
                    try:
                        ra = ex.headers.get("Retry-After")
                        if ra and ra.isdigit():
                            retry_after_sec = float(ra)
                    except Exception:
                        pass
                elif "429" in str(ex) or "Too Many Requests" in str(ex):
                    is_rate_limit = True

                if is_rate_limit:
                    # Rate Limit의 경우 5초, 10초, 20초, 40초, 60초 대기
                    wait_time = retry_after_sec if retry_after_sec else min(5.0 * (2 ** (attempt - 1)), 60.0)
                    print(f"  [Rate Limit 감지 {attempt}/{effective_max_retries}] 지역 {district_code} p.{page}: HTTP 429 발생. API 서버 보호를 위해 {wait_time:.1f}초 대기 후 자동 재시도합니다...")
                else:
                    wait_time = (2 ** (attempt - 1)) * 1.5
                    print(f"  [재시도 {attempt}/{effective_max_retries}] 지역 {district_code} p.{page} 오류: {safe_err}. {wait_time:.1f}초 대기 후 재시도...")

                time.sleep(wait_time)

        # 최대 재시도 실패 시 이슈 기록 (인증키 마스킹)
        masked_err = sanitize_text(str(last_error), self.api_key)
        self.db.log_issue(district_code, page, None, "API_ERROR", masked_err)
        raise RuntimeError(f"API 호출 {effective_max_retries}회 재시도 실패 (지역: {district_code}, p.{page}): {masked_err}")

    def collect_district(
        self,
        province: ProvinceInfo,
        district: DistrictInfo,
        single_page_test: bool = False,
        progress_info: str = ""
    ) -> Dict[str, Any]:
        """
        특정 시군구의 점포 데이터를 페이지네이션하며 수집하고 검증합니다.
        """
        prefix = f"[{progress_info}] " if progress_info else ""
        print(f"\n==================================================")
        print(f"▶ {prefix}{province.name} [{district.code}] {district.name} 수집 시작")
        print(f"==================================================")

        # 1. 기준년월 초기화 및 배치 확인
        if self.source_month is None:
            db_month = self.db.get_known_source_month()
            self.source_month = db_month

        # 2. 이미 시군구 전체 수집이 완료되었는지 확인 (건너뛰기)
        if self.source_month and not single_page_test:
            is_done, cached_summary = self.db.is_district_completed(district.code, self.source_month)
            if is_done and cached_summary:
                cached_summary["province_code"] = province.code
                cached_summary["province_name"] = province.name
                cached_summary["district_name"] = district.name
                print(f"  [건너뛰기] {province.name} {district.name}는 이미 수집 완료됨 (저장: {cached_summary['actual_new_saved']:,}건)")
                return cached_summary

        # 3. 이어받기(Resume) 페이지 확인
        last_page = 0
        if self.source_month:
            last_page = self.db.get_last_completed_page(district.code, self.source_month)
            if last_page > 0:
                print(f"  [이어받기] 기존 수집 완료: {last_page}페이지 (다음 페이지부터 진행)")

        current_page = last_page + 1
        district_summary = {
            "province_code": province.code,
            "province_name": province.name,
            "district_code": district.code,
            "district_name": district.name,
            "total_api_count": 0,
            "collected_pages": 0,
            "raw_collected_count": 0,
            "excluded_count": 0,
            "target_save_count": 0,
            "actual_new_saved": 0,
            "duplicate_count": 0,
            "missing_coords_count": 0,
            "validation_passed": False,
            "total_count_match": False,
        }

        con = self.db.get_connection()
        try:
            while True:
                # API 호출 (지수 백오프 적용)
                resp_data = self._fetch_page_with_retry(district.code, current_page)
                header = resp_data.get("header", {})
                body = resp_data.get("body", {})

                # 기준년월(stdrYm) 정밀 추출 및 엄격한 유효성 검증 (규칙 4, 5 준수)
                raw_month = header.get("stdrYm")
                month = str(raw_month).strip() if raw_month is not None else ""
                
                # 데이터 0건(NODATA_ERROR) 응답 시 header에 stdrYm이 없으면 기존 배치 기준월 계승
                if not month and self.source_month:
                    month = self.source_month

                # 기준월 누락 또는 비정상 포맷 검사 (YYYYMM 6자리 숫자 필수)
                if not month or month in ["unknown", "None", "null", ""] or not (month.isdigit() and len(month) == 6):
                    err_msg = f"API 응답 header에 데이터 기준월(stdrYm)이 누락되었거나 형식이 비정상입니다: '{raw_month}'"
                    self.db.log_issue(district.code, current_page, None, "INVALID_OR_MISSING_STDR_YM", err_msg, con=con)
                    raise ValueError(err_msg)

                total_api_count = int(body.get("totalCount", 0))
                district_summary["total_api_count"] = total_api_count

                # 기준년월 검증 및 배치 등록 (서로 다른 기준월 데이터 혼합 방지)
                if self.source_month is None:
                    self.source_month = month
                    self.db.register_batch_if_new(self.source_month)
                elif self.source_month != month:
                    err_msg = (
                        f"API 데이터 기준월이 변경되었습니다! (배치 기준월: {self.source_month} -> 수신 기준월: {month})\n"
                        "기준월이 서로 다른 데이터를 동일한 시점의 전국 통계로 혼합할 수 없습니다."
                    )
                    self.db.log_issue(district.code, current_page, None, "STDR_YM_MISMATCH", err_msg, con=con)
                    raise RuntimeError(err_msg)

                items = body.get("items") or []
                if isinstance(items, dict):
                    items = items.get("item", [])
                if isinstance(items, dict):
                    items = [items]

                page_raw = len(items)
                page_excluded = 0
                page_saved = 0
                page_duplicates = 0
                page_missing_coords = 0

                # 원자적 트랜잭션으로 페이지 단위 저장
                with con:
                    for s in items:
                        m_code = s.get("indsMclsCd")
                        s_code = s.get("indsSclsCd")
                        bizes_id = s.get("bizesId")

                        # 1) 제외 규칙 검증
                        # I211 (주점 전체 제외)
                        if m_code in self.excluded_middle_codes:
                            page_excluded += 1
                            continue
                        # I20701 (구내식당 제외)
                        if s_code in self.excluded_small_codes:
                            page_excluded += 1
                            continue
                        # bizes_id 누락 건 예외 처리
                        if not bizes_id:
                            page_excluded += 1
                            self.db.log_issue(district.code, current_page, None, "MISSING_BIZES_ID", json.dumps(s, ensure_ascii=False), con=con)
                            continue

                        # 2) 좌표 누락 검사
                        lat = s.get("lat")
                        lon = s.get("lon")
                        if lat is None or lon is None or str(lat).strip() == "" or str(lon).strip() == "":
                            page_missing_coords += 1
                            self.db.log_issue(district.code, current_page, bizes_id, "MISSING_COORDINATES", f"lat={lat}, lon={lon}", con=con)

                        # 3) 중복 점포 검사
                        existing = con.execute("SELECT 1 FROM stores WHERE bizes_id = ?", (bizes_id,)).fetchone()
                        if existing:
                            page_duplicates += 1
                            self.db.log_issue(district.code, current_page, bizes_id, "DUPLICATE_STORE", f"Duplicate bizes_id in district {district.code}", con=con)

                        # 4) 저장 또는 갱신
                        con.execute("""
                            INSERT OR REPLACE INTO stores (
                                bizes_id, name, middle_code, small_code,
                                province, district, dong, address,
                                lat, lon, raw_json, updated_at
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                        """, (
                            bizes_id,
                            s.get("bizesNm"),
                            m_code,
                            s_code,
                            s.get("ctprvnNm") or province.name,
                            s.get("signguNm") or district.name,
                            s.get("adongNm"),
                            s.get("rdnmAdr"),
                            float(lat) if (lat is not None and str(lat).strip() != "") else None,
                            float(lon) if (lon is not None and str(lon).strip() != "") else None,
                            json.dumps(s, ensure_ascii=False)
                        ))
                        page_saved += 1

                    # 진행 상태(progress) 저장
                    con.execute("""
                        INSERT OR REPLACE INTO progress (
                            district_code, page, source_month, total_api_count,
                            raw_count, excluded_count, saved_count, status
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, 'COMPLETED')
                    """, (
                        district.code, current_page, self.source_month, total_api_count,
                        page_raw, page_excluded, page_saved
                    ))

                # 시군구 누적 집계
                district_summary["collected_pages"] += 1
                district_summary["raw_collected_count"] += page_raw
                district_summary["excluded_count"] += page_excluded
                district_summary["target_save_count"] += (page_raw - page_excluded)
                district_summary["actual_new_saved"] += page_saved
                district_summary["duplicate_count"] += page_duplicates
                district_summary["missing_coords_count"] += page_missing_coords

                print(f"  [저장완료] p.{current_page:02d} | 원본: {page_raw:4d}건 | 제외: {page_excluded:3d}건 | 저장: {page_saved:4d}건 (누적 저장: {district_summary['actual_new_saved']:,}건)")

                if single_page_test:
                    print(f"  [시험 모드] 1페이지 수집 후 종료합니다.")
                    break

                if current_page * 1000 >= total_api_count or not items:
                    print(f"  [완료] {district.name} 전체 수집 완료 (총 {current_page}페이지)")
                    break

                current_page += 1
                time.sleep(0.6)  # API 부하 및 429 Rate Limit 방지 대기시간

        finally:
            con.close()

        # 데이터 무결성 검증 (원본 - 제외 = 저장 대상)
        expected_target = district_summary["raw_collected_count"] - district_summary["excluded_count"]
        district_summary["validation_passed"] = (expected_target == district_summary["target_save_count"])
        district_summary["total_count_match"] = (district_summary["total_api_count"] == district_summary["raw_collected_count"])

        print(f"--------------------------------------------------")
        print(f"▶ {province.name} [{district.name}] 수집 검증:")
        print(f"  - API totalCount: {district_summary['total_api_count']:,}건")
        print(f"  - 원본: {district_summary['raw_collected_count']:,}건 | 제외: {district_summary['excluded_count']:,}건 | 저장대상: {district_summary['target_save_count']:,}건")
        print(f"  - 무결성 공식 검증: {'[성공 PASS]' if district_summary['validation_passed'] else '[실패 FAIL]'}")
        print(f"  - 좌표 누락: {district_summary['missing_coords_count']}건 | 중복 점포: {district_summary['duplicate_count']}건")
        print(f"--------------------------------------------------")

        return district_summary


# ==============================================================================
# 5. 리포트 생성기 (Report Generator)
# ==============================================================================

class ReportGenerator:
    """수집 결과 및 무결성 검증 내역을 JSON 및 Markdown 보고서로 생성합니다."""

    @staticmethod
    def generate_json_report(
        report_path: Path,
        source_month: Optional[str],
        district_summaries: List[Dict[str, Any]],
        execution_mode: str = "NORMAL"
    ) -> Dict[str, Any]:
        report_path = Path(report_path)
        report_path.parent.mkdir(parents=True, exist_ok=True)

        total_api = sum(d["total_api_count"] for d in district_summaries)
        total_raw = sum(d["raw_collected_count"] for d in district_summaries)
        total_excluded = sum(d["excluded_count"] for d in district_summaries)
        total_target = sum(d["target_save_count"] for d in district_summaries)
        total_saved = sum(d["actual_new_saved"] for d in district_summaries)
        total_duplicates = sum(d["duplicate_count"] for d in district_summaries)
        total_missing_coords = sum(d["missing_coords_count"] for d in district_summaries)
        valid_month = bool(source_month and source_month != "unknown" and source_month.isdigit() and len(source_month) == 6)
        all_passed = (all(d["validation_passed"] for d in district_summaries) and valid_month) if district_summaries else False

        # 시도별 집계
        province_stats: Dict[str, Dict[str, Any]] = {}
        for d in district_summaries:
            p_code = d.get("province_code", "unknown")
            p_name = d.get("province_name", "unknown")
            if p_code not in province_stats:
                province_stats[p_code] = {
                    "province_code": p_code,
                    "province_name": p_name,
                    "districts_count": 0,
                    "total_api_count": 0,
                    "raw_count": 0,
                    "excluded_count": 0,
                    "saved_count": 0,
                    "missing_coords": 0,
                    "duplicates": 0
                }
            ps = province_stats[p_code]
            ps["districts_count"] += 1
            ps["total_api_count"] += d["total_api_count"]
            ps["raw_count"] += d["raw_collected_count"]
            ps["excluded_count"] += d["excluded_count"]
            ps["saved_count"] += d["actual_new_saved"]
            ps["missing_coords"] += d["missing_coords_count"]
            ps["duplicates"] += d["duplicate_count"]

        report = {
            "meta": {
                "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                "source_month": source_month or "unknown",
                "execution_mode": execution_mode,
                "target_region": "대한민국 전국 17개 시도",
                "validation_rule": "raw_collected_count - excluded_count == target_save_count"
            },
            "overall_summary": {
                "districts_processed": len(district_summaries),
                "provinces_processed": len(province_stats),
                "total_api_count": total_api,
                "total_raw_collected": total_raw,
                "total_excluded": total_excluded,
                "total_target_save": total_target,
                "total_actual_saved": total_saved,
                "total_duplicates": total_duplicates,
                "total_missing_coordinates": total_missing_coords,
                "all_validations_passed": all_passed
            },
            "provinces_summary": list(province_stats.values()),
            "districts": district_summaries
        }

        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        print(f"\n[보고서 JSON 생성 완료] -> {report_path.resolve()}")
        return report

    @staticmethod
    def generate_markdown_summary(summary_path: Path, report_dict: Dict[str, Any], db_manager: DatabaseManager):
        summary_path = Path(summary_path)
        summary_path.parent.mkdir(parents=True, exist_ok=True)

        meta = report_dict["meta"]
        ov = report_dict["overall_summary"]
        provs = report_dict.get("provinces_summary", [])
        districts = report_dict["districts"]

        with db_manager.get_connection() as con:
            unique_total = con.execute("SELECT COUNT(*) FROM stores").fetchone()[0]
            top_middle = con.execute("""
                SELECT middle_code, COUNT(*) FROM stores
                GROUP BY middle_code ORDER BY COUNT(*) DESC
            """).fetchall()
            issues_total = con.execute("SELECT COUNT(*) FROM integrity_issues").fetchone()[0]

        lines = [
            "# 대한민국 전국 외식업 점포 데이터 수집 종합 보고서",
            "",
            f"- **수집 일시**: {meta['generated_at']}",
            f"- **데이터 기준월 (`stdrYm`)**: `{meta['source_month']}`",
            f"- **실행 모드**: `{meta['execution_mode']}`",
            f"- **검증 공식**: `{meta['validation_rule']}`",
            "",
            "## 1. 전국 수집 및 정합성 요약",
            "",
            f"- **수집 완료 시군구 수**: {ov['districts_processed']}개 시군구 (진행 시도: {ov['provinces_processed']}개 시도)",
            f"- **API 총 원본 건수 (`totalCount` 합계)**: {ov['total_api_count']:,}건",
            f"- **실제 수신 원본 건수**: {ov['total_raw_collected']:,}건",
            f"- **제외 업종 건수 (주점 I211 + 구내식당 I20701)**: {ov['total_excluded']:,}건",
            f"- **최종 저장 대상 건수 (`raw - excluded`)**: {ov['total_target_save']:,}건",
            f"- **DB 실제 저장 건수**: {ov['total_actual_saved']:,}건",
            f"- **DB 고유 점포 수 (Unique stores)**: {unique_total:,}건",
            f"- **중복 점포 수**: {ov['total_duplicates']}건",
            f"- **좌표 누락 건수**: {ov['total_missing_coordinates']}건",
            f"- **전체 데이터 무결성 검증 통과 여부**: {'[성공 PASS]' if ov['all_validations_passed'] else '[실패 FAIL]'}",
            "",
            "## 2. 17개 시도별 수집 통계 현황",
            "",
            "| 시도코드 | 시도명 | 수집 시군구 수 | API 총건수 | 수신 원본 | 제외 건수 | 저장 건수 | 좌표 누락 | 중복 |",
            "| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |",
        ]

        for p in provs:
            lines.append(
                f"| `{p['province_code']}` | **{p['province_name']}** | {p['districts_count']}개 | "
                f"{p['total_api_count']:,} | {p['raw_count']:,} | {p['excluded_count']:,} | "
                f"{p['saved_count']:,} | {p['missing_coords']} | {p['duplicates']} |"
            )

        lines.extend([
            "",
            "## 3. 외식업 8대 대분류/중분류별 점포 분포",
            "",
            "| 중분류 코드 | 점포 수 | 전국 점유율 |",
            "| :---: | :---: | :---: |",
        ])

        for m_code, cnt in top_middle:
            pct = (cnt / unique_total * 100) if unique_total > 0 else 0
            lines.append(f"| `{m_code}` | {cnt:,}건 | {pct:.1f}% |")

        lines.extend([
            "",
            "## 4. 이상치 및 오류 현황",
            f"- **총 이상치 기록 건수**: {issues_total}건",
            f"- **좌표 누락 (`lat/lon is null`)**: {ov['total_missing_coordinates']}건",
            f"- **동일 점포 중복 수집**: {ov['total_duplicates']}건",
            "",
            "## 5. 시군구별 상세 수집 내역",
            "",
            "| 시도 | 시군구 | 코드 | API 총건수 | 원본 수신 | 제외 건수 | 저장 건수 | 좌표 누락 | 중복 | 검증 |",
            "| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |",
        ])

        for d in districts:
            status_str = "PASS" if d["validation_passed"] else "FAIL"
            lines.append(
                f"| {d.get('province_name','')} | {d['district_name']} | `{d['district_code']}` | "
                f"{d['total_api_count']:,} | {d['raw_collected_count']:,} | {d['excluded_count']:,} | "
                f"{d['actual_new_saved']:,} | {d['missing_coords_count']} | {d['duplicate_count']} | {status_str} |"
            )

        lines.extend([
            "",
            "---",
            "*보고서 생성: Franchise Dashboard Nationwide Data Pipeline*"
        ])

        with open(summary_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        print(f"[요약 마크다운 보고서 생성 완료] -> {summary_path.resolve()}")


# ==============================================================================
# 6. 유틸리티 및 API 키 로더 (안전한 비공개 로드)
# ==============================================================================

def load_api_key_safely() -> str:
    """
    인증키를 안전하게 로드합니다.
    (CLI 인자에 노출하지 않고, 환경변수 -> .env 파일 -> 실행 시 비공개 입력 순으로 처리합니다.)
    """
    for env_var in ["SERVICE_KEY", "DATA_GO_KR_API_KEY", "PUBLIC_DATA_API_KEY"]:
        val = os.getenv(env_var)
        if val and val.strip():
            return val.strip()

    env_file = BASE_DIR / ".env"
    if env_file.exists():
        try:
            with open(env_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" in line:
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.strip().strip('"').strip("'")
                        if k in ["SERVICE_KEY", "DATA_GO_KR_API_KEY", "PUBLIC_DATA_API_KEY"] and v:
                            return v
        except Exception:
            pass

    try:
        user_key = getpass.getpass("공공데이터포털 API Key (비공개 입력): ").strip()
        if user_key:
            return user_key
    except Exception:
        pass

    return ""


# ==============================================================================
# 7. 메인 실행 진입점 (CLI Entry Point)
# ==============================================================================

def main():
    parser = argparse.ArgumentParser(description="Franchise Dashboard - 대한민국 전국 17개 시도 외식업 데이터 자동 수집 프로그램")
    parser.add_argument("--config", type=str, default=str(DEFAULT_CONFIG_PATH), help="전국 행정구역 설정 JSON 경로")
    parser.add_argument("--db", type=str, default=str(DEFAULT_DB_PATH), help="저장할 SQLite 데이터베이스 경로")
    parser.add_argument("--report", type=str, default=str(DEFAULT_REPORT_PATH), help="결과 JSON 보고서 경로")
    parser.add_argument("--summary", type=str, default=str(DEFAULT_SUMMARY_PATH), help="결과 마크다운 요약 보고서 경로")
    parser.add_argument("--province", type=str, default=None, help="특정 시도 코드만 수집 (예: 부산 26, 경기 41)")
    parser.add_argument("--district", type=str, default=None, help="특정 시군구 코드만 수집 (예: 해운대구 26350)")
    parser.add_argument("--test-single-page", action="store_true", help="각 시군구의 첫 1페이지만 시험 수집")
    parser.add_argument("--dry-run-schema", action="store_true", help="API 호출 없이 DB 테이블 생성 및 스키마만 검증")

    args = parser.parse_args()

    print("================================================================")
    print("  Franchise Dashboard - 전국 외식업 데이터 자동 수집 프로그램")
    print("================================================================")

    db_path = Path(args.db)
    report_path = Path(args.report)
    summary_path = Path(args.summary)
    config_path = Path(args.config)

    db_manager = DatabaseManager(db_path)

    # 모의 스키마 검증 모드
    if args.dry_run_schema:
        print("[모드] --dry-run-schema: DB 스키마 초기화 및 테이블 구조 검증을 완료했습니다.")
        with db_manager.get_connection() as con:
            cur = con.cursor()
            tables = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'")]
            print(f"생성된 테이블: {tables}")
        return

    # 전국 행정구역 매니저 로드
    region_mgr = NationwideRegionManager(config_path)
    all_pairs = region_mgr.get_all_districts()
    print(f"[정보] 행정구역 명세 로드 완료: {len(region_mgr.provinces)}개 시도, 총 {len(all_pairs)}개 시군구")

    # 대상 지역 필터링
    target_pairs: List[Tuple[ProvinceInfo, DistrictInfo]] = []
    if args.district:
        found = region_mgr.find_district(args.district)
        if not found:
            print(f"[오류] 지정한 시군구 코드({args.district})를 행정구역 명세에서 찾을 수 없습니다.")
            sys.exit(1)
        target_pairs = [found]
    elif args.province:
        prov = region_mgr.get_province(args.province)
        if not prov:
            print(f"[오류] 지정한 시도 코드({args.province})를 찾을 수 없습니다.")
            sys.exit(1)
        target_pairs = [(prov, d) for d in prov.districts]
    else:
        target_pairs = all_pairs

    print(f"수집 대상 시군구 수: {len(target_pairs)}개")
    if args.test_single_page:
        print("※ [시험 모드] 각 시군구의 첫 1페이지만 수집합니다.")

    # API 키 안전 로드
    api_key = load_api_key_safely()
    if not api_key:
        print("\n[오류] API Key가 설정되지 않았습니다.")
        print("  - .env 파일에 'SERVICE_KEY=인증키' 설정하거나")
        print("  - 환경변수 SERVICE_KEY를 설정하거나")
        print("  - 프로그램 실행 시 비공개 입력 프롬프트에 입력하세요.")
        sys.exit(1)

    engine = NationwideStoreCollectorEngine(api_key, db_manager)
    district_summaries = []

    total_districts_count = len(target_pairs)
    start_time = time.time()

    try:
        for idx, (province, district) in enumerate(target_pairs, start=1):
            pct = (idx / total_districts_count) * 100
            elapsed = time.time() - start_time
            avg_per_district = (elapsed / idx) if idx > 1 else 0
            remaining_districts = total_districts_count - idx
            estimated_remaining_sec = avg_per_district * remaining_districts

            progress_str = f"{idx}/{total_districts_count} ({pct:.1f}%) | 잔여예상: {int(estimated_remaining_sec//60)}분 {int(estimated_remaining_sec%60)}초"
            summary = engine.collect_district(
                province=province,
                district=district,
                single_page_test=args.test_single_page,
                progress_info=progress_str
            )
            district_summaries.append(summary)

    except KeyboardInterrupt:
        print("\n[중단] 사용자에 의해 수집이 중단되었습니다. (완료된 페이지까지 안전하게 커밋됨)")
    except Exception as ex:
        print(f"\n[오류 발생] {ex}")
        raise
    finally:
        # 최종 결과 보고서 생성 (JSON & Markdown)
        mode_str = "TEST_SINGLE_PAGE" if args.test_single_page else "FULL_COLLECTION"
        report_dict = ReportGenerator.generate_json_report(
            report_path=report_path,
            source_month=engine.source_month,
            district_summaries=district_summaries,
            execution_mode=mode_str
        )
        ReportGenerator.generate_markdown_summary(
            summary_path=summary_path,
            report_dict=report_dict,
            db_manager=db_manager
        )

    print("\n전국 수집 프로그램 실행이 정상적으로 마무리되었습니다.")


if __name__ == "__main__":
    main()
