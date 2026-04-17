from django.db import models
from django.contrib.auth.models import AbstractUser

class TimeStampedModel(models.Model):
    """
    공통 생성/수정 시간 필드 모델
    """
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="생성일")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="수정일")

    class Meta:
        abstract = True

class User(AbstractUser, TimeStampedModel):
    """
    보호자 모델
    - Toss 로그인 연동을 위해 social_id 사용
    """
    social_id = models.CharField(max_length=255, unique=True, verbose_name="Toss 식별값")
    nickname = models.CharField(max_length=50, verbose_name="닉네임")

    def __str__(self):
        return f"{self.nickname} ({self.username})"

class Dog(TimeStampedModel):
    """
    강아지 모델
    """
    class GenderChoices(models.TextChoices):
        MALE = 'MALE', '수컷'
        FEMALE = 'FEMALE', '암컷'
        NEUTERED = 'NEUTERED', '중성화'

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='dogs', verbose_name="보호자")
    name = models.CharField(max_length=50, verbose_name="강아지 이름")
    birth_date = models.DateField(null=True, blank=True, verbose_name="생년월일")
    birth_time = models.TimeField(null=True, blank=True, verbose_name="태어난 시간")
    is_lunar = models.BooleanField(default=False, verbose_name="음력 여부")
    gender = models.CharField(max_length=10, choices=GenderChoices.choices, verbose_name="성별")
    is_estimated_birth = models.BooleanField(default=False, verbose_name="생일 추정 여부(유기견 등)")

    def __str__(self):
        return f"{self.name} ({self.user.nickname}님의 반려견)"

class SajuBasics(TimeStampedModel):
    """
    사주 원국 모델 (manseryeok 결과)
    """
    dog = models.OneToOneField(Dog, on_delete=models.CASCADE, related_name='saju_basics', verbose_name="강아지")
    
    # 사주 팔자 (년주, 월주, 일주, 시주)
    year_pillar = models.CharField(max_length=10, verbose_name="년주")
    month_pillar = models.CharField(max_length=10, verbose_name="월주")
    day_pillar = models.CharField(max_length=10, verbose_name="일주")
    hour_pillar = models.CharField(max_length=10, blank=True, null=True, verbose_name="시주")
    
    main_element = models.CharField(max_length=10, verbose_name="일간 오행")
    element_distribution = models.JSONField(verbose_name="오행 비중", help_text="목/화/토/금/수 비중 저장")

    # 3단계: 십성(十星) 관련 필드
    relationship_type = models.CharField(
        max_length=10, blank=True, null=True, verbose_name="십성 유형",
        help_text="비겁/인성/식상/재성/관성"
    )
    secondary_element = models.CharField(
        max_length=10, blank=True, null=True, verbose_name="2위 오행"
    )

    def __str__(self):
        return f"{self.dog.name}의 사주 원국"

class AIInterpretation(TimeStampedModel):
    """
    AI 성격 분석 결과 (Gemini API 결과 캐싱)
    """
    dog = models.OneToOneField(Dog, on_delete=models.CASCADE, related_name='ai_interpretation', verbose_name="강아지")
    
    personality_summary = models.CharField(max_length=255, verbose_name="성격 요약")
    personality_keywords = models.JSONField(verbose_name="성격 키워드 목록")
    
    vitality_analysis = models.TextField(verbose_name="활력 분석서")
    social_analysis = models.TextField(verbose_name="사회성 분석서")
    treat_luck = models.TextField(verbose_name="간식운")
    care_tips = models.TextField(verbose_name="케어 팁")

    def __str__(self):
        return f"{self.dog.name}의 AI 성격 분석"

class DailyWalkingLuck(TimeStampedModel):
    """
    오늘의 산책운 (매일 갱신 및 이력 보관)
    """
    dog = models.ForeignKey(Dog, on_delete=models.CASCADE, related_name='daily_walking_lucks', verbose_name="강아지")
    date = models.DateField(verbose_name="해당 날짜")
    
    luck_score = models.IntegerField(verbose_name="운세 점수")
    message = models.TextField(verbose_name="산책운 메시지")
    lucky_color = models.CharField(max_length=30, verbose_name="행운의 색")
    lucky_direction = models.CharField(max_length=30, verbose_name="행운의 방향")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['dog', 'date'], name='unique_dog_daily_luck')
        ]

    def __str__(self):
        return f"{self.date} - {self.dog.name}의 산책운 ({self.luck_score}점)"

