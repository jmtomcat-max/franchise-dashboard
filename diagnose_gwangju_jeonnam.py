#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Franchise Dashboard — Phase 3 광주·전남 API 조회 실패 원인 집중 진단기
(diagnose_gwangju_jeonnam.py)

목적:
  광주광역시(29) 및 전라남도(46)에서 발생하는 03 NODATA_ERROR의 원인을 다각도로 분석:
  1. 업종코드 I2 유무 비교 (I2 포함 vs 전체 업종)
  2. 행정구역 단위 비교 (시군구 signguCd vs 시도 ctprvnCd vs 행정동 adongCd)
  3. 타 오퍼레이션 비교 (storeListInDong vs storeZoneInAdmi vs storeZoneInRadius)
  4. 정상 대조군(서울 강남구 11680)과 동일 파라미터 비교 검증
"""

import os
import sys
import json
import time
import argparse
import getpass
import urllib.request
import urllib.parse
from pathlib import Path
from typing import Dict, Any, List, Optional

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_API_URL = "https://apis.data.go.kr/B553077/api/open/sdsc2"
REPORT_JSON_PATH = Path("reports/gwangju_jeonnam_diagnostic_report.json")
REPORT_MD_PATH = Path("reports/gwangju_jeonnam_diagnostic_summary.md")

TEST_CASES = [
    # 1. 업종코드 I2 포함 vs 제외 비교 (요구사항 3)
    {
        "group": "업종코드 비교",
        "name": "광주 동구 (I2 포함)",
        "operation": "storeListInDong",
        "params": {"divId": "signguCd", "key": "29110", "indsLclsCd": "I2"}
    },
    {
        "group": "업종코드 비교",
        "name": "광주 동구 (업종코드 제외/전체업종)",
        "operation": "storeListInDong",
        "params": {"divId": "signguCd", "key": "29110"}
    },
    {
        "group": "업종코드 비교",
        "name": "광주 북구 (I2 포함)",
        "operation": "storeListInDong",
        "params": {"divId": "signguCd", "key": "29170", "indsLclsCd": "I2"}
    },
    {
        "group": "업종코드 비교",
        "name": "광주 북구 (업종코드 제외/전체업종)",
        "operation": "storeListInDong",
        "params": {"divId": "signguCd", "key": "29170"}
    },
    {
        "group": "업종코드 비교",
        "name": "전남 목포시 (I2 포함)",
        "operation": "storeListInDong",
        "params": {"divId": "signguCd", "key": "46110", "indsLclsCd": "I2"}
    },
    {
        "group": "업종코드 비교",
        "name": "전남 목포시 (업종코드 제외/전체업종)",
        "operation": "storeListInDong",
        "params": {"divId": "signguCd", "key": "46110"}
    },
    {
        "group": "업종코드 비교",
        "name": "전남 순천시 (I2 포함)",
        "operation": "storeListInDong",
        "params": {"divId": "signguCd", "key": "46150", "indsLclsCd": "I2"}
    },
    {
        "group": "업종코드 비교",
        "name": "전남 순천시 (업종코드 제외/전체업종)",
        "operation": "storeListInDong",
        "params": {"divId": "signguCd", "key": "46150"}
    },

    # 2. 시도 단위(ctprvnCd) 조회 비교 (요구사항 2, 3)
    {
        "group": "시도단위 비교",
        "name": "광주광역시 전체 (I2 포함)",
        "operation": "storeListInDong",
        "params": {"divId": "ctprvnCd", "key": "29", "indsLclsCd": "I2"}
    },
    {
        "group": "시도단위 비교",
        "name": "광주광역시 전체 (업종코드 제외)",
        "operation": "storeListInDong",
        "params": {"divId": "ctprvnCd", "key": "29"}
    },
    {
        "group": "시도단위 비교",
        "name": "전라남도 전체 (I2 포함)",
        "operation": "storeListInDong",
        "params": {"divId": "ctprvnCd", "key": "46", "indsLclsCd": "I2"}
    },
    {
        "group": "시도단위 비교",
        "name": "전라남도 전체 (업종코드 제외)",
        "operation": "storeListInDong",
        "params": {"divId": "ctprvnCd", "key": "46"}
    },

    # 3. 행정동 단위(adongCd) 조회 테스트 (요구사항 4)
    {
        "group": "행정동단위 조회",
        "name": "광주 동구 충장동 (adongCd 2911052500, I2)",
        "operation": "storeListInDong",
        "params": {"divId": "adongCd", "key": "2911052500", "indsLclsCd": "I2"}
    },
    {
        "group": "행정동단위 조회",
        "name": "광주 동구 충장동 (adongCd 2911052500, 업종제외)",
        "operation": "storeListInDong",
        "params": {"divId": "adongCd", "key": "2911052500"}
    },
    {
        "group": "행정동단위 조회",
        "name": "전남 목포시 목원동 (adongCd 4611053000, I2)",
        "operation": "storeListInDong",
        "params": {"divId": "adongCd", "key": "4611053000", "indsLclsCd": "I2"}
    },
    {
        "group": "행정동단위 조회",
        "name": "전남 목포시 목원동 (adongCd 4611053000, 업종제외)",
        "operation": "storeListInDong",
        "params": {"divId": "adongCd", "key": "4611053000"}
    },

    # 4. 타 오퍼레이션 검증 (요구사항 4)
    {
        "group": "타 오퍼레이션",
        "name": "광주 동구 상권조회 (storeZoneInAdmi)",
        "operation": "storeZoneInAdmi",
        "params": {"divId": "signguCd", "key": "29110"}
    },
    {
        "group": "타 오퍼레이션",
        "name": "광주 전체 상권조회 (storeZoneInAdmi)",
        "operation": "storeZoneInAdmi",
        "params": {"divId": "ctprvnCd", "key": "29"}
    },
    {
        "group": "타 오퍼레이션",
        "name": "전남 목포 상권조회 (storeZoneInAdmi)",
        "operation": "storeZoneInAdmi",
        "params": {"divId": "signguCd", "key": "46110"}
    },
    {
        "group": "타 오퍼레이션",
        "name": "광주시청 반경 1km 상권조회 (storeZoneInRadius)",
        "operation": "storeZoneInRadius",
        "params": {"cx": "126.8526", "cy": "35.1595", "radius": "1000"}
    },

    # 5. 정상 대조군 (서울 강남구 11680)
    {
        "group": "정상 대조군",
        "name": "서울 강남구 점포조회 (storeListInDong, I2)",
        "operation": "storeListInDong",
        "params": {"divId": "signguCd", "key": "11680", "indsLclsCd": "I2"}
    },
    {
        "group": "정상 대조군",
        "name": "서울 강남구 상권조회 (storeZoneInAdmi)",
        "operation": "storeZoneInAdmi",
        "params": {"divId": "signguCd", "key": "11680"}
    }
]


def sanitize_text(text: str, api_key: str) -> str:
    if not api_key:
        return text
    clean = text.replace(api_key, "[MASKED_KEY]")
    quoted = urllib.parse.quote(api_key, safe="")
    if quoted in clean:
        clean = clean.replace(quoted, "[MASKED_KEY]")
    return clean


def get_api_key(cli_key: Optional[str] = None) -> str:
    if cli_key and cli_key.strip():
        return cli_key.strip()

    for k in ["SERVICE_KEY", "DATA_GO_KR_API_KEY", "PUBLIC_DATA_API_KEY"]:
        v = os.getenv(k)
        if v and v.strip():
            return v.strip()

    env_path = Path(".env")
    if env_path.exists():
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" in line:
                        k, v = line.split("=", 1)
                        if k.strip() in ["SERVICE_KEY", "DATA_GO_KR_API_KEY", "PUBLIC_DATA_API_KEY"] and v.strip():
                            return v.strip().strip('"').strip("'")
        except Exception:
            pass

    try:
        user_key = getpass.getpass("공공데이터포털 API Key (비공개 입력): ").strip()
        if user_key:
            return user_key
    except Exception:
        pass

    return ""


def call_api(api_key: str, operation: str, query_params: Dict[str, Any]) -> Dict[str, Any]:
    params = {"serviceKey": api_key, "numOfRows": 10, "pageNo": 1, "type": "json"}
    params.update(query_params)
    url = f"{BASE_API_URL}/{operation}?{urllib.parse.urlencode(params)}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 FranchiseDashboard-GJ/1.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.load(resp)
            return {"success": True, "http_status": resp.status, "data": data, "error": None}
    except Exception as e:
        return {"success": False, "http_status": getattr(e, "code", 0), "data": None, "error": sanitize_text(str(e), api_key)}


def generate_markdown(tested_at: str, results: List[Dict[str, Any]]) -> str:
    lines = [
        "# Phase 3 — 광주·전남 API 조회 실패 원인 집중 분석 보고서",
        "",
        f"- **검증 일시**: {tested_at}",
        "- **분석 목적**: 광주광역시 및 전라남도 소진공 API 03 NODATA_ERROR 발생 원인 정밀 규명",
        "- **Base Endpoint**: `https://apis.data.go.kr/B553077/api/open/sdsc2`",
        "",
        "---",
        "",
        "## 1. 테스트 결과 요약표",
        "",
        "| 그룹 | 테스트 명칭 | 오퍼레이션 | 요청 파라미터 | 응답코드 | resultMsg | totalCount | 기준월 | 반환 지역정보 |",
        "| :--- | :--- | :---: | :--- | :---: | :--- | :---: | :---: | :--- |"
    ]

    for r in results:
        t_cnt = f"{r['total_count']:,}건" if r['total_count'] > 0 else "0건"
        p_str = ", ".join([f"{k}={v}" for k, v in r['params'].items()])
        loc = f"{r['ctprvn_nm']} {r['signgu_nm']}".strip() or "-"
        lines.append(
            f"| {r['group']} | {r['name']} | `{r['operation']}` | `{p_str}` | "
            f"`{r['result_code']}` | {r['result_msg']} | **{t_cnt}** | "
            f"`{r['stdr_ym'] or '-'}` | {loc} |"
        )

    lines.extend([
        "",
        "---",
        "",
        "## 2. 심층 분석 및 원인 판정",
        "",
        "### 2.1 업종코드(I2) 필터 유무에 따른 영향 분석",
        "- 업종코드 `I2`를 생략(전체 업종 조회)했을 때의 응답 여부를 통해 외식업 데이터 누락인지, 광주/전남 전체 데이터의 엔드포인트 미서비스인지 판별.",
        "",
        "### 2.2 행정구역 구분자(`divId`) 및 타 오퍼레이션 분석",
        "- `signguCd` vs `ctprvnCd` vs `adongCd` 응답 비교.",
        "- `storeZoneInAdmi`(상권조회)의 동작 여부를 통해 상권 DB와 점포 DB의 서비스 상태 대조.",
        "",
        "### 2.3 광주·전남 데이터 확보 가능 여부 및 대체 수집 방안",
        "- **방법 1 (Open API 내부 해결)**: `adongCd` 또는 `ctprvnCd` 조회를 통한 데이터 수집 가능성.",
        "- **방법 2 (공공데이터포털 파일데이터 연계)**: 공공데이터포털에서 공식 제공하는 '소상공인시장진흥공단_상가(상권)정보' 광주/전남 최신 CSV 파일 연계를 통한 100% 무결성 데이터 확보."
    ])

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="광주·전남 API 조회 실패 원인 집중 진단기")
    parser.add_argument("--key", type=str, default=None, help="공공데이터 API 인증키 (선택 사항)")
    args = parser.parse_args()

    print("================================================================")
    print("  Franchise Dashboard — 광주·전남 API 조회 실패 원인 집중 분석")
    print("================================================================")

    api_key = get_api_key(args.key)
    if not api_key:
        print("[오류] API 인증키를 가져올 수 없습니다.")
        sys.exit(1)

    print(f"[보안] 인증키 확인 완료: [MASKED_KEY] ({len(api_key)}자)\n")

    tested_at = time.strftime("%Y-%m-%d %H:%M:%S")
    results = []

    print(f"{'그룹':<10} | {'테스트 명칭':<28} | {'오퍼레이션':<18} | {'응답':<4} | {'totalCount':<10} | {'기준월':<6} | {'반환정보'}")
    print("-" * 115)

    for case in TEST_CASES:
        res = call_api(api_key, case["operation"], case["params"])
        data = res["data"]
        error = res["error"]

        res_code = "ERR"
        res_msg = error or ""
        total_count = 0
        stdr_ym = ""
        ret_signgu_cd = ""
        ret_signgu_nm = ""
        ret_ctprvn_nm = ""

        if data:
            header = data.get("header", {})
            res_code = str(header.get("resultCode", ""))
            res_msg = str(header.get("resultMsg", ""))
            stdr_ym = str(header.get("stdrYm", "") or "")

            body = data.get("body", {})
            total_count = int(body.get("totalCount", 0))
            items = body.get("items", [])
            if isinstance(items, dict):
                items = items.get("item", [])
            if isinstance(items, dict):
                items = [items]

            if items and len(items) > 0:
                it = items[0]
                ret_signgu_cd = str(it.get("signguCd", "") or "")
                ret_signgu_nm = str(it.get("signguNm", "") or it.get("mainTrarNm", "") or "")
                ret_ctprvn_nm = str(it.get("ctprvnNm", "") or "")

        entry = {
            "group": case["group"],
            "name": case["name"],
            "operation": case["operation"],
            "params": case["params"],
            "http_status": res["http_status"],
            "result_code": res_code,
            "result_msg": res_msg,
            "total_count": total_count,
            "stdr_ym": stdr_ym,
            "signgu_cd": ret_signgu_cd,
            "signgu_nm": ret_signgu_nm,
            "ctprvn_nm": ret_ctprvn_nm
        }
        results.append(entry)

        count_str = f"{total_count:,}건" if total_count > 0 else "0건"
        loc_str = f"{ret_ctprvn_nm} {ret_signgu_nm}".strip() or "-"
        print(f"{case['group']:<10} | {case['name']:<28} | {case['operation']:<18} | {res_code:<4} | {count_str:<10} | {stdr_ym:<6} | {loc_str}")
        time.sleep(0.5)

    # 보고서 저장
    REPORT_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(REPORT_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump({"meta": {"tested_at": tested_at, "total_cases": len(results)}, "results": results}, f, ensure_ascii=False, indent=2)

    summary_md = generate_markdown(tested_at, results)
    with open(REPORT_MD_PATH, "w", encoding="utf-8") as f:
        f.write(summary_md)

    print("\n================================================================")
    print("진단 완료!")
    print(f"  - JSON 보고서: {REPORT_JSON_PATH}")
    print(f"  - 마크다운 요약: {REPORT_MD_PATH}")
    print("================================================================")


if __name__ == "__main__":
    main()
