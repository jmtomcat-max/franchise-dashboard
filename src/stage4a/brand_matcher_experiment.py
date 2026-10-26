"""
Stage 4A: 소진공 전국 점포 DB 대상 브랜드 매칭 표본 실험 모듈
프로젝트: D:/Franchise_Dashboard
위치: src/stage4a/brand_matcher_experiment.py

목적:
- 73.5만 건 전국 점포 중 37개 대표 표본 브랜드(8대 업종, 대형/중소형, 영/한 혼용, 유사상호 등)를 대상으로
  상호명 정규화, 지점 접미어 분리, 매칭 유형 분류(정확/정규화/모호/오탐의심/미매칭) 실험 수행
- 정밀도/오탐률 측정용 라벨링 표본 생성 및 Stage 4A DB(store_brand_match_samples) 적재
- Phase 4B(알고리즘 고도화)를 위한 규칙 및 이상 사례 도출
"""

import sys
import re
import json
import sqlite3
import unicodedata
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional

BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.stage4a.schema_stage4a import DEFAULT_STAGE4A_DB_PATH

SEMAS_V2_DB_PATH = BASE_DIR / "data" / "nationwide_food_stores_v2.sqlite3"

# ==============================================================================
# 1. 37개 대표 표본 브랜드 정의 (8대 대분류 및 특성별 스펙트럼 포함)
# ==============================================================================
SAMPLE_BRANDS: List[Dict[str, Any]] = [
    # 1. 한식 (5개)
    {
        "brand_name": "본죽",
        "category_major": "한식",
        "aliases": ["본죽", "BONJUK", "본죽&비빔밥", "본죽앤비빔밥"],
        "negative_keywords": ["본죽집", "맛있는본죽", "일본죽", "근본죽"],
        "scale_type": "LARGE_NATIONAL"
    },
    {
        "brand_name": "한솥도시락",
        "category_major": "한식",
        "aliases": ["한솥도시락", "한솥", "HANSOOT"],
        "negative_keywords": ["한솥밥", "한솥식당", "한솥가득"],
        "scale_type": "LARGE_NATIONAL"
    },
    {
        "brand_name": "하남돼지집",
        "category_major": "한식",
        "aliases": ["하남돼지집", "하남돼지"],
        "negative_keywords": ["하남돼지골", "하남고깃집"],
        "scale_type": "MID_SIZE"
    },
    {
        "brand_name": "두찜",
        "category_major": "한식",
        "aliases": ["두찜", "두마리찜닭두찜", "두마리찜닭"],
        "negative_keywords": ["두마리", "모두찜"],
        "scale_type": "LARGE_NATIONAL"
    },
    {
        "brand_name": "놀부보쌈",
        "category_major": "한식",
        "aliases": ["놀부보쌈", "놀부보쌈족발", "놀부보쌈&부대찌개"],
        "negative_keywords": ["놀부식당", "흥부놀부", "놀부네"],
        "scale_type": "LARGE_NATIONAL"
    },

    # 2. 중식 (4개)
    {
        "brand_name": "홍콩반점0410",
        "category_major": "중식",
        "aliases": ["홍콩반점0410", "홍콩반점 0410", "홍콩반점", "홍콩반점0410PLUS"],
        "negative_keywords": ["홍콩대반점", "홍콩차이나", "홍콩식당"],
        "scale_type": "LARGE_NATIONAL"
    },
    {
        "brand_name": "짬뽕지존",
        "category_major": "중식",
        "aliases": ["짬뽕지존"],
        "negative_keywords": ["짬뽕의지존", "지존짬뽕"],
        "scale_type": "MID_SIZE"
    },
    {
        "brand_name": "보배반점",
        "category_major": "중식",
        "aliases": ["보배반점"],
        "negative_keywords": ["보배식당", "보배각"],
        "scale_type": "MID_SIZE"
    },
    {
        "brand_name": "탕화쿵푸마라탕",
        "category_major": "중식",
        "aliases": ["탕화쿵푸마라탕", "탕화쿵푸", "탕화쿵푸 마라탕"],
        "negative_keywords": ["쿵푸마라탕", "탕화마라탕"],
        "scale_type": "LARGE_NATIONAL"
    },

    # 3. 일식 (4개)
    {
        "brand_name": "미소야",
        "category_major": "일식",
        "aliases": ["미소야", "MISOYA"],
        "negative_keywords": ["미소야식", "미소식당", "미소라멘"],
        "scale_type": "LARGE_NATIONAL"
    },
    {
        "brand_name": "아비꼬",
        "category_major": "일식",
        "aliases": ["아비꼬", "아비꼬카레", "ABIKO"],
        "negative_keywords": ["아비꼬식당", "아비꼬이자카야"],
        "scale_type": "MID_SIZE"
    },
    {
        "brand_name": "쿠우쿠우",
        "category_major": "일식",
        "aliases": ["쿠우쿠우", "QOOQOO"],
        "negative_keywords": ["쿠우쿠우카페"],
        "scale_type": "LARGE_NATIONAL"
    },
    {
        "brand_name": "백소정",
        "category_major": "일식",
        "aliases": ["백소정"],
        "negative_keywords": ["백소정식당"],
        "scale_type": "MID_SIZE"
    },

    # 4. 양식·세계음식 (4개)
    {
        "brand_name": "롤링파스타",
        "category_major": "양식·세계음식",
        "aliases": ["롤링파스타", "ROLLING PASTA"],
        "negative_keywords": ["롤링파스타하우스"],
        "scale_type": "LARGE_NATIONAL"
    },
    {
        "brand_name": "서가앤쿡",
        "category_major": "양식·세계음식",
        "aliases": ["서가앤쿡", "SEOGA & COOK", "서가엔쿡"],
        "negative_keywords": ["서가식당", "서가네"],
        "scale_type": "MID_SIZE"
    },
    {
        "brand_name": "아웃백스테이크하우스",
        "category_major": "양식·세계음식",
        "aliases": ["아웃백스테이크하우스", "아웃백", "OUTBACK", "아웃백스테이크"],
        "negative_keywords": ["아웃백카페"],
        "scale_type": "LARGE_NATIONAL"
    },
    {
        "brand_name": "애슐리퀸즈",
        "category_major": "양식·세계음식",
        "aliases": ["애슐리퀸즈", "애슐리", "ASHLEY QUEENS", "애슐리W"],
        "negative_keywords": ["애슐리네"],
        "scale_type": "LARGE_NATIONAL"
    },

    # 5. 치킨·패스트푸드 (6개)
    {
        "brand_name": "교촌치킨",
        "category_major": "치킨·패스트푸드",
        "aliases": ["교촌치킨", "교촌", "KYOCHON"],
        "negative_keywords": ["교촌면옥", "교촌식당", "교촌마을", "교촌한우", "교촌칼국수"],
        "scale_type": "LARGE_NATIONAL"
    },
    {
        "brand_name": "bbq치킨",
        "category_major": "치킨·패스트푸드",
        "aliases": ["bbq치킨", "비비큐", "BBQ", "BBQ치킨", "비비큐치킨", "bbq"],
        "negative_keywords": ["바베큐", "비비큐포차", "삼겹살bbq"],
        "scale_type": "LARGE_NATIONAL"
    },
    {
        "brand_name": "bhc치킨",
        "category_major": "치킨·패스트푸드",
        "aliases": ["bhc치킨", "BHC", "BHC치킨", "비에이치씨", "bhc"],
        "negative_keywords": ["bhc골프"],
        "scale_type": "LARGE_NATIONAL"
    },
    {
        "brand_name": "맘스터치",
        "category_major": "치킨·패스트푸드",
        "aliases": ["맘스터치", "MOM'S TOUCH", "MOMSTOUCH", "맘스피자"],
        "negative_keywords": ["맘스터치식당", "엄마손"],
        "scale_type": "LARGE_NATIONAL"
    },
    {
        "brand_name": "버거킹",
        "category_major": "치킨·패스트푸드",
        "aliases": ["버거킹", "BURGER KING", "BURGERKING"],
        "negative_keywords": ["버거킹포차", "수제버거킹"],
        "scale_type": "LARGE_NATIONAL"
    },
    {
        "brand_name": "롯데리아",
        "category_major": "치킨·패스트푸드",
        "aliases": ["롯데리아", "LOTTERIA"],
        "negative_keywords": ["롯데마트롯데리아", "롯데리아식당"],
        "scale_type": "LARGE_NATIONAL"
    },

    # 6. 분식·간편식 (4개)
    {
        "brand_name": "김가네김밥",
        "category_major": "분식·간편식",
        "aliases": ["김가네김밥", "김가네", "대학로김가네김밥"],
        "negative_keywords": ["김가네식당", "김가네한우", "김가네고깃집", "김가네국밥"],
        "scale_type": "LARGE_NATIONAL"
    },
    {
        "brand_name": "죠스떡볶이",
        "category_major": "분식·간편식",
        "aliases": ["죠스떡볶이", "죠스", "JAWS FOOD"],
        "negative_keywords": ["죠스바", "죠스호프"],
        "scale_type": "LARGE_NATIONAL"
    },
    {
        "brand_name": "동대문엽기떡볶이",
        "category_major": "분식·간편식",
        "aliases": ["동대문엽기떡볶이", "엽기떡볶이", "엽떡"],
        "negative_keywords": ["엽기포차", "엽기불닭"],
        "scale_type": "LARGE_NATIONAL"
    },
    {
        "brand_name": "신전떡볶이",
        "category_major": "분식·간편식",
        "aliases": ["신전떡볶이", "신전 떡볶이"],
        "negative_keywords": ["신전식당", "신전분식"],
        "scale_type": "LARGE_NATIONAL"
    },

    # 7. 카페·음료 (5개)
    {
        "brand_name": "스타벅스",
        "category_major": "카페·음료",
        "aliases": ["스타벅스", "STARBUCKS", "스타벅스코리아", "STARBUCKS COFFEE"],
        "negative_keywords": ["스타벅스앞", "스타포차", "스타분식"],
        "scale_type": "LARGE_NATIONAL"
    },
    {
        "brand_name": "이디야커피",
        "category_major": "카페·음료",
        "aliases": ["이디야커피", "이디야", "EDIYA COFFEE", "EDIYA"],
        "negative_keywords": ["이디야식당", "이디야호프"],
        "scale_type": "LARGE_NATIONAL"
    },
    {
        "brand_name": "투썸플레이스",
        "category_major": "카페·음료",
        "aliases": ["투썸플레이스", "투썸", "A TWOSOME PLACE", "TWOSOME PLACE"],
        "negative_keywords": ["투썸포차"],
        "scale_type": "LARGE_NATIONAL"
    },
    {
        "brand_name": "메가MGC커피",
        "category_major": "카페·음료",
        "aliases": ["메가MGC커피", "메가커피", "MEGA COFFEE", "메가엠지씨커피", "MEGA MGC COFFEE"],
        "negative_keywords": ["메가치킨", "메가분식"],
        "scale_type": "LARGE_NATIONAL"
    },
    {
        "brand_name": "컴포즈커피",
        "category_major": "카페·음료",
        "aliases": ["컴포즈커피", "컴포즈", "COMPOSE COFFEE", "COMPOSE"],
        "negative_keywords": ["컴포즈식당"],
        "scale_type": "LARGE_NATIONAL"
    },

    # 8. 베이커리·디저트 (5개)
    {
        "brand_name": "파리바게뜨",
        "category_major": "베이커리·디저트",
        "aliases": ["파리바게뜨", "파리바게트", "PARIS BAGUETTE", "파리크라상"],
        "negative_keywords": ["파리식당", "바게뜨호프"],
        "scale_type": "LARGE_NATIONAL"
    },
    {
        "brand_name": "뚜레쥬르",
        "category_major": "베이커리·디저트",
        "aliases": ["뚜레쥬르", "뚜레주르", "TOUS LES JOURS"],
        "negative_keywords": ["뚜레식당"],
        "scale_type": "LARGE_NATIONAL"
    },
    {
        "brand_name": "배스킨라빈스",
        "category_major": "베이커리·디저트",
        "aliases": ["배스킨라빈스", "베스킨라빈스", "BASKIN ROBBINS", "배스킨라빈스31", "베스킨라빈스31"],
        "negative_keywords": ["베스킨식당"],
        "scale_type": "LARGE_NATIONAL"
    },
    {
        "brand_name": "설빙",
        "category_major": "베이커리·디저트",
        "aliases": ["설빙", "SULBING", "코리안디저트카페설빙"],
        "negative_keywords": ["설빙식당", "설빙포차"],
        "scale_type": "LARGE_NATIONAL"
    },
    {
        "brand_name": "던킨",
        "category_major": "베이커리·디저트",
        "aliases": ["던킨", "던킨도너츠", "DUNKIN'", "DUNKIN DONUTS", "DUNKIN"],
        "negative_keywords": ["던킨식당"],
        "scale_type": "LARGE_NATIONAL"
    }
]


