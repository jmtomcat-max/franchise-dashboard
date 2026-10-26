"""
Stage 4B: 상호명 정규화 및 가역적 지점 접미어 분리 엔진 (버그 수정 및 정밀화)
프로젝트: D:/Franchise_Dashboard
위치: src/stage4b/normalizer.py
"""

import re
import unicodedata
from typing import Dict, Any, Optional

# 1. 법인격 및 사업자 형태 태그 패턴
# 괄호로 둘러싸인 단일문자 (주, 유, 합, 사, 재 등) 또는 온전한 법인 단어 (주식회사, 유한회사 등)만 매칭
LEGAL_ENTITY_PATTERN = re.compile(
    r"(?:\s*[\(\[\{](?:주|유|합|사|재|법인|개인)[\)\]\}]\s*|"
    r"\s*(?:주식회사|유한회사|합명회사|합자회사|사단법인|재단법인|사회적협동조합|협동조합)\s*)",
    re.IGNORECASE
)

# 2. 특수기호 및 문장부호 (공백으로 치환)
PUNCT_PATTERN = re.compile(r"['\",`~!?@#$%^&*()_+=/\\\[\]{}|:;<>·•]")

# 3. 지점명 접미어 패턴 (상호 뒷부분에 분리 기호와 함께 붙는 지점 표기)
BRANCH_SUFFIX_PATTERN = re.compile(
    r"[\s\-_/]+(?:"
    r"[가-힣0-9a-zA-Z]+(?:점|호점|직영점|가맹점|역점|본점|분점|센터|타운|스퀘어|로드점|드라이브스루점|DT점)"
    r"|제?[0-9]+호점"
    r"|본점"
    r"|직영점"
    r")$",
    re.IGNORECASE
)

# 4. 지점명 접두어 패턴 (상호 앞부분에 대괄호나 괄호로 붙는 지점 표기, 예: [강남점] 스타벅스)
BRANCH_PREFIX_PATTERN = re.compile(
    r"^[\(\[\{](?:[가-힣0-9a-zA-Z]+(?:점|호점|직영점|가맹점|역점|본점|분점))[\)\]\}]\s*",
    re.IGNORECASE
)

def normalize_store_name_full(raw_name: str, brch_nm_col: Optional[str] = None) -> Dict[str, Any]:
    """
    상호명을 정규화하고 지점명 분리, 법인격 태그, 복원 가능성을 종합 판정한다.
    
    반환 딕셔너리:
      - raw_bizes_nm: 원본 상호명
      - normalized_core_nm: 공백이 정제된 코어 상호명
      - clean_key: 특수문자/공백/대소문자가 완전히 제거된 매칭용 키
      - branch_suffix: 분리된 지점명
      - branch_position: 'SUFFIX' | 'PREFIX' | 'STANDALONE_COLUMN' | 'NONE'
      - legal_entity_tag: 추출된 법인격 표기
      - is_reconstructible: 원본 상호 복원 가능 여부 (1: 가능, 0: 불능)
    """
    if not raw_name:
        return {
            "raw_bizes_nm": "",
            "normalized_core_nm": "",
            "clean_key": "",
            "branch_suffix": brch_nm_col or None,
            "branch_position": "STANDALONE_COLUMN" if brch_nm_col else "NONE",
            "legal_entity_tag": None,
            "is_reconstructible": 1
        }

    # 1. 유니코드 NFC 정규화
    text = unicodedata.normalize("NFC", str(raw_name))
    original_text = text

    # 2. 법인격 태그 감지 및 추출 (온전한 단어 또는 괄호 감싸인 단일글자만 분리)
    legal_tag = None
    legal_match = LEGAL_ENTITY_PATTERN.search(text)
    if legal_match:
        legal_tag = legal_match.group(0).strip(" ()[]{}")
        text = LEGAL_ENTITY_PATTERN.sub(" ", text)

    # 3. 지점 접두어(Prefix) 검사
    branch_extracted = None
    branch_pos = "NONE"

    prefix_match = BRANCH_PREFIX_PATTERN.search(text)
    if prefix_match:
        branch_extracted = prefix_match.group(0).strip(" ()[]{}")
        branch_pos = "PREFIX"
        text = text[prefix_match.end():]
    else:
        # 4. 특수문자 공백 치환 전 지점 접미어(Suffix) 검사
        suffix_match = BRANCH_SUFFIX_PATTERN.search(text)
        if suffix_match:
            branch_extracted = suffix_match.group(0).strip(" -_/")
            branch_pos = "SUFFIX"
            text = text[:suffix_match.start()]

    # 5. 특수문자 공백 치환
    text = PUNCT_PATTERN.sub(" ", text)

    # 6. 연속 공백 압축 및 좌우 공백 제거
    core_nm = re.sub(r"\s+", " ", text).strip()

    # 7. 상호명 내에 지점 접미어가 없고 소진공 brch_nm 컬럼에 값이 있는 경우 보완
    if not branch_extracted and brch_nm_col and str(brch_nm_col).strip():
        branch_extracted = str(brch_nm_col).strip()
        branch_pos = "STANDALONE_COLUMN"

    # 8. 매칭용 클린 키 (공백 제거 및 소문자화)
    clean_key = re.sub(r"\s+", "", core_nm).lower()

    # 9. 가역성(Reconstructibility) 검증: 코어 상호와 지점명이 원본에 기반하는지
    is_reconstructible = 1 if len(core_nm) > 0 and (core_nm in original_text or clean_key in re.sub(r"\s+", "", original_text).lower()) else 0

    return {
        "raw_bizes_nm": raw_name,
        "normalized_core_nm": core_nm,
        "clean_key": clean_key,
        "branch_suffix": branch_extracted,
        "branch_position": branch_pos,
        "legal_entity_tag": legal_tag,
        "is_reconstructible": is_reconstructible
    }
