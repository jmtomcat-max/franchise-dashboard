"""
Franchise Dashboard - 프로덕션 SQLite 데이터베이스 안전 백업 스크립트
위치: scripts/backup_production_db.py

주요 기능:
1. SQLite Online Backup API를 통한 무중단/일관성 백업 생성
2. 백업 파일 SHA-256 해시 생성 및 .sha256 검증 파일 기록
3. 백업된 복사본 대상 PRAGMA integrity_check 무결성 자동 검증
4. 백업 보존 주기(기본 7일) 초과 파일 자동 회전 및 정리
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import sqlite3
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("backup")

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
DEFAULT_BACKUP_DIR = ROOT / "backups"

# 프로덕션 서비스 운영 데이터베이스 3종 정의
SERVICE_DATABASES = [
    {
        "name": "franchise_analytics_v1",
        "filename": "franchise_analytics_v1.sqlite3",
        "description": "전국 73.5만 점포 전수 공간 분석 및 16개 시도/256개 시군구 통계 DB",
        "verify_sql": "SELECT COUNT(*) FROM regional_overall_stats;",
    },
    {
        "name": "ftc_macro_statistics_v1",
        "filename": "ftc_macro_statistics_v1.sqlite3",
        "description": "공정거래위원회 4개년(2023~2026) 거시통계 및 창업비용 벤치마크 DB",
        "verify_sql": "SELECT COUNT(*) FROM ftc_industry_macro_summary;",
    },
    {
        "name": "brand_master_v1",
        "filename": "brand_master_v1.sqlite3",
        "description": "5,063개 브랜드 마스터 및 대사 데이터베이스",
        "verify_sql": "SELECT COUNT(*) FROM brands;",
    },
]


def compute_sha256(path: Path) -> str:
    """파일의 SHA-256 해시를 계산합니다."""
    hasher = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(1024 * 1024):
            hasher.update(chunk)
    return hasher.hexdigest().upper()


def perform_single_db_backup(source_db_path: Path, dest_dir: Path, verify_sql: Optional[str] = None) -> tuple[Path, str, dict]:
    """단일 SQLite 데이터베이스에 대한 온라인 백업 및 무결성 검증을 수행합니다."""
    if not source_db_path.exists():
        raise FileNotFoundError(f"데이터베이스 파일을 찾을 수 없습니다: {source_db_path}")

    dest_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"{source_db_path.stem}_backup_{timestamp}.sqlite3"
    backup_path = dest_dir / backup_filename

    logger.info(f"온라인 백업 진행: {source_db_path.name} -> {backup_filename}")
    start_time = time.time()

    # 원본 DB는 읽기 전용 URI 모드로 연결 (무락 복제)
    source_uri = f"{source_db_path.resolve().as_uri()}?mode=ro"
    with sqlite3.connect(source_uri, uri=True) as src_conn:
        with sqlite3.connect(str(backup_path)) as dst_conn:
            src_conn.backup(dst_conn, pages=200, sleep=0.005)

    elapsed = time.time() - start_time
    file_size = backup_path.stat().st_size
    backup_hash = compute_sha256(backup_path)

    # SHA256 체크섬 파일 저장
    sha_file = dest_dir / f"{backup_filename}.sha256"
    sha_file.write_text(f"{backup_hash}  {backup_filename}\n", encoding="utf-8")

    # 무결성 검증
    with sqlite3.connect(str(backup_path)) as verify_conn:
        integrity_row = verify_conn.execute("PRAGMA integrity_check;").fetchone()
        integrity_status = integrity_row[0] if integrity_row else "unknown"
        sample_metric = None
        if verify_sql:
            try:
                sample_metric = verify_conn.execute(verify_sql).fetchone()[0]
            except Exception as e:
                logger.warning(f"샘플 쿼리 검증 경고 ({source_db_path.name}): {e}")

    if integrity_status.lower() != "ok":
        raise RuntimeError(f"백업 무결성 검사 실패 ({source_db_path.name}): {integrity_status}")

    metadata = {
        "source": str(source_db_path),
        "source_filename": source_db_path.name,
        "backup_file": backup_filename,
        "backup_path": str(backup_path),
        "backup_size_bytes": file_size,
        "sha256": backup_hash,
        "integrity_check": integrity_status,
        "sample_metric": sample_metric,
        "elapsed_seconds": round(elapsed, 2),
        "timestamp": datetime.now().isoformat()
    }

    meta_file = dest_dir / f"{backup_filename}.meta.json"
    meta_file.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")

    logger.info(f"성공 [{source_db_path.name}]: {file_size:,} bytes, {elapsed:.2f}s, 무결성={integrity_status}")
    return backup_path, backup_hash, metadata


def rotate_old_backups(backup_dir: Path, retention_days: int = 7) -> int:
    """보존 기한을 초과한 오래된 백업 파일을 정리합니다."""
    if retention_days < 1:
        raise ValueError(f"보존 일수(retention_days)는 최소 1일 이상이어야 합니다. (입력값: {retention_days})")

    cutoff = datetime.now() - timedelta(days=retention_days)
    removed_count = 0

    for item in backup_dir.glob("*_backup_*.sqlite3*"):
        try:
            mtime = datetime.fromtimestamp(item.stat().st_mtime)
            if mtime < cutoff:
                item.unlink()
                removed_count += 1
                logger.info(f"오래된 백업 삭제: {item.name}")
        except Exception as e:
            logger.warning(f"백업 파일 정리 실패 ({item.name}): {e}")

    return removed_count


def backup_all_service_databases(data_dir: Path, dest_dir: Path) -> list[dict]:
    """운영 서비스 데이터베이스 3종 전체를 순차적으로 안전하게 백업합니다."""
    results = []
    logger.info(f"서비스 데이터베이스 3종 일괄 백업 시작 (대상: {len(SERVICE_DATABASES)}개)")
    for db_info in SERVICE_DATABASES:
        db_path = data_dir / db_info["filename"]
        backup_path, backup_hash, meta = perform_single_db_backup(db_path, dest_dir, db_info.get("verify_sql"))
        meta["description"] = db_info["description"]
        results.append(meta)
    return results


def main():
    parser = argparse.ArgumentParser(description="Franchise Dashboard SQLite Multi-DB Backup Utility")
    parser.add_argument("--db-path", type=Path, default=None, help="특정 단일 SQLite 데이터베이스 백업 시 경로")
    parser.add_argument("--data-dir", type=Path, default=DATA_DIR, help="운영 DB 디렉터리 경로")
    parser.add_argument("--target-dir", type=Path, default=DEFAULT_BACKUP_DIR, help="백업 저장 대상 디렉터리")
    parser.add_argument("--retention-days", type=int, default=7, help="보존 일수 (기본 7일, 최소 1일 이상)")
    parser.add_argument("--no-rotate", action="store_true", help="오래된 백업 자동 정리 건너뛰기")
    args = parser.parse_args()

    try:
        # 백업 시작 전 보존 일수 유효성 선행 검증 (방금 생성한 백업 삭제 방지)
        if not args.no_rotate and args.retention_days < 1:
            raise ValueError(f"보존 일수(--retention-days)는 최소 1일 이상이어야 합니다. (입력값: {args.retention_days})")

        if args.db_path:
            # 단일 DB 백업 모드
            backup_path, backup_hash, meta = perform_single_db_backup(args.db_path, args.target_dir)
            print(f"BACKUP_SUCCESS: {backup_path.name} [SHA256: {backup_hash[:16]}...]")
        else:
            # 서비스 운영 DB 3종 전체 일괄 백업 모드 (기본)
            results = backup_all_service_databases(args.data_dir, args.target_dir)
            summary_str = ", ".join(f"{r['source_filename']}({r['backup_size_bytes']//1024}KB)" for r in results)
            print(f"ALL_BACKUPS_SUCCESS: {len(results)}개 DB 백업 완료 [{summary_str}]")

        if not args.no_rotate:
            removed = rotate_old_backups(args.target_dir, args.retention_days)
            logger.info(f"백업 보존 주기 로테이션 완료: {removed}개 정리됨")
        return 0
    except Exception as exc:
        logger.error(f"백업 작업 실패: {exc}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
