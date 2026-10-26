#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Franchise Dashboard — Phase 4 Stage 4A 신규 데이터베이스 스키마 정의
Target DB: data/brand_intelligence_stage4a.sqlite3

엔터티 구성:
  A. api_sources: 공정위 등 공식 API 출처 메타데이터
  B. ftc_raw_records: 공정위 실제 API 원본 응답 페이로드 및 호출 메타
  C. ftc_brand_candidates: 공정위 원본 브랜드/가맹 통계 후보 (가명관리번호, 가맹점수, 매출 등)
  D. brand_identity_proposals: 내부 brand_id 및 식별자 연계 제안 모델
  E. store_brand_match_samples: 소진공 점포와 브랜드 표본 매칭 실험 데이터
  F. data_quality_results: 데이터 무결성, API 검증, 이상치 감사 로그
  G. pipeline_runs: 파이프라인 실행 이력 및 API 호출 예산 추적
"""

import sqlite3
import sys
from pathlib import Path
from typing import Optional

BASE_DIR = Path("D:/Franchise_Dashboard")
DEFAULT_STAGE4A_DB_PATH = BASE_DIR / "data" / "brand_intelligence_stage4a.sqlite3"

DDL_STATEMENTS = """
-- 1. 공식 API 출처 메타데이터 (api_sources)
CREATE TABLE IF NOT EXISTS api_sources (
    source_id               TEXT PRIMARY KEY,              -- 출처 식별자 (예: 'FTC_EATOUT_STATS_V2')
    agency_name             TEXT NOT NULL,                 -- 제공 기관명 ('공정거래위원회')
    service_name            TEXT NOT NULL,                 -- 서비스명 ('(AI친화)가맹정보_브랜드 가맹사업자 통합정보 외식업종 현황 제공 서비스')
    portal_data_id          TEXT NOT NULL,                 -- 공공데이터포털 데이터 ID ('15165094')
    endpoint_url            TEXT NOT NULL,                 -- 엔드포인트 URL
    operation_name          TEXT NOT NULL,                 -- 오퍼레이션명 ('getBrandFrcsBzmnIntgInfoEatoutTpbiz2')
    api_version             TEXT NOT NULL DEFAULT '1.0.0', -- 버전
    spec_type               TEXT NOT NULL DEFAULT 'OPENAPI_SWAGGER', -- 명세 유형
    is_active               INTEGER NOT NULL DEFAULT 1,    -- 활성 여부 (1/0)
    created_at              TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 2. 공정위 API 원본 응답 저장소 (ftc_raw_records)
CREATE TABLE IF NOT EXISTS ftc_raw_records (
    raw_record_id           TEXT PRIMARY KEY,              -- 원본 레코드 식별자 ('RAW_{yr}_{page}_{idx}')
    source_id               TEXT NOT NULL,                 -- 출처 ID (FK -> api_sources)
    run_id                  TEXT NOT NULL,                 -- 파이프라인 실행 ID (FK -> pipeline_runs)
    crtr_yr                 TEXT NOT NULL,                 -- 가맹사업기준연도 (jngBizCrtrYr)
    page_no                 INTEGER NOT NULL,              -- 조회 페이지 번호
    num_of_rows             INTEGER NOT NULL,              -- 요청 건수
    total_count             INTEGER NOT NULL,              -- 전체 결과 건수
    result_code             TEXT NOT NULL,                 -- API 결과코드 ('00', '10', '11' 등)
    result_msg              TEXT NOT NULL,                 -- API 결과메시지
    payload_json            TEXT NOT NULL,                 -- 원본 JSON 레코드 전문 (단일 아이템)
    collected_at            TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (source_id) REFERENCES api_sources(source_id),
    FOREIGN KEY (run_id) REFERENCES pipeline_runs(run_id)
);

-- 3. 공정위 외식업 브랜드/가맹 통계 후보 (ftc_brand_candidates)
CREATE TABLE IF NOT EXISTS ftc_brand_candidates (
    ftc_candidate_id        TEXT PRIMARY KEY,              -- 'FTC_{crtr_yr}_{alsBrandMngNo}'
    raw_record_id           TEXT NOT NULL,                 -- FK -> ftc_raw_records
    crtr_yr                 TEXT NOT NULL,                 -- 기준연도 (YYYY)
    als_brand_mng_no        TEXT NOT NULL,                 -- 가명브랜드관리번호 (15자리)
    als_jnghq_mng_no        TEXT NOT NULL,                 -- 가명가맹본부관리번호 (15자리)
    jnghq_rgn_nm            TEXT,                          -- 가맹본부지역명 (예: 서울, 경기)
    biz_strt_ymd            TEXT,                          -- 가맹사업개시일자 (YYYYMMDD)
    tpbiz_mclsf_nm          TEXT NOT NULL,                 -- 업종중분류명 (한식, 치킨, 커피 등)
    frcs_cnt                INTEGER DEFAULT 0,             -- 가맹점수
    dms_cnt                 INTEGER DEFAULT 0,             -- 직영점수
    total_store_cnt         INTEGER GENERATED ALWAYS AS (COALESCE(frcs_cnt, 0) + COALESCE(dms_cnt, 0)) VIRTUAL,
    prvyr_frcs_cnt          INTEGER DEFAULT 0,             -- 이전연도 가맹점수
    prvyr_dms_cnt           INTEGER DEFAULT 0,             -- 이전연도 직영점수
    jng_amt                 REAL DEFAULT 0.0,              -- 가맹비 (천원)
    edu_amt                 REAL DEFAULT 0.0,              -- 교육비 (천원)
    grnte_amt               REAL DEFAULT 0.0,              -- 보증금 (천원)
    etc_amt                 REAL DEFAULT 0.0,              -- 기타금액 (천원)
    depst_amt               REAL DEFAULT 0.0,              -- 예치금액 (천원)
    unit_area_intrr_amt     REAL DEFAULT 0.0,              -- 단위면적인테리어비용 (천원/평)
    stor_crtr_area          REAL DEFAULT 0.0,              -- 점포기준면적 (평)
    intrr_amt               REAL DEFAULT 0.0,              -- 인테리어총액 (천원)
    fyr                     TEXT,                          -- 결산회계연도 (YYYY)
    avg_sls_amt             REAL DEFAULT 0.0,              -- 가맹점 평균매출액 (천원)
    area_unit_avg_sls_amt   REAL DEFAULT 0.0,              -- 면적단위 평균매출액 (천원/평)
    anonymization_state     TEXT NOT NULL DEFAULT 'PSEUDONYMIZED', -- 'PSEUDONYMIZED', 'CLEAR_NAME'
    verification_status     TEXT NOT NULL DEFAULT 'UNVERIFIED',    -- 'VERIFIED', 'UNVERIFIED', 'PROPOSED'
    created_at              TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (raw_record_id) REFERENCES ftc_raw_records(raw_record_id)
);

-- 4. 내부 브랜드 식별자 연계 제안 (brand_identity_proposals)
CREATE TABLE IF NOT EXISTS brand_identity_proposals (
    proposal_id             TEXT PRIMARY KEY,              -- 'PROP_{UUID}'
    internal_brand_id       TEXT NOT NULL,                 -- 제안 내부 브랜드 ID (예: 'BRD_KOR_0001')
    proposed_brand_name     TEXT NOT NULL,                 -- 제안 브랜드 정규화명 (예: '본죽', '스타벅스')
    category_major          TEXT NOT NULL,                 -- 8대 대분류
    category_middle         TEXT NOT NULL,                 -- 48대 중분류
    identity_source         TEXT NOT NULL,                 -- 'SEMAS_EXTRACTED', 'FTC_LINKED', 'HYBRID_PROPOSAL'
    ftc_candidate_id        TEXT,                          -- 연결된 FTC 후보 ID (존재 시)
    confidence_score        REAL NOT NULL DEFAULT 0.0,     -- 매핑 신뢰도 (0.0 ~ 1.0)
    decision_branch         TEXT NOT NULL DEFAULT 'BRANCH_C', -- 'BRANCH_A', 'BRANCH_B', 'BRANCH_C'
    status                  TEXT NOT NULL DEFAULT 'PROPOSAL', -- 'PROPOSAL', 'APPROVED', 'REJECTED'
    rationale               TEXT,                          -- 제안 근거 및 사유
    created_at              TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at              TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (ftc_candidate_id) REFERENCES ftc_brand_candidates(ftc_candidate_id)
);

-- 5. 소진공 점포-브랜드 표본 매칭 실험 데이터 (store_brand_match_samples)
CREATE TABLE IF NOT EXISTS store_brand_match_samples (
    sample_id               INTEGER PRIMARY KEY AUTOINCREMENT,
    target_brand_name       TEXT NOT NULL,                 -- 실험 대상 브랜드명 (예: '교촌치킨', '스타벅스')
    brand_category_major    TEXT NOT NULL,                 -- 대표 8대 대분류
    bizes_id                TEXT NOT NULL,                 -- 소진공 상가업소번호 (stores.bizes_id)
    raw_bizes_nm            TEXT NOT NULL,                 -- 소진공 원본 상호명 (stores.bizes_nm)
    normalized_bizes_nm     TEXT NOT NULL,                 -- 정규화 상호명
    branch_suffix_removed   TEXT,                          -- 제거된 지점 접미어
    semas_mcls_nm           TEXT,                          -- 소진공 업종중분류명
    sido_name               TEXT,                          -- 시도명
    signgu_name             TEXT,                          -- 시군구명
    match_type              TEXT NOT NULL,                 -- 'EXACT_MATCH', 'NORMALIZED_MATCH', 'AMBIGUOUS_MATCH', 'FALSE_POSITIVE_SUSPECT', 'NON_MATCH'
    match_score             REAL NOT NULL,                 -- 유사도 점수 (0.0 ~ 1.0)
    is_true_positive        INTEGER,                       -- 수동 검토 참/거짓 (1: 참, 0: 오탐, NULL: 미판정)
    review_status           TEXT NOT NULL DEFAULT 'PENDING', -- 'PENDING', 'VERIFIED_TP', 'CONFIRMED_FP', 'NEEDS_RULE'
    notes                   TEXT,                          -- 비고 및 특이사항
    created_at              TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 6. 데이터 품질 검증 및 오류 감사 (data_quality_results)
CREATE TABLE IF NOT EXISTS data_quality_results (
    audit_id                INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id                  TEXT NOT NULL,                 -- FK -> pipeline_runs
    audit_category          TEXT NOT NULL,                 -- 'API_VERIFICATION', 'SCHEMA_INTEGRITY', 'KEY_STABILITY', 'MATCH_EXPERIMENT'
    assertion_name          TEXT NOT NULL,                 -- 검증 규칙명
    assertion_status        TEXT NOT NULL,                 -- 'PASS', 'FAIL', 'CONDITIONAL', 'WARNING'
    target_dataset          TEXT NOT NULL,                 -- 검증 대상 ('FTC_API', 'SEMAS_V2_DB', 'STAGE4A_DB')
    actual_value            TEXT,                          -- 실측값
    expected_value          TEXT,                          -- 기댓값
    detail_message          TEXT,                          -- 상세 메시지
    created_at              TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (run_id) REFERENCES pipeline_runs(run_id)
);

-- 7. 파이프라인 실행 이력 및 예산 추적 (pipeline_runs)
CREATE TABLE IF NOT EXISTS pipeline_runs (
    run_id                  TEXT PRIMARY KEY,              -- 'RUN_4A_{YYYYMMDD_HHMMSS}'
    stage_name              TEXT NOT NULL DEFAULT 'STAGE_4A',
    description             TEXT,
    call_budget_limit       INTEGER NOT NULL DEFAULT 30,   -- API 호출 예산 상한
    actual_calls_made       INTEGER NOT NULL DEFAULT 0,    -- 실제 실행된 API 호출 수
    total_records_ingested  INTEGER NOT NULL DEFAULT 0,    -- 적재된 레코드 수
    sample_matches_tested   INTEGER NOT NULL DEFAULT 0,    -- 매칭 실험 점포 수
    status                  TEXT NOT NULL DEFAULT 'RUNNING', -- 'RUNNING', 'COMPLETED', 'FAILED', 'ABORTED'
    error_summary           TEXT,
    started_at              TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at            TEXT
);

-- 성능 최적화 인덱스
CREATE INDEX IF NOT EXISTS idx_ftc_cand_yr ON ftc_brand_candidates(crtr_yr);
CREATE INDEX IF NOT EXISTS idx_ftc_cand_brand ON ftc_brand_candidates(als_brand_mng_no);
CREATE INDEX IF NOT EXISTS idx_ftc_cand_jnghq ON ftc_brand_candidates(als_jnghq_mng_no);
CREATE INDEX IF NOT EXISTS idx_ftc_cand_tpbiz ON ftc_brand_candidates(tpbiz_mclsf_nm);
CREATE INDEX IF NOT EXISTS idx_match_samples_brand ON store_brand_match_samples(target_brand_name);
CREATE INDEX IF NOT EXISTS idx_match_samples_type ON store_brand_match_samples(match_type);
CREATE INDEX IF NOT EXISTS idx_match_samples_bizes ON store_brand_match_samples(bizes_id);
CREATE INDEX IF NOT EXISTS idx_quality_category ON data_quality_results(audit_category, assertion_status);
"""


def init_stage4a_database(db_path: Optional[Path] = None) -> sqlite3.Connection:
    """Stage 4A 전용 지능형 데이터베이스 초기화"""
    path = db_path or DEFAULT_STAGE4A_DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path)
    con.execute("PRAGMA journal_mode = WAL;")
    con.execute("PRAGMA synchronous = NORMAL;")
    con.execute("PRAGMA foreign_keys = ON;")
    con.executescript(DDL_STATEMENTS)
    con.commit()
    
    # 기본 api_sources 초기 등록
    cur = con.cursor()
    cur.execute("""
        INSERT OR IGNORE INTO api_sources (
            source_id, agency_name, service_name, portal_data_id, endpoint_url, operation_name, api_version
        ) VALUES (
            'FTC_EATOUT_STATS_V2',
            '공정거래위원회',
            '(AI친화)가맹정보_브랜드 가맹사업자 통합정보 외식업종 현황 제공 서비스',
            '15165094',
            'https://apis.data.go.kr/1130000/FftcBrandFrcsBzmnIntgInfoEatoutTpbizStats2_Service/getBrandFrcsBzmnIntgInfoEatoutTpbiz2',
            'getBrandFrcsBzmnIntgInfoEatoutTpbiz2',
            '1.0.0'
        )
    """)
    con.commit()
    return con


if __name__ == "__main__":
    test_db = BASE_DIR / "data" / "brand_intelligence_stage4a_test.sqlite3"
    print(f"Testing Stage 4A DB Schema at: {test_db}")
    con = init_stage4a_database(test_db)
    cur = con.cursor()
    tables = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    print("Created tables:", tables)
    assert len(tables) >= 7, f"Expected at least 7 tables, got {len(tables)}"
    con.close()
    if test_db.exists():
        test_db.unlink()
        for extra in [test_db.with_name(test_db.name + "-wal"), test_db.with_name(test_db.name + "-shm")]:
            if extra.exists(): extra.unlink()
    print("Stage 4A Schema successfully verified!")
