# Phase 5C Step 2 실행 및 검증 보고서
**대시보드 지표의 데이터 출처·기준시점·집계단위 정합화 (실제 API 응답 연동)**

- **문서 버전**: v1.0
- **작성 일자**: 2026-10-14
- **작업 디렉터리**: `D:\Franchise_Dashboard`
- **준수 규격**: `AGENTS.md` (보호 규칙 및 단계별 승인 절차 준수), `reports/reference_dashboard_adoption_plan_r3.md`

---

## 1. 개요 및 작업 목표

본 단계(Phase 5C Step 2)는 대시보드 화면에 하드코딩되어 있던 고정 문구(`소진공 2024 공간 전수`)를 전면 제거하고, **실제 백엔드 API 응답 필드(`meta.data_reference_month`)에 기반한 동적 출처·기준시점 표기 체계를 확립**하는 것을 목표로 수행되었습니다.

또한, 공정거래위원회의 등록 기준연도(`benchmark_year`)와 결산연도(`financial_year`)의 개념적 차이를 명확히 구분하고, 소상공인시장진흥공단의 개별 점포 전수 조사와 공정위 가맹본부 거시 공시가 서로 다른 모집단·집계단위임을 이용자가 오인하지 않도록 정합화 및 주의 문구(Disclaimer)를 배치하였습니다.

---

## 2. 핵심 수정 및 구현 내역

### 2.1 소진공 기준월 동적 연동 및 폴백(Fallback) 안전망 구축
1. **고정 문구 완전 제거**:
   - `frontend/src/components/CategoryFilterBar.jsx`에 하드코딩되었던 `소진공 2024 공간 전수` 제거.
   - `App.jsx`에서 활성 지역 통계 API(`/api/v1/analytics/regions/{code}`)의 `meta.data_reference_month` 및 요약 API(`/api/v1/analytics/summary`)의 메타값을 수신하여 동적으로 상태를 전달.
2. **실제 API 응답값 반영**:
   - 실제 API 반환값인 `"2026-07"`에 따라 대시보드 전반에 `소진공 2026-07 공간 전수`로 자동 렌더링.
3. **결손 및 조회 실패 시 안전망**:
   - `meta.data_reference_month`가 `null`, `undefined`, 또는 빈 문자열(`""`)일 경우, 임의의 연도를 추측하여 표시하지 않고 `소진공 기준월 확인 불가`로 안전하게 표시(CSS 스타일: `.tag-unverified`, 회색 점선 보더).

### 2.2 공정위 기준연도(등록) vs 결산연도(회계) 명확한 분리 및 상태 판정
실제 API 필드인 `is_snapshot`, `is_fallback_applied`, `benchmark_year`, `financial_year`에 따라 뱃지와 상태를 동적으로 판정합니다.

| 상태 구분 | 판정 조건 (API 응답 필드) | 화면 표기 문구 | UI 스타일 및 의미 |
| :--- | :--- | :--- | :--- |
| **진행형 스냅샷** | `benchmark_year == 2026` 또는 `is_snapshot == true` | `공정위 2026년 등록 (2025년 결산) · 진행형 스냅샷` | 앰버 뱃지 (`.badge-snapshot-amber`), 모집단 30% 미등록 결손 주의 문구 명시 |
| **최신 완결 후보** | `benchmark_year == 2025` (마감 미확정) | `공정위 2025년 등록 (2024년 결산) · 최신 완결 후보` | 틸 뱃지 (`.badge-candidate-teal`), 공식 행정마감 미확인 안내 |
| **이전 연도 대체 (Fallback)** | `is_fallback_applied == true` | `공정위 {benchmark_year}년 대체 ({financial_year}년 결산)` | 경고 뱃지 (`.tag-ftc-fallback`), 대체 사유 툴팁 표시 |
| **기준연도 미확인** | `benchmark_year` 부재/오류 | `공정위 기준연도 확인 불가` | 중립 뱃지 (`.tag-unverified`), 임의 연도 추측 차단 |

### 2.3 듀얼 침투율 분자·분모 정합성 검증 및 모집단 분리 경고
1. **소진공 공간 전수 듀얼 침투율**:
   - **공식 프랜차이즈 침투율**: 전국 기준 `6.53%` (분자 48,002개 / 분모 735,185개)
   - **브랜드 연계 침투율**: 전국 기준 `22.89%` (분자 168,295개 / 분모 735,185개)
   - 지역 선택 시 분자·분모 및 전국 기준선 분자·분모를 툴팁과 수식 텍스트로 투명하게 표시:
     - 광진구 예시: `지역: 323개 / 4,507개 (전국 기준 6.53%: 48,002 / 735,185)`
     - 제주시 예시: `지역: 535개 / 11,711개 (전국 기준 6.53%: 48,002 / 735,185)`
     - 전국 모드(`00`): `전국: 48,002개 / 735,185개 (전국 기준 6.53%: 48,002 / 735,185)`, 격차(Diff) 뱃지 자동 숨김
