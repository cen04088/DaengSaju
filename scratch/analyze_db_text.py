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

def analyze_text(text):
    if not text: return 0, 0
    # Emoji regex (basic detection of special symbols commonly used as emojis)
    emojis = len(re.findall(r'[^\w\s,.\?\!\(\)\[\]\%\-\:\;\/\'\"]', text))
    commas = text.count(',')
    return emojis, commas

def report_archetypes(model_class, name):
    print(f"\n--- {name} Analysis ---")
    items = model_class.objects.all()
    for item in items[:2]:
        text = ""
        if hasattr(item, 'message'):
            text = item.message
        elif hasattr(item, 'description'):
            text = item.description
        else:
            text = item.personality_summary
            
        e, c = analyze_text(text)
        print(f"Sample (v={getattr(item, 'version', 'N/A')}): Emojis/Symbols ~{e}, Commas {c}")
        # Use repr to see control characters/emojis clearly without causing encoding errors in some terminals
        print(f"Text snippet: {text[:150]}")


if __name__ == '__main__':
    # Fix encoding for windows terminal
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
        
    report_archetypes(ArchetypeSaju, "ArchetypeSaju")
    report_archetypes(DailyLuckArchetype, "DailyLuckArchetype")
    report_archetypes(CompatibilityArchetype, "CompatibilityArchetype")