class Compatibility(TimeStampedModel):
    """
    댕궁합 (강아지와 보호자 궁합)
    """
    dog = models.ForeignKey(Dog, on_delete=models.CASCADE, related_name='compatibilities', verbose_name="강아지")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='compatibilities', verbose_name="대상 보호자")
    
    score = models.IntegerField(verbose_name="궁합 점수")
    title = models.CharField(max_length=100, verbose_name="궁합 타이틀", help_text="예: 환상의 콤비")
    description = models.TextField(verbose_name="궁합 상세 설명")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['dog', 'user'], name='unique_dog_user_compatibility')
        ]

    def __str__(self):
        return f"{self.dog.name} & {self.user.nickname}: {self.title} ({self.score}점)"


class CompatibilityArchetype(TimeStampedModel):
    """
    댕궁합 결과 사전 생성 템플릿
    총 50개: 강아지 오행(5) × 십성 유형(5) × 버전(A/B) 2개
    """
    dog_element = models.CharField(max_length=10, verbose_name="강아지 본질 오행")
    relationship_type = models.CharField(max_length=10, verbose_name="십성 유형 (강아지↔보호자)")
    version = models.CharField(max_length=5, default="A", verbose_name="버전")

    score = models.IntegerField(verbose_name="궁합 점수 (0~100)")
    title = models.CharField(max_length=100, verbose_name="궁합 타이틀")
    description = models.TextField(verbose_name="궁합 상세 설명")
    advice = models.TextField(verbose_name="보호자를 위한 관계 어드바이스")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['dog_element', 'relationship_type', 'version'],
                name='unique_compatibility_archetype'
            )
        ]

    def __str__(self):
        return f"[{self.version}] 강아지:{self.dog_element} / 관계:{self.relationship_type}"

class ArchetypeSaju(TimeStampedModel):
    """
    평생 사주 원국 조합의 템플릿(Archetype) 캐싱 모델
    3단계: strongest_element → relationship_type (십성 유형) 으로 전환
    """
    primary_element = models.CharField(max_length=10, verbose_name="본질 오행")
    relationship_type = models.CharField(
        max_length=10, verbose_name="십성 유형",
        help_text="비겁/인성/식상/재성/관성"
    )
    version = models.CharField(max_length=10, default="A", verbose_name="버전 (A/B/C)")

    personality_summary = models.CharField(max_length=255, verbose_name="성격 요약")
    personality_keywords = models.JSONField(verbose_name="성격 키워드 목록")
    vitality_analysis = models.TextField(verbose_name="활력 분석서")
    social_analysis = models.TextField(verbose_name="사회성 분석서")
    treat_luck = models.TextField(verbose_name="간식운")
    care_tips = models.TextField(verbose_name="케어 팁")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['primary_element', 'relationship_type', 'version'], name='unique_archetype_saju')
        ]

    def __str__(self):
        return f"[{self.version}] 본질:{self.primary_element} / 십성:{self.relationship_type}"

class DailyElementLuck(TimeStampedModel):
    """
    매일 오행(5개) 별로 하루 한 번만 갱신되는 공통 산책운
    """
    date = models.DateField(verbose_name="해당 날짜")
    element = models.CharField(max_length=10, verbose_name="주인공 오행")

    luck_score = models.IntegerField(verbose_name="운세 점수")
    message = models.TextField(verbose_name="산책운 메시지")
    lucky_color = models.CharField(max_length=30, verbose_name="행운의 색")
    lucky_direction = models.CharField(max_length=30, verbose_name="행운의 방향")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['date', 'element'], name='unique_daily_element_luck')
        ]

    def __str__(self):
        return f"{self.date} - {self.element} 기운의 산책운"
