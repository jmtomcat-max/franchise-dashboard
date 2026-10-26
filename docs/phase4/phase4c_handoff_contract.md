# Phase 4 Stage 4C 후속 단계 인계 데이터 계약서 (Handoff Contract)

- **문서 ID**: `CONTRACT-PHASE4-STAGE4C-HANDOFF-V1`
- **프로젝트**: 대한민국 외식 프랜차이즈 시장 분석 3D GIS 대시보드 (`D:\Franchise_Dashboard`)
- **버전**: `v1.0.0`
- **작성 일자**: 2026-10-13
- **인계 발신**: Phase 4 / Stage 4C (브랜드 마스터 구축 및 전국 점포 정합성 검증)
- **인계 수신**:
  - Stage 4D (8대 대분류 & 48대 중분류 정밀 매핑)
  - Stage 4E (시도/시군구/행정동 공간 단위 브랜드 밀집도 및 경쟁 분석)
  - Phase 5~6 (3D GIS MapLibre / deck.gl 인터랙티브 렌더링)

---

## 1. 개요 및 인계 원칙

본 계약서는 Stage 4C에서 확정된 브랜드 마스터(`data/brand_master_v1.sqlite3`)를 후속 파이프라인과 프론트엔드 시각화 계층에서 사용할 때 준수해야 할 데이터 인터페이스와 집계 원칙을 규정합니다.

후속 단계에서는 브랜드 테이블의 구조를 재설계하지 않으며, 본 계약서에 정의된 뷰(View) 및 필드 인터페이스를 직접 활용합니다.

---

## 2. Stage 4D 인계 인터페이스 (업종 체계 연계)

### 2.1 요구 필드 명세

| 필드명 | 데이터 타입 | 필수 여부 | 설명 |
| :--- | :--- | :---: | :--- |
| `internal_brand_id` | `TEXT` | 필수 | 영구 고유 브랜드 마스터 식별자 (`BRD_xxxx`) |
| `brand_name_std` | `TEXT` | 필수 | 표준 브랜드명 |
| `representative_category`| `TEXT` | 필수 | 확정된 8대 외식업 대분류 (한식, 중식, 일식, 양식·세계음식, 치킨·패스트푸드, 분식·간편식, 카페·음료, 베이커리·디저트) |
| `representative_inds_mcls_cd` | `TEXT` | 필수 | 대표 공공데이터 중분류 코드 (예: `I212`) |
| `representative_inds_scls_cd` | `TEXT` | 필수 | 대표 공공데이터 소분류 코드 (예: `I21201`) |
| `mapped_mid_category_48` | `TEXT` | 필수 (4D 산출) | 48대 확정 중분류 매핑명 |
| `original_store_inds_code` | `TEXT` | 필수 | 원본 점포(`stores`)의 실제 업종코드 (1:N 매핑 허용) |
| `classification_status` | `TEXT` | 필수 | `CATEGORY_CONFIRMED`, `CATEGORY_PROVISIONAL`, `AMBIGUOUS_REVIEW` |

### 2.2 4D 인계 규칙
- **8대 대분류 / 48대 중분류 체계 엄격 유지**: 임의의 신규 분류를 신설하거나 기존 분류를 변경하지 않습니다.
- **1:N 업종 분산 허용**: 동일 브랜드(예: `본죽&비빔밥`) 소속 점포들이 원본 데이터상 `죽 전문점`과 `한식 일반`으로 분산 등록되어 있더라도, 브랜드 대표 업종은 1개로 확정하되 개별 점포의 원본 업종코드는 그대로 유지합니다.

---

## 3. Stage 4E 인계 인터페이스 (지역 통계 및 상권 분석)

### 3.1 요구 필드 명세

