"""
Stage 4C: 브랜드 마스터 데이터베이스 스키마 정의 및 초기화 모듈
프로젝트: D:/Franchise_Dashboard
위치: src/stage4c/schema_stage4c.py
"""

import sqlite3
from pathlib import Path
from typing import Optional

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DEFAULT_STAGE4C_DB_PATH = BASE_DIR / "data" / "brand_master_v1.sqlite3"

SCHEMA_STAGE4C_DDL = """
-- 1. brands: 내부 브랜드 마스터 엔터티
CREATE TABLE IF NOT EXISTS brands (
    internal_brand_id TEXT PRIMARY KEY,
    candidate_brand_id TEXT UNIQUE NOT NULL,
    brand_name_std TEXT NOT NULL,
    brand_name_core TEXT NOT NULL,
    brand_name_clean TEXT NOT NULL,
    brand_officiality TEXT NOT NULL, -- FRANCHISE_CONFIRMED, BRAND_CONFIRMED, UNVERIFIED, REJECTED
    category_major TEXT NOT NULL,
    representative_inds_mcls_cd TEXT,
    representative_inds_scls_cd TEXT,
    discovery_method TEXT NOT NULL,
    total_store_count INTEGER NOT NULL DEFAULT 0,
    verified_store_count INTEGER NOT NULL DEFAULT 0,
    provisional_store_count INTEGER NOT NULL DEFAULT 0,
    review_required_store_count INTEGER NOT NULL DEFAULT 0,
    review_priority_score REAL NOT NULL DEFAULT 0.0,
    current_review_status TEXT NOT NULL DEFAULT 'PENDING', -- APPROVED, REJECTED, PENDING
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- 2. brand_aliases: 공식/비공식 별칭 매핑 테이블
CREATE TABLE IF NOT EXISTS brand_aliases (
    alias_id INTEGER PRIMARY KEY AUTOINCREMENT,
    internal_brand_id TEXT NOT NULL,
    alias_text TEXT NOT NULL,
    alias_norm TEXT NOT NULL,
    alias_type TEXT NOT NULL, -- OFFICIAL_NAME, ENGLISH_NAME, ACRONYM, POPULAR_NAME, TYPO_FALLBACK
    is_official INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (internal_brand_id) REFERENCES brands(internal_brand_id)
);

-- 3. brand_sources: 공식 출처 및 기준일 이력 테이블
CREATE TABLE IF NOT EXISTS brand_sources (
    source_id INTEGER PRIMARY KEY AUTOINCREMENT,
    internal_brand_id TEXT NOT NULL,
    source_name TEXT NOT NULL,
    source_url TEXT,
    document_name TEXT,
    reference_date TEXT NOT NULL,
    verified_at TEXT NOT NULL,
    FOREIGN KEY (internal_brand_id) REFERENCES brands(internal_brand_id)
);

-- 4. brand_franchise_evidence: 가맹사업 공식성 근거 테이블
CREATE TABLE IF NOT EXISTS brand_franchise_evidence (
    evidence_id INTEGER PRIMARY KEY AUTOINCREMENT,
    internal_brand_id TEXT NOT NULL,
    operating_entity TEXT,
    business_reg_no TEXT,
    franchise_reg_no TEXT,
    is_franchise_business INTEGER, -- 1: 가맹사업, 0: 직영만 운영, NULL: 미확인
    evidence_grade TEXT NOT NULL, -- A_OFFICIAL_REGISTRATION, B_CORPORATE_VERIFIED, C_STATISTICAL_CLUSTER, D_DEFICIENT
    evidence_notes TEXT,
    FOREIGN KEY (internal_brand_id) REFERENCES brands(internal_brand_id)
);

-- 5. store_brand_links: 점포-브랜드 N:M 연결 관계 테이블
CREATE TABLE IF NOT EXISTS store_brand_links (
    link_id INTEGER PRIMARY KEY AUTOINCREMENT,
    bizes_id TEXT NOT NULL,
    internal_brand_id TEXT, -- NULL 또는 'BRD_UNMATCHED' 허용
    match_status TEXT NOT NULL, -- MATCH_VERIFIED, MATCH_AUTO_HIGH_CONFIDENCE, MATCH_PROVISIONAL, REVIEW_REQUIRED, UNMATCHED, MATCH_REJECTED
    operation_type TEXT NOT NULL DEFAULT 'UNKNOWN', -- FRANCHISED, COMPANY_OPERATED, OTHER, UNKNOWN
    confidence_score REAL NOT NULL,
    is_primary_link INTEGER NOT NULL DEFAULT 1,
    match_method TEXT NOT NULL,
    notes TEXT,
    linked_at TEXT NOT NULL,
    FOREIGN KEY (internal_brand_id) REFERENCES brands(internal_brand_id)
);

-- 6. brand_reviews: 승인·거절·보류 심사 및 수동 검토 보존 테이블
CREATE TABLE IF NOT EXISTS brand_reviews (
    review_id INTEGER PRIMARY KEY AUTOINCREMENT,
    target_type TEXT NOT NULL, -- BRAND, STORE_LINK
    target_id TEXT NOT NULL,
    review_decision TEXT NOT NULL, -- APPROVED, REJECTED, PENDING
    decision_reason TEXT NOT NULL,
    reviewer TEXT NOT NULL, -- SYSTEM_AUTO, HUMAN_EXPERT
    is_persistent INTEGER NOT NULL DEFAULT 1,
    reviewed_at TEXT NOT NULL
);

-- 7. matching_rules: 매칭 규칙 및 버전 메타데이터 테이블
CREATE TABLE IF NOT EXISTS matching_rules (
    rule_id INTEGER PRIMARY KEY AUTOINCREMENT,
    rule_version TEXT NOT NULL,
    rule_type TEXT NOT NULL,
    description TEXT NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1,
    registered_at TEXT NOT NULL
);

-- 8. brand_history: 개명·합병·분리 등 이력 관리 테이블
CREATE TABLE IF NOT EXISTS brand_history (
    history_id INTEGER PRIMARY KEY AUTOINCREMENT,
    internal_brand_id TEXT NOT NULL,
    event_type TEXT NOT NULL, -- CREATION, REBRANDING, MERGER, SPLIT, STATUS_CHANGE
    before_value TEXT,
    after_value TEXT,
    event_date TEXT NOT NULL,
    notes TEXT,
    FOREIGN KEY (internal_brand_id) REFERENCES brands(internal_brand_id)
);

-- 9. data_quality_audits: 품질 평가 및 검증 지표 테이블
CREATE TABLE IF NOT EXISTS data_quality_audits (
    audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    audit_scope TEXT NOT NULL,
    metric_name TEXT NOT NULL,
    metric_value REAL NOT NULL,
    threshold_value REAL,
    confidence_interval_low REAL,
    confidence_interval_high REAL,
    audit_verdict TEXT NOT NULL,
    sample_size INTEGER NOT NULL,
    notes TEXT,
    audited_at TEXT NOT NULL
);

-- 10. independent_eval_samples: 독립 품질 평가 표본 테이블
CREATE TABLE IF NOT EXISTS independent_eval_samples (
    sample_id INTEGER PRIMARY KEY AUTOINCREMENT,
    bizes_id TEXT NOT NULL,
    raw_bizes_nm TEXT NOT NULL,
    clean_bizes_nm TEXT NOT NULL,
    sample_stratum TEXT NOT NULL, -- TRUE_FRANCHISE, HARD_NEGATIVE_SIMILAR, INDEPENDENT_NON_BRAND, MULTI_BRAND_SHOP, GENERIC_FOOD_WORD, REGIONAL_CHAIN
    ground_truth_brand_id TEXT,
    ground_truth_label INTEGER NOT NULL, -- 1: 참 소속, 0: 비소속/오탐
    ground_truth_evidence TEXT NOT NULL,
    predicted_brand_id TEXT,
    predicted_match_status TEXT,
    is_correct INTEGER,
    evaluated_at TEXT NOT NULL
);

-- 11. 성능 최적화 인덱스
CREATE INDEX IF NOT EXISTS idx_brands_std_name ON brands(brand_name_std);
CREATE INDEX IF NOT EXISTS idx_brands_officiality ON brands(brand_officiality);
CREATE INDEX IF NOT EXISTS idx_brands_category ON brands(category_major);
CREATE INDEX IF NOT EXISTS idx_brands_cand_id ON brands(candidate_brand_id);
CREATE INDEX IF NOT EXISTS idx_brand_aliases_norm ON brand_aliases(alias_norm);
CREATE INDEX IF NOT EXISTS idx_store_brand_links_bizes ON store_brand_links(bizes_id);
CREATE INDEX IF NOT EXISTS idx_store_brand_links_brand ON store_brand_links(internal_brand_id);
CREATE INDEX IF NOT EXISTS idx_store_brand_links_status ON store_brand_links(match_status);
CREATE INDEX IF NOT EXISTS idx_store_brand_links_op ON store_brand_links(operation_type);
CREATE INDEX IF NOT EXISTS idx_brand_reviews_target ON brand_reviews(target_type, target_id);
"""

def initialize_stage4c_database(db_path: Optional[Path] = None) -> Path:
    """Stage 4C 브랜드 마스터 SQLite 데이터베이스를 WAL 모드로 초기화한다."""
    target_path = db_path or DEFAULT_STAGE4C_DB_PATH
    target_path.parent.mkdir(parents=True, exist_ok=True)
    
    con = sqlite3.connect(target_path)
    cur = con.cursor()
    cur.execute("PRAGMA journal_mode=WAL;")
    cur.execute("PRAGMA synchronous=NORMAL;")
    cur.execute("PRAGMA foreign_keys=ON;")
    cur.executescript(SCHEMA_STAGE4C_DDL)
    con.commit()
    con.close()
    return target_path

if __name__ == "__main__":
    db = initialize_stage4c_database()
    print(f"[OK] Initialized Stage 4C Brand Master Database at: {db}")
