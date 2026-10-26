# Franchise Dashboard Frontend — Phase 5A 기본 지도 서비스

대한민국 외식 프랜차이즈 시장 분석 3D GIS 대시보드의 Phase 5A 프론트엔드 실행 패키지입니다.
React 및 MapLibre GL JS 기반으로 광진구 중심의 2D 밀집도 프리뷰와 백엔드 API 연동을 검증합니다.

---

## 1. 실행 전제 조건

- **Node.js**: v18.0 이상 (권장 v20.x 또는 v23.x)
- **Python**: v3.11 이상 (백엔드 FastAPI 실행용)
- **백엔드 서비스**: `http://127.0.0.1:8000` (Stage 4E 분석 API)

---

## 2. 실행 명령어 안내

### 2.1 백엔드 API 서버 실행 (프로젝트 루트 `D:\Franchise_Dashboard`에서 실행)

```powershell
python -m uvicorn src.stage4e.api.main:app --host 127.0.0.1 --port 8000
```
> 정상 실행 시 `http://127.0.0.1:8000/docs` (Swagger UI) 및 `/api/v1/analytics/summary` 접근 가능.

---

### 2.2 프론트엔드 의존성 설치 (`D:\Franchise_Dashboard\frontend`에서 실행)

```powershell
cd D:\Franchise_Dashboard\frontend
npm install
```

---

### 2.3 프론트엔드 개발 서버 실행 (Vite)

```powershell
npm run dev
```
> 브라우저에서 `http://127.0.0.1:5173/` 접속.

---

### 2.4 프로덕션 빌드 및 미리보기

```powershell
# 프로덕션 번들 빌드
npm run build

# 빌드 산출물 로컬 미리보기
npm run preview
```

---

## 3. 환경 변수 설정 (`.env`)

프론트엔드 루트의 `.env` 파일에서 백엔드 API 주소를 단일 진입점으로 설정합니다:

```env
VITE_API_URL=http://127.0.0.1:8000
```
*(예시 템플릿: `.env.example`)*

---

## 4. 아키텍처 및 기본 지도(Basemap) 정책

- **기본 지도(Basemap)**:
  - **Phase 5A 로컬 검증**: 별도의 API 키나 인증 토큰이 필요 없고 워터마크가 없는 **OpenStreetMap 표준 래스터 타일**(`https://tile.openstreetmap.org/{z}/{x}/{y}.png`)을 기본 적용하였습니다.
  - **저작권 표기 (Attribution)**: `© OpenStreetMap contributors`
  - **향후 상용 배포용 지도 공급자 선정**: 고해상도 벡터 타일 또는 3D 건물 익스트루전을 위한 상용/자체 호스팅 지도 공급자(Mapbox, Protomaps, VWorld, Maptiler 등)는 **Phase 5B 또는 프로덕션 배포 단계에서 별도로 선정**하여 적용합니다.
- **연동 엔드포인트**:
  - `GET /api/v1/analytics/summary`: 전국 735,185건 외식업 시장 요약
  - `GET /api/v1/spatial/density/grid?sigungu_code=11215`: 광진구 100m 정밀 밀집도 격자 (2D 프리뷰 서클 레이어 및 팝업)
  - `GET /api/v1/spatial/hotspots`: 상권 핫스팟 Top 5 목록 및 카메라 이동 (`jumpTo` / `flyTo`)

