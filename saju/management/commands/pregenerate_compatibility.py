# -*- coding: utf-8 -*-
"""
댕궁합 사전 생성 템플릿(CompatibilityArchetype) 생성 커맨드.
총 50개 강아지 오행(5) x 십성 유형(5) x 버전(A/B) 2개를 생성한다.
"""

from django.core.management.base import BaseCommand

from saju.compatibility_copy import get_curated_compatibility_copy
from saju.models import CompatibilityArchetype


class Command(BaseCommand):
    help = '댕궁합 CompatibilityArchetype 50개를 사전 생성합니다.'

    def handle(self, *args, **options):
        dog_elements = ['목', '화', '토', '금', '수']
        relationship_types = ['비겁', '인성', '식상', '재성', '관성']
        versions = ['A', 'B']

        total = len(dog_elements) * len(relationship_types) * len(versions)
        current = 0
        total_created = 0

        self.stdout.write(f'[START] 총 {total}개의 댕궁합 원형 생성을 시작합니다.')

        for dog_element in dog_elements:
            for relationship_type in relationship_types:
                for version in versions:
                    current += 1

                    if CompatibilityArchetype.objects.filter(
                        dog_element=dog_element,
                        relationship_type=relationship_type,
                        version=version,
                    ).exists():
                        self.stdout.write(
                            f'[SKIP] ({current}/{total}) {dog_element}-{relationship_type}-{version} 이미 존재'
                        )
                        continue

                    data = get_curated_compatibility_copy(
                        dog_element=dog_element,
                        relationship_type=relationship_type,
                        version=version,
                    )

                    CompatibilityArchetype.objects.create(
                        dog_element=dog_element,
                        relationship_type=relationship_type,
                        version=version,
                        score=data['score'],
                        title=data['title'],
                        description=data['description'],
                        advice=data['advice'],
                    )
                    total_created += 1
                    self.stdout.write(
                        f'[OK  ] ({current}/{total}) {dog_element}-{relationship_type}-{version} 생성 완료'
                    )

        self.stdout.write(f'[DONE] 완료! 총 {total_created}개 신규 생성')
