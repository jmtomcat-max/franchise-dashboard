# Phase 7 Step 7-1 실행 보고서 — 실행환경 표준화 및 통합 스모크 테스트 (Iteration 3 완료)

- **실행일**: 2026-10-20
- **상태**: 구현, Codex 지적 사항(P1~P4 전수 조치, 동적 테스트 집계, 산출물 실측 크기 동기화) 및 전체 종합 검증(사전점검, 12개 API 스모크, 82개 단위테스트 격리/동적집계, Vite 빌드, 브라우저 레이어 visibility 실측, 운영 DB 100% 불변) 전수 통과 완료
- **선행 단계**: Phase 6 Step 6-3 건물 데이터 평가 완료 (HOLD / 현 MVP 유지 확정)
- **목표**: 현재 완성된 Franchise Dashboard MVP를 새 개발환경에서도 동일하게 재현하고 검증할 수 있도록 실행환경을 표준화 (신규 비즈니스/UI 기능 추가 배제)

---

## 1. 개요 및 배경

Franchise Dashboard는 전국 735,185개 고유 외식업 점포 데이터, 공간 집계(100m 3D 헥사곤/격자 `fill-extrusion`, BBOX 기반 개별 점포), 공정거래위원회 4개년(2023~2026) 거시 통계 및 3D GIS 인터랙티브 시각화를 갖춘 프로덕션 수준의 MVP입니다.
본 단계(Phase 7 Step 7-1)에서는 개발자 또는 신규 배포 환경에서 시스템을 즉시 재현·검증할 수 있도록:
1. Python 3.12.7 기반 루트 가상환경(`.venv`) 및 최소 의존성(`requirements.txt`) 표준화
2. 원클릭 사전점검 및 안전 실행 스크립트 구축 (`scripts/preflight_check.py`, `scripts/run_backend.*`, `scripts/run_frontend.*`)
3. 핵심 12대 FastAPI 엔드포인트 자동 스모크 테스트 (`scripts/smoke_test_api.py`, `scripts/run_smoke.bat`)
4. 82개 단위/통합 테스트 스위트의 진정한 테스트 격리 및 실제 통과 건수 동적 집계 러너 구축 (`scripts/run_tests.py`, `scripts/run_tests.bat`)
5. Vite 프로덕션 빌드(`npm run build`) 무결성 및 실제 바이트 크기 확인
6. Phase 6-2 브라우저 실제 인터랙션(격자·점포·핫스팟 토글) 및 MapLibre 레이어 visibility/복원 CDP 자동 검증
7. `data/brand_master_v1.sqlite3` 롤백 및 임시 DB 복사본 기반 100% 읽기 전용 불변 보장
8. 포괄적인 루트 `README.md` 및 정량 검증 JSON(`reports/phase7_step1_validation.json`) 작성을 완료했습니다.

---

## 2. Codex 검토 피드백 및 시정 조치 내역

Codex 검토(Iteration 1~3)에서 제기된 지적 사항에 대해 다음과 같이 완벽한 시정 조치를 완료했습니다:

