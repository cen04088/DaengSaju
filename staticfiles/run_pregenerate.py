# -*- coding: utf-8 -*-
"""
평생 사주 원형(ArchetypeSaju) 사전 생성 스크립트.
Django management command 대신 독립 스크립트로 실행하여 인코딩 문제를 완전히 회피합니다.
"""
import sys
import os
import time

# stdout/stderr 인코딩 강제 설정
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# Django 설정
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from dotenv import load_dotenv
load_dotenv()

from saju.models import ArchetypeSaju
from saju.services.gemini_ai import generate_personality

def log(msg):
    print(msg, flush=True)

elements = ['목', '화', '토', '금', '수']
versions = ['A', 'B', 'C']

total = len(elements) * len(elements) * len(versions)
current = 0
total_created = 0

log(f"[START] 총 {total}개의 사주 원형 생성을 시작합니다.")
log("API Rate Limit 방지를 위해 8초 간격으로 진행됩니다. 약 10분 소요됩니다.\n")

for primary in elements:
    for strongest in elements:
        for version in versions:
            current += 1

            if ArchetypeSaju.objects.filter(
                primary_element=primary,
                strongest_element=strongest,
                version=version
            ).exists():
                log(f"[SKIP] ({current}/{total}) {primary}-{strongest}-{version} → 이미 존재함")
                continue

            log(f"[GEN ] ({current}/{total}) {primary}-{strongest}-{version} → 생성 중 (8초 대기)...")
            time.sleep(8)

            try:
                dist = {'목': 10, '화': 10, '토': 10, '금': 10, '수': 10}
                dist[strongest] = 60

                data = generate_personality(
                    dog_name="[강아지이름]",
                    main_element=primary,
                    element_dist=dist,
                    saju_text=f"전체적으로 {strongest} 기운이 강하며, 버전 {version} 스타일로 묘사해주세요."
                )

                # 폴백 데이터 감지 (API 실패 시)
                if "현재 데이터를 불러오는 데 실패했어요" in data.get('vitality_analysis', ''):
                    log(f"[WARN] 429 Rate Limit 의심! 60초 대기 후 재시도...")
                    time.sleep(60)
                    continue

                ArchetypeSaju.objects.create(
                    primary_element=primary,
                    strongest_element=strongest,
                    version=version,
                    personality_summary=data.get('personality_summary', ''),
                    personality_keywords=data.get('personality_keywords', []),
                    vitality_analysis=data.get('vitality_analysis', ''),
                    social_analysis=data.get('social_analysis', ''),
                    treat_luck=data.get('treat_luck', ''),
                    care_tips=data.get('care_tips', '')
                )
                total_created += 1
                log(f"[OK  ] ({current}/{total}) {primary}-{strongest}-{version} → 저장 완료!")

            except Exception as e:
                log(f"[ERR ] 생성 실패: {str(e)[:100]}")
                log(f"       30초 대기 후 다음 항목으로 진행...")
                time.sleep(30)

log(f"\n[DONE] 완료! 총 {total_created}개 신규 생성됨.")
