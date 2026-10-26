"""
Stage 4E: 분석용 통합 데이터베이스 스키마 정의 모듈
프로젝트: D:/Franchise_Dashboard
위치: src/stage4e/schema_stage4e.py
"""

import sqlite3
from pathlib import Path
from typing import Optional

BASE_DIR = Path(__file__).resolve().parent.parent.parent
ANALYTICS_DB_PATH = BASE_DIR / "data" / "franchise_analytics_v1.sqlite3"

SCHEMA_STAGE4E_DDL = """
-- ==============================================================================
-- Franchise Dashboard - Phase 4 Stage 4E: Analytics Database Schema
-- ==============================================================================

-- 1. 전국 및 시도/시군구 표준 지역 마스터 (regions_master)
CREATE TABLE IF NOT EXISTS regions_master (
    region_code             TEXT PRIMARY KEY,              -- '00' (전국), '11' (시도), '11680' (시군구)
    region_type             TEXT NOT NULL,                 -- 'NATIONWIDE', 'SIDO', 'SIGUNGU'
    sido_code               TEXT,                          -- 2자리 시도코드 (전국은 NULL)
    sido_name               TEXT,                          -- 시도명 (예: 서울특별시)
    sigungu_code            TEXT,                          -- 5자리 시군구코드 (전국/시도는 NULL)
    sigungu_name            TEXT,                          -- 시군구명 (예: 강남구, 광진구)
    dashboard_code          TEXT NOT NULL,                 -- 대시보드 및 3D GIS 렌더링용 식별자
    area_sq_km              REAL,                          -- 행정구역 면적(km², 검증된 면적만 보존)
    area_status             TEXT NOT NULL DEFAULT 'UNAVAILABLE', -- 'AVAILABLE', 'UNAVAILABLE'
    center_lon              REAL,                          -- 중심 경도
    center_lat              REAL,                          -- 중심 위도
    created_at              TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 2. 지역별 외식업 전체 현황 집계 (regional_overall_stats)
CREATE TABLE IF NOT EXISTS regional_overall_stats (
    region_code             TEXT PRIMARY KEY,              -- FK -> regions_master.region_code
    region_name             TEXT NOT NULL,                 -- 표시용 지역 명칭
    region_type             TEXT NOT NULL,                 -- 'NATIONWIDE', 'SIDO', 'SIGUNGU'
    total_stores            INTEGER NOT NULL,              -- 외식업 전체 고유 점포 수 (COUNT(DISTINCT bizes_id))
    brand_linked_stores     INTEGER NOT NULL,              -- 브랜드 연결 점포 수 (프랜차이즈/체인 후보)
    independent_stores      INTEGER NOT NULL,              -- 미매칭 독립 점포 수 (독립 사업자 확정이 아닌 미매칭 분류)
    franchise_confirmed_stores INTEGER NOT NULL,           -- 공인 가맹사업 브랜드(FRANCHISE_CONFIRMED) 점포 수
    brand_confirmed_stores  INTEGER NOT NULL,              -- 직영 체인 브랜드(BRAND_CONFIRMED) 점포 수
    unverified_brand_stores INTEGER NOT NULL,              -- 미검증 후보 브랜드(UNVERIFIED) 점포 수
    confirmed_franchisees   INTEGER NOT NULL,              -- 공식 가맹점 운영 점포 수 (증거 충족)
    ambiguous_category_stores INTEGER NOT NULL,            -- 모호 분류 점포 수 (AMBIGUOUS_REVIEW)
    confirmed_category_stores INTEGER NOT NULL,            -- 확정 업종 점포 수 (CATEGORY_CONFIRMED)
    provisional_category_stores INTEGER NOT NULL,          -- 잠정 업종 점포 수 (CATEGORY_PROVISIONAL)
    franchise_penetration_rate REAL NOT NULL,              -- 공인 프랜차이즈 침투율 (%) (franchise_confirmed_stores / total_stores * 100)
    brand_penetration_rate  REAL NOT NULL,                 -- 전체 브랜드 침투율 (%) (brand_linked_stores / total_stores * 100)
    density_per_sq_km       REAL,                          -- 면적당 점포 수 (검증된 면적 부재 시 NULL)
    density_status          TEXT NOT NULL DEFAULT 'UNAVAILABLE', -- 'AVAILABLE', 'UNAVAILABLE'
    updated_at              TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (region_code) REFERENCES regions_master(region_code)
);

-- 3. 지역별 8대 대분류 및 48대 중분류 집계 (regional_category_stats)
CREATE TABLE IF NOT EXISTS regional_category_stats (
    stat_id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    region_code             TEXT NOT NULL,                 -- FK -> regions_master.region_code
    category_major_id       TEXT NOT NULL,                 -- 'CAT_MAJ_01' ~ 'CAT_MAJ_08'
    category_major_name     TEXT NOT NULL,                 -- 대분류명
    category_mid_id         TEXT NOT NULL,                 -- 'CAT_MID_0101' ~ 'CAT_MID_0806'
    category_mid_name       TEXT NOT NULL,                 -- 중분류명
    total_stores            INTEGER NOT NULL,              -- 해당 업종 전체 점포 수
    stores_excluding_ambiguous INTEGER NOT NULL,           -- 모호 분류(AMBIGUOUS_REVIEW) 제외 점포 수
    brand_linked_stores     INTEGER NOT NULL,              -- 브랜드 소속 점포 수
    independent_stores      INTEGER NOT NULL,              -- 독립 점포 수
    franchise_confirmed_stores INTEGER NOT NULL,           -- 공인 가맹사업 점포 수
    ambiguous_stores        INTEGER NOT NULL,              -- 모호 분류 점포 수
    category_share_pct      REAL NOT NULL,                 -- 지역 내 외식업 전체 대비 비중 (%)
    category_rank_in_region INTEGER NOT NULL,              -- 지역 내 업종 순위
    FOREIGN KEY (region_code) REFERENCES regions_master(region_code)
);

-- 4. 지역별 브랜드 점포수 및 경쟁도 집계 (regional_brand_stats)
CREATE TABLE IF NOT EXISTS regional_brand_stats (
    stat_id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    region_code             TEXT NOT NULL,                 -- FK -> regions_master.region_code
    internal_brand_id       TEXT NOT NULL,                 -- 브랜드 ID ('BRD_xxxx')
    brand_name_std          TEXT NOT NULL,                 -- 표준 브랜드명
    brand_officiality       TEXT NOT NULL,                 -- 'FRANCHISE_CONFIRMED', 'BRAND_CONFIRMED', 'UNVERIFIED'
    category_major_id       TEXT NOT NULL,                 -- 대표 대분류 ID
    category_mid_id         TEXT NOT NULL,                 -- 대표 중분류 ID
    discovered_store_count  INTEGER NOT NULL,              -- 지역 내 발견 점포 수
    confirmed_franchisee_count INTEGER NOT NULL,           -- 지역 내 확인된 공식 가맹점 수
    market_share_in_region  REAL NOT NULL,                 -- 지역 외식업 전체 대비 점포 비중 (%)
    category_share_in_region REAL NOT NULL,                -- 동일 업종 내 상대 점포 비중 (동일 업종 내 경쟁도 %)
    rank_in_region          INTEGER NOT NULL,              -- 지역 내 전체 브랜드 순위
    rank_in_category_region INTEGER NOT NULL,              -- 지역 내 동일 업종 내 브랜드 순위
    FOREIGN KEY (region_code) REFERENCES regions_master(region_code)
);

-- 5. 지역별/업종별 상위 브랜드 랭킹 인덱스 (regional_brand_rankings)
CREATE TABLE IF NOT EXISTS regional_brand_rankings (
    ranking_id              INTEGER PRIMARY KEY AUTOINCREMENT,
    region_code             TEXT NOT NULL,                 -- FK -> regions_master.region_code
    ranking_type            TEXT NOT NULL,                 -- 'OVERALL_TOP20', 'CATEGORY_TOP10'
    category_major_id       TEXT,                          -- 대분류 필터 (전체 순위는 NULL)
    rank_num                INTEGER NOT NULL,              -- 순위 (1~20)
    internal_brand_id       TEXT NOT NULL,                 -- 브랜드 ID
    brand_name_std          TEXT NOT NULL,                 -- 브랜드명
    brand_officiality       TEXT NOT NULL,                 -- 공식성
    store_count             INTEGER NOT NULL,              -- 점포 수
    share_pct               REAL NOT NULL,                 -- 점유율 (%)
    FOREIGN KEY (region_code) REFERENCES regions_master(region_code)
);

-- 6. 개별 점포 통합 조회 및 공간 검색 테이블 (store_analytics_lookup)
-- (전국 735,185건 고유 점포와 1:1 매핑 - 중복 없는 검색 전용 계층)
CREATE TABLE IF NOT EXISTS store_analytics_lookup (
    bizes_id                TEXT PRIMARY KEY,              -- 소진공 고유 점포 ID (전국 735,185건)
    bizes_nm                TEXT NOT NULL,                 -- 상호명
    brch_nm                 TEXT,                          -- 지점명
    std_sido_code           TEXT NOT NULL,                 -- 표준 2자리 시도코드
    std_sido_name           TEXT NOT NULL,                 -- 표준 시도명
    std_signgu_code         TEXT NOT NULL,                 -- 표준 5자리 시군구코드
    std_signgu_name         TEXT NOT NULL,                 -- 표준 시군구명
    rdnm_adr                TEXT,                          -- 도로명주소
    lno_adr                 TEXT,                          -- 지번주소
    lon                     REAL NOT NULL,                 -- WGS84 경도
    lat                     REAL NOT NULL,                 -- WGS84 위도
    category_major_id       TEXT NOT NULL,                 -- 8대 대분류 ID
    category_major_name     TEXT NOT NULL,                 -- 8대 대분류명
    category_mid_id         TEXT NOT NULL,                 -- 48대 중분류 ID
    category_mid_name       TEXT NOT NULL,                 -- 48대 중분류명
    primary_brand_id        TEXT NOT NULL,                 -- 주 브랜드 ID ('BRD_UNMATCHED' 포함)
    brand_name_std          TEXT,                          -- 표준 브랜드명
    brand_officiality       TEXT NOT NULL,                 -- 'FRANCHISE_CONFIRMED', 'BRAND_CONFIRMED', 'UNVERIFIED', 'UNMATCHED'
    match_status            TEXT NOT NULL,                 -- 'MATCH_VERIFIED', 'MATCH_AUTO_HIGH_CONFIDENCE', 'MATCH_PROVISIONAL', 'REVIEW_REQUIRED', 'UNMATCHED'
    operation_type          TEXT NOT NULL,                 -- 'COMPANY_OPERATED', 'FRANCHISED', 'UNKNOWN'
    classification_status   TEXT NOT NULL,                 -- 'CATEGORY_CONFIRMED', 'CATEGORY_PROVISIONAL', 'AMBIGUOUS_REVIEW'
    is_brand_linked         INTEGER NOT NULL,              -- 브랜드 연결 여부 (1/0)
    is_category_divergent   INTEGER NOT NULL,              -- 업종 불일치/복합메뉴 여부 (1/0)
    is_multi_brand_store    INTEGER NOT NULL DEFAULT 0,    -- 23개 복수 후보 점포 식별 플래그 (1/0)
    auxiliary_brand_names   TEXT                           -- 복수 브랜드 매장일 경우 보조 브랜드명 (쉼표 구분)
);

-- 7. 3D 상권 핫스팟 및 드론 비행 카메라 경로 (commercial_hotspots)
-- (사용자 제시 reference UI의 '드론 비행 1/5 예측 핫스팟 1위' 및 3D 시점 투어용)
CREATE TABLE IF NOT EXISTS commercial_hotspots (
    hotspot_id              TEXT PRIMARY KEY,              -- 'HOTSPOT_01'
    hotspot_name            TEXT NOT NULL,                 -- 핫스팟 명칭 (예: 강남역 상권, 홍대 상권, 광진 건대입구 맛의거리)
    sido_code               TEXT NOT NULL,                 -- 시도코드
    sigungu_code            TEXT NOT NULL,                 -- 시군구코드
    center_lon              REAL NOT NULL,                 -- 중심 경도
    center_lat              REAL NOT NULL,                 -- 중심 위도
    pitch                   REAL NOT NULL DEFAULT 60.0,    -- 3D 틸트 카메라 각도 (경사도)
    bearing                 REAL NOT NULL DEFAULT -20.0,   -- 카메라 방위각
    zoom                    REAL NOT NULL DEFAULT 16.5,    -- 3D 건물 줌레벨
    store_count             INTEGER NOT NULL,              -- 핫스팟 반경 내 점포 수
    franchise_ratio         REAL NOT NULL,                 -- 프랜차이즈 점유율 (%)
    dominant_category_name  TEXT NOT NULL,                 -- 주요 업종
    description             TEXT,                          -- 상권 해설 및 비즈니스 인사이트
    tour_order              INTEGER NOT NULL               -- 드론 투어 재생 순서
);

-- 8. 3D GIS 100m 밀집도 격자 기둥 집계 (spatial_density_grid_100m)
-- (사용자 제시 reference UI의 '격자 기둥' / deck.gl ColumnLayer 연동용)
CREATE TABLE IF NOT EXISTS spatial_density_grid_100m (
    grid_id                 TEXT PRIMARY KEY,              -- 'GRID_xxxxx'
    sido_code               TEXT NOT NULL,                 -- 시도코드
    sigungu_code            TEXT NOT NULL,                 -- 시군구코드
    center_lon              REAL NOT NULL,                 -- 셀 중심 경도
    center_lat              REAL NOT NULL,                 -- 셀 중심 위도
    min_lon                 REAL NOT NULL,                 -- 바운딩 박스
    min_lat                 REAL NOT NULL,
    max_lon                 REAL NOT NULL,
    max_lat                 REAL NOT NULL,
    total_stores            INTEGER NOT NULL,              -- 셀 내 점포 수
    brand_stores            INTEGER NOT NULL,              -- 셀 내 브랜드 점포 수
    top_category_name       TEXT NOT NULL,                 -- 최다 업종
    column_height_m         REAL NOT NULL,                 -- 3D 기둥 렌더링 높이(m) (점포 밀집도 비례)
    created_at              TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 9. 분석 지표 및 차원 정의 사전 (metric_definitions)
CREATE TABLE IF NOT EXISTS metric_definitions (
    metric_key              TEXT PRIMARY KEY,              -- 'TOTAL_STORES', 'FRANCHISE_PENETRATION' 등
    metric_name_ko          TEXT NOT NULL,                 -- 한글 명칭
    definition              TEXT NOT NULL,                 -- 산출 공식 및 정의
    dimension               TEXT NOT NULL,                 -- 적용 차원
    interpretation_guide    TEXT NOT NULL,                 -- 해석 가이드
    unit                    TEXT NOT NULL                  -- 단위 ('건', '%', '개/km²' 등)
);

-- 10. 감사 및 빌드 이력 로그 (audit_logs)
CREATE TABLE IF NOT EXISTS audit_logs (
    log_id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    run_timestamp           TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    action_type             TEXT NOT NULL,                 -- 'ETL_BUILD', 'VERIFICATION'
    total_unique_stores     INTEGER NOT NULL,              -- 735,185
    multi_brand_store_count INTEGER NOT NULL,              -- 23
    total_brand_links       INTEGER NOT NULL,              -- 735,208
    provinces_count         INTEGER NOT NULL,              -- 16
    districts_count         INTEGER NOT NULL,              -- 256
    status                  TEXT NOT NULL,                 -- 'SUCCESS', 'FAILED'
    details                 TEXT                           -- JSON 세부 정보
);

-- ==============================================================================
-- 고속 3D 지도 및 분석 쿼리를 위한 최적화 인덱스 설계
-- ==============================================================================

-- 점포 공간 바운딩 박스(BBOX) 초고속 검색 인덱스 (deck.gl / MapLibre 뷰포트 쿼리)
CREATE INDEX IF NOT EXISTS idx_store_lookup_geo ON store_analytics_lookup(lon, lat);
CREATE INDEX IF NOT EXISTS idx_store_lookup_rgn ON store_analytics_lookup(std_sido_code, std_signgu_code);
CREATE INDEX IF NOT EXISTS idx_store_lookup_maj ON store_analytics_lookup(category_major_id);
CREATE INDEX IF NOT EXISTS idx_store_lookup_mid ON store_analytics_lookup(category_mid_id);
CREATE INDEX IF NOT EXISTS idx_store_lookup_brd ON store_analytics_lookup(primary_brand_id);
CREATE INDEX IF NOT EXISTS idx_store_lookup_off ON store_analytics_lookup(brand_officiality);
CREATE INDEX IF NOT EXISTS idx_store_lookup_stat ON store_analytics_lookup(classification_status);
CREATE INDEX IF NOT EXISTS idx_store_lookup_comp ON store_analytics_lookup(std_signgu_code, category_major_id, brand_officiality);

-- 집계 테이블 조회 인덱스
CREATE INDEX IF NOT EXISTS idx_cat_stats_rgn ON regional_category_stats(region_code, category_major_id);
CREATE INDEX IF NOT EXISTS idx_brd_stats_rgn ON regional_brand_stats(region_code, internal_brand_id);
CREATE INDEX IF NOT EXISTS idx_brd_stats_brd ON regional_brand_stats(internal_brand_id);
CREATE INDEX IF NOT EXISTS idx_brd_stats_name ON regional_brand_stats(brand_name_std);
CREATE INDEX IF NOT EXISTS idx_brd_rank_rgn ON regional_brand_rankings(region_code, ranking_type);
CREATE INDEX IF NOT EXISTS idx_grid_rgn ON spatial_density_grid_100m(sigungu_code);
CREATE INDEX IF NOT EXISTS idx_grid_geo ON spatial_density_grid_100m(min_lon, min_lat, max_lon, max_lat);
"""


def init_analytics_db(db_path: Path = ANALYTICS_DB_PATH) -> None:
    """새로운 분석용 DB를 초기화하고 스키마를 적용합니다."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("PRAGMA journal_mode = WAL;")
    cur.execute("PRAGMA synchronous = NORMAL;")
    cur.executescript(SCHEMA_STAGE4E_DDL)
    conn.commit()
    conn.close()
    print(f"[Stage 4E Schema] Initialized analytics database: {db_path}")


if __name__ == "__main__":
    init_analytics_db()
