# Gravity 전달용 작업지시서 — Phase 5D R2 Step 5D-1 R3

> **Gravity에는 이 문서 전체를 그대로 전달한다.**  
> 본 작업은 감사 스크립트와 보고서 정정만 수행한다. 애플리케이션 기능 코드는 수정하지 않는다.

## 1. 작업 목적

Phase 5D R2 Step 5D-1 재감사 R2 결과에서 데스크톱 A·B·D는 정상 확인됐지만, C·E·F·G는 화면 밖 또는 비가시 요소를 PASS로 잘못 판정했다.

이번 R3 작업의 목적은 다음 두 가지다.

1. 감사 스크립트의 실제 가시성 assertion을 바로잡는다.
2. C·E·F·G만 다시 실행하여 실제 화면 노출 여부를 확정한다.

## 2. 반드시 먼저 읽을 문서

1. `reports/phase5d_ftc_semantic_safety_plan_r2.md`
2. `reports/phase5d_step1_semantic_audit_r2_verification.md`
3. `reports/phase5d_step1_semantic_audit_r2.json`
4. `scratch/audit_phase5d_step1_semantic_safety_r2.mjs`

위 문서와 원시 JSON을 확인하지 않고 작업을 시작하지 마라.

## 3. 현재 검증 판정

| 시나리오 | 현재 판정 | 조치 |
|---|---|---|
| A. 데스크톱 전국·카페·2024 | PASS | 재실행 불필요, 기존 근거 보존 |
| B. 데스크톱 광진구·치킨·2024 | PASS | 재실행 불필요, 기존 근거 보존 |
| C. Top 5 브랜드와 FTC 동시 노출 | FAIL | R3 재측정 |
| D. 데스크톱 전국·한식·2026 | PASS | 재실행 불필요, 기존 근거 보존 |
| E. 모바일 축소 피크 | FAIL | R3 재측정 |
| F. 모바일 확장 | FAIL | R3 재측정 |
| G. 모바일 광진구·카페 피크 | FAIL | R3 재측정 |

## 4. 확인된 R2 오류

### 오류 1 — 모바일 피크 바가 화면 밖인데 PASS 처리

```text
CSS 뷰포트 높이: 844px
피크 바 top: 845px
피크 바 bottom: 888px
viewportIntersection: false
isActuallyVisible: false
```

R2 스크립트는 `height > 0`만으로 `peekVisibleOk: true`를 만들었다. 크기가 있어도 화면 밖이면 보이지 않으므로 잘못된 assertion이다.

### 오류 2 — 모바일 확장 클래스만 확인

`mobile-expanded` 클래스는 존재하지만 히어로가 `top: 924px`에서 시작하여 844px 뷰포트 밖에 있었다. 클래스 상태가 아니라 실제 패널 콘텐츠 노출을 검사해야 한다.

### 오류 3 — 브랜드와 FTC 동시 노출 미입증

시나리오 C 원시 JSON에서 FTC 히어로는 `isActuallyVisible: false`였다. 캡처에서도 메가MGC커피 Top 5 행을 확인하기 어렵다.

### 오류 4 — overflow clipping 미검사

요소의 좌표가 뷰포트 안이어도 상위 컨테이너의 `overflow: hidden/auto` 영역 밖이면 실제로 보이지 않는다. 현재 helper는 이 조건을 검사하지 않는다.

## 5. 작업 범위

### 수정 허용

- `scratch/audit_phase5d_step1_semantic_safety_r3.mjs` 신규 생성
- R3 원시 JSON 신규 생성
- R3 캡처 신규 생성
- R3 실행보고서 및 품질검증보고서 신규 생성

### 수정 금지

- `frontend/src/**`
- `src/**`
- `frontend/package.json`
- SQLite DB 전체
- API 및 수집 파이프라인
- `collector.py`
- `gangnam_food_stores.sqlite3`
- `run_gangnam.bat`
- 기존 R1/R2 감사 파일과 캡처 덮어쓰기
- Step 5D-2 UI/CSS 수정 착수

