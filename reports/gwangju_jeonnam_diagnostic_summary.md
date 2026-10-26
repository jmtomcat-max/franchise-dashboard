# Phase 3 — 광주·전남 API 조회 실패 원인 집중 분석 보고서

- **검증 일시**: 2026-10-12 16:25:33
- **분석 목적**: 광주광역시 및 전라남도 소진공 API 03 NODATA_ERROR 발생 원인 정밀 규명
- **Base Endpoint**: `https://apis.data.go.kr/B553077/api/open/sdsc2`

---

## 1. 테스트 결과 요약표

| 그룹 | 테스트 명칭 | 오퍼레이션 | 요청 파라미터 | 응답코드 | resultMsg | totalCount | 기준월 | 반환 지역정보 |
| :--- | :--- | :---: | :--- | :---: | :--- | :---: | :---: | :--- |
| 업종코드 비교 | 광주 동구 (I2 포함) | `storeListInDong` | `divId=signguCd, key=29110, indsLclsCd=I2` | `03` | NODATA_ERROR | **0건** | `-` | - |
| 업종코드 비교 | 광주 동구 (업종코드 제외/전체업종) | `storeListInDong` | `divId=signguCd, key=29110` | `03` | NODATA_ERROR | **0건** | `-` | - |
| 업종코드 비교 | 광주 북구 (I2 포함) | `storeListInDong` | `divId=signguCd, key=29170, indsLclsCd=I2` | `03` | NODATA_ERROR | **0건** | `-` | - |
| 업종코드 비교 | 광주 북구 (업종코드 제외/전체업종) | `storeListInDong` | `divId=signguCd, key=29170` | `03` | NODATA_ERROR | **0건** | `-` | - |
| 업종코드 비교 | 전남 목포시 (I2 포함) | `storeListInDong` | `divId=signguCd, key=46110, indsLclsCd=I2` | `03` | NODATA_ERROR | **0건** | `-` | - |
| 업종코드 비교 | 전남 목포시 (업종코드 제외/전체업종) | `storeListInDong` | `divId=signguCd, key=46110` | `03` | NODATA_ERROR | **0건** | `-` | - |
| 업종코드 비교 | 전남 순천시 (I2 포함) | `storeListInDong` | `divId=signguCd, key=46150, indsLclsCd=I2` | `03` | NODATA_ERROR | **0건** | `-` | - |
| 업종코드 비교 | 전남 순천시 (업종코드 제외/전체업종) | `storeListInDong` | `divId=signguCd, key=46150` | `03` | NODATA_ERROR | **0건** | `-` | - |
| 시도단위 비교 | 광주광역시 전체 (I2 포함) | `storeListInDong` | `divId=ctprvnCd, key=29, indsLclsCd=I2` | `03` | NODATA_ERROR | **0건** | `-` | - |
| 시도단위 비교 | 광주광역시 전체 (업종코드 제외) | `storeListInDong` | `divId=ctprvnCd, key=29` | `03` | NODATA_ERROR | **0건** | `-` | - |
| 시도단위 비교 | 전라남도 전체 (I2 포함) | `storeListInDong` | `divId=ctprvnCd, key=46, indsLclsCd=I2` | `03` | NODATA_ERROR | **0건** | `-` | - |
| 시도단위 비교 | 전라남도 전체 (업종코드 제외) | `storeListInDong` | `divId=ctprvnCd, key=46` | `03` | NODATA_ERROR | **0건** | `-` | - |
| 행정동단위 조회 | 광주 동구 충장동 (adongCd 2911052500, I2) | `storeListInDong` | `divId=adongCd, key=2911052500, indsLclsCd=I2` | `03` | NODATA_ERROR | **0건** | `-` | - |
| 행정동단위 조회 | 광주 동구 충장동 (adongCd 2911052500, 업종제외) | `storeListInDong` | `divId=adongCd, key=2911052500` | `03` | NODATA_ERROR | **0건** | `-` | - |
| 행정동단위 조회 | 전남 목포시 목원동 (adongCd 4611053000, I2) | `storeListInDong` | `divId=adongCd, key=4611053000, indsLclsCd=I2` | `03` | NODATA_ERROR | **0건** | `-` | - |
| 행정동단위 조회 | 전남 목포시 목원동 (adongCd 4611053000, 업종제외) | `storeListInDong` | `divId=adongCd, key=4611053000` | `03` | NODATA_ERROR | **0건** | `-` | - |
| 타 오퍼레이션 | 광주 동구 상권조회 (storeZoneInAdmi) | `storeZoneInAdmi` | `divId=signguCd, key=29110` | `03` | NODATA_ERROR | **0건** | `-` | - |
| 타 오퍼레이션 | 광주 전체 상권조회 (storeZoneInAdmi) | `storeZoneInAdmi` | `divId=ctprvnCd, key=29` | `03` | NODATA_ERROR | **0건** | `-` | - |
| 타 오퍼레이션 | 전남 목포 상권조회 (storeZoneInAdmi) | `storeZoneInAdmi` | `divId=signguCd, key=46110` | `03` | NODATA_ERROR | **0건** | `-` | - |
| 타 오퍼레이션 | 광주시청 반경 1km 상권조회 (storeZoneInRadius) | `storeZoneInRadius` | `cx=126.8526, cy=35.1595, radius=1000` | `00` | NORMAL SERVICE | **0건** | `-` | 전남광주통합특별시 서구 |
| 정상 대조군 | 서울 강남구 점포조회 (storeListInDong, I2) | `storeListInDong` | `divId=signguCd, key=11680, indsLclsCd=I2` | `00` | NORMAL SERVICE | **12,628건** | `202606` | 서울특별시 강남구 |
| 정상 대조군 | 서울 강남구 상권조회 (storeZoneInAdmi) | `storeZoneInAdmi` | `divId=signguCd, key=11680` | `00` | NORMAL SERVICE | **0건** | `-` | 서울특별시 강남구 |

---

## 2. 심층 분석 및 원인 판정

### 2.1 업종코드(I2) 필터 유무에 따른 영향 분석
- 업종코드 `I2`를 생략(전체 업종 조회)했을 때의 응답 여부를 통해 외식업 데이터 누락인지, 광주/전남 전체 데이터의 엔드포인트 미서비스인지 판별.

### 2.2 행정구역 구분자(`divId`) 및 타 오퍼레이션 분석
- `signguCd` vs `ctprvnCd` vs `adongCd` 응답 비교.
- `storeZoneInAdmi`(상권조회)의 동작 여부를 통해 상권 DB와 점포 DB의 서비스 상태 대조.

### 2.3 광주·전남 데이터 확보 가능 여부 및 대체 수집 방안
- **방법 1 (Open API 내부 해결)**: `adongCd` 또는 `ctprvnCd` 조회를 통한 데이터 수집 가능성.
- **방법 2 (공공데이터포털 파일데이터 연계)**: 공공데이터포털에서 공식 제공하는 '소상공인시장진흥공단_상가(상권)정보' 광주/전남 최신 CSV 파일 연계를 통한 100% 무결성 데이터 확보.