| ID | 우선순위 | 지적 사항 | 시정 조치 및 결과 |
|---|:---:|---|---|
| **P1** | High | `scripts/run_tests.py`가 테스트 실행 중 운영 DB에 쓰고 `finally`에서 `shutil.copy2`로 덮어쓰는 구조는 강제 종료 시 오염 및 복원 중단 위험이 존재함. 테스트용 임시 DB에 `db_path`를 전달하도록 격리하고 운영 DB 복원을 제거해야 함 | 1) `tests/test_phase4_stage4c.py`의 `test_10_review_system_persistence`를 수정하여, `tempfile.NamedTemporaryFile` 기반의 임시 DB 복사본을 생성하고 `record_brand_review(..., db_path=tmp_db_path)`로 전달하도록 격리.<br>2) 테스트 완료 후 임시 DB 파일을 즉시 삭제하고, 운영 DB `data/brand_master_v1.sqlite3`에는 단 1건의 쓰기도 발생하지 않도록 원천 차단.<br>3) `scripts/run_tests.py`에서 운영 DB의 백업 및 복원(`shutil.copy2`) 코드를 전면 제거.<br>4) 82개 전체 테스트 재실행 후 운영 DB 상태 실측: 리뷰 수 정확히 2건, 브랜드 5,063건, 링크 735,208건, `BRD_KOR_0001`의 `updated_at`(`2026-10-14 14:48:01`), 무결성(`ok`)으로 100% 불변 입증 완료. |
| **P2** | Medium | `run_tests.py`에서 실제 pytest 결과 대신 고정 expected_count를 합산하여 모의 실행 시 건수 미달에도 82개 통과로 오표시될 수 있음 | 1) `parse_pytest_summary()` 정규식 파서를 구현하여 pytest 출력에서 실제 `passed`, `failed`, `skipped`, `errors` 건수를 정밀 추출.<br>2) 실제 통과 건수가 기대 건수 미달(`passed < expected`)이거나 실패/에러 발생 시 즉시 실패(exit code 1) 처리하도록 엄격 합격 기준 적용.<br>3) 모의 테스트(4개만 통과 시 exit 1 반환) 및 실제 82개 전수 통과(82/82 통과 시 exit 0 반환) 모두 실측 검증 완료. |
| **P2** | Medium | `validation.json`의 산출물 크기(JS, 브랜드 DB 등)가 실제 파일 시스템 크기와 불일치함 | `pathlib.Path.stat().st_size`를 통해 모든 산출물 크기를 전수 실측하여 1바이트 오차도 없이 동기화 완료:<br>- `brand_master_v1.sqlite3`: 200,921,088 bytes (191.6 MB)<br>- `franchise_analytics_v1.sqlite3`: 514,043,904 bytes (490.2 MB)<br>- `ftc_macro_statistics_v1.sqlite3`: 32,325,632 bytes (30.8 MB)<br>- `index-Cv1fum3t.js`: 1,046,827 bytes (gzip: 290,625 bytes)<br>- `index-BpXN-xr5.css`: 130,111 bytes (gzip: 20,356 bytes)<br>- `index.html`: 668 bytes (gzip: 466 bytes) |
| **P2** | Medium | `preflight_check.py`에서 `frontend/src/services/api.js:6`이 실제로 사용하는 `VITE_API_URL` 대신 `VITE_API_BASE_URL`만 있어도 통과하는 문제 및 DB URI 연결 안정성 | 1) `scripts/preflight_check.py`에서 `frontend/.env` 내 실제 사용 변수인 `VITE_API_URL`을 엄격히 검사하고, `urllib.parse`를 통해 유효한 HTTP/HTTPS URL 스킴 및 호스트/포트가 존재하는지 유효성 검증 로직 추가.<br>2) Windows 환경에서 RFC 8089 규격에 부합하도록 `db_path.resolve().as_uri() + "?mode=ro"` (`file:///D:/...`) 형식으로 안전하게 연결하여 DB 열기 실패 오류를 원천 방지. (사전점검 100% PASS 확인) |
| **P2** | Medium | `test_phase6_step2_browser.mjs`의 `storePass` 판정이 수집한 `layerVisibility`를 합격 조건에 포함하지 않음 | 1) `storePass` 판정 조건에 `storeOffState.layerVisibility === 'none'` 및 `storeRestoredState.layerVisibility === 'visible'`을 엄격히 추가.<br>2) `evaluation.details`에 `storeOffVerified` 및 `storeRestoredVerified` 항목을 포함하여 실제 MapLibre 점포 원형 레이어(`store-points`)의 은닉 및 복원이 완벽하게 실측 검증됨을 확인. |
| **P2** | Medium | `run_backend.bat` 및 `run_backend.ps1`이 프로젝트 루트 디렉터리로 이동하지 않고 uvicorn을 실행하여 다른 작업 디렉터리에서 호출 시 모듈 탐색 실패 위험 존재 | 1) `scripts/run_backend.bat`: `cd /d "%ROOT_DIR%"` 및 uvicorn 실행 시 `--app-dir "%ROOT_DIR%"` 명시.<br>2) `scripts/run_backend.ps1`: `Set-Location -LiteralPath $rootDir` 및 `--app-dir $rootDir` 명시하여 어느 경로에서 호출하든 항상 안정적으로 실행되도록 조치 완료. |

