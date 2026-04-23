from datetime import date, datetime
import re

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (
    AIInterpretation,
    ArchetypeSaju,
    Attendance,
    Compatibility,
    CompatibilityArchetype,
    DailyElementLuck,
    DailyWalkingLuck,
    Dog,
    SajuBasics,
    User,
)
from .serializers import (
    AIInterpretationSerializer,
    DailyWalkingLuckSerializer,
    DogSerializer,
    SajuBasicsSerializer,
)
from .services.manseryeok import (
    add_hanja_to_terms,
    get_relationship_type,
    get_saju_for_dog,
    get_secondary_influence_text,
    smart_replace,
)


def resolve_social_id(request):
    return (
        request.headers.get('X-Toss-User-Key')
        or request.data.get('social_id')
        or request.query_params.get('social_id')
        or ''
    )


def normalize_owner_honorific_text(text, owner_name):
    if not text or not owner_name or not owner_name.endswith('님'):
        return text

    normalized = text
    special_replacements = {
        f'{owner_name}이의': f'{owner_name}의',
        f'{owner_name}가의': f'{owner_name}의',
        f'{owner_name}이께': f'{owner_name}께',
        f'{owner_name}가께': f'{owner_name}께',
        f'{owner_name}이에게': f'{owner_name}에게',
        f'{owner_name}가에게': f'{owner_name}에게',
    }
    particles = ['이', '가', '은', '는', '을', '를', '과', '와', '으로', '로', '의']

    for source, target in special_replacements.items():
        normalized = normalized.replace(source, target)

    for particle in particles:
        normalized = normalized.replace(f'{owner_name}{particle}님{particle}', f'{owner_name}{particle}')
        normalized = normalized.replace(f'{owner_name}{particle}님', f'{owner_name}{particle}')
        normalized = normalized.replace(f'{owner_name}{particle}{particle}', f'{owner_name}{particle}')

    normalized = normalized.replace(f'{owner_name}님', owner_name)
    normalized = re.sub(r'(님){2,}', '님', normalized)
    return normalized


def normalize_compatibility_owner_text(text, owner_name=''):
    if not text:
        return text

    normalized = text
    display_owner_name = '보호자님'
    placeholder_variants = ['[보호자이름]', '[보호자 이름]', '[보호자명]']

    for placeholder in placeholder_variants:
        normalized = normalized.replace(placeholder, display_owner_name)

    if owner_name:
        normalized = normalized.replace(owner_name, display_owner_name)

    generic_particle_fixes = {
        '보호자님가': '보호자님이',
        '보호자님는': '보호자님은',
        '보호자님를': '보호자님을',
        '보호자님와': '보호자님과',
        '보호자님로': '보호자님으로',
    }
    for source, target in generic_particle_fixes.items():
        normalized = normalized.replace(source, target)

    stacked_particle_fixes = {
        '보호자님이은': '보호자님은',
        '보호자님이는': '보호자님은',
        '보호자님이을': '보호자님을',
        '보호자님이를': '보호자님을',
        '보호자님이와': '보호자님과',
        '보호자님이과': '보호자님과',
        '보호자님이의': '보호자님의',
        '보호자님이께': '보호자님께',
        '보호자님이에게': '보호자님에게',
        '보호자님이으로': '보호자님으로',
        '보호자님이로': '보호자님으로',
        '보호자님가은': '보호자님은',
        '보호자님가는': '보호자님은',
        '보호자님가을': '보호자님을',
        '보호자님가를': '보호자님을',
        '보호자님가와': '보호자님과',
        '보호자님가과': '보호자님과',
        '보호자님가의': '보호자님의',
        '보호자님가께': '보호자님께',
        '보호자님가에게': '보호자님에게',
        '보호자님가으로': '보호자님으로',
        '보호자님가로': '보호자님으로',
        '보호자님은은': '보호자님은',
        '보호자님는는': '보호자님은',
        '보호자님을을': '보호자님을',
        '보호자님를를': '보호자님을',
        '보호자님과과': '보호자님과',
        '보호자님와와': '보호자님과',
        '보호자님의의': '보호자님의',
    }
    for source, target in stacked_particle_fixes.items():
        normalized = normalized.replace(source, target)

    return normalize_owner_honorific_text(normalized, display_owner_name)


