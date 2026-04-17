from django.contrib import admin
from .models import User, Dog, SajuBasics, AIInterpretation, DailyWalkingLuck, Compatibility

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('id', 'username', 'nickname', 'social_id', 'created_at')
    search_fields = ('username', 'nickname', 'social_id')

@admin.register(Dog)
class DogAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'user', 'birth_date', 'gender', 'created_at')
    list_filter = ('gender', 'is_lunar', 'is_estimated_birth')
    search_fields = ('name', 'user__nickname')

@admin.register(SajuBasics)
class SajuBasicsAdmin(admin.ModelAdmin):
    list_display = ('id', 'dog', 'main_element', 'created_at')
    search_fields = ('dog__name',)

@admin.register(AIInterpretation)
class AIInterpretationAdmin(admin.ModelAdmin):
    list_display = ('id', 'dog', 'personality_summary', 'updated_at')
    search_fields = ('dog__name', 'personality_summary')

@admin.register(DailyWalkingLuck)
class DailyWalkingLuckAdmin(admin.ModelAdmin):
    list_display = ('id', 'dog', 'date', 'luck_score', 'created_at')
    list_filter = ('date', 'luck_score')
    search_fields = ('dog__name',)

@admin.register(Compatibility)
class CompatibilityAdmin(admin.ModelAdmin):
    list_display = ('id', 'dog', 'user', 'score', 'title', 'created_at')
    list_filter = ('score',)
    search_fields = ('dog__name', 'user__nickname', 'title')
