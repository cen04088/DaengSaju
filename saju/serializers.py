from datetime import date

from django.utils import timezone
from rest_framework import serializers

from .models import Dog, SajuBasics, AIInterpretation, DailyWalkingLuck
from .services.manseryeok import InvalidBirthDateError, to_solar_date

NAME_MAX_LENGTH = 20
DOG_BIRTH_MIN = date(1990, 1, 1)
PERSON_BIRTH_MIN = date(1900, 1, 1)
LUNAR_DATE_ERROR = '음력 날짜를 확인해주세요. 윤달이 없는 달이거나 존재하지 않는 날짜예요.'


def validate_birth(birth_date, is_lunar, is_leap_month, min_date, label):
    """음력이면 양력으로 바꾼 뒤 범위를 검사하고, 양력 날짜를 반환합니다."""
    try:
        solar_date = to_solar_date(birth_date, is_lunar, is_leap_month)
    except InvalidBirthDateError:
        raise serializers.ValidationError({'birth_date': LUNAR_DATE_ERROR})
    if solar_date > timezone.localdate():
        raise serializers.ValidationError({'birth_date': f'{label} 생일이 오늘보다 미래일 수 없어요.'})
    if solar_date < min_date:
        raise serializers.ValidationError({'birth_date': f'{label} 생일은 {min_date.year}년 이후로 입력해주세요.'})
    return solar_date


def clean_name(value, label):
    name = (value or '').strip()
    if not name:
        raise serializers.ValidationError(f'{label} 이름을 입력해주세요.')
    if len(name) > NAME_MAX_LENGTH:
        raise serializers.ValidationError(f'{label} 이름은 {NAME_MAX_LENGTH}자 이내로 입력해주세요.')
    return name


class DogSerializer(serializers.ModelSerializer):
    class Meta:
        model = Dog
        fields = ['id', 'name', 'birth_date', 'birth_time', 'is_lunar', 'is_leap_month', 'gender', 'is_estimated_birth']
        extra_kwargs = {'birth_date': {'required': True, 'allow_null': False}}

    def validate_name(self, value):
        return clean_name(value, '강아지')

    def validate(self, attrs):
        # 누락된 선택 필드는 기본값으로 채워서, 같은 이름 재등록 시 비교가 정확하도록 함
        attrs.setdefault('birth_time', None)
        attrs.setdefault('is_lunar', False)
        attrs.setdefault('is_estimated_birth', False)
        attrs['is_leap_month'] = bool(attrs.get('is_leap_month')) and attrs['is_lunar']
        validate_birth(attrs['birth_date'], attrs['is_lunar'], attrs['is_leap_month'], DOG_BIRTH_MIN, '강아지')
        return attrs


class PersonBirthSerializer(serializers.Serializer):
    """궁합용 보호자 생년월일시 입력."""
    owner_birth_date = serializers.DateField()
    owner_birth_time = serializers.TimeField(required=False, allow_null=True)
    owner_is_lunar = serializers.BooleanField(required=False, default=False)
    owner_is_leap_month = serializers.BooleanField(required=False, default=False)

    def to_internal_value(self, data):
        data = data.copy() if hasattr(data, 'copy') else dict(data)
        if data.get('owner_birth_time') in ('', None):
            data['owner_birth_time'] = None
        return super().to_internal_value(data)

    def validate(self, attrs):
        attrs['owner_is_leap_month'] = attrs['owner_is_leap_month'] and attrs['owner_is_lunar']
        try:
            validate_birth(attrs['owner_birth_date'], attrs['owner_is_lunar'], attrs['owner_is_leap_month'], PERSON_BIRTH_MIN, '보호자')
        except serializers.ValidationError as exc:
            raise serializers.ValidationError({'owner_birth_date': exc.detail['birth_date']})
        return attrs


class FriendDogSerializer(serializers.Serializer):
    """강아지 친구 궁합용 친구 강아지 입력."""
    friend_name = serializers.CharField(max_length=50)
    friend_birth_date = serializers.DateField()
    friend_is_lunar = serializers.BooleanField(required=False, default=False)
    friend_is_leap_month = serializers.BooleanField(required=False, default=False)

    def validate_friend_name(self, value):
        return clean_name(value, '친구 강아지')

    def validate(self, attrs):
        attrs['friend_is_leap_month'] = attrs['friend_is_leap_month'] and attrs['friend_is_lunar']
        try:
            validate_birth(attrs['friend_birth_date'], attrs['friend_is_lunar'], attrs['friend_is_leap_month'], DOG_BIRTH_MIN, '친구 강아지')
        except serializers.ValidationError as exc:
            raise serializers.ValidationError({'friend_birth_date': exc.detail['birth_date']})
        return attrs


class SajuBasicsSerializer(serializers.ModelSerializer):
    class Meta:
        model = SajuBasics
        fields = ['year_pillar', 'month_pillar', 'day_pillar', 'hour_pillar', 'main_element', 'element_distribution']

class AIInterpretationSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIInterpretation
        fields = ['personality_summary', 'personality_keywords', 'vitality_analysis', 'social_analysis', 'treat_luck', 'care_tips', 'updated_at']

class DailyWalkingLuckSerializer(serializers.ModelSerializer):
    class Meta:
        model = DailyWalkingLuck
        fields = ['date', 'luck_score', 'message', 'lucky_color', 'lucky_direction']
