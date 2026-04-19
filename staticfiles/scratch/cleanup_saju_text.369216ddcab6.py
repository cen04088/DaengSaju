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

# Emoji regex (covers most emojis and symbols)
EMOJI_PATTERN = re.compile(r'[^\w\s,.\?\!\(\)\[\]\%\-\:\;\/\'\"]')

def split_into_paragraphs(text, max_sentences=2):
    """
    Splits a single block of text into paragraphs of max_sentences each.
    """
    # Split by sentence endings (. ! ?) followed by space
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    if not sentences:
        return text
        
    paragraphs = []
    for i in range(0, len(sentences), max_sentences):
        para = " ".join(sentences[i:i+max_sentences])
        paragraphs.append(para)
        
    return "\n\n".join(paragraphs)

# Dark/Muted Emojis -> Bright/Visible Emojis
EMOJI_REPLACEMENT_MAP = {
    '🌳': '🍀',
    '🌑': '🌟',
    '🌚': '🌟',
    '🌊': '💎',
    '🍖': '🥩',
    '🍗': '🥩',
    '🐾': '✨',
    '🐕': '🐶',
    '🩺': '✨',
    '🌲': '🌿',
    '🍂': '🌸',
    '🌑': '☀️',
}

def clean_text(text):
    if not text: return text
    
    # 1. Reduce Commas: Remove duplicate commas and commas before/after periods
    text = re.sub(r',+', ',', text)
    text = re.sub(r',\s*\.', '.', text)
    text = re.sub(r'\.\s*,', '.', text)
    
    # 2. Limit Emojis to 1 per paragraph, Replace Dark ones, and Split into shorter paragraphs
    # First, handle existing logical paragraphs
    logical_sections = text.split('\n')
    all_cleaned_paragraphs = []
    
    for section in logical_sections:
        section = section.strip()
        if not section:
            continue
            
        # Split long sections into smaller chunks if necessary
        chunks = split_into_paragraphs(section, max_sentences=2)
        for chunk in chunks.split('\n\n'):
            # First, apply replacements to ALL text
            for dark, bright in EMOJI_REPLACEMENT_MAP.items():
                chunk = chunk.replace(dark, bright)
                
            emojis = EMOJI_PATTERN.findall(chunk)
            if len(emojis) > 1:
                # Keep only the last one
                last_emoji = emojis[-1]
                # Remove all emojis from chunk
                chunk_no_emojis = EMOJI_PATTERN.sub('', chunk)
                # Add the last emoji back at the end
                chunk = chunk_no_emojis.strip() + " " + last_emoji
            all_cleaned_paragraphs.append(chunk)
    
    return '\n\n'.join(all_cleaned_paragraphs)

def cleanup_models():
    print("Starting cleanup...")
    
    # ArchetypeSaju
    print("Cleaning ArchetypeSaju...")
    for item in ArchetypeSaju.objects.all():
        updated = False
        fields = ['personality_summary', 'vitality_analysis', 'social_analysis', 'treat_luck', 'care_tips']
        for field in fields:
            val = getattr(item, field)
            if isinstance(val, str):
                cleaned = clean_text(val)
                if cleaned != val:
                    setattr(item, field, cleaned)
                    updated = True
        
        if updated:
            item.save()
            
    # DailyLuckArchetype
    print("Cleaning DailyLuckArchetype...")
    for item in DailyLuckArchetype.objects.all():
        if item.message:
            cleaned = clean_text(item.message)
            if cleaned != item.message:
                item.message = cleaned
                item.save()

    # CompatibilityArchetype
    print("Cleaning CompatibilityArchetype...")
    for item in CompatibilityArchetype.objects.all():
        updated = False
        if item.description:
            cleaned = clean_text(item.description)
            if cleaned != item.description:
                item.description = cleaned
                updated = True
        if item.advice:
            cleaned = clean_text(item.advice)
            if cleaned != item.advice:
                item.advice = cleaned
                updated = True
        if updated:
            item.save()
            
    print("Cleanup complete!")

if __name__ == '__main__':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    cleanup_models()
