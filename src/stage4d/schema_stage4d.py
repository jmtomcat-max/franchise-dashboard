"""
Stage 4D: 외식업 8대 대분류 및 48대 중분류 마스터 스키마 정의 모듈
프로젝트: D:/Franchise_Dashboard
위치: src/stage4d/schema_stage4d.py
"""

import sqlite3
import os
from pathlib import Path

CATEGORY_MASTER_DB_PATH = Path("d:/Franchise_Dashboard/data/food_category_master_v1.sqlite3")

STAGE4D_SCHEMA_SQL = """
-- ==============================================================================
-- Franchise Dashboard - Phase 4 Stage 4D: Food Category Master Schema
-- ==============================================================================

-- 1. 확정 외식업 8대 대분류 마스터 (major_categories)
CREATE TABLE IF NOT EXISTS major_categories (
    category_maj_id         TEXT PRIMARY KEY,              -- 'CAT_MAJ_01' ~ 'CAT_MAJ_08' (불변 고유키)
    category_maj_name       TEXT NOT NULL UNIQUE,          -- 대분류명 (한식, 중식, 일식 등)
    slot_count              INTEGER NOT NULL,              -- 배정된 중분류 슬롯 개수 (8, 5, 6, 5, 6, 6, 6, 6)
    display_order           INTEGER NOT NULL,              -- 정렬 순서 (1~8)
    description             TEXT,                          -- 대분류 설명
    created_at              TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 2. 확정 외식업 48대 중분류 마스터 (mid_categories)
CREATE TABLE IF NOT EXISTS mid_categories (
    category_mid_id         TEXT PRIMARY KEY,              -- 'CAT_MID_0101' ~ 'CAT_MID_0806' (48개 불변 고유키)
    category_maj_id         TEXT NOT NULL,                 -- FK -> major_categories.category_maj_id
    category_mid_name       TEXT NOT NULL,                 -- 중분류 한글 표준명 (예: '고기구이/육류', '치킨')
    category_mid_name_en    TEXT,                          -- 영문 명칭
    spec_status             TEXT NOT NULL,                 -- 'CONFIRMED_BY_SEMAS_DIRECT', 'CANDIDATE_CONSENSUS', 'PENDING_USER_APPROVAL'
    is_confirmed            INTEGER NOT NULL DEFAULT 0,    -- 공식 합의 확정 여부 (1: 확정, 0: 제안/잠정)
    representative_menu     TEXT,                          -- 대표 메뉴 및 업태 예시
    display_order           INTEGER NOT NULL,              -- 대분류 내 정렬 순서
    created_at              TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at              TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (category_maj_id) REFERENCES major_categories(category_maj_id)
);

-- 3. 소진공 I2 38개 소분류 원본 마스터 (semas_industry_codes)
CREATE TABLE IF NOT EXISTS semas_industry_codes (
    scls_code               TEXT PRIMARY KEY,              -- 소분류코드 ('I20101' 등)
    scls_name               TEXT NOT NULL,                 -- 소분류명 ('백반/한정식' 등)
    mcls_code               TEXT NOT NULL,                 -- 중분류코드 ('I201' 등)
    mcls_name               TEXT NOT NULL,                 -- 중분류명 ('한식' 등)
    lcls_code               TEXT NOT NULL DEFAULT 'I2',    -- 대분류코드 ('I2')
    lcls_name               TEXT NOT NULL DEFAULT '음식',  -- 대분류명 ('음식')
    nationwide_store_count  INTEGER NOT NULL DEFAULT 0,    -- 전국 점포 건수
    created_at              TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 4. 소진공 소분류 <-> 자체 48대 중분류 매핑 마스터 (semas_to_mid_mappings)
CREATE TABLE IF NOT EXISTS semas_to_mid_mappings (
    mapping_id              INTEGER PRIMARY KEY AUTOINCREMENT,
    scls_code               TEXT NOT NULL,                 -- 소진공 소분류코드
    category_mid_id         TEXT NOT NULL,                 -- 48대 중분류코드
    is_primary              INTEGER NOT NULL DEFAULT 1,    -- 대표/기본 매핑 여부 (1/0)
    rule_type               TEXT NOT NULL,                 -- 'DIRECT_MAP', '1_TO_N_SPLIT', 'KEYWORD_RESOLVED', 'DEFAULT_FALLBACK'
    disambiguation_keywords TEXT,                          -- 상호명 키워드 분기 규칙 (쉼표 구분)
    priority                INTEGER NOT NULL DEFAULT 1,    -- 매핑 우선순위 (1이 최고)
    notes                   TEXT,                          -- 매핑 근거 및 사유
    created_at              TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (scls_code) REFERENCES semas_industry_codes(scls_code),
    FOREIGN KEY (category_mid_id) REFERENCES mid_categories(category_mid_id)
);

-- 5. 브랜드 대표 업종 마스터 (brand_category_master)
CREATE TABLE IF NOT EXISTS brand_category_master (
    internal_brand_id       TEXT PRIMARY KEY,              -- 내부 브랜드 ID ('BRD_xxxx')
    brand_name_std          TEXT NOT NULL,                 -- 표준 브랜드명
    category_major_id       TEXT NOT NULL,                 -- 대표 8대 대분류 ID ('CAT_MAJ_xx')
    category_major_name     TEXT NOT NULL,                 -- 대표 8대 대분류명
    category_mid_id         TEXT NOT NULL,                 -- 대표 48대 중분류 ID ('CAT_MID_xxxx')
    category_mid_name       TEXT NOT NULL,                 -- 대표 48대 중분류명
    brand_officiality       TEXT NOT NULL,                 -- 'FRANCHISE_CONFIRMED', 'BRAND_CONFIRMED', 'UNVERIFIED'
    classification_status   TEXT NOT NULL,                 -- 'CATEGORY_CONFIRMED', 'CATEGORY_PROVISIONAL', 'AMBIGUOUS_REVIEW', 'UNCLASSIFIED'
    total_stores            INTEGER NOT NULL DEFAULT 0,    -- 총 소속 점포 수
    representative_inds_scls_cd TEXT,                      -- 소진공 대표 소분류코드
    rationale               TEXT,                          -- 분류 사유 및 근거
    created_at              TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at              TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (category_major_id) REFERENCES major_categories(category_maj_id),
    FOREIGN KEY (category_mid_id) REFERENCES mid_categories(category_mid_id)
);

-- 6. 전국 개별 점포 고유 업종 분류 마스터 (store_category_classifications)
-- (전국 735,185개 고유 점포와 1:1 대응 - 중복 계산 원천 차단)
CREATE TABLE IF NOT EXISTS store_category_classifications (
    bizes_id                TEXT PRIMARY KEY,              -- 소진공 고유 점포 식별자 (전국 735,185건 고유)
    bizes_nm                TEXT NOT NULL,                 -- 점포 상호명
    signgu_cd               TEXT NOT NULL,                 -- 시군구코드 (5자리)
    ctprvn_cd               TEXT NOT NULL,                 -- 시도코드 (2자리)
    inds_mcls_cd            TEXT NOT NULL,                 -- 원본 소진공 중분류코드 보존
    inds_scls_cd            TEXT NOT NULL,                 -- 원본 소진공 소분류코드 보존
    inds_scls_nm            TEXT NOT NULL,                 -- 원본 소진공 소분류명 보존
    primary_brand_id        TEXT NOT NULL,                 -- 주 브랜드 ID (미매칭 시 'BRD_UNMATCHED')
    category_major_id       TEXT NOT NULL,                 -- 최종 확정 8대 대분류 ID
    category_major_name     TEXT NOT NULL,                 -- 최종 확정 8대 대분류명
    category_mid_id         TEXT NOT NULL,                 -- 최종 확정 48대 중분류 ID
    category_mid_name       TEXT NOT NULL,                 -- 최종 확정 48대 중분류명
    classification_status   TEXT NOT NULL,                 -- 'CATEGORY_CONFIRMED', 'CATEGORY_PROVISIONAL', 'AMBIGUOUS_REVIEW', 'UNCLASSIFIED'
    is_brand_linked         INTEGER NOT NULL DEFAULT 0,    -- 브랜드 소속 여부 (1: 브랜드 소속, 0: 미매칭 일반점포)
    is_category_divergent   INTEGER NOT NULL DEFAULT 0,    -- 점포 원본업종과 브랜드 대표업종 간 불일치 여부 (1/0)
    applied_rule            TEXT NOT NULL,                 -- 적용된 분류 규칙 식별자
    lon                     REAL,                          -- WGS84 경도
    lat                     REAL,                          -- WGS84 위도
    created_at              TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (category_major_id) REFERENCES major_categories(category_maj_id),
    FOREIGN KEY (category_mid_id) REFERENCES mid_categories(category_mid_id)
);

-- 7. 점포-브랜드-업종 N:M 연결 마스터 (store_brand_category_links)
-- (23개 복수 브랜드 숍인숍 점포를 온전히 수용하는 735,208건 링크)
CREATE TABLE IF NOT EXISTS store_brand_category_links (
    link_id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    bizes_id                TEXT NOT NULL,                 -- 점포 ID
    internal_brand_id       TEXT NOT NULL,                 -- 브랜드 ID
    category_major_id       TEXT NOT NULL,                 -- 대분류 ID
    category_mid_id         TEXT NOT NULL,                 -- 중분류 ID
    match_status            TEXT NOT NULL,                 -- 'MATCH_VERIFIED', 'MATCH_AUTO_HIGH_CONFIDENCE', 'UNMATCHED' 등
    operation_type          TEXT NOT NULL,                 -- 'COMPANY_OPERATED', 'FRANCHISED', 'UNKNOWN'
    is_primary_link         INTEGER NOT NULL DEFAULT 1,    -- 주 브랜드 여부 (1: 주 브랜드, 0: 보조 브랜드)
    created_at              TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (bizes_id) REFERENCES store_category_classifications(bizes_id),
    FOREIGN KEY (internal_brand_id) REFERENCES brand_category_master(internal_brand_id)
);

-- 8. 복합 메뉴 및 예외 처리 규칙 사전 (category_exception_rules)
CREATE TABLE IF NOT EXISTS category_exception_rules (
    rule_id                 TEXT PRIMARY KEY,              -- 'RULE_EXC_001' 등
    target_brand_id         TEXT,                          -- 대상 브랜드 ID (특정 브랜드 대상 시)
    brand_name_pattern      TEXT,                          -- 브랜드명 패턴
    source_scls_cd          TEXT,                          -- 원본 소진공 코드
    override_category_mid_id TEXT NOT NULL,                -- 강제/대체 매핑될 중분류 ID
    exception_reason        TEXT NOT NULL,                 -- 예외 처리 사유 (예: 본죽&비빔밥 복합메뉴 등)
    is_active               INTEGER NOT NULL DEFAULT 1,    -- 활성 여부
    created_at              TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 9. 품질 평가 및 집계 대사 감사 지표 (category_audit_metrics)
CREATE TABLE IF NOT EXISTS category_audit_metrics (
    audit_id                INTEGER PRIMARY KEY AUTOINCREMENT,
    metric_name             TEXT NOT NULL UNIQUE,          -- 지표명
    metric_value            REAL NOT NULL,                 -- 지표값
    target_dimension        TEXT NOT NULL,                 -- 검증 차원
    status                  TEXT NOT NULL,                 -- 'PASS', 'FAIL', 'WARNING'
    detail_message          TEXT,                          -- 상세 설명
    recorded_at             TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 10. 분류체계 변경 이력 관리 (taxonomy_version_history)
CREATE TABLE IF NOT EXISTS taxonomy_version_history (
    version_id              TEXT PRIMARY KEY,              -- 'VER_001'
    version_tag             TEXT NOT NULL,                 -- 'v1.0.0-stage4d'
    change_summary          TEXT NOT NULL,                 -- 변경 내역
    authorized_by           TEXT NOT NULL,                 -- 승인 주체
    created_at              TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ==============================================================================
-- 인덱스 설계 (대용량 735,185건 고속 조회 최적화)
-- ==============================================================================
CREATE INDEX IF NOT EXISTS idx_store_cat_maj ON store_category_classifications(category_major_id);
CREATE INDEX IF NOT EXISTS idx_store_cat_mid ON store_category_classifications(category_mid_id);
CREATE INDEX IF NOT EXISTS idx_store_cat_status ON store_category_classifications(classification_status);
CREATE INDEX IF NOT EXISTS idx_store_cat_brand ON store_category_classifications(primary_brand_id);
CREATE INDEX IF NOT EXISTS idx_store_cat_rgn ON store_category_classifications(ctprvn_cd, signgu_cd);
CREATE INDEX IF NOT EXISTS idx_store_cat_scls ON store_category_classifications(inds_scls_cd);

CREATE INDEX IF NOT EXISTS idx_links_cat_bizes ON store_brand_category_links(bizes_id);
CREATE INDEX IF NOT EXISTS idx_links_cat_brand ON store_brand_category_links(internal_brand_id);

CREATE INDEX IF NOT EXISTS idx_brand_cat_maj ON brand_category_master(category_major_id);
CREATE INDEX IF NOT EXISTS idx_brand_cat_mid ON brand_category_master(category_mid_id);

-- ==============================================================================
-- Stage 4E 및 Phase 5~6 3D GIS 지도 시각화용 통합 인터페이스 뷰 (Handoff Views)
-- ==============================================================================

-- 뷰 1: 지도 및 지역 통계용 통합 점포-업종 마스터 뷰
CREATE VIEW IF NOT EXISTS v_store_category_master AS
SELECT 
    s.bizes_id,
    s.bizes_nm,
    s.signgu_cd,
    s.ctprvn_cd,
    s.inds_mcls_cd,
    s.inds_scls_cd,
    s.inds_scls_nm,
    s.lon,
    s.lat,
    s.primary_brand_id,
    b.brand_name_std,
    b.brand_officiality,
    s.category_major_id,
    s.category_major_name,
    s.category_mid_id,
    s.category_mid_name,
    s.classification_status,
    s.is_brand_linked,
    s.is_category_divergent,
    s.applied_rule
FROM store_category_classifications s
LEFT JOIN brand_category_master b ON s.primary_brand_id = b.internal_brand_id;

-- 뷰 2: 대분류/중분류별 점포 통계 집계 뷰 (중복 없는 순수 점포 수 집계)
CREATE VIEW IF NOT EXISTS v_category_store_aggregates AS
SELECT 
    m.category_maj_id,
    m.category_maj_name,
    c.category_mid_id,
    c.category_mid_name,
    c.is_confirmed,
    COUNT(s.bizes_id) AS total_stores,
    SUM(CASE WHEN s.is_brand_linked = 1 THEN 1 ELSE 0 END) AS brand_linked_stores,
    SUM(CASE WHEN s.is_brand_linked = 0 THEN 1 ELSE 0 END) AS independent_stores,
    SUM(CASE WHEN s.classification_status = 'CATEGORY_CONFIRMED' THEN 1 ELSE 0 END) AS confirmed_stores,
    SUM(CASE WHEN s.classification_status = 'CATEGORY_PROVISIONAL' THEN 1 ELSE 0 END) AS provisional_stores,
    SUM(CASE WHEN s.classification_status = 'AMBIGUOUS_REVIEW' THEN 1 ELSE 0 END) AS ambiguous_stores,
    SUM(CASE WHEN s.classification_status = 'UNCLASSIFIED' THEN 1 ELSE 0 END) AS unclassified_stores
FROM mid_categories c
JOIN major_categories m ON c.category_maj_id = m.category_maj_id
LEFT JOIN store_category_classifications s ON c.category_mid_id = s.category_mid_id
GROUP BY m.category_maj_id, m.category_maj_name, c.category_mid_id, c.category_mid_name, c.is_confirmed;
"""


def init_category_master_db(db_path: Path = CATEGORY_MASTER_DB_PATH) -> None:
    """새로운 카테고리 마스터 DB를 생성하고 WAL 모드 및 스키마를 적용합니다."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("PRAGMA journal_mode = WAL;")
    cur.execute("PRAGMA synchronous = NORMAL;")
    cur.executescript(STAGE4D_SCHEMA_SQL)
    conn.commit()
    conn.close()
    print(f"[Stage 4D Schema] Successfully initialized: {db_path}")


if __name__ == "__main__":
    init_category_master_db()