---

## 3. 세부 구현 및 표준화 내역

### 3.1 Python 의존성 표준화 (`requirements.txt`)
`src/` 및 `tests/` 전역의 실제 `import` 문을 전수 스캔하여 최소 필수 의존성만을 명시했습니다.
- `fastapi>=0.100.0`: 고성능 비동기 REST API 프레임워크
- `uvicorn[standard]>=0.20.0`: ASGI 고성능 서버 런타임
- `pydantic>=2.0.0`: 데이터 검증 및 API 직렬화
- `pytest>=7.0.0`: 단위/통합 테스트 프레임워크
- `httpx>=0.24.0`: FastAPI TestClient 및 비동기 HTTP 요청

### 3.2 사전점검 도구 (`scripts/preflight_check.py`, `scripts/check_env.*`)
새 환경에서 시스템 기동 전 필수 요건을 5단계로 엄격하게 검증하며, 결함 시 exit code 1로 비정상 종료합니다.
- **Python 런타임**: Python 3.11 이상 여부 및 `.venv` 활성화 검사 (표준 환경: `.venv` Python 3.12.7 확인)
- **필수 패키지**: `fastapi`, `uvicorn`, `pydantic`, `httpx`, `pytest` 임포트 검증
- **SQLite DB 및 무결성/테이블 전수 검증**:
  - `data/franchise_analytics_v1.sqlite3` (514,043,904 bytes, 490.2MB): 7개 테이블 검증 및 `PRAGMA quick_check;` (`ok`)
  - `data/ftc_macro_statistics_v1.sqlite3` (32,325,632 bytes, 30.8MB): 3개 테이블, 2023~2026 4개년 연도 검증 및 `PRAGMA integrity_check;` (`ok`)
  - `data/brand_master_v1.sqlite3` (200,921,088 bytes, 191.6MB): 5개 핵심 테이블, 5,063개 브랜드, 735,208개 링크 전수 보존 검증 및 `PRAGMA integrity_check;` (`ok`)
- **프론트엔드 환경**: `frontend/.env`의 `VITE_API_URL` 필수 환경변수 유효성, Node.js 런타임(`v23.4.0`), `frontend/node_modules` 존재 검증
- **보호 자산 SHA-256 무결성**: `collector.py`, `gangnam_food_stores.sqlite3`, `run_gangnam.bat` 해시 대조

### 3.3 서비스 기동 스크립트 (`scripts/run_backend.*`, `scripts/run_frontend.*`)
- `run_backend.bat` / `.ps1`: 작업 디렉터리를 프로젝트 루트로 고정하고 `--app-dir`을 지정하여 사전점검(`preflight_check.py`) 후 `.venv` 기반 FastAPI 백엔드(포트 8000)를 안정적으로 기동
- `run_frontend.bat` / `.ps1`: `node_modules` 및 `.env`를 점검하고 필요 시 `npm install` 안내 후 Vite 개발서버(포트 5173)를 기동

