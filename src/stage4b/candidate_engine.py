"""
Stage 4B: 브랜드 후보 추출, 매칭 및 신뢰도 판정 엔진 (고도화 버전)
프로젝트: D:/Franchise_Dashboard
위치: src/stage4b/candidate_engine.py
"""

import re
from typing import Dict, List, Any, Optional

from src.stage4b.brand_dictionary import (
    OFFICIAL_BRAND_SEEDS,
    BRAND_LOOKUP_DICT,
    GENERIC_FOOD_NOUNS,
    get_official_brand_by_clean_name
)

RULE_VERSION = "4B.1.0"

# 분리 기호 없이 붙어있는 지점명 꼬리 패턴 (예: "신당동점", "역삼1호점", "서대문역점", "본점")
ATTACHED_BRANCH_TAIL_PATTERN = re.compile(
    r"^[가-힣0-9a-zA-Z]{1,15}(?:점|호점|직영점|가맹점|역점|본점|분점|DT점|스퀘어|센터)$",
    re.IGNORECASE
)

# 사전 내 별칭들을 길이 내림차순(긴 문자열 우선 매칭)으로 정렬
SORTED_BRAND_ALIASES = sorted(
    BRAND_LOOKUP_DICT.keys(),
    key=len,
    reverse=True
)

