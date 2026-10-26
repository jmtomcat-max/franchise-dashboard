"""
Stage 4C: 브랜드 마스터 구축 및 전국 점포 링크 이관 파이프라인 (초고속 최적화 버전)
프로젝트: D:/Franchise_Dashboard
위치: src/stage4c/migration_pipeline.py

본 모듈은:
1. data/brand_candidates_v1.sqlite3의 5,062개 후보 및 735,208개 링크를 읽어
2. data/brand_master_v1.sqlite3로 안전하게 이관하고
3. 80개 공인 브랜드에 대한 전수 검증 정보(운영법인, 가맹사업여부, 근거등급)를 등록하며
4. 3축 상태 모델(브랜드 공식성, 점포 매칭 상태, 운영 형태) 및 검토 우선순위를 적용합니다.
"""

import math
import sqlite3
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional

BASE_DIR = Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.stage4c.schema_stage4c import initialize_stage4c_database, DEFAULT_STAGE4C_DB_PATH
from src.stage4c.brand_evidence import OFFICIAL_80_BRANDS_CENSUS, get_official_census_dict

SOURCE_CAND_DB_PATH = BASE_DIR / "data" / "brand_candidates_v1.sqlite3"
TARGET_MASTER_DB_PATH = DEFAULT_STAGE4C_DB_PATH

RULE_VERSION_STAGE4C = "v1.0.0-stage4c"

HIGH_COLLISION_RISK_NAMES = {
    "두찜", "두끼", "본죽", "한솥", "배떡", "설빙", "공차", "던킨", "빕스", "백채",
    "이디야", "빽다방", "컴포즈", "더벤티", "아비꼬", "미소야", "교촌", "굽네"
}

def calculate_review_priority_score(
    store_count: int,
    officiality: str,
    brand_name_core: str,
    category_major: str
) -> float:
    """브랜드 검토 우선순위 점수를 산정한다 (0.0 ~ 100.0)."""
    scale_score = min(40.0, math.log10(max(1, store_count) + 1) * 10.0)
    
    if officiality in ("FRANCHISE_CONFIRMED", "BRAND_CONFIRMED"):
        gov_score = 30.0
    elif officiality == "UNVERIFIED":
        gov_score = 15.0
    else:
        gov_score = 5.0
        
    risk_score = 0.0
    if len(brand_name_core) <= 2 or brand_name_core in HIGH_COLLISION_RISK_NAMES:
        risk_score += 20.0
    elif len(brand_name_core) <= 3:
        risk_score += 10.0
        
    cat_score = 10.0
    return min(100.0, round(scale_score + gov_score + risk_score + cat_score, 2))

