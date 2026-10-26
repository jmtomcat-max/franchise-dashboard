# Phase 5C 1단계 보완 보고서: 제주시 지도 범위 실측, 화면 즉시 분리, 시도 경쟁 방지 및 실 브라우저 정밀 검증

**문서 번호**: `FRANCHISE-REPORT-PH5C-STEP1-COMPLEMENT-002`  
**작성 일자**: 2026-10-14  
**프로젝트**: `D:\Franchise_Dashboard`  
**상태**: **격자 수신 확인 및 제주시 지도 이동 완료 실측 완료 (사용자 최종 확인 대기)**  
**참조 문서**: `AGENTS.md`, `reports/phase5c_step1_execution_report.md`, `reports/reference_dashboard_adoption_plan_r3.md`

---

## 1. 개요 및 사용자 보완 지침

본 보고서는 **Phase 5C 1단계(선택 지역 연동 100m 밀집도 격자 지도 표출)** 작업 중, **제주시 선택 후 지도 이동 애니메이션 완료 시점의 중심·줌·화면 경계 실측 및 1,351개 격자 포함 여부 검증**에 대한 사용자 보완 지침을 충실히 반영하여 작성되었습니다.

### 1.1 사용자 핵심 지침 및 조치 사항

1. **제주시 지도 이동 완료 시점 정밀 측정**:
   - 데이터 응답 직후가 아닌, **지도 이동 애니메이션(`map.fitBounds`)이 완전히 종료되어 카메라가 정지한 시점**의 중심 좌표, 줌 레벨, 뷰포트 화면 경계(Bounds)를 측정.
2. **1,351개 격자의 화면 내 포함 여부 전수 검증**:
   - 제주시 1,351개 격자의 경위도 바운딩 박스가 지도 화면 뷰포트에 잘림 없이 모두 들어오는지(`insideCount`, `outsideCount`, `coveragePercent`) 정밀 계산.
3. **제주 화면 캡처 및 판정 기준 명시**:
   - 제주시 이동 완료 상태의 실제 크롬 브라우저 화면 캡처 아티팩트(`reports/phase5c_step1_jeju_viewport.png`)를 첨부하고 객관적 판정 기준 제시.
4. **검증 상태 표기 투명화**:
   - 단순 "100% 완전 검증" 주장 대신, **"격자 수신 확인 및 제주시 지도 이동 완료 실측 완료 (사용자 최종 확인 대기)"**로 상태를 투명하게 정정 보고.

---

## 2. 제주시 지도 범위 실측 및 1,351개 격자 포용성 검증

### 2.1 이전 측정의 한계 및 원인 분석

