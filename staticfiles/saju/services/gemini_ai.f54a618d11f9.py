import os
import json
import google.generativeai as genai

def _get_model():
    api_key = os.environ.get('GEMINI_API_KEY')
    if not api_key:
        raise ValueError("GEMINI_API_KEY가 설정되지 않았습니다.")
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-2.5-flash')
    return model
    
def _get_josa_name(name):
    """
    이름의 마지막 글자에 받침이 있으면 '이'를 붙여 반환합니다. (예: 바둑 -> 바둑이, 단비 -> 단비)
    """
    if not name:
        return name
    last_char = name[-1]
    # 한글 범위인지 확인
    if '가' <= last_char <= '힣':
        if (ord(last_char) - 0xAC00) % 28 > 0:
            return name + '이'
    return name

def generate_personality(dog_name, main_element, element_dist, saju_text="알 수 없음"):
    """
    사주의 오행과 원국을 바탕으로 강아지의 성격과 궁합 등을 분석합니다.
    사용자가 제시한 따뜻하고 친근하며('보호자님~'), 이모지를 적극 활용하는 포춘텔링 톤앤매너를 반영합니다.
    """
    model = _get_model()
    
    josa_name = _get_josa_name(dog_name)
    
    prompt = f"""
당신은 다정하고 통찰력 있는 반려견 전용 사주명리학 전문가이자 최고의 반려견 스토리텔러입니다.
강아지의 이름은 '{dog_name}'이며, 일간(타고난 본질) 오행은 '{main_element}', 
전체 오행의 구성 비율은 다음과 같습니다: {element_dist}.
(참고 사주 원국: {saju_text})

이제 보호자님에게 직접 따뜻하고 세심하게 말하는 듯한 말투(예: "보호자님! {josa_name}는 정말 ~한 아이네요!", "~하는 경향이 깊어요 😊")로 다음 항목들을 아주 상세하고 풍부하게 분석해 주세요. 
강아지 이름 뒤에 붙는 조사(은/는, 이/가, 을/를 등)를 한국어 문법에 맞게(받침 유무에 따라) 자연스럽게 사용해 주세요.

[중요 작성 지침]
1. 분량: 각 영역(간식운, 에너지, 사회성, 케어팁)마다 무조건 "최소 150자에서 250자 사이"로 매우 길고 디테일하게 작성해야 합니다. 절대 1~2문장으로 끝내지 마세요.
2. 구체성: 두루뭉술한 설명 대신, "예를 들어 산책하다 낯선 강아지를 만났을 때", "간식 봉투 소리를 들었을 때" 등 눈앞에 그려지는 생생한 상황극이나 예시를 2개 이상 꼭 포함하세요.
3. 가독성: 글이 촘촘해 보이지 않도록 문단(2~3문장)마다 반드시 이스케이프된 "\\n\\n" (줄바꿈 두 번)을 넣어주세요. 절대 한 덩어리의 긴 글로 작성하지 마세요.
4. 분위기: 모든 텍스트 본문에서 **이모지(🎨, ✨ 등 모든 그림 문자) 사용을 절대 금지**합니다. 오직 텍스트로만 전문적이고 깔끔하게 작성해 주세요.
5. 강조: 중요한 단어는 **굵게** 표시하되, 쉼표(,)를 남발하지 말고 간결한 문장으로 작성해 주세요.
6. 불렛 포인트: 팁이나 분석 항목을 나열할 때는 '- '를 사용하여 가독성을 높여주세요.
7. 한자 병기: 명리학 용어를 사용할 때는 한자를 병기하세요. (예: 비겁(比劫), 인성(印星) 등)

반드시 아래에 정의된 Key를 가진 완벽하고 유효한(Valid) JSON 객체로반환하세요.

{{
    "personality_summary": "{josa_name}의 성격을 보여주는 아주 매력적이고 위트 있는 한 줄 평",
    "personality_keywords": ["재치단어1", "재치단어2", "재치단어3"],
    "vitality_analysis": "에너지 수준, 선호하는 산책 스타일, 호기심, 선천적 건강 체질 등에 관한 프리미엄 분석글 (반드시 150자 이상)",
    "social_analysis": "사회성, 피아식별, 스킨십 선호 등에 관한 꼼꼼한 분석글 (반드시 150자 이상)",
    "treat_luck": "강아지의 간식 취향, 식탐, 식복에 대한 재미있는 풀이 (반드시 150자 이상)",
    "care_tips": "보호자님이 {josa_name}와 교감하기 위한 구체적인 케어 솔루션과 꿀팁 (반드시 150자 이상)"
}}
"""
    try:
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                response_mime_type="application/json"
            )
        )
        data = json.loads(response.text)
        return dict(data)
    except Exception as e:
        print("Gemini Personality Generation Error:", e)
        # Fallback dummy data
        return {
            "personality_summary": f"알 수 없는 매력을 지닌 신비로운 댕댕이, {dog_name}!",
            "personality_keywords": ["신비로움", "매력만점", "독특함"],
            "vitality_analysis": "현재 데이터를 불러오는 데 실패했어요. 평소의 루틴대로 즐겁게 산책해 주세요!",
            "social_analysis": "세상 모든 친구들과 천천히 알아가는 시간이 필요할지 몰라요.",
            "treat_luck": "보호자님의 사랑이 담긴 간식이라면 뭐든 좋아할 거예요.",
            "care_tips": "가장 중요한 건 보호자님의 여유와 사랑이랍니다."
        }

