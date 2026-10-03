"""
사전 생성(LLM) 콘텐츠 위에 얹는 규칙 기반 콘텐츠.

- 일주(日柱) 캐릭터: 60갑자마다 다른 별명 + 천간·지지 조합 설명 → 같은 오행이어도 결과가 겹치지 않게 함
- 띠(年支)와 띠 궁합(육합·삼합·충): 보호자 궁합 점수 보정, 강아지 친구 궁합에 사용
- 강아지 ↔ 강아지(댕친) 궁합 문구
"""
import hashlib

from .manseryeok import has_batchim

ELEMENT_HANJA = {'목': '木', '화': '火', '토': '土', '금': '金', '수': '水'}

STEMS = {
    '甲': {'ko': '갑', 'element': '목', 'keyword': '듬직한 대장',
          'line': '큰 나무(甲木)처럼 곧고 듬직해서, 한번 정한 산책 코스는 끝까지 지키는 대장 기질이에요.'},
    '乙': {'ko': '을', 'element': '목', 'keyword': '붙임성 만렙',
          'line': '풀과 덩굴(乙木)처럼 유연해서, 낯선 곳에서도 금세 적응하고 누구에게나 살갑게 다가가요.'},
    '丙': {'ko': '병', 'element': '화', 'keyword': '분위기 메이커',
          'line': '태양(丙火)처럼 밝아서, 꼬리 한 번 흔들면 집안 분위기가 환해지는 분위기 메이커예요.'},
    '丁': {'ko': '정', 'element': '화', 'keyword': '다정다감',
          'line': '촛불(丁火)처럼 따뜻하고 섬세해서, 보호자님 기분을 가장 먼저 알아채고 곁을 지켜줘요.'},
    '戊': {'ko': '무', 'element': '토', 'keyword': '느긋한 든든함',
          'line': '큰 산(戊土)처럼 느긋하고 묵직해서, 웬만한 소리에는 꿈쩍 않는 든든한 성격이에요.'},
    '己': {'ko': '기', 'element': '토', 'keyword': '포근한 껌딱지',
          'line': '기름진 흙(己土)처럼 포근해서, 품에 안기는 걸 좋아하고 가족을 살뜰히 챙겨요.'},
    '庚': {'ko': '경', 'element': '금', 'keyword': '의리파',
          'line': '단단한 바위(庚金)처럼 씩씩해서, 의리 있고 한번 믿은 사람은 끝까지 따라요.'},
    '辛': {'ko': '신', 'element': '금', 'keyword': '깔끔쟁이',
          'line': '반짝이는 보석(辛金)처럼 깔끔하고 섬세해서, 자기 자리와 물건에 대한 취향이 확실해요.'},
    '壬': {'ko': '임', 'element': '수', 'keyword': '호기심 탐험가',
          'line': '넓은 바다(壬水)처럼 호기심이 많아서, 새로운 냄새와 길을 탐험할 때 눈이 반짝여요.'},
    '癸': {'ko': '계', 'element': '수', 'keyword': '눈치 백단',
          'line': '이슬비(癸水)처럼 촉촉하고 눈치가 빨라서, 말하지 않아도 분위기를 척척 읽어내요.'},
}

