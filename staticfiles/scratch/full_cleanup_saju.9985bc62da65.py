import os
import django
import sys
import re

# Set up Django
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from saju.models import (
    ArchetypeSaju, 
    DailyLuckArchetype, 
    CompatibilityArchetype,
    DailyWalkingLuck,
    DailyElementLuck
)

# Emoji regex (covers most emojis and symbols)
# Added '*' to the exclusion list so it's not treated as an emoji
EMOJI_PATTERN = re.compile(r'[^\w\s,.\?\!\(\)\[\]\%\-\:\;\/\'\"\*]')

def split_into_paragraphs(text, max_sentences=2):
    """
    Splits a single block of text into paragraphs of max_sentences each.
    """
    # Normalize path: sometimes AI output has literal \n text instead of actual newlines
    text = text.replace('\\n', '\n')
    
    # Split by actual newlines first to honor existing structure
    original_paragraphs = text.split('\n')
    final_paragraphs = []
    
    for p in original_paragraphs:
        p = p.strip()
        if not p: continue
        
        # Split by sentence endings (. ! ?) followed by space
        sentences = re.split(r'(?<=[.!?])\s+', p)
        if not sentences:
            final_paragraphs.append(p)
            continue
            
        for i in range(0, len(sentences), max_sentences):
            para = " ".join(sentences[i:i+max_sentences])
            final_paragraphs.append(para)
            
    return "\n\n".join(final_paragraphs)

def clean_text(text):
    if not text: return text
    
    # 0. Specifically remove '*' characters as requested by the user
    text = text.replace('*', '')
    
    # 1. Basic cleaning
    text = text.replace('\\n', '\n')
    text = re.sub(r',+', ',', text)
    text = re.sub(r',\s*\.', '.', text)
    text = re.sub(r'\.\s*,', '.', text)
    
    # 2. Split into paragraphs first to get a clean base
    text_with_paras = split_into_paragraphs(text, max_sentences=2)
    
    # 3. Process each paragraph to remove all emojis
    paras = text_with_paras.split('\n\n')
    cleaned_paras = []
    
    for p in paras:
        p = p.strip()
        if not p: continue
        
        # Remove all emojis
        p = EMOJI_PATTERN.sub('', p).strip()
        
        if p:
            cleaned_paras.append(p)
        
    return '\n\n'.join(cleaned_paras)

def cleanup_models():
    print("Starting full cleanup...")
    
    models_to_clean = [
        (ArchetypeSaju, ['personality_summary', 'vitality_analysis', 'social_analysis', 'treat_luck', 'care_tips']),
        (DailyLuckArchetype, ['message']),
        (CompatibilityArchetype, ['description', 'advice']),
        (DailyWalkingLuck, ['message']),
        (DailyElementLuck, ['message']),
    ]
    
    for model_class, fields in models_to_clean:
        print(f"Cleaning {model_class.__name__}...")
        count = 0
        for item in model_class.objects.all():
            updated = False
            for field in fields:
                val = getattr(item, field)
                if isinstance(val, str):
                    cleaned = clean_text(val)
                    if cleaned != val:
                        setattr(item, field, cleaned)
                        updated = True
            
            if updated:
                item.save()
                count += 1
        print(f"  -> {count} records updated.")
            
    print("Cleanup complete!")

if __name__ == '__main__':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    cleanup_models()