### 3.4 핵심 API 12대 스모크 테스트 (`scripts/smoke_test_api.py`, `scripts/run_smoke.bat`)
FastAPI TestClient 기반으로 인메모리 직접 호출 또는 기동 중인 서버 라이브 테스트를 지원합니다.
1. `GET /` (헬스체크 및 기본 메타데이터)
2. `GET /api/v1/analytics/summary` (전국 점포 603,059개, 8개 대분류 요약)
3. `GET /api/v1/analytics/regions` (전국 16개 시도 공간 목록)
4. `GET /api/v1/analytics/regions/11` (서울시 세부 시군구 데이터)
5. `GET /api/v1/analytics/categories` (48개 공식 중분류 계층 구조)
6. `GET /api/v1/analytics/brands/search` (브랜드 검색 및 정규화 상호)
7. `GET /api/v1/spatial/stores/bbox` (코엑스 일대 BBOX 점포 공간 필터링)
8. `GET /api/v1/spatial/density/grid` (광진구 100m 육각 기둥/격자 MapLibre `fill-extrusion`)
9. `GET /api/v1/spatial/hotspots` (상위 상권 핫스팟 클러스터 Drone Flight Tour)
10. `GET /api/v1/ftc/status` (공정위 4개년 2023~2026 매크로 데이터 상태)
11. `GET /api/v1/ftc/benchmark/latest` (공정위 최신 창업비용 벤치마크 지표)
12. `GET /api/v1/ftc/trends` (한식 업종 다년도 트렌드 2023~2026)

### 3.5 82개 단위/통합 테스트 격리 및 동적 집계 러너 (`scripts/run_tests.py`, `scripts/run_tests.bat`)
- `tests/test_phase4_stage4c.py`의 `test_10`이 `tempfile` 임시 DB에 `db_path`를 전달하여 자체 격리하므로, `run_tests.py`는 운영 DB에 대한 어떠한 파일 복사/복원 작업 없이도 안전하고 완전한 읽기 전용 상태를 유지합니다.
- `parse_pytest_summary()` 함수를 통해 pytest 출력 문자열에서 실제 `passed` 건수를 정규식으로 동적 추출하고, 건수 미달 시 실패(exit code 1)를 강제합니다.
- 실제 7개 테스트 파일명 기준 4개 모듈 그룹으로 안전하게 분할 실행합니다:
  - 그룹 1: `test_phase4_stage4a.py`, `test_phase4_stage4b.py`, `test_phase4_stage4c.py` (실제 통과: 40개)
  - 그룹 2: `test_phase4_stage4d.py` (실제 통과: 11개)
  - 그룹 3: `test_phase4_stage4e.py` (실제 통과: 15개)
  - 그룹 4: `test_phase5b_step1.py`, `test_phase5b_step2_supplement.py` (실제 통과: 16개)

### 3.6 Phase 6-2 브라우저 실제 인터랙션 및 MapLibre 레이어 실측 검증 (`scratch/test_phase6_step2_browser.mjs`)
Chrome DevTools Protocol(CDP)을 통해 실제 브라우저 환경에서:
1. 핫스팟 카드 클릭을 통해 광진구 상권으로 진입하여 시군구 격자 데이터(`hasGridData: true`)를 활성화
2. `SlimMapRail`의 3대 레이어 토글(격자, 점포, 핫스팟)을 순차 클릭
3. 버튼 속성(`aria-pressed`)뿐만 아니라 MapLibre 실제 레이어(`density-grid-3d-columns`, `density-grid-overview-points`, `store-points`)의 `visibility` 속성이 `none`으로 전환되고, 재클릭 시 `visible`로 완벽히 복원됨을 실측 판정에 포함
4. HUD 상태 텍스트("개별 점포 레이어 숨김") 및 핫스팟 패널 표시 상태를 검증하고 증빙 스크린샷 4종을 확보했습니다.

---

## 4. 종합 검증 결과

