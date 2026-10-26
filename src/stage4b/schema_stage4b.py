"""
Stage 4B: 브랜드 후보 데이터베이스 스키마 정의 및 초기화 모듈
프로젝트: D:/Franchise_Dashboard
위치: src/stage4b/schema_stage4b.py
"""

import sqlite3
from pathlib import Path
from typing import Optional

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DEFAULT_STAGE4B_DB_PATH = BASE_DIR / "data" / "brand_candidates_v1.sqlite3"

SCHEMA_STAGE4B_DDL = """
-- 1. 브랜드 후보 마스터 테이블
CREATE TABLE IF NOT EXISTS brand_candidates (
    candidate_brand_id TEXT PRIMARY KEY,
    brand_name_raw TEXT NOT NULL,
    brand_name_norm TEXT NOT NULL,
    brand_name_clean TEXT NOT NULL,
    category_major TEXT NOT NULL,
    representative_inds_mcls_cd TEXT,
    representative_inds_scls_cd TEXT,
    discovery_method TEXT NOT NULL,
    official_source TEXT,
    total_store_count INTEGER NOT NULL DEFAULT 0,
    verification_status TEXT NOT NULL,
    rule_version TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- 2. 점포 상호명 정규화 및 원본 보존 테이블
CREATE TABLE IF NOT EXISTS store_normalization (
    bizes_id TEXT PRIMARY KEY,
    raw_bizes_nm TEXT NOT NULL,
    normalized_core_nm TEXT NOT NULL,
    branch_suffix TEXT,
    branch_position TEXT NOT NULL DEFAULT 'NONE',
    legal_entity_tag TEXT,
    is_reconstructible INTEGER NOT NULL DEFAULT 1,
    processed_at TEXT NOT NULL
);

-- 3. 점포-브랜드 후보 매핑 테이블 (N:M 지원)
CREATE TABLE IF NOT EXISTS store_brand_candidates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bizes_id TEXT NOT NULL,
    candidate_brand_id TEXT NOT NULL,
    match_method TEXT NOT NULL,
    confidence_score REAL NOT NULL,
    store_verification_status TEXT NOT NULL,
    franchisor_status TEXT NOT NULL DEFAULT 'UNCONFIRMED',
    branch_operation_type TEXT NOT NULL DEFAULT 'UNKNOWN',
    is_primary_candidate INTEGER NOT NULL DEFAULT 1,
    notes TEXT,
    rule_version TEXT NOT NULL,
    evaluated_at TEXT NOT NULL,
    FOREIGN KEY (candidate_brand_id) REFERENCES brand_candidates(candidate_brand_id)
);

-- 4. 브랜드 별칭 테이블
CREATE TABLE IF NOT EXISTS brand_aliases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    candidate_brand_id TEXT NOT NULL,
    alias_text TEXT NOT NULL,
    alias_norm TEXT NOT NULL,
    alias_type TEXT NOT NULL DEFAULT 'SYNONYM',
    is_official INTEGER NOT NULL DEFAULT 1,
    FOREIGN KEY (candidate_brand_id) REFERENCES brand_candidates(candidate_brand_id)
);

-- 5. 검증 평가 라벨링 표본 테이블 (Stage 4A 표본 및 골드 스탠다드)
CREATE TABLE IF NOT EXISTS labeled_evaluation_samples (
    sample_id INTEGER PRIMARY KEY AUTOINCREMENT,
    bizes_id TEXT NOT NULL,
    raw_bizes_nm TEXT NOT NULL,
    normalized_bizes_nm TEXT NOT NULL,
    target_brand_name TEXT NOT NULL,
    category_major TEXT NOT NULL,
    ground_truth_label INTEGER NOT NULL, -- 1: TP, 0: FP
    ground_truth_brand_id TEXT,
    ground_truth_rationale TEXT NOT NULL,
    predicted_candidate_id TEXT,
    predicted_status TEXT,
    is_correct INTEGER,
    evaluated_at TEXT NOT NULL
);

-- 6. 데이터 품질 및 성능 평가 지표 테이블
CREATE TABLE IF NOT EXISTS quality_metrics (
    metric_id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    metric_name TEXT NOT NULL,
    metric_value REAL NOT NULL,
    threshold_value REAL,
    status TEXT NOT NULL,
    sample_size INTEGER,
    notes TEXT,
    measured_at TEXT NOT NULL
);

-- 7. 파이프라인 실행 및 감사 로그 테이블
CREATE TABLE IF NOT EXISTS candidate_audit_log (
    audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    batch_step TEXT NOT NULL,
    start_time TEXT NOT NULL,
    end_time TEXT,
    total_processed INTEGER NOT NULL DEFAULT 0,
    matched_stores INTEGER NOT NULL DEFAULT 0,
    unmatched_stores INTEGER NOT NULL DEFAULT 0,
    multi_candidate_stores INTEGER NOT NULL DEFAULT 0,
    duration_seconds REAL,
    throughput_stores_per_sec REAL,
    peak_memory_mb REAL,
    status TEXT NOT NULL,
    log_message TEXT
);

-- 8. 성능 최적화 인덱스
CREATE INDEX IF NOT EXISTS idx_brand_cand_name_clean ON brand_candidates(brand_name_clean);
CREATE INDEX IF NOT EXISTS idx_brand_cand_status ON brand_candidates(verification_status);
CREATE INDEX IF NOT EXISTS idx_brand_cand_cat ON brand_candidates(category_major);
CREATE INDEX IF NOT EXISTS idx_store_norm_core ON store_normalization(normalized_core_nm);
CREATE INDEX IF NOT EXISTS idx_store_cand_bizes ON store_brand_candidates(bizes_id);
CREATE INDEX IF NOT EXISTS idx_store_cand_brand ON store_brand_candidates(candidate_brand_id);
CREATE INDEX IF NOT EXISTS idx_store_cand_status ON store_brand_candidates(store_verification_status);
CREATE INDEX IF NOT EXISTS idx_brand_aliases_norm ON brand_aliases(alias_norm);
"""

def initialize_stage4b_database(db_path: Optional[Path] = None) -> Path:
    """Stage 4B 브랜드 후보 SQLite 데이터베이스를 WAL 모드로 초기화한다."""
    target_path = db_path or DEFAULT_STAGE4B_DB_PATH
    target_path.parent.mkdir(parents=True, exist_ok=True)
    
    con = sqlite3.connect(target_path)
    cur = con.cursor()
    cur.execute("PRAGMA journal_mode=WAL;")
    cur.execute("PRAGMA synchronous=NORMAL;")
    cur.execute("PRAGMA foreign_keys=ON;")
    cur.executescript(SCHEMA_STAGE4B_DDL)
    con.commit()
    con.close()
    return target_path

if __name__ == "__main__":
    db = initialize_stage4b_database()
    print(f"[OK] Initialized Stage 4B Database at: {db}")
