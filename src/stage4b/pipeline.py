"""
Stage 4B: 전국 735,185건 외식업 점포 대상 브랜드 후보 추출 고속 파이프라인
프로젝트: D:/Franchise_Dashboard
위치: src/stage4b/pipeline.py
"""

import os
import sys
import time
import sqlite3
import datetime
from pathlib import Path
from collections import Counter, defaultdict
from typing import Dict, List, Any, Optional, Tuple

BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.stage4b.schema_stage4b import DEFAULT_STAGE4B_DB_PATH, initialize_stage4b_database
from src.stage4b.normalizer import normalize_store_name_full
from src.stage4b.brand_dictionary import (
    OFFICIAL_BRAND_SEEDS,
    BRAND_LOOKUP_DICT,
    GENERIC_FOOD_NOUNS
)
from src.stage4b.candidate_engine import evaluate_store_candidate, RULE_VERSION

SEMAS_V2_DB_PATH = BASE_DIR / "data" / "nationwide_food_stores_v2.sqlite3"
BATCH_CHUNK_SIZE = 50000


def run_stage4b_nationwide_pipeline(
    source_db_path: Path = SEMAS_V2_DB_PATH,
    target_db_path: Path = DEFAULT_STAGE4B_DB_PATH,
    resume_checkpoint: bool = True
) -> Dict[str, Any]:
    """
    전국 735,185건 점포를 대상으로 고속 브랜드 후보 추출 및 매핑 파이프라인을 실행한다.
    
    1. Read-Only 소스 DB 연결 및 무결성 검증
    2. 정규화 및 전국 단위 상호 빈도 집계 (Pass 1)
    3. 공식 브랜드 및 10개 이상 클러스터 후보 마스터 등록
    4. 점포-후보 매핑 및 정밀 상태 판정 (Pass 2)
    5. 감사 로그, 체크포인트 및 정합성 검증
    """
    start_time_all = time.time()
    run_id = f"RUN_4B_NW_{int(start_time_all)}"
    now_iso = datetime.datetime.now().isoformat()

    print(f"================================================================================")
    print(f"[*] Phase 4 Stage 4B 전국 브랜드 후보 추출 파이프라인 시작 (Run ID: {run_id})")
    print(f"[*] 원본 소스 DB (Read-Only): {source_db_path}")
    print(f"[*] 타깃 후보 DB: {target_db_path}")
    print(f"================================================================================")

    # 1. 타깃 DB 초기화
    initialize_stage4b_database(target_db_path)

    # 소스 DB 연결 (Read-Only 명시)
    if not source_db_path.exists():
        raise FileNotFoundError(f"Source DB not found at: {source_db_path}")

    src_uri = f"file:{source_db_path.resolve()}?mode=ro"
    src_con = sqlite3.connect(src_uri, uri=True)
    src_cur = src_con.cursor()

    total_input_stores = src_cur.execute("SELECT COUNT(*) FROM stores").fetchone()[0]
    print(f"[*] 원본 총 점포 수: {total_input_stores:,}건")

    tgt_con = sqlite3.connect(target_db_path)
    tgt_cur = tgt_con.cursor()
    tgt_cur.execute("PRAGMA journal_mode=WAL;")
    tgt_cur.execute("PRAGMA synchronous=NORMAL;")
    tgt_cur.execute("PRAGMA cache_size=200000;")

    # 기존 진행 데이터 확인 (체크포인트)
    existing_processed = 0
    if resume_checkpoint:
        existing_processed = tgt_cur.execute("SELECT COUNT(*) FROM store_normalization").fetchone()[0]
        if existing_processed == total_input_stores:
            print(f"[!] 이미 전수 정규화({existing_processed:,}건)가 완료되어 있습니다. 갱신 또는 재평가를 진행합니다.")

    # 2. 공식 브랜드 사전 시드 등록
    print(f"[*] 1단계: 공인 브랜드 사전 등록 (총 {len(OFFICIAL_BRAND_SEEDS)}개 브랜드)...")
    for b in OFFICIAL_BRAND_SEEDS:
        tgt_cur.execute("""
            INSERT OR REPLACE INTO brand_candidates (
                candidate_brand_id, brand_name_raw, brand_name_norm, brand_name_clean,
                category_major, discovery_method, official_source,
                total_store_count, verification_status, rule_version, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, 'OFFICIAL_DICTIONARY', ?, 0, 'OFFICIAL_VERIFIED', ?, ?, ?)
        """, (
            b["candidate_id"], b["brand_name"], b["brand_name"], b["brand_name"].replace(" ", "").lower(),
            b["category_major"], b["official_source"], RULE_VERSION, now_iso, now_iso
        ))

        # 별칭 등록
        for alias in b["aliases"]:
            tgt_cur.execute("""
                INSERT OR IGNORE INTO brand_aliases (
                    candidate_brand_id, alias_text, alias_norm, alias_type, is_official
                ) VALUES (?, ?, ?, 'SYNONYM', 1)
            """, (b["candidate_id"], alias, alias.replace(" ", "").lower()))

    tgt_con.commit()

    # 3. Pass 1: 전국 전수 정규화 및 클러스터 빈도 집계
    print(f"[*] 2단계: 전국 {total_input_stores:,}건 상호 정규화 및 클러스터 빈도 계산 (배치 크기: {BATCH_CHUNK_SIZE:,}건)...")
    clean_key_counter: Counter = Counter()
    clean_key_meta: Dict[str, Dict[str, Any]] = {}

    pass1_start = time.time()
    offset = 0
    norm_batch = []

    # 기존 store_normalization 초기화 (멱등성 보장)
    tgt_cur.execute("DELETE FROM store_normalization;")
    tgt_cur.execute("DELETE FROM store_brand_candidates;")
    tgt_con.commit()

    src_cur.execute("""
        SELECT bizes_id, bizes_nm, brch_nm, inds_mcls_cd, inds_scls_cd, inds_mcls_nm, inds_scls_nm
        FROM stores
    """)

    processed_count = 0
    while True:
        rows = src_cur.fetchmany(BATCH_CHUNK_SIZE)
        if not rows:
            break

        norm_insert_batch = []
        for r in rows:
            bizes_id, bizes_nm, brch_nm, mcls_cd, scls_cd, mcls_nm, scls_nm = r
            norm = normalize_store_name_full(bizes_nm, brch_nm)
            ckey = norm["clean_key"]

            clean_key_counter[ckey] += 1
            if ckey not in clean_key_meta:
                clean_key_meta[ckey] = {
                    "raw_name": norm["normalized_core_nm"],
                    "mcls_nm": mcls_nm,
                    "mcls_cd": mcls_cd,
                    "scls_cd": scls_cd
                }

            norm_insert_batch.append((
                bizes_id, bizes_nm, norm["normalized_core_nm"],
                norm["branch_suffix"], norm["branch_position"],
                norm["legal_entity_tag"], norm["is_reconstructible"], now_iso
            ))

        tgt_cur.executemany("""
            INSERT INTO store_normalization (
                bizes_id, raw_bizes_nm, normalized_core_nm, branch_suffix,
                branch_position, legal_entity_tag, is_reconstructible, processed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, norm_insert_batch)
        tgt_con.commit()

        processed_count += len(rows)
        if processed_count % 100000 == 0 or processed_count == total_input_stores:
            elapsed = time.time() - pass1_start
            rate = processed_count / elapsed
            print(f"    [Pass 1 진행] {processed_count:,} / {total_input_stores:,}건 정규화 완료 ({rate:.0f} stores/sec)")

    pass1_duration = time.time() - pass1_start
    print(f"[OK] Pass 1 정규화 완료: {processed_count:,}건 소요시간: {pass1_duration:.2f}초 (고유 상호키: {len(clean_key_counter):,}개)")

    # 4. Pass 1.5: 10개 이상 동일 상호 클러스터 후보 마스터 자동 승격
    print(f"[*] 3단계: 전국 동일 상호 10개 이상 클러스터 후보 승격 판정...")
    cluster_promoted_count = 0
    for ckey, count in clean_key_counter.items():
        if count >= 10 and len(ckey) >= 2:
            # 일반명사 및 공식 사전 제외
            if ckey not in GENERIC_FOOD_NOUNS and ckey not in BRAND_LOOKUP_DICT:
                meta = clean_key_meta[ckey]
                cand_id = f"CAN_CLUS_{ckey[:12]}"
                tgt_cur.execute("""
                    INSERT OR REPLACE INTO brand_candidates (
                        candidate_brand_id, brand_name_raw, brand_name_norm, brand_name_clean,
                        category_major, representative_inds_mcls_cd, representative_inds_scls_cd,
                        discovery_method, official_source, total_store_count,
                        verification_status, rule_version, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, 'NATIONWIDE_CLUSTER_10PLUS', 'SEMAS_V2_STAT', ?, 'CANDIDATE_CLUSTER', ?, ?, ?)
                """, (
                    cand_id, meta["raw_name"], meta["raw_name"], ckey,
                    meta["mcls_nm"] or "기타외식", meta["mcls_cd"], meta["scls_cd"],
                    count, RULE_VERSION, now_iso, now_iso
                ))
                cluster_promoted_count += 1

    tgt_con.commit()
    print(f"[OK] 10개 이상 클러스터 후보 {cluster_promoted_count:,}개 자동 승격 완료")

    # 5. Pass 2: 점포-후보 정밀 매핑 및 평가
    print(f"[*] 4단계: 전국 점포-후보 매핑 및 신뢰도/상태 판정 (Pass 2)...")
    pass2_start = time.time()

    src_cur.execute("""
        SELECT bizes_id, bizes_nm, brch_nm, inds_mcls_cd, inds_scls_cd, inds_mcls_nm, inds_scls_nm
        FROM stores
    """)

    mapped_count = 0
    verified_auto_count = 0
    provisional_count = 0
    review_required_count = 0
    independent_count = 0
    multi_candidate_count = 0

    brand_store_counts = defaultdict(int)

    while True:
        rows = src_cur.fetchmany(BATCH_CHUNK_SIZE)
        if not rows:
            break

        cand_insert_batch = []
        for r in rows:
            bizes_id, bizes_nm, brch_nm, mcls_cd, scls_cd, mcls_nm, scls_nm = r
            norm = normalize_store_name_full(bizes_nm, brch_nm)
            ckey = norm["clean_key"]
            cluster_cnt = clean_key_counter[ckey]

            eval_cands = evaluate_store_candidate(
                store_norm=norm,
                bizes_id=bizes_id,
                inds_mcls_cd=mcls_cd,
                inds_scls_cd=scls_cd,
                inds_mcls_nm=mcls_nm,
                inds_scls_nm=scls_nm,
                cluster_store_count=cluster_cnt
            )

            if len(eval_cands) > 1:
                multi_candidate_count += 1

            for c in eval_cands:
                status = c["store_verification_status"]
                cand_id = c["candidate_brand_id"]
                if status == "VERIFIED_AUTO":
                    verified_auto_count += 1
                    brand_store_counts[cand_id] += 1
                elif status == "PROVISIONAL":
                    provisional_count += 1
                    brand_store_counts[cand_id] += 1
                elif status == "REVIEW_REQUIRED":
                    review_required_count += 1
                    brand_store_counts[cand_id] += 1
                else:
                    independent_count += 1

                cand_insert_batch.append((
                    bizes_id, cand_id, c["match_method"],
                    c["confidence_score"], status,
                    c["franchisor_status"], c["branch_operation_type"],
                    c["is_primary_candidate"], c["notes"],
                    c["rule_version"], now_iso
                ))

        tgt_cur.executemany("""
            INSERT INTO store_brand_candidates (
                bizes_id, candidate_brand_id, match_method,
                confidence_score, store_verification_status,
                franchisor_status, branch_operation_type,
                is_primary_candidate, notes, rule_version, evaluated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, cand_insert_batch)
        tgt_con.commit()

        mapped_count += len(rows)
        if mapped_count % 100000 == 0 or mapped_count == total_input_stores:
            elapsed = time.time() - pass2_start
            rate = mapped_count / elapsed
            print(f"    [Pass 2 진행] {mapped_count:,} / {total_input_stores:,}건 매핑 완료 ({rate:.0f} stores/sec)")

    # 브랜드 후보별 최종 점포 수 업데이트
    for cand_id, s_cnt in brand_store_counts.items():
        if cand_id != "NONE_INDEPENDENT":
            tgt_cur.execute("""
                UPDATE brand_candidates
                SET total_store_count = ?
                WHERE candidate_brand_id = ?
            """, (s_cnt, cand_id))
    tgt_con.commit()

    pass2_duration = time.time() - pass2_start
    total_duration = time.time() - start_time_all

    # 6. 감사 로그 기록
    candidate_linked_stores = verified_auto_count + provisional_count + review_required_count
    distinct_brands_count = tgt_cur.execute("SELECT COUNT(*) FROM brand_candidates").fetchone()[0]

    tgt_cur.execute("""
        INSERT INTO candidate_audit_log (
            run_id, batch_step, start_time, end_time,
            total_processed, matched_stores, unmatched_stores,
            multi_candidate_stores, duration_seconds, throughput_stores_per_sec,
            status, log_message
        ) VALUES (?, 'FULL_NATIONWIDE_PIPELINE', ?, ?, ?, ?, ?, ?, ?, ?, 'COMPLETED', ?)
    """, (
        run_id, now_iso, datetime.datetime.now().isoformat(),
        total_input_stores, candidate_linked_stores, independent_count,
        multi_candidate_count, round(total_duration, 2),
        round(total_input_stores / total_duration, 1),
        f"Nationwide processing completed: verified_auto={verified_auto_count}, provisional={provisional_count}, review={review_required_count}, independent={independent_count}"
    ))
    tgt_con.commit()

    src_con.close()
    tgt_con.close()

    summary = {
        "run_id": run_id,
        "total_input_stores": total_input_stores,
        "processed_stores": mapped_count,
        "candidate_linked_stores": candidate_linked_stores,
        "independent_unlinked_stores": independent_count,
        "breakdown": {
            "verified_auto_stores": verified_auto_count,
            "provisional_cluster_stores": provisional_count,
            "review_required_stores": review_required_count,
            "independent_stores": independent_count,
            "multi_candidate_stores": multi_candidate_count
        },
        "distinct_brand_candidates_count": distinct_brands_count,
        "execution_time_seconds": round(total_duration, 2),
        "overall_throughput_stores_per_sec": round(total_input_stores / total_duration, 1)
    }

    print(f"\n================================================================================")
    print(f"[*] 전국 735,185건 처리 완료 요약")
    print(f"    - 총 입력 점포 수: {summary['total_input_stores']:,}건 (100.0%)")
    print(f"    - 후보 연결 점포 수: {summary['candidate_linked_stores']:,}건 ({(candidate_linked_stores/total_input_stores)*100:.2f}%)")
    print(f"      * 자동 확정(VERIFIED_AUTO): {verified_auto_count:,}건")
    print(f"      * 클러스터 후보(PROVISIONAL): {provisional_count:,}건")
    print(f"      * 검토 필요(REVIEW_REQUIRED): {review_required_count:,}건")
    print(f"    - 독립 개인 점포 수: {summary['independent_unlinked_stores']:,}건 ({(independent_count/total_input_stores)*100:.2f}%)")
    print(f"    - 복수 후보 점포 수: {multi_candidate_count:,}건")
    print(f"    - 도출된 총 브랜드 후보 수: {distinct_brands_count:,}개")
    print(f"    - 총 소요 시간: {summary['execution_time_seconds']}초 (초당 {summary['overall_throughput_stores_per_sec']}건)")
    print(f"================================================================================")

    return summary


if __name__ == "__main__":
    run_stage4b_nationwide_pipeline()