BRANCHES = {
    '子': {'ko': '자', 'animal': '쥐', 'keyword': '간식 탐지기',
          'line': '여기에 한밤의 쥐(子) 기운이 더해져 머리 회전이 빠르고, 숨겨둔 간식은 기가 막히게 찾아내요.'},
    '丑': {'ko': '축', 'animal': '소', 'keyword': '기다려 장인',
          'line': '여기에 우직한 소(丑) 기운이 더해져 참을성이 강하고, "기다려"를 누구보다 잘해요.'},
    '寅': {'ko': '인', 'animal': '호랑이', 'keyword': '산책 선두',
          'line': '여기에 호랑이(寅) 기운이 더해져 용감하고, 산책길에서는 늘 앞장서고 싶어 해요.'},
    '卯': {'ko': '묘', 'animal': '토끼', 'keyword': '귀쫑긋',
          'line': '여기에 토끼(卯) 기운이 더해져 귀여운 매력이 넘치고, 작은 소리에도 귀를 쫑긋 세워요.'},
    '辰': {'ko': '진', 'animal': '용', 'keyword': '골목 대장',
          'line': '여기에 용(辰) 기운이 더해져 존재감이 남달라서, 강아지 친구들 사이에서 대장 노릇을 해요.'},
    '巳': {'ko': '사', 'animal': '뱀', 'keyword': '외출 예지력',
          'line': '여기에 뱀(巳) 기운이 더해져 직감이 뛰어나서, 보호자님이 외출 준비하는 걸 귀신같이 알아채요.'},
    '午': {'ko': '오', 'animal': '말', 'keyword': '전력 질주',
          'line': '여기에 말(午) 기운이 더해져 에너지가 넘치고, 넓은 곳에서 전력 질주할 때 가장 행복해요.'},
    '未': {'ko': '미', 'animal': '양', 'keyword': '순둥순둥',
          'line': '여기에 양(未) 기운이 더해져 순하고 다정해서, 처음 보는 사람에게도 경계심이 적어요.'},
    '申': {'ko': '신', 'animal': '원숭이', 'keyword': '개인기 부자',
          'line': '여기에 원숭이(申) 기운이 더해져 재주가 많고, 새로운 개인기도 금방 배워요.'},
    '酉': {'ko': '유', 'animal': '닭', 'keyword': '아침 알람',
          'line': '여기에 닭(酉) 기운이 더해져 부지런하고 깔끔해서, 아침 기상 알람은 이 아이 담당이에요.'},
    '戌': {'ko': '술', 'animal': '개', 'keyword': '찐 댕댕이',
          'line': '여기에 개(戌) 기운까지 더해진 "찐 댕댕이 일주"라, 충성심과 집 지키는 본능이 남달라요.'},
    '亥': {'ko': '해', 'animal': '돼지', 'keyword': '꿀잠 먹보',
          'line': '여기에 돼지(亥) 기운이 더해져 먹는 즐거움을 알고, 낮잠과 간식 앞에서 세상 행복해져요.'},
}

# 60갑자 일주별 별명
ILJU_NICKNAMES = {
    '갑자': '밤숲을 지키는 꾀돌이', '을축': '눈 속에서도 꿋꿋한 들풀', '병인': '아침 해를 몰고 오는 꼬마 호랑이',
    '정묘': '촛불처럼 다정한 토끼', '무진': '큰 산을 지키는 용', '기사': '앞마당을 순찰하는 눈치왕',
    '경오': '강철 체력 질주왕', '신미': '반짝반짝 순둥이', '임신': '바다를 누비는 장난꾸러기',
    '계유': '이슬처럼 깔끔한 새침이', '갑술': '숲을 지키는 충직한 파수꾼', '을해': '들꽃밭의 행복한 먹보',
    '병자': '밤에도 빛나는 꼬마 태양', '정축': '겨울밤 모닥불 같은 든든이', '무인': '산을 호령하는 대장 호랑이',
    '기묘': '앞마당의 깡총 토끼', '경진': '강철 비늘의 용', '신사': '예리한 보석 탐정',
    '임오': '파도 위를 달리는 준마', '계미': '이슬 머금은 아기 양', '갑신': '나무 타는 재주꾼',
    '을유': '꽃밭의 부지런쟁이', '병술': '노을처럼 따뜻한 찐 댕댕이', '정해': '등불 아래 꿀잠 먹보',
    '무자': '큰 산 속 꾀돌이', '기축': '묵묵한 밭갈이 소', '경인': '강철 발톱 호랑이',
    '신묘': '보석처럼 귀한 토끼', '임진': '바다를 다스리는 용왕님', '계사': '조용한 이슬 속 전략가',
    '갑오': '숲길을 질주하는 준마', '을미': '풀밭 위 순둥 양', '병신': '햇살 아래 개구쟁이',
    '정유': '촛불 켜는 새벽 알람', '무술': '큰 산을 지키는 듬직한 수호견', '기해': '풍년 들판의 먹보',
    '경자': '날쌘 강철 꾀돌이', '신축': '반짝이는 우직한 소', '임인': '파도를 넘는 호랑이',
    '계묘': '이슬비 속 아기 토끼', '갑진': '청룡 같은 숲의 대장', '을사': '넝쿨 사이 눈치 백단',
    '병오': '한여름 태양을 닮은 질주왕', '정미': '촛불처럼 포근한 아기 양', '무신': '산을 누비는 재주꾼',
    '기유': '정원을 가꾸는 깔끔쟁이', '경술': '강철 의리의 수호견', '신해': '보석 같은 복덩이 먹보',
    '임자': '깊은 바다의 꾀돌이', '계축': '새벽 이슬 맞은 뚝심이', '갑인': '숲의 왕 호랑이',
    '을묘': '봄 풀밭의 깡총이', '병진': '태양을 삼킨 용', '정사': '반짝 촛불 같은 직관왕',
    '무오': '산을 넘는 천리마', '기미': '넓은 들판의 순둥 양', '경신': '강철 체력 개구쟁이',
    '신유': '보석처럼 빛나는 새침데기', '임술': '바다를 지키는 구조견', '계해': '비 오는 날 꿀잠 복덩이',
}

