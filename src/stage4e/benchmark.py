"""
Stage 4E: 실제 대규모 지역 API 검색 성능 및 응답시간 실측 벤치마크 (benchmark.py)
프로젝트: D:/Franchise_Dashboard
위치: src/stage4e/benchmark.py
"""

import sys
import time
import os
from pathlib import Path
from typing import Dict, Any, List

# Windows 콘솔 인코딩 보호
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

BASE_DIR = Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from fastapi.testclient import TestClient
from src.stage4e.api.main import app

def run_performance_benchmarks() -> Dict[str, Any]:
    """서울/경기 대규모 지역 및 핵심 엔드포인트의 실측 응답속도와 성능을 측정합니다."""
    client = TestClient(app)
    
    scenarios = [
        {
            "name": "강남역 테헤란로 고밀집 BBOX 점포 검색 (500건)",
            "url": "/api/v1/spatial/stores/bbox?min_lon=127.025&min_lat=37.495&max_lon=127.035&max_lat=37.505&limit=500",
            "sla_target_ms": 150.0
        },
        {
            "name": "광진구 건대입구 상권 BBOX 점포 검색 (100건, Reference UI)",
            "url": "/api/v1/spatial/stores/bbox?min_lon=127.060&min_lat=37.530&max_lon=127.080&max_lat=37.550&limit=100",
            "sla_target_ms": 50.0
        },
        {
            "name": "경기 수원 인계동 중심상권 BBOX 점포 검색 (500건)",
            "url": "/api/v1/spatial/stores/bbox?min_lon=127.020&min_lat=37.255&max_lon=127.040&max_lat=37.275&limit=500",
            "sla_target_ms": 150.0
        },
        {
            "name": "전국 외식업 총괄 통계 요약 (735,185건 대사)",
            "url": "/api/v1/analytics/summary",
            "sla_target_ms": 50.0
        },
        {
            "name": "전국 16개 시도 침투율 순위 조회",
            "url": "/api/v1/analytics/regions?region_type=SIDO&sort_by=franchise_penetration_rate&order=desc",
            "sla_target_ms": 50.0
        },
        {
            "name": "전국 256개 시군구 전수 랭킹 페이징 조회",
            "url": "/api/v1/analytics/regions?region_type=SIGUNGU&limit=300",
            "sla_target_ms": 60.0
        },
        {
            "name": "전국 8대 대분류 및 48대 중분류 통계 (모호 분류 분리)",
            "url": "/api/v1/analytics/categories?include_ambiguous=true",
            "sla_target_ms": 50.0
        },
        {
            "name": "브랜드 고속 검색 및 자동완성 (메가MGC커피)",
            "url": "/api/v1/analytics/brands/search?q=메가&limit=10",
            "sla_target_ms": 60.0
        },
        {
            "name": "브랜드 전국 시도별 분포 조회 (메가커피)",
            "url": "/api/v1/analytics/brands/BRD_CAF_0004/distribution?region_type=SIDO",
            "sla_target_ms": 60.0
        },
        {
            "name": "3D GIS 100m 격자 기둥 조회 (광진구 11215 Reference)",
            "url": "/api/v1/spatial/density/grid?sigungu_code=11215&limit=500",
            "sla_target_ms": 70.0
        },
        {
            "name": "3D 상권 핫스팟 및 드론 비행 카메라 경로 조회",
            "url": "/api/v1/spatial/hotspots",
            "sla_target_ms": 50.0
        }
    ]

    print("\n=======================================================")
    print("[*] Starting Phase 4 Stage 4E Real Performance Benchmarks")
    print("=======================================================\n")

    results = []

    for sc in scenarios:
        name = sc["name"]
        url = sc["url"]
        sla = sc["sla_target_ms"]

        # 엔드포인트 워밍업 1회 (JIT 및 OS 캐시 활성화)
        client.get(url)

        # 5회 반복 측정 후 평균치 산출
        latencies = []
        status_code = 200
        count_returned = 0

        for _ in range(5):
            t0 = time.perf_counter()
            res = client.get(url)
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            latencies.append(elapsed_ms)
            status_code = res.status_code
            if res.status_code == 200:
                data = res.json()
                if "features" in data:
                    count_returned = len(data["features"])
                elif "data" in data and isinstance(data["data"], list):
                    count_returned = len(data["data"])

        avg_ms = sum(latencies) / len(latencies)
        min_ms = min(latencies)
        max_ms = max(latencies)
        passed = (avg_ms <= sla) and (status_code == 200)

        result_item = {
            "scenario": name,
            "url": url,
            "status_code": status_code,
            "items_returned": count_returned,
            "sla_target_ms": sla,
            "avg_latency_ms": round(avg_ms, 2),
            "min_latency_ms": round(min_ms, 2),
            "max_latency_ms": round(max_ms, 2),
            "verdict": "PASS" if passed else "FAIL"
        }
        results.append(result_item)

        print(f"[{result_item['verdict']}] {name}")
        print(f"      Latency: avg={avg_ms:.2f}ms (min={min_ms:.2f}ms, max={max_ms:.2f}ms) | SLA: <={sla}ms | Count={count_returned}")

    print("\n=======================================================")
    print("[*] Benchmark Completed")
    print("=======================================================\n")

    return {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_scenarios": len(scenarios),
        "all_passed": all(r["verdict"] == "PASS" for r in results),
        "results": results
    }


if __name__ == "__main__":
    run_performance_benchmarks()
