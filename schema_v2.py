#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Franchise Dashboard — Phase 3 신규 데이터베이스 스키마 정의 (schema_v2.py)
Target DB: data/nationwide_food_stores_v2.sqlite3

특징:
  1. 원본 API 지역정보(raw_*) 및 표준 정규화 지역정보(std_*) 동시 보존
  2. 공간 인덱스(lat, lon) 및 고속 조회 복합 인덱스 완비
  3. 무결성 계약(raw - excluded == saved) 및 수집 이력 추적(collection_logs)
  4. 8대 대분류 / 48대 중분류 체계(category_mappings) 탑재
  5. 브랜드 마스터(brand_masters, brand_aliases) 및 공정위 연계 인터페이스(ftc_interfaces) 확장 구조 제공
  6. 3D GIS 지도 렌더링용 집계 뷰(regional_3d_summary) 제공
"""

import sqlite3
import sys
from pathlib import Path
from typing import Optional

DDL_STATEMENTS = """
-- 1. 전국 외식업 점포 마스터 테이블 (stores)
CREATE TABLE IF NOT EXISTS stores (
    bizes_id                TEXT PRIMARY KEY,                  -- 상가업소번호 (소진공 고유식별자)
    bizes_nm                TEXT NOT NULL,                     -- 상호명
    brch_nm                 TEXT,                              -- 지점명
    inds_lcls_cd            TEXT NOT NULL,                     -- 업종대분류코드 ('I2': 음식)
    inds_lcls_nm            TEXT NOT NULL,                     -- 업종대분류명
    inds_mcls_cd            TEXT NOT NULL,                     -- 업종중분류코드 (I201, I202 등)
    inds_mcls_nm            TEXT NOT NULL,                     -- 업종중분류명
    inds_scls_cd            TEXT NOT NULL,                     -- 업종소분류코드
    inds_scls_nm            TEXT NOT NULL,                     -- 업종소분류명
    ksic_cd                 TEXT,                              -- 표준산업분류코드
    ksic_nm                 TEXT,                              -- 표준산업분류명
    
    -- [API 원본 지역정보]
    raw_ctprvn_cd           TEXT NOT NULL,                     -- API 반환 시도코드
    raw_ctprvn_nm           TEXT NOT NULL,                     -- API 반환 시도명
    raw_signgu_cd           TEXT NOT NULL,                     -- API 반환 시군구코드
    raw_signgu_nm           TEXT NOT NULL,                     -- API 반환 시군구명
    raw_adong_cd            TEXT,                              -- 행정동코드
    raw_adong_nm            TEXT,                              -- 행정동명
    raw_ldong_cd            TEXT,                              -- 법정동코드
    raw_ldong_nm            TEXT,                              -- 법정동명
    
    -- [표준 정규화 지역정보]
    std_sido_code           TEXT NOT NULL,                     -- 정규화 시도코드 (예: 11, 12, 51, 52)
    std_sido_name           TEXT NOT NULL,                     -- 정규화 시도명 (예: 서울특별시, 전남광주통합특별시)
    std_signgu_code         TEXT NOT NULL,                     -- 정규화 시군구코드 (소진공 조회용)
    std_signgu_name         TEXT NOT NULL,                     -- 정규화 시군구명
    dashboard_region_code   TEXT NOT NULL,                     -- 대시보드 및 3D GIS 렌더링용 고유코드
    
    -- [주소 및 좌표]
    rdnm_adr                TEXT,                              -- 도로명주소
    lno_adr                 TEXT,                              -- 지번주소
    new_zipcd               TEXT,                              -- 신우편번호
    lon                     REAL NOT NULL,                     -- 경도 (WGS84, 124.0 ~ 132.0 범위)
    lat                     REAL NOT NULL,                     -- 위도 (WGS84, 33.0 ~ 39.0 범위)
    
    -- [데이터 관리 및 감사]
    stdr_ym                 TEXT NOT NULL,                     -- 데이터 기준월 (예: '202606')
    data_source             TEXT NOT NULL,                     -- 데이터 유입 출처 ('MIGRATED_V1', 'NEW_COLLECTED')
    raw_json                TEXT,                              -- API 응답 원본 JSON 전문
    created_at              TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at              TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT chk_coordinates CHECK (lon BETWEEN 124.0 AND 132.0 AND lat BETWEEN 33.0 AND 39.0)
);

-- 2. 행정구역 마스터 테이블 (region_master)
CREATE TABLE IF NOT EXISTS region_master (
    signgu_code             TEXT PRIMARY KEY,                  -- 소진공 API 조회 시군구코드
    official_code           TEXT NOT NULL,                     -- 행정안전부 공식 행정표준코드
    dashboard_code          TEXT NOT NULL,                     -- 대시보드 표출용 지역 식별코드
    sido_code               TEXT NOT NULL,                     -- 시도 코드 (11, 12, 51, 52 등)
    sido_name               TEXT NOT NULL,                     -- 시도 명칭
    signgu_name             TEXT NOT NULL,                     -- 시군구 명칭
    category                TEXT NOT NULL,                     -- '자치구', '일반구', '일반시', '군', '단일시'
    parent_city             TEXT,                              -- 상위 일반시명 (부천시, 화성시, 수원시 등)
    status                  TEXT NOT NULL DEFAULT 'ACTIVE',    -- 'ACTIVE', 'DEPRECATED'
    api_total_count         INTEGER DEFAULT 0,                 -- API 기준 외식업 총 건수 (totalCount)
    saved_store_count       INTEGER DEFAULT 0,                 -- DB 실제 저장 점포 수
    verified_at             TEXT                               -- API 실측 검증 일시
);