2. **모집단 오인 방지 경고 박스 배치**:
   - 침투율 카드 하단에 공식 주의 문구 박스(`.penetration-caution-box`)를 추가:
     > *"※ 침투율 비교는 소진공 공간 전수 점포(소진공 2026-07 공간 전수) 기준이며, 공정위 가맹본부 거시 공시(연간 실적)와는 집계 단위 및 대상 모집단이 다릅니다."*
   - 공정위 패널 푸터에도 개별 점포 실측치가 아님을 명시:
     > *"출처: 공정거래위원회 가맹사업정보제공시스템 (가맹본부 정기공시 정보공개서) | 집계단위: 전국 등록 가맹본부 거시 벤치마크 (개별 매장 실측치 아님)"*

---

## 3. API 응답 필드와 UI 뱃지/지표 간 1:1 대응표

| 대시보드 UI 컴포넌트 | 표시 지표 / 뱃지 문구 | 참조 API 엔드포인트 | 실제 매핑 필드 | 비고 |
| :--- | :--- | :--- | :--- | :--- |
| **상단 필터바** (`CategoryFilterBar`) | `소진공 2026-07 공간 전수` | `GET /api/v1/analytics/regions/{code}` | `meta.data_reference_month` | 결손 시 `소진공 기준월 확인 불가` |
| **상단 필터바** (`CategoryFilterBar`) | `공정위 2026년 등록 (2025년 결산) · 진행형 스냅샷` | `GET /api/v1/ftc/status` & `latest` | `benchmark_year`, `financial_year`, `is_snapshot` | 2026년 선택 시 동적 표시 |
| **상단 필터바** (`CategoryFilterBar`) | `공정위 2025년 등록 (2024년 결산) · 최신 완결 후보` | `GET /api/v1/ftc/benchmark/latest?year=2025` | `benchmark_year`, `financial_year`, `is_snapshot` | 2025년 선택 시 동적 표시 |
| **상태 요약 카드** (`MarketSummary`) | `소진공 2026-07 공간 전수` (우측 상단 뱃지) | `GET /api/v1/analytics/regions/{code}` | `meta.data_reference_month` | 점포 전수 센서스 출처 명시 |
| **듀얼 침투율 카드** (`MarketSummary`) | `지역: 323개 / 4,507개` | `GET /api/v1/analytics/regions/11215` | `franchise_stores`, `total_stores` | 광진구 기준 실측값 |
| **듀얼 침투율 카드** (`MarketSummary`) | `전국 기준 6.53%: 48,002 / 735,185` | `GET /api/v1/analytics/summary` | `franchise_stores`, `total_stores` | 전국 256개 시군구 분자/분모 |
| **지도 범례** (`MapContainer`) | `전체 외식 점포 밀집도 (소진공 2026-07)` | `App.jsx` 주입 prop | `meta.data_reference_month` | 지도 레이어 기준시점 명시 |
| **지도 마커 팝업** (`MapContainer`) | `소진공 (2026-07)` | `App.jsx` 주입 prop | `meta.data_reference_month` | 개별 점포 팝업 출처 |
| **공정위 벤치마크 헤더** (`FtcBenchmarkPanel`) | `2026년 등록 (2025년 결산)` | `GET /api/v1/ftc/benchmark/latest` | `data.benchmark_year`, `data.financial_year` | 등록연도 vs 결산연도 분리 |
| **공정위 벤치마크 뱃지** (`FtcBenchmarkPanel`) | `진행형 스냅샷` (Amber) | `GET /api/v1/ftc/status` | `is_snapshot == true` | 30% 미등록 결손 상태 알림 |
| **공정위 벤치마크 뱃지** (`FtcBenchmarkPanel`) | `최신 완결 후보 (공식마감 미확인)` (Teal) | `GET /api/v1/ftc/status` | `benchmark_year == 2025` | 행정 마감 전 후보 표기 |
| **추이 차트 태그** (`FtcBenchmarkPanel`) | `스냅샷` (Amber), `완결후보` (Teal) | 추이 데이터 루프 | `d.year === 2026`, `d.year === 2025` | 4개년 바 차트 연도별 태그 |
| **표본 수 스트립** (`FtcBenchmarkPanel`) | `전국 가맹사업망 10,230개 브랜드 / 371,114개 가맹점` | `GET /api/v1/ftc/status` | `total_registered_brands`, `total_franchise_stores` | 공정위 거시 표본 전수 |

