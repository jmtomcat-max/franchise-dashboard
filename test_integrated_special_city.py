#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Franchise Dashboard — Phase 3 전남광주통합특별시(12) 점포조회 실증 테스트
(test_integrated_special_city.py)

목적:
  2026.07.01 공식 출범한 '전남광주통합특별시'(시도코드 12)의
  확인된 신규 시군구 코드로 소진공 storeListInDong API 1페이지(10건) 소량 시험 조회
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

API_BASE_URL = "https://apis.data.go.kr/B553077/api/open/sdsc2/storeListInDong"
REPORT_JSON_PATH = Path("reports/integrated_city_test_report.json")
REPORT_MD_PATH = Path("reports/integrated_city_test_summary.md")

TEST_CASES = [
    # 1. 시도 단위 (전남광주통합특별시 전체)
    {
        "name": "전남광주통합특별시 전체 (시도단위)",
        "divId": "ctprvnCd",
        "key": "12",
        "indsLclsCd": "I2"
    },
    # 2. 자치구 (옛 광주 지역)
    {
        "name": "전남광주통합특별시 서구 (확인코드 12240)",
        "divId": "signguCd",
        "key": "12240",
        "indsLclsCd": "I2"
    },
    {
        "name": "전남광주통합특별시 동구 (확인코드 12210)",
        "divId": "signguCd",
        "key": "12210",
        "indsLclsCd": "I2"
    },
    {
        "name": "전남광주통합특별시 북구 (확인코드 12300)",
        "divId": "signguCd",
        "key": "12300",
        "indsLclsCd": "I2"
    },
    {
        "name": "전남광주통합특별시 광산구 (확인코드 12330)",
        "divId": "signguCd",
        "key": "12330",
        "indsLclsCd": "I2"
    },
    # 3. 시 단위 (옛 전남 지역)
    {
        "name": "전남광주통합특별시 목포시 (확인코드 12110)",
        "divId": "signguCd",
        "key": "12110",
        "indsLclsCd": "I2"
    },
    {
        "name": "전남광주통합특별시 여수시 (확인코드 12130)",
        "divId": "signguCd",
        "key": "12130",
        "indsLclsCd": "I2"
    },
    {
        "name": "전남광주통합특별시 순천시 (확인코드 12150)",
        "divId": "signguCd",
        "key": "12150",
        "indsLclsCd": "I2"
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


def call_api(api_key: str, div_id: str, key: str, inds_lcls_cd: str) -> Dict[str, Any]:
    params = {
        "serviceKey": api_key,
        "divId": div_id,
        "key": key,
        "indsLclsCd": inds_lcls_cd,
        "numOfRows": 10,
        "pageNo": 1,
        "type": "json"
    }
    url = f"{API_BASE_URL}?{urllib.parse.urlencode(params)}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 FranchiseDashboard-12/1.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.load(resp)
            return {"success": True, "http_status": resp.status, "data": data, "error": None}
    except Exception as e:
        return {"success": False, "http_status": getattr(e, "code", 0), "data": None, "error": sanitize_text(str(e), api_key)}


def generate_markdown(tested_at: str, results: List[Dict[str, Any]]) -> str:
    lines = [
        "# Phase 3 — 전남광주통합특별시(12) 점포조회 API 실증 검증 보고서",
        "",
        f"- **검증 일시**: {tested_at}",
        "- **조회 대상**: 전남광주통합특별시(시도 12) 주요 시군구 8대 표본",
        "- **오퍼레이션**: `storeListInDong` (외식업 I2)",
        "",
        "---",
        "",
        "## 1. 테스트 결과 요약표",
        "",
        "| 테스트 명칭 | divId | 요청Key | 응답코드 | resultMsg | totalCount | 기준월 | 반환 시군구코드 | 반환 지역명 |",
        "| :--- | :---: | :---: | :---: | :--- | :---: | :---: | :---: | :--- |"
    ]

    for r in results:
        t_cnt = f"{r['total_count']:,}건" if r['total_count'] > 0 else "0건"
        loc = f"{r['ctprvn_nm']} {r['signgu_nm']}".strip() or "-"
        lines.append(
            f"| {r['name']} | `{r['divId']}` | `{r['key']}` | "
            f"`{r['result_code']}` | {r['result_msg']} | **{t_cnt}** | "
            f"`{r['stdr_ym'] or '-'}` | `{r['signgu_cd'] or '-'}` | {loc} |"
        )

    lines.extend([
        "",
        "---",
        "",
        "## 2. 결론 및 종합 판단",
        "- 전남광주통합특별시 코드 체계(`12xxx`)가 점포조회 API(`storeListInDong`)에서 동작하는지 실측 결과에 따라 수집 파이프라인의 방향 확정."
    ])

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="전남광주통합특별시 점포조회 실증 테스트")
    parser.add_argument("--key", type=str, default=None, help="공공데이터 API 인증키")
    args = parser.parse_args()

    print("================================================================")
    print("  Franchise Dashboard — 전남광주통합특별시(12) 점포조회 실증 테스트")
    print("================================================================")

    api_key = get_api_key(args.key)
    if not api_key:
        print("[오류] API 인증키를 가져올 수 없습니다.")
        sys.exit(1)

    print(f"[보안] 인증키 확인 완료: [MASKED_KEY] ({len(api_key)}자)\n")

    tested_at = time.strftime("%Y-%m-%d %H:%M:%S")
    results = []

    print(f"{'테스트 명칭':<32} | {'divId':<9} | {'Key':<6} | {'응답':<4} | {'totalCount':<10} | {'기준월':<6} | {'반환정보'}")
    print("-" * 105)

    for case in TEST_CASES:
        res = call_api(api_key, case["divId"], case["key"], case["indsLclsCd"])
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
                ret_signgu_nm = str(it.get("signguNm", "") or "")
                ret_ctprvn_nm = str(it.get("ctprvnNm", "") or "")

        entry = {
            "name": case["name"],
            "divId": case["divId"],
            "key": case["key"],
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
        print(f"{case['name']:<32} | {case['divId']:<9} | {case['key']:<6} | {res_code:<4} | {count_str:<10} | {stdr_ym:<6} | {loc_str}")
        time.sleep(0.5)

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
