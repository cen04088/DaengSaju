# -*- coding: utf-8 -*-

from django.core.management.base import BaseCommand

from saju.compatibility_copy import get_curated_compatibility_copy
from saju.models import CompatibilityArchetype


class Command(BaseCommand):
    help = '현재 CompatibilityArchetype 문구를 최신 고정 카피로 모두 갱신합니다.'

    def handle(self, *args, **options):
        dog_elements = ['목', '화', '토', '금', '수']
        relationship_types = ['비겁', '인성', '식상', '재성', '관성']
        versions = ['A', 'B']

        updated = 0

        for dog_element in dog_elements:
            for relationship_type in relationship_types:
                for version in versions:
                    data = get_curated_compatibility_copy(
                        dog_element=dog_element,
                        relationship_type=relationship_type,
                        version=version,
                    )

                    CompatibilityArchetype.objects.update_or_create(
                        dog_element=dog_element,
                        relationship_type=relationship_type,
                        version=version,
                        defaults={
                            'score': data['score'],
                            'title': data['title'],
                            'description': data['description'],
                            'advice': data['advice'],
                        },
                    )
                    updated += 1

        self.stdout.write(self.style.SUCCESS(f'CompatibilityArchetype {updated}개를 최신 문구로 갱신했습니다.'))
