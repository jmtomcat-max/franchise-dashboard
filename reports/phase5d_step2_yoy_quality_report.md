# Phase 5D Step 2 품질 보고서: FTC 전년비 보조 비교 UI 품질 평가 (R4)

- **평가일**: 2026-10-19
- **회차 (Iteration)**: 4 (Codex Iteration 3 Review 검토 의견 전수 조치: 뷰포트 중앙 스크롤 및 카드 내부 요소 잘림 전수 실측)
- **평가 대상**: `FTC 전년비 Step 2 보조 비교 UI` ([`frontend/src/components/FtcBenchmarkPanel.jsx`](file:///d:/Franchise_Dashboard/frontend/src/components/FtcBenchmarkPanel.jsx), [`frontend/src/index.css`](file:///d:/Franchise_Dashboard/frontend/src/index.css))
- **품질 판정**: **최종 승인 적격 (VERDICT: PASS)**
- **검증 근거**: [`reports/phase5d_step2_yoy_validation.json`](file:///d:/Franchise_Dashboard/reports/phase5d_step2_yoy_validation.json)
- **검증 스크립트**: [`scratch/verify_phase5d_step2_yoy_ui.mjs`](file:///d:/Franchise_Dashboard/scratch/verify_phase5d_step2_yoy_ui.mjs)

---

## 1. 품질 평가 요약

| 평가 차원 | 기준 사양 | 실측치 및 검증 결과 (R4) | 평가 |
| :--- | :--- | :--- | :---: |
| **정보 구조 일관성** | 다년도 추세 바로 아래 1개 블록 삽입, 신규 탭/패널 금지 | `.visual-trends-section` 직하단에 단일 `.ftc-yoy-comparison-block` 삽입 완료 | **PASS** |
| **지표 표출 완전성** | 4개 지표별 '24값, '25값, 증감액, 증감률, 방향성, 부호 | 4대 지표(중위매출, 5%절사평균, 가중평균, 가맹점수) 전수 부호·텍스트 병행 표기 실측 완료 | **PASS** |
| **방향성/변동 실측** | 증가, 감소, 변동 없음, 비교 불가 4종 상태 실측 | 카페 업종 실제 감소(-351만원, -1,703개) 및 Mock 주입 4종 동시 표출 실측 완비 | **PASS** |
| **의미 안전성** | 거시 통계 한계 명시, 2025 완결후보 미확인, 2026 스냅샷 제외 | 3줄 캡션 및 뱃지 완전 보존, 2026년 수치 계산식 전수 배제 실측 확인 | **PASS** |
| **예외 및 결손 방어** | 데이터 누락 및 비수치 시 런타임 오류 차단 및 안내 배너 | 2025 누락/빈 시계열 시 배너 정상 표출, 개별 지표별 `비교 불가` 표출 실측 완료 | **PASS** |
| **다업종 기대값 대사** | 8대 외식 업종 전환 시 4개 지표 및 표본수 기대값 일치 | `id="tab-CAT_MAJ_*"` 정밀 클릭 및 8개 전 업종 trends API 기대값 1:1 대사 통과 | **PASS** |
| **반응형 핏 & 무잘림** | 1440×900 및 390×844 가로 오버플로 0 및 카드/텍스트 잘림 0건 | 데스크톱 1440px / 모바일 390px (0px 오버플로), 카드 및 텍스트 내부 잘림 0건 (`hasAnyClipping: false`) | **PASS** |
| **모바일 사용성** | 1열 세로 배치, 최소 터치 영역 44px 이상, 바텀시트 전개 시 가시성 | 바텀시트 확장 후 비교 블록 스크롤, 1열 배치, 카드 실측 높이 74px (≥ 44px), 블록 가시성 100% | **PASS** |
| **접근성 및 키보드** | Enter/Escape, 패널 접기/펼치기, 연도 선택 유지 | 접기/펼치기 Enter 토글, 연도 선택 2025년 Enter 선택, Escape 닫기 실측 완비 | **PASS** |
| **코드베이스 순도** | 신규 의존성 0건, 백엔드/수집기/DB 변경 금지 | `package.json`, API, DB, 수집기 무수정, 보호 파일 3종 해시 100% 불변 | **PASS** |

---

## 2. Codex Review 지적 사항 조치 상세 (Iteration 3 -> Iteration 4)

### 2.1 [P2] 비교 블록 뷰포트 중앙 스크롤 및 화면 캡처 정밀화
- **지적 사항**: `scratch/verify_phase5d_step2_yoy_ui.mjs:780` — 비교 블록으로 스크롤하지 않고 화면을 캡처하여 S6 모바일 증빙에 비교 블록이 보이지 않고, S1·S2 데스크톱 증빙도 카드 하단이 잘려 있음.
- **조치 내역**:
  * `scrollBlockIntoViewAndCheckClipping()` 함수를 제작하여 각 시나리오(S1, S2-A, S2-B, S3, S6)에서 캡처 직전 비교 블록(`.ftc-yoy-comparison-block`)을 뷰포트 중앙(`block: 'center'`)으로 즉시 스크롤 수행.
  * S6(모바일 390×844)의 경우 패널 본문이 바텀시트 내부에 위치하므로 바텀시트 핸들(`.mobile-bottom-sheet-handle`)을 먼저 클릭하여 전체 확장 상태로 전환한 뒤 비교 블록을 뷰포트 중앙으로 스크롤하여 4개 카드가 전체 노출되도록 개선.
  * 데스크톱 S1 및 S2에서도 비교 블록 전체(표본 수 헤더, 4개 카드, 3줄 캡션)가 온전히 프레임 안에 들어오도록 스크롤 후 캡처 완료.

### 2.2 [P2] 카드 내부 요소 및 텍스트 잘림(Clipping) 전수 실측 검증
- **지적 사항**: 문서의 `scrollWidth`와 카드 높이만으로는 텍스트 말줄임이나 내부 내용 잘림을 검증할 수 없음.
- **조치 내역**:
  * DOM 평가 루프를 통해 각 지표 카드(`.yoy-metric-card`) 4개에 대해:
    1. 카드 컨테이너 잘림 여부: `card.scrollHeight > card.clientHeight + 1` 또는 `card.scrollWidth > card.clientWidth + 1`
    2. 카드 내부 개별 텍스트 요소 잘림 여부: 라벨(`.metric-name`), 2024년 값(`.val-old`), 2025년 값(`.val-new`), 증감액(`.diff-val`), 증감률(`.diff-rate`), 방향성 뱃지(`.dir-badge`)의 `el.scrollWidth > el.clientWidth + 1`
  * 위 조건을 자동 검사하여 `isBlockInView: true`, `hasAnyClipping: false`, `cardsChecked: 4`, `allCardsFreeOfClipping: true`를 엄격히 단언.
  * S1, S2(2-A 카페 실데이터, 2-B Mock 주입), S6(모바일) 전수에서 잘림 0건(`hasAnyClipping: false`)을 입증하고 원시 JSON(`reports/phase5d_step2_yoy_validation.json`)에 기록.

---

## 3. 남은 위험 요소 및 완화 방안 (Remaining Risks)

1. **공정위 2025년 행정 마감 시점 변동**:
   - 현재 2025년은 `최신 완결 후보 · 공식 마감 여부 미확인` 상태로 안전하게 표기되고 있으며, 향후 공정위가 2025년 등록을 공식 마감 확정하거나 정보공개서 시스템 갱신 시 메타데이터 플래그만 조정하면 되도록 모듈화되어 있습니다.
2. **2026년 진행형 스냅샷의 직접 비교 유혹**:
   - UI 캡션 및 툴팁에서 2026년과의 전년비 계산이 전수 배제되었음을 강력히 고지하고 있어 사용자 오독 위험이 원천 완화되었습니다.

---

## 4. 최종 품질 판정

- **완료 판정**: **적격 (PASS)**
- **결론**: Codex Review 지적 사항(Iteration 3의 P2 1건)이 완전 조치되었으며, 비교 블록 뷰포트 중앙 스크롤을 통한 완전한 시각 증빙 확보 및 카드/텍스트 내부 잘림 0건 실측 검증을 통해 `TASK.md`의 모든 완료 조건과 반응형 품질 요건을 100% 충족하였습니다.
