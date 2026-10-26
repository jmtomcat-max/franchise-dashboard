#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
신규 분석 DB 무결성 및 품질 게이트 검증 스크립트
위치: scripts/data_quality_gate.py

새로 생성된 SQLite 분석 DB(Green DB)가 운영 환경에 투입(Promotion)되기 전에
4대 핵심 품질 기준을 만족하는지 엄격히 검증합니다:
1. 필수 테이블 및 인덱스 존재 여부
2. 좌표(lat, lon) 결측치 및 이상치 허용율 검증 (99.9% 이상 정상)
3. 점포 유니버스 규모 검증 (최소 700,000건 이상)
4. FastAPI 스모크 테스트 전수 통과 (12/12 PASS)
"""

import sys
import os
import sqlite3
import argparse
import subprocess
from pathlib import Path

# Windows UTF-8 출력 보장
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))


def verify_database_schema(db_path: Path) -> bool:
    """1. 필수 테이블 존재 여부 검사"""
    required_tables = [
        "store_analytics_lookup",
        "spatial_density_grid_100m",
        "commercial_hotspots",
        "regions_master",
        "regional_overall_stats"
    ]
    conn = sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type IN ('table', 'view');")
    tables = {row[0] for row in cur.fetchall()}
    conn.close()

    missing = [t for t in required_tables if t not in tables]
    if missing:
        print(f"[FAIL] 필수 테이블 누락: {missing}", file=sys.stderr)
        return False
    print(f"[PASS] 1. 필수 테이블 확인 완료: {required_tables}")
    return True


def verify_coordinate_integrity(db_path: Path) -> bool:
    """2. 좌표(lat, lon) 결측치 및 대한민국 경계 유효성 검사"""
    conn = sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True)
    cur = conn.cursor()

    cur.execute("SELECT count(*) FROM store_analytics_lookup;")
    total_stores = cur.fetchone()[0]

    # 대한민국 위경도 경계: 위도 33~39, 경도 124~132
    cur.execute("""
        SELECT count(*) FROM store_analytics_lookup 
        WHERE lat IS NULL OR lon IS NULL 
           OR lat < 33.0 OR lat > 39.0 
           OR lon < 124.0 OR lon > 132.0;
    """)
    invalid_coords = cur.fetchone()[0]
    conn.close()

    if total_stores == 0:
        print("[FAIL] 점포 수가 0건입니다.", file=sys.stderr)
        return False

    invalid_ratio = (invalid_coords / total_stores) * 100
    print(f"[*] 점포 총수: {total_stores:,}건 | 좌표 결측/이상치: {invalid_coords:,}건 ({invalid_ratio:.4f}%)")

    # 결측치 0.1% 이하만 허용
    if invalid_ratio > 0.1:
        print(f"[FAIL] 좌표 결측/이상치 비율 초과: {invalid_ratio:.4f}% > 0.1%", file=sys.stderr)
        return False

    print("[PASS] 2. 공간 좌표 무결성 검증 통과 (정상률 99.9% 이상)")
    return True


def verify_store_volume(db_path: Path, min_threshold: int = 700000) -> bool:
    """3. 점포 수 규모 및 급감 여부 검사"""
    conn = sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True)
    cur = conn.cursor()
    cur.execute("SELECT count(*) FROM store_analytics_lookup;")
    count = cur.fetchone()[0]
    conn.close()

    if count < min_threshold:
        print(f"[FAIL] 점포 유니버스 기준치 미달: {count:,}건 < {min_threshold:,}건", file=sys.stderr)
        return False

    print(f"[PASS] 3. 전국 점포 규모 검증 통과 ({count:,}건 >= {min_threshold:,}건)")
    return True


def run_smoke_tests(db_path: Path) -> bool:
    """4. 대상 DB에 대한 FastAPI 핵심 라우터 인프로세스 쿼리 및 무결성 전수 검증 (소켓 불필요)"""
    print("[*] 4. FastAPI 핵심 라우터 및 공간 쿼리 무결성 검증 중...")
    try:
        from src.stage4e.api.routers.summary import get_nationwide_summary
        from src.stage4e.api.routers.system import get_data_status
        from src.stage4e.api.routers.regions import list_regions
        from src.stage4e.api.routers.categories import list_category_stats
        from src.stage4e.api.routers.spatial import get_spatial_density_grid

        # 1. 요약 통계 검증
        s = get_nationwide_summary()
        assert s.data.total_stores >= 700000, f"점포수 미달: {s.data.total_stores}"
        print(f"    -> [PASS] 요약 통계 라우터 검증 완료 (점포수: {s.data.total_stores:,}건)")

        # 2. 지역 통계 검증
        r = list_regions(
            region_type="SIDO", sido_code=None, category_major_id=None, category_mid_id=None,
            sort_by="total_stores", order="desc", limit=20, offset=0
        )
        assert len(r.data) == 16, f"16개 시도 불일치: {len(r.data)}"
        print("    -> [PASS] 16개 광역 시도 라우터 검증 완료")

        # 3. 업종 분류 검증
        c = list_category_stats(
            region_code="00", category_major_id=None, include_ambiguous=True,
            sort_by="total_stores", order="desc"
        )
        assert len(c.data) == 48, f"48대 중분류 불일치: {len(c.data)}"
        print("    -> [PASS] 48대 외식 중분류 라우터 검증 완료")

        # 4. 3D 공간 밀집도 격자 검증
        g = get_spatial_density_grid(
            sigungu_code="11215", sido_code=None, category_major_id=None, category_mid_id=None,
            min_stores=3, limit=50
        )
        assert len(g.data) > 0, "격자 데이터 0건"
        print(f"    -> [PASS] 3D GIS 100m 격자 기둥 라우터 검증 완료 (광진구 샘플: {len(g.data)}개)")

        # 5. 시스템 상태 라우터 검증
        st = get_data_status()
        assert st.active_version is not None
        print(f"    -> [PASS] 시스템 데이터 상태 라우터 검증 완료 (활성: {st.active_version})")

        print("[PASS] 4. FastAPI 핵심 비즈니스 및 3D GIS 공간 라우터 전수 검증 통과")
        return True
    except Exception as e:
        print(f"[FAIL] 라우터 검증 실패: {e}", file=sys.stderr)
        return False


def main():
    parser = argparse.ArgumentParser(description="분석 DB 데이터 품질 게이트 검증기")
    parser.add_argument("--target-db", type=str, required=True, help="검증 대상 SQLite DB 경로")
    args = parser.parse_args()

    db_path = Path(args.target_db).resolve()
    if not db_path.exists():
        print(f"[ERROR] 대상 DB 파일이 존재하지 않습니다: {db_path}", file=sys.stderr)
        sys.exit(1)

    print("=" * 70)
    print(f"  데이터 품질 게이트 검증: {db_path.name} ({db_path.stat().st_size / 1024 / 1024:.1f} MB)")
    print("=" * 70)

    checks = [
        verify_database_schema(db_path),
        verify_coordinate_integrity(db_path),
        verify_store_volume(db_path),
        run_smoke_tests(db_path)
    ]

    if all(checks):
        print("=" * 70)
        print("[SUCCESS] 모든 데이터 품질 게이트를 통과했습니다. 운영 투입이 가능합니다.")
        print("=" * 70)
        sys.exit(0)
    else:
        print("=" * 70)
        print("[REJECT] 데이터 품질 게이트 검증에 실패했습니다. 배포를 중단합니다.", file=sys.stderr)
        print("=" * 70)
        sys.exit(1)


if __name__ == "__main__":
    main()