| 검증 항목 | 대상 / 명령 | 결과 | 세부 내용 |
|---|---|:---:|---|
| **사전점검** | `.venv/Scripts/python.exe scripts/preflight_check.py` | **PASS** | Python 3.12.7 (.venv), 패키지 5종, DB 3종(RFC 8089 as_uri() 연결, 물리 무결성 ok, 테이블 15개, 연도 4개년, 브랜드 5,063개, 링크 735,208개), frontend/.env VITE_API_URL 유효성, Node v23.4.0, 보호자산 100% 일치 |
| **스모크 테스트 (인메모리)** | `.venv/Scripts/python.exe scripts/smoke_test_api.py` | **PASS** | **12/12 성공 (0 실패)**, **평균 지연시간 28.7ms** |
| **단위/통합 테스트 (격리/동적집계)** | `.venv/Scripts/python.exe scripts/run_tests.py` | **PASS** | **82/82 성공 (0 실패)**, 실제 통과 건수 동적 집계(40+11+15+16=82), 소요시간 31.99s, 운영 DB 파일 쓰기/복원 없이 100% 원본 유지 |
| **프론트엔드 빌드** | `npm run build --prefix frontend` | **PASS** | Vite v5.4.21, 4.04s, HTML(668B)/CSS(130,111B)/JS(1,046,827B) 번들 정상 생성 (exit code: 0) |
| **브라우저 레이어 실측** | `node scratch/test_phase6_step2_browser.mjs` | **PASS** | CDP 환경에서 격자·점포·핫스팟 토글 및 MapLibre 레이어 visibility(`none` <-> `visible`) 전환/복원 실측 100% 일치 (`allPassed: true`) |
| **운영 DB 불변성** | `PRAGMA integrity_check` & 전수 검사 | **PASS** | `ok`, 크기 200,921,088바이트, 리뷰 2건 보존, `BRD_KOR_0001` 원래 타임스탬프(`2026-10-14 14:48:01`) 유지, 브랜드 5,063개 / 링크 735,208개 전수 불변 |
| **보호 자산 SHA-256** | 보호 파일 3종 해시 검증 | **PASS** | 원본 해시 기준값과 비트 단위 100% 일치 |
| **비즈니스 코드 불변** | `src/**`, `frontend/src/**` | **PASS** | 신규 비즈니스 로직 추가 및 기존 소스 코드 수정 없음 |

### 4.1 스모크 테스트 세부 지표 (인메모리 기준)
```text
[PASS] 1. 헬스체크 및 기본 메타데이터                  | 200 |   77.2ms | /
[PASS] 2. 전국 시장 종합 대시보드 개요                 | 200 |   15.2ms | /api/v1/analytics/summary
[PASS] 3. 16개 광역 시도 목록                     | 200 |   18.5ms | /api/v1/analytics/regions?region_type=SIDO&limit=20
[PASS] 4. 서울특별시(11) 지역 상세 통계               | 200 |   15.5ms | /api/v1/analytics/regions/11
[PASS] 5. 48개 외식 중분류 및 통계                  | 200 |   17.8ms | /api/v1/analytics/categories
[PASS] 6. 브랜드 검색 및 자동완성                    | 200 |   20.5ms | /api/v1/analytics/brands/search?limit=10
[PASS] 7. 강남구 코엑스 BBOX 점포 GeoJSON 스트리밍     | 200 |   68.2ms | /api/v1/spatial/stores/bbox
[PASS] 8. 광진구 100m 정밀 밀집도 격자 (MapLibre fill-extrusion 3D 기둥) | 200 |   16.8ms | /api/v1/spatial/density/grid?sigungu_code=11215&limit=1500
[PASS] 9. 상위 상권 핫스팟 클러스터 (Drone Flight Tour) | 200 |   10.9ms | /api/v1/spatial/hotspots
[PASS] 10. 공정위 거시통계 및 감사 상태 (2023~2026 4개년) | 200 |   22.4ms | /api/v1/ftc/status
[PASS] 11. 한식 업종 공정위 창업비용 벤치마크             | 200 |   35.5ms | /api/v1/ftc/benchmark/latest?category_major_id=CAT_MAJ_01
[PASS] 12. 한식 업종 다년도 거시 추세 (2023~2026 Trends) | 200 |   25.3ms | /api/v1/ftc/trends?category_major_id=CAT_MAJ_01
-----------------------------------------------------------------
스모크 테스트 결과: 12 성공 / 0 실패 (평균 지연시간: 28.7ms)
```

