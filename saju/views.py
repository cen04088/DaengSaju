from datetime import timedelta
import random
import re
import secrets

from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.permissions import AllowAny, BasePermission
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (
    AIInterpretation,
    ArchetypeSaju,
    Attendance,
    Compatibility,
    CompatibilityArchetype,
    DailyLuckArchetype,
    DailyWalkingLuck,
    Dog,
    SajuBasics,
    User,
)
from .serializers import (
    AIInterpretationSerializer,
    DailyWalkingLuckSerializer,
    DogSerializer,
    FriendDogSerializer,
    LUNAR_DATE_ERROR,
    PersonBirthSerializer,
    SajuBasicsSerializer,
)
from .services.manseryeok import (
    InvalidBirthDateError,
    add_hanja_to_terms,
    get_daily_pillar,
    get_relationship_type,
    get_saju_for_dog,
    get_secondary_influence_text,
    smart_replace,
)
from .services.profiles import (
    build_friend_compatibility,
    build_zodiac_match,
    clamp_score,
    get_day_pillar_profile,
    get_zodiac,
    seeded_offset,
)

USER_KEY_HEADER = 'X-Toss-User-Key'
USER_KEY_MAX_LENGTH = 150  # User.username(max 150)에 그대로 저장되므로 같은 한도
DEFAULT_NICKNAME = 'Toss 사용자'
ARCHETYPE_VERSIONS = ['A', 'B', 'C']
MY_DOGS_LIMIT = 10

# 오늘의 기운과 강아지 오행의 관계별 산책 점수 범위
DAILY_SCORE_RANGES = {
    '인성': (88, 98),
    '비겁': (82, 95),
    '식상': (78, 92),
    '재성': (72, 88),
    '관성': (60, 78),
}
DEFAULT_DAILY_MESSAGE = "오늘은 [강아지이름]이와 동네 한 바퀴 도는 것만으로도 행복해지는 날이에요!"


def get_request_user_key(request):
    """토스 미니앱이 헤더로 보내는 사용자 키. body/query 값은 위조가 쉬워 신뢰하지 않습니다."""
    key = (request.headers.get(USER_KEY_HEADER) or '').strip()
    if not key or len(key) > USER_KEY_MAX_LENGTH:
        return ''
    return key


class HasTossUserKey(BasePermission):
    message = '토스 사용자 정보를 확인할 수 없어요. 앱을 다시 열어주세요.'

    def has_permission(self, request, view):
        return bool(get_request_user_key(request))


def first_error_message(errors, default='입력한 정보를 다시 확인해주세요.'):
    """DRF 검증 에러 구조에서 사용자에게 보여줄 첫 메시지를 꺼냅니다."""
    if isinstance(errors, dict):
        values = errors.values()
    elif isinstance(errors, (list, tuple)):
        values = errors
    else:
        return str(errors) if errors else default
    for value in values:
        message = first_error_message(value, None)
        if message:
            return message
    return default


def validation_error_response(errors):
    return Response({'error': first_error_message(errors), 'errors': errors}, status=status.HTTP_400_BAD_REQUEST)


def get_or_create_user(social_id, nickname=None):
    user, _ = User.objects.get_or_create(
        social_id=social_id,
        defaults={'username': social_id, 'nickname': nickname or DEFAULT_NICKNAME},
    )
    if nickname and user.nickname != nickname:
        user.nickname = nickname
        user.save(update_fields=['nickname'])
    return user


def ensure_saju_basics(dog):
    """사주 원국을 한 번만 계산해 저장합니다. 동시 요청이 와도 중복 생성 에러가 나지 않습니다."""
    try:
        return dog.saju_basics
    except SajuBasics.DoesNotExist:
        pass

    saju_data = get_saju_for_dog(dog.birth_date, dog.birth_time, dog.is_lunar, dog.is_leap_month)
    basics, _ = SajuBasics.objects.get_or_create(
        dog=dog,
        defaults={
            'year_pillar': saju_data['year_pillar'],
            'month_pillar': saju_data['month_pillar'],
            'day_pillar': saju_data['day_pillar'],
            'hour_pillar': saju_data['hour_pillar'],
            'main_element': saju_data['main_element'],
            'element_distribution': saju_data['element_distribution'],
            'relationship_type': saju_data.get('relationship_type', '비겁'),
            'secondary_element': saju_data.get('secondary_element', ''),
        },
    )
    dog.saju_basics = basics
    return basics


