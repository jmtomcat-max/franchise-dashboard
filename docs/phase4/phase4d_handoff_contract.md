# Phase 4 Stage 4D 후속 단계 인계 데이터 계약서 (Handoff Contract)

- **문서 ID**: `CONTRACT-PHASE4-STAGE4D-HANDOFF-V1`
- **프로젝트**: 대한민국 외식 프랜차이즈 시장 분석 3D GIS 대시보드 (`D:\Franchise_Dashboard`)
- **버전**: `v1.0.0`
- **작성 일자**: 2026-10-13
- **인계 발신**: Phase 4 / Stage 4D (8대 대분류 & 48대 중분류 체계 구축 및 전국 점포 분류)
- **인계 수신**:
  - Stage 4E (시도/시군구/행정동 공간 단위 브랜드 밀집도 및 상권 경쟁 분석)
  - Phase 5~6 (3D GIS MapLibre GL JS / deck.gl 인터랙티브 시각화)

---

## 1. 개요 및 인계 원칙

본 계약서는 Stage 4D에서 완성된 카테고리 마스터 DB(`data/food_category_master_v1.sqlite3`)를 후속 공간 분석(Stage 4E)과 프론트엔드 3D 지도 계층(Phase 5~6)에 인계하기 위한 표준 인터페이스와 연산 규칙을 규정합니다.

후속 단계 개발자는 데이터베이스 스키마를 재설계하거나 임의로 업종 코드를 매핑하지 않으며, 본 계약서에 정의된 뷰(`v_store_category_master`, `v_category_store_aggregates`)와 불변 ID를 직접 활용합니다.

---

## 2. Stage 4E 인계 인터페이스 (지역별 업종·브랜드 밀집도 분석)

### 2.1 요구 필드 명세

| 필드명 | 데이터 타입 | 필수 여부 | 설명 |
| :--- | :--- | :---: | :--- |
| `signgu_cd` | `TEXT` | 필수 | 5자리 시군구 행정구역 코드 (예: `11680` 강남구) |
| `ctprvn_cd` | `TEXT` | 필수 | 2자리 시도 코드 (예: `11` 서울특별시) |
| `bizes_id` | `TEXT` | 필수 | 소진공 고유 점포 식별자 (전국 735,185건 고유) |
| `category_major_id` | `TEXT` | 필수 | 확정 8대 대분류 ID (`CAT_MAJ_01` ~ `CAT_MAJ_08`) |
| `category_major_name` | `TEXT` | 필수 | 8대 대분류명 (한식, 카페·음료, 치킨·패스트푸드 등) |
| `category_mid_id` | `TEXT` | 필수 | 확정 48대 중분류 ID (`CAT_MID_0101` ~ `CAT_MID_0806`) |
| `category_mid_name` | `TEXT` | 필수 | 48대 중분류 표준명 (고기구이/육류, 치킨, 커피전문점 등) |
| `primary_brand_id` | `TEXT` | 필수 | 소속 주 브랜드 ID (독립 점포는 `BRD_UNMATCHED`) |
| `brand_officiality` | `TEXT` | 선택 | `FRANCHISE_CONFIRMED`, `BRAND_CONFIRMED`, `UNVERIFIED` |
| `classification_status` | `TEXT` | 필수 | `CATEGORY_CONFIRMED`, `CATEGORY_PROVISIONAL`, `AMBIGUOUS_REVIEW` |
| `is_brand_linked` | `INTEGER` | 필수 | 브랜드 소속 여부 (1: 프랜차이즈/체인, 0: 독립음식점) |
| `is_category_divergent` | `INTEGER` | 필수 | 점포 원본업종과 브랜드 대표업종 간 불일치 여부 (1/0) |

### 2.2 4E 분석 및 집계 규칙
1. **외식업 전체 모수 왜곡 차단**:
   - 지역별 프랜차이즈 점유율 산출 시, 분모(외식업 전체 점포 수)는 반드시 `COUNT(DISTINCT bizes_id)`를 사용해야 합니다.
   - 23개 복수 브랜드 숍인숍 점포로 인해 모수가 중복 카운트되는 오류를 원천 차단합니다.
2. **공식 가맹 vs 전체 브랜드 분리 집계**:
   - `classification_status = 'CATEGORY_CONFIRMED'` 점포만을 대상으로 한 '공식 프랜차이즈 업종 분포'와
   - `CATEGORY_PROVISIONAL`을 포함한 '전체 브랜드(잠정 클러스터 포함) 업종 분포'를 독립적으로 분리 집계할 수 있어야 합니다.
3. **모호 분류 점포 투명 관리**:
   - `AMBIGUOUS_REVIEW`로 표기된 104,060건(주로 키워드가 없는 일반 소형 개인 카페 및 간이식당)은 집계 리포트에서 '모호/검토 대기 점포'로 별도 주석을 병기합니다.

---

## 3. Phase 5~6 3D GIS 지도 렌더링 인계 인터페이스

### 3.1 지도 렌더링 명세 및 시각화 규칙

| 지도 요구 항목 | 데이터베이스 소스 | 3D GIS (deck.gl / MapLibre) 렌더링 규칙 |
| :--- | :--- | :--- |
| **점포 포인트 렌더링** | `lon`, `lat` (WGS84) | deck.gl `ScatterplotLayer` 또는 `IconLayer`로 렌더링 (줌레벨 14+) |
| **3D 건물 기둥 집계** | `v_category_store_aggregates` | deck.gl `ColumnLayer` 또는 `HexagonLayer`로 업종별 밀집도 높이 표현 |
| **8대 대분류 필터링** | `category_major_id` | 대시보드 좌측 상단 8대 대분류 토글 버튼의 Key로 사용 |
| **48대 중분류 드롭다운** | `category_mid_id` | 상위 대분류 선택 시 하위 48대 중분류 다중 선택 필터 바인딩 |
| **브랜드 공식성 배지** | `brand_officiality` | 팝업 창에 골드(공인 가맹), 퍼플(직영 체인), 그레이(미확인 후보) 배지 표기 |
| **복합 메뉴 안내** | `is_category_divergent = 1` | 팝업 상세창에 '복합 업태 운영 매장 (예: 비빔밥 취급 본죽)' 알림 표시 |
| **모호 분류 안내** | `classification_status = 'AMBIGUOUS_REVIEW'` | 팝업 상세창에 '세부 업태 확인 중인 일반 음식점'으로 중립적 표기 |

---

## 4. SQL 표준 뷰 인터페이스

후속 단계 개발자가 복잡한 조인 쿼리 없이 즉시 사용할 수 있도록 아래 뷰 인터페이스를 제공합니다:

```sql
-- 1. 개별 점포 및 공간 정보 통합 뷰 (Stage 4E 및 3D 지도 팝업용)
SELECT * FROM v_store_category_master
WHERE ctprvn_cd = '11' AND signgu_cd = '11680' AND category_major_id = 'CAT_MAJ_01';

-- 2. 업종별 전국 집계 요약 뷰 (통계 패널 및 대시보드 요약 차트용)
SELECT 
    category_maj_name,
    category_mid_name,
    total_stores,
    brand_linked_stores,
    independent_stores,
    confirmed_stores,
    provisional_stores,
    ambiguous_stores
FROM v_category_store_aggregates
ORDER BY category_maj_id, total_stores DESC;
```