def run_migration_pipeline(
    source_db: Optional[Path] = None,
    target_db: Optional[Path] = None,
    batch_size: int = 50000
) -> Dict[str, Any]:
    """Stage 4C 브랜드 마스터 이관 파이프라인을 실행한다."""
    src_path = source_db or SOURCE_CAND_DB_PATH
    tgt_path = target_db or TARGET_MASTER_DB_PATH
    
    start_time = time.time()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    print(f"=== [Stage 4C Migration Pipeline] Starting ===")
    print(f"  Source: {src_path}")
    print(f"  Target: {tgt_path}")
    sys.stdout.flush()
    
    # 1. 대상 데이터베이스 초기화
    if tgt_path.exists():
        tgt_path.unlink(missing_ok=True)
    initialize_stage4c_database(tgt_path)
    
    src_con = sqlite3.connect(f"file:{src_path}?mode=ro", uri=True)
    src_cur = src_con.cursor()
    
    tgt_con = sqlite3.connect(tgt_path)
    tgt_cur = tgt_con.cursor()
    
    # 2. 매칭 규칙 등록
    tgt_cur.execute("""
        INSERT INTO matching_rules (rule_version, rule_type, description, is_active, registered_at)
        VALUES (?, ?, ?, ?, ?)
    """, (
        RULE_VERSION_STAGE4C,
        "STAGE4C_3AXIS_RECONCILIATION",
        "3-axis state model: brand officiality, store match status, operation type with nationwide non-duplicate store reconciliation",
        1,
        now_str
    ))
    
    # 3. 미매칭 전용 센티넬 브랜드 마스터 등록
    tgt_cur.execute("""
        INSERT OR REPLACE INTO brands (
            internal_brand_id, candidate_brand_id, brand_name_std, brand_name_core, brand_name_clean,
            brand_officiality, category_major, discovery_method, total_store_count,
            verified_store_count, provisional_store_count, review_required_store_count,
            review_priority_score, current_review_status, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        "BRD_UNMATCHED", "CAN_UNMATCHED", "미매칭(독립점포 추정)", "미매칭", "미매칭",
        "UNVERIFIED", "전체", "SYSTEM_UNMATCHED_FALLBACK", 0, 0, 0, 0,
        0.0, "PENDING", now_str, now_str
    ))
    
    # 4. 80개 공인 브랜드 전수 등록
    census_dict = get_official_census_dict()
    official_cand_ids = set(census_dict.keys())
    
    cand_rows = src_cur.execute("""
        SELECT candidate_brand_id, brand_name_raw, brand_name_norm, brand_name_clean,
               category_major, representative_inds_mcls_cd, representative_inds_scls_cd,
               discovery_method, total_store_count
        FROM brand_candidates
    """).fetchall()
    
    cand_map = {r[0]: r for r in cand_rows}
    candidate_id_to_internal_id: Dict[str, str] = {"CAN_UNMATCHED": "BRD_UNMATCHED"}
    
    # 4.1 80개 공인 브랜드 등록
    for b in OFFICIAL_80_BRANDS_CENSUS:
        cid = b["candidate_id"]
        ibid = b["internal_brand_id"]
        candidate_id_to_internal_id[cid] = ibid
        
        orig = cand_map.get(cid)
        store_count = orig[8] if orig else 0
        mcls_cd = orig[5] if orig else None
        scls_cd = orig[6] if orig else None
        
        p_score = calculate_review_priority_score(
            store_count=store_count,
            officiality=b["brand_officiality"],
            brand_name_core=b["brand_name_core"],
            category_major=b["category_major"]
        )
        
        tgt_cur.execute("""
            INSERT OR REPLACE INTO brands (
                internal_brand_id, candidate_brand_id, brand_name_std, brand_name_core, brand_name_clean,
                brand_officiality, category_major, representative_inds_mcls_cd, representative_inds_scls_cd,
                discovery_method, total_store_count, verified_store_count, provisional_store_count,
                review_required_store_count, review_priority_score, current_review_status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            ibid, cid, b["brand_name_std"], b["brand_name_core"], b["brand_name_core"],
            b["brand_officiality"], b["category_major"], mcls_cd, scls_cd,
            "OFFICIAL_SEED_CENSUS", store_count, 0, 0, 0,
            p_score, "APPROVED" if b["brand_officiality"] in ("FRANCHISE_CONFIRMED", "BRAND_CONFIRMED") else "PENDING",
            now_str, now_str
        ))
        
        tgt_cur.execute("""
            INSERT INTO brand_franchise_evidence (
                internal_brand_id, operating_entity, business_reg_no, franchise_reg_no,
                is_franchise_business, evidence_grade, evidence_notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            ibid, b["operating_entity"], b["business_reg_no"], b["franchise_reg_no"],
            b["is_franchise_business"], b["evidence_grade"], b["evidence_notes"]
        ))
        
        tgt_cur.execute("""
            INSERT INTO brand_sources (
                internal_brand_id, source_name, source_url, reference_date, verified_at
            ) VALUES (?, ?, ?, ?, ?)
        """, (
            ibid, b["source_name"], b["source_url"], b["reference_date"], now_str
        ))
        
        tgt_cur.execute("""
            INSERT INTO brand_history (
                internal_brand_id, event_type, before_value, after_value, event_date, notes
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (
            ibid, "CREATION", None, b["brand_name_std"], now_str,
            f"공인 브랜드 마스터 등록 (공식성: {b['brand_officiality']})"
        ))
        
        for a_text, a_norm, a_type, is_off in b["aliases"]:
            tgt_cur.execute("""
                INSERT INTO brand_aliases (
                    internal_brand_id, alias_text, alias_norm, alias_type, is_official
                ) VALUES (?, ?, ?, ?, ?)
            """, (ibid, a_text, a_norm, a_type, is_off))
            
    print(f"  [Brands] 80 Official Census Brands registered.")
    sys.stdout.flush()
    
    # 4.2 나머지 4,982개 클러스터 후보 등록
    cluster_cands = [r for r in cand_rows if r[0] not in official_cand_ids]
    
    brands_batch = []
    evidence_batch = []
    sources_batch = []
    
    for r in cluster_cands:
        cid, raw_nm, norm_nm, clean_nm, cat_maj, mcls, scls, disc_meth, store_cnt = r
        ibid = cid[4:] if cid.startswith("CAN_") else f"BRD_{cid}"
        candidate_id_to_internal_id[cid] = ibid
        
        p_score = calculate_review_priority_score(
            store_count=store_cnt,
            officiality="UNVERIFIED",
            brand_name_core=norm_nm,
            category_major=cat_maj
        )
        
        brands_batch.append((
            ibid, cid, raw_nm, norm_nm, clean_nm,
            "UNVERIFIED", cat_maj, mcls, scls,
            disc_meth, store_cnt, 0, 0, 0,
            p_score, "PENDING", now_str, now_str
        ))
        
        evidence_batch.append((
            ibid, None, None, None, None, "C_STATISTICAL_CLUSTER",
            f"전국 {store_cnt}개 점포 클러스터 기반 추출 (공식 가맹정보 미검증)"
        ))
        
        sources_batch.append((
            ibid, "소상공인시장진흥공단 상가(상권)정보 통계 클러스터",
            "https://apis.data.go.kr/B553077/api/open/sdsc2", "2026-06-30", now_str
        ))
        
    tgt_cur.executemany("""
        INSERT OR REPLACE INTO brands (
            internal_brand_id, candidate_brand_id, brand_name_std, brand_name_core, brand_name_clean,
            brand_officiality, category_major, representative_inds_mcls_cd, representative_inds_scls_cd,
            discovery_method, total_store_count, verified_store_count, provisional_store_count,
            review_required_store_count, review_priority_score, current_review_status, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, brands_batch)
    
    tgt_cur.executemany("""
        INSERT INTO brand_franchise_evidence (
            internal_brand_id, operating_entity, business_reg_no, franchise_reg_no,
            is_franchise_business, evidence_grade, evidence_notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
    """, evidence_batch)
    
    tgt_cur.executemany("""
        INSERT INTO brand_sources (
            internal_brand_id, source_name, source_url, reference_date, verified_at
        ) VALUES (?, ?, ?, ?, ?)
    """, sources_batch)
    
    print(f"  [Brands] {len(cluster_cands):,} Cluster Candidates registered. Total Brands: {len(brands_batch) + 81:,}")
    sys.stdout.flush()
    
    # 4.3 클러스터 별칭 이관
    alias_rows = src_cur.execute("""
        SELECT candidate_brand_id, alias_text, alias_norm, alias_type, is_official
        FROM brand_aliases
        WHERE candidate_brand_id NOT IN (SELECT candidate_brand_id FROM brand_candidates WHERE verification_status = 'OFFICIAL_VERIFIED')
    """).fetchall()
    
    alias_tuples = []
    for cid, a_text, a_norm, a_type, is_off in alias_rows:
        ibid = candidate_id_to_internal_id.get(cid)
        if ibid:
            alias_tuples.append((ibid, a_text, a_norm, a_type, is_off))
            
    if alias_tuples:
        tgt_cur.executemany("""
            INSERT INTO brand_aliases (internal_brand_id, alias_text, alias_norm, alias_type, is_official)
            VALUES (?, ?, ?, ?, ?)
        """, alias_tuples)
    print(f"  [Aliases] {len(alias_tuples):,} cluster aliases migrated.")
    
    tgt_con.commit()
    sys.stdout.flush()
    
    # 5. store_brand_candidates -> store_brand_links 이관 (keyset pagination 최적화)
    print("  [Links] Migrating 735,208 store-brand links with 3-axis state model...")
    sys.stdout.flush()
    
    brand_meta_map: Dict[str, Tuple[str, Optional[int]]] = {}
    for r in tgt_cur.execute("""
        SELECT b.internal_brand_id, b.brand_officiality, e.is_franchise_business
        FROM brands b
        LEFT JOIN brand_franchise_evidence e ON b.internal_brand_id = e.internal_brand_id
    """).fetchall():
        brand_meta_map[r[0]] = (r[1], r[2])
        
    total_links_migrated = 0
    last_id = 0
    
    while True:
        chunk = src_cur.execute("""
            SELECT id, bizes_id, candidate_brand_id, match_method, confidence_score,
                   store_verification_status, franchisor_status, branch_operation_type,
                   is_primary_candidate, notes
            FROM store_brand_candidates
            WHERE id > ?
            ORDER BY id ASC
            LIMIT ?
        """, (last_id, batch_size)).fetchall()
        
        if not chunk:
            break
            
        last_id = chunk[-1][0]
        link_batch = []
        for row in chunk:
            (_, b_id, cid, m_method, c_score, v_status, frcs_status, branch_op, is_prim, notes) = row
            
            if v_status == "INDEPENDENT_STORE" or cid is None:
                ibid = "BRD_UNMATCHED"
            else:
                ibid = candidate_id_to_internal_id.get(cid, "BRD_UNMATCHED")
                
            # 3축 모델 1: match_status
            if v_status == "INDEPENDENT_STORE":
                match_status = "UNMATCHED"
            elif v_status == "VERIFIED_AUTO":
                match_status = "MATCH_AUTO_HIGH_CONFIDENCE"
            elif v_status == "PROVISIONAL":
                match_status = "MATCH_PROVISIONAL"
            elif v_status == "REVIEW_REQUIRED":
                match_status = "REVIEW_REQUIRED"
            elif v_status == "REJECTED":
                match_status = "MATCH_REJECTED"
            else:
                match_status = "UNMATCHED"
                
            # 3축 모델 2: operation_type
            brand_off, is_frcs_biz = brand_meta_map.get(ibid, ("UNVERIFIED", None))
            
            if branch_op == "DIRECT_OPERATED":
                operation_type = "COMPANY_OPERATED"
            elif branch_op == "FRANCHISE_STORE":
                operation_type = "FRANCHISED"
            elif is_frcs_biz == 0 and brand_off == "BRAND_CONFIRMED":
                operation_type = "COMPANY_OPERATED"
            else:
                operation_type = "UNKNOWN"
                
            link_batch.append((
                b_id,
                ibid,
                match_status,
                operation_type,
                c_score,
                is_prim,
                m_method,
                notes,
                now_str
            ))
            
        tgt_cur.executemany("""
            INSERT INTO store_brand_links (
                bizes_id, internal_brand_id, match_status, operation_type,
                confidence_score, is_primary_link, match_method, notes, linked_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, link_batch)
        
        tgt_con.commit() # commit per batch for low memory and safe WAL
        total_links_migrated += len(link_batch)
        print(f"    Migrated {total_links_migrated:,} / 735,208 links...")
        sys.stdout.flush()
        
    print(f"  [Links] Migration complete. Total links inserted: {total_links_migrated:,}")
    sys.stdout.flush()
    
    # 6. brands 테이블 점포 카운트 롤업 업데이트 (초고속 단일 GROUP BY 방식)
    print("  [Rollup] Updating brands aggregate store counts via fast GROUP BY...")
    sys.stdout.flush()
    
    rollup_rows = tgt_cur.execute("""
        SELECT internal_brand_id,
               count(*) as tot_cnt,
               sum(CASE WHEN match_status IN ('MATCH_VERIFIED', 'MATCH_AUTO_HIGH_CONFIDENCE') THEN 1 ELSE 0 END) as v_cnt,
               sum(CASE WHEN match_status = 'MATCH_PROVISIONAL' THEN 1 ELSE 0 END) as p_cnt,
               sum(CASE WHEN match_status = 'REVIEW_REQUIRED' THEN 1 ELSE 0 END) as r_cnt
        FROM store_brand_links
        GROUP BY internal_brand_id;
    """).fetchall()
    
    tgt_cur.executemany("""
        UPDATE brands
        SET total_store_count = ?,
            verified_store_count = ?,
            provisional_store_count = ?,
            review_required_store_count = ?,
            updated_at = ?
        WHERE internal_brand_id = ?
    """, [(r[1], r[2], r[3], r[4], now_str, r[0]) for r in rollup_rows])
    tgt_con.commit()
    
    # 7. 정합성 및 무결성 검증
    uniq_stores_in_links = tgt_cur.execute("SELECT count(DISTINCT bizes_id) FROM store_brand_links;").fetchone()[0]
    total_link_rows = tgt_cur.execute("SELECT count(*) FROM store_brand_links;").fetchone()[0]
    unmatched_count = tgt_cur.execute("SELECT count(*) FROM store_brand_links WHERE match_status = 'UNMATCHED';").fetchone()[0]
    verified_links = tgt_cur.execute("SELECT count(*) FROM store_brand_links WHERE match_status = 'MATCH_AUTO_HIGH_CONFIDENCE';").fetchone()[0]
    provisional_links = tgt_cur.execute("SELECT count(*) FROM store_brand_links WHERE match_status = 'MATCH_PROVISIONAL';").fetchone()[0]
    review_links = tgt_cur.execute("SELECT count(*) FROM store_brand_links WHERE match_status = 'REVIEW_REQUIRED';").fetchone()[0]
    rejected_links = tgt_cur.execute("SELECT count(*) FROM store_brand_links WHERE match_status = 'MATCH_REJECTED';").fetchone()[0]
    multi_cand_stores = tgt_cur.execute("""
        SELECT count(*) FROM (
            SELECT bizes_id, count(*) as c FROM store_brand_links GROUP BY bizes_id HAVING c > 1
        )
    """).fetchone()[0]
    
    brands_count = tgt_cur.execute("SELECT count(*) FROM brands;").fetchone()[0]
    
    duration = round(time.time() - start_time, 2)
    
    summary = {
        "migration_status": "SUCCESS",
        "duration_seconds": duration,
        "target_db_path": str(tgt_path),
        "total_brands_in_master": brands_count,
        "census_80_brands_registered": len(OFFICIAL_80_BRANDS_CENSUS),
        "cluster_candidates_migrated": len(cluster_cands),
        "total_store_links": total_link_rows,
        "unique_stores_in_links": uniq_stores_in_links,
        "multi_candidate_stores": multi_cand_stores,
        "unmatched_stores_count": unmatched_count,
        "match_auto_high_confidence_count": verified_links,
        "match_provisional_count": provisional_links,
        "review_required_count": review_links,
        "match_rejected_count": rejected_links,
        "integrity_check": {
            "unique_stores_exact_match": uniq_stores_in_links == 735185,
            "total_links_exact_match": total_link_rows == 735208,
            "multi_candidate_exact_match": multi_cand_stores == 23
        }
    }
    
    print(f"=== [Stage 4C Migration Complete in {duration}s] ===")
    print(f"  Total Brands: {brands_count:,}")
    print(f"  Unique Stores in Links: {uniq_stores_in_links:,} (Expected: 735,185)")
    print(f"  Total Links: {total_link_rows:,} (Expected: 735,208)")
    print(f"  Multi-Candidate Stores: {multi_cand_stores:,} (Expected: 23)")
    print(f"  UNMATCHED Stores: {unmatched_count:,}")
    print(f"  MATCH_AUTO_HIGH_CONFIDENCE: {verified_links:,}")
    sys.stdout.flush()
    
    src_con.close()
    tgt_con.close()
    
    return summary

if __name__ == "__main__":
    res = run_migration_pipeline()
    import json
    print(json.dumps(res, indent=2, ensure_ascii=False))
