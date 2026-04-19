import os
import django
import sys
import re

# Set up Django
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from saju.models import ArchetypeSaju, DailyLuckArchetype, CompatibilityArchetype

# Emoji regex
EMOJI_PATTERN = re.compile(r'[^\w\s,.\?\!\(\)\[\]\%\-\:\;\/\'\"]')

def find_all_emojis():
    unique_emojis = set()
    
    # ArchetypeSaju
    for item in ArchetypeSaju.objects.all():
        fields = ['personality_summary', 'vitality_analysis', 'social_analysis', 'treat_luck', 'care_tips']
        for f in fields:
            val = getattr(item, f)
            if val:
                unique_emojis.update(EMOJI_PATTERN.findall(val))
                
    # DailyLuckArchetype
    for item in DailyLuckArchetype.objects.all():
        if item.message:
            unique_emojis.update(EMOJI_PATTERN.findall(item.message))

    # CompatibilityArchetype
    for item in CompatibilityArchetype.objects.all():
        if item.description:
            unique_emojis.update(EMOJI_PATTERN.findall(item.description))
        if item.advice:
            unique_emojis.update(EMOJI_PATTERN.findall(item.advice))
            
    return sorted(list(unique_emojis))

if __name__ == '__main__':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    emojis = find_all_emojis()
    print(f"Found {len(emojis)} unique emojis/symbols: {' '.join(emojis)}")
