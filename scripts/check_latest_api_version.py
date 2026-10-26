#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
소상공인시장진흥공단 공공데이터 최신 기준월 감지 스크립트
위치: scripts/check_latest_api_version.py

공공 API에서 최소 1건(numOfRows=1)을 조회하여 헤더의 'stdrYm'(기준년월)을 추출하고,
현재 활성화된 DB 버전(config/data_versions.json)과 비교합니다.
"""

import sys
import os
import json
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

# Windows UTF-8 출력 보장
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = BASE_DIR / "config" / "data_versions.json"
API_URL = "https://apis.data.go.kr/B553077/api/open/sdsc2/storeListInDong"


def get_api_key() -> str:
    """환경변수 및 .env에서 공공데이터 API 키를 추출합니다."""
    # 1. 환경변수 우선
    key = os.getenv("DATA_GO_KR_API_KEY") or os.getenv("SERVICE_KEY") or os.getenv("PUBLIC_DATA_API_KEY")
    if key:
        return key.strip()

    # 2. .env 파일 확인
    env_file = BASE_DIR / ".env"
    if env_file.exists():
        try:
            with open(env_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("#") or "=" not in line:
                        continue
                    k, v = line.split("=", 1)
                    k = k.strip()
                    v = v.strip().strip("'").strip('"')
                    if k in ("DATA_GO_KR_API_KEY", "SERVICE_KEY", "PUBLIC_DATA_API_KEY", "API_KEY"):
                        return v
        except Exception:
            pass
    return ""


def fetch_latest_api_stdr_ym(api_key: str) -> str:
    """소상공인 API에서 최신 기준년월(stdrYm) 1건을 조회합니다."""
    params = {
        "serviceKey": api_key,
        "divId": "signguCd",
        "key": "11680", # 강남구 코드 기준 경량 샘플링
        "indsLclsCd": "I2",
        "numOfRows": 1,
        "pageNo": 1,
        "type": "json"
    }
    url = API_URL + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "FranchiseDashboardWatcher/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    header = data.get("header", {})
    if str(header.get("resultCode")) != "00":
        raise RuntimeError(f"API 응답 오류: {header}")

    stdr_ym = header.get("stdrYm")
    if not stdr_ym:
        raise ValueError("API 응답 헤더에 'stdrYm' 필드가 존재하지 않습니다.")
    return str(stdr_ym).strip()


def main():
    import argparse
    parser = argparse.ArgumentParser(description="소상공인 공공데이터 최신 등록월 감지기")
    parser.add_argument("--mock-version", type=str, default=None, help="테스트용 모의 최신 버전 (예: 202611)")
    args = parser.parse_args()

    # 1. 현재 로컬 버전 메타데이터 읽기
    if not CONFIG_PATH.exists():
        print(f"[ERROR] 설정 파일이 존재하지 않습니다: {CONFIG_PATH}", file=sys.stderr)
        sys.exit(1)

    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        meta = json.load(f)

    active_version = meta.get("active_version", "unknown")

    # 2. 최신 API 버전 획득
    if args.mock_version:
        latest_api_version = args.mock_version
        print(f"[MOCK] 테스트 모의 최신 버전 사용: {latest_api_version}")
    else:
        api_key = get_api_key()
        if not api_key:
            print("[WARN] 공공데이터 API 키가 설정되지 않았습니다. 현재 버전을 유지합니다.")
            latest_api_version = active_version
        else:
            try:
                latest_api_version = fetch_latest_api_stdr_ym(api_key)
            except Exception as e:
                print(f"[WARN] API 호출 실패: {e}. 현재 버전을 유지합니다.")
                latest_api_version = active_version

    # 3. 버전 비교 및 메타데이터 업데이트
    now_iso = datetime.now(timezone.utc).isoformat()
    has_update = str(latest_api_version) > str(active_version)

    meta["latest_checked_api_version"] = latest_api_version
    meta["last_checked_at"] = now_iso
    meta["has_update"] = has_update

    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)

    result = {
        "active_version": active_version,
        "latest_api_version": latest_api_version,
        "has_update": has_update,
        "checked_at": now_iso
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))

    # 새 데이터가 감지되면 종료 코드 10 반환 (GitHub Actions 등에서 분기용)
    if has_update:
        sys.exit(10)
    sys.exit(0)


if __name__ == "__main__":
    main()
