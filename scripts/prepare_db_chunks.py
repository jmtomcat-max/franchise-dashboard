"""
prepare_db_chunks.py
대용량 SQLite DB(490MB)를 gzip 압축 후 60MB 청크로 분할하여 깃허브 용량 한도(100MB)를 준수합니다.
"""

import os
import gzip
import shutil
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
CHUNKS_DIR = DATA_DIR / "chunks"

SOURCE_DB = DATA_DIR / "franchise_analytics_v1.sqlite3"
CHUNK_SIZE = 60 * 1024 * 1024  # 60MB

def main():
    if not SOURCE_DB.exists():
        raise FileNotFoundError(f"원본 DB를 찾을 수 없습니다: {SOURCE_DB}")

    CHUNKS_DIR.mkdir(parents=True, exist_ok=True)
    temp_gz = DATA_DIR / "temp_analytics.gz"

    print(f"[*] 1단계: 원본 DB 압축 시작 ({SOURCE_DB.name}, {SOURCE_DB.stat().st_size / 1024 / 1024:.1f} MB)...")
    with open(SOURCE_DB, "rb") as f_in:
        with gzip.open(temp_gz, "wb", compresslevel=6) as f_out:
            shutil.copyfileobj(f_in, f_out)

    compressed_size = temp_gz.stat().st_size
    print(f"[+] 압축 완료: {compressed_size / 1024 / 1024:.1f} MB")

    print(f"[*] 2단계: 60MB 단위 분할 저장 시작 (저장 경로: {CHUNKS_DIR})...")
    part_num = 1
    with open(temp_gz, "rb") as f_gz:
        while True:
            chunk = f_gz.read(CHUNK_SIZE)
            if not chunk:
                break
            part_path = CHUNKS_DIR / f"franchise_analytics_v1.sqlite3.gz.part{part_num:02d}"
            with open(part_path, "wb") as f_part:
                f_part.write(chunk)
            print(f"    -> 생성됨: {part_path.name} ({len(chunk) / 1024 / 1024:.2f} MB)")
            part_num += 1

    temp_gz.unlink(missing_ok=True)
    print(f"[성공] 총 {part_num - 1}개 청크 분할 완료. 모든 파일이 깃허브 100MB 한도를 안전하게 충족합니다.")

if __name__ == "__main__":
    main()
