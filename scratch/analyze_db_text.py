import sajupy
import sys

# Set encoding to utf-8 for printing
sys.stdout.reconfigure(encoding='utf-8')

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

def analyze(y, m, d, h=12, mi=0):
    result = sajupy.calculate_saju(y, m, d, h, mi)
    print(f"\n--- Analysis for {y}-{m}-{d} ---")
    
    chars = []
    for key in ['year', 'month', 'day', 'hour']:
        stem = result.get(f'{key}_stem')
        branch = result.get(f'{key}_branch')
        if stem:
            el = ELEMENT_MAP.get(stem, 'Unknown')
            print(f"{key}_stem: {stem} -> {el}")
            chars.append(stem)
        if branch:
            el = ELEMENT_MAP.get(branch, 'Unknown')
            print(f"{key}_branch: {branch} -> {el}")
            chars.append(branch)

    elements = {'목': 0, '화': 0, '토': 0, '금': 0, '수': 0}
    for ch in chars:
        element = ELEMENT_MAP.get(ch)
        if element:
            elements[element] += 1
            
    print("Final Counts:", elements)

analyze(1997, 6, 29)