def clear_dog_results(dog):
    """생일 정보가 바뀐 강아지의 계산 결과 캐시를 지웁니다 (다음 조회 때 다시 계산)."""
    SajuBasics.objects.filter(dog=dog).delete()
    AIInterpretation.objects.filter(dog=dog).delete()
    DailyWalkingLuck.objects.filter(dog=dog).delete()
    Compatibility.objects.filter(dog=dog).delete()


def build_profile_payload(dog, basics):
    """일주 캐릭터·띠처럼 저장하지 않고 원국에서 바로 계산하는 정보."""
    return {
        'day_pillar_profile': get_day_pillar_profile(basics.day_pillar),
        'zodiac': get_zodiac(basics.year_pillar),
        'is_estimated_birth': dog.is_estimated_birth,
    }


def build_daily_luck(dog, dog_element, target_date):
    """그날의 일진(日辰)과 강아지 오행의 관계로 산책운을 고릅니다.

    관계는 일진에 따라 바뀌고, 버전(A/B/C)도 날짜마다 돌아가므로 매일 다른 문구가 나옵니다.
    """
    today_element = get_daily_pillar(target_date)['element']
    relationship_type = get_relationship_type(dog_element, today_element)
    version = ARCHETYPE_VERSIONS[(target_date.toordinal() + dog.id) % len(ARCHETYPE_VERSIONS)]

    archetype = DailyLuckArchetype.objects.filter(
        dog_element=dog_element,
        relationship_type=relationship_type,
        version=version,
    ).first() or DailyLuckArchetype.objects.filter(
        dog_element=dog_element,
        relationship_type=relationship_type,
    ).order_by('version').first()

    low, high = DAILY_SCORE_RANGES.get(relationship_type, (70, 90))
    luck_score = random.Random(f'{dog.id}:{target_date.isoformat()}').randint(low, high)

    if archetype:
        return {
            'luck_score': luck_score,
            'message': smart_replace(archetype.message, dog.name),
            'lucky_color': archetype.lucky_color,
            'lucky_direction': archetype.lucky_direction,
        }
    return {
        'luck_score': luck_score,
        'message': smart_replace(DEFAULT_DAILY_MESSAGE, dog.name),
        'lucky_color': '보라색',
        'lucky_direction': '어디든',
    }


def build_interpretation(dog, saju):
    """사전 생성 프로필(아키타입)로 강아지의 평생 풀이 필드를 만듭니다. 프로필이 없으면 None."""
    primary = saju.main_element
    relationship_type = saju.relationship_type or '비겁'
    secondary_element = saju.secondary_element or primary

    archetype = ArchetypeSaju.objects.filter(
        primary_element=primary,
        relationship_type=relationship_type,
        version=ARCHETYPE_VERSIONS[dog.id % len(ARCHETYPE_VERSIONS)],
    ).first() or ArchetypeSaju.objects.filter(
        primary_element=primary,
        relationship_type=relationship_type,
    ).first()
    if not archetype:
        return None

    def replace_name(text):
        return smart_replace(text, dog.name)

    keywords = [replace_name(k) for k in archetype.personality_keywords] if isinstance(archetype.personality_keywords, list) else []
    secondary_text = get_secondary_influence_text(primary, secondary_element)
    care_tips = replace_name(archetype.care_tips)
    if secondary_text:
        care_tips += f"\n\n\U0001f4a1 [추가 사주 분석] {secondary_text}"

    return {
        'personality_summary': add_hanja_to_terms(replace_name(archetype.personality_summary)),
        'personality_keywords': [add_hanja_to_terms(k) for k in keywords],
        'vitality_analysis': add_hanja_to_terms(replace_name(archetype.vitality_analysis)),
        'social_analysis': add_hanja_to_terms(replace_name(archetype.social_analysis)),
        'treat_luck': add_hanja_to_terms(replace_name(archetype.treat_luck)),
        'care_tips': add_hanja_to_terms(care_tips),
    }


