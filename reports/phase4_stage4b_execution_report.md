# Phase 4 Stage 4B 최종 완료 보고서: 전국 외식업 73.5만 건 브랜드 후보 추출 엔진 구축

- **프로젝트 명**: Franchise Dashboard (대한민국 외식 프랜차이즈 시장 분석 3D GIS 대시보드)
- **프로젝트 경로**: `D:\Franchise_Dashboard`
- **단계**: Phase 4 / Stage 4B
- **보고 일시**: 2026-10-13
- **최종 판정**: **PASS (전국 735,185건 전수 처리, 5,062개 브랜드 후보 추출, 정밀도 100.0% 달성, 자동 테스트 15/15 전수 통과)**
- **승인 게이트 상태**: **READY FOR USER APPROVAL (Phase 4C 착수 대기)**

---

## 1. 종합 요약 및 핵심 성과

Phase 4 Stage 4B는 단순한 문자열 검색 스크립트를 넘어, 전국 735,185건의 소상공인진흥공단 외식업 점포 데이터를 바탕으로 **신뢰할 수 있는 프랜차이즈 브랜드 후보를 자동 생성·검증·품질 평가·오류 복구하는 엔터프라이즈급 통합 데이터 처리 엔진을 구축**하였습니다.

### 5대 핵심 성과:
1. **공식 브랜드 식별 자료 실증 조사 완수 (Branch C 확정 유지)**:
   - 주력 공정위 AI친화 API(15165094)의 가명화 상태를 재확인하고, 타 공정위 오픈API 3종에 대한 실측 조사를 완료하였습니다. 공통 식별키 부재 및 권한 제약에 따라 가명번호 임의 결합을 원천 차단하고 소진공 공간 점포 기반 독자 브랜드 후보 추출 아키텍처를 확립하였습니다.
2. **10단계 다중 방어선 브랜드 추출 엔진 개발**:
   - 유니코드 NFC, 가역적 지점명 분리, 단어 경계 일치, 부정 키워드 사전, 일반명사 단독 상호 필터, 유사 상호 충돌 해결(본죽/본도시락, 신전/신참 등)을 망라한 고정밀 엔진(`src/stage4b/`)을 구현하였습니다.
3. **골드 스탠다드 평가셋 기반 정밀도 100.0% 달성**:
   - 37개 대표 브랜드 및 1,110건 실제 점포 표본 기반 평가에서 **자동 확정(`VERIFIED_AUTO`) 후보의 정밀도 100.0%(오탐 0건)를 달성**하여 개발 목표(>= 95.0%)를 완벽히 초과 충족하였습니다. 모호한 상호는 `REVIEW_REQUIRED`(28.56%)로 안전 격리하였습니다.
4. **전국 735,185건 전수 고속 배치 파이프라인 완수**:
   - 전국 735,185건 전역을 217.93초(초당 3,373.5건)만에 고속 처리 완료하여 신규 격리 DB `data/brand_candidates_v1.sqlite3`에 적재하였습니다.
   - **총 5,062개 브랜드 후보**(공식 확인 80개 + 전국 10개 이상 클러스터 후보 4,982개)를 발굴하였습니다.
   - 후보 연결 점포 168,318건(22.89%), 비프랜차이즈 독립 점포 566,890건(77.11%)을 명확히 분류하고 100% 무결성 대조를 완료하였습니다.
5. **15대 예외 시나리오 자동 테스트 100% 통과**:
   - `tests/test_phase4_stage4b.py`의 15개 단위/통합 테스트를 0.224초 만에 전수 통과(PASS)하였습니다.

---

## 2. 기존 전국 점포 DB (v2) 사전 검증 및 불변성 확인

소진공 전국 외식업 v2 데이터베이스의 무결성과 불변성을 엄격히 준수하였습니다.

- **대상 DB 경로**: `data/nationwide_food_stores_v2.sqlite3`
- **접근 모드**: `mode=ro` (Read-Only URI 강제)
- **총 저장 점포 수**: **735,185건** (보존율 100.0%)
- **점포 고유 식별자(`bizes_id`) 고유율**: **100.0%** (중복 0건)
- **보호 원칙 준수**: 파이프라인 전후 원본 DB에 대한 쓰기/변조가 일절 발생하지 않았음을 재검증 완료하였습니다.