| 필드명 | 데이터 타입 | 필수 여부 | 설명 |
| :--- | :--- | :---: | :--- |
| `signgu_cd` | `TEXT` | 필수 | 5자리 시군구 행정구역 코드 (예: `11680` 강남구) |
| `ctprvn_cd` | `TEXT` | 필수 | 2자리 시도 코드 (예: `11` 서울특별시) |
| `bizes_id` | `TEXT` | 필수 | 소진공 고유 점포 식별자 |
| `internal_brand_id` | `TEXT` | 선택 | 소속 브랜드 ID (미매칭 점포는 `BRD_UNMATCHED`) |
| `brand_officiality` | `TEXT` | 필수 | `FRANCHISE_CONFIRMED`, `BRAND_CONFIRMED`, `UNVERIFIED` |
| `match_status` | `TEXT` | 필수 | `MATCH_AUTO_HIGH_CONFIDENCE`, `MATCH_PROVISIONAL`, `UNMATCHED` 등 |
| `operation_type` | `TEXT` | 필수 | `FRANCHISED`, `COMPANY_OPERATED`, `UNKNOWN` |
| `stdr_ym` | `TEXT` | 필수 | 데이터 기준월 (`202606`) |

### 3.2 4E 인계 규칙
- **공식 프랜차이즈 vs 미확인 클러스터 분리 집계**:
  - `FRANCHISE_CONFIRMED` 점포만으로 산출한 '공식 프랜차이즈 밀집도' 지표와
  - `UNVERIFIED` 후보를 포함한 '전체 프랜차이즈 추정 밀집도' 지표를 독립적으로 산출합니다.
- **점포 고유성 보장 (Non-Duplicate Count)**:
  - 지역별 외식업 점포 밀집도 계산 시 23개 다중 브랜드 숍인숍 점포가 중복 카운트되어 모수가 왜곡되지 않도록 반드시 `COUNT(DISTINCT bizes_id)`를 사용합니다.

---

## 4. Phase 5~6 3D GIS 지도 렌더링 인계 인터페이스

### 4.1 요구 필드 및 렌더링 규칙 명세

| 지도 요구 항목 | 데이터베이스 소스 | 렌더링 규칙 및 시각적 표현 |
| :--- | :--- | :--- |
| **지도 검색용 브랜드 ID** | `brands.internal_brand_id` | 검색 필터 및 브랜드 드롭다운의 고유 키로 사용 |
| **표준 표시명** | `brands.brand_name_std` | 3D 지도 팝업, 점포 마커 툴팁, 상단 랭킹 패널에 표기 |
| **점포 좌표 연결** | `stores.lon`, `stores.lat` (WGS84) | deck.gl Point/ScatterplotLayer 및 3D ColumnLayer 렌더링 |
| **브랜드 공식성 시각 배지** | `brands.brand_officiality` | - `FRANCHISE_CONFIRMED`: 인증 골드/블루 배지<br/>- `BRAND_CONFIRMED`: 직영 퍼플 배지<br/>- `UNVERIFIED`: 회색/점선 미확인 배지 (추정 브랜드임을 명시) |
| **다중 브랜드 점포 렌더링** | `store_brand_links.is_primary_link` | 지도 화면에는 `is_primary_link = 1`인 주 브랜드를 우선 마커로 렌더링하고, 팝업 상세창에 '숍인숍 복합 매장' 표기 |
| **미매칭 점포 표시** | `match_status = 'UNMATCHED'` | 지도상에 '일반 음식점 (독립 자영업 추정)'으로 중립 표기하며, 프랜차이즈 아이콘 부여 금지 |

---

## 5. SQL 인계 뷰 (Handoff Views)

후속 단계 개발자가 복잡한 조인 쿼리 없이 즉시 사용할 수 있도록 아래 뷰 인터페이스를 권장합니다:

```sql
-- Stage 4E / Phase 5-6 인계용 통합 점포-브랜드 뷰
CREATE VIEW IF NOT EXISTS v_store_brand_master AS
SELECT 
    s.bizes_id,
    s.bizes_nm,
    s.signgu_cd,
    s.signgu_nm,
    s.admd_cd,
    s.admd_nm,
    s.inds_mcls_cd,
    s.inds_scls_cd,
    s.lon,
    s.lat,
    l.internal_brand_id,
    b.brand_name_std,
    b.category_major,
    b.brand_officiality,
    l.match_status,
    l.operation_type,
    l.is_primary_link,
    l.confidence_score
FROM store_brand_links l
JOIN brands b ON l.internal_brand_id = b.internal_brand_id
JOIN stores s ON l.bizes_id = s.bizes_id;
```
