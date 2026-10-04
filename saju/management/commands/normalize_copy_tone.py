# -*- coding: utf-8 -*-
import difflib

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from saju.models import AIInterpretation, ArchetypeSaju, DailyLuckArchetype, DailyWalkingLuck
from saju.services.tone import normalize_copy
from saju.views import build_daily_luck, build_interpretation

TEXT_FIELDS = ('personality_summary', 'vitality_analysis', 'social_analysis', 'treat_luck', 'care_tips')
# 다시 만든 글이 저장된 글과 이만큼 비슷해야 같은 원본으로 보고 바꿔 씀(어미·조사만 다른 경우)
SAME_SOURCE_RATIO = 0.85


def same_source(saved, regenerated):
    matcher = difflib.SequenceMatcher(None, normalize_copy(saved), regenerated, autojunk=False)
    return (
        matcher.real_quick_ratio() >= SAME_SOURCE_RATIO
        and matcher.quick_ratio() >= SAME_SOURCE_RATIO
        and matcher.ratio() >= SAME_SOURCE_RATIO
    )


def refreshed(saved, regenerated):
    """같은 원본에서 나온 글이면 새로 만든 글(어미·이름 조사 모두 정리), 아니면 저장된 글의 어미만 정리."""
    if regenerated and same_source(saved, regenerated):
        return regenerated
    return normalize_copy(saved)


class Command(BaseCommand):
    help = '사전 생성 운세 문구를 해요체로 맞추고, 강아지별로 저장된 평생 풀이·오늘 산책운도 새 문구로 다시 만듭니다.'

    def add_arguments(self, parser):
        parser.add_argument('--all', action='store_true', help='원본이 이미 정리돼 있어도 강아지별 문구를 다시 확인')

    @transaction.atomic
    def handle(self, *args, **options):
        archetypes = 0
        for archetype in ArchetypeSaju.objects.all():
            changed = [f for f in TEXT_FIELDS if normalize_copy(getattr(archetype, f)) != getattr(archetype, f)]
            for field in changed:
                setattr(archetype, field, normalize_copy(getattr(archetype, field)))
            if changed:
                archetype.save(update_fields=changed)
                archetypes += 1
        for archetype in DailyLuckArchetype.objects.all():
            message = normalize_copy(archetype.message)
            if message != archetype.message:
                archetype.message = message
                archetype.save(update_fields=['message'])
                archetypes += 1

        if not archetypes and not options['all']:
            self.stdout.write('운세 문구가 이미 정리돼 있어요.')
            return

        interpretations = 0
        for interpretation in AIInterpretation.objects.select_related('dog', 'dog__saju_basics'):
            saju = getattr(interpretation.dog, 'saju_basics', None)
            fresh = build_interpretation(interpretation.dog, saju) if saju else None
            changed = []
            for field in TEXT_FIELDS:
                saved = getattr(interpretation, field)
                value = refreshed(saved, fresh[field] if fresh else None)
                if value != saved:
                    setattr(interpretation, field, value)
                    changed.append(field)
            if changed:
                interpretation.save(update_fields=changed)
                interpretations += 1

        lucks = 0
        today = timezone.localdate()
        for luck in DailyWalkingLuck.objects.filter(date__gte=today).select_related('dog', 'dog__saju_basics'):
            saju = getattr(luck.dog, 'saju_basics', None)
            fresh = build_daily_luck(luck.dog, saju.main_element, luck.date)['message'] if saju else None
            message = refreshed(luck.message, fresh)
            if message != luck.message:
                luck.message = message
                luck.save(update_fields=['message'])
                lucks += 1

        self.stdout.write(self.style.SUCCESS(
            f'문구 정리: 원본 {archetypes}개, 평생 풀이 {interpretations}개, 오늘 산책운 {lucks}개를 해요체로 바꿨어요.'
        ))
