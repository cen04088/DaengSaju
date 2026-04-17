from datetime import date
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .models import User, Dog, SajuBasics, AIInterpretation, DailyWalkingLuck, ArchetypeSaju, DailyElementLuck
from .serializers import DogSerializer, SajuBasicsSerializer, AIInterpretationSerializer, DailyWalkingLuckSerializer
from .services.manseryeok import get_saju_for_dog

class DogRegisterView(APIView):
    """
    Toss 웹뷰에서 보호자와 강아지 정보를 최초 등록하는 API
    """
    authentication_classes = []

    def post(self, request):
        social_id = request.data.get('social_id')
        nickname = request.data.get('nickname')
        dog_data = request.data.get('dog') # name, birth_date, birth_time, is_lunar, gender, is_estimated_birth

        if not social_id or not nickname or not dog_data:
            return Response({"error": "Missing required fields"}, status=status.HTTP_400_BAD_REQUEST)

        # 1. 보호자 조회 또는 생성
        user, created = User.objects.get_or_create(
            social_id=social_id,
            defaults={'username': social_id, 'nickname': nickname}
        )

        # 2. 강아지 데이터 직렬화 및 저장
        serializer = DogSerializer(data=dog_data)
        if serializer.is_valid():
            dog = serializer.save(user=user)
            return Response({
                "message": "등록 완료",
                "user_nickname": user.nickname,
                "dog_id": dog.id
            }, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class SajuBasicsView(APIView):
    """
    강아지의 사주 원국 정보 조회.
    데이터가 없으면 manseryeok 모듈을 이용해 사주를 계산하고 저장한 후 반환합니다.
    """
    def get(self, request, dog_id):
        dog = get_object_or_404(Dog, id=dog_id)
        
        # 캐싱된 사주 원국이 있는지 확인
        if hasattr(dog, 'saju_basics'):
            serializer = SajuBasicsSerializer(dog.saju_basics)
            return Response(serializer.data, status=status.HTTP_200_OK)
        
        # 없으면 계산 진행
        if not dog.birth_date:
            return Response({"error": "강아지의 생일 정보가 없어 사주를 계산할 수 없습니다."}, status=status.HTTP_400_BAD_REQUEST)
        
        saju_data = get_saju_for_dog(dog.birth_date, dog.birth_time)
        
        # SajuBasics 레코드 생성
        saju_basics = SajuBasics.objects.create(
            dog=dog,
            year_pillar=saju_data['year_pillar'],
            month_pillar=saju_data['month_pillar'],
            day_pillar=saju_data['day_pillar'],
            hour_pillar=saju_data['hour_pillar'],
            main_element=saju_data['main_element'],
            element_distribution=saju_data['element_distribution']
        )
        
        serializer = SajuBasicsSerializer(saju_basics)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class AIInterpretationView(APIView):
    """
    강아지의 AI 성격 분석 정보 조회.
    데이터가 없으면 Gemini API를 호출하여 분석 결과를 생성하고 저장 후 반환합니다.
    """
    def get(self, request, dog_id):
        dog = get_object_or_404(Dog, id=dog_id)

        # 1. 캐싱 검사
        if hasattr(dog, 'ai_interpretation'):
            serializer = AIInterpretationSerializer(dog.ai_interpretation)
            return Response(serializer.data, status=status.HTTP_200_OK)
        
        # 2. 사주 데이터 필수 검사 (없는 경우 사주 기초를 먼저 생성하도록 요구하거나 뷰에서 처리)
        if not hasattr(dog, 'saju_basics'):
            return Response({"error": "먼저 사주 원국(/basics/)을 생성해야 합니다."}, status=status.HTTP_400_BAD_REQUEST)
        
        saju = dog.saju_basics
        saju_text = f"{saju.year_pillar}년 {saju.month_pillar}월 {saju.day_pillar}일"
        if saju.hour_pillar:
            saju_text += f" {saju.hour_pillar}시"

        # 3. 사전 생성된 ArchetypeSaju 맵핑
        primary = saju.main_element
        dist = saju.element_distribution
        if isinstance(dist, dict) and dist:
            strongest = max(dist, key=dist.get)
        else:
            strongest = primary

        # 버전 선택 (강아지 id 기반으로 일정하게)
        version_idx = dog.id % 3
        versions = ['A', 'B', 'C']
        selected_version = versions[version_idx]

        archetype = ArchetypeSaju.objects.filter(primary_element=primary, strongest_element=strongest, version=selected_version).first()
        if not archetype:
            archetype = ArchetypeSaju.objects.filter(primary_element=primary, strongest_element=strongest).first()
        
        if not archetype:
            return Response({"error": "사전 생성된 사주 프로필을 찾을 수 없습니다. (pregenerate_saju 명령어 실행 필요)"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        def replace_name(text):
            if not text: return ""
            return text.replace("[강아지이름]", dog.name)

        keywords = []
        if isinstance(archetype.personality_keywords, list):
            keywords = [replace_name(k) for k in archetype.personality_keywords]

        try:
            interpretation = AIInterpretation.objects.create(
                dog=dog,
                personality_summary=replace_name(archetype.personality_summary),
                personality_keywords=keywords,
                vitality_analysis=replace_name(archetype.vitality_analysis),
                social_analysis=replace_name(archetype.social_analysis),
                treat_luck=replace_name(archetype.treat_luck),
                care_tips=replace_name(archetype.care_tips)
            )
        except Exception as e:
            return Response({"error": f"DB 저장 중 오류 발생: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        serializer = AIInterpretationSerializer(interpretation)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class DailyWalkingLuckView(APIView):
    """
    강아지의 오늘 산책운 조회 (Lazy evaluation).
    오늘 날짜 기준 데이터가 없으면 Gemini API를 호출하여 즉석에서 생성합니다.
    """
    def get(self, request, dog_id):
        dog = get_object_or_404(Dog, id=dog_id)
        today = date.today()

        # 1. 오늘 날짜의 산책운이 있는지 확인
        luck = DailyWalkingLuck.objects.filter(dog=dog, date=today).first()
        if luck:
            serializer = DailyWalkingLuckSerializer(luck)
            return Response(serializer.data, status=status.HTTP_200_OK)
        
        # 2. 사주 정보 확인 (본질 오행 등 필요)
        main_element = "알수없음"
        if hasattr(dog, 'saju_basics'):
            main_element = dog.saju_basics.main_element
        
        today_str = today.strftime("%Y년 %m월 %d일")

        # 3. 오늘의 사전 생성된 오행별 운세 조회
        daily_luck_record = DailyElementLuck.objects.filter(date=today, element=main_element).first()
        
        if not daily_luck_record:
            # 크론 스케줄러 누락 등의 fallback
            luck_data = {
                'luck_score': 80,
                'message': f"오늘은 {dog.name}이와 동네 한 바퀴 도는 것만으로도 행복해지는 날이에요!",
                'lucky_color': "보라색",
                'lucky_direction': "어디든"
            }
        else:
            luck_data = {
                'luck_score': daily_luck_record.luck_score,
                'message': daily_luck_record.message.replace("[강아지이름]", dog.name),
                'lucky_color': daily_luck_record.lucky_color,
                'lucky_direction': daily_luck_record.lucky_direction
            }

        luck = DailyWalkingLuck.objects.create(
            dog=dog,
            date=today,
            luck_score=luck_data.get('luck_score'),
            message=luck_data.get('message'),
            lucky_color=luck_data.get('lucky_color'),
            lucky_direction=luck_data.get('lucky_direction')
        )

        serializer = DailyWalkingLuckSerializer(luck)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
