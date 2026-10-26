"""
restore_db.py
클라우드 배포(Render, Vercel, Docker 등) 또는 신규 환경에서
data/chunks/ 내의 분할 압축 파일들을 원본 SQLite DB로 자동 복원합니다.
"""

import sys
import gzip
import shutil
import sqlite3
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
CHUNKS_DIR = DATA_DIR / "chunks"
TARGET_DB = DATA_DIR / "franchise_analytics_v1.sqlite3"


def restore_analytics_db(force: bool = False) -> bool:
    if TARGET_DB.exists() and not force:
        file_size = TARGET_DB.stat().st_size
        if file_size > 50 * 1024 * 1024:  # 50MB 이상 정상 파일 존재 시 복원 생략
            print(f"[정보] 원본 DB가 이미 존재합니다 ({TARGET_DB.name}, {file_size / 1024 / 1024:.1f} MB). 복원을 생략합니다.")
            return True

    chunk_files = sorted(CHUNKS_DIR.glob("franchise_analytics_v1.sqlite3.gz.part*"))
    if not chunk_files:
        print(f"[경고] 복원할 청크 파일을 찾을 수 없습니다: {CHUNKS_DIR}")
        return False

    print(f"[*] 청크 결합 및 압축 해제 시작 (대상: {len(chunk_files)}개 청크)...")
    start_time = time.time()

    temp_gz = DATA_DIR / "temp_restore.gz"
    temp_target = DATA_DIR / "temp_restored_analytics.sqlite3"

    try:
        # 1. 청크 파일 결합
        with open(temp_gz, "wb") as f_out:
            for part in chunk_files:
                print(f"    - 결합 중: {part.name} ({part.stat().st_size / 1024 / 1024:.2f} MB)")
                with open(part, "rb") as f_in:
                    shutil.copyfileobj(f_in, f_out)

        # 2. gzip 압축 해제
        print(f"[*] gzip 압축 해제 중 -> {TARGET_DB.name}...")
        with gzip.open(temp_gz, "rb") as f_in:
            with open(temp_target, "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)

        # 3. SQLite 무결성 검증
        print("[*] SQLite 데이터베이스 무결성 검사 중...")
        conn = sqlite3.connect(temp_target)
        cursor = conn.cursor()
        cursor.execute("PRAGMA quick_check;")
        check_result = cursor.fetchone()[0]
        cursor.execute("SELECT count(*) FROM sqlite_master WHERE type='table';")
        table_count = cursor.fetchone()[0]
        conn.close()

        if check_result != "ok":
            raise ValueError(f"SQLite quick_check 실패: {check_result}")

        # 원자적 교체
        if TARGET_DB.exists():
            TARGET_DB.unlink()
        temp_target.rename(TARGET_DB)

        elapsed = time.time() - start_time
        print(f"[성공] DB 복원 완료! ({TARGET_DB.stat().st_size / 1024 / 1024:.1f} MB, {table_count}개 테이블, {elapsed:.2f}초 소요)")
        return True

    except Exception as e:
        print(f"[오류] DB 복원 중 오류 발생: {e}", file=sys.stderr)
        if temp_target.exists():
            temp_target.unlink()
        return False
    finally:
        if temp_gz.exists():
            temp_gz.unlink()


if __name__ == "__main__":
    force_run = "--force" in sys.argv
    success = restore_analytics_db(force=force_run)
    sys.exit(0 if success else 1)
