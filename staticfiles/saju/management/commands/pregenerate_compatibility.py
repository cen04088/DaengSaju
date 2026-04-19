# -*- coding: utf-8 -*-
"""
댕궁합 사전 생성 템플릿(CompatibilityArchetype) 생성 커맨드.
총 50개: 강아지 오행(5) × 십성 유형(5) × 버전(A/B) 2개
"""
import time
import sys
import io
from django.core.management.base import BaseCommand
from saju.models import CompatibilityArchetype
from saju.services.gemini_ai import generate_compatibility


class Command(BaseCommand):
    help = '댕궁합 CompatibilityArchetype 50개를 사전 생성합니다.'

    def handle(self, *args, **options):
        # 인코딩 강제 설정
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')

        dog_elements = ['목', '화', '토', '금', '수']
        relationship_types = ['비겁', '인성', '식상', '재성', '관성']
        versions = ['A', 'B']

        total = len(dog_elements) * len(relationship_types) * len(versions)
        current = 0
        total_created = 0

        print(f"[START] 총 {total}개의 댕궁합 원형 생성을 시작합니다.")
        print("API Rate Limit 방지를 위해 8초 간격으로 진행됩니다.\n", flush=True)

        for dog_element in dog_elements:
            for rel_type in relationship_types:
                for version in versions:
                    current += 1

                    if CompatibilityArchetype.objects.filter(
                        dog_element=dog_element,
                        relationship_type=rel_type,
                        version=version
                    ).exists():
                        print(f"[SKIP] ({current}/{total}) {dog_element}-{rel_type}-{version} → 이미 존재함", flush=True)
                        continue

                    print(f"[GEN ] ({current}/{total}) {dog_element}-{rel_type}-{version} → 생성 중 (8초 대기)...", flush=True)
                    time.sleep(8)

                    try:
                        data = generate_compatibility(
                            dog_element=dog_element,
                            relationship_type=rel_type,
                            version=version
                        )

                        # fallback 감지
                        if "데이터를 불러오는 데 실패" in data.get('description', ''):
                            print(f"[WARN] API 한도 초과 의심. 60초 대기 후 재시도...", flush=True)
                            time.sleep(60)
                            continue

                        CompatibilityArchetype.objects.create(
                            dog_element=dog_element,
                            relationship_type=rel_type,
                            version=version,
                            score=data.get('score', 75),
                            title=data.get('title', ''),
                            description=data.get('description', ''),
                            advice=data.get('advice', '')
                        )
                        total_created += 1
                        print(f"[OK  ] ({current}/{total}) {dog_element}-{rel_type}-{version} → 저장 완료!", flush=True)

                    except Exception as e:
                        print(f"[ERR ] 생성 실패: {str(e)[:100]}", flush=True)
                        print(f"       30초 대기 후 다음 항목으로 진행...", flush=True)
                        time.sleep(30)

        print(f"\n[DONE] 완료! 총 {total_created}개 신규 생성됨.", flush=True)