### 4.2 기존 테스트 스위트 82개 세부 통과 결과 (격리 및 동적 집계 러너)
- `tests/test_phase4_stage4a.py` ~ `test_phase4_stage4c.py`: **40 passed** (5.08s)
- `tests/test_phase4_stage4d.py`: **11 passed** (16.26s)
- `tests/test_phase4_stage4e.py`: **15 passed** (7.70s)
- `tests/test_phase5b_step1.py`, `test_phase5b_step2_supplement.py`: **16 passed** (2.95s)
- **합계: 82 passed in 31.99s (100% 무결점 통과, 모의 미달 실패 검증 및 운영 DB 전후 수정 0건)**

### 4.3 브라우저 토글 및 MapLibre 레이어 visibility 실측 증빙
- `reports/phase6_step2_browser_toggle_grid_off.png`: 3D 격자 기둥 레이어 OFF (`visibility: none`) 시각적 증빙
- `reports/phase6_step2_browser_toggle_store_off.png`: 개별 점포 스트리밍 레이어 OFF (`visibility: none`, HUD 숨김) 시각적 증빙
- `reports/phase6_step2_browser_toggle_hotspot_off.png`: 상권 핫스팟 패널 OFF 시각적 증빙
- `reports/phase6_step2_browser_all_toggles_verified.png`: 전체 레이어 정상 복원 (`visibility: visible`) 종합 증빙

### 4.4 보호 파일 SHA-256 무결성 검증
| 파일명 | 기준 해시 (SHA-256) | 측정 해시 | 판정 |
|---|---|---|:---:|
| `collector.py` | `341BAC12BB0AF58DCBDEBBA9459033521F27DF9817E35BAD8B21A4D07BA3369C` | `341BAC12BB0AF58DCBDEBBA9459033521F27DF9817E35BAD8B21A4D07BA3369C` | **일치** |
| `gangnam_food_stores.sqlite3` | `FEE3B58651CFED5C390C0B95DB02B05EBE92DF18619A06F4E399D429236F3A78` | `FEE3B58651CFED5C390C0B95DB02B05EBE92DF18619A06F4E399D429236F3A78` | **일치** |
| `run_gangnam.bat` | `0582C3A1AE53450DDC482E9BF538510780CA2F14D44E987CC753D4E12C816491` | `0582C3A1AE53450DDC482E9BF538510780CA2F14D44E987CC753D4E12C816491` | **일치** |

---

## 5. 결론 및 다음 단계

Phase 7 Step 7-1의 모든 요구사항 및 Codex 지적 사항:
1. `tests/test_phase4_stage4c.py`의 `record_brand_review` 테스트를 `tempfile` 임시 DB로 완전 격리하여 운영 DB 쓰기 0건 입증 완료
2. `scripts/run_tests.py`에서 운영 DB 파일 복사 및 복원 로직을 전면 제거하고 실제 pytest 출력을 파싱하여 건수 미달 시 실패 처리하는 동적 집계 러너 구축 완료
3. 검증 JSON 및 보고서에 기록된 DB 및 번들 크기를 실제 파일 시스템 측정값(200,921,088 bytes, 1,046,827 bytes 등)으로 전수 동기화 완료
4. `preflight_check.py`에 RFC 8089 `as_uri() + "?mode=ro"` 연결, 물리 무결성, FTC 연도 목록, 브랜드/링크 임계치, `VITE_API_URL` 엄격 검사 및 exit 1 강제 완료
5. 백엔드 기동 스크립트 루트 작업 디렉터리 고정 및 `--app-dir` 적용 완료
6. MapLibre 실제 레이어 visibility(`none` <-> `visible`) 전환 및 복원 실측 검증 통과
7. 12대 API 스모크 테스트 100% 통과 (인메모리 평균 28.7ms)
8. 82개 테스트 스위트 100% 통과 (31.99s, 운영 DB 불변 확인)
9. 보호 파일 3종 SHA-256 무결성 100% 일치
를 모두 완벽히 달성했습니다.

`.agent-workflow/IMPLEMENTATION.md`를 갱신하고 재검토를 요청합니다.