-- 3. 수집 배치 및 무결성 검증 로그 (collection_logs)
CREATE TABLE IF NOT EXISTS collection_logs (
    log_id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_id                TEXT NOT NULL,                     -- 배치 식별자
    signgu_code             TEXT NOT NULL,                     -- 대상 시군구코드
    page_no                 INTEGER NOT NULL,                  -- 페이지 번호
    stdr_ym                 TEXT NOT NULL,                     -- 데이터 기준월
    raw_count               INTEGER NOT NULL,                  -- 수신 원본 건수
    excluded_count          INTEGER NOT NULL,                  -- 제외 건수 (주점 I211, 구내식당 I20701)
    saved_count             INTEGER NOT NULL,                  -- 저장 대상 건수
    is_contract_valid       INTEGER NOT NULL,                  -- 계약 수식 일치 여부 (raw - excluded == saved) (1/0)
    api_result_code         TEXT NOT NULL,                     -- API 응답코드 ('00', '03' 등)
    api_result_msg          TEXT,                              -- API 응답 메시지
    ret_signgu_cd           TEXT,                              -- API 반환 시군구코드
    ret_signgu_nm           TEXT,                              -- API 반환 시군구명
    collected_at            TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 4. 8대 대분류 / 48대 중분류 매핑 마스터 (category_mappings)
CREATE TABLE IF NOT EXISTS category_mappings (
    scls_code               TEXT PRIMARY KEY,                  -- 소분류코드 (예: I20101)
    scls_name               TEXT NOT NULL,                     -- 소분류명
    mcls_code               TEXT NOT NULL,                     -- 중분류코드 (예: I201)
    mcls_name               TEXT NOT NULL,                     -- 중분류명
    major_category          TEXT NOT NULL,                     -- 확정 8대 대분류
    middle_category         TEXT NOT NULL                      -- 확정 48대 중분류
);

-- 5. 브랜드 마스터 확장 준비 테이블 (brand_masters)
CREATE TABLE IF NOT EXISTS brand_masters (
    brand_id                INTEGER PRIMARY KEY AUTOINCREMENT,
    standard_name           TEXT NOT NULL UNIQUE,              -- 정규화된 공식 브랜드명
    major_category          TEXT NOT NULL,                     -- 8대 대분류
    middle_category         TEXT NOT NULL,                     -- 48대 중분류
    is_franchise            INTEGER NOT NULL DEFAULT 0,        -- 검증된 프랜차이즈 여부 (1: 프랜차이즈, 0: 후보/개인)
    nationwide_count        INTEGER DEFAULT 0,                 -- 전국 점포수
    threshold_passed        INTEGER DEFAULT 0,                 -- 전국 10개 이상 점포 기준 충족 여부 (1/0)
    created_at              TEXT DEFAULT CURRENT_TIMESTAMP
);

-- 6. 브랜드 별칭 및 표기 변형 매핑 테이블 (brand_aliases)
CREATE TABLE IF NOT EXISTS brand_aliases (
    alias_id                INTEGER PRIMARY KEY AUTOINCREMENT,
    brand_id                INTEGER NOT NULL REFERENCES brand_masters(brand_id),
    alias_pattern           TEXT NOT NULL UNIQUE,              -- 별칭/영문/표기 변형 (예: 'STARBUCKS', '스타벅스커피')
    match_type              TEXT NOT NULL DEFAULT 'EXACT'      -- 'EXACT', 'REGEX', 'CONTAINS'
);

-- 7. 공정거래위원회 가맹정보 API 연계 인터페이스 (ftc_interfaces)
CREATE TABLE IF NOT EXISTS ftc_interfaces (
    ftc_id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    brand_name              TEXT NOT NULL,                     -- 공정위 등록 브랜드명
    corp_name               TEXT,                              -- 가맹본부 법인명
    registration_no         TEXT UNIQUE,                       -- 정보공개서 등록번호
    category_name           TEXT,                              -- 공정위 외식 업종분류
    official_store_count    INTEGER,                           -- 공정위 등록 점포 수
    avg_sales_amount        REAL,                              -- 연평균 매출액
    initial_cost            REAL,                              -- 가맹 초기비용
    sync_status             TEXT DEFAULT 'READY',              -- 'READY', 'SYNCED', 'MISMATCH'
    verified_state          TEXT DEFAULT 'UNVERIFIED',         -- 연계 검증 상태 ('UNVERIFIED', 'VERIFIED_MATCH', 'MANUAL_REVIEW')
    last_synced_at          TEXT
);

-- 8. 검증 실패 및 격리 대상 데이터 보관 테이블 (quarantine_stores)
CREATE TABLE IF NOT EXISTS quarantine_stores (
    quarantine_id           INTEGER PRIMARY KEY AUTOINCREMENT,
    bizes_id                TEXT,                              -- 상가업소번호 (있는 경우)
    bizes_nm                TEXT,                              -- 상호명
    reason                  TEXT NOT NULL,                     -- 격리 사유 (좌표이상, 지역코드불일치, 기준월불일치 등)
    raw_ctprvn_cd           TEXT,
    raw_signgu_cd           TEXT,
    raw_signgu_nm           TEXT,
    raw_json                TEXT,                              -- 원본 데이터 전문
    quarantined_at          TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 9. 복구 단계별 체크포인트 관리 테이블 (recovery_checkpoints)
CREATE TABLE IF NOT EXISTS recovery_checkpoints (
    checkpoint_key          TEXT PRIMARY KEY,                  -- 고유 체크포인트 키 (예: 'MIGRATION_V1_COMPLETE', 'SUPP_12110')
    stage_name              TEXT NOT NULL,                     -- 단계 ('MIGRATION', 'SUPPLEMENTARY', 'VERIFICATION')
    target_code             TEXT,                              -- 대상 시군구코드
    status                  TEXT NOT NULL,                     -- 'IN_PROGRESS', 'COMPLETED', 'FAILED'
    record_count            INTEGER DEFAULT 0,                 -- 처리 건수
    detail_note             TEXT,                              -- 상세 비고
    updated_at              TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 10. 3D GIS 대시보드 렌더링용 고속 집계 뷰 (regional_3d_summary)
CREATE VIEW IF NOT EXISTS regional_3d_summary AS
SELECT 
    std_sido_code,
    std_sido_name,
    std_signgu_code,
    std_signgu_name,
    dashboard_region_code,
    stdr_ym,
    COUNT(*) AS total_stores,
    AVG(lon) AS center_lon,
    AVG(lat) AS center_lat,
    COUNT(DISTINCT inds_mcls_cd) AS distinct_mcls_count
FROM stores
GROUP BY std_sido_code, std_signgu_code, stdr_ym;

-- 11. 전국 10개 이상 점포 브랜드 후보 자동 추출 뷰 (brand_candidates_view)
CREATE VIEW IF NOT EXISTS brand_candidates_view AS
SELECT 
    bizes_nm,
    inds_mcls_cd,
    inds_mcls_nm,
    COUNT(*) AS nationwide_store_count,
    COUNT(DISTINCT std_sido_code) AS province_spread_count,
    COUNT(DISTINCT std_signgu_code) AS district_spread_count,
    MIN(stdr_ym) AS earliest_ym,
    MAX(stdr_ym) AS latest_ym
FROM stores
GROUP BY bizes_nm, inds_mcls_cd
HAVING COUNT(*) >= 10;

-- [성능 최적화 인덱스 설계]
CREATE INDEX IF NOT EXISTS idx_stores_spatial ON stores(lat, lon);
CREATE INDEX IF NOT EXISTS idx_stores_sido_signgu ON stores(std_sido_code, std_signgu_code);
CREATE INDEX IF NOT EXISTS idx_stores_dashboard ON stores(dashboard_region_code);
CREATE INDEX IF NOT EXISTS idx_stores_mcls ON stores(inds_mcls_cd);
CREATE INDEX IF NOT EXISTS idx_stores_name ON stores(bizes_nm);
CREATE INDEX IF NOT EXISTS idx_stores_stdr_ym ON stores(stdr_ym);
CREATE INDEX IF NOT EXISTS idx_logs_batch_signgu ON collection_logs(batch_id, signgu_code);
CREATE INDEX IF NOT EXISTS idx_quarantine_reason ON quarantine_stores(reason);
CREATE INDEX IF NOT EXISTS idx_checkpoints_stage ON recovery_checkpoints(stage_name, status);
"""


def init_database(db_path: Path) -> sqlite3.Connection:
    """신규 SQLite 데이터베이스를 생성하고 최적화 PRAGMA 및 DDL을 실행합니다."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(db_path)
    con.execute("PRAGMA journal_mode = WAL;")
    con.execute("PRAGMA synchronous = NORMAL;")
    con.execute("PRAGMA foreign_keys = ON;")
    con.executescript(DDL_STATEMENTS)
    con.commit()
    return con


if __name__ == "__main__":
    test_db = Path("data/nationwide_food_stores_v2_schema_test.sqlite3")
    print(f"Creating test schema at: {test_db}")
    con = init_database(test_db)
    cur = con.cursor()
    tables = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    views = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='view'").fetchall()]
    indexes = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='index'").fetchall()]
    print(f"Tables ({len(tables)}): {tables}")
    print(f"Views ({len(views)}): {views}")
    print(f"Indexes ({len(indexes)}): {indexes}")
    con.close()
    if test_db.exists():
        test_db.unlink()
        wal = test_db.with_name(test_db.name + "-wal")
        shm = test_db.with_name(test_db.name + "-shm")
        if wal.exists(): wal.unlink()
        if shm.exists(): shm.unlink()
    print("Schema v2 successfully verified!")
