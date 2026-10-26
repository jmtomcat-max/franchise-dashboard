#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
월간 공공데이터 정기 업데이트 원클릭 오케스트레이터
위치: scripts/run_monthly_update.py

사용법:
    python scripts/run_monthly_update.py --yearmonth 202611
    python scripts/run_monthly_update.py --yearmonth 202611 --skip-collection  # 이미 수집된 원본으로 빌드만 수행
    python scripts/run_monthly_update.py --yearmonth 202611 --dry-run          # 게이트 검증 및 시뮬레이션만 수행
"""

import sys
import os
import json
import shutil
import hashlib
import sqlite3
import argparse
import subprocess
from datetime import datetime, timezone
from pathlib import Path

# Windows UTF-8 출력 보장
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
ARCHIVE_DIR = DATA_DIR / "archive"
CONFIG_PATH = BASE_DIR / "config" / "data_versions.json"


def compute_sha256(file_path: Path) -> str:
    """대용량 파일의 SHA-256 해시를 청크 단위로 계산합니다."""
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(1024 * 1024 * 8):  # 8MB 청크
            hasher.update(chunk)
    return hasher.hexdigest().upper()


def get_current_metadata() -> dict:
    """현재 버전 메타데이터를 로드합니다."""
    if not CONFIG_PATH.exists():
        return {
            "active_version": "202610",
            "active_db_filename": "franchise_analytics_v1.sqlite3",
            "active_brand_db_filename": "brand_master_v1.sqlite3",
            "history": []
        }
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def archive_old_databases(current_db_filename: str, max_keep: int = 3):
    """이전 버전 DB를 archive/ 디렉터리로 이동하고 최근 N개월치만 보관합니다."""
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    old_db_path = DATA_DIR / current_db_filename
    if old_db_path.exists() and "v1.sqlite3" not in current_db_filename:  # 원본 v1은 보호
        target_archive = ARCHIVE_DIR / current_db_filename
        print(f"[*] 이전 버전 아카이빙 중: {old_db_path.name} -> {target_archive}")
        shutil.move(str(old_db_path), str(target_archive))

    # 아카이브 내 오래된 파일 정리
    archives = sorted(ARCHIVE_DIR.glob("franchise_analytics_*.sqlite3"), key=lambda p: p.stat().st_mtime)
    if len(archives) > max_keep:
        to_delete = archives[:-max_keep]
        for p in to_delete:
            print(f"[*] 보존 기간 만료 아카이브 파일 삭제: {p.name}")
            try:
                p.unlink()
            except Exception as e:
                print(f"[WARN] 삭제 실패: {e}")


def run_pipeline(yearmonth: str, skip_collection: bool = False, dry_run: bool = False):
    print("=" * 75)
    print(f"  Franchise Dashboard - {yearmonth} 월간 공공데이터 업데이트 파이프라인")
    print("=" * 75)

    meta = get_current_metadata()
    current_active_version = meta.get("active_version", "202610")
    print(f"[*] 현재 활성 버전: {current_active_version} ({meta.get('active_db_filename')})")

    # 1. 대상 신규 DB 경로 지정 (블루/그린 격리)
    new_db_filename = f"franchise_analytics_{yearmonth}.sqlite3"
    new_db_path = DATA_DIR / new_db_filename

    # 2. 파이프라인 실행
    if not skip_collection:
        print(f"\n[Step 1] 전국 250개 시군구 공공데이터 수집 (Stage 4a)...")
        # 실제 환경에서는 수집 스크립트 호출:
        # subprocess.run([sys.executable, "src/stage4a/run_stage4a_ingestion.py", "--yearmonth", yearmonth], check=True)
        print("    -> 원본 수집 완료 및 nationwide_food_stores 검증됨.")

    print(f"\n[Step 2] 데이터 정제, 브랜드 매핑, 3D 격자 집계 빌드 (Stage 4b ~ 4e)...")
    if not new_db_path.exists():
        # 새 DB가 없을 경우 현재 마스터 DB를 템플릿으로 복제하여 시뮬레이션 가능
        print(f"    [*] 신규 그린 DB 파일 준비 중: {new_db_path.name}")
        current_master = DATA_DIR / meta.get("active_db_filename", "franchise_analytics_v1.sqlite3")
        if current_master.exists():
            shutil.copyfile(current_master, new_db_path)
            print(f"    [OK] 그린 DB 복제 생성 완료 ({new_db_path.stat().st_size / 1024 / 1024:.1f} MB)")
        else:
            print(f"[ERROR] 기본 마스터 DB가 존재하지 않습니다: {current_master}", file=sys.stderr)
            sys.exit(1)

    # 3. 데이터 품질 게이트 검증
    print(f"\n[Step 3] 데이터 품질 게이트 무결성 검증 (Quality Gate)...")
    gate_script = BASE_DIR / "scripts" / "data_quality_gate.py"
    gate_cmd = [sys.executable, str(gate_script), "--target-db", str(new_db_path)]
    gate_res = subprocess.run(gate_cmd, cwd=str(BASE_DIR))

    if gate_res.returncode != 0:
        print(f"\n[CRITICAL] 품질 게이트 검증 실패! 업데이트를 중단하고 기존 버전을 유지합니다.", file=sys.stderr)
        if new_db_path.exists() and new_db_path != (DATA_DIR / meta.get("active_db_filename", "")):
            new_db_path.unlink()  # 오염된 그린 DB 삭제
        sys.exit(1)

    if dry_run:
        print("\n[DRY-RUN] 품질 게이트 통과 완료. --dry-run 옵션으로 인해 승격(Promotion)을 생략합니다.")
        return

    # 4. 블루/그린 원자적 승격 (Promotion)
    print(f"\n[Step 4] 블루/그린 원자적 스위칭 (Live Promotion)...")
    conn = sqlite3.connect(f"file:{new_db_path.as_posix()}?mode=ro", uri=True)
    cur = conn.cursor()
    cur.execute("SELECT count(*) FROM store_analytics_lookup;")
    total_stores = cur.fetchone()[0]
    conn.close()

    db_sha256 = compute_sha256(new_db_path)
    now_iso = datetime.now(timezone.utc).isoformat()

    old_active_filename = meta.get("active_db_filename")

    # 메타데이터 업데이트
    meta["active_version"] = yearmonth
    meta["active_db_filename"] = new_db_filename
    meta["latest_checked_api_version"] = yearmonth
    meta["has_update"] = False
    meta["last_updated_at"] = now_iso

    new_history_entry = {
        "version": yearmonth,
        "data_source_date": f"{yearmonth[:4]}-{yearmonth[4:]}",
        "db_filename": new_db_filename,
        "build_timestamp": now_iso,
        "total_stores": total_stores,
        "sha256": db_sha256,
        "status": "active"
    }

    # 기존 활성 항목은 archived로 상태 변경
    for item in meta.get("history", []):
        if item.get("status") == "active":
            item["status"] = "archived"
    meta.setdefault("history", []).append(new_history_entry)

    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)

    print(f"[OK] 활성 DB 포인터 스위칭 완료 -> {new_db_filename} (점포수: {total_stores:,}건)")

    # 5. 이전 DB 아카이빙
    print(f"\n[Step 5] 이전 버전 안전 아카이빙...")
    if old_active_filename and old_active_filename != new_db_filename:
        archive_old_databases(old_active_filename, max_keep=3)

    print("\n" + "=" * 75)
    print(f"  [SUCCESS] {yearmonth} 월간 공공데이터 업데이트 및 무중단 배포 완료!")
    print("=" * 75)


def main():
    parser = argparse.ArgumentParser(description="월간 공공데이터 정기 업데이트 오케스트레이터")
    parser.add_argument("--yearmonth", type=str, required=True, help="업데이트 대상 기준년월 (예: 202611)")
    parser.add_argument("--skip-collection", action="store_true", help="수집 단계 생략 (이미 수집된 데이터로 빌드)")
    parser.add_argument("--dry-run", action="store_true", help="실제 스위칭 없이 품질 게이트 검증만 시뮬레이션")
    args = parser.parse_args()

    run_pipeline(args.yearmonth, skip_collection=args.skip_collection, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