## 6. 감사 스크립트 R3 필수 수정사항

### 6.1 실제 가시성 함수

요소는 다음 조건을 모두 만족할 때만 `isActuallyVisible: true`로 판정한다.

1. 요소가 존재함
2. `display !== 'none'`
3. `visibility !== 'hidden'`
4. `Number(opacity) > 0`
5. `rect.width > 0 && rect.height > 0`
6. `rect.left < window.innerWidth`
7. `rect.right > 0`
8. `rect.top < window.innerHeight`
9. `rect.bottom > 0`
10. 닫힌 드로어 내부가 아님
11. 축소 바텀시트에서 허용된 피크 핸들 외부가 아님
12. 모든 조상 요소의 clipping 영역과 실제로 교차함

조상 요소의 `overflow`, `overflowX`, `overflowY`가 `hidden`, `clip`, `auto`, `scroll`이면 해당 조상의 bounding rect와 요소 rect의 교차 영역을 계산하라. 교차 너비 또는 높이가 0이면 비가시로 판정한다.

원시 JSON에는 다음을 기록한다.

- `elementRect`
- `viewportRect`
- `visibleIntersectionRect`
- `clippingAncestors`
- `display`
- `visibility`
- `opacity`
- `viewportIntersection`
- `notClippedByAncestor`
- `isActuallyVisible`

### 6.2 캡처 전 공통 assertion

각 캡처 직전에 아래 조건을 검사한다.

- 요청 지역 값 일치
- 요청 업종 `aria-selected=true`
- 요청 공정위 연도 값 일치
- 화면 배지 연도 일치
- 대상 패널 상태 일치
- 캡처하려는 핵심 요소의 `isActuallyVisible=true`

하나라도 실패하면:

- 정상 캡처로 기록하지 마라.
- 실패 상태 캡처는 `_failure.png`로 저장하라.
- 시나리오를 FAIL로 기록하라.
- 다음 시나리오 진행은 가능하지만 전체 판정은 FAIL로 유지하라.

## 7. R3 재실행 시나리오

### C — 지역 Top 5 브랜드와 FTC 패널 동시 노출

- 뷰포트: 1440×900
- 지역: 서울특별시 광진구(11215)
- 업종: 카페·음료(CAT_MAJ_07)
- 공정위 연도: 2024
- FTC 드로어: 열림

필수 assertion:

- 좌측 Top 5의 메가MGC커피 행 `isActuallyVisible=true`
- 우측 FTC 히어로 라벨 `isActuallyVisible=true`
- 우측 FTC 대표 수치 `isActuallyVisible=true`
- 세 요소가 동일 캡처에 육안 식별 가능

현재 레이아웃에서 동시에 보이지 않으면 화면 스크롤로 억지 조정하지 말고 `동시 노출 불가`로 기록하라. 이는 제품 정보구조의 실제 상태다.

### E — 모바일 축소 피크

- CSS 뷰포트: 정확히 390×844
- 지역: 전국(00)
- 업종: 한식(CAT_MAJ_01)
- 공정위 연도: 2024
- 상태: 모바일 축소

필수 assertion:

- `window.innerWidth === 390`
- `window.innerHeight === 844`
- 피크 바 전체 또는 유효 영역이 뷰포트와 교차
- 피크 바 `isActuallyVisible=true`
- PNG의 하단에서 피크 문구를 육안 확인 가능

피크 바가 다시 `top >= 844`이면 시나리오 FAIL이며, `모바일 피크 화면 밖 배치 결함`으로 확정하라.

### F — 모바일 확장

- E와 동일한 지역·업종·연도
- 실제 피크 바 클릭으로 확장

필수 assertion:

- `mobile-expanded=true`
- 패널 헤더 또는 히어로가 `isActuallyVisible=true`
- 패널의 visible intersection height가 44px 이상
- PNG에서 확장 패널을 육안 확인 가능