---

## 3. 공식 브랜드 식별 자료 실증 조사 결과

`docs/phase4/official_brand_source_review.md`에 기반한 실측 조사 결과입니다.

1. **공정위 AI친화 외식업 통합정보 API (15165094)**:
   - 정상 수집 완료(2024년 6,346건), 평문 브랜드명/법인명 부재, 15자리 가명번호(`alsBrandMngNo`) 제공.
   - **판정**: 거시 통계 벤치마크 계층으로 분리 활용 (Branch C 유지).
2. **공정위 브랜드 가맹점 목록 정보 API (15125489)**:
   - 실측 결과: HTTP 403 (`SERVICE_KEY_IS_NOT_REGISTERED_ERROR`, 응답코드 30).
   - **판정**: 공공데이터포털 개별 추가 승인이 필요하며 공통 외래키가 없어 즉시 결합 불가.
3. **공정위 브랜드 가맹점 및 직영점 정보 API (15109810)**:
   - 실측 결과: HTTP 400 (`NO_OPENAPI_SERVICE_ERROR`, 응답코드 12).
   - **판정**: 해당 오픈API 폐기/중단 상태 확인.
4. **결론**:
   - 외부 API에 의존하지 않고, 소진공 점포 상호 데이터 기반 정규화 + 전국 10개 이상 클러스터링 + 공인 대표 브랜드 사전을 결합한 자체 자립 파이프라인을 확정하였습니다.

---

## 4. 전국 735,185건 처리 결과 및 정합성 대조 (Data Reconciliation)

신규 데이터베이스 `data/brand_candidates_v1.sqlite3`에 적재된 전국 전수 처리 결과입니다.

### 4.1 전국 점포 대사 결과표 (Reconciliation Table)

| 항목 (Classification) | 건수 (Count) | 비율 (%) | 비고 및 처리 방침 |
| :--- | :---: | :---: | :--- |
| **총 입력 점포 수 (Input Stores)** | **735,185건** | **100.00%** | 소진공 nationwide v2 원본 점포 전수 |
| **상호 정규화 완료 건수** | **735,185건** | **100.00%** | 유니코드 정규화 및 가역 지점명 분리 완료 |
| **1. 후보 연결 점포 (Candidate Linked)** | **168,318건** | **22.89%** | 프랜차이즈 후보 매핑 점포군 |
| 　- 자동 확정 (`VERIFIED_AUTO`) | 32,903건 | 4.48% | 공인 브랜드/별칭 완전 일치 (정밀도 100%) |
| 　- 클러스터 후보 (`PROVISIONAL`) | 117,158건 | 15.94% | 전국 10개 이상 동일 상호 비공식 프랜차이즈 |
| 　- 검토 필요 (`REVIEW_REQUIRED`) | 18,257건 | 2.48% | 복합 상호, 부가 수식어 결합 매장 (안전 격리) |
| **2. 비후보 독립 점포 (Independent)** | **566,890건** | **77.11%** | 독립 개인식당 및 부정 키워드 제외 점포군 |
| 　- 독립 개인 점포 (`INDEPENDENT_STORE`) | 566,056건 | 77.00% | 전국 10개 미만 단독 개인 점포 |
| 　- 부정 키워드 거절 (`REJECTED`) | 834건 | 0.11% | 교촌면옥, 놀부식당 등 오탐 방지 제외 점포 |
| **복수 후보 점포 수 (Multi-Candidate)** | **23건** | 0.003% | 숍인숍 매장 (교촌치킨&피자마루 등) |
| **총 생성된 매핑 레코드 수** | **735,208건** | - | `735,185 + 23 = 735,208` (100% 무결성 일치) |
| **도출된 총 브랜드 후보 수** | **5,062개** | - | 공식 브랜드 80개 + 클러스터 후보 4,982개 |

---

## 5. 전국 상위 대표 프랜차이즈 브랜드 발견 현황 (Top 15)

본 파이프라인을 통해 전국 73.5만 건에서 도출된 상위 대표 브랜드 점포 수 통계입니다.

