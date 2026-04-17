from datetime import date
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .models import User, Dog, SajuBasics, AIInterpretation, DailyWalkingLuck, ArchetypeSaju, DailyElementLuck, Compatibility, CompatibilityArchetype
from .serializers import DogSerializer, SajuBasicsSerializer, AIInterpretationSerializer, DailyWalkingLuckSerializer
from .services.manseryeok import get_saju_for_dog, get_secondary_influence_text, get_relationship_type

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
        
        # SajuBasics 레코드 생성 (3단계: relationship_type, secondary_element 포함)
        saju_basics = SajuBasics.objects.create(
            dog=dog,
            year_pillar=saju_data['year_pillar'],
            month_pillar=saju_data['month_pillar'],
            day_pillar=saju_data['day_pillar'],
            hour_pillar=saju_data['hour_pillar'],
            main_element=saju_data['main_element'],
            element_distribution=saju_data['element_distribution'],
            relationship_type=saju_data.get('relationship_type', '비겁'),
            secondary_element=saju_data.get('secondary_element', ''),
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

        # 3단계: 십성(十星) 기반 ArchetypeSaju 맵핑
        primary = saju.main_element
        relationship_type = saju.relationship_type or '비겁'
        secondary_element = saju.secondary_element or primary

        # 버전 선택 (강아지 id 기반으로 일정하게)
        version_idx = dog.id % 3
        versions = ['A', 'B', 'C']
        selected_version = versions[version_idx]

        archetype = ArchetypeSaju.objects.filter(
            primary_element=primary,
            relationship_type=relationship_type,
            version=selected_version
        ).first()
        if not archetype:
            archetype = ArchetypeSaju.objects.filter(
                primary_element=primary,
                relationship_type=relationship_type
            ).first()

        if not archetype:
            return Response({"error": "사전 생성된 사주 프로필을 찾을 수 없습니다. (pregenerate_saju 명령어 실행 필요)"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        def replace_name(text):
            if not text: return ""
            return text.replace("[강아지이름]", dog.name)

        keywords = []
        if isinstance(archetype.personality_keywords, list):
            keywords = [replace_name(k) for k in archetype.personality_keywords]

        # 2위 오행 보조 텍스트(수식 기반, AI 호출 없음)
        secondary_text = get_secondary_influence_text(primary, secondary_element)
        care_tips_with_secondary = replace_name(archetype.care_tips)
        if secondary_text:
            care_tips_with_secondary += f"\n\n\U0001f4a1 [추가 사주 분석] {secondary_text}"

        try:
            interpretation = AIInterpretation.objects.create(
                dog=dog,
                personality_summary=replace_name(archetype.personality_summary),
                personality_keywords=keywords,
                vitality_analysis=replace_name(archetype.vitality_analysis),
                social_analysis=replace_name(archetype.social_analysis),
                treat_luck=replace_name(archetype.treat_luck),
                care_tips=care_tips_with_secondary  # 2위 오행 보조 내용 포함
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


class CompatibilityView(APIView):
    """
    댓궁합 API - 근석에 따라외 CompatibilityArchetype에서 결과를 즉시 반환
    POST /api/saju/dogs/<dog_id>/compatibility/
    """
    authentication_classes = []

    def post(self, request, dog_id):
        dog = get_object_or_404(Dog, id=dog_id)
        owner_birth_date_str = request.data.get('owner_birth_date')
        owner_birth_time_str = request.data.get('owner_birth_time')
        owner_name = request.data.get('owner_name', '보호자님')

        if not owner_birth_date_str:
            return Response({"error": "보호자 생년월일을 입력해주세요."}, status=status.HTTP_400_BAD_REQUEST)

        # 1. 캐시 확인: 이미 저장된 결과가 있다면 즉시 반환
        cached = Compatibility.objects.filter(dog=dog, user=dog.user).first()
        if cached:
            return Response({
                'dog_element': cached.description.split('|')[0] if '|' in cached.description else '',
                'owner_element': cached.description.split('|')[1] if '|' in cached.description else '',
                'relationship_type': cached.description.split('|')[2] if '|' in cached.description else '',
                'score': cached.score,
                'title': cached.title,
                'description': cached.description.split('|', 3)[-1] if '|' in cached.description else cached.description,
                'advice': cached.advice if hasattr(cached, 'advice') else '',
            }, status=status.HTTP_200_OK)

        # 2. 강아지 사주 확인 (없으면 자동 계산)
        if not hasattr(dog, 'saju_basics'):
            if not dog.birth_date:
                return Response({"error": "강아지 생년월일 정보가 없어 사주를 계산할 수 없습니다."}, status=status.HTTP_400_BAD_REQUEST)
            saju_data = get_saju_for_dog(dog.birth_date, dog.birth_time)
            SajuBasics.objects.create(
                dog=dog,
                year_pillar=saju_data['year_pillar'], month_pillar=saju_data['month_pillar'],
                day_pillar=saju_data['day_pillar'], hour_pillar=saju_data['hour_pillar'],
                main_element=saju_data['main_element'], element_distribution=saju_data['element_distribution'],
                relationship_type=saju_data.get('relationship_type', '비겁'),
                secondary_element=saju_data.get('secondary_element', ''),
            )
            dog.refresh_from_db()

        dog_element = dog.saju_basics.main_element

        # 3. 보호자 사주 계산
        from datetime import datetime
        try:
            owner_birth_date = datetime.strptime(owner_birth_date_str, '%Y-%m-%d').date()
        except ValueError:
            return Response({"error": "날짜 형식이 잘못되었습니다. (YYYY-MM-DD)"}, status=status.HTTP_400_BAD_REQUEST)

        owner_birth_time = None
        if owner_birth_time_str:
            try:
                owner_birth_time = datetime.strptime(owner_birth_time_str, '%H:%M').time()
            except ValueError:
                pass

        owner_saju = get_saju_for_dog(owner_birth_date, owner_birth_time)
        owner_element = owner_saju['main_element']

        # 4. 십성 관계 계산 (강아지 관점에서 보호자를 바라봄)
        relationship_type = get_relationship_type(dog_element, owner_element)

        # 5. 버전 결정
        version = 'A' if dog.id % 2 == 0 else 'B'

        # 6. CompatibilityArchetype 조회
        archetype = CompatibilityArchetype.objects.filter(
            dog_element=dog_element,
            relationship_type=relationship_type,
            version=version
        ).first()
        if not archetype:
            archetype = CompatibilityArchetype.objects.filter(
                dog_element=dog_element,
                relationship_type=relationship_type
            ).first()

        if not archetype:
            return Response(
                {"error": "사전 생성된 궁합 프로필을 찾을 수 없습니다. (pregenerate_compatibility 명령어 실행 필요)"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # 7. 플레이스홀더 치환
        def replace_ph(text):
            if not text: return ""
            return text.replace("[강아지이름]", dog.name).replace("[보호자이름]", owner_name)

        result_title = replace_ph(archetype.title)
        result_description = replace_ph(archetype.description)
        result_advice = replace_ph(archetype.advice)

        # 8. Compatibility 모델에 캐시 저장
        # description에 메타데이터를 |로 구분하여 저장(커스텀 필드 확장 없이)
        meta_prefix = f"{dog_element}|{owner_element}|{relationship_type}|"
        try:
            Compatibility.objects.update_or_create(
                dog=dog, user=dog.user,
                defaults={
                    'score': archetype.score,
                    'title': result_title,
                    'description': meta_prefix + result_description,
                }
            )
        except Exception as e:
            print(f"Compatibility 캐시 저장 오류: {e}")

        return Response({
            'dog_element': dog_element,
            'owner_element': owner_element,
            'relationship_type': relationship_type,
            'score': archetype.score,
            'title': result_title,
            'description': result_description,
            'advice': result_advice,
        }, status=status.HTTP_200_OK)
