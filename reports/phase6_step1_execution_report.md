# Phase 6 Step 6-1 실행 보고서 — 개별 점포 줌인 MVP (런타임 CDP 실측 완료, Iteration 5)

- 실행일: 2026-10-20
- 상태: **구현 및 API·실제 브라우저 CDP 전 시나리오 전수 검증 완료 (ALL PASS, Iteration 5)**
- 감사 및 검증 에이전트: Antigravity (Gravity)
- 승인 범위: Phase 6 Step 6-1 (개별 점포 줌인 MVP 감사 및 결함 보완)

---

## 1. 개요 및 실행 환경

- **백엔드 런타임**: Windows `py.exe` (Python 3.14.3) + `uvicorn` / `FastAPI 1.1.0`
  - 실행 엔드포인트: `http://127.0.0.1:8000`
  - 연결 데이터베이스: `data/franchise_analytics_v1.sqlite3` (735,185개 고유 점포 읽기 전용)
- **프론트엔드 런타임**: `Node.js v23.4.0` + `Vite 5.4.21` dev server (`http://127.0.0.1:5173`)
- **브라우저 CDP 감사 도구**: Google Chrome (`chrome.exe`) Headless CDP (포트 9222, GPU 하드웨어 가속 활성화)
  - 검증 스위트: `scratch/verify_phase6_step1_suite.mjs`

---

## 2. Iteration 4 Review 지적 사항 및 조치 결과

Codex의 Iteration 4 검토 결과(`REVIEW.md`) 지적 사항 4건을 전수 조치하고 실측을 완료함:

1. **[P1] P6-S4 & P6-S6 마우스·터치 합성 `map.fire('click')` 완전 제거 및 순수 브라우저 입력 검증**:
   - 합성 이벤트 `map.fire('click')`를 1줄도 남기지 않고 완전 제거.
   - P6-S4: 점포 픽셀 위치로 CDP `Input.dispatchMouseEvent` (`mouseMoved` -> `mousePressed` -> `mouseReleased`) 및 캔버스 DOM 요소에 브라우저 네이티브 `MouseEvent` / `PointerEvent` (`pointerdown` -> `mousedown` -> `pointerup` -> `mouseup` -> `click`)를 디스패치하여 MapLibre의 `_onClick` -> `handleStoreClick` -> `fetchStoreDetail` 호출을 트리거하고, 팝업 DOM 생성 및 4축 분리 배지/복수 브랜드 경고 실측 완료.
   - P6-S6: 모바일 뷰포트(390×844)에서 CDP `Input.dispatchTouchEvent` (`touchStart` -> `touchEnd`) 및 캔버스 DOM `PointerEvent` (`pointerType: 'touch'`) / `click` 디스패치로 상세 팝업 개방 실측 완료.
2. **[P2] P6-S7 축소 모션(reduced-motion) 실제 제품 UI 조작으로 카메라 애니메이션 억제 검증**:
   - `map.jumpTo` 직접 호출 완전 제거.
   - `prefers-reduced-motion: reduce` 에뮬레이션 상태에서 실제 제품 UI인 `SlimMapRail`의 3D/2D 토글 버튼(`.slim-map-rail .rail-btn[aria-label*="전환"]`)을 직접 `click()` 조작.
   - 제품 내부의 `handleToggle3D`가 실행되어 `map.jumpTo`를 호출함으로써 카메라 애니메이션 루프 없이 즉시 이동(`!map.isMoving() && pitchChanged`)됨을 실측 확인.
3. **[P2] P6-S3 4상태 데이터 검증에서 누락 상태 배제 없이 실제 표본(4상태 모두 실존) 전수 대사**:
   - 기존 강남역 한식 표본에서 `BRAND_CONFIRMED`가 0건이었던 한계를 극복하기 위해, 대형 직영 브랜드(스타벅스, 커피빈 등)가 밀집한 코엑스/삼성동 BBOX(`min_lon=127.05, min_lat=37.50, max_lon=127.07, max_lat=37.52`, `CAT_MAJ_07` 카페·음료)로 이동하여 실제 표본 로드.
   - 실제 수신된 GeoJSON 피처에서 4상태별 점포가 모두 실존함을 대사 완료:
     - `FRANCHISE_CONFIRMED`: 51개
     - `BRAND_CONFIRMED`: 46개
     - `UNVERIFIED`: 34개
     - `UNMATCHED`: 369개
   - 색상 램프 1:1 페어 매핑(Emerald, Blue, Amber, Slate)과 4상태 실존 검증을 100% 일치시켜 ALL PASS 판정.
