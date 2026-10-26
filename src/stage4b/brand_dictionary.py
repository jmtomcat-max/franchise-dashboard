"""
Stage 4B: 브랜드 사전, 별칭, 충돌 해결 규칙 및 오탐 방지 필터 정의
프로젝트: D:/Franchise_Dashboard
위치: src/stage4b/brand_dictionary.py
"""

from typing import Dict, List, Any, Set

# ==============================================================================
# 1. 8대 대분류별 공인 브랜드 및 별칭 마스터 사전 (Brand Seed Master)
# ==============================================================================
OFFICIAL_BRAND_SEEDS: List[Dict[str, Any]] = [
    # --------------------------------------------------------------------------
    # 1. 한식 (Korean Food)
    # --------------------------------------------------------------------------
    {
        "candidate_id": "CAN_BRD_KOR_0001",
        "brand_name": "본죽",
        "category_major": "한식",
        "aliases": ["본죽", "BONJUK", "본죽앤비빔밥", "본죽&비빔밥", "본죽비빔밥", "본죽앤비빔밥cafe"],
        "negative_keywords": ["본죽집", "맛있는본죽", "일본죽", "근본죽", "본죽이"],
        "official_source": "KFTC_CONFIRMED"
    },
    {
        "candidate_id": "CAN_BRD_KOR_0002",
        "brand_name": "본도시락",
        "category_major": "한식",
        "aliases": ["본도시락", "BONDOSIRAK"],
        "negative_keywords": ["본도시락집"],
        "official_source": "KFTC_CONFIRMED"
    },
    {
        "candidate_id": "CAN_BRD_KOR_0003",
        "brand_name": "본설렁탕",
        "category_major": "한식",
        "aliases": ["본설렁탕", "BONSOL"],
        "negative_keywords": [],
        "official_source": "KFTC_CONFIRMED"
    },
    {
        "candidate_id": "CAN_BRD_KOR_0004",
        "brand_name": "한솥도시락",
        "category_major": "한식",
        "aliases": ["한솥도시락", "한솥", "HANSOOT", "HANSOODOSIRAK"],
        "negative_keywords": ["한솥밥", "한솥식당", "한솥가득", "한솥마을"],
        "official_source": "KFTC_CONFIRMED"
    },
    {
        "candidate_id": "CAN_BRD_KOR_0005",
        "brand_name": "하남돼지집",
        "category_major": "한식",
        "aliases": ["하남돼지집", "하남돼지"],
        "negative_keywords": ["하남돼지골", "하남고깃집"],
        "official_source": "KFTC_CONFIRMED"
    },
    {
        "candidate_id": "CAN_BRD_KOR_0006",
        "brand_name": "두찜",
        "category_major": "한식",
        "aliases": ["두찜", "두마리찜닭두찜", "두마리찜닭 두찜", "두마리찜닭"],
        "negative_keywords": ["두마리", "모두찜", "두마리치킨"],
        "official_source": "KFTC_CONFIRMED"
    },
    {
        "candidate_id": "CAN_BRD_KOR_0007",
        "brand_name": "놀부보쌈",
        "category_major": "한식",
        "aliases": ["놀부보쌈", "놀부보쌈족발", "놀부보쌈&부대찌개", "놀부보쌈부대찌개"],
        "negative_keywords": ["놀부식당", "흥부놀부", "놀부네", "놀부마을", "놀부주막"],
        "official_source": "KFTC_CONFIRMED"
    },
    {
        "candidate_id": "CAN_BRD_KOR_0008",
        "brand_name": "놀부부대찌개",
        "category_major": "한식",
        "aliases": ["놀부부대찌개", "놀부부대"],
        "negative_keywords": ["놀부식당"],
        "official_source": "KFTC_CONFIRMED"
    },
    {
        "candidate_id": "CAN_BRD_KOR_0009",
        "brand_name": "원할머니보쌈",
        "category_major": "한식",
        "aliases": ["원할머니보쌈", "원할머니보쌈족발", "원할머니족발", "원할머니"],
        "negative_keywords": ["원할머니식당", "할머니보쌈"],
        "official_source": "KFTC_CONFIRMED"
    },
    {
        "candidate_id": "CAN_BRD_KOR_0010",
        "brand_name": "채선당",
        "category_major": "한식",
        "aliases": ["채선당", "채선당PLUS", "채선당플러스", "채선당SHABU"],
        "negative_keywords": ["채선식당"],
        "official_source": "KFTC_CONFIRMED"
    },
    {
        "candidate_id": "CAN_BRD_KOR_0011",
        "brand_name": "새마을식당",
        "category_major": "한식",
        "aliases": ["새마을식당"],
        "negative_keywords": ["새마을금고", "새마을포차"],
        "official_source": "KFTC_CONFIRMED"
    },
    {
        "candidate_id": "CAN_BRD_KOR_0012",
        "brand_name": "명륜진사갈비",
        "category_major": "한식",
        "aliases": ["명륜진사갈비", "명륜진사갈비NEW"],
        "negative_keywords": ["명륜식당"],
        "official_source": "KFTC_CONFIRMED"
    },
    {
        "candidate_id": "CAN_BRD_KOR_0013",
        "brand_name": "백채김치찌개",
        "category_major": "한식",
        "aliases": ["백채김치찌개", "백채"],
        "negative_keywords": [],
        "official_source": "KFTC_CONFIRMED"
    },

    # --------------------------------------------------------------------------
    # 2. 중식 (Chinese Food)
    # --------------------------------------------------------------------------
    {
        "candidate_id": "CAN_BRD_CHN_0001",
        "brand_name": "홍콩반점0410",
        "category_major": "중식",
        "aliases": ["홍콩반점0410", "홍콩반점 0410", "홍콩반점", "홍콩반점0410PLUS"],
        "negative_keywords": ["홍콩대반점", "홍콩차이나", "홍콩식당", "홍콩야시장"],
        "official_source": "KFTC_CONFIRMED"
    },
    {
        "candidate_id": "CAN_BRD_CHN_0002",
        "brand_name": "짬뽕지존",
        "category_major": "중식",
        "aliases": ["짬뽕지존"],
        "negative_keywords": ["짬뽕의지존", "지존짬뽕"],
        "official_source": "KFTC_CONFIRMED"
    },
    {
        "candidate_id": "CAN_BRD_CHN_0003",
        "brand_name": "보배반점",
        "category_major": "중식",
        "aliases": ["보배반점"],
        "negative_keywords": ["보배식당", "보배각"],
        "official_source": "KFTC_CONFIRMED"
    },
    {
        "candidate_id": "CAN_BRD_CHN_0004",
        "brand_name": "탕화쿵푸마라탕",
        "category_major": "중식",
        "aliases": ["탕화쿵푸마라탕", "탕화쿵푸", "탕화쿵푸 마라탕"],
        "negative_keywords": ["쿵푸마라탕", "탕화마라탕"],
        "official_source": "KFTC_CONFIRMED"
    },
    {
        "candidate_id": "CAN_BRD_CHN_0005",
        "brand_name": "라화쿵부",
        "category_major": "중식",
        "aliases": ["라화쿵부", "라화쿵부마라탕"],
        "negative_keywords": [],
        "official_source": "KFTC_CONFIRMED"
    },
    {
        "candidate_id": "CAN_BRD_CHN_0006",
        "brand_name": "교동짬뽕",
        "category_major": "중식",
        "aliases": ["교동짬뽕", "전국5대교동짬뽕", "강릉교동짬뽕"],
        "negative_keywords": ["교동칼국수"],
        "official_source": "KFTC_CONFIRMED"
    },
    {
        "candidate_id": "CAN_BRD_CHN_0007",
        "brand_name": "이비가짬뽕",
        "category_major": "중식",
        "aliases": ["이비가짬뽕", "이비가"],
        "negative_keywords": [],
        "official_source": "KFTC_CONFIRMED"
    },

    # --------------------------------------------------------------------------
    # 3. 일식 (Japanese Food)
    # --------------------------------------------------------------------------
    {
        "candidate_id": "CAN_BRD_JPN_0001",
        "brand_name": "미소야",
        "category_major": "일식",
        "aliases": ["미소야", "MISOYA"],
        "negative_keywords": ["미소야식", "미소식당", "미소라멘", "미소포차"],
        "official_source": "KFTC_CONFIRMED"
    },
    {
        "candidate_id": "CAN_BRD_JPN_0002",
        "brand_name": "아비꼬",
        "category_major": "일식",
        "aliases": ["아비꼬", "아비꼬카레", "ABIKO"],
        "negative_keywords": ["아비꼬식당", "아비꼬이자카야"],
        "official_source": "KFTC_CONFIRMED"
    },
    {
        "candidate_id": "CAN_BRD_JPN_0003",
        "brand_name": "쿠우쿠우",
        "category_major": "일식",
        "aliases": ["쿠우쿠우", "QOOQOO"],
        "negative_keywords": ["쿠우쿠우카페"],
        "official_source": "KFTC_CONFIRMED"
    },
    {
        "candidate_id": "CAN_BRD_JPN_0004",
        "brand_name": "백소정",
        "category_major": "일식",
        "aliases": ["백소정"],
        "negative_keywords": ["백소정식당"],
        "official_source": "KFTC_CONFIRMED"
    },
    {
        "candidate_id": "CAN_BRD_JPN_0005",
        "brand_name": "역전우동0410",
        "category_major": "일식",
        "aliases": ["역전우동0410", "역전우동 0410", "역전우동"],
        "negative_keywords": ["역전포차", "역전식당"],
        "official_source": "KFTC_CONFIRMED"
    },
    {
        "candidate_id": "CAN_BRD_JPN_0006",
        "brand_name": "상무초밥",
        "category_major": "일식",
        "aliases": ["상무초밥"],
        "negative_keywords": ["상무식당"],
        "official_source": "KFTC_CONFIRMED"
    },
    {
        "candidate_id": "CAN_BRD_JPN_0007",
        "brand_name": "토끼정",
        "category_major": "일식",
        "aliases": ["토끼정"],
        "negative_keywords": ["토끼네"],
        "official_source": "KFTC_CONFIRMED"
    },

    # --------------------------------------------------------------------------
    # 4. 양식·세계음식 (Western & World Food)
    # --------------------------------------------------------------------------
    {
        "candidate_id": "CAN_BRD_WST_0001",
        "brand_name": "아웃백스테이크하우스",
        "category_major": "양식·세계음식",
        "aliases": ["아웃백스테이크하우스", "아웃백", "OUTBACK", "아웃백스테이크"],
        "negative_keywords": ["아웃백카페"],
        "official_source": "KFTC_CONFIRMED"
    },
    {
        "candidate_id": "CAN_BRD_WST_0002",
        "brand_name": "애슐리퀸즈",
        "category_major": "양식·세계음식",
        "aliases": ["애슐리퀸즈", "애슐리", "ASHLEY QUEENS", "애슐리W", "ASHLEY"],
        "negative_keywords": ["애슐리네"],
        "official_source": "KFTC_CONFIRMED"
    },
    {
        "candidate_id": "CAN_BRD_WST_0003",
        "brand_name": "빕스",
        "category_major": "양식·세계음식",
        "aliases": ["빕스", "VIPS", "빕스프리미어"],
        "negative_keywords": ["빕스버거"],
        "official_source": "KFTC_CONFIRMED"
    },
    {
        "candidate_id": "CAN_BRD_WST_0004",
        "brand_name": "서가앤쿡",
        "category_major": "양식·세계음식",
        "aliases": ["서가앤쿡", "SEOGA & COOK", "서가엔쿡"],
        "negative_keywords": ["서가식당", "서가네"],
        "official_source": "KFTC_CONFIRMED"
    },
    {
        "candidate_id": "CAN_BRD_WST_0005",
        "brand_name": "롤링파스타",
        "category_major": "양식·세계음식",
        "aliases": ["롤링파스타", "ROLLING PASTA"],
        "negative_keywords": ["롤링파스타하우스"],
        "official_source": "KFTC_CONFIRMED"
    },
    {
        "candidate_id": "CAN_BRD_WST_0006",
        "brand_name": "매드포갈릭",
        "category_major": "양식·세계음식",
        "aliases": ["매드포갈릭", "MAD FOR GARLIC"],
        "negative_keywords": [],
        "official_source": "KFTC_CONFIRMED"
    },
    {
        "candidate_id": "CAN_BRD_WST_0007",
        "brand_name": "포메인",
        "category_major": "양식·세계음식",
        "aliases": ["포메인", "PHOMEIN"],
        "negative_keywords": [],
        "official_source": "KFTC_CONFIRMED"
    },
    {
        "candidate_id": "CAN_BRD_WST_0008",
        "brand_name": "미스사이공",
        "category_major": "양식·세계음식",
        "aliases": ["미스사이공", "노량진의전설미스사이공"],
        "negative_keywords": [],
        "official_source": "KFTC_CONFIRMED"
    },

    # --------------------------------------------------------------------------
    # 5. 치킨·패스트푸드 (Chicken & Fast Food)
    # --------------------------------------------------------------------------
    {
        "candidate_id": "CAN_BRD_CHK_0001",
        "brand_name": "교촌치킨",
        "category_major": "치킨·패스트푸드",
        "aliases": ["교촌치킨", "교촌", "KYOCHON"],
        "negative_keywords": ["교촌면옥", "교촌식당", "교촌마을", "교촌한우", "교촌칼국수", "교촌쌈밥", "교촌고기"],
        "official_source": "KFTC_CONFIRMED"
    },
    {
        "candidate_id": "CAN_BRD_CHK_0002",
        "brand_name": "bbq치킨",
        "category_major": "치킨·패스트푸드",
        "aliases": ["bbq치킨", "비비큐", "BBQ", "BBQ치킨", "비비큐치킨", "bbq"],
        "negative_keywords": ["바베큐", "비비큐포차", "삼겹살bbq", "바비큐", "바베큐파티"],
        "official_source": "KFTC_CONFIRMED"
    },
    {
        "candidate_id": "CAN_BRD_CHK_0003",
        "brand_name": "bhc치킨",
        "category_major": "치킨·패스트푸드",
        "aliases": ["bhc치킨", "BHC", "BHC치킨", "비에이치씨", "bhc"],
        "negative_keywords": ["bhc골프", "bhc볼링"],
        "official_source": "KFTC_CONFIRMED"
    },
    {
        "candidate_id": "CAN_BRD_CHK_0004",
        "brand_name": "맘스터치",
        "category_major": "치킨·패스트푸드",
        "aliases": ["맘스터치", "MOM'S TOUCH", "MOMSTOUCH", "맘스피자"],
        "negative_keywords": ["맘스터치식당", "엄마손"],
        "official_source": "KFTC_CONFIRMED"
    },
    {
        "candidate_id": "CAN_BRD_CHK_0005",
        "brand_name": "버거킹",
        "category_major": "치킨·패스트푸드",
        "aliases": ["버거킹", "BURGER KING", "BURGERKING"],
        "negative_keywords": ["버거킹포차", "수제버거킹"],
        "official_source": "KFTC_CONFIRMED"
    },
    {
        "candidate_id": "CAN_BRD_CHK_0006",
        "brand_name": "롯데리아",
        "category_major": "치킨·패스트푸드",
        "aliases": ["롯데리아", "LOTTERIA"],
        "negative_keywords": ["롯데마트롯데리아", "롯데리아식당"],
        "official_source": "KFTC_CONFIRMED"
    },
    {
        "candidate_id": "CAN_BRD_CHK_0007",
        "brand_name": "맥도날드",
        "category_major": "치킨·패스트푸드",
        "aliases": ["맥도날드", "MCDONALD'S", "MCDONALDS"],
        "negative_keywords": ["맥도날드식당"],
        "official_source": "KFTC_CONFIRMED"
    },
    {
        "candidate_id": "CAN_BRD_CHK_0008",
        "brand_name": "굽네치킨",
        "category_major": "치킨·패스트푸드",
        "aliases": ["굽네치킨", "굽네", "GOOBNE"],
        "negative_keywords": ["굽네식당"],
        "official_source": "KFTC_CONFIRMED"
    },
    {
        "candidate_id": "CAN_BRD_CHK_0009",
        "brand_name": "노랑통닭",
        "category_major": "치킨·패스트푸드",
        "aliases": ["노랑통닭"],
        "negative_keywords": ["노랑식당"],
        "official_source": "KFTC_CONFIRMED"
    },
    {
        "candidate_id": "CAN_BRD_CHK_0010",
        "brand_name": "푸라닭",
        "category_major": "치킨·패스트푸드",
        "aliases": ["푸라닭", "PURADAK"],
        "negative_keywords": [],
        "official_source": "KFTC_CONFIRMED"
    },
    {
        "candidate_id": "CAN_BRD_CHK_0011",
        "brand_name": "처갓집양념치킨",
        "category_major": "치킨·패스트푸드",
        "aliases": ["처갓집양념치킨", "처갓집통닭", "처갓집"],
        "negative_keywords": ["처갓집식당", "처갓집밥상"],
        "official_source": "KFTC_CONFIRMED"
    },
    {
        "candidate_id": "CAN_BRD_CHK_0012",
        "brand_name": "네네치킨",
        "category_major": "치킨·패스트푸드",
        "aliases": ["네네치킨", "NENE CHICKEN"],
        "negative_keywords": [],
        "official_source": "KFTC_CONFIRMED"
    },
    {
        "candidate_id": "CAN_BRD_CHK_0013",
        "brand_name": "써브웨이",
        "category_major": "치킨·패스트푸드",
        "aliases": ["써브웨이", "서브웨이", "SUBWAY"],
        "negative_keywords": ["서브웨이노래방"],
        "official_source": "KFTC_CONFIRMED"
    },
    {
        "candidate_id": "CAN_BRD_CHK_0014",
        "brand_name": "프랭크버거",
        "category_major": "치킨·패스트푸드",
        "aliases": ["프랭크버거", "FRANK BURGER"],
        "negative_keywords": [],
        "official_source": "KFTC_CONFIRMED"
    },
    {
        "candidate_id": "CAN_BRD_CHK_0015",
        "brand_name": "노브랜드버거",
        "category_major": "치킨·패스트푸드",
        "aliases": ["노브랜드버거", "NBB", "NO BRAND BURGER"],
        "negative_keywords": [],
        "official_source": "KFTC_CONFIRMED"
    },

    # --------------------------------------------------------------------------
    # 6. 분식·간편식 (Flour & Quick Food)
    # --------------------------------------------------------------------------
    {
        "candidate_id": "CAN_BRD_SNK_0001",
        "brand_name": "김가네김밥",
        "category_major": "분식·간편식",
        "aliases": ["김가네김밥", "김가네", "대학로김가네김밥"],
        "negative_keywords": ["김가네식당", "김가네한우", "김가네고깃집", "김가네국밥", "김가네포차"],
        "official_source": "KFTC_CONFIRMED"
    },
    {
        "candidate_id": "CAN_BRD_SNK_0002",
        "brand_name": "죠스떡볶이",
        "category_major": "분식·간편식",
        "aliases": ["죠스떡볶이", "죠스", "JAWS FOOD"],
        "negative_keywords": ["죠스바", "죠스호프"],
        "official_source": "KFTC_CONFIRMED"
    },
    {
        "candidate_id": "CAN_BRD_SNK_0003",
        "brand_name": "동대문엽기떡볶이",
        "category_major": "분식·간편식",
        "aliases": ["동대문엽기떡볶이", "엽기떡볶이", "엽떡"],
        "negative_keywords": ["엽기포차", "엽기불닭"],
        "official_source": "KFTC_CONFIRMED"
    },
    {
        "candidate_id": "CAN_BRD_SNK_0004",
        "brand_name": "신전떡볶이",
        "category_major": "분식·간편식",
        "aliases": ["신전떡볶이", "신전 떡볶이", "신전"],
        "negative_keywords": ["신전식당", "신전분식", "신전골", "신전마을"],
        "official_source": "KFTC_CONFIRMED"
    },
    {
        "candidate_id": "CAN_BRD_SNK_0005",
        "brand_name": "신참떡볶이",
        "category_major": "분식·간편식",
        "aliases": ["신참떡볶이", "신참"],
        "negative_keywords": [],
        "official_source": "KFTC_CONFIRMED"
    },
    {
        "candidate_id": "CAN_BRD_SNK_0006",
        "brand_name": "바르다김선생",
        "category_major": "분식·간편식",
        "aliases": ["바르다김선생", "김선생"],
        "negative_keywords": ["김선생한우"],
        "official_source": "KFTC_CONFIRMED"
    },
    {
        "candidate_id": "CAN_BRD_SNK_0007",
        "brand_name": "고봉민김밥인",
        "category_major": "분식·간편식",
        "aliases": ["고봉민김밥인", "고봉민김밥", "고봉민"],
        "negative_keywords": [],
        "official_source": "KFTC_CONFIRMED"
    },
    {
        "candidate_id": "CAN_BRD_SNK_0008",
        "brand_name": "청년다방",
        "category_major": "분식·간편식",
        "aliases": ["청년다방"],
        "negative_keywords": ["청년식당", "청년포차"],
        "official_source": "KFTC_CONFIRMED"
    },
    {
        "candidate_id": "CAN_BRD_SNK_0009",
        "brand_name": "두끼",
        "category_major": "분식·간편식",
        "aliases": ["두끼", "두끼떡볶이"],
        "negative_keywords": ["두끼식당"],
        "official_source": "KFTC_CONFIRMED"
    },
    {
        "candidate_id": "CAN_BRD_SNK_0010",
        "brand_name": "배떡",
        "category_major": "분식·간편식",
        "aliases": ["배떡", "배달떡볶이배떡"],
        "negative_keywords": [],
        "official_source": "KFTC_CONFIRMED"
    },

    # --------------------------------------------------------------------------
    # 7. 카페·음료 (Cafe & Beverages)
    # --------------------------------------------------------------------------
    {
        "candidate_id": "CAN_BRD_CAF_0001",
        "brand_name": "스타벅스",
        "category_major": "카페·음료",
        "aliases": ["스타벅스", "STARBUCKS", "스타벅스코리아", "STARBUCKS COFFEE"],
        "negative_keywords": ["스타벅스앞", "스타포차", "스타분식", "스타식당"],
        "official_source": "KFTC_CONFIRMED"
    },
    {
        "candidate_id": "CAN_BRD_CAF_0002",
        "brand_name": "이디야커피",
        "category_major": "카페·음료",
        "aliases": ["이디야커피", "이디야", "EDIYA COFFEE", "EDIYA"],
        "negative_keywords": ["이디야식당", "이디야호프", "이디야포차"],
        "official_source": "KFTC_CONFIRMED"
    },
    {
        "candidate_id": "CAN_BRD_CAF_0003",
        "brand_name": "투썸플레이스",
        "category_major": "카페·음료",
        "aliases": ["투썸플레이스", "투썸", "A TWOSOME PLACE", "TWOSOME PLACE"],
        "negative_keywords": ["투썸포차"],
        "official_source": "KFTC_CONFIRMED"
    },
    {
        "candidate_id": "CAN_BRD_CAF_0004",
        "brand_name": "메가MGC커피",
        "category_major": "카페·음료",
        "aliases": ["메가MGC커피", "메가커피", "MEGA COFFEE", "메가엠지씨커피", "MEGA MGC COFFEE", "메가엠지씨"],
        "negative_keywords": ["메가치킨", "메가분식", "메가호프"],
        "official_source": "KFTC_CONFIRMED"
    },
    {
        "candidate_id": "CAN_BRD_CAF_0005",
        "brand_name": "컴포즈커피",
        "category_major": "카페·음료",
        "aliases": ["컴포즈커피", "컴포즈", "COMPOSE COFFEE", "COMPOSE"],
        "negative_keywords": ["컴포즈식당"],
        "official_source": "KFTC_CONFIRMED"
    },
    {
        "candidate_id": "CAN_BRD_CAF_0006",
        "brand_name": "빽다방",
        "category_major": "카페·음료",
        "aliases": ["빽다방", "PAIK'S COFFEE", "PAIKS COFFEE"],
        "negative_keywords": ["빽보이", "빽보이피자"],
        "official_source": "KFTC_CONFIRMED"
    },
    {
        "candidate_id": "CAN_BRD_CAF_0007",
        "brand_name": "더벤티",
        "category_major": "카페·음료",
        "aliases": ["더벤티", "THE VENTI", "THEVENTI"],
        "negative_keywords": [],
        "official_source": "KFTC_CONFIRMED"
    },
    {
        "candidate_id": "CAN_BRD_CAF_0008",
        "brand_name": "공차",
        "category_major": "카페·음료",
        "aliases": ["공차", "GONG CHA", "GONGCHA"],
        "negative_keywords": ["공차포차"],
        "official_source": "KFTC_CONFIRMED"
    },
    {
        "candidate_id": "CAN_BRD_CAF_0009",
        "brand_name": "폴바셋",
        "category_major": "카페·음료",
        "aliases": ["폴바셋", "PAUL BASSETT"],
        "negative_keywords": [],
        "official_source": "KFTC_CONFIRMED"
    },
    {
        "candidate_id": "CAN_BRD_CAF_0010",
        "brand_name": "할리스",
        "category_major": "카페·음료",
        "aliases": ["할리스", "할리스커피", "HOLLYS COFFEE", "HOLLYS"],
        "negative_keywords": [],
        "official_source": "KFTC_CONFIRMED"
    },
    {
        "candidate_id": "CAN_BRD_CAF_0011",
        "brand_name": "파스쿠찌",
        "category_major": "카페·음료",
        "aliases": ["파스쿠찌", "CAFFE PASCUCCI", "PASCUCCI"],
        "negative_keywords": [],
        "official_source": "KFTC_CONFIRMED"
    },
    {
        "candidate_id": "CAN_BRD_CAF_0012",
        "brand_name": "커피빈",
        "category_major": "카페·음료",
        "aliases": ["커피빈", "THE COFFEE BEAN", "COFFEE BEAN"],
        "negative_keywords": ["커피빈식당"],
        "official_source": "KFTC_CONFIRMED"
    },

    # --------------------------------------------------------------------------
    # 8. 베이커리·디저트 (Bakery & Desserts)
    # --------------------------------------------------------------------------
    {
        "candidate_id": "CAN_BRD_BKR_0001",
        "brand_name": "파리바게뜨",
        "category_major": "베이커리·디저트",
        "aliases": ["파리바게뜨", "파리바게트", "PARIS BAGUETTE", "파리크라상"],
        "negative_keywords": ["파리식당", "바게뜨호프"],
        "official_source": "KFTC_CONFIRMED"
    },
    {
        "candidate_id": "CAN_BRD_BKR_0002",
        "brand_name": "뚜레쥬르",
        "category_major": "베이커리·디저트",
        "aliases": ["뚜레쥬르", "뚜레주르", "TOUS LES JOURS"],
        "negative_keywords": ["뚜레식당"],
        "official_source": "KFTC_CONFIRMED"
    },
    {
        "candidate_id": "CAN_BRD_BKR_0003",
        "brand_name": "배스킨라빈스",
        "category_major": "베이커리·디저트",
        "aliases": ["배스킨라빈스", "베스킨라빈스", "BASKIN ROBBINS", "배스킨라빈스31", "베스킨라빈스31"],
        "negative_keywords": ["베스킨식당"],
        "official_source": "KFTC_CONFIRMED"
    },
    {
        "candidate_id": "CAN_BRD_BKR_0004",
        "brand_name": "설빙",
        "category_major": "베이커리·디저트",
        "aliases": ["설빙", "SULBING", "코리안디저트카페설빙"],
        "negative_keywords": ["설빙식당", "설빙포차"],
        "official_source": "KFTC_CONFIRMED"
    },
    {
        "candidate_id": "CAN_BRD_BKR_0005",
        "brand_name": "던킨",
        "category_major": "베이커리·디저트",
        "aliases": ["던킨", "던킨도너츠", "DUNKIN'", "DUNKIN DONUTS", "DUNKIN"],
        "negative_keywords": ["던킨식당"],
        "official_source": "KFTC_CONFIRMED"
    },
    {
        "candidate_id": "CAN_BRD_BKR_0006",
        "brand_name": "크리스피크림도넛",
        "category_major": "베이커리·디저트",
        "aliases": ["크리스피크림도넛", "크리스피도넛", "크리스피크림", "KRISPY KREME"],
        "negative_keywords": [],
        "official_source": "KFTC_CONFIRMED"
    },
    {
        "candidate_id": "CAN_BRD_BKR_0007",
        "brand_name": "와플대학",
        "category_major": "베이커리·디저트",
        "aliases": ["와플대학", "WAFFLE UNIV"],
        "negative_keywords": [],
        "official_source": "KFTC_CONFIRMED"
    },
    {
        "candidate_id": "CAN_BRD_BKR_0008",
        "brand_name": "디저트39",
        "category_major": "베이커리·디저트",
        "aliases": ["디저트39", "DESSERT39"],
        "negative_keywords": [],
        "official_source": "KFTC_CONFIRMED"
    }
]

