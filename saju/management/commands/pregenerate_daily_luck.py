# -*- coding: utf-8 -*-
"""
오늘의 운세 사전 생성 템플릿(DailyLuckArchetype) 생성 커맨드.
총 25개: 강아지 오행(5) × 십성 유형(5)
"""
import time
import sys
from django.core.management.base import BaseCommand
from saju.models import DailyLuckArchetype
from saju.services.gemini_ai import generate_daily_luck_template

class Command(BaseCommand):
    help = '오늘의 산책운 DailyLuckArchetype 25개를 사전 생성합니다.'

    def handle(self, *args, **options):
        # 인코딩 강제 설정 (Windows 파워쉘 한글 깨짐 방지)
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')

        elements = ['목', '화', '토', '금', '수']
        relationship_types = ['비겁', '인성', '식상', '재성', '관성']
        versions = ['A', 'B', 'C']

        total = len(elements) * len(relationship_types) * len(versions)
        current = 0
        total_created = 0

        print(f"[START] 총 {total}개의 오늘의 운세 원형(A/B/C 버전) 생성을 시작합니다.")
        print("API Rate Limit 방지를 위해 8초 간격으로 진행됩니다.\n", flush=True)

        for element in elements:
            for rel_type in relationship_types:
                for version in versions:
                    current += 1

                    try:
                        # 이미 존재하는지 확인
                        if DailyLuckArchetype.objects.filter(
                            dog_element=element,
                            relationship_type=rel_type,
                            version=version
                        ).exists():
                            print(f"[SKIP] ({current}/{total}) {element}-{rel_type}-{version} → 이미 존재함", flush=True)
                            continue

                        print(f"[GEN ] ({current}/{total}) {element}-{rel_type}-{version} → 생성 중 (8초 대기)...", flush=True)
                        time.sleep(8)

                        data = generate_daily_luck_template(
                            dog_element=element,
                            relationship_type=rel_type,
                            version=version
                        )

                        # fallback(에러 메시지 포함 여부) 감지
                        if "데이터를 불러오는 데 실패" in data.get('message', ''):
                            print(f"[WARN] API 한도 초과 의심. 60초 대기 후 재시도...", flush=True)
                            time.sleep(60)
                            continue

                        DailyLuckArchetype.objects.create(
                            dog_element=element,
                            relationship_type=rel_type,
                            version=version,
                            message=data.get('message', ''),
                            lucky_color=data.get('lucky_color', '무지개색'),
                            lucky_direction=data.get('lucky_direction', '어디든')
                        )
                        total_created += 1
                        
                        print(f"[OK  ] ({current}/{total}) {element}-{rel_type}-{version} → 저장 완료!", flush=True)

                    except Exception as e:
                        try:
                            err_msg = str(e)
                            print(f"[ERR ] 생성 실패: {err_msg[:100]}", flush=True)
                        except:
                            print(f"[ERR ] 알 수 없는 생성 실패 (인코딩 문제 포함)", flush=True)
                        
                        print(f"       30초 대기 후 다음 항목으로 진행...", flush=True)
                        time.sleep(30)

        print(f"\n[DONE] 완료! 총 {total_created}개 신규 생성됨.", flush=True)
