# Phase 4 Stage 4E: 품질 및 무결성 검증 보고서 (Quality Report)

- **작성 일시**: 2026-10-13
- **프로젝트 경로**: `D:\Franchise_Dashboard`
- **대상 데이터베이스**: `data/franchise_analytics_v1.sqlite3` (507 MB)
- **품질 판정**: **PASS (전체 15개 무결성 검증 100% 통과, 11개 벤치마크 SLA 충족, 15개 Pytest 시나리오 전수 통과)**

---

## 1. 15대 핵심 무결성 검증 결과 요약 (Validator Results)

`src/stage4e/validator.py`를 통해 분석 데이터베이스의 전수 무결성을 검증한 결과입니다 (검증 소요 시간: 1.88초).

| 검증 ID | 검증 항목 | 기대값 (Expected) | 실측값 (Actual) | 결과 |
| :--- | :--- | :--- | :--- | :---: |
| **CHK_01** | 전국 외식업 총 점포 수 일치 | 735,185 | 735,185 | **PASS** |
| **CHK_02** | 16개 시도 점포 수 합계 대사 | 735,185 (16개 시도) | 735,185 (16개 시도) | **PASS** |
| **CHK_03** | 256개 시군구 점포 수 합계 대사 | 735,185 (256개 시군구) | 735,185 (256개 시군구) | **PASS** |
| **CHK_04** | 점포 룩업 테이블 1:1 고유성 무결성 | 735,185 (중복 0건) | Total: 735,185 / Distinct: 735,185 | **PASS** |
| **CHK_05** | 브랜드 연결 점포 + 독립 점포 합계 | 168,295 + 566,890 = 735,185 | 168,295 + 566,890 = 735,185 | **PASS** |
| **CHK_06** | 8대 확정 외식업 대분류 체계 일치 | 8개 대분류 | 8개 대분류 | **PASS** |
| **CHK_07** | 48개 확정 외식업 중분류 점포 수 합계 | 48개 중분류, 735,185 | 48개 중분류, 735,185 | **PASS** |
| **CHK_08** | 모호 분류(104,060건) 격리 필터 대사 | 확정 631,125 + 모호 104,060 | 확정 631,125 + 모호 104,060 | **PASS** |
| **CHK_09** | 복수 브랜드 샵인샵 점포 수 대사 | 23건 (`is_multi_brand_store = 1`) | 23건 | **PASS** |
| **CHK_10** | 3D GIS 상권 핫스팟 및 드론 투어 파라미터 | 10곳 (광진구 건대입구 등) | 10곳 (광진구 pitch 60.0° 일치) | **PASS** |
| **CHK_11** | 100m 정밀 격자 기둥(ColumnLayer) 밀집도 | 76,745셀, 587,500개 점포 | 76,745셀, 587,500개 점포 | **PASS** |
| **CHK_12** | 비즈니스 메트릭 공식 정의 사전 | $\ge 10$종 | 10종 완비 | **PASS** |
| **CHK_13** | 선행 원본 데이터베이스 3종 불변성 보존 | V2: 735,185 / BM: 5,063 / CM: 735,185 | V2: 735,185 / BM: 5,063 / CM: 735,185 | **PASS** |
| **CHK_14** | 4개 비즈니스 축 독립성 및 상태 격리 | 공식성 4 / 매칭 5 / 운영 3 / 업종 3 | 공식성 4 / 매칭 5 / 운영 3 / 업종 3 | **PASS** |
| **CHK_15** | 지역별 브랜드 랭킹 테이블 탑재 | $> 90,000$건 | 94,060건 (Top 20/10) | **PASS** |

---

## 2. API 실측 성능 벤치마크 결과 (Benchmark Results)

`src/stage4e/benchmark.py`를 통해 실측한 FastAPI 엔드포인트 응답 속도 및 SLA 달성률입니다.

| 시나리오 | 엔드포인트 | 반환 건수 | SLA 목표 | 실측 평균 레이턴시 | 실측 최소 | 실측 최대 | 판정 |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **강남역 테헤란로 고밀집 BBOX** | `/api/v1/spatial/stores/bbox` | 500건 | $\le 150\text{ms}$ | **61.43ms** | 47.30ms | 69.50ms | **PASS** |
| **광진구 건대입구 상권 BBOX (Ref UI)** | `/api/v1/spatial/stores/bbox` | 100건 | $\le 50\text{ms}$ | **30.79ms** | 25.40ms | 37.15ms | **PASS** |
| **경기 수원 인계동 중심상권 BBOX** | `/api/v1/spatial/stores/bbox` | 500건 | $\le 150\text{ms}$ | **66.56ms** | 50.62ms | 77.96ms | **PASS** |
| **전국 외식업 총괄 통계 요약** | `/api/v1/analytics/summary` | 1건 | $\le 50\text{ms}$ | **22.46ms** | 18.81ms | 34.74ms | **PASS** |
| **전국 16개 시도 침투율 순위** | `/api/v1/analytics/regions?region_type=SIDO` | 16건 | $\le 50\text{ms}$ | **22.39ms** | 17.84ms | 28.07ms | **PASS** |
| **전국 256개 시군구 전수 랭킹 페이징** | `/api/v1/analytics/regions?region_type=SIGUNGU` | 256건 | $\le 60\text{ms}$ | **31.09ms** | 27.11ms | 40.77ms | **PASS** |
| **8대 대분류 및 48대 중분류 통계** | `/api/v1/analytics/categories` | 48건 | $\le 50\text{ms}$ | **20.80ms** | 20.18ms | 21.20ms | **PASS** |
| **브랜드 고속 검색 및 자동완성** | `/api/v1/analytics/brands/search?q=메가` | 4건 | $\le 60\text{ms}$ | **31.87ms** | 30.25ms | 32.78ms | **PASS** |
| **브랜드 전국 시도별 분포 조회** | `/api/v1/analytics/brands/.../distribution` | 16건 | $\le 60\text{ms}$ | **23.68ms** | 22.30ms | 25.15ms | **PASS** |
| **3D GIS 100m 격자 기둥 (광진구 11215)** | `/api/v1/spatial/density/grid` | 466셀 | $\le 70\text{ms}$ | **31.85ms** | 25.19ms | 55.83ms | **PASS** |
| **3D 상권 핫스팟 및 드론 카메라 투어** | `/api/v1/spatial/hotspots` | 10곳 | $\le 50\text{ms}$ | **12.32ms** | 11.38ms | 13.78ms | **PASS** |

