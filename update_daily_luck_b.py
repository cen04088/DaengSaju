# -*- coding: utf-8 -*-
import sys
import os
import time

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from dotenv import load_dotenv
load_dotenv()

from saju.models import DailyLuckArchetype
from saju.services.gemini_ai import generate_daily_luck_template

def update_b_types():
    b_types = DailyLuckArchetype.objects.filter(version='B')
    total = b_types.count()
    current = 0
    print(f"Total B types to update: {total}")

    for archetype in b_types:
        current += 1
        print(f"[{current}/{total}] Updating {archetype.dog_element} - {archetype.relationship_type} (B)...")
        time.sleep(8) # API Limit 방지
        
        try:
            data = generate_daily_luck_template(
                dog_element=archetype.dog_element,
                relationship_type=archetype.relationship_type,
                version="B"
            )
            archetype.message = data.get("message", archetype.message)
            archetype.lucky_color = data.get("lucky_color", archetype.lucky_color)
            archetype.lucky_direction = data.get("lucky_direction", archetype.lucky_direction)
            archetype.save()
            print(f"  -> Updated!")
        except Exception as e:
            print(f"  -> Error: {e}")
            time.sleep(10) # 실패 시 조금 더 대기

if __name__ == '__main__':
    update_b_types()
    print("Done!")
