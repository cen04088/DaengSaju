import sajupy
from datetime import date

def test_date(y, m, d, h=12, mi=0):
    result = sajupy.calculate_saju(y, m, d, h, mi)
    print(f"\n--- Testing {y}-{m:02d}-{d:02d} {h:02d}:{mi:02d} ---")
    
    pillars = {
        'Year': (result.get('year_stem'), result.get('year_branch')),
        'Month': (result.get('month_stem'), result.get('month_branch')),
        'Day': (result.get('day_stem'), result.get('day_branch')),
        'Hour': (result.get('hour_stem'), result.get('hour_branch'))
    }
    
    for k, v in pillars.items():
        print(f"{k} Pillar: {v[0]}{v[1]}")

    ELEMENT_MAP = {
        '갑': '목', '甲': '목', '을': '목', '乙': '목',
        '병': '화', '丙': '화', '정': '화', '丁': '화',
        '무': '토', '戊': '토', '기': '토', '己': '토',
        '경': '금', '庚': '금', '신': '금', '辛': '금',
        '임': '수', '壬': '수', '계': '수', '癸': '수',
        '자': '수', '子': '수', '축': '토', '丑': '토',
        '인': '목', '寅': '목', '묘': '목', '卯': '목',
        '진': '토', '辰': '토', '사': '화', '巳': '화',
        '오': '화', '午': '화', '미': '토', '未': '토',
        '신': '금', '申': '금', '유': '금', '酉': '금',
        '술': '토', '戌': '토', '해': '수', '亥': '수'
    }

    counts = {'목': 0, '화': 0, '토': 0, '금': 0, '수': 0}
    for stem, branch in pillars.values():
        if stem: counts[ELEMENT_MAP.get(stem, '?')] += 1
        if branch: counts[ELEMENT_MAP.get(branch, '?')] += 1
    
    print("Counts:", counts)

# Test the user's date
test_date(1997, 6, 29)
# Test if it might be interpreting as lunar (Solar 1997-08-01 is Lunar 1997-06-29)
test_date(1997, 8, 1) 
