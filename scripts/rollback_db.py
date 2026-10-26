#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
데이터베이스 비상 롤백(Rollback) 스크립트
위치: scripts/rollback_db.py

사용법:
    python scripts/rollback_db.py --to 202610
    python scripts/rollback_db.py --list          # 롤백 가능한 버전 목록 확인
"""

import sys
import json
import shutil
import argparse
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


def list_versions():
    if not CONFIG_PATH.exists():
        print("[ERROR] config/data_versions.json 파일이 없습니다.", file=sys.stderr)
        sys.exit(1)

    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        meta = json.load(f)

    active_v = meta.get("active_version", "unknown")
    print("=" * 60)
    print(f"  Franchise Dashboard - 데이터베이스 버전 히스토리 (현재 활성: {active_v})")
    print("=" * 60)
    for idx, item in enumerate(meta.get("history", []), 1):
        v = item.get("version")
        status = item.get("status")
        stores = item.get("total_stores", 0)
        dt = item.get("build_timestamp", "")[:10]
        curr_mark = " <-- [ACTIVE]" if v == active_v else ""
        print(f"  {idx}. 버전: {v} | 점포수: {stores:,}건 | 빌드: {dt} | 상태: {status}{curr_mark}")
    print("=" * 60)


def rollback_to_version(target_version: str):
    if not CONFIG_PATH.exists():
        print("[ERROR] config/data_versions.json 파일이 없습니다.", file=sys.stderr)
        sys.exit(1)

    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        meta = json.load(f)

    active_v = meta.get("active_version")
    if active_v == target_version:
        print(f"[WARN] 요청하신 버전({target_version})은 이미 현재 활성 버전입니다.")
        return

    # 대상 버전 찾기
    target_entry = None
    for item in meta.get("history", []):
        if item.get("version") == target_version:
            target_entry = item
            break

    if not target_entry:
        print(f"[ERROR] 히스토리에 존재하지 않는 버전입니다: {target_version}", file=sys.stderr)
        sys.exit(1)

    target_db_filename = target_entry.get("db_filename") or f"franchise_analytics_{target_version}.sqlite3"
    target_path = DATA_DIR / target_db_filename

    # data/ 에 없으면 archive/ 확인 후 복원
    if not target_path.exists():
        archive_path = ARCHIVE_DIR / target_db_filename
        if archive_path.exists():
            print(f"[*] 아카이브에서 DB 파일 복원 중: {archive_path.name} -> data/")
            shutil.copyfile(archive_path, target_path)
        else:
            print(f"[ERROR] 복원 대상 DB 파일을 찾을 수 없습니다: {target_path}", file=sys.stderr)
            sys.exit(1)

    # 메타데이터 업데이트
    meta["active_version"] = target_version
    meta["active_db_filename"] = target_db_filename
    for item in meta.get("history", []):
        if item.get("version") == target_version:
            item["status"] = "active"
        elif item.get("status") == "active":
            item["status"] = "archived"

    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)

    print("=" * 65)
    print(f"[SUCCESS] 성공적으로 버전 {target_version} ({target_db_filename})으로 롤백되었습니다.")
    print("FastAPI 백엔드가 다음 요청부터 복원된 버전을 즉시 서빙합니다.")
    print("=" * 65)


def main():
    parser = argparse.ArgumentParser(description="분석 DB 롤백 오케스트레이터")
    parser.add_argument("--to", type=str, help="롤백할 목표 버전 (예: 202610)")
    parser.add_argument("--list", action="store_true", help="가용 버전 목록 출력")
    args = parser.parse_args()

    if args.list or not args.to:
        list_versions()
    else:
        rollback_to_version(args.to)


if __name__ == "__main__":
    main()
