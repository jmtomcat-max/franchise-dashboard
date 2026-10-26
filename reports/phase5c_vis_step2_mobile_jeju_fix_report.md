# Phase 5C-Vis Step 2 모바일 제주시 전체 조망 표시 오류 수정 및 회귀 검증 보고서

**문서 경로**: `reports/phase5c_vis_step2_mobile_jeju_fix_report.md`  
**작성 일시**: 2026-10-16  
**원시 측정 데이터**: `reports/phase5c_vis_step2_mobile_jeju_metrics.json`  
**검증 브라우저**: Google Chrome 155.0.8059.81 (Headless with CDP, WebGL 2.0 하드웨어 가속)

---

## 1. 개요 및 수정 배경

### 1.1 오류 현상
- 390×844 모바일 뷰포트에서 제주시(`sigungu_code: '50110'`) 선택 시, 소진공 API로부터 1,351건의 격자 데이터를 정상 수신함에도 불구하고 지도 화면상에 점포 분포 표시가 나타나지 않았습니다.
- 직전 측정(`phase5c_vis_step2_comp_after_metrics.json`)에서 카메라 줌이 약 `zoom 7.42`였으며, `mobile.jejuOverview.counts.rendered.overviewLayer.uniqueGridIds`가 `0`으로 측정되어 화면에 표시되지 않는 결함이 확인되었습니다.

### 1.2 근본 원인 분석
1. **타일링 엔진(`geojson-vt`)의 폴리곤 면적 단순화 허용치(Tolerance)**:
   - 100m 격자 셀의 지리적 폭은 약 0.001°이며, zoom 7.42 시점에서는 화면 픽셀 폭이 **약 0.26px**에 불과합니다.
   - `geojson-vt`의 기본 허용치(0.375px)보다 작아, 폴리곤 기하구조(`Polygon`)로만 소스가 구성되었을 때 모바일 저줌 타일에서 격자 셀들이 축소 소멸(degenerate)되어 타일 피처 목록에서 제외되었습니다.
2. **개요 레이어 표현식의 줌 하한선 미달**:
   - `density-grid-overview-points` 레이어의 `circle-opacity` 및 `circle-stroke-opacity` 보간 식의 시작 stop이 `zoom 8`로 설정되어 있어 zoom 7.42 영역에서 정상적인 불투명도 적용이 보장되지 않았습니다.
3. **모바일 뷰포트 대비 과도한 패딩**:
   - 390px 폭 모바일 환경에서 좌우 65px(총 130px) 패딩을 적용하여 유효 가시 폭이 260px로 축소되었고, 이로 인해 카메라가 zoom 7.421까지 과도하게 멀어지는 현상이 발생했습니다.

---

## 2. 코드 수정 내역 (`frontend/src/components/MapContainer.jsx`)

1. **광역 조망 전용 포인트 소스(`density-grid-overview-source`) 신설**:
   - `formatGridToPointsGeoJSON(gridItems)` 함수를 추가하여 100m 정밀 격자 셀의 중심 좌표 `[center_lon, center_lat]` 기반 `Point` 피처 컬렉션을 생성했습니다.
   - `Point` 기하구조는 `geojson-vt` 엔진에서 면적 단순화에 의해 삭제되지 않으므로, 광역 저줌(zoom 6~8)에서도 1,351개 피처가 100% 온전하게 보존됩니다.
   - 소스 옵션에 `tolerance: 0`을 명시하여 타일 축소 시에도 피처 누락을 방지했습니다.
2. **개요 원형 레이어 표현식 최소 줌 확장 (zoom 6부터 지원)**:
   - `circle-radius`: `[interpolate, linear, zoom, 6, 2.0, 7, 2.5, 8, 3.2, 10, 4.2, 13, 5.5, 15, 7.0]`
   - `circle-opacity`: `[interpolate, linear, zoom, 6, 0.90, 8, 0.88, 12, 0.85, 14, 0.40, 15.5, 0.0]`
   - `circle-stroke-opacity`: `[interpolate, linear, zoom, 6, 0.85, 8, 0.85, 13, 0.70, 15, 0.0]`
   - 모바일 제주시 전체 조망(zoom 7.4 ~ 7.9)에서 0.90의 선명한 불투명도와 2.5~3.2px의 반경을 확보했습니다.
