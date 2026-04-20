import sajupy
import re

# 오행 맵핑
ELEMENT_MAP = {
    # 천간 (한글 + 한자)
    '갑': '목', '甲': '목', '을': '목', '乙': '목',
    '병': '화', '丙': '화', '정': '화', '丁': '화',
    '무': '토', '戊': '토', '기': '토', '己': '토',
    '경': '금', '庚': '금', '신': '금', '辛': '금',
    '임': '수', '壬': '수', '계': '수', '癸': '수',
    
    # 지지 (한글 + 한자)
    '자': '수', '子': '수', '축': '토', '丑': '토',
    '인': '목', '寅': '목', '묘': '목', '卯': '목',
    '진': '토', '辰': '토', '사': '화', '巳': '화',
    '오': '화', '午': '화', '미': '토', '未': '토',
    '신': '금', '申': '금', '유': '금', '酉': '금',
    '술': '토', '戌': '토', '해': '수', '亥': '수'
}

# =========================================================
# 3단계: 십성(十星) 시스템 - 상생/상극 관계 테이블
# =========================================================

# 상생(相生): 木생火, 火생土, 土생金, 金생수, 수생木
SHENG_MAP = {
    '목': '화',  # 목이 화를 생함
    '화': '토',
    '토': '금',
    '금': '수',
    '수': '목',
}

# 상극(相克): 木克土, 土克水, 水克火, 火克金, 金克木
KE_MAP = {
    '목': '토',  # 목이 토를 극함
    '토': '수',
    '수': '화',
    '화': '금',
    '금': '목',
}

def get_relationship_type(primary: str, other: str) -> str:
    """
    본질 오행(primary)과 비교 대상 오행(other)의 관계를 십성 유형으로 반환합니다.
    """
    if primary == other:
        return '비겁'
    if SHENG_MAP.get(other) == primary:  # other가 primary를 생함
        return '인성'
    if SHENG_MAP.get(primary) == other:  # primary가 other를 생함
        return '식상'
    if KE_MAP.get(primary) == other:    # primary가 other를 극함
        return '재성'
    if KE_MAP.get(other) == primary:    # other가 primary를 극함
        return '관성'
    return '비겁'  # fallback

def get_secondary_element(distribution: dict, primary: str) -> str:
    """
    오행 분포에서 1위(주된 오행)를 제외한 2위 오행을 반환합니다.
    """
    if not distribution:
        return primary
    
    sorted_elements = sorted(distribution.items(), key=lambda x: x[1], reverse=True)
    
    # 1위 오행 결정
    first = sorted_elements[0][0] if sorted_elements else primary
    
    # 2위는 1위와 다른 오행 중 가장 높은 값
    for element, _ in sorted_elements[1:]:
        if element != first:
            return element
        
    return primary  # fallback

# =========================================================
# 2위 오행이 미치는 보조 영향 텍스트
# =========================================================