> **성능 요약**: 11개 전 시나리오에서 목표 SLA를 $100\%$ 충족하였으며, 고밀집 뷰포트(500건) GeoJSON 스트리밍에서도 60ms 대의 고속 응답을 유지했습니다.

---

## 3. Pytest 자동화 통합 테스트 스위트 (15/15 Pass)

`tests/test_phase4_stage4e.py`를 실행하여 15개 시나리오를 전수 검증했습니다.

```
tests/test_phase4_stage4e.py::test_01_regional_store_counts_reconciliation PASSED [  6%]
tests/test_phase4_stage4e.py::test_02_zero_double_counting_in_overall_metrics PASSED [ 13%]
tests/test_phase4_stage4e.py::test_03_category_hierarchy_reconciliation PASSED [ 20%]
tests/test_phase4_stage4e.py::test_04_franchise_brand_vs_franchisee_decoupling PASSED [ 26%]
tests/test_phase4_stage4e.py::test_05_unverified_brand_candidates_isolation PASSED [ 33%]
tests/test_phase4_stage4e.py::test_06_unmatched_stores_neutral_presentation PASSED [ 40%]
tests/test_phase4_stage4e.py::test_07_ambiguous_category_filter PASSED   [ 46%]
tests/test_phase4_stage4e.py::test_08_invalid_inputs_and_injection_prevention PASSED [ 53%]
tests/test_phase4_stage4e.py::test_09_multi_brand_shop_in_shop_stores PASSED [ 60%]
tests/test_phase4_stage4e.py::test_10_cross_filters PASSED               [ 66%]
tests/test_phase4_stage4e.py::test_11_large_bbox_search_limits PASSED    [ 73%]
tests/test_phase4_stage4e.py::test_12_pagination PASSED                  [ 80%]
tests/test_phase4_stage4e.py::test_13_response_metadata_and_axes PASSED  [ 86%]
tests/test_phase4_stage4e.py::test_14_3d_hotspots_and_grid_pillars PASSED [ 93%]
tests/test_phase4_stage4e.py::test_15_source_databases_immutability PASSED [100%]
======================== 15 passed in 7.71s ========================
```

---

## 4. 데이터 정합성 핵심 지표 대사표

| 비즈니스 분석 차원 | 점포 수 / 건수 | 비고 |
| :--- | :---: | :--- |
| **전국 외식업 총 고유 점포** | **735,185** | 단일 진실 모수 ($100.00\%$) |
| **독립 점포 (단독 매장)** | **566,890** | $77.11\%$, 공식성 `UNMATCHED` |
| **브랜드 연결 점포** | **168,295** | $22.89\%$, 프랜차이즈/체인 후보군 |
| ├ 공인 가맹사업 브랜드 소속 | 48,002 | 공정위 72개 가맹사업 브랜드 |
| │ ├ 확인된 가맹점 | 45,202 | 순수 가맹 계약 매장 |
| │ └ 확인된 직영점 | 2,800 | 가맹사업 본사 직영 매장 |
| └ 미검증 후보 브랜드 소속 | 117,493 | 동일 상호 10개 이상 점포군 |
| **복수 브랜드 샵인샵 매장** | **23** | 이중 계산 차단 (`is_multi_brand_store = 1`) |
| **모호 업종 점포 (1:N 분기)** | **104,060** | $14.15\%$, 격리 필터 지원 |
| **확정 업종 점포 (1:1 매핑)** | **631,125** | $85.85\%$, 순수 업종 분석 대상 |
| **3D 밀집도 100m 격자 기둥** | **76,745** | deck.gl `ColumnLayer` 연동 |
| **3D 상권 핫스팟 및 투어** | **10** | 광진구 건대입구 등 드론 카메라 투어 |
| **지역별 브랜드 랭킹 데이터** | **94,060** | Top 20 전체 및 Top 10 업종별 순위 |