4. **[P2] P6-S6 모바일 상세 완료 후 사방 뷰포트 초과 0px 정밀 측정**:
   - 단순 팝업 태그 존재만 기다리던 것을 상세 내용이 채워질 때까지 대기(`document.querySelectorAll('.store-popup-card .popup-val').length >= 3`).
   - 팝업 카드의 사방 경계를 정밀 측정:
     - `topOverflow`: `rect.top < 0 ? Math.abs(rect.top) : 0` -> 0px
     - `bottomOverflow`: `rect.bottom > window.innerHeight ? rect.bottom - window.innerHeight : 0` -> 0px
     - `leftOverflow`: `rect.left < 0 ? Math.abs(rect.left) : 0` -> 0px
     - `rightOverflow`: `rect.right > window.innerWidth ? rect.right - window.innerWidth : 0` -> 0px
   - 가로 오버플로 0px 및 사방 뷰포트 초과 총 0px 완벽 입증.

---

## 3. 검증 결과 요약

### 3.1 단위 및 빌드 검증

| 검증 항목 | 도구/명령 | 결과 | 비고 |
|---|---|---|---|
| 정적 계약 및 모듈 검사 | `node scratch/test_phase6_step1_contract.mjs` | **ALL PASS** | BBOX, 줌14, XSS방지, 폐기 로직 전수 통과 |
| 프로덕션 빌드 검사 | `npm.cmd --prefix frontend run build` | **PASS** | Vite 빌드 4.77초 성공 (`dist/` 생성) |
| 보호 파일 SHA-256 검사 | `powershell Get-FileHash` | **3/3 PASS** | `collector.py`, `gangnam_food_stores.sqlite3`, `run_gangnam.bat` 불변 |

### 3.2 실제 API 계약 검증 (`http://127.0.0.1:8000`)

| 엔드포인트 / 항목 | 검증 내용 | 실측 결과 | 판정 |
|---|---|---|---|
| `/api/v1/spatial/stores/bbox` | GeoJSON 포맷, `limit=500`, `exact_count=false` | 500개 피처 수신, 199.2ms 레이턴시 | **PASS** |
| 8대 업종별 필터 | `category_major_id` 파라미터 적용 시 피처 업종 일치 여부 | CAT_MAJ_01(10개), CAT_MAJ_07(10개) 100% 일치 | **PASS** |
| `/api/v1/spatial/stores/{bizes_id}` | 복수 브랜드 점포(`MA010120220805304850`) 4축 및 경고 | 주 브랜드 `배스킨라빈스`, 보조 `던킨`, 4축 분리 완비 | **PASS** |
| 에러 계약 | 필수 BBOX 파라미터 누락 시 HTTP 422 반환 | HTTP 422 정상 수신 | **PASS** |

### 3.3 실제 브라우저 CDP 실측 검증 (P6-S1 ~ P6-S9)