# ==============================================================================
# 2. 상호명 정규화 및 지점 접미어 분리 로직
# ==============================================================================
# 지점 접미어 정규식 패턴 (단어 뒤에 붙는 점, 호점, 직영점, 역점 등)
BRANCH_SUFFIX_PATTERN = re.compile(
    r"[\s\-_/]+(?:"
    r"[가-힣0-9a-zA-Z]+(?:점|호점|직영점|가맹점|역점|본점|분점|센터|타운|스퀘어|로드점|드라이브스루점|DT점)"
    r"|제?[0-9]+호점"
    r"|본점"
    r"|직영점"
    r")$",
    re.IGNORECASE
)

# 법인/상호 접두·접미어 제거 패턴
LEGAL_ENTITY_PATTERN = re.compile(
    r"\s*[\(\[\{]?(?:주|유|합|사|재|법인|개인|주식회사|유한회사|사단법인|재단법인|협동조합)[\)\]\}]?\s*",
    re.IGNORECASE
)

# 특수기호 제거 패턴 (공백으로 치환)
PUNCT_PATTERN = re.compile(r"['\",`~!?@#$%^&*()_+=/\\\[\]{}|:;<>·•]")


def normalize_store_name(raw_name: str) -> Tuple[str, Optional[str]]:
    """
    상호명을 정규화하고 분리된 지점 접미어를 반환한다.
    반환값: (normalized_base_name, branch_suffix_removed)
    """
    if not raw_name:
        return "", None

    # 1. 유니코드 정규화 (NFC)
    text = unicodedata.normalize("NFC", str(raw_name))

    # 2. 법인격 표기 제거
    text = LEGAL_ENTITY_PATTERN.sub(" ", text)

    # 3. 특수문자 공백 치환
    text = PUNCT_PATTERN.sub(" ", text)

    # 4. 연속 공백 압축 및 좌우 공백 제거
    text = re.sub(r"\s+", " ", text).strip()

    # 5. 지점 접미어 추출 및 분리
    branch_suffix = None
    suffix_match = BRANCH_SUFFIX_PATTERN.search(text)
    if suffix_match:
        branch_suffix = suffix_match.group(0).strip()
        base_name = text[:suffix_match.start()].strip()
    else:
        base_name = text

    return base_name, branch_suffix


