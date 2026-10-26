"""
Stage 4E: FastAPI 메인 애플리케이션 진입점
프로젝트: D:/Franchise_Dashboard
위치: src/stage4e/api/main.py

실행:
    python -m uvicorn src.stage4e.api.main:app --host 0.0.0.0 --port 8000
"""

import os
import sys
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from src.stage4e.api.routers import summary, regions, categories, brands, spatial, ftc_macro, system
from scripts.restore_db import restore_analytics_db

app = FastAPI(
    title="Franchise Dashboard Spatial & Business Analytics API",
    description="""
    대한민국 외식 프랜차이즈 시장 분석 3D GIS 대시보드 백엔드 API (Phase 4 Stage 4E / Phase 5B)
    
    주요 기능:
    - 전국 735,185개 고유 외식업 점포 전수 대사 및 분석
    - 16개 시도 및 256개 시군구 다차원 공간 집계
    - 8대 대분류 및 48대 중분류 시장 점유율 및 모호 분류(104,060건) 필터링
    - 5,062개 브랜드 후보 검색 및 지역별 침투율/경쟁도 분석
    - MapLibre / deck.gl 호환 바운딩 박스(BBOX) GeoJSON 점포 스트리밍
    - 3D GIS 100m 밀집도 격자 기둥 (ColumnLayer) 및 상권 핫스팟 드론 비행 투어
    - [Phase 5B] 공정거래위원회 4개년(2023~2026) 외식업 거시통계 및 창업비용 벤치마크 통합
    """,
    version="1.1.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS 정책:
# - 운영 환경 (ENVIRONMENT=production): 동일 출처(Same-Origin) 전용
#   -> CORS_ORIGINS 미지정 시 교차 출처 미들웨어를 비활성화하여 외부 임의 출처를 전면 차단
#   -> CORS_ORIGINS 지정 시 해당 화이트리스트 도메인만 허용
# - 개발 환경 (기본값, ENVIRONMENT != "production" 또는 ALLOW_DEV_CORS=1):
#   -> 로컬 개발 프론트엔드 포트(5173, 4173 등)에 대한 CORS 자동 허용 (기존 개발 워크플로우 100% 보장)
environment = os.getenv("ENVIRONMENT", "development").strip().lower()
cors_env = os.getenv("CORS_ORIGINS", "").strip()
allow_dev_cors = os.getenv("ALLOW_DEV_CORS", "").strip().lower() in ("1", "true", "yes")

if cors_env:
    cors_origins = [o.strip() for o in cors_env.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
elif environment != "production" or allow_dev_cors:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:4173",
            "http://127.0.0.1:4173",
        ],
        allow_origin_regex=r"^https?://.*",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# 라우터 등록
app.include_router(summary.router)
app.include_router(regions.router)
app.include_router(categories.router)
app.include_router(brands.router)
app.include_router(spatial.router)
app.include_router(ftc_macro.router)
app.include_router(system.router)


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    return JSONResponse(
        status_code=400,
        content={"detail": str(exc), "status": 400}
    )


@app.on_event("startup")
def startup_event():
    """서버 시작 시 데이터베이스 존재 여부를 확인하고 청크로부터 자동 복원합니다."""
    try:
        restore_analytics_db()
    except Exception as e:
        print(f"[경고] DB 자동 복원 확인 중 오류: {e}")


@app.get("/api/health", tags=["Health Check"])
def health_check():
    """API 서비스 상태 및 기본 메타데이터를 반환합니다."""
    return {
        "status": "healthy",
        "service": "Franchise Dashboard Analytics & Spatial Engine",
        "version": "1.1.0",
        "data_reference_month": "2026-07",
        "total_stores_universe": 735185,
        "provinces": 16,
        "districts": 256,
        "taxonomy": "8 Major / 48 Mid Categories",
        "docs_url": "/docs",
        "timestamp": datetime.now().isoformat()
    }


# 프론트엔드 정적 파일 서빙 및 SPA 라우팅 지원 (Render / 단일 배포 컨테이너 대응)
DIST_DIR = BASE_DIR / "frontend" / "dist"
ASSETS_DIR = DIST_DIR / "assets"

if ASSETS_DIR.exists():
    app.mount("/assets", StaticFiles(directory=str(ASSETS_DIR)), name="assets")


@app.get("/", include_in_schema=False)
async def root_endpoint(request: Request):
    """루트 요청: 브라우저(HTML) 요청 시 SPA index.html을 서빙하고, API 클라이언트(JSON) 요청 시 헬스체크를 반환합니다."""
    accept = request.headers.get("accept", "")
    index_file = DIST_DIR / "index.html"
    if "text/html" in accept and index_file.is_file():
        return FileResponse(index_file)
    if index_file.is_file() and "application/json" not in accept:
        return FileResponse(index_file)
    return health_check()


@app.get("/{full_path:path}", include_in_schema=False)
async def serve_spa_app(full_path: str):
    """
    프론트엔드 빌드 결과물(frontend/dist) 서빙 및 클라이언트 사이드 SPA 라우팅 지원
    API 라우트(/api/*), 문서(/docs) 외의 모든 요청을 index.html로 전달합니다.
    """
    # 1. dist 디렉터리 내 개별 정적 파일(favicon, manifest 등) 직접 매칭
    target_file = DIST_DIR / full_path
    if full_path and target_file.is_file():
        return FileResponse(target_file)

    # 2. SPA index.html 제공
    index_file = DIST_DIR / "index.html"
    if index_file.is_file():
        return FileResponse(index_file)

    # 3. 프론트엔드가 아직 빌드되지 않은 환경에서는 API 헬스체크 정보 반환
    return health_check()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.stage4e.api.main:app", host="0.0.0.0", port=8000, reload=True)