def build_today_context(dog_element, target_date):
    daily = get_daily_pillar(target_date)
    profile = get_day_pillar_profile(daily['pillar'])
    return {
        'today_pillar': profile['pillar'] if profile else '',
        'today_pillar_hanja': daily['pillar'],
        'today_element': daily['element'],
        'today_relationship': add_hanja_to_terms(get_relationship_type(dog_element, daily['element'])),
    }


def compute_attendance_streak(user, today):
    """오늘(또는 아직 출석 전이면 어제)부터 거꾸로 이어지는 연속 출석 일수. 월이 바뀌어도 이어집니다."""
    days_by_month = {
        (record.year, record.month): set(record.attended_days)
        for record in Attendance.objects.filter(user=user).only('year', 'month', 'attended_days')
    }
    cursor = today
    if today.day not in days_by_month.get((today.year, today.month), ()):
        cursor = today - timedelta(days=1)
    streak = 0
    while cursor.day in days_by_month.get((cursor.year, cursor.month), ()):
        streak += 1
        cursor -= timedelta(days=1)
    return streak


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


class TossUserAPIView(APIView):
    """토스 사용자 키 헤더가 있어야 하고, 강아지는 본인 것만 접근할 수 있는 API의 기반 클래스."""
    authentication_classes = []
    permission_classes = [HasTossUserKey]

    @property
    def user_key(self):
        return get_request_user_key(self.request)

    def get_owned_dog(self, dog_id, *related):
        queryset = Dog.objects.filter(user__social_id=self.user_key)
        if related:
            queryset = queryset.select_related(*related)
        dog = queryset.filter(id=dog_id).first()
        if dog is None:
            raise NotFound('강아지 정보를 찾을 수 없어요.')
        return dog

    def get_saju_basics_or_error(self, dog):
        """원국을 보장합니다. 계산할 수 없으면 (None, 에러 응답)을 돌려줍니다."""
        if not dog.birth_date:
            return None, Response({"error": "강아지의 생일 정보가 없어 사주를 계산할 수 없어요."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            return ensure_saju_basics(dog), None
        except InvalidBirthDateError:
            return None, Response({"error": LUNAR_DATE_ERROR}, status=status.HTTP_400_BAD_REQUEST)


class DogRegisterView(TossUserAPIView):
    def post(self, request):
        dog_data = request.data.get('dog')
        if not isinstance(dog_data, dict):
            return Response({"error": "강아지 정보를 입력해주세요."}, status=status.HTTP_400_BAD_REQUEST)

        serializer = DogSerializer(data=dog_data)
        if not serializer.is_valid():
            return validation_error_response(serializer.errors)

        user = get_or_create_user(self.user_key, request.data.get('nickname'))
        values = serializer.validated_data

        # 같은 이름의 강아지는 한 마리로 관리: 생일 정보가 바뀌면 고쳐 쓰고 결과를 다시 계산
        dog = user.dogs.filter(name=values['name']).order_by('-updated_at', '-id').first()
        if dog is None:
            dog = serializer.save(user=user)
            return Response(
                {"message": "등록 완료", "user_nickname": user.nickname, "dog_id": dog.id, "updated": False},
                status=status.HTTP_201_CREATED,
            )

        changed = any(getattr(dog, field) != value for field, value in values.items())
        if changed:
            for field, value in values.items():
                setattr(dog, field, value)
            dog.save()
            clear_dog_results(dog)
        else:
            dog.save(update_fields=['updated_at'])  # 최근에 본 강아지가 목록 맨 앞에 오도록

        return Response(
            {"message": "등록 완료", "user_nickname": user.nickname, "dog_id": dog.id, "updated": changed},
            status=status.HTTP_200_OK,
        )


class MyDogsView(TossUserAPIView):
    """재방문 시 다시 입력하지 않도록, 내가 등록한 강아지 목록을 최근 순으로 돌려줍니다."""

    def get(self, request):
        dogs = (
            Dog.objects.filter(user__social_id=self.user_key)
            .select_related('saju_basics')
            .order_by('-updated_at', '-id')[:MY_DOGS_LIMIT]
        )
        results = []
        for dog in dogs:
            item = DogSerializer(dog).data
            basics = dog.saju_basics if hasattr(dog, 'saju_basics') else None
            item['main_element'] = basics.main_element if basics else None
            profile = get_day_pillar_profile(basics.day_pillar) if basics else None
            item['nickname'] = profile['nickname'] if profile else None
            results.append(item)
        return Response({'dogs': results}, status=status.HTTP_200_OK)


class SajuBasicsView(TossUserAPIView):
    def get(self, request, dog_id):
        dog = self.get_owned_dog(dog_id, 'saju_basics')
        created = not hasattr(dog, 'saju_basics')
        basics, error = self.get_saju_basics_or_error(dog)
        if error:
            return error
        serializer = SajuBasicsSerializer(basics)
        return Response(serializer.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class AIInterpretationView(TossUserAPIView):
    def get(self, request, dog_id):
        dog = self.get_owned_dog(dog_id, 'saju_basics', 'ai_interpretation')
        saju, error = self.get_saju_basics_or_error(dog)
        if error:
            return error

        created = False
        if hasattr(dog, 'ai_interpretation'):
            interpretation = dog.ai_interpretation
        else:
            fields = build_interpretation(dog, saju)
            if fields is None:
                return Response({"error": "사전 생성된 사주 프로필을 찾을 수 없어요. (pregenerate_saju 명령어 실행 필요)"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            interpretation, created = AIInterpretation.objects.get_or_create(dog=dog, defaults=fields)

        data = AIInterpretationSerializer(interpretation).data
        data.update(build_profile_payload(dog, saju))
        return Response(data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class DailyWalkingLuckView(TossUserAPIView):
    def get(self, request, dog_id):
        dog = self.get_owned_dog(dog_id, 'saju_basics')
        saju, error = self.get_saju_basics_or_error(dog)
        if error:
            return error

        today = timezone.localdate()
        luck = DailyWalkingLuck.objects.filter(dog=dog, date=today).first()
        created = False
        if luck is None:
            luck, created = DailyWalkingLuck.objects.get_or_create(
                dog=dog,
                date=today,
                defaults=build_daily_luck(dog, saju.main_element, today),
            )

        data = DailyWalkingLuckSerializer(luck).data
        data['message'] = add_hanja_to_terms(data['message'])
        data.update(build_today_context(saju.main_element, today))
        return Response(data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class CompatibilityResultView(TossUserAPIView):
    def post(self, request, dog_id):
        dog = self.get_owned_dog(dog_id, 'user', 'saju_basics')
        owner_name = request.data.get('owner_name', '')
        display_owner_name = '보호자님'

        serializer = PersonBirthSerializer(data=request.data)
        if not serializer.is_valid():
            return validation_error_response(serializer.errors)
        owner = serializer.validated_data

        saju, error = self.get_saju_basics_or_error(dog)
        if error:
            return error

        dog_element = saju.main_element
        owner_saju = get_saju_for_dog(
            owner['owner_birth_date'],
            owner.get('owner_birth_time'),
            owner['owner_is_lunar'],
            owner['owner_is_leap_month'],
        )
        owner_element = owner_saju['main_element']
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
                {"error": "사전 생성된 궁합 프로필을 찾을 수 없어요. (pregenerate_compatibility 명령어 실행 필요)"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        def normalize(text):
            # 보호자 자리표시자는 smart_replace에 맡기지 않음: 조사 없이 끝나는 '[보호자이름]'에
            # 강아지 이름처럼 '이'를 붙여 "…리더, 보호자님이"가 되는 문제가 있어 정규화 함수가 처리
            return normalize_owner_honorific_text(
                normalize_compatibility_owner_text(
                    smart_replace(text, dog.name),
                    owner_name,
                ),
                display_owner_name,
            )

        result_title = normalize(archetype.title)
        result_description = normalize(archetype.description)
        result_advice = normalize(archetype.advice)

        # 같은 오행 관계라도 띠 궁합(육합·삼합·충)으로 점수가 달라지도록 보정
        zodiac = build_zodiac_match(saju.year_pillar, owner_saju.get('year_pillar'))
        score = clamp_score(archetype.score + (zodiac['bonus'] if zodiac else 0))

        meta_prefix = f"{dog_element}|{owner_element}|{relationship_type}|"
        Compatibility.objects.update_or_create(
            dog=dog,
            user=dog.user,
            defaults={
                'score': score,
                'title': result_title,
                'description': meta_prefix + result_description,
            },
        )

        return Response(
            {
                'dog_element': dog_element,
                'owner_element': owner_element,
                'relationship_type': add_hanja_to_terms(relationship_type),
                'score': score,
                'base_score': archetype.score,
                'title': add_hanja_to_terms(result_title),
                'description': add_hanja_to_terms(result_description),
                'advice': add_hanja_to_terms(result_advice),
                'zodiac': zodiac,
            },
            status=status.HTTP_200_OK,
        )


class FriendCompatibilityView(TossUserAPIView):
    """내 강아지 ↔ 친구 강아지 궁합 (저장하지 않고 바로 계산)."""

    def post(self, request, dog_id):
        dog = self.get_owned_dog(dog_id, 'saju_basics')
        serializer = FriendDogSerializer(data=request.data)
        if not serializer.is_valid():
            return validation_error_response(serializer.errors)
        friend = serializer.validated_data

        saju, error = self.get_saju_basics_or_error(dog)
        if error:
            return error

        friend_saju = get_saju_for_dog(
            friend['friend_birth_date'], None, friend['friend_is_lunar'], friend['friend_is_leap_month'],
        )
        my_element = saju.main_element
        friend_element = friend_saju['main_element']
        relationship_type = get_relationship_type(my_element, friend_element)

        seed = (dog.id, friend['friend_name'], friend['friend_birth_date'].isoformat())
        content = build_friend_compatibility(
            relationship_type, dog.name, friend['friend_name'], my_element, friend_element, seed,
        )
        zodiac = build_zodiac_match(saju.year_pillar, friend_saju.get('year_pillar'))
        score = clamp_score(content['base_score'] + (zodiac['bonus'] if zodiac else 0) + seeded_offset(2, *seed))

        return Response(
            {
                'score': score,
                'title': content['title'],
                'description': content['description'],
                'tip': content['tip'],
                'relationship_type': add_hanja_to_terms(relationship_type),
                'my_element': my_element,
                'friend_element': friend_element,
                'friend_name': friend['friend_name'],
                'zodiac': zodiac,
                'my_profile': get_day_pillar_profile(saju.day_pillar),
                'friend_profile': get_day_pillar_profile(friend_saju.get('day_pillar')),
            },
            status=status.HTTP_200_OK,
        )


class DogShareView(TossUserAPIView):
    """공유 카드 토큰을 발급합니다. 한 번 만든 토큰은 계속 같은 값을 씁니다."""

    def post(self, request, dog_id):
        dog = self.get_owned_dog(dog_id)
        for _ in range(3):
            if dog.share_token:
                break
            try:
                with transaction.atomic():
                    # 조건부 업데이트라 동시에 요청해도 먼저 저장된 토큰 하나만 남음
                    Dog.objects.filter(id=dog.id, share_token__isnull=True).update(share_token=secrets.token_urlsafe(12))
            except IntegrityError:
                continue
            dog.share_token = Dog.objects.values_list('share_token', flat=True).get(id=dog.id)
        if not dog.share_token:
            return Response({"error": "공유 링크를 만들지 못했어요. 잠시 후 다시 시도해주세요."}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        return Response({'token': dog.share_token}, status=status.HTTP_200_OK)


class SharedCardView(APIView):
    """공유 링크로 들어온 사람에게 보여주는 공개 카드. 생년월일·사주표는 노출하지 않습니다."""
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request, token):
        dog = Dog.objects.select_related('saju_basics', 'ai_interpretation').filter(share_token=token).first()
        if dog is None or not dog.birth_date:
            raise NotFound('공유 카드를 찾을 수 없어요.')
        try:
            saju = ensure_saju_basics(dog)
        except InvalidBirthDateError:
            raise NotFound('공유 카드를 찾을 수 없어요.')
        interpretation = dog.ai_interpretation if hasattr(dog, 'ai_interpretation') else None
        return Response(
            {
                'dog_name': dog.name,
                'main_element': saju.main_element,
                'profile': get_day_pillar_profile(saju.day_pillar),
                'zodiac': get_zodiac(saju.year_pillar),
                'personality_summary': interpretation.personality_summary if interpretation else '',
                'keywords': interpretation.personality_keywords if interpretation else [],
            },
            status=status.HTTP_200_OK,
        )


class AttendanceView(TossUserAPIView):
    MILESTONES = [1, 3, 5, 7, 10, 15, 20]

    def _get_or_create_attendance(self, user, today):
        attendance, _ = Attendance.objects.get_or_create(
            user=user,
            year=today.year,
            month=today.month,
            defaults={'attended_days': [], 'streak_count': 0, 'claimed_milestones': []},
        )
        return attendance

    def _build_payload(self, user, attendance, today):
        total_days = len(attendance.attended_days)
        return {
            'year': attendance.year,
            'month': attendance.month,
            'attended_days': attendance.attended_days,
            # streak_count는 이전 버전 앱 호환용(이번 달 누적 일수). 새 앱은 total_days/streak_days 사용
            'streak_count': total_days,
            'total_days': total_days,
            'streak_days': compute_attendance_streak(user, today),
            'claimed_milestones': attendance.claimed_milestones,
            'next_milestone': next((m for m in self.MILESTONES if m > total_days), None),
            'already_stamped_today': today.day in attendance.attended_days,
        }

    def get(self, request):
        user = get_or_create_user(self.user_key)
        today = timezone.localdate()
        attendance = self._get_or_create_attendance(user, today)
        return Response(self._build_payload(user, attendance, today), status=status.HTTP_200_OK)

    def post(self, request):
        user = get_or_create_user(self.user_key)
        today = timezone.localdate()
        self._get_or_create_attendance(user, today)

        new_milestone = None
        with transaction.atomic():
            # 연타·중복 요청이 동시에 와도 출석이 한 번만 반영되도록 행 잠금
            attendance = Attendance.objects.select_for_update().get(user=user, year=today.year, month=today.month)
            stamped = today.day not in attendance.attended_days
            if stamped:
                new_days = sorted(set(attendance.attended_days + [today.day]))
                new_total = len(new_days)
                if new_total in self.MILESTONES and new_total not in attendance.claimed_milestones:
                    new_milestone = new_total
                    attendance.claimed_milestones = sorted(set(attendance.claimed_milestones + [new_total]))
                attendance.attended_days = new_days
                attendance.streak_count = new_total
                attendance.save(update_fields=['attended_days', 'streak_count', 'claimed_milestones', 'updated_at'])

        payload = self._build_payload(user, attendance, today)
        payload.update({
            'stamped': stamped,
            'message': '출석 완료!' if stamped else '오늘은 이미 출석했어요.',
            'new_milestone': new_milestone,
        })
        return Response(payload, status=status.HTTP_200_OK)