---

## 4. 실 브라우저 CDP 전수 검증 결과 (100% 실측)

실제 구동 중인 프런트엔드(`http://127.0.0.1:5173`) 및 백엔드(`http://127.0.0.1:8000`) 환경에서 Chrome CDP(DevTools Protocol)를 연결하여 5개 시나리오 전수 자동화 검증을 완료하였습니다.

### 4.1 테스트 요약표

| 테스트 번호 | 검증 시나리오 및 조건 | 주요 검증 항목 | 실측 결과 | 판정 |
| :---: | :--- | :--- | :--- | :---: |
| **T1** | **광진구(`11215`) + 공정위 2026년 스냅샷** | SEDA 출처 배지, FTC 스냅샷 태그, 듀얼 침투율 수식, 지도 범례, 모집단 경고 박스 | - SEDA: `소진공 2026-07 공간 전수`<br>- FTC: `공정위 2026년 등록 (2025년 결산) · 진행형 스냅샷`<br>- 수식: `지역: 323개 / 4,507개 (전국 기준 6.53%: 48,002 / 735,185)`<br>- 경고문구: 정상 표출 | **PASS** |
| **T2** | **광진구(`11215`) + 공정위 2025년 수동 선택** | FTC 연도 전환, 최신 완결 후보 뱃지(`badge-candidate-teal`), 2024년 결산 표기 | - FTC: `공정위 2025년 등록 (2024년 결산) · 최신 완결 후보`<br>- 뱃지: `최신 완결 후보 (공식마감 미확인)`<br>- 2026 스냅샷 뱃지 미표출 확인 | **PASS** |
| **T3** | **제주시(`50110`) 선택 시 실측 검증** | 제주시 SEDA 2026-07 연동, 점포수(11,711개), 듀얼 침투율 분자/분모, 1,351개 격자 범례 | - 지역: `제주특별자치도 제주시 분석`<br>- 점포수: `11,711 개소`<br>- 공식침투율: `535개 / 11,711개 (4.57%)`<br>- 브랜드침투율: `1,244개 / 11,711개 (10.62%)`<br>- 범례: `100m 격자당 점포 수 (1,351개 격자)` | **PASS** |
| **T4** | **전국(`00`) 모드 집계 단위 및 기준선** | 전국 735,185개 점포 표본, 전국 기준선 모드(`전국 벤치마크 침투율 (기준선)`), 격차 뱃지 숨김 | - 지역: `전국 외식업 시장 분석`<br>- 전체 점포: `735,185 개소`<br>- 수식: `전국: 48,002개 / 735,185개 (6.53%)`<br>- 격차 뱃지: 0개 (자기 자신과의 불필요한 차이 숨김) | **PASS** |
| **T5** | **기준시점 결손 폴백 로직 검증** | `null`, `undefined`, `""` 등 비정상 값 주입 시 안전 동작 | - `null` 주입: `소진공 기준월 확인 불가`<br>- `undefined` 주입: `소진공 기준월 확인 불가`<br>- `""` 주입: `소진공 기준월 확인 불가`<br>- 임의 연도 생성 차단 확인 | **PASS** |

### 4.2 실제 브라우저 캡처 화면

