"""
Stage 4D: 외식업 8대 대분류 및 48대 중분류 전국 분류 파이프라인 엔진
프로젝트: D:/Franchise_Dashboard
위치: src/stage4d/classifier.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import sqlite3
import time
import json
from typing import Dict, List, Any, Tuple, Optional

from src.stage4d.schema_stage4d import (
    CATEGORY_MASTER_DB_PATH,
    init_category_master_db
)
from src.stage4d.taxonomy_master import (
    load_taxonomy_config,
    SEMAS_38_SUBCLASSES,
    SEMAS_TO_MID_RULES,
    OFFICIAL_80_BRAND_CATEGORY_MAP,
    MCLS_NAME_TO_MAJOR_MAP,
    resolve_semas_to_mid
)

NATIONWIDE_V2_DB_PATH = Path("d:/Franchise_Dashboard/data/nationwide_food_stores_v2.sqlite3")
BRAND_MASTER_DB_PATH = Path("d:/Franchise_Dashboard/data/brand_master_v1.sqlite3")


def populate_taxonomy_reference_tables(conn: sqlite3.Connection) -> None:
    """분류체계 마스터 테이블(major, mid, semas, rules) 적재"""
    tax_config = load_taxonomy_config()
    cur = conn.cursor()

    # 1. major_categories (8개)
    cur.executemany("""
        INSERT OR REPLACE INTO major_categories 
        (category_maj_id, category_maj_name, slot_count, display_order, description)
        VALUES (?, ?, ?, ?, ?)
    """, [
        (
            m["category_maj_id"],
            m["category_maj_name"],
            m["slot_count"],
            m["display_order"],
            m.get("description", "")
        )
        for m in tax_config["major_categories"]
    ])

    # 2. mid_categories (48개)
    cur.executemany("""
        INSERT OR REPLACE INTO mid_categories 
        (category_mid_id, category_maj_id, category_mid_name, category_mid_name_en,
         spec_status, is_confirmed, representative_menu, display_order)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, [
        (
            c["category_mid_id"],
            c["category_maj_id"],
            c["category_mid_name"],
            c.get("category_mid_name_en", ""),
            c["spec_status"],
            c["is_confirmed"],
            c.get("representative_menu", ""),
            idx + 1
        )
        for idx, c in enumerate(tax_config["mid_categories"])
    ])

    # 3. semas_industry_codes (38개)
    cur.executemany("""
        INSERT OR REPLACE INTO semas_industry_codes 
        (scls_code, scls_name, mcls_code, mcls_name, nationwide_store_count)
        VALUES (?, ?, ?, ?, ?)
    """, [
        (s["scls_code"], s["scls_name"], s["mcls_code"], s["mcls_name"], s["count"])
        for s in SEMAS_38_SUBCLASSES
    ])

    # 4. semas_to_mid_mappings
    cur.executemany("""
        INSERT INTO semas_to_mid_mappings 
        (scls_code, category_mid_id, is_primary, rule_type, disambiguation_keywords, priority, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, [
        (
            r["scls_code"],
            r["category_mid_id"],
            r["is_primary"],
            r["rule_type"],
            ",".join(r["keywords"]) if r.get("keywords") else None,
            1 if r["is_primary"] == 1 else 2,
            r.get("notes", "")
        )
        for r in SEMAS_TO_MID_RULES
    ])

    # 5. category_exception_rules 등록
    exception_rules = [
        ("RULE_EXC_001", "BRD_KOR_0001", "본죽&비빔밥", "I20101", "CAT_MID_0103", "본죽&비빔밥 매장의 백반(I20101) 등록 건 한식 대표 백반/죽 매핑", 1),
        ("RULE_EXC_002", "BRD_CHN_0001", "홍콩반점0410", "I20201", "CAT_MID_0201", "홍콩반점 일반중식 대표업종 확정", 1),
        ("RULE_EXC_003", "BRD_CHK_0004", "맘스터치", "I21006", "CAT_MID_0502", "맘스터치 치킨코드(I21006) 등록 건도 대표 버거(CAT_MID_0502)로 통합", 1),
        ("RULE_EXC_004", "BRD_BKR_0004", "설빙", "I21201", "CAT_MID_0803", "설빙 카페코드(I21201) 등록 건도 대표 빙수(CAT_MID_0803)로 통합", 1),
    ]
    cur.executemany("""
        INSERT OR REPLACE INTO category_exception_rules
        (rule_id, target_brand_id, brand_name_pattern, source_scls_cd, override_category_mid_id, exception_reason, is_active)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, exception_rules)

    # 6. taxonomy_version_history
    cur.execute("""
        INSERT OR REPLACE INTO taxonomy_version_history
        (version_id, version_tag, change_summary, authorized_by)
        VALUES ('VER_001', 'v1.0.0-stage4d', '8대 대분류 및 48대 중분류 초기 베이스라인 배포', 'SYSTEM_PIPELINE')
    """)

    conn.commit()
    print("[Stage 4D Classifier] Taxonomy reference tables successfully populated.")


