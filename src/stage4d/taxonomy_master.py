"""
Stage 4D: 8대 대분류 및 48대 중분류 체계 마스터 및 소진공 업종 매핑 정의
프로젝트: D:/Franchise_Dashboard
위치: src/stage4d/taxonomy_master.py
"""

import json
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional

TAXONOMY_CONFIG_PATH = Path("d:/Franchise_Dashboard/config/food_category_taxonomy_v1.json")


def load_taxonomy_config() -> Dict[str, Any]:
    """분류체계 JSON 설정 파일 로드"""
    with open(TAXONOMY_CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


# ==============================================================================
# 1. 소진공 I2 38개 소분류 기본 데이터
# ==============================================================================
SEMAS_38_SUBCLASSES: List[Dict[str, Any]] = [
    {"scls_code": "I20101", "scls_name": "백반/한정식", "mcls_code": "I201", "mcls_name": "한식", "count": 180762},
    {"scls_code": "I20102", "scls_name": "국/탕/찌개류", "mcls_code": "I201", "mcls_name": "한식", "count": 31908},
    {"scls_code": "I20103", "scls_name": "족발/보쌈", "mcls_code": "I201", "mcls_name": "한식", "count": 7573},
    {"scls_code": "I20104", "scls_name": "전/부침개", "mcls_code": "I201", "mcls_name": "한식", "count": 914},
    {"scls_code": "I20105", "scls_name": "국수/칼국수", "mcls_code": "I201", "mcls_name": "한식", "count": 20442},
    {"scls_code": "I20106", "scls_name": "냉면/밀면", "mcls_code": "I201", "mcls_name": "한식", "count": 3883},
    {"scls_code": "I20107", "scls_name": "돼지고기 구이/찜", "mcls_code": "I201", "mcls_name": "한식", "count": 55328},
    {"scls_code": "I20108", "scls_name": "소고기 구이/찜", "mcls_code": "I201", "mcls_name": "한식", "count": 6184},
    {"scls_code": "I20109", "scls_name": "곱창 전골/구이", "mcls_code": "I201", "mcls_name": "한식", "count": 7194},
    {"scls_code": "I20110", "scls_name": "닭/오리고기 구이/찜", "mcls_code": "I201", "mcls_name": "한식", "count": 8622},
    {"scls_code": "I20111", "scls_name": "횟집", "mcls_code": "I201", "mcls_name": "한식", "count": 19385},
    {"scls_code": "I20112", "scls_name": "해산물 구이/찜", "mcls_code": "I201", "mcls_name": "한식", "count": 14561},
    {"scls_code": "I20113", "scls_name": "복 요리 전문", "mcls_code": "I201", "mcls_name": "한식", "count": 591},
    {"scls_code": "I20199", "scls_name": "기타 한식 음식점", "mcls_code": "I201", "mcls_name": "한식", "count": 2485},
    {"scls_code": "I20201", "scls_name": "중국집", "mcls_code": "I202", "mcls_name": "중식", "count": 27615},
    {"scls_code": "I20202", "scls_name": "마라탕/훠궈", "mcls_code": "I202", "mcls_name": "중식", "count": 4369},
    {"scls_code": "I20301", "scls_name": "일식 회/초밥", "mcls_code": "I203", "mcls_name": "일식", "count": 19499},
    {"scls_code": "I20302", "scls_name": "일식 카레/돈가스/덮밥", "mcls_code": "I203", "mcls_name": "일식", "count": 2539},
    {"scls_code": "I20303", "scls_name": "일식 면 요리", "mcls_code": "I203", "mcls_name": "일식", "count": 2292},
    {"scls_code": "I20399", "scls_name": "기타 일식 음식점", "mcls_code": "I203", "mcls_name": "일식", "count": 512},
    {"scls_code": "I20401", "scls_name": "경양식", "mcls_code": "I204", "mcls_name": "서양식", "count": 19598},
    {"scls_code": "I20402", "scls_name": "파스타/스테이크", "mcls_code": "I204", "mcls_name": "서양식", "count": 2041},
    {"scls_code": "I20403", "scls_name": "패밀리레스토랑", "mcls_code": "I204", "mcls_name": "서양식", "count": 410},
    {"scls_code": "I20499", "scls_name": "기타 서양식 음식점", "mcls_code": "I204", "mcls_name": "서양식", "count": 1051},
    {"scls_code": "I20501", "scls_name": "베트남식 전문", "mcls_code": "I205", "mcls_name": "동남아시아", "count": 6094},
    {"scls_code": "I20599", "scls_name": "기타 동남아식 전문", "mcls_code": "I205", "mcls_name": "동남아시아", "count": 537},
    {"scls_code": "I20601", "scls_name": "분류 안된 외국식 음식점", "mcls_code": "I206", "mcls_name": "기타 외국", "count": 49},
    {"scls_code": "I20702", "scls_name": "뷔페", "mcls_code": "I207", "mcls_name": "구내식당·뷔페", "count": 3184},
    {"scls_code": "I21001", "scls_name": "빵/도넛", "mcls_code": "I210", "mcls_name": "기타 간이", "count": 31168},
    {"scls_code": "I21002", "scls_name": "떡/한과", "mcls_code": "I210", "mcls_name": "기타 간이", "count": 9418},
    {"scls_code": "I21003", "scls_name": "피자", "mcls_code": "I210", "mcls_name": "기타 간이", "count": 17509},
    {"scls_code": "I21004", "scls_name": "버거", "mcls_code": "I210", "mcls_name": "기타 간이", "count": 5749},
    {"scls_code": "I21005", "scls_name": "토스트/샌드위치/샐러드", "mcls_code": "I210", "mcls_name": "기타 간이", "count": 3407},
    {"scls_code": "I21006", "scls_name": "치킨", "mcls_code": "I210", "mcls_name": "기타 간이", "count": 40315},
    {"scls_code": "I21007", "scls_name": "김밥/만두/분식", "mcls_code": "I210", "mcls_name": "기타 간이", "count": 44410},
    {"scls_code": "I21008", "scls_name": "아이스크림/빙수", "mcls_code": "I210", "mcls_name": "기타 간이", "count": 2821},
    {"scls_code": "I21099", "scls_name": "그 외 기타 간이 음식점", "mcls_code": "I210", "mcls_name": "기타 간이", "count": 8144},
    {"scls_code": "I21201", "scls_name": "카페", "mcls_code": "I212", "mcls_name": "비알코올 ", "count": 122622},
]


# ==============================================================================
# 2. 소진공 소분류 -> 48대 중분류 매핑 규칙 (1:1 및 1:N)
# ==============================================================================
SEMAS_TO_MID_RULES: List[Dict[str, Any]] = [
    # ---------------- 한식 (I201) ----------------
    {"scls_code": "I20101", "category_mid_id": "CAT_MID_0103", "is_primary": 1, "rule_type": "DIRECT_MAP", "keywords": None, "notes": "백반/한정식 -> 백반/한정식"},
    {"scls_code": "I20102", "category_mid_id": "CAT_MID_0102", "is_primary": 1, "rule_type": "DIRECT_MAP", "keywords": None, "notes": "국/탕/찌개류 -> 찌개/탕/국"},
    {"scls_code": "I20103", "category_mid_id": "CAT_MID_0104", "is_primary": 1, "rule_type": "DIRECT_MAP", "keywords": None, "notes": "족발/보쌈 -> 족발/보쌈"},
    {"scls_code": "I20104", "category_mid_id": "CAT_MID_0108", "is_primary": 1, "rule_type": "DIRECT_MAP", "keywords": None, "notes": "전/부침개 -> 전/부침/기타한식"},
    {"scls_code": "I20105", "category_mid_id": "CAT_MID_0105", "is_primary": 1, "rule_type": "DIRECT_MAP", "keywords": None, "notes": "국수/칼국수 -> 국수/면류"},
    {"scls_code": "I20106", "category_mid_id": "CAT_MID_0105", "is_primary": 1, "rule_type": "DIRECT_MAP", "keywords": None, "notes": "냉면/밀면 -> 국수/면류"},
    {"scls_code": "I20107", "category_mid_id": "CAT_MID_0101", "is_primary": 1, "rule_type": "DIRECT_MAP", "keywords": None, "notes": "돼지고기 구이/찜 -> 고기구이/육류"},
    {"scls_code": "I20108", "category_mid_id": "CAT_MID_0101", "is_primary": 1, "rule_type": "DIRECT_MAP", "keywords": None, "notes": "소고기 구이/찜 -> 고기구이/육류"},
    {"scls_code": "I20109", "category_mid_id": "CAT_MID_0101", "is_primary": 1, "rule_type": "DIRECT_MAP", "keywords": None, "notes": "곱창 전골/구이 -> 고기구이/육류"},
    {"scls_code": "I20110", "category_mid_id": "CAT_MID_0106", "is_primary": 1, "rule_type": "DIRECT_MAP", "keywords": None, "notes": "닭/오리고기 구이/찜 -> 닭/오리요리"},
    {"scls_code": "I20111", "category_mid_id": "CAT_MID_0107", "is_primary": 1, "rule_type": "DIRECT_MAP", "keywords": None, "notes": "횟집 -> 해산물/회"},
    {"scls_code": "I20112", "category_mid_id": "CAT_MID_0107", "is_primary": 1, "rule_type": "DIRECT_MAP", "keywords": None, "notes": "해산물 구이/찜 -> 해산물/회"},
    {"scls_code": "I20113", "category_mid_id": "CAT_MID_0107", "is_primary": 1, "rule_type": "DIRECT_MAP", "keywords": None, "notes": "복 요리 전문 -> 해산물/회"},
    {"scls_code": "I20199", "category_mid_id": "CAT_MID_0108", "is_primary": 1, "rule_type": "DIRECT_MAP", "keywords": None, "notes": "기타 한식 음식점 -> 전/부침/기타한식"},

    # ---------------- 중식 (I202) ----------------
    {"scls_code": "I20201", "category_mid_id": "CAT_MID_0201", "is_primary": 1, "rule_type": "DIRECT_MAP", "keywords": None, "notes": "중국집 -> 일반중식/짜장·짬뽕 (기본)"},
    {"scls_code": "I20201", "category_mid_id": "CAT_MID_0203", "is_primary": 0, "rule_type": "1_TO_N_SPLIT", "keywords": ["딤섬", "만두", "소룡포", "하가우"], "notes": "중국집 중 딤섬/만두 전문"},
    {"scls_code": "I20201", "category_mid_id": "CAT_MID_0204", "is_primary": 0, "rule_type": "1_TO_N_SPLIT", "keywords": ["양꼬치", "양갈비", "꼬치구이"], "notes": "중국집 중 양꼬치 전문"},
    {"scls_code": "I20201", "category_mid_id": "CAT_MID_0205", "is_primary": 0, "rule_type": "1_TO_N_SPLIT", "keywords": ["중식포차", "홍콩포차", "중식주점"], "notes": "중국집 중 주점/비스트로"},
    {"scls_code": "I20202", "category_mid_id": "CAT_MID_0202", "is_primary": 1, "rule_type": "DIRECT_MAP", "keywords": None, "notes": "마라탕/훠궈 -> 마라탕/훠궈"},

    # ---------------- 일식 (I203) ----------------
    {"scls_code": "I20301", "category_mid_id": "CAT_MID_0302", "is_primary": 1, "rule_type": "DIRECT_MAP", "keywords": None, "notes": "일식 회/초밥 -> 초밥/회"},
    {"scls_code": "I20302", "category_mid_id": "CAT_MID_0301", "is_primary": 1, "rule_type": "1_TO_N_SPLIT", "keywords": ["돈가스", "돈카츠", "카레", "카츠", "가츠"], "notes": "일식 카레/돈가스/덮밥 -> 돈가스/카레 (기본)"},
    {"scls_code": "I20302", "category_mid_id": "CAT_MID_0304", "is_primary": 0, "rule_type": "1_TO_N_SPLIT", "keywords": ["덮밥", "규동", "가츠동", "사케동", "가정식", "정식"], "notes": "일식 덮밥/가정식 분기"},
    {"scls_code": "I20303", "category_mid_id": "CAT_MID_0303", "is_primary": 1, "rule_type": "DIRECT_MAP", "keywords": None, "notes": "일식 면 요리 -> 라멘/소바/우동"},
    {"scls_code": "I20399", "category_mid_id": "CAT_MID_0306", "is_primary": 1, "rule_type": "1_TO_N_SPLIT", "keywords": None, "notes": "기타 일식 음식점 -> 기타일식 (기본)"},
    {"scls_code": "I20399", "category_mid_id": "CAT_MID_0305", "is_primary": 0, "rule_type": "1_TO_N_SPLIT", "keywords": ["이자카야", "야키토리", "꼬치", "오코노미"], "notes": "기타 일식 중 이자카야 분기"},

    # ---------------- 서양식/아시안/외국식 (I204, I205, I206, I207) ----------------
    {"scls_code": "I20401", "category_mid_id": "CAT_MID_0402", "is_primary": 1, "rule_type": "DIRECT_MAP", "keywords": None, "notes": "경양식 -> 패밀리레스토랑/경양식"},
    {"scls_code": "I20402", "category_mid_id": "CAT_MID_0401", "is_primary": 1, "rule_type": "DIRECT_MAP", "keywords": None, "notes": "파스타/스테이크 -> 파스타/스테이크"},
    {"scls_code": "I20403", "category_mid_id": "CAT_MID_0402", "is_primary": 1, "rule_type": "DIRECT_MAP", "keywords": None, "notes": "패밀리레스토랑 -> 패밀리레스토랑/경양식"},
    {"scls_code": "I20499", "category_mid_id": "CAT_MID_0405", "is_primary": 1, "rule_type": "DIRECT_MAP", "keywords": None, "notes": "기타 서양식 음식점 -> 기타세계음식"},
    {"scls_code": "I20501", "category_mid_id": "CAT_MID_0403", "is_primary": 1, "rule_type": "DIRECT_MAP", "keywords": None, "notes": "베트남식 전문 -> 베트남/아시안"},
    {"scls_code": "I20599", "category_mid_id": "CAT_MID_0403", "is_primary": 1, "rule_type": "DIRECT_MAP", "keywords": None, "notes": "기타 동남아식 전문 -> 베트남/아시안"},
    {"scls_code": "I20601", "category_mid_id": "CAT_MID_0405", "is_primary": 1, "rule_type": "DIRECT_MAP", "keywords": None, "notes": "분류 안된 외국식 음식점 -> 기타세계음식"},
    {"scls_code": "I20702", "category_mid_id": "CAT_MID_0404", "is_primary": 1, "rule_type": "DIRECT_MAP", "keywords": None, "notes": "뷔페 -> 뷔페/샐러드바"},

    # ---------------- 기타 간이 (I210) ----------------
    {"scls_code": "I21001", "category_mid_id": "CAT_MID_0801", "is_primary": 1, "rule_type": "1_TO_N_SPLIT", "keywords": ["베이커리", "빵", "제과", "바게트", "식빵", "크루아상"], "notes": "빵/도넛 -> 제과/베이커리 (기본)"},
    {"scls_code": "I21001", "category_mid_id": "CAT_MID_0802", "is_primary": 0, "rule_type": "1_TO_N_SPLIT", "keywords": ["도넛", "도너츠", "와플", "꽈배기"], "notes": "빵/도넛 중 도넛/와플 분기"},
    {"scls_code": "I21001", "category_mid_id": "CAT_MID_0804", "is_primary": 0, "rule_type": "1_TO_N_SPLIT", "keywords": ["케이크", "타르트", "마카롱", "디저트"], "notes": "빵/도넛 중 케이크/타르트 분기"},
    {"scls_code": "I21002", "category_mid_id": "CAT_MID_0805", "is_primary": 1, "rule_type": "DIRECT_MAP", "keywords": None, "notes": "떡/한과 -> 떡/한과"},
    {"scls_code": "I21003", "category_mid_id": "CAT_MID_0503", "is_primary": 1, "rule_type": "DIRECT_MAP", "keywords": None, "notes": "피자 -> 피자"},
    {"scls_code": "I21004", "category_mid_id": "CAT_MID_0502", "is_primary": 1, "rule_type": "DIRECT_MAP", "keywords": None, "notes": "버거 -> 버거"},
    {"scls_code": "I21005", "category_mid_id": "CAT_MID_0504", "is_primary": 1, "rule_type": "1_TO_N_SPLIT", "keywords": ["토스트", "샌드위치", "이삭", "에그"], "notes": "토스트/샌드위치/샐러드 -> 토스트/샌드위치 (기본)"},
    {"scls_code": "I21005", "category_mid_id": "CAT_MID_0505", "is_primary": 0, "rule_type": "1_TO_N_SPLIT", "keywords": ["샐러드", "샐러디", "포케", "그릭요거트", "보울"], "notes": "토스트/샌드위치/샐러드 중 샐러드/포케 분기"},
    {"scls_code": "I21006", "category_mid_id": "CAT_MID_0501", "is_primary": 1, "rule_type": "DIRECT_MAP", "keywords": None, "notes": "치킨 -> 치킨"},
    {"scls_code": "I21007", "category_mid_id": "CAT_MID_0602", "is_primary": 1, "rule_type": "1_TO_N_SPLIT", "keywords": ["김밥", "분식", "라면", "종합분식"], "notes": "김밥/만두/분식 -> 김밥/종합분식 (기본)"},
    {"scls_code": "I21007", "category_mid_id": "CAT_MID_0601", "is_primary": 0, "rule_type": "1_TO_N_SPLIT", "keywords": ["떡볶이", "엽떡", "죠스", "신전", "튀김", "순대", "배떡"], "notes": "김밥/만두/분식 중 떡볶이/튀김 분기"},
    {"scls_code": "I21007", "category_mid_id": "CAT_MID_0603", "is_primary": 0, "rule_type": "1_TO_N_SPLIT", "keywords": ["만두", "찐빵", "손만두"], "notes": "김밥/만두/분식 중 만두 분기"},
    {"scls_code": "I21007", "category_mid_id": "CAT_MID_0604", "is_primary": 0, "rule_type": "1_TO_N_SPLIT", "keywords": ["도시락", "한솥", "본도시락", "주먹밥"], "notes": "김밥/만두/분식 중 도시락 분기"},
    {"scls_code": "I21007", "category_mid_id": "CAT_MID_0605", "is_primary": 0, "rule_type": "1_TO_N_SPLIT", "keywords": ["죽", "본죽", "맛죽"], "notes": "김밥/만두/분식 중 죽전문 분기"},
    {"scls_code": "I21008", "category_mid_id": "CAT_MID_0803", "is_primary": 1, "rule_type": "DIRECT_MAP", "keywords": None, "notes": "아이스크림/빙수 -> 아이스크림/빙수"},
    {"scls_code": "I21099", "category_mid_id": "CAT_MID_0506", "is_primary": 1, "rule_type": "1_TO_N_SPLIT", "keywords": None, "notes": "그 외 기타 간이 음식점 -> 기타패스트푸드 (기본)"},
    {"scls_code": "I21099", "category_mid_id": "CAT_MID_0606", "is_primary": 0, "rule_type": "1_TO_N_SPLIT", "keywords": ["분식", "포장마차", "어묵", "호떡", "붕어빵"], "notes": "기타 간이 중 기타분식 분기"},
    {"scls_code": "I21099", "category_mid_id": "CAT_MID_0806", "is_primary": 0, "rule_type": "1_TO_N_SPLIT", "keywords": ["탕후루", "디저트", "와플", "추로스"], "notes": "기타 간이 중 기타디저트 분기"},

    # ---------------- 카페/음료 (I212) ----------------
    {"scls_code": "I21201", "category_mid_id": "CAT_MID_0701", "is_primary": 1, "rule_type": "1_TO_N_SPLIT", "keywords": ["커피", "로스터리", "에스프레소", "카페"], "notes": "카페 -> 커피전문점 (기본)"},
    {"scls_code": "I21201", "category_mid_id": "CAT_MID_0702", "is_primary": 0, "rule_type": "1_TO_N_SPLIT", "keywords": ["메가", "컴포즈", "빽다방", "더벤티", "하삼동", "매머드", "바나프레소", "감성커피", "테이크아웃"], "notes": "카페 중 저가커피/테이크아웃 분기"},
    {"scls_code": "I21201", "category_mid_id": "CAT_MID_0703", "is_primary": 0, "rule_type": "1_TO_N_SPLIT", "keywords": ["공차", "버블티", "주스", "쥬씨", "스무디", "밀크티", "에이드"], "notes": "카페 중 음료/버블티/주스 분기"},
    {"scls_code": "I21201", "category_mid_id": "CAT_MID_0704", "is_primary": 0, "rule_type": "1_TO_N_SPLIT", "keywords": ["전통차", "찻집", "쌍화차", "오설록", "홍차", "티하우스"], "notes": "카페 중 차/전통찻집 분기"},
    {"scls_code": "I21201", "category_mid_id": "CAT_MID_0705", "is_primary": 0, "rule_type": "1_TO_N_SPLIT", "keywords": ["디저트카페", "베이커리카페", "크로플", "디저트39"], "notes": "카페 중 디저트카페 분기"},
    {"scls_code": "I21201", "category_mid_id": "CAT_MID_0706", "is_primary": 0, "rule_type": "1_TO_N_SPLIT", "keywords": ["무인", "24시카페", "로봇", "북카페", "보드게임"], "notes": "카페 중 무인/기타카페 분기"},
]


# ==============================================================================
# 3. 공식 80개 브랜드 대표 업종 명시적 매핑 (Ground Truth Seed Mapping)
# ==============================================================================
OFFICIAL_80_BRAND_CATEGORY_MAP: Dict[str, Tuple[str, str, str]] = {
    # (internal_brand_id): (category_maj_id, category_mid_id, rationale)
    # 1. 한식 (13개)
    "BRD_KOR_0001": ("CAT_MAJ_01", "CAT_MID_0103", "본죽: 죽 전문점, 한식 백반/죽 대표메뉴"),
    "BRD_KOR_0002": ("CAT_MAJ_01", "CAT_MID_0103", "본도시락: 테이크아웃 한식 도시락"),
    "BRD_KOR_0003": ("CAT_MAJ_01", "CAT_MID_0102", "본설렁탕: 설렁탕·국/탕 가맹사업"),
    "BRD_KOR_0004": ("CAT_MAJ_01", "CAT_MID_0103", "한솥도시락: 한식 도시락 가맹사업"),
    "BRD_KOR_0005": ("CAT_MAJ_01", "CAT_MID_0101", "하남돼지집: 돼지고기 구이 가맹사업"),
    "BRD_KOR_0006": ("CAT_MAJ_01", "CAT_MID_0106", "두찜: 닭/오리요리 (두마리찜닭)"),
    "BRD_KOR_0007": ("CAT_MAJ_01", "CAT_MID_0104", "놀부보쌈: 족발/보쌈 가맹사업"),
    "BRD_KOR_0008": ("CAT_MAJ_01", "CAT_MID_0102", "놀부부대찌개: 부대찌개·찌개/탕 가맹사업"),
    "BRD_KOR_0009": ("CAT_MAJ_01", "CAT_MID_0104", "원할머니보쌈: 족발/보쌈 가맹사업"),
    "BRD_KOR_0010": ("CAT_MAJ_01", "CAT_MID_0101", "채선당: 샤브샤브·고기구이/육류 가맹사업"),
    "BRD_KOR_0011": ("CAT_MAJ_01", "CAT_MID_0101", "새마을식당: 열탄불고기·고기구이 가맹사업"),
    "BRD_KOR_0012": ("CAT_MAJ_01", "CAT_MID_0101", "명륜진사갈비: 돼지갈비 구이 무한리필 가맹사업"),
    "BRD_KOR_0013": ("CAT_MAJ_01", "CAT_MID_0102", "백채김치찌개: 김치찌개·찌개/탕 가맹사업"),

    # 2. 중식 (7개)
    "BRD_CHN_0001": ("CAT_MAJ_02", "CAT_MID_0201", "홍콩반점0410: 짬뽕/짜장 일반중식 가맹사업"),
    "BRD_CHN_0002": ("CAT_MAJ_02", "CAT_MID_0201", "짬뽕지존: 짬뽕 전문 일반중식"),
    "BRD_CHN_0003": ("CAT_MAJ_02", "CAT_MID_0201", "보배반점: 짬뽕·짜장 일반중식"),
    "BRD_CHN_0004": ("CAT_MAJ_02", "CAT_MID_0202", "탕화쿵푸마라탕: 마라탕/훠궈 가맹사업"),
    "BRD_CHN_0005": ("CAT_MAJ_02", "CAT_MID_0202", "라화쿵부: 마라탕/마라샹궈 가맹사업"),
    "BRD_CHN_0006": ("CAT_MAJ_02", "CAT_MID_0201", "교동짬뽕: 짬뽕 전문 중식 (미확인 브랜드)"),
    "BRD_CHN_0007": ("CAT_MAJ_02", "CAT_MID_0201", "이비가짬뽕: 짬뽕 전문 중식 가맹사업"),

    # 3. 일식 (7개)
    "BRD_JPN_0001": ("CAT_MAJ_03", "CAT_MID_0301", "미소야: 돈카츠·우동·카레 가맹사업"),
    "BRD_JPN_0002": ("CAT_MAJ_03", "CAT_MID_0301", "아비꼬: 매운 일본식 카레·돈가스 가맹사업"),
    "BRD_JPN_0003": ("CAT_MAJ_03", "CAT_MID_0302", "쿠우쿠우: 초밥·샐러드 뷔페 가맹사업"),
    "BRD_JPN_0004": ("CAT_MAJ_03", "CAT_MID_0301", "백소정: 돈카츠·마제소바 가맹사업"),
    "BRD_JPN_0005": ("CAT_MAJ_03", "CAT_MID_0303", "역전우동0410: 우동·라멘 일식 면 요리"),
    "BRD_JPN_0006": ("CAT_MAJ_03", "CAT_MID_0302", "상무초밥: 초밥 전문 가맹사업"),
    "BRD_JPN_0007": ("CAT_MAJ_03", "CAT_MID_0304", "토끼정: 일본 가정식·덮밥 가맹사업"),

    # 4. 양식·세계음식 (8개)
    "BRD_WST_0001": ("CAT_MAJ_04", "CAT_MID_0402", "아웃백스테이크하우스: 패밀리레스토랑 직영 체인"),
    "BRD_WST_0002": ("CAT_MAJ_04", "CAT_MID_0404", "애슐리퀸즈: 패밀리 뷔페/샐러드바 직영 체인"),
    "BRD_WST_0003": ("CAT_MAJ_04", "CAT_MID_0402", "빕스: 패밀리레스토랑 직영 체인"),
    "BRD_WST_0004": ("CAT_MAJ_04", "CAT_MID_0401", "서가앤쿡: 파스타/스테이크 캐주얼 다이닝"),
    "BRD_WST_0005": ("CAT_MAJ_04", "CAT_MID_0401", "롤링파스타: 캐주얼 파스타 가맹사업"),
    "BRD_WST_0006": ("CAT_MAJ_04", "CAT_MID_0401", "매드포갈릭: 갈릭 파스타/스테이크 직영 체인"),
    "BRD_WST_0007": ("CAT_MAJ_04", "CAT_MID_0403", "포메인: 베트남 쌀국수 가맹사업"),
    "BRD_WST_0008": ("CAT_MAJ_04", "CAT_MID_0403", "미스사이공: 베트남 쌀국수 가맹사업"),

    # 5. 치킨·패스트푸드 (15개)
    "BRD_CHK_0001": ("CAT_MAJ_05", "CAT_MID_0501", "교촌치킨: 치킨 프랜차이즈"),
    "BRD_CHK_0002": ("CAT_MAJ_05", "CAT_MID_0501", "bbq치킨: 치킨 프랜차이즈"),
    "BRD_CHK_0003": ("CAT_MAJ_05", "CAT_MID_0501", "bhc치킨: 치킨 프랜차이즈"),
    "BRD_CHK_0004": ("CAT_MAJ_05", "CAT_MID_0502", "맘스터치: 버거·치킨 패스트푸드"),
    "BRD_CHK_0005": ("CAT_MAJ_05", "CAT_MID_0502", "버거킹: 햄버거 패스트푸드"),
    "BRD_CHK_0006": ("CAT_MAJ_05", "CAT_MID_0502", "롯데리아: 햄버거 패스트푸드"),
    "BRD_CHK_0007": ("CAT_MAJ_05", "CAT_MID_0502", "맥도날드: 햄버거 패스트푸드"),
    "BRD_CHK_0008": ("CAT_MAJ_05", "CAT_MID_0501", "굽네치킨: 오븐구이 치킨"),
    "BRD_CHK_0009": ("CAT_MAJ_05", "CAT_MID_0501", "노랑통닭: 가마솥 통닭 치킨"),
    "BRD_CHK_0010": ("CAT_MAJ_05", "CAT_MID_0501", "푸라닭: 오븐후라이드 치킨"),
    "BRD_CHK_0011": ("CAT_MAJ_05", "CAT_MID_0501", "처갓집양념치킨: 양념치킨 전문"),
    "BRD_CHK_0012": ("CAT_MAJ_05", "CAT_MID_0501", "네네치킨: 치킨 프랜차이즈"),
    "BRD_CHK_0013": ("CAT_MAJ_05", "CAT_MID_0504", "써브웨이: 샌드위치 글로벌 패스트푸드"),
    "BRD_CHK_0014": ("CAT_MAJ_05", "CAT_MID_0502", "프랭크버거: 수제버거 가맹사업"),
    "BRD_CHK_0015": ("CAT_MAJ_05", "CAT_MID_0502", "노브랜드버거: 가성비 버거 가맹사업"),

    # 6. 분식·간편식 (10개)
    "BRD_SNK_0001": ("CAT_MAJ_06", "CAT_MID_0602", "김가네김밥: 김밥·분식 가맹사업"),
    "BRD_SNK_0002": ("CAT_MAJ_06", "CAT_MID_0601", "죠스떡볶이: 매운 떡볶이 가맹사업"),
    "BRD_SNK_0003": ("CAT_MAJ_06", "CAT_MID_0601", "동대문엽기떡볶이: 엽떡 가맹사업"),
    "BRD_SNK_0004": ("CAT_MAJ_06", "CAT_MID_0601", "신전떡볶이: 국물 떡볶이 가맹사업"),
    "BRD_SNK_0005": ("CAT_MAJ_06", "CAT_MID_0601", "신참떡볶이: 즉석 떡볶이 가맹사업"),
    "BRD_SNK_0006": ("CAT_MAJ_06", "CAT_MID_0602", "바르다김선생: 프리미엄 김밥 가맹사업"),
    "BRD_SNK_0007": ("CAT_MAJ_06", "CAT_MID_0602", "고봉민김밥인: 프리미엄 수제 김밥 가맹사업"),
    "BRD_SNK_0008": ("CAT_MAJ_06", "CAT_MID_0601", "청년다방: 즉석 떡볶이·다방 가맹사업"),
    "BRD_SNK_0009": ("CAT_MAJ_06", "CAT_MID_0601", "두끼: 즉석 떡볶이 뷔페 가맹사업"),
    "BRD_SNK_0010": ("CAT_MAJ_06", "CAT_MID_0601", "배떡: 로제 떡볶이 배달 가맹사업"),

    # 7. 카페·음료 (12개)
    "BRD_CAF_0001": ("CAT_MAJ_07", "CAT_MID_0701", "스타벅스: 직영 프리미엄 커피전문점"),
    "BRD_CAF_0002": ("CAT_MAJ_07", "CAT_MID_0702", "이디야커피: 가성비·테이크아웃 커피전문점"),
    "BRD_CAF_0003": ("CAT_MAJ_07", "CAT_MID_0701", "투썸플레이스: 프리미엄 디저트·커피전문점"),
    "BRD_CAF_0004": ("CAT_MAJ_07", "CAT_MID_0702", "메가MGC커피: 대용량 저가커피 1위"),
    "BRD_CAF_0005": ("CAT_MAJ_07", "CAT_MID_0702", "컴포즈커피: 대용량 저가커피 가맹사업"),
    "BRD_CAF_0006": ("CAT_MAJ_07", "CAT_MID_0702", "빽다방: 가성비 저가커피 가맹사업"),
    "BRD_CAF_0007": ("CAT_MAJ_07", "CAT_MID_0702", "더벤티: 대용량 음료·커피 가맹사업"),
    "BRD_CAF_0008": ("CAT_MAJ_07", "CAT_MID_0703", "공차: 버블티·밀크티 전문 가맹사업"),
    "BRD_CAF_0009": ("CAT_MAJ_07", "CAT_MID_0701", "폴바셋: 스페셜티 커피 직영 체인"),
    "BRD_CAF_0010": ("CAT_MAJ_07", "CAT_MID_0701", "할리스: 프리미엄 커피전문점"),
    "BRD_CAF_0011": ("CAT_MAJ_07", "CAT_MID_0701", "파스쿠찌: 이탈리안 에스프레소 카페"),
    "BRD_CAF_0012": ("CAT_MAJ_07", "CAT_MID_0701", "커피빈: 직영 커피전문점 체인"),

    # 8. 베이커리·디저트 (8개)
    "BRD_BKR_0001": ("CAT_MAJ_08", "CAT_MID_0801", "파리바게뜨: 1위 제과/베이커리"),
    "BRD_BKR_0002": ("CAT_MAJ_08", "CAT_MID_0801", "뚜레쥬르: 제과/베이커리 가맹사업"),
    "BRD_BKR_0003": ("CAT_MAJ_08", "CAT_MID_0803", "배스킨라빈스: 1위 아이스크림 전문점"),
    "BRD_BKR_0004": ("CAT_MAJ_08", "CAT_MID_0803", "설빙: 코리안 디저트 빙수 전문점"),
    "BRD_BKR_0005": ("CAT_MAJ_08", "CAT_MID_0802", "던킨: 도넛/와플 전문 가맹사업"),
    "BRD_BKR_0006": ("CAT_MAJ_08", "CAT_MID_0802", "크리스피크림도넛: 도넛 전문 체인"),
    "BRD_BKR_0007": ("CAT_MAJ_08", "CAT_MID_0802", "와플대학: 와플 디저트 전문"),
    "BRD_BKR_0008": ("CAT_MAJ_08", "CAT_MID_0804", "디저트39: 케이크/타르트 디저트 전문"),
}


# ==============================================================================
# 4. 소진공 중분류 텍스트 -> 대분류 매핑 헬퍼
# ==============================================================================
MCLS_NAME_TO_MAJOR_MAP: Dict[str, str] = {
    "한식": "CAT_MAJ_01",
    "중식": "CAT_MAJ_02",
    "일식": "CAT_MAJ_03",
    "서양식": "CAT_MAJ_04",
    "동남아시아": "CAT_MAJ_04",
    "기타 외국": "CAT_MAJ_04",
    "구내식당·뷔페": "CAT_MAJ_04",
    "비알코올 ": "CAT_MAJ_07",
    "비알코올": "CAT_MAJ_07",
    # 기타 간이의 경우 소분류(inds_scls_cd)에 따라 치킨/버거/피자/분식/베이커리로 분기
}


def resolve_semas_to_mid(scls_cd: str, store_name: str = "") -> Tuple[str, str, str, str]:
    """
    소진공 소분류 코드와 상호명을 기반으로 (대분류ID, 중분류ID, 매핑규칙, 모호성상태)를 결정합니다.
    반환값: (category_maj_id, category_mid_id, rule_type, status)
    """
    matched_rules = [r for r in SEMAS_TO_MID_RULES if r["scls_code"] == scls_cd]
    if not matched_rules:
        # 미등록 코드인 경우
        return ("CAT_MAJ_01", "CAT_MID_0108", "UNREGISTERED_FALLBACK", "UNCLASSIFIED")

    if len(matched_rules) == 1:
        # 단일 1:1 매핑
        r = matched_rules[0]
        maj_id = r["category_mid_id"][:10].replace("MID", "MAJ")
        return (maj_id, r["category_mid_id"], r["rule_type"], "CATEGORY_PROVISIONAL")

    # 1:N 매핑 처리
    # 상호명 키워드 검사
    clean_name = store_name.strip().lower()
    for r in matched_rules:
        if r.get("keywords"):
            for kw in r["keywords"]:
                if kw.lower() in clean_name:
                    maj_id = r["category_mid_id"][:10].replace("MID", "MAJ")
                    return (maj_id, r["category_mid_id"], "KEYWORD_RESOLVED", "CATEGORY_PROVISIONAL")

    # 키워드로 해소되지 않은 경우 기본(primary) 규칙 적용
    primary_rule = next((r for r in matched_rules if r["is_primary"] == 1), matched_rules[0])
    maj_id = primary_rule["category_mid_id"][:10].replace("MID", "MAJ")
    
    # 1:N 코드에서 키워드 미매칭 시 모호 상태 표기
    status = "AMBIGUOUS_REVIEW" if len(matched_rules) > 1 else "CATEGORY_PROVISIONAL"
    return (maj_id, primary_rule["category_mid_id"], "DEFAULT_PRIMARY", status)