# ==============================================================================
# 2. 외식업 일반명사 단독 상호 (브랜드 후보 승격 전면 차단 Stop-words)
# ==============================================================================
GENERIC_FOOD_NOUNS: Set[str] = {
    # 단품 요리/식품 일반명사
    "김밥", "짜장면", "치킨", "피자", "커피", "카페", "국밥", "호프", "순대국", "순댓국",
    "삼겹살", "칼국수", "냉면", "돈까스", "돈가스", "떡볶이", "갈비", "한우", "곱창",
    "막창", "족발", "보쌈", "우동", "라멘", "초밥", "스시", "회", "해물탕", "아구찜",
    "부대찌개", "김치찌개", "된장찌개", "설렁탕", "곰탕", "갈비탕", "추어탕", "낙지",
    "쭈꾸미", "주꾸미", "닭갈비", "찜닭", "마라탕", "쌀국수", "토스트", "샌드위치",
    "베이커리", "빵", "도넛", "와플", "빙수", "아이스크림", "핫도그", "만두", "분식",
    "백반", "한정식", "식당", "밥상", "포차", "주막", "주점", "호프집", "치맥", "고깃집",
    "구이", "생고기", "정육식당", "면옥", "회관", "가든", "포장마차", "실내포차"
}

# ==============================================================================
# 3. 유사 상호 충돌 해결 그룹 (Prefix Confusion / Collision Groups)
# ==============================================================================
COLLISION_GROUPS = {
    "본_그룹": ["본죽", "본도시락", "본설렁탕", "본비빔밥"],
    "신_떡볶이_그룹": ["신전떡볶이", "신참떡볶이"],
    "더본_그룹": ["홍콩반점0410", "역전우동0410", "새마을식당", "롤링파스타", "빽다방"]
}

# ==============================================================================
# 4. 빠른 조회를 위한 전처리 인덱스 구축
# ==============================================================================
# clean_key -> brand_def
BRAND_LOOKUP_DICT: Dict[str, Dict[str, Any]] = {}

for b in OFFICIAL_BRAND_SEEDS:
    for alias in b["aliases"]:
        clean_alias = alias.replace(" ", "").lower()
        if clean_alias not in BRAND_LOOKUP_DICT:
            BRAND_LOOKUP_DICT[clean_alias] = b

def get_official_brand_by_clean_name(clean_key: str) -> Dict[str, Any]:
    """정규화된 클린 상호명으로 공인 브랜드를 검색한다."""
    return BRAND_LOOKUP_DICT.get(clean_key)