def build_brand_category_master(target_conn: sqlite3.Connection) -> Dict[str, Tuple[str, str, str, str, str, str]]:
    """
    모든 5,063개 브랜드에 대해 대표 대분류/중분류를 확정하고 brand_category_master를 구축합니다.
    반환값: brand_cache {internal_brand_id: (maj_id, maj_nm, mid_id, mid_nm, officiality, status)}
    """
    tax_config = load_taxonomy_config()
    maj_id_to_name = {m["category_maj_id"]: m["category_maj_name"] for m in tax_config["major_categories"]}
    mid_id_to_name = {c["category_mid_id"]: c["category_mid_name"] for c in tax_config["mid_categories"]}

    # 원본 브랜드 마스터(Stage 4C) 조회
    bm_conn = sqlite3.connect(BRAND_MASTER_DB_PATH)
    bm_cur = bm_conn.cursor()
    bm_cur.execute("""
        SELECT internal_brand_id, brand_name_std, category_major, 
               representative_inds_mcls_cd, representative_inds_scls_cd,
               brand_officiality, total_store_count
        FROM brands
    """)
    raw_brands = bm_cur.fetchall()
    bm_conn.close()

    brand_cache: Dict[str, Tuple[str, str, str, str, str, str]] = {}
    brand_rows_to_insert = []

    for b_id, b_name, cat_maj_raw, rep_mcls, rep_scls, officiality, store_cnt in raw_brands:
        if b_id in OFFICIAL_80_BRAND_CATEGORY_MAP:
            # 공식 80대 브랜드
            maj_id, mid_id, rationale = OFFICIAL_80_BRAND_CATEGORY_MAP[b_id]
            maj_nm = maj_id_to_name[maj_id]
            mid_nm = mid_id_to_name[mid_id]
            # 교동짬뽕 등 UNVERIFIED 브랜드는 CATEGORY_PROVISIONAL, 검증된 공식 브랜드는 CATEGORY_CONFIRMED
            status = "CATEGORY_CONFIRMED" if officiality in ("FRANCHISE_CONFIRMED", "BRAND_CONFIRMED") else "CATEGORY_PROVISIONAL"
        elif b_id == "BRD_UNMATCHED":
            # 미매칭 센티넬
            maj_id = "CAT_MAJ_01"
            maj_nm = "한식"
            mid_id = "CAT_MID_0108"
            mid_nm = "전/부침/기타한식"
            status = "UNCLASSIFIED"
            rationale = "비프랜차이즈 미매칭 점포 집합 센티넬 (개별 점포코드로 직접 분류)"
        else:
            # 4,982개 클러스터 후보 브랜드
            # representative_inds_scls_cd 기반 자동 매핑
            scls = rep_scls or "I20101"
            maj_id, mid_id, rule_type, _ = resolve_semas_to_mid(scls, b_name)
            maj_nm = maj_id_to_name.get(maj_id, "한식")
            mid_nm = mid_id_to_name.get(mid_id, "고기구이/육류")
            status = "CATEGORY_PROVISIONAL"
            rationale = f"클러스터 점포 소진공 최빈 소분류코드({scls}) 기반 잠정 매핑 ({rule_type})"

        brand_cache[b_id] = (maj_id, maj_nm, mid_id, mid_nm, officiality, status)
        brand_rows_to_insert.append((
            b_id, b_name, maj_id, maj_nm, mid_id, mid_nm, officiality,
            status, store_cnt, rep_scls, rationale
        ))

    cur = target_conn.cursor()
    cur.executemany("""
        INSERT OR REPLACE INTO brand_category_master
        (internal_brand_id, brand_name_std, category_major_id, category_major_name,
         category_mid_id, category_mid_name, brand_officiality, classification_status,
         total_stores, representative_inds_scls_cd, rationale)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, brand_rows_to_insert)
    target_conn.commit()

    print(f"[Stage 4D Classifier] brand_category_master populated with {len(brand_rows_to_insert)} brands.")
    return brand_cache


def classify_nationwide_stores(target_conn: sqlite3.Connection,
                               brand_cache: Dict[str, Tuple[str, str, str, str, str, str]]) -> None:
    """
    전국 735,185개 점포와 735,208개 링크를 고속으로 분류하여 적재합니다.
    """
    tax_config = load_taxonomy_config()
    maj_id_to_name = {m["category_maj_id"]: m["category_maj_name"] for m in tax_config["major_categories"]}
    mid_id_to_name = {c["category_mid_id"]: c["category_mid_name"] for c in tax_config["mid_categories"]}

    # attached databases 연결
    attached_conn = sqlite3.connect(":memory:")
    attached_conn.execute(f"ATTACH DATABASE '{NATIONWIDE_V2_DB_PATH}' AS nw")
    attached_conn.execute(f"ATTACH DATABASE '{BRAND_MASTER_DB_PATH}' AS bm")

    att_cur = attached_conn.cursor()
    # 전체 735,208개 링크와 점포 정보 조인 스트리밍
    print("[Stage 4D Classifier] Streaming 735,208 store-brand links for category assignment...")
    t0 = time.time()
    att_cur.execute("""
        SELECT 
            l.link_id,
            l.bizes_id,
            s.bizes_nm,
            s.std_signgu_code,
            s.std_sido_code,
            s.inds_mcls_cd,
            s.inds_scls_cd,
            s.inds_scls_nm,
            s.lon,
            s.lat,
            l.internal_brand_id,
            l.match_status,
            l.operation_type,
            l.is_primary_link
        FROM bm.store_brand_links l
        JOIN nw.stores s ON l.bizes_id = s.bizes_id
        ORDER BY l.link_id
    """)

    target_cur = target_conn.cursor()
    target_conn.execute("PRAGMA synchronous = OFF;")
    target_conn.execute("PRAGMA journal_mode = MEMORY;")

    store_classifications_batch = []
    store_links_batch = []
    
    seen_bizes_ids = set()
    total_processed_links = 0
    divergent_count = 0
    confirmed_store_count = 0
    provisional_store_count = 0
    ambiguous_store_count = 0
    unclassified_store_count = 0

    chunk_size = 50000

    while True:
        rows = att_cur.fetchmany(chunk_size)
        if not rows:
            break

        for (link_id, bizes_id, bizes_nm, signgu_cd, ctprvn_cd,
             inds_mcls_cd, inds_scls_cd, inds_scls_nm, lon, lat,
             b_id, match_status, op_type, is_primary) in rows:

            total_processed_links += 1

            # 브랜드 연계 점포인 경우
            if b_id != "BRD_UNMATCHED" and b_id in brand_cache:
                (b_maj_id, b_maj_nm, b_mid_id, b_mid_nm, b_officiality, b_status) = brand_cache[b_id]
                is_brand_linked = 1

                # 점포 소진공 업종과 브랜드 대표업종 비교 (불일치 판정)
                store_semas_maj, store_semas_mid, _, _ = resolve_semas_to_mid(inds_scls_cd, bizes_nm)
                if store_semas_maj != b_maj_id:
                    is_divergent = 1
                    divergent_count += 1
                    applied_rule = "BRAND_REPRESENTATIVE_DIVERGENT"
                    status = "CATEGORY_PROVISIONAL"
                else:
                    is_divergent = 0
                    applied_rule = "BRAND_REPRESENTATIVE_MATCH"
                    status = b_status

                final_maj_id = b_maj_id
                final_maj_nm = b_maj_nm
                final_mid_id = b_mid_id
                final_mid_nm = b_mid_nm

            else:
                # 미매칭 독립 점포인 경우 (소진공 원본 코드로 직접 분류)
                is_brand_linked = 0
                is_divergent = 0
                final_maj_id, final_mid_id, rule_type, status = resolve_semas_to_mid(inds_scls_cd, bizes_nm)
                final_maj_nm = maj_id_to_name.get(final_maj_id, "한식")
                final_mid_nm = mid_id_to_name.get(final_mid_id, "고기구이/육류")
                applied_rule = f"INDEPENDENT_{rule_type}"

            # 상태 카운트 집계 (고유 점포 기준)
            if bizes_id not in seen_bizes_ids:
                if status == "CATEGORY_CONFIRMED":
                    confirmed_store_count += 1
                elif status == "CATEGORY_PROVISIONAL":
                    provisional_store_count += 1
                elif status == "AMBIGUOUS_REVIEW":
                    ambiguous_store_count += 1
                elif status == "UNCLASSIFIED":
                    unclassified_store_count += 1

                seen_bizes_ids.add(bizes_id)
                store_classifications_batch.append((
                    bizes_id, bizes_nm, signgu_cd, ctprvn_cd,
                    inds_mcls_cd, inds_scls_cd, inds_scls_nm,
                    b_id, final_maj_id, final_maj_nm, final_mid_id, final_mid_nm,
                    status, is_brand_linked, is_divergent, applied_rule,
                    lon, lat
                ))

            # 링크 테이블에는 735,208건 전수 기록 (N:M 숍인숍 보존)
            store_links_batch.append((
                link_id, bizes_id, b_id, final_maj_id, final_mid_id,
                match_status, op_type, is_primary
            ))

        # 배치 저장
        if len(store_classifications_batch) >= 20000:
            target_cur.executemany("""
                INSERT OR REPLACE INTO store_category_classifications
                (bizes_id, bizes_nm, signgu_cd, ctprvn_cd,
                 inds_mcls_cd, inds_scls_cd, inds_scls_nm,
                 primary_brand_id, category_major_id, category_major_name,
                 category_mid_id, category_mid_name, classification_status,
                 is_brand_linked, is_category_divergent, applied_rule,
                 lon, lat)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, store_classifications_batch)
            store_classifications_batch.clear()

        if len(store_links_batch) >= 20000:
            target_cur.executemany("""
                INSERT OR REPLACE INTO store_brand_category_links
                (link_id, bizes_id, internal_brand_id, category_major_id, category_mid_id,
                 match_status, operation_type, is_primary_link)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, store_links_batch)
            store_links_batch.clear()

        print(f"  Processed {total_processed_links:,} links (Unique stores: {len(seen_bizes_ids):,})...")

    # 잔여 데이터 플러시
    if store_classifications_batch:
        target_cur.executemany("""
            INSERT OR REPLACE INTO store_category_classifications
            (bizes_id, bizes_nm, signgu_cd, ctprvn_cd,
             inds_mcls_cd, inds_scls_cd, inds_scls_nm,
             primary_brand_id, category_major_id, category_major_name,
             category_mid_id, category_mid_name, classification_status,
             is_brand_linked, is_category_divergent, applied_rule,
             lon, lat)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, store_classifications_batch)
        store_classifications_batch.clear()

    if store_links_batch:
        target_cur.executemany("""
            INSERT OR REPLACE INTO store_brand_category_links
            (link_id, bizes_id, internal_brand_id, category_major_id, category_mid_id,
             match_status, operation_type, is_primary_link)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, store_links_batch)
        store_links_batch.clear()

    target_conn.commit()
    target_conn.execute("PRAGMA synchronous = NORMAL;")
    target_conn.execute("PRAGMA journal_mode = WAL;")

    attached_conn.close()

    elapsed = time.time() - t0
    print(f"[Stage 4D Classifier] Store classification completed in {elapsed:.2f}s:")
    print(f"  - Total unique stores classified: {len(seen_bizes_ids):,}")
    print(f"  - Total links classified: {total_processed_links:,}")
    print(f"  - Category confirmed stores: {confirmed_store_count:,}")
    print(f"  - Category provisional stores: {provisional_store_count:,}")
    print(f"  - Ambiguous review stores: {ambiguous_store_count:,}")
    print(f"  - Unclassified stores: {unclassified_store_count:,}")
    print(f"  - Category divergent stores: {divergent_count:,}")


def record_audit_metrics(conn: sqlite3.Connection) -> None:
    """분류 결과 정합성 감사 지표를 category_audit_metrics 테이블에 기록합니다."""
    cur = conn.cursor()

    # 1. 점포 수 확인
    cur.execute("SELECT count(*) FROM store_category_classifications")
    total_stores = cur.fetchone()[0]

    # 2. 링크 수 확인
    cur.execute("SELECT count(*) FROM store_brand_category_links")
    total_links = cur.fetchone()[0]

    # 3. 중분류 개수 확인
    cur.execute("SELECT count(*) FROM mid_categories")
    mid_count = cur.fetchone()[0]

    # 4. 대분류 개수 확인
    cur.execute("SELECT count(*) FROM major_categories")
    maj_count = cur.fetchone()[0]

    # 5. 브랜드 수 확인
    cur.execute("SELECT count(*) FROM brand_category_master")
    brand_count = cur.fetchone()[0]

    # 6. 모호 분류 점포 수
    cur.execute("SELECT count(*) FROM store_category_classifications WHERE classification_status = 'AMBIGUOUS_REVIEW'")
    ambiguous_stores = cur.fetchone()[0]

    # 7. 확정 점포 수
    cur.execute("SELECT count(*) FROM store_category_classifications WHERE classification_status = 'CATEGORY_CONFIRMED'")
    confirmed_stores = cur.fetchone()[0]

    # 8. 미분류 점포 수
    cur.execute("SELECT count(*) FROM store_category_classifications WHERE classification_status = 'UNCLASSIFIED'")
    unclassified_stores = cur.fetchone()[0]

    # 9. 복수 브랜드 점포 수 (23건)
    cur.execute("SELECT count(*) FROM (SELECT bizes_id FROM store_brand_category_links GROUP BY bizes_id HAVING count(*) > 1)")
    multi_brand_stores = cur.fetchone()[0]

    metrics = [
        ("NATIONWIDE_TOTAL_STORES", float(total_stores), "STORE_LEVEL", "PASS" if total_stores == 735185 else "FAIL", f"전국 점포수 735,185건 일치 여부: {total_stores}"),
        ("STORE_BRAND_CATEGORY_LINKS", float(total_links), "LINK_LEVEL", "PASS" if total_links == 735208 else "FAIL", f"전국 링크수 735,208건 일치 여부: {total_links}"),
        ("MAJOR_CATEGORY_COUNT", float(maj_count), "TAXONOMY", "PASS" if maj_count == 8 else "FAIL", f"확정 8대 대분류 개수 일치: {maj_count}"),
        ("MID_CATEGORY_COUNT", float(mid_count), "TAXONOMY", "PASS" if mid_count == 48 else "FAIL", f"확정 48대 중분류 개수 일치: {mid_count}"),
        ("BRAND_MASTER_COUNT", float(brand_count), "BRAND_LEVEL", "PASS" if brand_count == 5063 else "FAIL", f"브랜드 마스터 5,063건 전수 이관 일치: {brand_count}"),
        ("MULTI_BRAND_SHOP_COUNT", float(multi_brand_stores), "LINK_LEVEL", "PASS" if multi_brand_stores == 23 else "FAIL", f"복수 브랜드 숍인숍 점포 수 23건 대사: {multi_brand_stores}"),
        ("AMBIGUOUS_STORE_COUNT", float(ambiguous_stores), "QUALITY", "PASS", f"모호 분류 관리 점포 수: {ambiguous_stores:,}"),
        ("CONFIRMED_STORE_COUNT", float(confirmed_stores), "QUALITY", "PASS", f"공식 브랜드 기반 확정 점포 수: {confirmed_stores:,}"),
        ("UNCLASSIFIED_STORE_COUNT", float(unclassified_stores), "QUALITY", "PASS" if unclassified_stores == 0 else "WARNING", f"미분류 결측 점포 수: {unclassified_stores:,}"),
    ]

    cur.executemany("""
        INSERT OR REPLACE INTO category_audit_metrics
        (metric_name, metric_value, target_dimension, status, detail_message)
        VALUES (?, ?, ?, ?, ?)
    """, metrics)
    conn.commit()
    print("[Stage 4D Classifier] Category audit metrics successfully recorded.")


def run_stage4d_pipeline() -> None:
    """Stage 4D 전체 분류 파이프라인 실행 진입점"""
    print("=" * 70)
    print("Franchise Dashboard - Stage 4D: 8대 대분류 & 48대 중분류 분류 파이프라인 가동")
    print("=" * 70)

    # 1. DB 초기화
    init_category_master_db()

    conn = sqlite3.connect(CATEGORY_MASTER_DB_PATH)
    
    # 2. 마스터 분류체계 등록
    populate_taxonomy_reference_tables(conn)

    # 3. 브랜드 대표 업종 마스터 구축
    brand_cache = build_brand_category_master(conn)

    # 4. 전국 73.5만 개 점포 및 링크 분류
    classify_nationwide_stores(conn, brand_cache)

    # 5. 집계 감사 지표 기록
    record_audit_metrics(conn)

    conn.close()
    print("=" * 70)
    print("Stage 4D 분류 파이프라인 정상 완료!")
    print("=" * 70)


if __name__ == "__main__":
    run_stage4d_pipeline()
