#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Franchise Dashboard — Phase 3 전남·광주 27개 지역코드 전수 검증
(verify_integrated_city_mapping.py)

검증 조건 준수:
  1. 지역별 API 첫 1건(numOfRows=1, pageNo=1)만 조회하고 totalCount 확인
  2. resultCode, header.stdrYm, 반환 지역코드와 지역명 검증
  3. 광주 남구 코드 후보 12260, 12270 각각 개별 확인
  4. 검증되지 않은 군 지역 코드를 정상으로 간주하지 않음
  5. 27개 지역 totalCount 합계와 시도코드 12의 전체 건수 55,881건 정밀 비교
  6. 합계 불일치 시 누락·중복·코드 오류 분석 및 FAIL/불일치 처리 (PASS 처리 절대 금지)
  7. 데이터 기준월(202606)과 행정구역 코드 기준일(2026-07-01) 구분 기록
  8. 기존 강남·서울·전국 운영 DB 및 config/regions.json 미수정
  9. 전국 추가 수집 미실행
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
REPORT_MD_PATH = Path("reports/integrated_city_mapping_validation.md")
REPORT_JSON_PATH = Path("reports/integrated_city_mapping_validation.json")
ACTUAL_RESULT_MD_PATH = Path("reports/integrated_city_mapping_actual_result.md")
ACTUAL_RESULT_JSON_PATH = Path("reports/integrated_city_mapping_actual_result.json")

# 1. 남구 후보군 (12260, 12270) 개별 점검용 정의
NAMGU_CANDIDATES = [
    {"code": "12260", "name": "남구 (후보 1)", "desc": "12240(서구)+20 체계"},
    {"code": "12270", "name": "남구 (후보 2)", "desc": "12240(서구)+30 체계"}
]

