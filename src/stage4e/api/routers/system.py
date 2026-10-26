"""
시스템 메타데이터 및 데이터 버전 상태 API 라우터
위치: src/stage4e/api/routers/system.py
"""

import json
from pathlib import Path
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

router = APIRouter(prefix="/api/v1/system", tags=["System & Versioning"])

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent
CONFIG_PATH = BASE_DIR / "config" / "data_versions.json"


class DataStatusResponse(BaseModel):
    active_version: str
    latest_available_version: str
    has_update: bool
    last_checked_at: Optional[str] = None
    total_stores: Optional[int] = None
    total_brands: Optional[int] = None


@router.get("/data-status", response_model=DataStatusResponse)
def get_data_status():
    """현재 서빙 중인 DB 버전 및 공공데이터 최신 업데이트 가능 여부를 조회합니다."""
    default_meta = {
        "active_version": "202610",
        "latest_checked_api_version": "202610",
        "has_update": False,
        "last_checked_at": None,
        "total_stores": 735185,
        "total_brands": 5063
    }
    
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                active_v = data.get("active_version", "202610")
                latest_v = data.get("latest_checked_api_version", active_v)
                has_up = data.get("has_update", False)
                checked_at = data.get("last_checked_at")
                
                # 활성 버전의 점포수/브랜드수 추출
                total_stores = 735185
                total_brands = 5063
                history = data.get("history", [])
                for item in history:
                    if item.get("version") == active_v:
                        total_stores = item.get("total_stores", total_stores)
                        total_brands = item.get("total_brands", total_brands)
                        break

                return DataStatusResponse(
                    active_version=active_v,
                    latest_available_version=latest_v,
                    has_update=has_up,
                    last_checked_at=checked_at,
                    total_stores=total_stores,
                    total_brands=total_brands
                )
        except Exception:
            pass

    return DataStatusResponse(
        active_version=default_meta["active_version"],
        latest_available_version=default_meta["latest_checked_api_version"],
        has_update=default_meta["has_update"],
        last_checked_at=default_meta["last_checked_at"],
        total_stores=default_meta["total_stores"],
        total_brands=default_meta["total_brands"]
    )
