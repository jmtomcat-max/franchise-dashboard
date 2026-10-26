# Phase 6 Step 6-2 실행 보고서 — 레이어 제어와 카메라 사용성 정리

- 실행일: 2026-10-20
- 상태: 구현 및 정적 회귀 검증 완료, 사용자 승인 대기
- 선행 단계: Phase 6 Step 6-1 개별 점포 줌인 MVP 완료

## 구현 결과

- 기존 `SlimMapRail`에 `3D 격자`, `개별 점포`, `핫스팟` 표시 토글을 한곳에 통합했다.
- 격자 토글은 개요 포인트, 3D 기둥, 호버 하이라이트를 함께 제어한다.
- 점포 토글을 끄면 진행 중 BBOX 요청을 취소하고 요청 세대를 증가시켜 늦은 응답의 재표시를 차단한다.
- 점포 토글을 다시 켜면 현재 줌·BBOX·업종 조건으로 즉시 재조회한다.
- 모든 레이어 토글에 명확한 한글 `aria-label`과 `aria-pressed`를 적용했다.
- 데스크톱과 모바일의 레일 버튼을 44×44px로 통일했다.
- 기존 2D/3D 전환의 `prefers-reduced-motion` 분기는 유지했다.

## 변경 범위

- `frontend/src/components/SlimMapRail.jsx`
- `frontend/src/components/MapContainer.jsx`
- `frontend/src/index.css`
- `scratch/test_phase6_step2_contract.mjs`

수집기, API, SQLite DB, 분류체계와 기존 보호 파일은 변경하지 않았다.

## 검증 결과

| 검증 | 결과 |
|---|---|
| Step 6-2 레이어·접근성·요청취소 계약 | PASS |
| 기존 Step 6-1 계약 회귀 | PASS |
| Vite 프로덕션 빌드 | PASS |
| 보호 파일 SHA-256 3종 | PASS |
| Python 테스트 | 미실행 — 현재 셸에 실행 가능한 Python 미설치 |

보호 파일 해시는 기존 기준값과 모두 일치한다.

## 남은 경고

- 프로덕션 빌드의 단일 JavaScript 청크가 500kB를 초과한다. 기능 결함은 아니며 번들 분할은 이번 단계 범위에서 제외했다.
- 실제 브라우저에서 레이어 버튼의 화면 동작과 모바일 390×844 오버플로를 다시 캡처하는 검증은 실행 환경의 Python 백엔드 부재로 수행하지 못했다.

## 승인 게이트

Step 6-2 범위를 종료한다. 사용자 승인 전에는 Step 6-3 외부 3D 건물 데이터 타당성 조사나 제품 코드 도입을 시작하지 않는다.