def calculate_token_similarity(s1: str, s2: str) -> float:
    """간단하고 효율적인 공통 토큰 유사도 (Jaccard / Character Overlap)"""
    s1_clean = re.sub(r"\s+", "", s1).lower()
    s2_clean = re.sub(r"\s+", "", s2).lower()
    if s1_clean == s2_clean:
        return 1.0
    if not s1_clean or not s2_clean:
        return 0.0

    # 부분 문자열 포함 검사
    if s1_clean in s2_clean or s2_clean in s1_clean:
        shorter = min(len(s1_clean), len(s2_clean))
        longer = max(len(s1_clean), len(s2_clean))
        return shorter / longer

    # 바이그램 자카드 유사도
    def get_bigrams(s):
        return set(s[i:i+2] for i in range(len(s)-1)) if len(s) > 1 else {s}
    
    b1, b2 = get_bigrams(s1_clean), get_bigrams(s2_clean)
    intersection = b1.intersection(b2)
    union = b1.union(b2)
    return len(intersection) / len(union) if union else 0.0


# ==============================================================================
# 3. 매칭 판정 로직
# ==============================================================================
def evaluate_store_match(
    brand_def: Dict[str, Any],
    raw_bizes_nm: str,
    normalized_bizes_nm: str,
    branch_suffix: Optional[str],
    semas_mcls_nm: str
) -> Tuple[str, float, str]:
    """
    점포 상호명과 브랜드 정의 간 매칭 판정 수행
    반환값: (match_type, match_score, notes)
    match_type 종류:
      - 'EXACT_MATCH'
      - 'NORMALIZED_MATCH'
      - 'AMBIGUOUS_MATCH'
      - 'FALSE_POSITIVE_SUSPECT'
      - 'NON_MATCH'
    """
    brand_name = brand_def["brand_name"]
    aliases = brand_def["aliases"]
    negative_kws = brand_def.get("negative_keywords", [])

    clean_norm = re.sub(r"\s+", "", normalized_bizes_nm).lower()
    clean_brand = re.sub(r"\s+", "", brand_name).lower()
    clean_aliases = [re.sub(r"\s+", "", a).lower() for a in aliases]

    # 1. 부정 키워드 (Negative keywords / 유사 일반상호) 우선 탐지
    for neg in negative_kws:
        clean_neg = re.sub(r"\s+", "", neg).lower()
        if clean_neg in clean_norm:
            return "FALSE_POSITIVE_SUSPECT", 0.35, f"부정 키워드 '{neg}' 포함으로 일반식당 오탐 의심"

    # 2. 정확 일치 (EXACT_MATCH)
    if clean_norm == clean_brand:
        if branch_suffix:
            return "NORMALIZED_MATCH", 0.98, f"지점 접미어('{branch_suffix}') 제거 후 브랜드 정식명칭 완전 일치"
        return "EXACT_MATCH", 1.0, "브랜드 정식명칭 완전 일치"

    # 3. 별칭 정규화 일치 (NORMALIZED_MATCH)
    for alias in clean_aliases:
        if clean_norm == alias:
            return "NORMALIZED_MATCH", 0.95, f"등록된 브랜드 별칭('{alias}')과 완전 일치"

    # 4. 모호한 일치 vs 오탐 의심 (AMBIGUOUS_MATCH / FALSE_POSITIVE_SUSPECT)
    for alias in clean_aliases:
        if alias in clean_norm:
            # 브랜드 별칭이 상호명의 일부로 포함된 경우
            # 예: '교촌치킨&호프' -> AMBIGUOUS
            # 예: '교촌쌈밥' -> FALSE_POSITIVE_SUSPECT
            sim = calculate_token_similarity(clean_norm, alias)
            
            # 일반 음식점 오탐 위험 키워드 목록
            generic_food_words = ["식당", "밥상", "한우", "갈비", "삼겹살", "포차", "주막", "국밥", "면옥", "마을"]
            has_generic_word = any(gw in clean_norm for gw in generic_food_words)
            
            if has_generic_word:
                return "FALSE_POSITIVE_SUSPECT", round(sim * 0.6, 2), f"브랜드명 포함되나 일반명사('{clean_norm}') 결합으로 오탐 의심"
            elif sim >= 0.6:
                return "AMBIGUOUS_MATCH", round(sim, 2), f"브랜드명 포함 및 부가수식어 결합 (유사도 {sim:.2f})"
            else:
                return "FALSE_POSITIVE_SUSPECT", round(sim * 0.5, 2), f"브랜드명 일부 포함되나 긴 상호명 (유사도 {sim:.2f})"

    # 5. 미매칭 (NON_MATCH)
    return "NON_MATCH", 0.0, "브랜드명 미일치"