| 순위 | 브랜드 후보 ID | 브랜드명 | 업종 대분류 | 발견 경로 | 전국 매핑 점포 수 | 상태 |
| :---: | :--- | :--- | :--- | :--- | :---: | :--- |
| **1** | `CAN_BRD_CAF_0004` | **메가MGC커피** | 카페·음료 | OFFICIAL_DICTIONARY | **4,178건** | OFFICIAL_VERIFIED |
| **2** | `CAN_BRD_BKR_0001` | **파리바게뜨** | 베이커리·디저트 | OFFICIAL_DICTIONARY | **3,402건** | OFFICIAL_VERIFIED |
| **3** | `CAN_BRD_CAF_0005` | **컴포즈커피** | 카페·음료 | OFFICIAL_DICTIONARY | **3,000건** | OFFICIAL_VERIFIED |
| **4** | `CAN_BRD_CAF_0002` | **이디야커피** | 카페·음료 | OFFICIAL_DICTIONARY | **2,262건** | OFFICIAL_VERIFIED |
| **5** | `CAN_BRD_CAF_0001` | **스타벅스** | 카페·음료 | OFFICIAL_DICTIONARY | **2,152건** | OFFICIAL_VERIFIED |
| **6** | `CAN_BRD_CHK_0002` | **bbq치킨** | 치킨·패스트푸드 | OFFICIAL_DICTIONARY | **2,017건** | OFFICIAL_VERIFIED |
| **7** | `CAN_BRD_CHK_0003` | **bhc치킨** | 치킨·패스트푸드 | OFFICIAL_DICTIONARY | **2,013건** | OFFICIAL_VERIFIED |
| **8** | `CAN_BRD_CAF_0006` | **빽다방** | 카페·음료 | OFFICIAL_DICTIONARY | **1,819건** | OFFICIAL_VERIFIED |
| **9** | `CAN_BRD_BKR_0003` | **배스킨라빈스** | 베이커리·디저트 | OFFICIAL_DICTIONARY | **1,745건** | OFFICIAL_VERIFIED |
| **10** | `CAN_BRD_CHK_0004` | **맘스터치** | 치킨·패스트푸드 | OFFICIAL_DICTIONARY | **1,563건** | OFFICIAL_VERIFIED |
| **11** | `CAN_BRD_CAF_0003` | **투썸플레이스** | 카페·음료 | OFFICIAL_DICTIONARY | **1,560건** | OFFICIAL_VERIFIED |
| **12** | `CAN_BRD_KOR_0001` | **본죽** | 한식 | OFFICIAL_DICTIONARY | **1,540건** | OFFICIAL_VERIFIED |
| **13** | `CAN_BRD_CHK_0001` | **교촌치킨** | 치킨·패스트푸드 | OFFICIAL_DICTIONARY | **1,388건** | OFFICIAL_VERIFIED |
| **14** | `CAN_BRD_CAF_0007` | **더벤티** | 카페·음료 | OFFICIAL_DICTIONARY | **1,333건** | OFFICIAL_VERIFIED |
| **15** | `CAN_BRD_BKR_0002` | **뚜레쥬르** | 베이커리·디저트 | OFFICIAL_DICTIONARY | **1,286건** | OFFICIAL_VERIFIED |

> 대한민국 외식 프랜차이즈 시장의 실제 상위 브랜드 순위 및 점포 수 스케일과 완벽히 부합함을 실증 증명하였습니다.

---

## 6. 처리 성능 및 리소스 측정

- **총 소요 시간**: **217.93초** (약 3분 37초)
- **전체 처리 속도**: **초당 3,373.5건**
  - Pass 1 (상호 정규화 및 클러스터 카운팅): 73.55초 (초당 9,997건)
  - Pass 2 (점포-후보 매핑 및 정밀 상태 판정): 144.38초 (초당 5,105건)
- **피크 메모리 점유**: **200MB 미만** (스트리밍 및 인메모리 Counter 기반 최적화)
- **DB 저널 모드**: SQLite WAL 모드 (`brand_candidates_v1.sqlite3-wal`, 169MB)

---

## 7. 자동 테스트 결과 (15/15 전수 통과)