1. **광진구(`11215`) + 공정위 2026 스냅샷**:
   - 파일: [phase5c_step2_gwangjin_2026.png](file:///D:/Franchise_Dashboard/reports/phase5c_step2_gwangjin_2026.png)
   - 브레인 아티팩트: `phase5c_step2_gwangjin_2026.png`
2. **광진구(`11215`) + 공정위 2025 최신 완결 후보**:
   - 파일: [phase5c_step2_gwangjin_2025.png](file:///D:/Franchise_Dashboard/reports/phase5c_step2_gwangjin_2025.png)
   - 브레인 아티팩트: `phase5c_step2_gwangjin_2025.png`
3. **제주시(`50110`) 선택 시 실제 11,711개 점포 및 1,351개 격자**:
   - 파일: [phase5c_step2_jeju_2025.png](file:///D:/Franchise_Dashboard/reports/phase5c_step2_jeju_2025.png)
   - 브레인 아티팩트: `phase5c_step2_jeju_2025.png`
4. **전국(`00`) 모드 735,185개 점포 기준선 표출**:
   - 파일: [phase5c_step2_nationwide.png](file:///D:/Franchise_Dashboard/reports/phase5c_step2_nationwide.png)
   - 브레인 아티팩트: `phase5c_step2_nationwide.png`

---

## 5. 수정 파일 목록 및 불변 검증

### 5.1 수정된 프런트엔드 파일 (7개)
1. `frontend/src/App.jsx`:
   - `sedaReferenceMonth` 및 `sedaProvenanceText` 계산 로직 추가
   - 하위 컴포넌트(`CategoryFilterBar`, `MarketSummary`, `MapContainer`, `FtcBenchmarkPanel`)로 메타 및 출처 정보 주입
2. `frontend/src/components/Header.jsx`:
   - 헤더 부제목을 최신 전국 256개 시군구 전수 및 공정위 벤치마크 기준으로 최신화
3. `frontend/src/components/CategoryFilterBar.jsx`:
   - 고정 문구 제거 및 `sedaText`, `ftcTag` 동적 배지 생성 로직 적용
4. `frontend/src/components/MarketSummary.jsx`:
   - 상단 뱃지 동적 표기 및 전국/지역 모드별 제목·수식 레이블 분기
   - 듀얼 침투율 하단 모집단 분리 주의 문구(`penetration-caution-box`) 추가
5. `frontend/src/components/FtcBenchmarkPanel.jsx`:
   - 2026 진행형 스냅샷 및 2025 최신 완결 후보 뱃지 분기
   - 4개년 바 차트에 연도별 스냅샷/완결후보 태그 및 명목금액/모집단 결손 캡션 추가
   - 푸터 출처 및 가맹본부 거시 벤치마크(개별 매장 실측치 아님) 명시
6. `frontend/src/components/MapContainer.jsx`:
   - 지도 범례 및 점포 팝업 타이틀에 소진공 기준월 동적 표기
7. `frontend/src/index.css`:
   - 신규 뱃지(`.tag-ftc-snapshot`, `.tag-ftc-candidate`, `.tag-ftc-fallback`, `.tag-unverified`, `.badge-snapshot-amber`, `.badge-candidate-teal`, `.penetration-caution-box`) 디자인 토큰 정의

### 5.2 신규 작성된 검증 스크립트 (1개)
- `scratch/test_phase5c_step2_cdp.mjs`: Chrome DevTools Protocol 기반 5개 시나리오 자동 검증 및 스크린샷 캡처 스크립트

### 5.3 기존 자산 보존 확인 (100% 무변경)
- **SQLite DB (16개 전체)**: `gangnam_food_stores.sqlite3`, `nationwide_food_stores_v2.sqlite3`, `brand_master_v1.sqlite3`, `ftc_macro_statistics_v1.sqlite3`, `franchise_analytics_v1.sqlite3` 등 파일 수정 시각 및 바이너리 변경 없음.
- **Python 백엔드**: `src/stage4e/api/` 및 수집 스크립트 일체 변경 없음.
- **기존 보고서 및 업종분류 체계**: 8대 대분류 및 48개 중분류 정의 무변경 유지.

---

## 6. 남은 위험 요소 및 향후 제약사항

1. **공정위 2026년 가맹본부 미등록 결손 위험**:
   - 2026년 공정위 데이터는 공정거래위원회가 정기 공시를 접수 중인 진행형 스냅샷입니다. 약 30%의 가맹본부가 아직 정보공개서를 최종 제출하지 않았으므로, 2025년 대비 단순 시계열 성장률을 계산할 경우 심각한 왜곡이 발생합니다.
   - 대책: UI에 앰버 뱃지 및 직접 비교 불가 캡션을 유지하고, 전년 대비 증감률(YoY)을 강제로 계산하지 않습니다.
2. **소진공 점포 센서스와 공정위 가맹사업 공시의 집계 시점 불일치**:
   - 소진공 점포 데이터는 **2026년 7월 공간 시점의 개별 매장 인허가/영업 상태**이며, 공정위 2025년 데이터는 **2024년 12월 말 기준 가맹본부의 연간 결산 실적**입니다.
   - 대책: 본 단계에서 추가된 `.penetration-caution-box` 및 푸터 주석을 유지하여 사용자가 두 지표의 기준시점과 모집단이 다름을 상시 인지하도록 합니다.
3. **API 백엔드 변경 불필요 확인**:
   - 현 단계의 출처 정합화는 기존 `/api/v1/analytics/regions/{code}`, `/api/v1/analytics/summary`, `/api/v1/ftc/status` 응답 필드로 100% 수용 가능하여 백엔드 수정 없이 안전하게 완료되었습니다.

---

## 7. 결론 및 승인 대기

Phase 5C Step 2의 모든 구현 및 실 브라우저 CDP 검증이 성공적으로 완료되었습니다.
**`AGENTS.md` 지침에 따라, 사용자의 공식 확인 및 승인 전까지 Phase 5C Step 3(다음 단계)로 임의 진행하지 않고 현 상태에서 작업을 중단하고 대기합니다.**
