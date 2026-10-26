# Phase 5D Step 5D-2 의미 안전성 최소 수정계획서 (R1)

> **문서 상태**: 계획 수립 완료 (사용자 승인 대기)  
> **기준 감사**: Phase 5D Step 5D-1 R3 감사 결과 ([`reports/phase5d_step1_semantic_audit_r3.json`](file:///d:/Franchise_Dashboard/reports/phase5d_step1_semantic_audit_r3.json))  
> **선행 검증 의견**: [`reports/phase5d_step1_r3_final_review.md`](file:///d:/Franchise_Dashboard/reports/phase5d_step1_r3_final_review.md)  
> **수정 원칙**: 최소 침습(Minimal Invasive), 코드 동결 유지, 명시적 제외 준수  

---

## 1. 수정 목적 및 배경

Step 5D-1 R3 감사 결과, 대시보드 화면상에서 공정거래위원회 가맹사업 통계 데이터가 **선택된 지역(시군구)의 점포 평균이나 특정 브랜드(메가MGC커피 등)의 자체 실적으로 오인될 수 있는 5대 의미론적 결함**이 확인되었습니다.

본 계획서는 기존 대시보드의 지도 가시 면적, 모바일 초기 수납 구조, 좌측 요약 패널 스크롤 레이아웃을 그대로 보존하면서, **공정위 벤치마크 패널 내의 문구 및 첫 화면(Above the Fold) 안내 배치를 정밀 교정**하여 의미 안전성을 확보하는 **Step 5D-2 최소 수정 작업 명세**를 정의합니다.

---

## 2. 수정 전/후 UI 및 문구 대조표

| 구분 | 대상 영역 | 현행 (수정 전) | 개선 (수정 후) | 개선 목적 및 의미 안전성 효과 |
| :--- | :--- | :--- | :--- | :--- |
| **공통/데스크톱** | 히어로 대표 라벨 | `가맹점 연간 대표매출 (중앙값)` | **`전국 가맹본부 대표매출 (중앙값)`** | 지역 모드(광진구 등) 탐색 시에도 수치의 전국 거시 맥락을 즉각 전달 |
| **공통/데스크톱** | 히어로 첫 화면 비귀속 안내 | *(문구 전무)* | **`* 전국 {업종명} 등록 가맹본부 기준 거시 지표이며, 특정 브랜드나 개별 점포의 실적이 아닙니다.`** | 메가MGC커피 등 특정 브랜드 고유 실적으로의 오독을 근본적으로 차단 |
| **공통/데스크톱** | 2026 스냅샷 주의사항 | 배지 `진행형 스냅샷` (설명은 HTML `title` 툴팁 및 최하단 각주에만 존재) | **인라인 앰버 콜아웃 상시 렌더링**:<br>`⚠️ 진행형 스냅샷: 2026년은 정기공시 진행 중(약 30% 미등록 결손)으로 2025년과 직접 비교가 불가합니다.` | 마우스 호버가 불가능한 터치/키보드 환경에서도 데이터 한계점을 즉시 인지 |
| **모바일** | 축소 피크 바 (43px) | `🍚 한식 중위매출 33,061만원 2024년 등록 (2023년 결산) ▲ 차트/상세 ✕` | **`[공정위 전국] 🍚 한식 중위 3.31억 (업종 참고치) ▲`** | 43px 콤팩트 공간 내에 `공정위`, `전국`, `업종 참고치` 3대 핵심 맥락 압축 노출 |
| **모바일** | 확장 패널 첫 화면 (Above the Fold) | 첫 844px 화면에 수치만 보이고, 출처/면책 고지는 701px 아래 매몰 | **패널 상단 콤팩트 공지 배너 상시 배치**:<br>`📌 출처: 공정위 가맹사업공시 · 전국 가맹본부 거시 벤치마크 (개별 매장·브랜드 실측치 아님)` | 스크롤 없이도 첫 뷰포트에서 출처와 브랜드 비귀속성을 즉시 확인 가능 |

---

## 3. 예상 수정 위치 및 코드 변경 상세 명세

수정 대상 파일은 정확히 **2개**입니다. 백엔드 API, 데이터베이스, 지도 엔진, 좌측 패널 등은 일절 수정하지 않습니다.

### 3.1 `frontend/src/components/FtcBenchmarkPanel.jsx`

#### 1) 모바일 축소 피크 바 문구 정밀 개편 (Line 345~361 부근)
- **목적**: 43px 높이 내에서 가로 오버플로 없이 `공정위`, `전국`, `업종 참고치` 3대 키워드를 콤팩트하게 수용.
- **예상 코드 diff**:
```diff
         <div className="mobile-summary-row">
+          <span className="mobile-summary-tag">공정위 전국</span>
           <span className="mobile-summary-cat" style={{ color: themeColor }}>
             {categoryInfo?.icon} {data.category_major_name}
           </span>
           <span className="mobile-summary-kpi">
-            중위매출 <strong>{formatManwonOnly(sales.median_sales_thousand_krw)}</strong>
+            중위 <strong>{formatEokShort(sales.median_sales_thousand_krw)}</strong>
           </span>
+          <span className="mobile-summary-sub">(업종 참고치)</span>
           <span className="mobile-summary-badge">
             {data.is_fallback_applied 
               ? `${data.benchmark_year}년 대체` 
               : data.benchmark_year === '2026'
-                ? `${data.benchmark_year}년 스냅샷 (${finYearText})`
-                : `${data.benchmark_year}년 등록 (${finYearText})`}
+                ? `${data.benchmark_year} 스냅샷`
+                : `${data.benchmark_year} 등록`}
           </span>
```

#### 2) 모바일 확장 패널 첫 화면 출처/면책 배너 신설 (Line 437 부근)
- **목적**: 모바일 확장 시 첫 844px 뷰포트 내에 출처와 비귀속 안내를 최상단에 상시 노출.
- **예상 코드 diff**:
```diff
       {!isCollapsed && (
         <div className="panel-body">
+          {/* 모바일 확장 시 첫 화면 즉각 인지용 콤팩트 출처/비귀속 배너 */}
+          <div className="mobile-first-screen-notice mobile-only" role="note">
+            <span className="notice-icon">📌</span>
+            <span>공정위 정기공시 전국 가맹본부 거시 벤치마크 (개별 점포·특정 브랜드 실적 아님)</span>
+          </div>
```

#### 3) 2026년 진행형 스냅샷 인라인 경고 콜아웃 신설 (Line 450 부근)
- **목적**: 마우스 호버(title 툴팁)에 의존하지 않고 첫 화면 본문에 결손 및 전년 비교 불가 경고 상시 가시화.
- **예상 코드 diff**:
```diff
+          {/* 2026년 진행형 스냅샷 인라인 경고 콜아웃 (호버 불필요, 상시 가시) */}
+          {data.benchmark_year === '2026' && (
+            <div className="snapshot-inline-alert" role="alert">
+              <span className="alert-icon">⚠️</span>
+              <div className="alert-content">
+                <strong>진행형 스냅샷:</strong> 2026년은 정기공시 진행 중(약 30% 미등록 결손)으로 2025년과 직접 비교가 불가합니다.
+              </div>
+            </div>
+          )}
```

#### 4) 히어로 카드 대표 라벨 및 브랜드 비귀속 상시 안내문 추가 (Line 464~475 부근)
- **목적**: 대표 매출 라벨에 '전국' 명시 및 히어로 카드 하단에 상시 비귀속 안내 배치.
- **예상 코드 diff**:
```diff
           <section className="visual-hero-section" aria-label="대표 가맹점 연간 매출액">
             <div className="hero-top-row">
-              <span className="hero-label">가맹점 연간 대표매출 (중앙값)</span>
+              <span className="hero-label">전국 가맹본부 대표매출 (중앙값)</span>
               <span className="hero-tag" style={{ borderColor: themeColor, color: themeColor }}>1순위 대표</span>
             </div>
             
             <div className="hero-main-stat">
               <span className="hero-stat-number" style={{ color: themeColor }}>
                 {formatCurrency(sales.median_sales_thousand_krw)}
               </span>
             </div>
+
+            {/* 특정 브랜드 및 지역 점포 비귀속 상시 안내문 */}
+            <div className="hero-scope-disclaimer">
+              * 전국 {data.category_major_name} 등록 가맹본부 기준 거시 통계이며, 특정 브랜드나 개별 점포의 실적이 아닙니다.
+            </div>
```

---

### 3.2 `frontend/src/index.css`

#### 1) 모바일 피크 바 콤팩트 스타일링 (가로 오버플로 0 보장)
- 피크 바 내부 요소들의 `font-size`, `padding`, `gap`을 정밀 조정하여 390px 뷰포트에서 줄바꿈 없이 한 행 안착 보장.
- `.mobile-summary-tag`: 폰트 크기 `0.68rem`, 패딩 `2px 5px`, 둥근 모서리, 배경색 및 테두리 미세 강조.
- `.mobile-summary-sub`: 폰트 크기 `0.68rem`, 색상 `var(--text-muted)`.

#### 2) 모바일 첫 화면 콤팩트 공지 배너 스타일링
- `.mobile-first-screen-notice`:
  - 배경색: `#f8fafc` (다크모드/라이트모드 조화), 테두리: `1px solid var(--border-subtle)`
  - 패딩: `6px 10px`, 마진 바텀: `8px`, 폰트 크기: `0.72rem`, 줄간격: `1.3`
  - 디스플레이: 데스크톱에서는 `display: none !important`, 모바일(`@media (max-width: 768px)`)에서는 `display: flex !important`.

#### 3) 2026 스냅샷 인라인 경고 콜아웃 스타일링
- `.snapshot-inline-alert`:
  - 배경색: `#fffbeb` (경고 앰버 톤), 테두리: `1px solid #fde68a`, 텍스트: `#92400e`
  - 패딩: `8px 12px`, 마진 바텀: `10px`, 폰트 크기: `0.76rem`, 둥근 모서리 `6px`
  - 조명 및 시각적 대비 확보 (WCAG 2.1 AA 명도 대비 4.5:1 이상 충족).

#### 4) 히어로 카드 비귀속 안내문 스타일링
- `.hero-scope-disclaimer`:
  - 폰트 크기: `0.72rem`, 색상: `var(--text-muted)` (#64748b)
  - 마진 탑: `6px`, 줄간격: `1.35`, 텍스트 정렬: `left`

---

## 4. 명시적 제외 사항 (Scope Exclusions)

작업지시서 및 최종 검증 의견에 따라 다음 항목은 수정 대상에서 **완전히 배제**합니다.

| 제외 항목 | 제외 사유 및 설계 의도 |
| :--- | :--- |
| **좌측 패널 높이 확장 및 Top 5 기본 노출** | 대시보드 화면 공간상 지도 영역을 보존하고 패널 스크롤 구조를 유지해야 함. FTC 패널 문구 자체가 독립적으로 안전해지면 억지 동시 노출이 불필요함. |
| **좌측 Top 5와 FTC 패널의 억지 화면 재배치** | 제품의 기존 3단 정보구조(필터바 - 지도/지역요약 - FTC벤치마크)를 훼손하지 않음. |
| **모바일 FTC 패널 자동 열기** | 모바일 초기 접속 시 지도를 가리지 않고 공간을 탐색할 수 있도록 한 기존 의도를 엄격히 보존함. |
| **모바일 초기 수납 구조 제거** | 바텀시트가 닫힌 상태로 시작하는 것은 정상이므로, 상단 버튼을 통해 사용자가 원할 때 여는 구조를 유지함. |
| **공정위 버튼의 불필요한 확대/신규 내비게이션** | 현행 44px 터치 규격 및 탭 구조를 유지함. |
| **전년비 UI 구현** | 본 단계는 의미 안전성 감사 및 문구 교정 단계이며, 전년비 복합 시각화는 별도 단계 과제임. |
| **백엔드 API 및 SQLite DB 변경** | 프론트엔드 표현 계층(UI/CSS)의 수정으로 100% 해결 가능하므로 데이터 파이프라인 불변 유지. |
| **외부 신규 라이브러리/의존성 추가** | 바닐라 CSS 및 기존 리액트 구조만을 활용하여 번들 크기 및 복잡도 증가 방지. |

---

## 5. 필수 8대 검증 시나리오 및 검증 방법

수정 완료 후 `scratch/verify_phase5d_step2_semantic_safety.mjs` 검증 스크립트를 작성하여 다음 8대 시나리오를 전수 실측 검증합니다.

| 번호 | 검증 시나리오 | 검증 조건 | 필수 Assertion 및 실측 항목 |
| :---: | :--- | :--- | :--- |
| **1** | 데스크톱 전국·카페·2024 | 1440×900 / 전국(00) / 카페 / 2024 | - 히어로 라벨: `전국 가맹본부 대표매출 (중앙값)` 일치<br>- 히어로 하단 비귀속 안내문 `isActuallyVisible: true` |
| **2** | 데스크톱 광진구·치킨·2024 | 1440×900 / 광진구(11215) / 치킨 / 2024 | - 지역 선택 중에도 히어로 라벨에 `전국 가맹본부` 명시 확인<br>- 광진구 점포 평균으로의 오인 차단 확인 |
| **3** | 데스크톱 전국·한식·2026 | 1440×900 / 전국 / 한식 / 2026 | - 인라인 앰버 경고 박스 `isActuallyVisible: true`<br>- 툴팁 호버 없이 결손/비교불가 문구 본문 노출 확인 |
| **4** | 모바일 전국·한식·2024 피크 | 390×844 / 전국 / 한식 / 2024 / 축소 | - 공정위 버튼 클릭 후 피크 바 `top: 781px` 안착 확인<br>- 피크 텍스트에 `공정위`, `전국`, `업종 참고치` 3개 키워드 포함 확인 |
| **5** | 모바일 전국·한식·2024 확장 | 390×844 / 전국 / 한식 / 2024 / 확장 | - 피크 클릭 후 패널 확장 확인<br>- 첫 844px 화면 내 콤팩트 공지 배너 `isActuallyVisible: true` 확인 |
| **6** | 모바일 광진구·카페·2024 피크 | 390×844 / 광진구 / 카페 / 2024 / 축소 | - 피크 바에 `[공정위 전국]` 접두어 노출 확인<br>- 광진구 카페 매출로의 오인 차단 확인 |
| **7** | 키보드 접근성 검증 | 데스크톱 및 모바일 | - 키보드 Tab 및 Enter/Space로 공정위 버튼 열기, 피크 바 확장/축소, ESC 닫기 정상 작동 확인 |
| **8** | 모바일 가로 오버플로 검증 | 390×844 뷰포트 | - `document.documentElement.scrollWidth <= 390` (가로 스크롤/오버플로 0px) 검증 |

---

## 6. 잠재적 회귀 위험 및 완화 대책

1. **모바일 피크 바 텍스트 길이 증가로 인한 줄바꿈/높이 초과 위험**:
   - **위험**: 390px 폭에서 문구가 길어지면 43px 높이를 초과하여 줄바꿈이 발생할 수 있음.
   - **완화 대책**: `중위매출 33,061만원`을 `중위 3.31억`으로 축약하고, 불필요한 공백을 제거하며 `white-space: nowrap` 및 `text-overflow: ellipsis`를 적용하여 43px 1행을 철저히 유지.
2. **모바일 확장 시 첫 화면 스크롤 영역 축소 위험**:
   - **위험**: 상단에 공지 배너를 추가하여 기존 차트나 수치가 아래로 밀릴 수 있음.
   - **완화 대책**: 배너 높이를 32px 이내(폰트 0.72rem, 패딩 6px)의 초슬림 콤팩트 카드로 설계하여 대표 수치와 비교 바가 첫 844px 뷰포트 안에 여전히 온전히 들어오도록 보장.
3. **데스크톱 히어로 카드 높이 증가로 인한 하단 차트 가림 위험**:
   - **위험**: 히어로 카드에 비귀속 안내 문구가 추가되면서 높이가 증가하여 스크롤이 발생할 수 있음.
   - **완화 대책**: 마진과 패딩을 2~3px씩 미세 최적화하여 전체 카드 높이 증가를 14px 이내로 억제.

---

## 7. 단계별 완료 및 인수 기준 (Acceptance Criteria)

다음 인수 기준을 100% 충족해야 Step 5D-2 완료로 판정합니다.

1. **데스크톱 의미 노출**: 히어로 라벨에 `전국` 의미가 직접 명시되고, 첫 화면에 `특정 브랜드/개별 점포 실적 아님` 문구가 `isActuallyVisible: true`일 것.
2. **2026 스냅샷 가시성**: 마우스 호버 없이 결손 및 전년 비교 불가 경고가 본문에 상시 노출될 것.
3. **모바일 피크 바 3대 맥락**: 피크 바에 `공정위`, `전국`, `업종 참고치`가 포함되고 가로 오버플로가 0일 것.
4. **모바일 확장 첫 화면 안내**: 바텀시트 확장 시 스크롤 전 첫 844px 뷰포트 내에 출처와 비귀속 안내 배너가 `isActuallyVisible: true`일 것.
5. **기존 동작 보존**: 모바일 초기 수납 구조, 지도 비차폐, 좌측 패널 레이아웃이 원형대로 유지될 것.
6. **무결성 100% 유지**: `collector.py`, `gangnam_food_stores.sqlite3`, `run_gangnam.bat` 해시 불변, API 및 DB 변경 건수 0건.
7. **증빙 일치**: 신규 검증 원시 JSON, 8종 캡처 PNG, 실행보고서, 품질보고서 간 불일치가 0건일 것.

---

## 8. 산출물 명세 및 종료 조건

- **작성 산출물**: [`reports/phase5d_step2_semantic_safety_remediation_plan_r1.md`](file:///d:/Franchise_Dashboard/reports/phase5d_step2_semantic_safety_remediation_plan_r1.md)
- **종료 조건**: 본 계획서 제출 후 작업을 즉시 중단하고 **사용자의 명시적 승인을 기다립니다**. 사용자 승인 전에는 `frontend/src/**`, CSS, API, DB를 수정하지 않습니다.