def generate_daily_luck(dog_name, main_element, today_date_str):
    """
    오늘의 산책운을 생성합니다.
    """
    model = _get_model()
    
    prompt = f"""
당신은 다정하고 통찰력 있는 반려견 전용 사주 전문가입니다.
오늘은 {today_date_str} 이며, 강아지 이름은 '{dog_name}'(본질 오행: {main_element})입니다.
이 강아지의 오늘 하루 '산책운'을 매우 다정하고 친절한 말투로(보호자님에게 말하듯) 점쳐주세요.

JSON 응답을 생성할 때, 문단 구분을 위해 반드시 문자열 안에 이스케이프된 "\\n\\n" 을 사용해 주세요.

{{
    "luck_score": (1부터 100 사이의 정수),
    "message": "오늘 산책에서 특히 주의할 점이나 기대되는 점을 다정하게 어드바이스 해주세요. (최소 3문장 이상, \\n\\n 활용, **이모지 사용 절대 금지**, 쉼표 남발 금지)",
    "lucky_color": "오늘의 럭키스웨그 컬러 (예: 쨍한 노란색, 사랑스러운 핑크 등)",
    "lucky_direction": "오늘의 발걸음 행운 방향 (예: 북적이는 남쪽, 여유로운 동쪽 등)"
}}
"""
    try:
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                response_mime_type="application/json"
            )
        )
        data = json.loads(response.text)
        return dict(data)
    except Exception as e:
        print("Gemini Daily Luck Generation Error:", e)
        josa_name = _get_josa_name(dog_name)
        return {
            "luck_score": 85,
            "message": f"오늘은 {josa_name}와 동네 한 바퀴만 돌아도 기분 좋은 에너지를 얻을 수 있을 거예요! 산책 렛츠고! 🐾",
            "lucky_color": "초록색",
            "lucky_direction": "어디든"
        }
