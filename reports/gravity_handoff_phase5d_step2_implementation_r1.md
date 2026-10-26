# Gravity 전달용 작업지시서 — Phase 5D Step 5D-2 구현

> **Gravity에는 이 문서 전체를 그대로 전달한다.**  
> 승인된 수정계획 범위만 구현하고 검증한다. 범위 밖 기능은 추가하지 않는다.

## 1. 승인된 기준 문서

작업 전에 다음 문서를 순서대로 읽는다.

1. `reports/phase5d_step2_semantic_safety_remediation_plan_r1.md`
2. `reports/phase5d_step1_r3_final_review.md`
3. `reports/phase5d_step1_semantic_audit_r3.json`

`phase5d_step2_semantic_safety_remediation_plan_r1.md`의 범위와 인수 기준을 구현 기준으로 사용한다.

## 2. 구현 목표

공정위 전국 업종 벤치마크 수치가 선택 지역 또는 특정 브랜드의 실적으로 오인되지 않도록 최소한의 문구와 정보 배치를 수정한다.

## 3. 수정 허용 파일

- `frontend/src/components/FtcBenchmarkPanel.jsx`
- `frontend/src/index.css`
- `scratch/verify_phase5d_step2_semantic_safety.mjs` 신규 생성
- Step 5D-2 실행·품질·원시 측정·화면 캡처 산출물

`App.jsx`는 현재 props만으로 업종명이 전달되지 않는 것이 실제로 확인된 경우에만 수정할 수 있다. 수정이 필요하지 않으면 건드리지 않는다.

## 4. 필수 구현

### 4.1 데스크톱 및 공통

1. 히어로 대표 라벨을 `전국 가맹본부 대표매출 (중앙값)`으로 변경한다.
2. 히어로 수치 근처 첫 화면에 다음 의미의 안내를 상시 표시한다.
   - 전국 선택 업종 기준
   - 공정위 가맹본부 거시 통계
   - 특정 브랜드 또는 개별 점포 실적이 아님
3. 2026년 선택 시 다음 경고를 호버 없이 표시한다.
   - 진행형 스냅샷
   - 약 30% 미등록 결손
   - 2025년과 직접 비교 불가

### 4.2 모바일 피크

1. 공정위 버튼을 눌러 나타나는 피크 바에 다음 의미를 포함한다.
   - `공정위`
   - `전국`
   - `업종 참고치`
2. 수치는 억 단위로 축약할 수 있다.
3. 390px 폭에서 한 줄과 기존 높이를 유지한다.
4. 필수 의미가 ellipsis에 의해 잘리지 않도록 실제 표시 문자열을 검사한다.

### 4.3 모바일 확장

1. 확장 첫 화면에 출처·전국 모집단·브랜드 비귀속 안내를 표시한다.
2. 안내문은 스크롤 전 390×844 뷰포트에서 실제로 보여야 한다.
3. 기존 대표 수치와 주요 비교 바가 불필요하게 화면 밖으로 밀리지 않도록 한다.

## 5. 수정 금지

- 좌측 패널 높이·스크롤·Top 5 배치 변경
- Top 5와 FTC 패널 강제 동시 노출
- 모바일 FTC 패널 자동 열기
- 모바일 초기 수납 제거
- 공정위 버튼의 불필요한 확대
- 전년비 UI 추가
- 백엔드 API·Pydantic 스키마·SQLite 변경
- 수집 및 브랜드 매칭 로직 변경
- 신규 npm 의존성 추가
- 보호 파일 3종 수정

## 6. 구현 전후 무결성

작업 전에 다음 파일의 SHA-256, 크기, 수정 시각을 기록하고 작업 후 대조한다.

- `collector.py`
- `gangnam_food_stores.sqlite3`
- `run_gangnam.bat`

API·DB·보호 파일 변경은 0건이어야 한다.

## 7. 필수 검증

### 시나리오

1. 1440×900 전국·카페·2024
2. 1440×900 광진구·치킨·2024
3. 1440×900 전국·한식·2026
4. 390×844 전국·한식·2024 피크
5. 390×844 전국·한식·2024 확장
6. 390×844 광진구·카페·2024 피크
7. 키보드로 공정위 버튼 열기, 피크 확장/축소, ESC 닫기
8. 390×844 문서 가로 오버플로 0

### 실제 가시성

R3 감사의 조상 clipping 포함 `isActuallyVisible` 판정 함수를 재사용한다. DOM에 존재하는 것만으로 PASS 처리하지 않는다.

다음을 원시 JSON에 기록한다.

- 요청 및 실제 지역·업종·연도
- 패널 상태
- 핵심 안내 문자열
- element rect
- viewport rect
- clipping ancestors
- visible intersection
- isActuallyVisible
- document scrollWidth 및 viewport width

### 빌드

- `frontend` 프로덕션 빌드 성공
- 빌드 오류 0건
- 기존 번들 크기 경고는 수치만 기록하고 이번 범위에서 분할하지 않는다.

## 8. 인수 기준

- 데스크톱 히어로에 `전국` 문구가 실제 노출됨
- `특정 브랜드 또는 개별 점포 실적 아님` 의미가 첫 화면에 노출됨
- 2026 경고가 호버 없이 노출됨
- 모바일 피크에 `공정위`, `전국`, `업종 참고치`가 실제로 보임
- 모바일 확장 첫 화면에 출처·모집단·비귀속 안내가 보임
- 모바일 가로 오버플로 0
- 모바일 초기 수납과 지도 비차폐 유지
- 키보드 동작 회귀 없음
- 좌측 패널 변경 0건
- API·DB 변경 0건
- 보호 파일 해시 불변
- JSON·PNG·보고서 판정 불일치 0건

## 9. 필수 산출물

- `reports/phase5d_step2_execution_report.md`
- `reports/phase5d_step2_quality_report.md`
- `reports/phase5d_step2_validation.json`
- 시나리오 1~6 캡처 PNG 6종 이상
- 키보드 접근성 증빙 캡처 또는 원시 이벤트 결과
- `scratch/verify_phase5d_step2_semantic_safety.mjs`

기존 Step 5D-1 및 R1/R2/R3 산출물은 덮어쓰지 않는다.

## 10. 종료 조건

구현과 검증 산출물을 제출한 뒤 중단한다. Step 5D-3 또는 전년비 UI에는 착수하지 말고 사용자 승인과 재검증을 기다린다.