3. **모바일 반응형 `fitBounds` 패딩 최적화**:
   - 모바일(화면 폭 768px 이하) 환경에서는 `padding: { top: 60, bottom: 40, left: 24, right: 24 }`를 적용하여 제주도 전역을 뷰포트 내에 시원하게 배치하면서 카메라 줌을 약 7.82로 안정화했습니다.

---

## 3. 모바일 제주시 실측 검증 결과 (수신 수 vs 실제 표시 수 구분)

소진공 공간 API 응답 수치, 레이어 렌더링 피처 수, 그리고 실제 캡처 화면상의 픽셀 검증 결과를 엄격히 분리하여 실측했습니다.

| 구분 항목 | 실측값 | 판정 기준 및 설명 | 일치 여부 |
| :--- | :---: | :--- | :---: |
| **API 수신 건수 (Received Count)** | **1,351건** | 백엔드 `/api/v1/spatial/density/grid?sigungu_code=50110&limit=1500` 실제 수신 | - |
| **API 메타 총 건수 (`meta.total_count`)** | **1,351건** | SQLite 데이터베이스 저장 총수와 100% 일치 | 일치 |
| **프론트엔드 상태 내 고유 격자 수** | **1,351개** | 중복 `grid_id` 0건 | 일치 |
| **카메라 뷰포트 BBOX 내 격자 중심 수** | **1,351개** | zoom 7.817 시점에서 제주시 전체 1,351개 중심이 화면 내 100% 포함 | 100% |
| **개요 레이어 렌더링 피처 수 (`overviewLayer.uniqueGridIds`)** | **1,351개** | `queryRenderedFeatures`로 실측된 고유 격자 ID 수 (기존 0 → **1,351개**) | **PASS** |
| **화면 캡처 실제 픽셀 분포 검증 (`hasVisibleDistribution`)** | **4,079 px** | 캡처 이미지(PNG) 본섬 영역 내 밀집도 색상(파랑/하늘/보라) 픽셀 실측 | **PASS** |
| **종합 검증 판정** | **PASS** | 수신 수(1,351) = 실제 렌더링 수(1,351) & 화면 가시성 확인 | **PASS** |

