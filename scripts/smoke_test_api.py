#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Franchise Dashboard - FastAPI 주요 엔드포인트 통합 스모크 테스트 (Smoke Test)
프로젝트: D:/Franchise_Dashboard
위치: scripts/smoke_test_api.py

핵심 비즈니스 및 3D GIS 공간 엔드포인트 12종의 응답 상태코드(200),
스키마 무결성, 필수 키 존재 여부 및 응답 지연시간(Latency)을 측정 검증합니다.

사용법:
    1. 인메모리 테스트 (서버 구동 불필요):
       py scripts/smoke_test_api.py
    2. 라이브 서버 테스트 (서버 실행 상태):
       py scripts/smoke_test_api.py --live
       py scripts/smoke_test_api.py --url http://127.0.0.1:8000
"""

import sys
import time
import argparse
from pathlib import Path
from typing import Dict, Any, List, Optional

# Windows 콘솔 UTF-8 출력 보장
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.stage4e.api.main import app

# 테스트 대상 핵심 엔드포인트 명세
SMOKE_ENDPOINTS = [
    {
        "name": "1. 헬스체크 및 기본 메타데이터",
        "path": "/",
        "expected_status": 200,
        "validate_fn": lambda d: d.get("status") == "healthy" and d.get("total_stores_universe") == 735185
    },
    {
        "name": "2. 전국 시장 종합 대시보드 개요",
        "path": "/api/v1/analytics/summary",
        "expected_status": 200,
        "validate_fn": lambda d: "data" in d and d["data"].get("total_stores") == 735185 and "meta" in d
    },
    {
        "name": "3. 16개 광역 시도 목록",
        "path": "/api/v1/analytics/regions?region_type=SIDO&limit=20",
        "expected_status": 200,
        "validate_fn": lambda d: "data" in d and len(d["data"]) == 16 and any(p["region_code"] == "11" for p in d["data"])
    },
    {
        "name": "4. 서울특별시(11) 지역 상세 통계",
        "path": "/api/v1/analytics/regions/11",
        "expected_status": 200,
        "validate_fn": lambda d: "region_stats" in d and d["region_stats"].get("region_code") == "11"
    },
    {
        "name": "5. 48개 외식 중분류 및 통계",
        "path": "/api/v1/analytics/categories",
        "expected_status": 200,
        "validate_fn": lambda d: "data" in d and len(d["data"]) == 48 and "meta" in d
    },
    {
        "name": "6. 브랜드 검색 및 자동완성",
        "path": "/api/v1/analytics/brands/search?limit=10",
        "expected_status": 200,
        "validate_fn": lambda d: "data" in d and len(d["data"]) == 10 and "brand_name_std" in d["data"][0]
    },
    {
        "name": "7. 강남구 코엑스 BBOX 점포 GeoJSON 스트리밍",
        "path": "/api/v1/spatial/stores/bbox?min_lon=127.055&min_lat=37.508&max_lon=127.062&max_lat=37.514",
        "expected_status": 200,
        "validate_fn": lambda d: d.get("type") == "FeatureCollection" and len(d.get("features", [])) > 0
    },
    {
        "name": "8. 광진구 100m 정밀 밀집도 격자 (MapLibre fill-extrusion 3D 기둥)",
        "path": "/api/v1/spatial/density/grid?sigungu_code=11215&limit=1500",
        "expected_status": 200,
        "validate_fn": lambda d: "data" in d and isinstance(d["data"], list) and len(d["data"]) > 0 and "grid_id" in d["data"][0]
    },
    {
        "name": "9. 상위 상권 핫스팟 클러스터 (Drone Flight Tour)",
        "path": "/api/v1/spatial/hotspots",
        "expected_status": 200,
        "validate_fn": lambda d: "data" in d and isinstance(d["data"], list) and len(d["data"]) > 0 and "hotspot_id" in d["data"][0]
    },
    {
        "name": "10. 공정위 거시통계 및 감사 상태 (2023~2026 4개년)",
        "path": "/api/v1/ftc/status",
        "expected_status": 200,
        "validate_fn": lambda d: d.get("status") == "SUCCESS" and "data" in d and all(y in d["data"].get("available_years", []) for y in ["2023", "2024", "2025", "2026"])
    },
    {
        "name": "11. 한식 업종 공정위 창업비용 벤치마크",
        "path": "/api/v1/ftc/benchmark/latest?category_major_id=CAT_MAJ_01",
        "expected_status": 200,
        "validate_fn": lambda d: d.get("status") == "SUCCESS" and "data" in d and "sales_benchmarks" in d["data"]
    },
    {
        "name": "12. 한식 업종 다년도 거시 추세 (2023~2026 Trends)",
        "path": "/api/v1/ftc/trends?category_major_id=CAT_MAJ_01",
        "expected_status": 200,
        "validate_fn": lambda d: d.get("status") == "SUCCESS" and "data" in d and "yearly_series" in d["data"] and len(d["data"]["yearly_series"]) == 4
    }
]


def run_smoke_tests(base_url: Optional[str] = None) -> int:
    import httpx
    from starlette.testclient import TestClient

    is_live = base_url is not None
    client = None
    if not is_live:
        print("[*] 모드: 인메모리 TestClient 실행 (외부 서버 구동 불필요)")
        client = TestClient(app)
    else:
        print(f"[*] 모드: 라이브 HTTP 요청 테스트 (대상 서버: {base_url})")

    print("=" * 75)
    print("  Franchise Dashboard - 주요 FastAPI 엔드포인트 스모크 테스트")
    print("=" * 75)

    passed = 0
    failed = 0
    results = []

    for item in SMOKE_ENDPOINTS:
        name = item["name"]
        path = item["path"]
        expected_status = item["expected_status"]
        validate_fn = item["validate_fn"]

        start_time = time.perf_counter()
        try:
            if is_live:
                resp = httpx.get(f"{base_url}{path}", timeout=10.0)
                status_code = resp.status_code
                data = resp.json()
            else:
                resp = client.get(path)
                status_code = resp.status_code
                data = resp.json()
            elapsed_ms = (time.perf_counter() - start_time) * 1000

            status_ok = (status_code == expected_status)
            content_ok = validate_fn(data) if status_ok else False

            if status_ok and content_ok:
                passed += 1
                result_str = "PASS"
            else:
                failed += 1
                result_str = "FAIL"

            results.append({
                "name": name,
                "path": path,
                "status_code": status_code,
                "elapsed_ms": elapsed_ms,
                "result": result_str,
                "error": None if (status_ok and content_ok) else f"Status: {status_code}, Valid: {content_ok}"
            })
            print(f"[{result_str}] {name:<35} | {status_code} | {elapsed_ms:6.1f}ms | {path}")

        except Exception as e:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            failed += 1
            results.append({
                "name": name,
                "path": path,
                "status_code": "ERR",
                "elapsed_ms": elapsed_ms,
                "result": "FAIL",
                "error": str(e)
            })
            print(f"[FAIL] {name:<35} |  ERR  | {elapsed_ms:6.1f}ms | 오류: {e}")

    print("\n" + "=" * 75)
    print(f"  스모크 테스트 결과 요약: 총 {len(SMOKE_ENDPOINTS)}개 중 성공 {passed}개, 실패 {failed}개")
    avg_latency = sum(r["elapsed_ms"] for r in results) / len(results)
    print(f"  평균 응답 지연시간(Latency): {avg_latency:.1f}ms")
    print("=" * 75)

    if failed > 0:
        print("[실패] 일부 엔드포인트에서 결함이 감지되었습니다:")
        for r in results:
            if r["result"] == "FAIL":
                print(f"  - {r['name']} ({r['path']}): {r['error']}")
        return 1, results

    print("[성공] 모든 핵심 API 엔드포인트가 정상 작동(HTTP 200 및 유효 데이터 반환)합니다.")
    return 0, results


def main():
    import json
    parser = argparse.ArgumentParser(description="Franchise Dashboard API Smoke Test")
    parser.add_argument("--live", action="store_true", help="http://127.0.0.1:8000 라이브 서버 테스트")
    parser.add_argument("--url", type=str, default=None, help="대상 기본 URL (예: http://localhost:8000)")
    parser.add_argument("--json", type=str, default=None, help="테스트 결과를 JSON 파일로 저장")
    args = parser.parse_args()

    target_url = None
    if args.url:
        target_url = args.url.rstrip("/")
    elif args.live:
        target_url = "http://127.0.0.1:8000"

    exit_code, results = run_smoke_tests(target_url)
    if args.json:
        out_path = Path(args.json)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump({
                "passed": exit_code == 0,
                "endpoints_tested": len(results),
                "endpoints_passed": sum(1 for r in results if r["result"] == "PASS"),
                "endpoints_failed": sum(1 for r in results if r["result"] == "FAIL"),
                "avg_latency_ms": sum(r["elapsed_ms"] for r in results) / len(results) if results else 0,
                "results": results
            }, f, ensure_ascii=False, indent=2)
        print(f"[*] 스모크 테스트 결과 JSON 저장: {out_path}")
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
