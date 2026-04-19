from django.contrib import admin
from .models import (
    User, Dog, SajuBasics, AIInterpretation, 
    DailyWalkingLuck, Compatibility, 
    ArchetypeSaju, CompatibilityArchetype, DailyElementLuck,
    DailyLuckArchetype
)

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

@admin.register(ArchetypeSaju)
class ArchetypeSajuAdmin(admin.ModelAdmin):
    list_display = ('id', 'primary_element', 'relationship_type', 'version', 'personality_summary')
    list_filter = ('primary_element', 'relationship_type', 'version')
    search_fields = ('personality_summary',)

@admin.register(CompatibilityArchetype)
class CompatibilityArchetypeAdmin(admin.ModelAdmin):
    list_display = ('id', 'dog_element', 'relationship_type', 'version', 'score', 'title')
    list_filter = ('dog_element', 'relationship_type', 'version')
    search_fields = ('title', 'description')

@admin.register(DailyLuckArchetype)
class DailyLuckArchetypeAdmin(admin.ModelAdmin):
    list_display = ('id', 'dog_element', 'relationship_type', 'version', 'lucky_color', 'lucky_direction')
    list_filter = ('dog_element', 'relationship_type', 'version')
    search_fields = ('message',)

@admin.register(DailyElementLuck)
class DailyElementLuckAdmin(admin.ModelAdmin):
    list_display = ('id', 'date', 'element', 'luck_score')
    list_filter = ('date', 'element')