- **원인 분석**: 이전 테스트에서는 제주시 격자 수신 이벤트(`cnt === 1351`)가 감지되자마자 즉시 좌표를 조회하여, 1,000ms 동안 진행되는 `map.fitBounds` 카메라 이동 애니메이션이 미처 시작/종료되지 않은 상태에서 이전 광진구 좌표(`lng: 127.0699, lat: 37.5407`)가 기록되는 오류가 있었습니다.
- **개선 조치**: Chrome CDP 테스트 스크립트([scratch/browser_cdp_test.mjs](file:///d:/Franchise_Dashboard/scratch/browser_cdp_test.mjs))에 `map.isMoving()`, `map.isZooming()`, `map.isRotating()`이 모두 `false`가 되고 300ms 추가 안정화가 완료될 때까지 대기하는 **카메라 정지 감지 루프**를 구현하여 이동 완료 시점의 순수 정적 뷰포트를 실측하였습니다.

### 2.2 제주시 이동 완료 시점 실측 측정값

| 측정 항목 | 실측값 | 판정 기준 및 의미 |
| --- | --- | --- |
| **카메라 상태** | 정지 완료 (`isMoving: false`) | 애니메이션 종료 확인 |
| **중심 경도 (Center Lng)** | `126.56700000000001° E` | 제주시 중심부 정확히 일치 |
| **중심 위도 (Center Lat)** | `33.63904340284516° N` | 제주시 중심부 정확히 일치 |
| **줌 레벨 (Zoom)** | `8.6278` | 1,351개 격자 전수 조망 최적 줌 |
| **화면 경계 남서단 (SW)** | `Lng: 125.440835°, Lat: 33.103944°` | 제주시 최남단/최서단 외곽 여유 확보 |
| **화면 경계 북동단 (NE)** | `Lng: 127.693165°, Lat: 35.326796°` | 추자도 등 부속 도서 포함 외곽 여유 확보 |
| **제주시 격자 최소 좌표** | `minLon: 126.165°, minLat: 33.298°` | `minLon >= SW.lng (126.165 >= 125.441)` : **충족**<br>`minLat >= SW.lat (33.298 >= 33.104)` : **충족** |
| **제주시 격자 최대 좌표** | `maxLon: 126.969°, maxLat: 33.964°` | `maxLon <= NE.lng (126.969 <= 127.693)` : **충족**<br>`maxLat <= NE.lat (33.964 <= 35.327)` : **충족** |
| **화면 내 포함 격자수** | **1,351개소 / 1,351개소** | **100.00% 전수 화면 내 포용** |
| **화면 외 이탈 격자수** | **0개소 (0.00%)** | 외곽 잘림/누락 0건 |

### 2.3 제주시 실측 화면 캡처 아티팩트

- **아티팩트 파일**: [reports/phase5c_step1_jeju_viewport.png](file:///d:/Franchise_Dashboard/reports/phase5c_step1_jeju_viewport.png)
- **로컬 아티팩트 저장소**: `C:\Users\jongmin98\.gemini\antigravity-ide\brain\e277a09d-d309-4b21-aaae-1fe31ab1fdc4\phase5c_step1_jeju_viewport.png`
- **파일 크기**: 315,316 Bytes
- **화면 검증 확인 내용**:
  - 제주시 중심부터 해안가 및 부속 도서에 걸친 1,351개 100m 밀집도 격자 원(Circle)이 화면 중심부에 온전히 프레이밍되어 렌더링됨.
  - 상단 HUD: `📍 제주특별자치도 제주시 전체 외식업 밀집도 (100m 격자 1,351개소) | 벤치마크 대상: 🍚 한식 (전국 공정위)` 정상 표출.
  - 우측 하단 범례: `전체 외식 점포 밀집도 (소진공) - 100m 격자당 점포 수 (1,351개 격자)` 정상 표출.

---

## 3. 화면 즉시 분리 및 시도 경쟁 방지 보완 내역

### 3.1 지역 선택 즉시 화면 분리 (Zero-delay Decoupling)

- **적용 위치**: [frontend/src/App.jsx](file:///d:/Franchise_Dashboard/frontend/src/App.jsx), [frontend/src/components/MapContainer.jsx](file:///d:/Franchise_Dashboard/frontend/src/components/MapContainer.jsx)
- **동작**:
  - 지역 선택 변경 즉시 `setRegionDetail(null)`, `setGridData([])`, `setRegionError(null)`, `setGridError(null)`을 실행.
  - 지도 인스턴스에서 격자 레이어 가시성을 `'none'`으로 전환하고, GeoJSON 소스를 빈 배열(`[]`)로 교체하며, 열려 있던 기존 팝업을 즉시 제거(`remove()`).
  - **실측 결과**: 제주시 선택 후 60ms 이내(네트워크 도착 전) `gridCount: 0`, HUD 로딩 스피너 활성화(`hasSpinner: true`) 확인.

### 3.2 새 지역 응답 확정 후 지도 범위 적용 (Deferred Camera Framing)

- **적용 위치**: [frontend/src/components/MapContainer.jsx](file:///d:/Franchise_Dashboard/frontend/src/components/MapContainer.jsx)
- **동작**:
  - `gridLoading`이 `true`인 동안에는 `map.fitBounds`나 `map.flyTo` 호출을 전면 보류(`if (gridLoading) return;`).
  - 새 지역 응답이 확정되어 `gridData`가 온전히 들어온 시점에만 해당 지역의 실제 BBOX를 계산하여 부드럽게 프레이밍.

### 3.3 시도 목록 조회 연속 선택 경쟁 상태 방지

- **적용 위치**: [frontend/src/App.jsx](file:///d:/Franchise_Dashboard/frontend/src/App.jsx)
- **동작**:
  - `sidoAbortRef`와 `sidoReqIdRef`를 신설하여, 시도 변경 시 진행 중인 이전 시군구 조회를 즉시 `abort()`하고 `setSigunguList([])`로 시군구 드롭다운을 즉시 비움.
  - 지연 도착한 과거 시도의 응답은 순번 검증(`reqId === sidoReqIdRef.current`)을 통해 엄격히 폐기.
  - **실측 결과**: 제주(`50`) 클릭 20ms 후 서울(`11`) 연속 전환 시, 최종 드롭다운에 서울 25개 구만 정상 표출(`hasGangnam: true, hasJeju: false`).

---

## 4. 실제 크롬 브라우저(CDP) 7대 항목 전수 검증 결과 종합

| 번호 | 테스트 항목 | 검증 조건 | 실측값 및 동작 상태 | 판정 |
| --- | --- | --- | --- | --- |
| **T1** | 초기 광진구 격자 및 HUD 표출 | 서울 광진구(`11215`) 로드 | `gridCount: 466`, HUD `466개소`, 범례 5단계 램프 표출 | **PASS** |
| **T2** | 지역 선택 즉시 이전 격자·팝업 분리 | 제주시 선택 직후(<60ms) 측정 | `gridCount: 0`, 로딩 스피너 활성화, 이전 셀/팝업 완전 제거 | **PASS** |
| **T3** | **제주시 1,351개 수신 및 이동 완료 뷰포트 포용** | 제주시 응답 후 애니메이션 완료 시점 | **중심 [126.567, 33.639], 줌 8.63, 1,351개소 전수 포용 (100.00%)** | **PASS** |
| **T4** | 빠른 연속 전환 레이스 컨디션 차단 | 강남 -> 송파 -> 광진 20ms 간격 전환 | 중간 지연 응답 자동 폐기, 최종 광진구(`11215`, 466개) 수렴 | **PASS** |
| **T5** | 시도 연속 전환 시군구 목록 정합성 | 제주(`50`) -> 서울(`11`) 20ms 간격 전환 | 서울 25개 구 일치, 제주 옵션 유입 0건 | **PASS** |
| **T6** | 전국/시도 단위 드릴다운 빈 상태 | 전국(`00`) 선택 | `gridCount: 0`, 레이어 숨김(`visibility: 'none'`), 안내 배지 표출 | **PASS** |
| **T7** | 팝업 소진공 전체 점포 vs 공정위 분리 명시 | 격자 셀 팝업 오픈 | `서울특별시 광진구 100m 격자 셀 분석 (전체 점포 기준)` 및 공정위 거시통계 분리 안내문 정상 표출 | **PASS** |

---

## 5. 기존 자산 무결성 확인 및 결론

### 5.1 무결성 확인

- SQLite 데이터베이스(`data/franchise_analytics_v1.sqlite3`, `data/gangnam_food_stores.sqlite3`): **무수정 유지 (100% 보존)**
- 데이터 수집기 및 배치 스크립트: **무수정 유지 (100% 보존)**
- 기존 검증 보고서 및 분류 체계: **무수정 유지 (100% 보존)**

### 5.2 현재 상태 및 보고

- 사용자 지침에 따라 **제주시 선택 후 지도 이동 완료 시점의 중심(`126.567, 33.639`), 줌(`8.628`), 화면 경계(Bounds) 및 1,351개 격자 100.00% 포용(이탈 0건) 실측 검증**을 완료하였으며, 실측 스크린샷 아티팩트를 첨부하였습니다.
- Phase 5C Step 2(브랜드 순위, 전년 대비 증감, 4개년 트렌드)로 임의 진행하지 않으며, **본 보완 보고서에 대한 사용자의 검토 및 승인을 대기합니다.**