# 지지 관계 (한글 지지 기준)
SIX_HARMONY = {frozenset(pair) for pair in [('자', '축'), ('인', '해'), ('묘', '술'), ('진', '유'), ('사', '신'), ('오', '미')]}
THREE_HARMONY_GROUPS = [{'신', '자', '진'}, {'해', '묘', '미'}, {'인', '오', '술'}, {'사', '유', '축'}]
CLASH = {frozenset(pair) for pair in [('자', '오'), ('축', '미'), ('인', '신'), ('묘', '유'), ('진', '술'), ('사', '해')]}


def element_label(element):
    hanja = ELEMENT_HANJA.get(element)
    return f'{element}({hanja})' if hanja else element


def attach_josa(name, josa):
    """'은/는', '이/가', '을/를', '와/과', '이랑/랑' 형태의 조사를 이름 받침에 맞게 붙입니다."""
    with_batchim, without_batchim = {
        '은/는': ('은', '는'),
        '이/가': ('이', '가'),
        '을/를': ('을', '를'),
        '와/과': ('과', '와'),
        '이랑/랑': ('이랑', '랑'),
    }[josa]
    return name + (with_batchim if has_batchim(name) else without_batchim)


def pick_variant(options, *seed_parts):
    """같은 입력에는 항상 같은 결과가 나오도록 시드 기반으로 하나를 고릅니다."""
    seed = '|'.join(str(part) for part in seed_parts)
    digest = int(hashlib.md5(seed.encode('utf-8')).hexdigest(), 16)
    return options[digest % len(options)]


def seeded_offset(spread, *seed_parts):
    """-spread ~ +spread 범위의 결정적 정수 오프셋."""
    return pick_variant(list(range(-spread, spread + 1)), *seed_parts)


def get_day_pillar_profile(day_pillar):
    """일주(예: '甲子')로 일주 캐릭터 프로필을 만듭니다. 계산 불가 시 None."""
    if not day_pillar or len(day_pillar) < 2:
        return None
    stem = STEMS.get(day_pillar[0])
    branch = BRANCHES.get(day_pillar[1])
    if not stem or not branch:
        return None
    pillar_ko = stem['ko'] + branch['ko']
    return {
        'pillar': pillar_ko,
        'pillar_hanja': day_pillar[:2],
        'nickname': ILJU_NICKNAMES.get(pillar_ko, f"{branch['animal']} 기운의 댕댕이"),
        'description': f"{stem['line']} {branch['line']}",
        'keywords': [stem['keyword'], branch['keyword']],
        'element': stem['element'],
    }


def get_zodiac(year_pillar):
    """연주(예: '己亥')로 띠 정보를 반환합니다. 계산 불가 시 None."""
    if not year_pillar or len(year_pillar) < 2:
        return None
    branch = BRANCHES.get(year_pillar[1])
    if not branch:
        return None
    return {'branch': branch['ko'], 'animal': branch['animal'], 'label': f"{branch['animal']}띠"}


def get_zodiac_relation(branch_a, branch_b):
    """두 띠(한글 지지) 사이의 관계와 점수 보정치를 반환합니다."""
    if not branch_a or not branch_b:
        return None
    # type은 명리 용어(식별용), label은 화면에 보여줄 쉬운 말
    pair = frozenset((branch_a, branch_b))
    if branch_a == branch_b:
        return {'type': '같은 띠', 'label': '같은 띠', 'bonus': 3, 'description': '같은 띠라 생활 리듬과 취향이 닮았어요.'}
    if pair in SIX_HARMONY:
        return {'type': '육합(六合)', 'label': '찰떡 띠 궁합(육합)', 'bonus': 7, 'description': '띠끼리 서로 끌어당기는 찰떡 조합이에요.'}
    if any(pair <= group for group in THREE_HARMONY_GROUPS):
        return {'type': '삼합(三合)', 'label': '한 팀 띠 궁합(삼합)', 'bonus': 5, 'description': '띠끼리 한 팀처럼 힘을 모으는 조합이에요.'}
    if pair in CLASH:
        return {'type': '충(沖)', 'label': '티격태격 띠 궁합(충)', 'bonus': -5, 'description': '띠끼리 부딪히는 기운이 있지만, 서로 속도를 맞추면 더 단단해져요.'}
    return {'type': '평(平)', 'label': '무난한 띠 궁합', 'bonus': 0, 'description': '띠끼리 무난하고 편안하게 어울리는 조합이에요.'}


