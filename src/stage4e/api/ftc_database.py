"""
Phase 5B: 공정거래위원회 거시통계 데이터베이스 전용 읽기 전용 연결 계층
프로젝트: D:/Franchise_Dashboard
위치: src/stage4e/api/ftc_database.py

역할:
- data/ftc_macro_statistics_v1.sqlite3 에 대한 안전한 읽기 전용(mode=ro) 스레드 풀링 연결 제공
- 기존 소상공인 지도 분석 DB(data/franchise_analytics_v1.sqlite3)와 완전 분리
"""

import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, List, Dict, Any, Optional, Tuple

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
FTC_MACRO_DB_PATH = BASE_DIR / "data" / "ftc_macro_statistics_v1.sqlite3"

_ftc_thread_local = threading.local()


def get_ftc_cached_connection() -> sqlite3.Connection:
    """스레드별 지속 연결 풀 및 읽기 전용 메모리 매핑을 반환합니다."""
    conn = getattr(_ftc_thread_local, "conn", None)
    if conn is None:
        if not FTC_MACRO_DB_PATH.exists():
            raise FileNotFoundError(f"공정위 거시통계 데이터베이스를 찾을 수 없습니다: {FTC_MACRO_DB_PATH}")
            
        uri = f"file:{FTC_MACRO_DB_PATH.as_posix()}?mode=ro"
        conn = sqlite3.connect(uri, uri=True, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        
        # 성능 최적화 PRAGMA (읽기 전용 쿼리 최적화)
        conn.execute("PRAGMA query_only = ON;")
        conn.execute("PRAGMA mmap_size = 134217728;")  # 128MB mmap
        conn.execute("PRAGMA cache_size = -32000;")    # 32MB cache
        _ftc_thread_local.conn = conn
    return conn


@contextmanager
def get_ftc_db_connection() -> Generator[sqlite3.Connection, None, None]:
    """공정위 거시통계 DB에 대한 안전한 읽기 전용 컨텍스트를 제공합니다."""
    yield get_ftc_cached_connection()


def ftc_query_one(sql: str, params: Tuple[Any, ...] = ()) -> Optional[Dict[str, Any]]:
    """단일 행을 딕셔너리로 조회합니다 (파라미터화된 쿼리 강제)."""
    conn = get_ftc_cached_connection()
    cur = conn.cursor()
    cur.execute(sql, params)
    row = cur.fetchone()
    return dict(row) if row else None


def ftc_query_all(sql: str, params: Tuple[Any, ...] = ()) -> List[Dict[str, Any]]:
    """모든 행을 딕셔너리 리스트로 조회합니다 (파라미터화된 쿼리 강제)."""
    conn = get_ftc_cached_connection()
    cur = conn.cursor()
    cur.execute(sql, params)
    rows = cur.fetchall()
    return [dict(r) for r in rows]
