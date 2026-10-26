"""
Stage 4E: FastAPI 데이터베이스 연결 및 고속 캐싱 쿼리 실행 계층
프로젝트: D:/Franchise_Dashboard
위치: src/stage4e/api/database.py
"""

import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, List, Dict, Any, Optional, Tuple

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
ANALYTICS_DB_PATH = BASE_DIR / "data" / "franchise_analytics_v1.sqlite3"

_thread_local = threading.local()


def get_cached_connection() -> sqlite3.Connection:
    """스레드별 지속 연결 풀 및 mmap 고속 메모리 매핑을 반환합니다."""
    conn = getattr(_thread_local, "conn", None)
    if conn is None:
        uri = f"file:{ANALYTICS_DB_PATH.as_posix()}?mode=ro"
        conn = sqlite3.connect(uri, uri=True, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        # 고속 메모리 매핑 및 캐시 설정 (Windows SQLite mmap 충돌 방지, Linux 배포 환경 유지)
        import sys
        if sys.platform != "win32":
            conn.execute("PRAGMA mmap_size = 268435456;") # 256MB mmap
        conn.execute("PRAGMA cache_size = -64000;")   # 64MB cache
        _thread_local.conn = conn
    return conn


@contextmanager
def get_db_connection() -> Generator[sqlite3.Connection, None, None]:
    """분석 DB에 대한 안전한 읽기 전용 연결을 제공합니다."""
    yield get_cached_connection()


def query_one(sql: str, params: Tuple[Any, ...] = ()) -> Optional[Dict[str, Any]]:
    """단일 행을 딕셔너리로 조회합니다 (파라미터화된 쿼리 강제)."""
    conn = get_cached_connection()
    cur = conn.cursor()
    cur.execute(sql, params)
    row = cur.fetchone()
    return dict(row) if row else None


def query_all(sql: str, params: Tuple[Any, ...] = ()) -> List[Dict[str, Any]]:
    """모든 행을 딕셔너리 리스트로 조회합니다 (파라미터화된 쿼리 강제)."""
    conn = get_cached_connection()
    cur = conn.cursor()
    cur.execute(sql, params)
    rows = cur.fetchall()
    return [dict(r) for r in rows]


def validate_whitelist(value: str, allowed_values: List[str], field_name: str) -> str:
    """SQL 인젝션을 방지하기 위해 화이트리스트 목록에 있는지 엄격히 검증합니다."""
    if value not in allowed_values:
        raise ValueError(f"유효하지 않은 {field_name} 값: '{value}'. 허용 목록: {allowed_values}")
    return value