def generate_compatibility(dog_element, relationship_type, version="A"):
    """
    강아지 오행과 보호자 오행 사이의 십성 관계를 분석하여 궁합 결과를 생성합니다.
    [강아지이름], [보호자이름] 플레이스홀더를 사용하여 나중에 치환합니다.
    """
    model = _get_model()

    RELATIONSHIP_DESCRIPTIONS = {
        '비겁': "강아지와 보호자가 같은 오행 에너지를 공유하는 비겁(比劫) 관계입니다. 서로 동질감을 느끼며 공명하지만, 때로는 비슷한 고집으로 부딪히기도 해요.",
        '인성': "보호자의 오행 에너지가 강아지를 生해주는 인성(印星) 관계입니다. 보호자가 강아지에게 든든한 울타리와 헌신적인 사랑을 쏟아주는 이상적인 보호자-아이 관계예요.",
        '식상': "강아지의 오행 에너지가 보호자를 生해주는 식상(食傷) 관계입니다. 강아지가 보호자에게 활력과 기쁨을 선물하는, 보호자에게 에너지를 주는 특별한 존재예요.",
        '재성': "강아지의 오행 에너지가 보호자를 克하는 재성(財星) 관계입니다. 강아지가 보호자의 삶을 이끌고 변화를 주는 당당하고 개성 넘치는 관계예요.",
        '관성': "보호자의 오행 에너지가 강아지를 克하는 관성(官星) 관계입니다. 보호자가 자연스럽게 리더십을 발휘하고 강아지가 보호자를 따르는 안정적인 주종 관계예요.",
    }

    rel_desc = RELATIONSHIP_DESCRIPTIONS.get(relationship_type, "")
    version_guide = {
        "A": "따뜻하고 감성적인 스토리텔링 방식으로",
        "B": "재치 있고 유머러스한 방식으로",
    }.get(version, "다정하게")

    prompt = f"""
당신은 다정하고 통찰력 있는 반려견 전용 사주명리학 전문가입니다.
이번에는 강아지와 보호자의 '댕궁합'을 분석합니다.

[분석 대상]
- 강아지 본질 오행: {dog_element}
- 십성 관계 유형: {relationship_type}
- 관계 설명: {rel_desc}

[작성 지침]
1. {version_guide} 작성해주세요. (버전 {version})
2. '보호자님'과 '[강아지이름]'이라는 표현을 자연스럽게 활용하세요.
3. '[강아지이름]', '[보호자이름]' 플레이스홀더를 반드시 사용하세요 (실제 이름 대신).
4. 명리학 용어(상생, 상극, 인성, 관성 등)를 일반인이 이해하기 쉽게 자연스럽게 녹여주세요.
5. description은 반드시 200자 이상, advice는 반드시 150자 이상 풍부하게 작성하세요.
6. 줄바꿈은 반드시 \"\\n\\n\" 이스케이프 문자로 표현하여 문단을 명확히 나누고 가독성을 높여주세요.
7. 강조: 핵심적인 특성이나 조언은 **굵게** 표시해 주세요.
8. 한자 병기: 명리학 용어(비겁, 인성, 식상, 재성, 관성 등)를 사용할 때는 반드시 한자를 병기하세요. (예: 비겁(比劫), 인성(印星), 식상(食傷), 재성(財星), 관성(官星))
9. 이모지 활용: 모든 항목(description, advice)에서 **이모지 사용을 절대 금지**합니다. 텍스트로만 명확하고 따뜻하게 전달하세요.
10. 가독성: 쉼표(,)를 너무 자주 사용하지 말고, 문장을 간결하게 끊어서 작성해 주세요.
11. score는 십성 관계의 궁합 점수를 0~100으로 표현하세요.
   - 비겁: 70~80, 인성: 85~95, 식상: 80~90, 재성: 65~75, 관성: 75~85

반드시 아래 JSON 형식으로만 반환하세요.

{{
    "score": (0~100 사이 정수),
    "title": "[강아지이름]과 [보호자이름]의 관계를 한 줄로 표현한 멋진 궁합 타이틀 (20자 이내)",
    "description": "강아지와 보호자의 십성 관계를 따뜻하고 재치 있게 설명하는 글 (반드시 200자 이상, 2~3문장마다 \\n\\n 활용)",
    "advice": "이 궁합 관계에서 [보호자이름]이 [강아지이름]과 더 깊이 교감하기 위한 구체적 애정 어드바이스 (반드시 150자 이상, 2~3문장마다 \\n\\n 활용)"
}}
"""
    try:
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                response_mime_type="application/json"
            )
        )
        data = json.loads(response.text)
        return dict(data)
    except Exception as e:
        print("Gemini Compatibility Generation Error:", e)
        return {
            "score": 75,
            "title": "[강아지이름]과 [보호자이름]의 특별한 인연",
            "description": "사주 궁합 데이터를 불러오는 데 실패했어요. 하지만 확실한 건 [강아지이름]과 [보호자이름]은 분명 특별한 인연으로 만난 사이라는 것이에요! 💖",
            "advice": "어떤 궁합이든 가장 중요한 건 매일의 작은 교감이에요. 오늘 [강아지이름]이에게 특별한 간식 하나를 선물해보세요! 🐾"
        }