SECONDARY_INFLUENCE_TEXT = {
    ('목', '화'): "특히 화(火) 기운의 영향으로 감정 표현이 풍부하고 열정이 넘쳐요. 보호자님과의 교감에서 더욱 활발한 반응을 보일 거예요! 🔥",
    ('목', '토'): "토(土) 기운이 더해져 다소 고집스럽고 자기 페이스를 중시하는 면도 있어요. 무리하게 빠른 산책보다 느긋한 탐색 산책을 선호해요! 🌿",
    ('목', '금'): "금(金) 기운이 함께 작용해 날카로운 관찰력과 집중력이 특징이에요. 훈련 습득 속도가 빠르고 한 번 각인된 규칙을 잘 지킨답니다! ✨",
    ('목', '수'): "수(水) 기운이 목에 힘을 더해주어 감수성이 매우 풍부해요. 보호자님의 표정이나 감정 변화에 민감하게 반응하는 공감 천재예요! 💧",
    ('목', '목'): "목(木) 기운이 몰려 있어 독립심과 자유로운 영혼이 더욱 도드라져요. 넓은 공간에서 마음껏 뛰어다닐 때 가장 행복한 아이예요! 🌲",
    
    ('화', '목'): "목(木) 기운이 화를 도와 에너지가 급상승해요! 폭발적인 순발력과 장난치기를 좋아하며 항상 새로운 자극을 갈망한답니다! 🌱",
    ('화', '토'): "토(土) 기운이 열기를 중화시켜 겉보기보다 훨씬 안정적인 면이 있어요. 에너지가 넘치면서도 보호자 곁에서 편안히 쉬는 균형잡힌 아이예요! 🏡",
    ('화', '금'): "금(金) 기운과의 긴장감이 날카로운 집중력을 만들어요. 게임이나 훈련에서 승부욕을 발휘하고 쉽게 포기하지 않는 근성이 있답니다! 🏆",
    ('화', '수'): "수(水) 기운과 끌리고도 밀리는 묘한 긴장감을 갖고 있어요. 냉정한 판단력과 뜨거운 열정이 공존하는 복잡한 매력의 소유자예요! 🌊",
    ('화', '화'): "화(火)가 화(火)를 만나 에너지가 폭발적이에요! 세상의 모든 것에 호기심을 갖고 달려드는 에너자이저 그 자체랍니다! ⚡",
    
    ('토', '목'): "목(木) 기운의 영향으로 규칙 안에서도 자유를 추구하는 반전 매력이 있어요. 고집도 있지만 새로운 것에 쉽게 설레기도 한답니다! 🌿",
    ('토', '화'): "화(火) 기운이 포근한 토의 성격을 더욱 따뜻하게 달궈요. 보호자님과의 스킨십을 누구보다 소중히 여기는 살가운 아이예요! ☀️",
    ('토', '금'): "금(金) 기운이 더해져 섬세하고 완벽주의적인 면도 적지 않아요. 자기만의 깔끔한 루틴과 정해진 자리를 매우 좋아한답니다! 💎",
    ('토', '수'): "수(水) 기운과의 조합으로 신중하고 천천히 생각하는 편이에요. 하지만 한 번 신뢰를 쌓으면 그 누구보다 든든한 동반자가 된답니다! 🐢",
    ('토', '토'): "토(土) 기운이 특히 강해 안정과 현실감을 최우선으로 여겨요. 변화보다는 일관된 루틴 속에서 깊은 행복을 느끼는 아이예요! 🏠",
    
    ('금', '목'): "목(木) 기운이 날카로운 금 성향에 유연함과 창의성을 더해줘요. 단순 반복보다는 다양한 놀이와 탐색을 즐기는 아이예요! 🌲",
    ('금', '화'): "화(火) 기운과 맞부딪쳐 열정과 신중함이 공존해요. 행동하기 전에 잠깐 생각하지만, 한 번 결정하면 전력을 다하는 스타일이에요! 🔥",
    ('금', '토'): "토(土) 기운이 금의 예리함을 떠받쳐 더욱 단단한 성격을 만들어요. 보호자님에게 한번 복종하면 매우 일관성 있고 믿음직스럽답니다! 🗿",
    ('금', '수'): "수(水) 기운이 금에 힘을 불어넣어 지적 호기심이 특히 뛰어나요. 냄새 탐정처럼 세심한 탐색과 관찰을 즐기는 영리한 아이예요! 🌊",
    ('금', '금'): "금(金) 기운이 두 겹으로 겹쳐 자기주장이 강하고 개성이 뚜렷해요. 보호자님과 독립적인 관계를 선호하는 자존심 강한 아이예요! 💫",
    
    ('수', '목'): "목(木) 기운이 수에 힘을 받아 자유롭고 창의적인 면을 끌어내요. 자연 속 탐험과 새로운 냄새 맡기를 진정으로 즐기는 탐험가예요! 🌱",
    ('수', '화'): "화(火) 기운과의 긴장감이 직관력과 결단력을 동시에 키워줘요. 상황을 빠르게 파악하고 대담하게 행동하는 순간이 종종 있답니다! ⚡",
    ('수', '토'): "토(土) 기운이 깊은 수의 감수성에 현실적인 중심을 잡아줘요. 상상력이 풍부하면서도 보호자님 곁에 안전하게 머물기를 원한답니다 🌍",
    ('수', '금'): "금(金) 기운이 수를 더욱 풍요롭게 만들어 지혜롭고 차분한 성격이에요. 천천히 주변을 파악하고 상황에 맞게 유연하게 행동한답니다! 💎",
    ('수', '수'): "수(水) 기운이 넘쳐흘러 감정 기복이 풍부하고 공감 능력이 탁월해요. 보호자님의 기분 변화를 가장 먼저 알아채는 감정 안테나예요! 🌊",
}

