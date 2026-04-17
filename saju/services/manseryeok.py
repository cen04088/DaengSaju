import sajupy

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

def analyze_elements(pillars: dict):
    """
    사주 팔자(4주 8자)의 오행 비중을 계산합니다.
    """
    elements = {'목': 0, '화': 0, '토': 0, '금': 0, '수': 0}
    total = 0
    chars = []

    # 년, 월, 일, (시)의 천간, 지지 수집
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

    # 퍼센트 계산
    if total > 0:
        for k in elements:
            elements[k] = round((elements[k] / total) * 100, 1)

    return elements

def get_saju_for_dog(birth_date, birth_time=None):
    """
    강아지의 생년월일시를 기반으로 사주 정보를 반환합니다.
    birth_date: datetime.date
    birth_time: datetime.time or None
    """
    year = birth_date.year
    month = birth_date.month
    day = birth_date.day
    
    # 시주를 모를 때는 일단 12시로 계산하되 나중에 반환값에서 시주를 뺍니다.
    hour = birth_time.hour if birth_time else 12
    minute = birth_time.minute if birth_time else 0

    try:
        # sajupy는 양력 기준으로 계산. 음력을 쓰려면 사전 변환 필요.
        # 현 로직은 공통 양력 기준
        result = sajupy.calculate_saju(year, month, day, hour, minute)
    except Exception as e:
        print("Saju calculate error:", e)
        # Fallback if any error occurs
        result = {
            'year_pillar': '알수없음', 'month_pillar': '알수없음', 
            'day_pillar': '알수없음', 'hour_pillar': '알수없음',
            'day_stem': '무'
        }

    year_pillar = result.get('year_pillar', '')
    month_pillar = result.get('month_pillar', '')
    day_pillar = result.get('day_pillar', '')
    hour_pillar = result.get('hour_pillar', '') if birth_time else None

    # 일간 오행 (주인공의 타고난 기질)
    day_stem = result.get('day_stem', '')
    main_element = ELEMENT_MAP.get(day_stem, '알수없음')

    # 성분 계산을 위해 dict를 보냅니다.
    # 단, 시주를 모르면 hour 부분은 삭제
    pillars_for_elements = result.copy()
    if not birth_time:
        pillars_for_elements.pop('hour_stem', None)
        pillars_for_elements.pop('hour_branch', None)

    distribution = analyze_elements(pillars_for_elements)

    return {
        'year_pillar': year_pillar,
        'month_pillar': month_pillar,
        'day_pillar': day_pillar,
        'hour_pillar': hour_pillar,
        'main_element': main_element,
        'element_distribution': distribution
    }