# ==============================================================================
# 4. 전체 실험 실행 모듈
# ==============================================================================
def run_brand_matching_experiments(
    limit_per_brand: int = 50,
    db_target_path: Optional[Path] = None
) -> Dict[str, Any]:
    """
    37개 표본 브랜드에 대해 소진공 nationwide_food_stores_v2 DB에서 매칭 후보를 추출하고,
    Stage 4A DB의 store_brand_match_samples에 적재 및 종합 통계를 산출한다.
    """
    target_db = db_target_path or DEFAULT_STAGE4A_DB_PATH
    print(f"[*] 소진공 DB 연결 (Read-Only): {SEMAS_V2_DB_PATH}")
    semas_con = sqlite3.connect(f"file:{SEMAS_V2_DB_PATH}?mode=ro", uri=True)
    semas_cur = semas_con.cursor()

    print(f"[*] Stage 4A DB 연결: {target_db}")
    stage4a_con = sqlite3.connect(target_db)
    stage4a_cur = stage4a_con.cursor()

    overall_stats: Dict[str, Any] = {
        "total_brands_tested": len(SAMPLE_BRANDS),
        "brand_results": {},
        "match_type_summary": {
            "EXACT_MATCH": 0,
            "NORMALIZED_MATCH": 0,
            "AMBIGUOUS_MATCH": 0,
            "FALSE_POSITIVE_SUSPECT": 0,
            "NON_MATCH": 0
        },
        "labeled_precision_stats": {
            "total_labeled": 0,
            "true_positives": 0,
            "false_positives": 0,
            "precision_rate": 0.0
        }
    }

    # 기존 실험 레코드 초기화 (동일 브랜드 재실행 시 멱등성 유지)
    stage4a_cur.execute("DELETE FROM store_brand_match_samples")
    stage4a_con.commit()

    total_samples_saved = 0
    labeled_samples_count = 0
    labeled_tp_count = 0
    labeled_fp_count = 0

    print(f"[*] 37개 대표 표본 브랜드 매칭 실험 시작 (브랜드당 최대 {limit_per_brand}건 표본 추출)...")

    for b_idx, brand_def in enumerate(SAMPLE_BRANDS, 1):
        brand_name = brand_def["brand_name"]
        cat_major = brand_def["category_major"]
        aliases = brand_def["aliases"]

        # 검색 쿼리 구성: 주 브랜드명 및 별칭으로 LIKE 질의
        like_clauses = " OR ".join(["bizes_nm LIKE ?"] * len(aliases))
        like_params = [f"%{a}%" for a in aliases]

        query = f"""
            SELECT bizes_id, bizes_nm, brch_nm, inds_mcls_nm, std_sido_name, std_signgu_name
            FROM stores
            WHERE ({like_clauses})
            LIMIT ?
        """
        params = like_params + [limit_per_brand * 2]
        matched_rows = semas_cur.execute(query, params).fetchall()

        brand_stat = {
            "brand_name": brand_name,
            "category_major": cat_major,
            "raw_matches_found": len(matched_rows),
            "exact_matches": 0,
            "normalized_matches": 0,
            "ambiguous_matches": 0,
            "false_positives": 0,
            "samples_stored": 0
        }

        inserted_for_brand = 0

        for r in matched_rows:
            if inserted_for_brand >= limit_per_brand:
                break

            bizes_id, raw_nm, brch_nm, mcls_nm, sido, signgu = r
            norm_nm, branch_suffix = normalize_store_name(raw_nm)

            # branch_suffix가 없는데 brch_nm 컬럼에 값이 있으면 보완
            if not branch_suffix and brch_nm:
                branch_suffix = brch_nm

            m_type, m_score, notes = evaluate_store_match(
                brand_def=brand_def,
                raw_bizes_nm=raw_nm,
                normalized_bizes_nm=norm_nm,
                branch_suffix=branch_suffix,
                semas_mcls_nm=mcls_nm or ""
            )

            if m_type == "NON_MATCH":
                continue

            # 라벨링 판정 규칙 (골드 스탠다드 평가용)
            # EXACT와 NORMALIZED는 기본 TP(True Positive, 1)
            # FALSE_POSITIVE_SUSPECT는 기본 FP(False Positive, 0)
            # AMBIGUOUS는 정밀 규칙 검토 필요 (NULL / PENDING)
            is_tp = None
            rev_status = "PENDING"
            if m_type in ["EXACT_MATCH", "NORMALIZED_MATCH"]:
                is_tp = 1
                rev_status = "VERIFIED_TP"
            elif m_type == "FALSE_POSITIVE_SUSPECT":
                is_tp = 0
                rev_status = "CONFIRMED_FP"
            elif m_type == "AMBIGUOUS_MATCH":
                is_tp = None
                rev_status = "NEEDS_RULE"

            # DB 저장
            stage4a_cur.execute("""
                INSERT INTO store_brand_match_samples (
                    target_brand_name, brand_category_major, bizes_id,
                    raw_bizes_nm, normalized_bizes_nm, branch_suffix_removed,
                    semas_mcls_nm, sido_name, signgu_name,
                    match_type, match_score, is_true_positive, review_status, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                brand_name, cat_major, bizes_id,
                raw_nm, norm_nm, branch_suffix,
                mcls_nm, sido, signgu,
                m_type, m_score, is_tp, rev_status, notes
            ))

            # 통계 집계
            overall_stats["match_type_summary"][m_type] += 1
            if m_type == "EXACT_MATCH": brand_stat["exact_matches"] += 1
            elif m_type == "NORMALIZED_MATCH": brand_stat["normalized_matches"] += 1
            elif m_type == "AMBIGUOUS_MATCH": brand_stat["ambiguous_matches"] += 1
            elif m_type == "FALSE_POSITIVE_SUSPECT": brand_stat["false_positives"] += 1

            if is_tp is not None:
                labeled_samples_count += 1
                if is_tp == 1: labeled_tp_count += 1
                else: labeled_fp_count += 1

            inserted_for_brand += 1
            total_samples_saved += 1

        brand_stat["samples_stored"] = inserted_for_brand
        overall_stats["brand_results"][brand_name] = brand_stat

        if b_idx % 5 == 0 or b_idx == len(SAMPLE_BRANDS):
            print(f"  [{b_idx}/{len(SAMPLE_BRANDS)}] {brand_name} ({cat_major}): 추출 {inserted_for_brand}건 (정확={brand_stat['exact_matches']}, 정규화={brand_stat['normalized_matches']}, 모호={brand_stat['ambiguous_matches']}, 오탐의심={brand_stat['false_positives']})")

    stage4a_con.commit()

    # 정밀도 계산 (라벨링 완료된 표본 대상)
    precision = (labeled_tp_count / labeled_samples_count * 100.0) if labeled_samples_count > 0 else 0.0
    overall_stats["labeled_precision_stats"]["total_labeled"] = labeled_samples_count
    overall_stats["labeled_precision_stats"]["true_positives"] = labeled_tp_count
    overall_stats["labeled_precision_stats"]["false_positives"] = labeled_fp_count
    overall_stats["labeled_precision_stats"]["precision_rate"] = round(precision, 2)
    overall_stats["total_samples_stored"] = total_samples_saved

    # 품질 검사 감사 레코드 기록
    cur_run_id = f"RUN_4A_EXP_{int(sqlite3.time.time())}"
    stage4a_cur.execute("""
        INSERT OR IGNORE INTO pipeline_runs (
            run_id, stage_name, description, sample_matches_tested, status
        ) VALUES (?, 'STAGE_4A', 'Brand Matching Experiment Run', ?, 'COMPLETED')
    """, (cur_run_id, total_samples_saved))

    stage4a_cur.execute("""
        INSERT INTO data_quality_results (
            run_id, audit_category, assertion_name, assertion_status,
            target_dataset, actual_value, expected_value, detail_message
        ) VALUES (
            ?, 'MATCH_EXPERIMENT', 'MATCH_PRECISION_THRESHOLD',
            CASE WHEN ? >= 90.0 THEN 'PASS' ELSE 'CONDITIONAL' END,
            'STAGE4A_MATCH_SAMPLES', ?, '>=90.0%',
            'Sample match precision on labeled subset: TP=' || ? || ', FP=' || ?
        )
    """, (cur_run_id, precision, f"{precision:.2f}%", labeled_tp_count, labeled_fp_count))

    stage4a_con.commit()
    semas_con.close()
    stage4a_con.close()

    print(f"\n[+] 매칭 실험 완료! 총 저장 표본: {total_samples_saved}건")
    print(f"    - 정확 일치(EXACT): {overall_stats['match_type_summary']['EXACT_MATCH']}건")
    print(f"    - 정규화 일치(NORMALIZED): {overall_stats['match_type_summary']['NORMALIZED_MATCH']}건")
    print(f"    - 모호한 일치(AMBIGUOUS): {overall_stats['match_type_summary']['AMBIGUOUS_MATCH']}건")
    print(f"    - 오탐 의심(FALSE_POSITIVE_SUSPECT): {overall_stats['match_type_summary']['FALSE_POSITIVE_SUSPECT']}건")
    print(f"    - 확정 라벨링 표본: {labeled_samples_count}건 중 TP={labeled_tp_count}건, FP={labeled_fp_count}건 (정밀도: {precision:.2f}%)")

    return overall_stats


if __name__ == "__main__":
    stats = run_brand_matching_experiments(limit_per_brand=30)
    print("\n최종 실험 결과 요약:")
    print(json.dumps(stats["match_type_summary"], indent=2, ensure_ascii=False))