def evaluate_store_candidate(
    store_norm: Dict[str, Any],
    bizes_id: str,
    inds_mcls_cd: Optional[str] = None,
    inds_scls_cd: Optional[str] = None,
    inds_mcls_nm: Optional[str] = None,
    inds_scls_nm: Optional[str] = None,
    cluster_store_count: int = 1
) -> List[Dict[str, Any]]:
    """
    정규화된 점포 상호 정보를 기반으로 브랜드 후보 매칭, 신뢰도 및 상태를 판정한다.
    
    다중 방어선:
    1. 외식업 일반명사 단독 상호 필터 (Stop-words)
    2. 공인 브랜드 사전 완전 일치 (EXACT_MATCH / NORMALIZED_MATCH)
    3. 붙어있는 지점 접미어 추출 일치 (PREFIX_BRAND + ATTACHED_BRANCH)
    4. 부정 키워드 및 일반 식당 접미어 오탐 필터 (Negative Keywords)
    5. 복합 상호 / 복수 브랜드 검출 (MULTI_BRAND_COMPLEX)
    6. 전국 10개 이상 동일 상호 클러스터링 (CLUSTER_10PLUS_MATCH)
    7. 10개 미만 단일 점포 독립 격리 (INDEPENDENT_BELOW_10)
    """
    core_nm = store_norm["normalized_core_nm"]
    clean_key = store_norm["clean_key"]
    branch_suffix = store_norm.get("branch_suffix")
    branch_pos = store_norm.get("branch_position", "NONE")
    raw_nm = store_norm.get("raw_bizes_nm", "")
    clean_raw = raw_nm.replace(" ", "").lower()

    # 직영점 / 가맹점 판정 (상호 또는 지점명에 명시된 경우만 인정)
    branch_op_type = "UNKNOWN"
    check_text = f"{raw_nm} {branch_suffix or ''}"
    if "직영" in check_text or "본사직영" in check_text:
        branch_op_type = "DIRECT_OPERATED"
    elif "가맹점" in check_text:
        branch_op_type = "FRANCHISE_STORE"

    # 1. 외식업 일반명사 단독 상호 검사 -> 무조건 독립 개인식당으로 격리
    if clean_key in GENERIC_FOOD_NOUNS or core_nm in GENERIC_FOOD_NOUNS:
        return [{
            "bizes_id": bizes_id,
            "candidate_brand_id": "NONE_INDEPENDENT",
            "brand_name_raw": core_nm,
            "category_major": inds_mcls_nm or "기타",
            "match_method": "GENERIC_NOUN_FILTERED",
            "confidence_score": 0.0,
            "store_verification_status": "INDEPENDENT_STORE",
            "franchisor_status": "INDEPENDENT",
            "branch_operation_type": branch_op_type,
            "is_primary_candidate": 1,
            "notes": f"외식업 일반명사 단독 상호('{core_nm}')로 브랜드 후보 제외",
            "rule_version": RULE_VERSION
        }]

    # 2. 공인 브랜드 사전 완전 일치 검사
    official_brand = get_official_brand_by_clean_name(clean_key)
    detected_brand_alias = None
    attached_branch_found = None

    if official_brand:
        detected_brand_alias = clean_key
    else:
        # 3. 붙어있는 지점명 분리 검사 (예: "본죽신당동점" -> brand="본죽", branch="신당동점")
        for alias in SORTED_BRAND_ALIASES:
            # 최소 2글자 이상 별칭
            if len(alias) >= 2 and clean_key.startswith(alias):
                remainder = clean_key[len(alias):]
                if ATTACHED_BRANCH_TAIL_PATTERN.match(remainder):
                    official_brand = BRAND_LOOKUP_DICT[alias]
                    detected_brand_alias = alias
                    attached_branch_found = remainder
                    break

    # 4. 공인 브랜드가 감지된 경우의 정밀 판정
    if official_brand:
        cand_id = official_brand["candidate_id"]
        brand_nm = official_brand["brand_name"]
        cat_major = official_brand["category_major"]
        neg_kws = official_brand.get("negative_keywords", [])

        # 4-1. 부정 키워드 (Negative Keywords) 탐지
        for neg in neg_kws:
            clean_neg = neg.replace(" ", "").lower()
            if clean_neg in clean_key or clean_neg in clean_raw:
                return [{
                    "bizes_id": bizes_id,
                    "candidate_brand_id": "NONE_INDEPENDENT",
                    "brand_name_raw": core_nm,
                    "category_major": cat_major,
                    "match_method": "NEGATIVE_KEYWORD_REJECTED",
                    "confidence_score": 0.1,
                    "store_verification_status": "REJECTED",
                    "franchisor_status": "INDEPENDENT",
                    "branch_operation_type": branch_op_type,
                    "is_primary_candidate": 1,
                    "notes": f"공인 브랜드 부정 키워드('{neg}') 감지로 오탐 차단",
                    "rule_version": RULE_VERSION
                }]

        # 4-2. 정상 일치 판정 (EXACT 또는 NORMALIZED)
        effective_branch = branch_suffix or attached_branch_found
        if effective_branch:
            method = "NORMALIZED_MATCH"
            score = 0.98
            notes = f"지점 접미어('{effective_branch}') 분리 후 공식 브랜드 완전 일치"
        else:
            method = "EXACT_MATCH"
            score = 1.00
            notes = "공식 브랜드 정식 명칭 완전 일치"

        return [{
            "bizes_id": bizes_id,
            "candidate_brand_id": cand_id,
            "brand_name_raw": brand_nm,
            "category_major": cat_major,
            "match_method": method,
            "confidence_score": score,
            "store_verification_status": "VERIFIED_AUTO",
            "franchisor_status": "OFFICIAL_FRANCHISEE",
            "branch_operation_type": branch_op_type,
            "is_primary_candidate": 1,
            "notes": notes,
            "rule_version": RULE_VERSION
        }]

    # 5. 복수 브랜드 또는 복합 상호 탐지 (예: 본죽&비빔밥, 교촌치킨&호프 등)
    matched_sub_brands = []
    for alias in SORTED_BRAND_ALIASES:
        if len(alias) >= 3 and alias in clean_key:
            b_def = BRAND_LOOKUP_DICT[alias]
            is_neg = any(neg.replace(" ", "").lower() in clean_key for neg in b_def.get("negative_keywords", []))
            if not is_neg and b_def not in matched_sub_brands:
                matched_sub_brands.append(b_def)

    if len(matched_sub_brands) > 1:
        candidates = []
        for idx, b_def in enumerate(matched_sub_brands):
            candidates.append({
                "bizes_id": bizes_id,
                "candidate_brand_id": b_def["candidate_id"],
                "brand_name_raw": b_def["brand_name"],
                "category_major": b_def["category_major"],
                "match_method": "MULTI_BRAND_COMPLEX",
                "confidence_score": 0.75 - (idx * 0.1),
                "store_verification_status": "REVIEW_REQUIRED",
                "franchisor_status": "UNCONFIRMED",
                "branch_operation_type": branch_op_type,
                "is_primary_candidate": 1 if idx == 0 else 0,
                "notes": f"복합 상호 내 복수 브랜드 검출 ({b_def['brand_name']})",
                "rule_version": RULE_VERSION
            })
        return candidates

    elif len(matched_sub_brands) == 1:
        b_def = matched_sub_brands[0]
        generic_suffixes = ["식당", "면옥", "한우", "갈비", "밥상", "포차", "주막", "국밥", "마을"]
        has_generic_suffix = any(gs in clean_key for gs in generic_suffixes)
        if has_generic_suffix:
            return [{
                "bizes_id": bizes_id,
                "candidate_brand_id": "NONE_INDEPENDENT",
                "brand_name_raw": core_nm,
                "category_major": b_def["category_major"],
                "match_method": "PARTIAL_GENERIC_SUSPECT",
                "confidence_score": 0.25,
                "store_verification_status": "REJECTED",
                "franchisor_status": "INDEPENDENT",
                "branch_operation_type": branch_op_type,
                "is_primary_candidate": 1,
                "notes": f"브랜드명 포함되나 일반음식 접미어 결합으로 오탐 제외",
                "rule_version": RULE_VERSION
            }]
        else:
            return [{
                "bizes_id": bizes_id,
                "candidate_brand_id": b_def["candidate_id"],
                "brand_name_raw": b_def["brand_name"],
                "category_major": b_def["category_major"],
                "match_method": "AMBIGUOUS_MATCH",
                "confidence_score": 0.70,
                "store_verification_status": "REVIEW_REQUIRED",
                "franchisor_status": "UNCONFIRMED",
                "branch_operation_type": branch_op_type,
                "is_primary_candidate": 1,
                "notes": f"브랜드명 포함 및 부가수식어 결합 상호 ('{core_nm}')",
                "rule_version": RULE_VERSION
            }]

    # 6. 전국 10개 이상 동일 상호 클러스터링 판정 (AGENTS.md 규칙)
    if cluster_store_count >= 10 and len(clean_key) >= 2:
        cluster_cand_id = f"CAN_CLUS_{clean_key[:12]}"
        return [{
            "bizes_id": bizes_id,
            "candidate_brand_id": cluster_cand_id,
            "brand_name_raw": core_nm,
            "category_major": inds_mcls_nm or "기타외식",
            "match_method": "CLUSTER_10PLUS_MATCH",
            "confidence_score": 0.85,
            "store_verification_status": "PROVISIONAL",
            "franchisor_status": "UNCONFIRMED",
            "branch_operation_type": branch_op_type,
            "is_primary_candidate": 1,
            "notes": f"전국 동일 상호 점포 수 {cluster_store_count}개로 후보 승격",
            "rule_version": RULE_VERSION
        }]

    # 7. 10개 미만 단일 점포 -> 독립 개인 식당
    return [{
        "bizes_id": bizes_id,
        "candidate_brand_id": "NONE_INDEPENDENT",
        "brand_name_raw": core_nm,
        "category_major": inds_mcls_nm or "기타",
        "match_method": "INDEPENDENT_BELOW_10",
        "confidence_score": 0.0,
        "store_verification_status": "INDEPENDENT_STORE",
        "franchisor_status": "INDEPENDENT",
        "branch_operation_type": branch_op_type,
        "is_primary_candidate": 1,
        "notes": f"전국 동일 상호 점포 수 {cluster_store_count}개로 독립 개인점포 분류",
        "rule_version": RULE_VERSION
    }]