> **캡처 증빙 파일**: `reports/phase5c_vis_step2_mobile_jeju_overview_fixed.png`  
> ![모바일 제주시 전체 조망 수정 후](file:///d:/Franchise_Dashboard/reports/phase5c_vis_step2_mobile_jeju_overview_fixed.png)  
> *제주시 도심(시청·연동·노형동) 및 해안선(애월, 한림, 조천, 구좌), 추자도, 우도에 걸쳐 1,351개 외식업 분포 원형 마커가 5단계 밀집도 색상으로 선명하게 표출됨을 확인.*

---

## 4. 데스크톱 5개 시나리오 회귀 검증

모바일 수정 조치 후 기존 데스크톱 기능 및 타 지역 표출에 부작용(Regression)이 없는지 동일 환경에서 전수 재검증했습니다.

| 검증 시나리오 | 해상도 / 카메라 | 렌더링 실측 결과 | 가시성 및 기능 확인 | 판정 |
| :--- | :---: | :--- | :--- | :---: |
| **D1. 데스크톱 제주시 전체 조망** | 1440×900<br>zoom 8.74, pitch 52° | `overviewLayer.uniqueGridIds`: **1,351개**<br>`centersInsideBounds`: 1,351개 | 제주시 전체 1,351개 분포가 5단계 색상 원형으로 정상 표출 | **PASS** |
| **D2. 데스크톱 제주시 상세 줌** | 1440×900<br>zoom 15.3, pitch 52° | `extrusionLayer.uniqueGridIds`: **219개**<br>최대 높이 123.0 pt (점포수 × 3.0) | 신제주 상권 3D 기둥이 입체적으로 정상 솟아오름 | **PASS** |
| **D3. 데스크톱 광진구 전체 조망** | 1440×900<br>zoom 14.0, pitch 52° | `extrusionLayer.uniqueGridIds`: **466개** (100%)<br>최대 기둥 높이 38.4 px | 기둥 화면 잠식 없이 466개 전체 격자 조망 유지 | **PASS** |
| **D4. 데스크톱 광진구 상세 줌** | 1440×900<br>zoom 15.6, pitch 52° | `extrusionLayer.uniqueGridIds`: **117개**<br>건대입구 55개소/165.0 pt | 건대입구 맛의거리 3D 기둥 및 도로망 정상 렌더링 | **PASS** |
| **D5. 전국 빈 상태** | 1440×900<br>zoom 7.0, pitch 20° | 격자 수: **0건**<br>기둥/개요 피처 수: **0 / 0**<br>팝업 잔류: 없음 (false) | 격자 레이어 완전 숨김, 안내 HUD 및 비활성화 범례 정상 | **PASS** |

### 회귀 검증 캡처 증빙 (신규 파일명)
1. `phase5c_vis_step2_desktop_jeju_overview_regression.png`  
   ![데스크톱 제주시 전체 조망](file:///d:/Franchise_Dashboard/reports/phase5c_vis_step2_desktop_jeju_overview_regression.png)
2. `phase5c_vis_step2_desktop_jeju_detail_regression.png`  
   ![데스크톱 제주시 상세 줌](file:///d:/Franchise_Dashboard/reports/phase5c_vis_step2_desktop_jeju_detail_regression.png)
3. `phase5c_vis_step2_desktop_gwangjin_overview_regression.png`  
   ![데스크톱 광진구 전체 조망](file:///d:/Franchise_Dashboard/reports/phase5c_vis_step2_desktop_gwangjin_overview_regression.png)
4. `phase5c_vis_step2_desktop_gwangjin_detail_regression.png`  
   ![데스크톱 광진구 상세 줌](file:///d:/Franchise_Dashboard/reports/phase5c_vis_step2_desktop_gwangjin_detail_regression.png)
5. `phase5c_vis_step2_desktop_nationwide_empty_regression.png`  
   ![데스크톱 전국 빈 상태](file:///d:/Franchise_Dashboard/reports/phase5c_vis_step2_desktop_nationwide_empty_regression.png)

---

## 5. 보고서 기술 정정 (실제 3D 건물 및 그림자 관련 범위)

직전 보고서(`phase5c_vis_step2_complement_report.md` 제7절 등)에서 **실제 3D 건물 모델 및 그림자 투사 기능**을 "Step 3에서 착수할 예정인 확정 작업"으로 기술하였던 부분을 다음과 같이 공식 정정합니다:

### [정정 고지]
- **실제 3D 건물 모델링 및 일조/그림자 투사 기능**은 Phase 5C-Vis Step 3의 확정 구현 작업이 **아닙니다**.
- 본 기능은 대한민국 건축물 공간정보(국토교통부 GIS 등)의 별도 데이터 수급 타당성, 대용량 3D 타일 라이선스 검증, 모바일/데스크톱 WebGL 렌더링 부하 평가가 선행되어야 하는 **후속 검토(Exploratory Review) 대상**입니다.
- 따라서 사용자의 사전 검토 및 명시적 착수 승인이 있기 전에는 임의로 구현 작업에 착수하지 않으며, 현재 단계에서는 확정 범위에서 완전히 배제됩니다.

---

## 6. 결론

- **모바일 제주시 전체 조망 표출 결함 완벽 해결**: 포인트 지오메트리 전용 소스 분리, 줌 표현식 확장(zoom 6~), 반응형 뷰포트 패딩을 적용하여 1,351개 전체 격자 피처 렌더링 및 4,079개의 실제 화면 픽셀 가시성을 입증했습니다.
- **무회귀(Zero Regression) 입증**: 데스크톱 제주시(전체/상세), 광진구(전체/상세), 전국 빈 상태 5개 시나리오가 모두 정상 작동함을 신규 캡처 및 원시 JSON으로 검증 완료했습니다.
- **기존 자산 보존 준수**: 기존 DB, 수집기, 기존 완료 보고서는 일체 수정하거나 덮어쓰지 않고 보존했습니다.
