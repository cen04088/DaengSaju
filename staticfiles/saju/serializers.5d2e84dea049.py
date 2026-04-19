from rest_framework import serializers
from .models import User, Dog, SajuBasics, AIInterpretation, DailyWalkingLuck

class DogSerializer(serializers.ModelSerializer):
    class Meta:
        model = Dog
        fields = ['id', 'name', 'birth_date', 'birth_time', 'is_lunar', 'gender', 'is_estimated_birth']

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