클래스만 변경되고 콘텐츠가 화면 밖이면 FAIL로 판정하고 `모바일 확장 패널 화면 밖 배치 결함`으로 확정하라.

### G — 모바일 광진구·카페 피크

- CSS 뷰포트: 정확히 390×844
- 지역: 서울특별시 광진구(11215)
- 업종: 카페·음료(CAT_MAJ_07)
- 공정위 연도: 2024
- 상태: 모바일 축소

필수 assertion:

- 시도 값 `11`
- 시군구 값 `11215`
- 카페·음료 선택 상태
- 공정위 연도 `2024`
- 피크 바 `isActuallyVisible=true`
- PNG 하단에서 카페·음료 피크 문구 확인 가능

## 8. 모바일 에뮬레이션 기록

다음 값을 원시 JSON에 반드시 기록한다.

- CDP device metrics 요청값
- `window.innerWidth`, `window.innerHeight`
- `window.devicePixelRatio`
- PNG 실제 픽셀 너비·높이
- CSS 픽셀과 이미지 픽셀의 배율

`deviceScaleFactor: 3`이면 PNG가 1170×2532인 것은 정상일 수 있으나, 판단 기준은 CSS 뷰포트 390×844와 요소 bounding rect다.

## 9. 보고서 표현 정정 규칙

- `모든 시나리오 완벽히 통과` 같은 표현을 사용하지 마라.
- 원시 JSON에서 `isActuallyVisible=false`인 요소를 화면 노출로 서술하지 마라.
- 사용자 시험 없이 `오인 확률 100%`, `대다수 사용자가`, `모바일 사용자의 70%` 같은 수치를 사용하지 마라.
- 관측 결과는 `오인 가능성이 있음/높음`으로 제한한다.
- 자동화 도구가 확인한 사실과 분석자의 해석을 구분한다.

## 10. 필수 산출물

- `scratch/audit_phase5d_step1_semantic_safety_r3.mjs`
- `reports/phase5d_step1_semantic_audit_r3.json`
- `reports/phase5d_step1_execution_report_r3.md`
- `reports/phase5d_step1_quality_report_r3.md`
- `reports/phase5d_step1_audit_r3_desktop_brand_coexistence.png` 또는 `_failure.png`
- `reports/phase5d_step1_audit_r3_mobile_peek.png` 또는 `_failure.png`
- `reports/phase5d_step1_audit_r3_mobile_expanded.png` 또는 `_failure.png`
- `reports/phase5d_step1_audit_r3_mobile_regional.png` 또는 `_failure.png`
- 보호 파일 3종 해시 대조 결과
- 애플리케이션 코드 무수정 확인 결과

## 11. 최종 판정 기준

### Step 5D-1 완료 가능

- A·B·D 기존 PASS 근거 유지
- C·E·F·G의 핵심 요소 `isActuallyVisible=true`
- PNG 육안 결과와 JSON 가시성 판정 일치
- 보고서 수치와 JSON 불일치 0건
- 코드·CSS·API·DB 변경 0건

### 제품 결함 확정 후 감사 완료 가능

올바른 조작과 측정에도 E·F·G가 화면 밖이면, 이를 억지로 PASS시키지 말고 다음처럼 판정한다.

- 감사 실행 자체: PASS
- 제품 의미 안전성/모바일 레이아웃: FAIL
- 확인 결함: 모바일 FTC 피크/확장 패널 화면 밖 배치
- 다음 단계: 사용자 승인 후 Step 5D-2에서 레이아웃과 의미 문구를 함께 수정

즉, 제품 결함 발견은 감사 실패가 아니다. **측정과 보고가 원시 사실과 일치하면 감사는 완료된 것**이다.

## 12. 작업 종료 조건

산출물 작성 후 사용자에게 결과만 제출하고 중단한다. Step 5D-2 코드를 수정하지 말고 명시적 승인을 기다린다.