def get_secondary_influence_text(primary: str, secondary: str) -> str:
    """2위 오행이 미치는 보조 영향 텍스트를 반환합니다."""
    return SECONDARY_INFLUENCE_TEXT.get((primary, secondary), "")

def analyze_elements(pillars: dict):
    """사주 팔자의 오행 비중을 계산합니다."""
    elements = {'목': 0, '화': 0, '토': 0, '금': 0, '수': 0}
    total = 0
    chars = []

    for key in ['year', 'month', 'day', 'hour']:
        if f'{key}_stem' in pillars and pillars[f'{key}_stem']:
            chars.append(pillars[f'{key}_stem'])
        if f'{key}_branch' in pillars and pillars[f'{key}_branch']:
            chars.append(pillars[f'{key}_branch'])

    for ch in chars:
        element = ELEMENT_MAP.get(ch)
        if element:
            elements[element] += 1
            total += 1

    if total > 0:
        for k in elements:
            elements[k] = round((elements[k] / total) * 100, 1)

    return elements

def get_saju_for_dog(birth_date, birth_time=None):
    """강아지의 생년월일시를 기반으로 사주 정보를 반환합니다."""
    year = birth_date.year
    month = birth_date.month
    day = birth_date.day
    
    hour = birth_time.hour if birth_time else 12
    minute = birth_time.minute if birth_time else 0

    try:
        result = sajupy.calculate_saju(year, month, day, hour, minute)
    except Exception as e:
        print("Saju calculate error:", e)
        result = {
            'year_pillar': '알수없음', 'month_pillar': '알수없음', 
            'day_pillar': '알수없음', 'hour_pillar': '알수없음',
            'day_stem': '무'
        }

    year_pillar = result.get('year_pillar', '')
    month_pillar = result.get('month_pillar', '')
    day_pillar = result.get('day_pillar', '')
    hour_pillar = result.get('hour_pillar', '') if birth_time else None

    day_stem = result.get('day_stem', '')
    main_element = ELEMENT_MAP.get(day_stem, '알수없음')

    pillars_for_elements = result.copy()
    if not birth_time:
        pillars_for_elements.pop('hour_stem', None)
        pillars_for_elements.pop('hour_branch', None)

    distribution = analyze_elements(pillars_for_elements)

    if distribution and main_element != '알수없음':
        sorted_elements = sorted(distribution.items(), key=lambda x: x[1], reverse=True)
        dominant_element = sorted_elements[0][0] if sorted_elements else main_element
        relationship_type = get_relationship_type(main_element, dominant_element)
        secondary_element = get_secondary_element(distribution, dominant_element)
    else:
        relationship_type = '비겁'
        secondary_element = main_element

    return {
        'year_pillar': year_pillar,
        'month_pillar': month_pillar,
        'day_pillar': day_pillar,
        'hour_pillar': hour_pillar,
        'main_element': main_element,
        'element_distribution': distribution,
        'relationship_type': relationship_type,
        'secondary_element': secondary_element,
    }

def add_hanja_to_terms(text: str) -> str:
    """텍스트 내의 주요 명리 용어(십성)에 한자를 병기합니다."""
    if not text:
        return text
    
    replacements = {
        '비겁': '비겁(比劫)',
        '인성': '인성(印星)',
        '식상': '식상(食傷)',
        '재성': '재성(財星)',
        '관성': '관성(官星)'
    }
    
    for term, hanja_term in replacements.items():
        pattern = re.compile(f"{term}(?!\\()", re.U)
        text = pattern.sub(hanja_term, text)
        
    return text