class DogRegisterView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        social_id = resolve_social_id(request)
        nickname = request.data.get('nickname')
        dog_data = request.data.get('dog')

        if not social_id or not nickname or not dog_data:
            return Response({"error": "Missing required fields"}, status=status.HTTP_400_BAD_REQUEST)

        user, _ = User.objects.get_or_create(
            social_id=social_id,
            defaults={'username': social_id, 'nickname': nickname}
        )
        if user.nickname != nickname:
            user.nickname = nickname
            user.save(update_fields=['nickname'])

        existing_dog = Dog.objects.filter(
            user=user,
            name=dog_data.get('name'),
            birth_date=dog_data.get('birth_date'),
            birth_time=dog_data.get('birth_time') or None,
            is_lunar=dog_data.get('is_lunar', False),
            gender=dog_data.get('gender'),
            is_estimated_birth=dog_data.get('is_estimated_birth', False),
        ).only('id').first()
        if existing_dog:
            return Response(
                {
                    "message": "등록 완료",
                    "user_nickname": user.nickname,
                    "dog_id": existing_dog.id,
                },
                status=status.HTTP_200_OK,
            )

        serializer = DogSerializer(data=dog_data)
        if serializer.is_valid():
            dog = serializer.save(user=user)
            return Response(
                {
                    "message": "등록 완료",
                    "user_nickname": user.nickname,
                    "dog_id": dog.id,
                },
                status=status.HTTP_201_CREATED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class SajuBasicsView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request, dog_id):
        dog = get_object_or_404(Dog.objects.select_related('saju_basics'), id=dog_id)

        if hasattr(dog, 'saju_basics'):
            serializer = SajuBasicsSerializer(dog.saju_basics)
            return Response(serializer.data, status=status.HTTP_200_OK)

        if not dog.birth_date:
            return Response({"error": "강아지의 생일 정보가 없어 사주를 계산할 수 없습니다."}, status=status.HTTP_400_BAD_REQUEST)

        saju_data = get_saju_for_dog(dog.birth_date, dog.birth_time)
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
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request, dog_id):
        dog = get_object_or_404(Dog.objects.select_related('saju_basics', 'ai_interpretation'), id=dog_id)

        if hasattr(dog, 'ai_interpretation'):
            serializer = AIInterpretationSerializer(dog.ai_interpretation)
            return Response(serializer.data, status=status.HTTP_200_OK)

        if not hasattr(dog, 'saju_basics'):
            return Response({"error": "먼저 사주 원국(/basics/)을 생성해야 합니다."}, status=status.HTTP_400_BAD_REQUEST)

        saju = dog.saju_basics
        primary = saju.main_element
        relationship_type = saju.relationship_type or '비겁'
        secondary_element = saju.secondary_element or primary

        selected_version = ['A', 'B', 'C'][dog.id % 3]
        archetype = ArchetypeSaju.objects.filter(
            primary_element=primary,
            relationship_type=relationship_type,
            version=selected_version,
        ).first() or ArchetypeSaju.objects.filter(
            primary_element=primary,
            relationship_type=relationship_type,
        ).first()

        if not archetype:
            return Response({"error": "사전 생성된 사주 프로필을 찾을 수 없습니다. (pregenerate_saju 명령어 실행 필요)"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        def replace_name(text):
            return smart_replace(text, dog.name)

        keywords = [replace_name(k) for k in archetype.personality_keywords] if isinstance(archetype.personality_keywords, list) else []
        secondary_text = get_secondary_influence_text(primary, secondary_element)
        care_tips_with_secondary = replace_name(archetype.care_tips)
        if secondary_text:
            care_tips_with_secondary += f"\n\n\U0001f4a1 [추가 사주 분석] {secondary_text}"

        interpretation = AIInterpretation.objects.create(
            dog=dog,
            personality_summary=add_hanja_to_terms(replace_name(archetype.personality_summary)),
            personality_keywords=[add_hanja_to_terms(k) for k in keywords],
            vitality_analysis=add_hanja_to_terms(replace_name(archetype.vitality_analysis)),
            social_analysis=add_hanja_to_terms(replace_name(archetype.social_analysis)),
            treat_luck=add_hanja_to_terms(replace_name(archetype.treat_luck)),
            care_tips=add_hanja_to_terms(care_tips_with_secondary),
        )

        serializer = AIInterpretationSerializer(interpretation)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class DailyWalkingLuckView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request, dog_id):
        dog = get_object_or_404(Dog.objects.select_related('saju_basics'), id=dog_id)
        today = date.today()

        luck = DailyWalkingLuck.objects.filter(dog=dog, date=today).first()
        if luck:
            serializer = DailyWalkingLuckSerializer(luck)
            data = serializer.data
            data['message'] = add_hanja_to_terms(data['message'])
            return Response(data, status=status.HTTP_200_OK)

        main_element = '알수없음'
        relationship_type = '비겁'
        if hasattr(dog, 'saju_basics'):
            main_element = dog.saju_basics.main_element
            relationship_type = dog.saju_basics.relationship_type or '비겁'

        dog_version = ['A', 'B', 'C'][dog.id % 3]
        from .models import DailyLuckArchetype

        archetype = DailyLuckArchetype.objects.filter(
            dog_element=main_element,
            relationship_type=relationship_type,
            version=dog_version,
        ).first() or DailyLuckArchetype.objects.filter(
            dog_element=main_element,
            relationship_type=relationship_type,
        ).first() or DailyLuckArchetype.objects.filter(
            dog_element=main_element,
        ).first()

        if archetype:
            import random

            score_range = {
                '인성': (88, 98),
                '비겁': (82, 95),
                '식상': (78, 92),
                '재성': (72, 88),
                '관성': (60, 78),
            }.get(relationship_type, (70, 90))
            luck_data = {
                'luck_score': random.randint(*score_range),
                'message': smart_replace(archetype.message, dog.name),
                'lucky_color': archetype.lucky_color,
                'lucky_direction': archetype.lucky_direction,
            }
        else:
            daily_luck_record = DailyElementLuck.objects.filter(date=today, element=main_element).first()
            if daily_luck_record:
                luck_data = {
                    'luck_score': daily_luck_record.luck_score,
                    'message': smart_replace(daily_luck_record.message, dog.name),
                    'lucky_color': daily_luck_record.lucky_color,
                    'lucky_direction': daily_luck_record.lucky_direction,
                }
            else:
                luck_data = {
                    'luck_score': 80,
                    'message': smart_replace("오늘은 [강아지이름]이와 동네 한 바퀴 도는 것만으로도 행복해지는 날이에요!", dog.name),
                    'lucky_color': '보라색',
                    'lucky_direction': '어디든',
                }

        luck = DailyWalkingLuck.objects.create(
            dog=dog,
            date=today,
            luck_score=luck_data['luck_score'],
            message=luck_data['message'],
            lucky_color=luck_data['lucky_color'],
            lucky_direction=luck_data['lucky_direction'],
        )
        serializer = DailyWalkingLuckSerializer(luck)
        data = serializer.data
        data['message'] = add_hanja_to_terms(data['message'])
        return Response(data, status=status.HTTP_201_CREATED)


class CompatibilityResultView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request, dog_id):
        dog = get_object_or_404(Dog.objects.select_related('user', 'saju_basics'), id=dog_id)
        owner_birth_date_str = request.data.get('owner_birth_date')
        owner_birth_time_str = request.data.get('owner_birth_time')
        owner_name = request.data.get('owner_name', '')
        display_owner_name = '보호자님'

        if not owner_birth_date_str:
            return Response({"error": "보호자 생년월일을 입력해주세요."}, status=status.HTTP_400_BAD_REQUEST)

        if not hasattr(dog, 'saju_basics'):
            if not dog.birth_date:
                return Response({"error": "강아지 생년월일 정보가 없어 사주를 계산할 수 없습니다."}, status=status.HTTP_400_BAD_REQUEST)
            saju_data = get_saju_for_dog(dog.birth_date, dog.birth_time)
            SajuBasics.objects.create(
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
            dog.refresh_from_db()

        try:
            owner_birth_date = datetime.strptime(owner_birth_date_str, '%Y-%m-%d').date()
        except ValueError:
            return Response({"error": "날짜 형식이 잘못되었습니다. (YYYY-MM-DD)"}, status=status.HTTP_400_BAD_REQUEST)

        owner_birth_time = None
        if owner_birth_time_str:
            try:
                owner_birth_time = datetime.strptime(owner_birth_time_str, '%H:%M').time()
            except ValueError:
                owner_birth_time = None

        dog_element = dog.saju_basics.main_element
        owner_element = get_saju_for_dog(owner_birth_date, owner_birth_time)['main_element']
        relationship_type = get_relationship_type(dog_element, owner_element)
        version = 'A' if dog.id % 2 == 0 else 'B'

        archetype = CompatibilityArchetype.objects.filter(
            dog_element=dog_element,
            relationship_type=relationship_type,
            version=version,
        ).first() or CompatibilityArchetype.objects.filter(
            dog_element=dog_element,
            relationship_type=relationship_type,
        ).first()

        if not archetype:
            return Response(
                {"error": "사전 생성된 궁합 프로필을 찾을 수 없습니다. (pregenerate_compatibility 명령어 실행 필요)"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        result_title = normalize_owner_honorific_text(
            normalize_compatibility_owner_text(
                smart_replace(archetype.title, dog.name, display_owner_name),
                owner_name,
            ),
            display_owner_name,
        )
        result_description = normalize_owner_honorific_text(
            normalize_compatibility_owner_text(
                smart_replace(archetype.description, dog.name, display_owner_name),
                owner_name,
            ),
            display_owner_name,
        )
        result_advice = normalize_owner_honorific_text(
            normalize_compatibility_owner_text(
                smart_replace(archetype.advice, dog.name, display_owner_name),
                owner_name,
            ),
            display_owner_name,
        )

        meta_prefix = f"{dog_element}|{owner_element}|{relationship_type}|"
        Compatibility.objects.update_or_create(
            dog=dog,
            user=dog.user,
            defaults={
                'score': archetype.score,
                'title': result_title,
                'description': meta_prefix + result_description,
            },
        )

        return Response(
            {
                'dog_element': dog_element,
                'owner_element': owner_element,
                'relationship_type': add_hanja_to_terms(relationship_type),
                'score': archetype.score,
                'title': add_hanja_to_terms(result_title),
                'description': add_hanja_to_terms(result_description),
                'advice': add_hanja_to_terms(result_advice),
            },
            status=status.HTTP_200_OK,
        )


class AttendanceView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    MILESTONES = [1, 3, 5, 7, 10, 15, 20]

    def _get_or_create_user(self, social_id):
        user, _ = User.objects.get_or_create(
            social_id=social_id,
            defaults={'username': social_id, 'nickname': 'Toss 사용자'}
        )
        return user

    def get(self, request):
        social_id = resolve_social_id(request)
        if not social_id:
            return Response({'error': 'social_id 파라미터가 필요합니다.'}, status=status.HTTP_400_BAD_REQUEST)

        user = self._get_or_create_user(social_id)
        today = date.today()
        attendance, _ = Attendance.objects.get_or_create(
            user=user,
            year=today.year,
            month=today.month,
            defaults={'attended_days': [], 'streak_count': 0, 'claimed_milestones': []},
        )

        return Response(
            {
                'year': attendance.year,
                'month': attendance.month,
                'attended_days': attendance.attended_days,
                'streak_count': attendance.streak_count,
                'claimed_milestones': attendance.claimed_milestones,
                'already_stamped_today': today.day in attendance.attended_days,
            },
            status=status.HTTP_200_OK,
        )

    def post(self, request):
        social_id = resolve_social_id(request)
        if not social_id:
            return Response({'error': 'social_id가 필요합니다.'}, status=status.HTTP_400_BAD_REQUEST)

        user = self._get_or_create_user(social_id)
        today = date.today()
        attendance, _ = Attendance.objects.get_or_create(
            user=user,
            year=today.year,
            month=today.month,
            defaults={'attended_days': [], 'streak_count': 0, 'claimed_milestones': []},
        )

        if today.day in attendance.attended_days:
            return Response(
                {
                    'stamped': False,
                    'message': '오늘 이미 출석하셨습니다.',
                    'attended_days': attendance.attended_days,
                    'streak_count': attendance.streak_count,
                },
                status=status.HTTP_200_OK,
            )

        new_days = sorted(set(attendance.attended_days + [today.day]))
        new_total = len(new_days)
        if new_total in self.MILESTONES and new_total not in attendance.claimed_milestones:
            new_milestone = new_total
            new_claimed = sorted(set(attendance.claimed_milestones + [new_total]))
        else:
            new_milestone = None
            new_claimed = attendance.claimed_milestones

        attendance.attended_days = new_days
        attendance.streak_count = new_total
        attendance.claimed_milestones = new_claimed
        attendance.save(update_fields=['attended_days', 'streak_count', 'claimed_milestones', 'updated_at'])

        return Response(
            {
                'stamped': True,
                'message': '출석 완료!',
                'attended_days': new_days,
                'streak_count': new_total,
                'claimed_milestones': new_claimed,
                'new_milestone': new_milestone,
            },
            status=status.HTTP_200_OK,
        )