def build_zodiac_match(first_year_pillar, second_year_pillar):
    """두 연주로 띠 궁합 요약을 만듭니다. 한쪽이라도 계산 불가면 None."""
    first = get_zodiac(first_year_pillar)
    second = get_zodiac(second_year_pillar)
    if not first or not second:
        return None
    relation = get_zodiac_relation(first['branch'], second['branch'])
    return {
        'first': first['label'],
        'second': second['label'],
        'type': relation['type'],
        'label': relation['label'],
        'bonus': relation['bonus'],
        'description': relation['description'],
    }


def clamp_score(score, low=60, high=99):
    return max(low, min(high, score))


# 강아지 ↔ 강아지 궁합: 내 강아지(A) 기준 십성 관계별 문구
FRIEND_COMPATIBILITY = {
    '비겁': {
        'base': 86,
        'titles': ['쌍둥이 같은 단짝', '거울 보듯 닮은 베프'],
        'description': '{A_wa} {B_neun} 같은 {me} 기운을 타고나서 노는 취향도, 좋아하는 산책 속도도 꼭 닮았어요. 둘이 만나면 텐션이 두 배로 올라가는 찐친 조합이에요.',
        'tip': '닮은 만큼 장난감과 간식 욕심도 비슷해요. 각자 몫을 따로 챙겨주면 다툼 없이 오래 놀 수 있어요.',
    },
    '인성': {
        'base': 91,
        'titles': ['든든한 수호천사 친구', '곁을 지켜주는 보호자 친구'],
        'description': '{B}의 {fe} 기운이 {A}의 {me} 기운을 북돋아 주는 관계예요. {B_wa} 함께 있으면 {A_ga} 한결 편안해지고 자신감이 붙어요.',
        'tip': '처음 가보는 공원이나 낯선 산책길에 {B_wa} 함께 가 보세요. {A_ga} 훨씬 씩씩하게 탐색할 거예요.',
    },
    '식상': {
        'base': 87,
        'titles': ['다정한 리더와 따르미', '놀이를 이끄는 대장 콤비'],
        'description': '{A}의 {me} 기운이 {B}의 {fe} 기운을 살려주는 관계예요. {A_ga} 먼저 놀이를 제안하면 {B_ga} 신나게 따라오는 그림이 그려져요.',
        'tip': '{A_ga} 리드하는 터그 놀이나 공놀이가 잘 맞아요. 놀이가 끝나면 {A}에게 칭찬 간식을 꼭 챙겨주세요.',
    },
    '재성': {
        'base': 79,
        'titles': ['밀당 고수 콤비', '주도권은 우리 아이 콤비'],
        'description': '{A}의 {me} 기운이 {B}의 {fe} 기운을 이끄는 관계예요. 놀이 주도권은 {A}에게 있지만, {B_ga} 맞춰주는 덕분에 의외로 잘 굴러가요.',
        'tip': '가끔은 {B_ga} 고른 놀이도 해 보게 해주세요. 주도권을 나누면 사이가 훨씬 끈끈해져요.',
    },
    '관성': {
        'base': 73,
        'titles': ['티격태격 성장 콤비', '서로를 단련하는 라이벌'],
        'description': '{B}의 {fe} 기운이 {A}의 {me} 기운을 다잡는 관계예요. 처음엔 서열 정리로 티격태격할 수 있지만, 그 과정에서 {A_ga} 한 뼘 더 의젓해져요.',
        'tip': '첫 만남은 넓은 공터에서 짧게 시작해 주세요. 냄새 인사를 충분히 나누면 금방 친해져요.',
    },
}


def build_friend_compatibility(relationship_type, my_name, friend_name, my_element, friend_element, seed):
    """강아지 친구 궁합 문구와 기본 점수를 만듭니다."""
    content = FRIEND_COMPATIBILITY.get(relationship_type, FRIEND_COMPATIBILITY['비겁'])
    values = {
        'A': my_name,
        'A_wa': attach_josa(my_name, '와/과'),
        'A_ga': attach_josa(my_name, '이/가'),
        'A_neun': attach_josa(my_name, '은/는'),
        'B': friend_name,
        'B_wa': attach_josa(friend_name, '와/과'),
        'B_ga': attach_josa(friend_name, '이/가'),
        'B_neun': attach_josa(friend_name, '은/는'),
        'me': element_label(my_element),
        'fe': element_label(friend_element),
    }
    return {
        'base_score': content['base'],
        'title': pick_variant(content['titles'], seed, 'title'),
        'description': content['description'].format(**values),
        'tip': content['tip'].format(**values),
    }