def generate_daily_luck_template(dog_element, relationship_type, version="A"):
    """
    강아지 오행과 오늘의 일진(기운) 사이의 십성 관계에 따른 산책운 템플릿을 생성합니다.
    버전(A/B/C)에 따라 톤앤매너를 다르게 가져갑니다.
    """
    model = _get_model()

    RELATIONSHIP_CONTEXT = {
        '비겁': "강아지와 오늘 하루의 기운이 동일한 '동료'의 날입니다. 자신감이 넘치고 사교성이 좋아지는 기운입니다.",
        '인성': "오늘의 기운이 강아지를 포근하게 감싸고 도와주는 '어머니'와 같은 날입니다. 정서적 안정감이 높고 사랑받는 기운입니다.",
        '식상': "강아지의 에너지가 밖으로 분출되는 '활동'의 날입니다. 호기심이 왕성해지고 에너지를 발산하고 싶어 하는 기운입니다.",
        '재성': "강아지가 주변 환경을 주도하고 탐험하는 '성취'의 날입니다. 목표 의식이 생기고 활발하게 움직이는 기운입니다.",
        '관성': "강아지가 주변을 의식하고 조심스럽게 행동하는 '규칙'의 날입니다. 차분해지고 보호자의 리드를 잘 따르는 기운입니다.",
    }

    VERSION_GUIDE = {
        "A": "보호자님에게 다정하고 감성적으로 이야기하는 '따뜻한 공감 스토리텔링' 스타일",
        "B": "일반적인 정통 사주 명리학 앱처럼 진지하고 담백하면서도 명확하게 핵심을 짚어주는 운세 풀이 스타일 (단, 분량은 다른 스타일처럼 상세하고 길게 유지)",
        "C": "차분하고 논리적이며 명리학적 근거를 부드럽게 곁들인 '신뢰감 있는 전문가' 스타일",
    }

    context = RELATIONSHIP_CONTEXT.get(relationship_type, "")
    style = VERSION_GUIDE.get(version, "다정한 스타일")

    prompt = f"""
당신은 다정하고 통찰력 있는 반려견 전용 사주명리학 전문가입니다.
강아지의 본질 오행이 '{dog_element}'인 아이에게, 오늘의 기운이 '{relationship_type}'로 작용하는 날의 '산책운' 템플릿(버전 {version})을 작성해 주세요.

[작성 지침]
1. 강아지 이름 대신 반드시 '[강아지이름]'이라는 플레이스홀더를 사용하세요.
2. {style}로 작성해 주세요.
3. '{relationship_type}' 관계의 특성({context})을 산책 상황(다른 강아지와의 만남, 냄새 맡기, 활동량 등)에 녹여내어 아주 구체적으로 작성하세요.
4. message는 반드시 200자 이상 풍부하게 작성하고, 중요 문구는 **굵게** 표시하세요.
5. 줄바꿈은 반드시 "\\n\\n" 이스케이프 문자를 사용하여 문단을 시원하게 나누어 주세요.
7. 한자 병기: 명리학 용어(비겁, 인성, 식상, 재성, 관성 등)를 사용할 때는 반드시 한자를 병기하세요. (예: 비겁(比劫), 인성(印星), 식상(食傷), 재성(財星), 관성(官星))

반드시 아래 JSON 형식으로만 반환하세요:
{{
    "message": "오늘의 산책 조언 (200자 이상, 2~3문장마다 \\n\\n 활용, **이모지 사용 절대 금지**, 쉼표 남발 금지)",
    "lucky_color": "행운의 색상",
    "lucky_direction": "행운의 방향"
}}
"""
    try:
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                response_mime_type="application/json"
            )
        )
        data = json.loads(response.text)
        return dict(data)
    except Exception as e:
        print(f"Gemini Daily Luck Template Gen Error (Ver {version}):", e)
        return {
            "message": f"오늘은 [강아지이름]이가 편안하게 산책을 즐기기 좋은 날이에요! **평소에 좋아하던 코스**로 여유롭게 다녀와 보세요. 🐾",
            "lucky_color": "편안한 아이보리",
            "lucky_direction": "익숙한 동네 한 바퀴"
        }