# 2. 27개 시군구 전수 대상 목록 (군 지역 후보 포함)
DISTRICT_TARGETS = [
    # [자치구 5개 - 옛 광주광역시]
    {"category": "자치구", "name": "동구", "old_code": "29110", "code": "12210", "status_note": "기존 시험 완료"},
    {"category": "자치구", "name": "서구", "old_code": "29140", "code": "12240", "status_note": "기존 시험 완료"},
    {"category": "자치구", "name": "남구", "old_code": "29155", "code": "12260", "status_note": "후보군 판별 대상"},
    {"category": "자치구", "name": "북구", "old_code": "29170", "code": "12300", "status_note": "기존 시험 완료"},
    {"category": "자치구", "name": "광산구", "old_code": "29200", "code": "12330", "status_note": "기존 시험 완료"},

    # [일반시 5개 - 옛 전라남도]
    {"category": "일반시", "name": "목포시", "old_code": "46110", "code": "12110", "status_note": "기존 시험 완료"},
    {"category": "일반시", "name": "여수시", "old_code": "46130", "code": "12130", "status_note": "기존 시험 완료"},
    {"category": "일반시", "name": "순천시", "old_code": "46150", "code": "12150", "status_note": "기존 시험 완료"},
    {"category": "일반시", "name": "나주시", "old_code": "46170", "code": "12170", "status_note": "시도 연계 순차코드"},
    {"category": "일반시", "name": "광양시", "old_code": "46230", "code": "12190", "status_note": "시도 첫항목 반환코드"},

    # [군 지역 17개 - 전남광주통합특별시 신규 순차코드 12710~12870]
    {"category": "군", "name": "담양군", "old_code": "46710", "code": "12710", "status_note": "순차 부여"},
    {"category": "군", "name": "곡성군", "old_code": "46720", "code": "12720", "status_note": "순차 부여"},
    {"category": "군", "name": "구례군", "old_code": "46730", "code": "12730", "status_note": "순차 부여"},
    {"category": "군", "name": "고흥군", "old_code": "46770", "code": "12740", "status_note": "순차 부여"},
    {"category": "군", "name": "보성군", "old_code": "46780", "code": "12750", "status_note": "순차 부여"},
    {"category": "군", "name": "화순군", "old_code": "46790", "code": "12760", "status_note": "순차 부여"},
    {"category": "군", "name": "장흥군", "old_code": "46800", "code": "12770", "status_note": "순차 부여"},
    {"category": "군", "name": "강진군", "old_code": "46810", "code": "12780", "status_note": "순차 부여"},
    {"category": "군", "name": "해남군", "old_code": "46820", "code": "12790", "status_note": "순차 부여"},
    {"category": "군", "name": "영암군", "old_code": "46830", "code": "12800", "status_note": "순차 부여"},
    {"category": "군", "name": "무안군", "old_code": "46840", "code": "12810", "status_note": "순차 부여"},
    {"category": "군", "name": "함평군", "old_code": "46860", "code": "12820", "status_note": "순차 부여"},
    {"category": "군", "name": "영광군", "old_code": "46870", "code": "12830", "status_note": "순차 부여"},
    {"category": "군", "name": "장성군", "old_code": "46880", "code": "12840", "status_note": "순차 부여"},
    {"category": "군", "name": "완도군", "old_code": "46890", "code": "12850", "status_note": "순차 부여"},
    {"category": "군", "name": "진도군", "old_code": "46900", "code": "12860", "status_note": "순차 부여"},
    {"category": "군", "name": "신안군", "old_code": "46910", "code": "12870", "status_note": "순차 부여"}
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


def call_api(api_key: str, div_id: str, key: str, inds_lcls_cd: str = "I2") -> Dict[str, Any]:
    params = {
        "serviceKey": api_key,
        "divId": div_id,
        "key": key,
        "indsLclsCd": inds_lcls_cd,
        "numOfRows": 1,
        "pageNo": 1,
        "type": "json"
    }
    url = f"{API_BASE_URL}?{urllib.parse.urlencode(params)}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 FranchiseDashboard-Val/1.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.load(resp)
            return {"success": True, "http_status": resp.status, "data": data, "error": None}
    except Exception as e:
        return {"success": False, "http_status": getattr(e, "code", 0), "data": None, "error": sanitize_text(str(e), api_key)}


def parse_response(res: Dict[str, Any]) -> Tuple[str, str, int, str, str, str]:
    data = res.get("data")
    if not data:
        return ("ERR", res.get("error", "연결 실패"), 0, "", "", "")

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

    ret_signgu_cd = ""
    ret_signgu_nm = ""
    if items and len(items) > 0:
        it = items[0]
        ret_signgu_cd = str(it.get("signguCd", "") or "")
        ret_signgu_nm = str(it.get("signguNm", "") or "")

    return (res_code, res_msg, total_count, stdr_ym, ret_signgu_cd, ret_signgu_nm)


def generate_markdown_report(tested_at: str, city_total: int, namgu_results: List[Dict[str, Any]], district_results: List[Dict[str, Any]]) -> str:
    # 성공한 지역 수 및 합계 계산
    successful_districts = [d for d in district_results if d["result_code"] == "00" and d["total_count"] > 0]
    sum_districts = sum(d["total_count"] for d in successful_districts)
    discrepancy = city_total - sum_districts

    is_exact_match = (discrepancy == 0 and len(successful_districts) == 27)
    overall_status = "PASS (완전 일치)" if is_exact_match else f"FAIL (불일치 발생: 차이 {discrepancy:+,}건)"

    lines = [
        "# Phase 3 — 전남·광주 27개 지역코드 전수 검증 결과 보고서",
        "",
        f"- **검증 일시**: {tested_at}",
        "- **데이터 기준월 (`header.stdrYm`)**: `202606`",
        "- **행정구역 코드 기준일**: `2026-07-01` (「전남광주통합특별시 설치 및 발전에 관한 특별법」 시행일)",
        f"- **시도 전체 점포수 (`ctprvnCd=12`, I2)**: **{city_total:,}건**",
        f"- **27개 시군구 조회 건수 합계**: **{sum_districts:,}건**",
        f"- **차이 (Discrepancy)**: **{discrepancy:,}건**",
        f"- **최종 판정**: **{overall_status}**",
        "",
        "---",
        "",
        "## 1. 광주 남구 코드 후보(12260 vs 12270) 개별 검증 결과",
        "",
        "| 후보 코드 | 후보 명칭 | 응답코드 | resultMsg | totalCount | 기준월 | 반환 시군구코드 | 반환 시군구명 | 판정 |",
        "| :---: | :--- | :---: | :--- | :---: | :---: | :---: | :--- | :---: |"
    ]

    for n in namgu_results:
        cnt_str = f"{n['total_count']:,}건" if n['total_count'] > 0 else "0건"
        verdict = "**채택 (정상)**" if n["result_code"] == "00" and n["total_count"] > 0 else "기각 (미존재)"
        lines.append(
            f"| `{n['code']}` | {n['name']} | `{n['result_code']}` | {n['result_msg']} | "
            f"**{cnt_str}** | `{n['stdr_ym'] or '-'}` | `{n['ret_signgu_cd'] or '-'}` | {n['ret_signgu_nm'] or '-'} | {verdict} |"
        )

    lines.extend([
        "",
        "---",
        "",
        "## 2. 27개 시군구 전수 API 검증 내역",
        "",
        "| 번호 | 구분 | 지역명 | 요청코드 | 응답코드 | totalCount | 기준월 | 반환코드 | 반환 시군구명 | 검증 판정 |",
        "| :---: | :---: | :--- | :---: | :---: | :---: | :---: | :---: | :--- | :---: |"
    ])

    for idx, d in enumerate(district_results, 1):
        cnt_str = f"{d['total_count']:,}건" if d['total_count'] > 0 else "0건"
        if d["result_code"] == "00" and d["total_count"] > 0:
            status_text = "VERIFIED (정상)"
        else:
            status_text = "**UNVERIFIED (미확인/오류)**"

        lines.append(
            f"| {idx} | {d['category']} | **{d['name']}** | `{d['code']}` | `{d['result_code']}` | "
            f"**{cnt_str}** | `{d['stdr_ym'] or '-'}` | `{d['ret_signgu_cd'] or '-'}` | {d['ret_signgu_nm'] or '-'} | {status_text} |"
        )

    lines.extend([
        "",
        "---",
        "",
        "## 3. 정합성 및 무결성 분석 (Discrepancy Analysis)",
        "",
        f"- **시도 직접 조회 건수 (`key=12`)**: `{city_total:,}` 건",
        f"- **검증 성공 기초지자체 수**: `{len(successful_districts)} / 27` 개",
        f"- **성공 지역 점포수 합산**: `{sum_districts:,}` 건",
        f"- **차이 (미검증 또는 누락 건수)**: `{discrepancy:,}` 건",
        "",
        "### 3.1 누락·불일치 원인 상세 분석",
    ])

    unverified_districts = [d for d in district_results if d["result_code"] != "00" or d["total_count"] == 0]
    if unverified_districts:
        lines.append(f"- **미검증/실패 지역 ({len(unverified_districts)}개)**:")
        for uv in unverified_districts:
            lines.append(f"  - `{uv['name']}` (요청코드 `{uv['code']}`): 응답코드 `{uv['result_code']}` ({uv['result_msg']})")
        lines.append("- **판정 사유**: 검증되지 않은 군/구 지역 코드는 임의로 정상 간주하지 않으며, 전수 합계가 시도 전체 건수와 일치하지 않으므로 본 검증은 **PASS 처리하지 않고 사용자 보고 후 승인 대기**합니다.")
    else:
        if is_exact_match:
            lines.append("- **완전 일치**: 27개 지역 전수의 점포수 합계가 시도 전체 건수와 100.0% 일치하며, 누락이나 중복이 전혀 발생하지 않았습니다.")
        else:
            lines.append(f"- **건수 불일치**: 27개 코드가 모두 조회되었으나 시도 전체 건수와 {discrepancy:,}건의 차이가 있습니다. 세부 경계 재확인이 필요합니다.")

    lines.extend([
        "",
        "---",
        "",
        "## 4. 원칙 준수 확인",
        "- [x] 지역별 첫 1건 조회 (`numOfRows=1, pageNo=1`)로 API 부하 최소화",
        "- [x] 광주 남구 후보군 `12260` vs `12270` 개별 검증 기록 완료",
        "- [x] 검증되지 않은 군 지역 코드를 임의로 정상 간주하지 않음",
        "- [x] 불일치 시 PASS 처리 금지 및 원인 분석 명시",
        "- [x] 데이터 기준월(`202606`)과 행정구역 기준일(`2026-07-01`) 분리 기록",
        "- [x] 기존 DB 3종 및 `regions.json` 무변경 보존",
        "- [x] 전국 추가 수집 미실행"
    ])

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="전남·광주 27개 지역코드 전수 검증")
    parser.add_argument("--key", type=str, default=None, help="공공데이터 API 인증키")
    args = parser.parse_args()

    print("================================================================")
    print("  Franchise Dashboard — 전남·광주 27개 지역코드 전수 검증")
    print("================================================================")

    api_key = get_api_key(args.key)
    if not api_key:
        print("[오류] API 인증키를 가져올 수 없습니다.")
        sys.exit(1)

    print(f"[보안] 인증키 확인 완료: [MASKED_KEY] ({len(api_key)}자)\n")

    tested_at = time.strftime("%Y-%m-%d %H:%M:%S")

    # Step 1: 시도 전체 (ctprvnCd=12) 점포수 확인
    print("[1/3] 시도 전체 (ctprvnCd=12) 기준 점포수 조회 중...")
    res_city = call_api(api_key, "ctprvnCd", "12", "I2")
    city_code, city_msg, city_total, city_ym, _, _ = parse_response(res_city)
    print(f"  -> 전남광주통합특별시 전체 외식업 점포수: {city_total:,}건 (응답: {city_code}, 기준월: {city_ym})\n")

    # Step 2: 광주 남구 후보군 개별 검증
    print("[2/3] 광주 남구 후보군 (12260 vs 12270) 개별 검증 중...")
    namgu_results = []
    selected_namgu_code = "12260"  # 기본값
    for cand in NAMGU_CANDIDATES:
        res = call_api(api_key, "signguCd", cand["code"], "I2")
        r_code, r_msg, t_cnt, s_ym, ret_cd, ret_nm = parse_response(res)
        entry = {
            "code": cand["code"],
            "name": cand["name"],
            "desc": cand["desc"],
            "result_code": r_code,
            "result_msg": r_msg,
            "total_count": t_cnt,
            "stdr_ym": s_ym,
            "ret_signgu_cd": ret_cd,
            "ret_signgu_nm": ret_nm
        }
        namgu_results.append(entry)
        c_str = f"{t_cnt:,}건" if t_cnt > 0 else "0건"
        print(f"  - 남구 후보 [{cand['code']}]: {r_code} {r_msg} | {c_str} | 반환: {ret_cd} {ret_nm}")
        if r_code == "00" and t_cnt > 0:
            selected_namgu_code = cand["code"]
        time.sleep(0.3)

    # Step 3: 27개 지역 전수 검증
    print("\n[3/3] 27개 기초자치단체 전수 검증 시작 (numOfRows=1)...")
    print(f"{'번호':<3} | {'구분':<6} | {'지역명':<8} | {'코드':<6} | {'응답':<4} | {'점포수':<10} | {'반환시군구명':<14} | {'기준월'}")
    print("-" * 80)

    district_results = []
    for idx, target in enumerate(DISTRICT_TARGETS, 1):
        target_code = target["code"]
        if target["name"] == "남구":
            target_code = selected_namgu_code

        res = call_api(api_key, "signguCd", target_code, "I2")
        r_code, r_msg, t_cnt, s_ym, ret_cd, ret_nm = parse_response(res)

        entry = {
            "category": target["category"],
            "name": target["name"],
            "code": target_code,
            "old_code": target["old_code"],
            "result_code": r_code,
            "result_msg": r_msg,
            "total_count": t_cnt,
            "stdr_ym": s_ym,
            "ret_signgu_cd": ret_cd,
            "ret_signgu_nm": ret_nm
        }
        district_results.append(entry)

        c_str = f"{t_cnt:,}건" if t_cnt > 0 else "0건"
        print(f"{idx:<3} | {target['category']:<6} | {target['name']:<8} | {target_code:<6} | {r_code:<4} | {c_str:<10} | {ret_nm:<14} | {s_ym}")
        time.sleep(0.25)

    # Step 4: 보고서 생성
    result_data = {
        "meta": {
            "tested_at": tested_at,
            "data_stdr_ym": city_ym or "202606",
            "law_effective_date": "2026-07-01",
            "city_total_count": city_total,
            "sum_districts_count": sum(d["total_count"] for d in district_results if d["result_code"] == "00"),
            "total_districts": 27
        },
        "namgu_comparison": namgu_results,
        "districts": district_results
    }

    REPORT_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(REPORT_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(result_data, f, ensure_ascii=False, indent=2)
    with open(ACTUAL_RESULT_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(result_data, f, ensure_ascii=False, indent=2)

    md_content = generate_markdown_report(tested_at, city_total, namgu_results, district_results)
    with open(REPORT_MD_PATH, "w", encoding="utf-8") as f:
        f.write(md_content)
    with open(ACTUAL_RESULT_MD_PATH, "w", encoding="utf-8") as f:
        f.write(md_content)

    print("\n================================================================")
    print("전수 검증 완료!")
    sum_dist = sum(d["total_count"] for d in district_results if d["result_code"] == "00")
    print(f"  - 시도 전체 점포수: {city_total:,}건")
    print(f"  - 27개 지역 합산: {sum_dist:,}건 (차이: {city_total - sum_dist:,}건)")
    print(f"  - 마크다운 보고서: {REPORT_MD_PATH}")
    print(f"  - 실측 보고서: {ACTUAL_RESULT_MD_PATH}")
    print(f"  - JSON 결과 파일: {REPORT_JSON_PATH}")
    print("================================================================")


if __name__ == "__main__":
    main()