단위 및 통합 자동 테스트 스위트(`tests/test_phase4_stage4b.py`)를 통해 지침 제9조에 명시된 모든 필수 시나리오를 검증하였습니다.

```
Ran 15 tests in 0.224s

OK
```

1. 한글·영문·약어 표기 매칭 검증 (`test_01`) -> **PASS**
2. 본죽/본도시락, 신전/신참, 빽다방/빽보이 유사 브랜드 충돌 분리 검증 (`test_02`) -> **PASS**
3. 김가네김밥, 한솥도시락 등 일반명사 포함 브랜드 정상 인식 검증 (`test_03`) -> **PASS**
4. 교촌식당, 놀부식당, 이디야호프 등 비가맹 일반식당 오탐 차단 검증 (`test_04`) -> **PASS**
5. 지점 접미어/접두어/별도컬럼 분리 및 원본 상호 가역성(100%) 검증 (`test_05`) -> **PASS**
6. 숍인숍 복합 매장 다중 후보 분리 및 `is_primary_candidate` 검증 (`test_06`) -> **PASS**
7. 명륜진사갈비NEW, 채선당PLUS, A TWOSOME PLACE 개명/별칭 검증 (`test_07`) -> **PASS**
8. 김밥, 치킨, 피자 등 일반명사 단독 상호 브랜드 승격 차단 검증 (`test_08`) -> **PASS**
9. 배치 중단 및 재개(Checkpointing) 메타데이터 검증 (`test_09`) -> **PASS**
10. 점포 고유 식별자(`bizes_id`) 중복 방지 및 멱등성 검증 (`test_10`) -> **PASS**
11. 전국 10개 이상 점포 임계치 및 공식 브랜드 보존 검증 (`test_11`) -> **PASS**
12. 공식 브랜드 정보 부재 시 소진공 점포 기반 클러스터링 자립 검증 (`test_12`) -> **PASS**
13. 잘못된 별칭 규칙 및 미등록 이상 업종코드 격리 검증 (`test_13`) -> **PASS**
14. 원본 전국 점포 DB (735,185건) Read-Only 불변성 검증 (`test_14`) -> **PASS**
15. 골드 스탠다드 평가셋 대상 자동 확정 정밀도 >= 95% 검증 (`test_15`, 실제 100.0%) -> **PASS**

---

## 8. Phase 4C~4E 및 Phase 5~6 3D 지도 인계 계약 준수 현황

1. **Stage 4C (브랜드 마스터 구축) 인계 데이터**:
   - 5,062개 브랜드 후보 마스터(`candidate_brand_id`, 대표명, 정규화명, 점포수, 발견경로).
   - 공인 별칭 사전(`brand_aliases`).
   - 수동 검토 필요 목록(`store_brand_candidates.store_verification_status = 'REVIEW_REQUIRED'` 18,257건).
2. **Stage 4D (8대·48중분류 체계) 인계 데이터**:
   - 후보 브랜드별 대표 업종(`category_major`, `representative_inds_mcls_cd`).
   - 점포별 공식 소진공 업종코드(`inds_mcls_cd`, `inds_scls_cd`) 원형 보존.
3. **Stage 4E (지역별 통계 집계) 인계 데이터**:
   - 소진공 점포 ID(`bizes_id`)와 후보 ID(`candidate_brand_id`) 간 N:M 연결 테이블.
4. **Phase 5~6 (3D GIS 지도 시각화) 인계 데이터**:
   - 점포별 검증 상태값(`store_verification_status`):
     - `VERIFIED_AUTO`: 정식 프랜차이즈 마커 렌더링.
     - `PROVISIONAL`: 신흥/지역 프랜차이즈 후보 마커 렌더링.
     - `INDEPENDENT_STORE`: 일반 개인 식당 레이어 분리.

---

## 9. 산출물 인벤토리 (Deliverables Inventory)

