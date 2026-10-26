# 대한민국 외식 프랜차이즈 시장 분석 3D GIS 대시보드
## Franchise Dashboard (Phase 6 MVP & Phase 7 실행환경 표준화)

> **🌐 공식 라이브 웹사이트**: [https://franchise-dashboard-scpz.onrender.com/](https://franchise-dashboard-scpz.onrender.com/)  
> **📖 공식 사용자 설명서 (용어사전 포함)**: [`USER_GUIDE.html`](USER_GUIDE.html)  
> **🎮 인터랙티브 라이브 쇼케이스**: [`Franchise_Dashboard_Showcase.html`](Franchise_Dashboard_Showcase.html)

전국 735,185개 고유 외식업 점포 전수 분석 데이터와 공정거래위원회 4개년(2023~2026) 거시통계를 결합한 **대한민국 외식 프랜차이즈 시장 분석용 인터랙티브 3D GIS 대시보드**입니다.

---

## 1. 시스템 주요 기능 및 아키텍처

- **전국 외식업 전수 공간 분석**: 16개 광역 시도, 256개 시군구 단위의 다차원 시장 점유율 및 프랜차이즈 침투율 집계.
- **확정 8대 대분류 및 48대 중분류 체계**: 한식, 중식, 일식, 양식·세계음식, 치킨·패스트푸드, 분식·간편식, 카페·음료, 베이커리·디저트 8대 확정 체계.
- **5,062개 브랜드 지능형 매칭**: 공정위 공식 가맹브랜드와 일반 독립점포를 엄격히 분리 대사(Decoupled State Model).
- **고성능 3D GIS 시각화 (MapLibre GL JS 기반)**:
  - **100m 정밀 밀집도 3D 격자 기둥 (MapLibre `fill-extrusion`)**: 상권 밀집도를 입체적 기둥 높이와 밀집도/업종별 테마 색상으로 표현.
  - **상권 핫스팟 드론 비행 투어 (`Drone Flight Tour`)**: 주요 핵심 상권으로 카메라가 부드럽게 활강 이동.
  - **줌인(Zoom 14+) 개별 점포 스트리밍**: 뷰포트 바운딩 박스(BBOX) 기반 점포 GeoJSON 실시간 렌더링.
  - **SlimMapRail 인터랙티브 제어**: 3D/2D 시점 전환, 기둥 높이 On/Off, 색상 테마 전환, 격자·점포·핫스팟 레이어 개별 토글 지원.
- **공정거래위원회 거시통계 및 창업비용 벤치마크 (FTC Macro)**: 2023~2026 4개년 시계열 횡단면 데이터(업종별 평균/중앙값 매출, 평당 인테리어비, 가맹금, 보증금 등) 제공.
- **현재 확정된 MVP 상태**: '100m 헥사곤 3D 기둥(`fill-extrusion`) + 줌 14 개별 점포 레이어' 체제로 확정 운영 (외부 3D 건물 레이어는 HOLD 결정에 따라 차기 고도화 과제로 분리).

---

## 2. 시스템 요구사항 (Prerequisites)

- **Python**: **3.11 이상** (표준 환경: Python 3.12.7, 프로젝트 루트 `.venv` 권장)
- **Node.js**: **v18.0.0 이상** (표준 환경: Node.js v23.4.0 / npm v10+)
- **운영체제**: Windows 10/11, macOS, Linux
- **저장공간**: 약 3GB 이상 (SQLite 전수 분석 DB 및 캐시 포함)

---

## 3. 빠른 시작 가이드 (Quick Start)

### 단계 1: 가상환경 생성 및 활성화
```bash
# Python 3.12 기준 가상환경 생성
py -3.12 -m venv .venv

# 가상환경 활성화 (Windows CMD)
.venv\Scripts\activate.bat

# 가상환경 활성화 (PowerShell)
.\.venv\Scripts\Activate.ps1
```

### 단계 2: Python 및 프론트엔드 의존성 설치
```bash
# Python 최소 필수 패키지 설치 (FastAPI, Uvicorn, Pydantic, Httpx, Pytest)
pip install -r requirements.txt

# 프론트엔드 React / MapLibre 패키지 설치
npm install --prefix frontend
```

### 단계 3: 실행환경 사전점검 (Preflight Check)
실행 전 필수 Python 버전(.venv), 패키지 로드, SQLite DB 스키마, FTC 2023~2026 연도, 브랜드 마스터 무결성, 환경설정 및 보호 파일 무결성을 자동 검사합니다.
```bash
# Windows 배치 스크립트 실행 (.venv 자동 감지)
scripts\check_env.bat

# 또는 직접 실행
.venv\Scripts\python.exe scripts/preflight_check.py
```
> 모든 항목이 `[PASS]`로 표시되면 시스템을 안전하게 시작할 수 있습니다.

---

## 4. 서비스 실행 방법 (Running Services)

### 백엔드 API 서버 실행 (FastAPI + Uvicorn)
```bash
# 편의 스크립트 실행 (사전점검 후 .venv 기반 자동 기동)
scripts\run_backend.bat

# 또는 직접 실행 (포트: 8000)
.venv\Scripts\python.exe -m uvicorn src.stage4e.api.main:app --host 127.0.0.1 --port 8000 --reload
```
- **API 기본 주소**: `http://127.0.0.1:8000`
- **대화형 Swagger 문서**: `http://127.0.0.1:8000/docs`
- **대체 Redoc 문서**: `http://127.0.0.1:8000/redoc`

### 프론트엔드 대시보드 실행 (React + Vite)
```bash
# 편의 스크립트 실행
scripts\run_frontend.bat

# 또는 직접 실행 (포트: 5173)
npm run dev --prefix frontend
```
- **클라우드 공식 웹사이트**: [https://franchise-dashboard-scpz.onrender.com/](https://franchise-dashboard-scpz.onrender.com/)
- **로컬 개발서버 접속 주소**: `http://localhost:5173`

---

## 5. 테스트 및 무결성 검증 (Verification)

### 1) 주요 FastAPI 엔드포인트 스모크 테스트 (Smoke Test)
서버 기동 여부와 관계없이 핵심 비즈니스 및 공간 쿼리 12개 엔드포인트의 응답 상태(200), 스키마 무결성, FTC 2023~2026 데이터 및 응답시간을 즉시 검증합니다:
```bash
# .venv 기반 인메모리 고속 스모크 테스트
scripts\run_smoke.bat

# 또는 JSON 결과 출력
.venv\Scripts\python.exe scripts/smoke_test_api.py --json reports/smoke_test_results.json

# 실제 구동 중인 로컬 서버 대상 라이브 테스트
.venv\Scripts\python.exe scripts/smoke_test_api.py --live
```

### 2) 전체 82개 단위/통합 테스트 스위트 실행
대용량 SQLite DB 연결 간섭을 방지하도록 4개 모듈 그룹으로 안전하게 분할 격리 실행합니다:
```bash
# 통합 테스트 러너 실행 (.venv 자동 감지)
scripts\run_tests.bat

# 또는 직접 실행 (JSON 저장 지원)
.venv\Scripts\python.exe scripts/run_tests.py --json reports/test_suite_results.json
```
실제 테스트 파일 및 통과 내역 (총 82개 전수 합격):
- `tests/test_phase4_stage4a.py` (소상공인 API 클라이언트 및 수집기 계약 테스트 10개): `PASS`
- `tests/test_phase4_stage4b.py` (브랜드 후보 추출 및 정규화 평가 테스트 19개): `PASS`
- `tests/test_phase4_stage4c.py` (브랜드 마스터 구축 및 80대 공인 브랜드 분류 테스트 11개): `PASS`
- `tests/test_phase4_stage4d.py` (8대 대분류/48대 중분류 매핑 및 뷰 무결성 테스트 11개): `PASS`
- `tests/test_phase4_stage4e.py` (735,185건 고유 외식 점포 및 다차원 공간 집계 테스트 15개): `PASS`
- `tests/test_phase5b_step1.py` (공정위 거시통계 및 창업비용 벤치마크 API 테스트 13개): `PASS`
- `tests/test_phase5b_step2_supplement.py` (연도 자동/수동 선택 및 원자적 폴백 보완 테스트 3개): `PASS`

---

## 6. 디렉터리 구조 및 핵심 데이터베이스

```
D:\Franchise_Dashboard\
├── .venv/                                # Python 3.12.7 가상환경
├── data/                                 # 핵심 SQLite 분석 데이터베이스
│   ├── franchise_analytics_v1.sqlite3   # 735,185건 전수 분석 마스터 DB (490.2MB)
│   ├── ftc_macro_statistics_v1.sqlite3   # 공정위 4개년(2023~2026) 거시통계 DB (30.8MB)
│   ├── brand_master_v1.sqlite3          # 5,063개 브랜드 마스터 및 735,208개 링크 DB (199.2MB)
│   ├── food_category_master_v1.sqlite3  # 8대/48대 업종분류 마스터 DB (410.6MB)
│   └── nationwide_food_stores_v2.sqlite3# 전국 외식 점포 원본 DB (1.5GB)
├── src/                                  # 백엔드 핵심 소스코드
│   └── stage4e/api/                     # FastAPI 애플리케이션 진입점 및 라우터
│       ├── main.py                      # FastAPI 메인 앱 및 미들웨어
│       ├── database.py                  # 분석 DB 읽기 전용 풀 및 쿼리 캐시
│       ├── ftc_database.py              # 공정위 DB 읽기 전용 풀
│       └── routers/                     # 비즈니스별 엔드포인트 라우터 (summary, regions, categories, brands, spatial, ftc_macro)
├── frontend/                             # React 18 + MapLibre GL JS 대시보드
│   ├── src/components/                  # MapContainer, SlimMapRail 등 3D GIS UI
│   ├── src/services/api.js              # 백엔드 연동 클라이언트
│   └── package.json                     # 프론트엔드 의존성 명세
├── scripts/                              # 운영 및 검증 표준화 스크립트
│   ├── preflight_check.py               # 런타임/DB/환경 사전점검 스크립트
│   ├── smoke_test_api.py                # 12대 핵심 엔드포인트 스모크 테스트
│   ├── run_tests.py                     # 82개 전체 테스트 러너
│   ├── run_backend.bat / .ps1           # 백엔드 안전 실행 스크립트
│   ├── run_frontend.bat / .ps1          # 프론트엔드 실행 스크립트
│   ├── run_smoke.bat                    # 스모크 테스트 실행 배치
│   ├── run_tests.bat                    # 전체 테스트 실행 배치
│   └── check_env.bat / .ps1             # 환경 점검 배치 스크립트
├── tests/                                # 82개 단위/통합 테스트 스위트 (7개 파일)
├── reports/                              # 단계별 실행 및 아키텍처 보고서
├── requirements.txt                      # 최소 Python 의존성 명세
└── AGENTS.md                             # AI 에이전트 작업 지침 및 보호 규칙
```

---

## 7. 보호 자산 관리 규칙 (Immutability Contract)

본 프로젝트는 강남구 원본 수집 자산의 영구적 보존을 위해 다음 3종 파일의 변경을 엄격히 금지합니다:
- `collector.py` (SHA-256: `341BAC12BB0AF58DCBDEBBA9459033521F27DF9817E35BAD8B21A4D07BA3369C`)
- `gangnam_food_stores.sqlite3` (SHA-256: `FEE3B58651CFED5C390C0B95DB02B05EBE92DF18619A06F4E399D429236F3A78`)
- `run_gangnam.bat` (SHA-256: `0582C3A1AE53450DDC482E9BF538510780CA2F14D44E987CC753D4E12C816491`)

모든 사전점검 스크립트(`preflight_check.py`)와 테스트 러너는 실행 시마다 위 해시를 자동으로 상호 검증합니다.