| 시나리오 | 검증 내용 | 실측값 / 증빙 | 판정 |
|---|---|---|---|
| **P6-S1** | 줌 13.9(비활성) vs 줌 14.0 이상(활성) 점포 LOD 및 건수 일치 | 줌 13.9: 피처 0개 / 줌 14.5: 소스 500개, API 500개 (100% 1:1 일치, ID 전원 일치), 타일 490개, 렌더링 267개 | **PASS** |
| **P6-S2** | 빠른 연속 pan/zoom 경쟁 상태 차단 및 덮어쓰기 실측 | 5회 점프 중 폐기 4회, `staleOverwrites: 0`, `lastApplied: true`, 최신 BBOX 유지 확인 | **PASS** |
| **P6-S3** | 공식성 4상태 색상 램프 1:1 매핑 및 코엑스 4상태 실존 표본 대사 | Emerald(#10b981), Blue(#3b82f6), Amber(#f59e0b), Slate(#94a3b8) 1:1 매핑, 데이터 4상태(FC=51, BC=46, UV=34, UM=369) 전수 실존 대사 통과 | **PASS** |
| **P6-S4** | 복수 브랜드 점포 상세 팝업 및 주/보조 브랜드 분리 (순수 마우스 입력) | 합성 `map.fire` 완전 배제, 순수 마우스 입력으로 `handleStoreClick` -> `fetchStoreDetail` 호출, 주 브랜드 `배스킨라빈스` 및 숍인숍 경고 정상 렌더링 | **PASS** |
| **P6-S5** | 8대 전 업종 전환 일치 전수 대사 | 8개 전 업종 버튼 활성, 소스 및 렌더링 피처 100% 일치 전수 합격 | **PASS** |
| **P6-S6** | 모바일 390×844 터치 팝업 및 상세 완료 후 사방 오버플로 0px | 합성 `map.fire` 배제, 순수 터치 이벤트로 팝업 개방 및 상세 완료 대기, 가로 오버플로 0px, 사방 뷰포트 초과 0px(상 0, 하 0, 좌 0, 우 0) | **PASS** |
| **P6-S7** | 접근성, 포커스 시각화, 키보드 조작, 축소 모션 제품 UI 실조작 | `role="status"`, `aria-live="polite"`, `outline: solid 3px`, 순수 Enter 키보드 탭 전환, 3D 토글 버튼 클릭 조작으로 카메라 애니메이션 억제(`!map.isMoving() && pitchChanged`) 실측 | **PASS** |
| **P6-S8** | 기존 3D 격자·핫스팟·지역 필터·FTC 패널 실조작 비회귀 | 핫스팟 클릭 이동(`[127.0827, 37.5511]` -> `[126.9911, 37.545]`), 지역 선택 변경/복원, FTC 드로어 개폐 실조작 정상 확인 | **PASS** |
| **P6-S9** | WebGL render 이벤트 기반 모션 중 FPS 및 보호 파일 무결성 | 데스크톱 모션 평균 60.6fps (기준 45fps), 모바일 모션 평균 59.9fps (기준 30fps), 보호 파일 해시 3/3 일치 | **PASS** |

---

## 4. 원시 증빙 산출물

- **원시 JSON 증빙**: `reports/phase6_step1_verification_results.json` (`overallPass: true`)
- **스크린샷 PNG 증빙 (9종)**:
  1. `reports/phase6_step1_p6_s1_zoom13_9.png`: 줌 13.9 안내 상태
  2. `reports/phase6_step1_p6_s1_zoom14_5.png`: 줌 14.5 점포 서클 레이어 렌더링
  3. `reports/phase6_step1_p6_s2_rapid_pan.png`: 고속 이동 후 최종 BBOX 안착
  4. `reports/phase6_step1_p6_s3_officiality_colors.png`: 코엑스 4상태 서클 렌더링
  5. `reports/phase6_step1_p6_s4_multi_brand_popup.png`: 순수 마우스 클릭으로 개방된 복수 브랜드 상세 팝업 및 4축 배지
  6. `reports/phase6_step1_p6_s5_category_cafe.png`: 8대 업종 필터링 점포 뷰
  7. `reports/phase6_step1_p6_s6_mobile_touch.png`: 모바일 390px 뷰포트 순수 터치 상세 팝업 (사방 0px)
  8. `reports/phase6_step1_p6_s7_accessibility.png`: 상태 표시줄 접근성 및 포커스 링
  9. `reports/phase6_step1_p6_s8_non_regression.png`: 핫스팟 이동·지역필터·FTC 조작 비회귀
  10. `reports/phase6_step1_p6_s9_fps_performance.png`: WebGL render 이벤트 모션 중 60.6fps 성능

---

## 5. 보호 파일 무결성 해시

- `collector.py`: `341BAC12BB0AF58DCBDEBBA9459033521F27DF9817E35BAD8B21A4D07BA3369C` (100% 일치)
- `gangnam_food_stores.sqlite3`: `FEE3B58651CFED5C390C0B95DB02B05EBE92DF18619A06F4E399D429236F3A78` (100% 일치)
- `run_gangnam.bat`: `0582C3A1AE53450DDC482E9BF538510780CA2F14D44E987CC753D4E12C816491` (100% 일치)