| 구분 | 파일 경로 | 내용 및 역할 |
| :--- | :--- | :--- |
| **알고리즘 명세서** | `docs/phase4/brand_matching_algorithm.md` | 10단계 매칭 알고리즘, 접미어 정규식, 충돌 해결 규칙 |
| **데이터 계약서** | `docs/phase4/brand_candidate_data_contract.md` | 신규 DB 스키마, 3대 독립 상태 모델, 10개 이상 임계치 규칙 |
| **공식 출처 보고서** | `docs/phase4/official_brand_source_review.md` | 공정위 API 실측 조사, Branch C 확정 근거, 비식별화 분석 |
| **품질 평가 보고서** | `reports/phase4_stage4b_quality_report.md` | 골드 스탠다드 평가(1,110건), 정밀도 100%, 혼동 행렬 |
| **최종 완료 보고서** | `reports/phase4_stage4b_execution_report.md` | 전국 73.5만 건 처리 결과, 상위 브랜드 통계 (본 문서) |
| **검증 데이터셋** | `reports/phase4_stage4b_validation.json` | 기계 판독형 Stage 4B 검증 결과 JSON 파일 |
| **신규 후보 DB** | `data/brand_candidates_v1.sqlite3` | 73.5만 건 점포 정규화 및 5,062개 브랜드 후보 적재 DB |
| **엔진 모듈** | `src/stage4b/schema_stage4b.py` | DB DDL, 인덱스 및 WAL 모드 초기화 |
| | `src/stage4b/normalizer.py` | 유니코드 NFC, 가역적 지점명 분리, 법인격 태그 정제 |
| | `src/stage4b/brand_dictionary.py` | 공인 브랜드 사전(80개), 별칭, 부정 키워드, 일반명사 정지어 |
| | `src/stage4b/candidate_engine.py` | 후보 매칭, 신뢰도 스코어링, 직영/가맹 판정 엔진 |
| | `src/stage4b/evaluator.py` | 골드 스탠다드 평가셋 평가기 및 지표 산출 모듈 |
| | `src/stage4b/pipeline.py` | 전국 735,185건 고속 2-Pass 배치 처리 파이프라인 |
| **테스트 스위트** | `tests/test_phase4_stage4b.py` | 15개 시나리오 전수 자동 테스트 스위트 (15/15 PASS) |
| **재실행 배치 파일**| `run_stage4b.bat` | 테스트 -> 전국 파이프라인 -> 품질 평가 일괄 실행 스크립트 |

---

## 10. 완료 기준 검증 및 승인 게이트

### Stage 4B 체크리스트 점검:
- [x] 선행 자료 및 Stage 4A 매칭 오탐률(56.67% vs 47.84%, 43.33%) 재검증 완료
- [x] 공식 공정위 API 명세 및 추가 엔드포인트 실측 조사 완료 (`official_brand_source_review.md`)
- [x] 임의 결합 금지 및 Branch C 원칙 준수 확인
- [x] 10단계 상호명 정규화 및 가역 지점명 분리 엔진 구현 완료 (`normalizer.py`)
- [x] 8대 대분류별 공인 브랜드 및 별칭 사전 구축 완료 (`brand_dictionary.py`)
- [x] 부정 키워드 및 일반명사 오탐 필터링 구현 완료 (`candidate_engine.py`)
- [x] 골드 스탠다드 평가셋(1,110건) 대상 자동 확정 정밀도 100.0% 달성 (목표 95.0% 초과)
- [x] 15개 단위/통합 자동 테스트 100% 통과 (`tests/test_phase4_stage4b.py`)
- [x] 전국 735,185건 점포 전수 처리 파이프라인 가동 및 무결성 대사 100% 일치 (`pipeline.py`)
- [x] 신규 격리 브랜드 후보 DB 생성 (`data/brand_candidates_v1.sqlite3`)
- [x] 원본 전국 v2 DB 불변성 확인 (735,185건 완벽 보존)
- [x] Stage 4C~4E 및 Phase 5~6 3D 지도 인계 계약 확정 (`brand_candidate_data_contract.md`)
- [x] 일괄 재실행 배치 스크립트 구축 및 검증 완료 (`run_stage4b.bat`)

### 판정: **PASS (통과)**

> **실행 제한 준수 안내**:
> 사용자 실행 지침 제11조에 따라, 본 Stage 4B 작업 완료 후 **Phase 4C(브랜드 마스터 구축)는 자동으로 시작하지 않으며**, 사용자의 확인 및 최종 승인을 대기합니다.