def has_batchim(text: str) -> bool:
    """한글 문자의 마지막 글자에 받침이 있는지 확인합니다."""
    if not text:
        return False
    last_char = text[-1]
    if not ('\uac00' <= last_char <= '\ud7a3'):
        return False
    return (ord(last_char) - 0xac00) % 28 > 0

def get_josa(name: str, josa_type: str) -> str:
    """이름에 맞는 조사를 반환합니다."""
    has_b = has_batchim(name)
    
    if josa_type in ['은', '는', '은/는', '은는']:
        return '은' if has_b else '는'
    if josa_type in ['이', '가', '이가', '이/가']:
        return '이' if has_b else '가'
    if josa_type in ['을', '를', '을/를', '을를']:
        return '을' if has_b else '를'
    if josa_type in ['와', '과', '와/과', '와과']:
        return '과' if has_b else '와'
    if josa_type in ['으로', '로', '으로/로', '으로로']:
        if has_b:
            last_char = name[-1]
            if (ord(last_char) - 0xac00) % 28 == 8: # 종성이 'ㄹ'인 경우
                return name + '로'
            return name + '으로'
        return name + '로'
    
    return josa_type

def smart_replace(text: str, dog_name: str, owner_name: str = None) -> str:
    """텍스트 내 플레이스홀더와 조사를 스마트하게 치환합니다."""
    if not text:
        return ""
    
    def get_replacement(name, josa_category):
        if not name:
            return ""
        has_b = has_batchim(name)
        
        if josa_category == '이/가':
            return (name + '이') if has_b else (name + '가')
        if josa_category == '이가':
            return (name + '이가') if has_b else (name + '가')
        if josa_category == '은/는':
            return (name + '은') if has_b else (name + '는')
        if josa_category == '을/를':
            return (name + '을') if has_b else (name + '를')
        if josa_category == '와/과':
            return (name + '과') if has_b else (name + '와')
        if josa_category == '으로/로':
            if has_b:
                last_char = name[-1]
                if (ord(last_char) - 0xac00) % 28 == 8: # 종성이 'ㄹ'인 경우
                    return name + '로'
                return name + '으로'
            return name + '로'
        return name + josa_category

    replacements = [
        ("[강아지이름]이가", "이가", dog_name),
        ("[강아지이름]은", "은/는", dog_name),
        ("[강아지이름]는", "은/는", dog_name),
        ("[강아지이름]이", "이/가", dog_name),
        ("[강아지이름]가", "이/가", dog_name),
        ("[강아지이름]을", "을/를", dog_name),
        ("[강아지이름]를", "을/를", dog_name),
        ("[강아지이름]과", "와/과", dog_name),
        ("[강아지이름]와", "와/과", dog_name),
        ("[강아지이름]으로", "으로/로", dog_name),
        ("[강아지이름]로", "으로/로", dog_name),
    ]
    
    if owner_name:
        replacements += [
            ("[보호자이름]이가", "이가", owner_name),
            ("[보호자이름]은", "은/는", owner_name),
            ("[보호자이름]는", "은/는", owner_name),
            ("[보호자이름]이", "이/가", owner_name),
            ("[보호자이름]가", "이/가", owner_name),
            ("[보호자이름]을", "을/를", owner_name),
            ("[보호자이름]를", "을/를", owner_name),
            ("[보호자이름]과", "와/과", owner_name),
            ("[보호자이름]와", "와/과", owner_name),
            ("[보호자이름]으로", "으로/로", owner_name),
            ("[보호자이름]로", "으로/로", owner_name),
        ]
    
    result = text
    for placeholder, category, name in replacements:
        if placeholder in result:
            replacement_text = get_replacement(name, category)
            result = result.replace(placeholder, replacement_text)
        
    result = result.replace("[강아지이름]", dog_name)
    if owner_name:
        result = result.replace("[보호자이름]", owner_name)
        
    return result
