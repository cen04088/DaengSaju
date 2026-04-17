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

def generate_personality(dog_name, main_element, element_dist, saju_text="알 수 없음"):
    """
    사주의 오행과 원국을 바탕으로 강아지의 성격과 궁합 등을 분석합니다.
    사용자가 제시한 따뜻하고 친근하며('보호자님~'), 이모지를 적극 활용하는 포춘텔링 톤앤매너를 반영합니다.
    """
    model = _get_model()
    
    prompt = f"""
당신은 다정하고 통찰력 있는 반려견 전용 사주명리학 전문가이자 최고의 반려견 스토리텔러입니다.
강아지의 이름은 '{dog_name}'이며, 일간(타고난 본질) 오행은 '{main_element}', 
전체 오행의 구성 비율은 다음과 같습니다: {element_dist}.
(참고 사주 원국: {saju_text})

이제 보호자님에게 직접 따뜻하고 세심하게 말하는 듯한 말투(예: "보호자님! {dog_name}이는 정말 ~한 아이네요!", "~하는 경향이 깊어요 😊")로 다음 항목들을 아주 상세하고 풍부하게 분석해 주세요. 

[중요 작성 지침]
1. 분량: 각 영역(간식운, 에너지, 사회성, 케어팁)마다 무조건 "최소 150자에서 250자 사이"로 매우 길고 디테일하게 작성해야 합니다. 절대 1~2문장으로 끝내지 마세요.
2. 구체성: 두루뭉술한 설명 대신, "예를 들어 산책하다 낯선 강아지를 만났을 때", "간식 봉투 소리를 들었을 때" 등 눈앞에 그려지는 생생한 상황극이나 예시를 2개 이상 꼭 포함하세요.
3. 가독성: 글이 촘촘해 보이지 않도록 문장 성격이 바뀔 때 적절히 줄바꿈을 넣어야 하는데, 반드시 문자열 내부에 이스케이프된 "\\n" 형태로 작성해주세요. (실제 엔터를 치지 마세요)
4. 분위기: 다채로운 이모지(🐶, 💖, 🍗, 🏃‍♂️ 등)를 풍부하게 섞어 프리미엄 감성 리포트 느낌을 내주세요.

반드시 아래에 정의된 Key를 가진 완벽하고 유효한(Valid) JSON 객체로반환하세요.

{{
    "personality_summary": "{dog_name}이의 성격을 보여주는 아주 매력적이고 위트 있는 한 줄 평",
    "personality_keywords": ["재치단어1", "재치단어2", "재치단어3"],
    "vitality_analysis": "에너지 수준, 선호하는 산책 스타일, 호기심, 선천적 건강 체질 등에 관한 프리미엄 분석글 (반드시 150자 이상)",
    "social_analysis": "사회성, 피아식별, 스킨십 선호 등에 관한 꼼꼼한 분석글 (반드시 150자 이상)",
    "treat_luck": "강아지의 간식 취향, 식탐, 식복에 대한 재미있는 풀이 (반드시 150자 이상)",
    "care_tips": "보호자님이 {dog_name}이와 교감하기 위한 구체적인 케어 솔루션과 꿀팁 (반드시 150자 이상)"
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

JSON 응답을 생성할 때, 텍스트 내에서 줄바꿈이 필요하다면 반드시 문자열 안에 이스케이프된 "\\n" 을 사용해 주세요.

{{
    "luck_score": (1부터 100 사이의 정수),
    "message": "오늘 산책에서 특히 주의할 점이나 기대되는 점, 강아지의 기분 상태 예측 등 다정하고 세심한 어드바이스 (최소 3문장 이상, \\n 및 이모지 적극 활용)",
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
        return {
            "luck_score": 85,
            "message": f"오늘은 {dog_name}이와 동네 한 바퀴만 돌아도 기분 좋은 에너지를 얻을 수 있을 거예요! 산책 렛츠고! 🐾",
            "lucky_color": "초록색",
            "lucky_direction": "어디든"
        }
